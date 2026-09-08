"""Bounded, reproducible planning and candidate search.

This module records task outcomes and externally supplied evaluation criteria. It
does not generate or persist private model reasoning. Injected callables are
trusted application code; deadlines are cooperative at their call boundaries.
Run untrusted or potentially blocking executors in a separate process supervisor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import random
import re
import time
from typing import Any, Callable, Mapping
import uuid


_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_RESERVED_PATHS = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def _integer(value: Any, name: str, lower: int, upper: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
        raise ValueError(f"{name} must be an integer from {lower} to {upper}")
    return value


def _seconds(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("timeout_seconds must be numeric")
    value = float(value)
    if not math.isfinite(value) or not 0 < value <= 60:
        raise ValueError("timeout_seconds must be greater than 0 and at most 60")
    return value


def _json_size(value: Any, limit: int = 1_000_000) -> None:
    try:
        encoded = json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("Input must be finite, acyclic JSON data") from exc
    if len(encoded) > limit:
        raise ValueError(f"Input exceeds the {limit} character limit")


def _artifact(workspace: Path, name: str, data: Any) -> str:
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / name
    if target.resolve().parent != workspace:
        raise ValueError("Artifact target leaves workspace")
    temporary = workspace / f".{name}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, allow_nan=False, indent=2)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return name


class TaskDAG:
    """Validate a task DAG before dispatch; failed descendants are skipped.

    ``executor(task, dependencies, remaining_seconds)`` receives only declared
    dependency outcomes. It must enforce its own interruption within the supplied
    budget. Independent tasks continue after a failure unless fail_fast is set.
    """

    def __init__(self, tasks: list[dict], max_nodes: int = 128):
        _integer(max_nodes, "max_nodes", 1, 512)
        if not isinstance(tasks, list) or not 1 <= len(tasks) <= max_nodes:
            raise ValueError(f"tasks must contain 1 to {max_nodes} task objects")
        _json_size(tasks)
        self.tasks: dict[str, dict] = {}
        for task in tasks:
            if not isinstance(task, dict):
                raise ValueError("Each task must be an object")
            task_id = task.get("id")
            if not isinstance(task_id, str) or not _ID.fullmatch(task_id) or task_id.upper() in _RESERVED_PATHS:
                raise ValueError("Task id must contain 1-64 letters, digits, underscores or hyphens")
            if task_id in self.tasks:
                raise ValueError(f"Duplicate task id: {task_id}")
            operation = task.get("operation")
            if not isinstance(operation, str) or not operation or len(operation) > 128:
                raise ValueError(f"Task {task_id} requires an operation name")
            dependencies = task.get("depends_on", [])
            if not isinstance(dependencies, list) or any(not isinstance(dep, str) for dep in dependencies):
                raise ValueError(f"Task {task_id} depends_on must be a list of task ids")
            if len(dependencies) != len(set(dependencies)):
                raise ValueError(f"Task {task_id} has duplicate dependencies")
            if not isinstance(task.get("payload", {}), dict):
                raise ValueError(f"Task {task_id} payload must be an object")
            self.tasks[task_id] = {
                "id": task_id, "operation": operation,
                "depends_on": list(dependencies), "payload": task.get("payload", {}),
            }
        self.order: list[str] = []
        remaining = {key: set(task["depends_on"]) for key, task in self.tasks.items()}
        for task_id, dependencies in remaining.items():
            missing = dependencies - self.tasks.keys()
            if missing:
                raise ValueError(f"Task {task_id} has unknown dependencies: {sorted(missing)}")
        while remaining:
            ready = [key for key, dependencies in remaining.items() if not dependencies]
            if not ready:
                raise ValueError("Task dependencies contain a cycle")
            self.order.extend(ready)
            for key in ready:
                del remaining[key]
            for dependencies in remaining.values():
                dependencies.difference_update(ready)

    def execute(
        self,
        executor: Callable[[dict, dict, float], Any],
        *,
        timeout_seconds: float = 10,
        fail_fast: bool = False,
        clock: Callable[[], float] = time.monotonic,
    ) -> dict:
        budget = _seconds(timeout_seconds)
        if not isinstance(fail_fast, bool):
            raise ValueError("fail_fast must be a boolean")
        start = clock()
        deadline = start + budget
        results: dict[str, dict] = {}
        events: list[dict] = []
        halted = False
        result_characters = 0
        for task_id in self.order:
            task = self.tasks[task_id]
            blocked = [dep for dep in task["depends_on"] if results[dep]["status"] != "succeeded"]
            if blocked:
                outcome = {"status": "skipped", "reason": "failed_dependency", "dependencies": blocked}
            elif halted:
                outcome = {"status": "skipped", "reason": "fail_fast"}
            elif clock() >= deadline:
                outcome = {"status": "skipped", "reason": "deadline"}
            else:
                task_started = clock()
                dependencies = {dep: results[dep]["result"] for dep in task["depends_on"]}
                try:
                    value = executor(task, dependencies, max(0.0, deadline - task_started))
                    _json_size(value)
                    encoded_size = len(json.dumps(value, allow_nan=False))
                    if result_characters + encoded_size > 1_000_000:
                        raise ValueError("Combined plan results exceed 1000000 characters")
                    if clock() > deadline:
                        outcome = {"status": "timed_out", "reason": "executor_exceeded_deadline"}
                    elif isinstance(value, dict) and (value.get("success") is False or value.get("status") in {"failed", "error"}):
                        outcome = {"status": "failed", "reason": "executor_reported_failure", "result": value}
                    else:
                        outcome = {"status": "succeeded", "result": value}
                    if "result" in outcome:
                        result_characters += encoded_size
                except Exception as exc:
                    outcome = {"status": "failed", "error_type": type(exc).__name__, "error": str(exc)[:500]}
                outcome["elapsed_ms"] = round(max(0.0, clock() - task_started) * 1000, 3)
                if outcome["status"] in {"failed", "timed_out"} and fail_fast:
                    halted = True
            results[task_id] = outcome
            events.append({"task_id": task_id, "operation": task["operation"], "status": outcome["status"],
                           "reason": outcome.get("reason")})
        counts = {status: sum(item["status"] == status for item in results.values())
                  for status in ("succeeded", "failed", "timed_out", "skipped")}
        return {"status": "succeeded" if counts["succeeded"] == len(self.tasks) else "incomplete",
                "order": list(self.order), "tasks": results, "counts": counts, "events": events,
                "elapsed_ms": round(max(0.0, clock() - start) * 1000, 3),
                "deadline_mode": "cooperative_executor_boundaries"}


@dataclass
class _SearchNode:
    state: Any
    parent: "_SearchNode | None" = None
    children: list["_SearchNode"] = field(default_factory=list)
    unexpanded: list[Any] | None = None
    visits: int = 0
    total_reward: float = 0.0


class UCTSearch:
    """Monte Carlo tree search using UCT selection and random rollouts.

    ``children(state)`` must return a bounded list. ``evaluate(state)`` returns a
    reward in [0, 1], or {reward: float, criteria: [str, ...]}. Evaluation criteria
    are observable assessment notes, not a model's internal reasoning trace.
    """

    def __init__(self, children: Callable[[Any], list], evaluate: Callable[[Any], Any],
                 *, seed: int = 0, exploration: float = math.sqrt(2)):
        _integer(seed, "seed", 0, 2**32 - 1)
        if isinstance(exploration, bool) or not isinstance(exploration, (int, float)) or not math.isfinite(exploration) or not 0 <= exploration <= 10:
            raise ValueError("exploration must be a finite number from 0 to 10")
        self.children = children
        self.evaluate = evaluate
        self.seed = seed
        self.exploration = float(exploration)

    def search(self, initial_state: Any, *, max_iterations: int = 256,
               max_nodes: int = 512, max_depth: int = 32,
               timeout_seconds: float = 10,
               clock: Callable[[], float] = time.monotonic) -> dict:
        _integer(max_iterations, "max_iterations", 1, 10_000)
        _integer(max_nodes, "max_nodes", 1, 2048)
        _integer(max_depth, "max_depth", 1, 64)
        deadline = clock() + _seconds(timeout_seconds)
        rng = random.Random(self.seed)
        root = _SearchNode(initial_state)
        allocated = 1
        completed = 0
        best: dict | None = None
        log: list[dict] = []
        stop_reason = "iteration_limit"

        def next_states(state: Any) -> list:
            values = self.children(state)
            if not isinstance(values, list) or len(values) > 2048:
                raise ValueError("children(state) must return a list with at most 2048 states")
            return list(values)

        for iteration in range(max_iterations):
            if clock() >= deadline:
                stop_reason = "deadline"
                break
            node = root
            depth = 0
            while depth < max_depth:
                if clock() >= deadline:
                    break
                if node.unexpanded is None:
                    node.unexpanded = next_states(node.state)
                if node.unexpanded and allocated < max_nodes:
                    state = node.unexpanded.pop(rng.randrange(len(node.unexpanded)))
                    child = _SearchNode(state, parent=node)
                    node.children.append(child)
                    node = child
                    allocated += 1
                    depth += 1
                    break
                if not node.children:
                    break
                parent_log = math.log(max(1, node.visits))
                node = max(node.children, key=lambda child: (
                    child.total_reward / child.visits + self.exploration * math.sqrt(parent_log / child.visits)
                    if child.visits else float("inf")
                ))
                depth += 1
            state = node.state
            rollout_depth = depth
            terminal = False
            while rollout_depth < max_depth and clock() < deadline:
                successors = next_states(state)
                if not successors:
                    terminal = True
                    break
                state = rng.choice(successors)
                rollout_depth += 1
            if clock() >= deadline:
                stop_reason = "deadline"
                break
            try:
                evaluation = self.evaluate(state)
                if isinstance(evaluation, dict):
                    reward = evaluation.get("reward")
                    criteria = evaluation.get("criteria", [])
                else:
                    reward, criteria = evaluation, []
                if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward) or not 0 <= reward <= 1:
                    raise ValueError("Evaluator reward must be finite and between 0 and 1")
                if not isinstance(criteria, list) or any(not isinstance(item, str) for item in criteria):
                    raise ValueError("Evaluator criteria must be a list of strings")
                if clock() >= deadline:
                    stop_reason = "deadline"
                    break
                reward = float(reward)
                criteria = [item[:500] for item in criteria[:16]]
                if best is None or reward > best["reward"]:
                    best = {"state": state, "reward": reward, "criteria": criteria, "terminal": terminal}
                entry = {"iteration": iteration + 1, "reward": reward, "state": state,
                         "criteria": criteria, "rollout_depth": rollout_depth, "terminal": terminal}
            except Exception as exc:
                reward = 0.0
                entry = {"iteration": iteration + 1, "reward": reward, "state": state,
                         "error_type": type(exc).__name__, "error": str(exc)[:500]}
            while node is not None:
                node.visits += 1
                node.total_reward += reward
                node = node.parent
            completed += 1
            if len(log) < 64:
                log.append(entry)
        choices = [{"state": child.state, "visits": child.visits,
                    "mean_reward": child.total_reward / child.visits if child.visits else None}
                   for child in root.children]
        visited_choices = [choice for choice in choices if choice["visits"]]
        selected = max(visited_choices, key=lambda item: (item["visits"], item["mean_reward"])) if visited_choices else None
        return {"algorithm": "UCT Monte Carlo tree search", "selected": selected, "best_evaluated": best,
                "choices": choices, "iterations": completed, "nodes": allocated, "seed": self.seed,
                "stop_reason": stop_reason, "evaluations": log, "log_truncated": completed > len(log),
                "deadline_mode": "cooperative_evaluator_boundaries"}


def search_candidates(payload: dict, workspace: Path) -> dict:
    """Search an explicit finite tree: tree={id, score?, children:[tree,...]}.

    Leaf scores are caller-supplied measurements in [0,1]. They are not estimates
    of truth or model confidence. ``candidates`` is a flat-tree convenience input.
    """
    _json_size(payload)
    raw_tree = payload.get("tree")
    if raw_tree is None:
        raw_tree = {"id": "root", "children": payload.get("candidates", [])}
    nodes: dict[str, dict] = {}

    def visit(raw: Any, depth: int = 0) -> str:
        if depth > 32 or len(nodes) >= 512:
            raise ValueError("Candidate tree exceeds 512 nodes or depth 32")
        if not isinstance(raw, dict):
            raise ValueError("Each candidate must be an object")
        node_id = raw.get("id")
        if not isinstance(node_id, str) or not _ID.fullmatch(node_id) or node_id in nodes:
            raise ValueError("Candidate ids must be unique, with 1-64 letters, digits, underscores or hyphens")
        children = raw.get("children", [])
        if not isinstance(children, list):
            raise ValueError("Candidate children must be a list")
        score = raw.get("score")
        if score is None and not children:
            raise ValueError("Each leaf candidate requires an explicit score")
        if score is not None and (isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1):
            raise ValueError("Candidate scores must be finite numbers in [0,1]")
        criteria = raw.get("criteria", [])
        if not isinstance(criteria, list) or len(criteria) > 16 or any(not isinstance(value, str) or len(value) > 500 for value in criteria):
            raise ValueError("Candidate criteria must contain at most 16 strings of at most 500 characters")
        nodes[node_id] = {"children": [], "reward": float(score) if score is not None else None, "criteria": criteria}
        nodes[node_id]["children"] = [visit(child, depth + 1) for child in children]
        return node_id

    initial = visit(raw_tree)
    search = UCTSearch(lambda state: nodes[state]["children"],
                       lambda state: {"reward": nodes[state]["reward"], "criteria": nodes[state]["criteria"]},
                       seed=payload.get("seed", 0), exploration=payload.get("exploration", math.sqrt(2)))
    data = search.search(initial, max_iterations=payload.get("max_iterations", 256),
                         max_nodes=payload.get("max_nodes", 512), max_depth=payload.get("max_depth", 32),
                         timeout_seconds=payload.get("timeout_seconds", 10))
    data["score_source"] = "caller_supplied_measurements"
    artifact = _artifact(workspace, "search_results.json", data)
    best = data["best_evaluated"]
    summary = (f"Evaluated {data['iterations']} candidate rollouts; best observed candidate: {best['state']} ({best['reward']:.3f})."
               if best else "Search finished before any valid evaluation completed.")
    return {"summary": summary, "data": data, "artifacts": [artifact]}


def _resolve_references(value: Any, dependencies: Mapping[str, Any], depth: int = 0) -> Any:
    if depth > 32:
        raise ValueError("Task payload nesting exceeds 32 levels")
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            reference = value["$ref"]
            if not isinstance(reference, str) or len(reference) > 512:
                raise ValueError("$ref must be a path string of at most 512 characters")
            parts = reference.split(".")
            if parts[0] not in dependencies:
                raise ValueError(f"Reference must name a declared dependency: {parts[0]}")
            current = dependencies[parts[0]]
            for part in parts[1:]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
                    current = current[int(part)]
                else:
                    raise ValueError(f"Reference does not exist: {reference}")
            return current
        return {key: _resolve_references(item, dependencies, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_references(item, dependencies, depth + 1) for item in value]
    return value


def plan_tasks(payload: dict, workspace: Path) -> dict:
    """Validate or execute a finite DAG of allowlisted local data capabilities.

    Execution requires ``execute: true``. Task payloads may use a single-key
    ``{"$ref": "dependency.data.value"}`` object to consume an earlier result.
    """
    _json_size(payload)
    graph = TaskDAG(payload.get("tasks"), max_nodes=payload.get("max_nodes", 128))
    execute = payload.get("execute", False)
    if not isinstance(execute, bool):
        raise ValueError("execute must be a boolean")
    artifacts: list[str] = []
    if execute:
        from omega_data import CAPABILITIES as data_capabilities
        operations = dict(data_capabilities)
        operations["reasoning.search"] = search_candidates
        operations["echo"] = lambda args, directory: {"summary": "Echoed explicit input", "data": args, "artifacts": []}
        unknown = sorted({task["operation"] for task in graph.tasks.values()} - operations.keys())
        if unknown:
            raise ValueError(f"Plan contains unsupported operations: {unknown}")
        base = Path(workspace).resolve()
        base.mkdir(parents=True, exist_ok=True)

        def dispatch(task: dict, dependencies: dict, remaining: float) -> dict:
            args = _resolve_references(task["payload"], dependencies)
            # Cap inner operations to the current plan budget; each capability
            # still applies its own hard input and resource limits.
            requested = _seconds(args.get("timeout_seconds", 10))
            args = dict(args, timeout_seconds=min(requested, remaining))
            directory = base / task["id"]
            if directory.resolve().parent != base:
                raise ValueError("Task directory leaves workspace")
            directory.mkdir(exist_ok=True)
            result = operations[task["operation"]](args, directory)
            for filename in result.get("artifacts", []):
                artifact_path = (directory / filename).resolve()
                if not artifact_path.is_relative_to(directory.resolve()) or not artifact_path.is_file():
                    raise ValueError("Task returned an invalid artifact path")
                artifacts.append(artifact_path.relative_to(base).as_posix())
            return result

        data = graph.execute(dispatch, timeout_seconds=payload.get("timeout_seconds", 10),
                             fail_fast=payload.get("fail_fast", False))
        summary = f"Plan {data['status']}: {data['counts']['succeeded']} succeeded, {data['counts']['failed']} failed, {data['counts']['skipped']} skipped."
    else:
        data = {"status": "validated", "order": graph.order, "tasks": list(graph.tasks.values()),
                "node_count": len(graph.tasks)}
        summary = f"Validated {len(graph.tasks)} tasks in dependency order."
    artifacts.append(_artifact(workspace, "plan_results.json", data))
    return {"summary": summary, "data": data, "artifacts": artifacts}


CAPABILITIES = {
    "reasoning.plan": plan_tasks,
    "reasoning.search": search_candidates,
}

CAPABILITY_INFO = {
    "reasoning.plan": {
        "description": "Validate or execute a bounded DAG with dependency result references",
        "example": {"execute": True, "tasks": [
            {"id": "base", "operation": "math.calculate", "payload": {"expression": "6 * 7"}},
            {"id": "next", "operation": "math.calculate", "depends_on": ["base"],
             "payload": {"expression": "answer + 8", "variables": {"answer": {"$ref": "base.data.value"}}}},
        ]},
    },
    "reasoning.search": {
        "description": "Seeded UCT Monte Carlo search over an explicit candidate tree and supplied scores",
        "example": {"candidates": [{"id": "quick", "score": 0.65}, {"id": "thorough", "score": 0.9}],
                    "max_iterations": 128, "seed": 42},
    },
}
