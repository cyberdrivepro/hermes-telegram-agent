import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from omega_reasoning import CAPABILITY_INFO, TaskDAG, UCTSearch, plan_tasks, search_candidates


class TaskDAGTests(unittest.TestCase):
    def test_topological_order_and_dependency_results(self):
        graph = TaskDAG([
            {"id": "end", "operation": "sum", "depends_on": ["left", "right"]},
            {"id": "left", "operation": "value"},
            {"id": "right", "operation": "value"},
        ])
        calls = []

        def execute(task, dependencies, remaining):
            calls.append(task["id"])
            self.assertGreater(remaining, 0)
            return sum(dependencies.values()) if dependencies else 21

        result = graph.execute(execute)
        self.assertEqual(calls, ["left", "right", "end"])
        self.assertEqual(result["tasks"]["end"]["result"], 42)
        self.assertEqual(result["status"], "succeeded")

    def test_invalid_graphs_fail_before_dispatch(self):
        cases = [
            [], [{"id": "a", "operation": "x", "depends_on": ["missing"]}],
            [{"id": "a", "operation": "x", "depends_on": ["a"]}],
            [{"id": "a", "operation": "x", "depends_on": ["b"]}, {"id": "b", "operation": "x", "depends_on": ["a"]}],
            [{"id": "a", "operation": "x"}, {"id": "a", "operation": "x"}],
            [{"id": "../outside", "operation": "x"}],
            [{"id": "CON", "operation": "x"}],
            [{"id": "a", "operation": "x", "depends_on": "b"}],
            [{"id": "a", "operation": "x", "payload": []}],
        ]
        for tasks in cases:
            with self.subTest(tasks=tasks), self.assertRaises(ValueError):
                TaskDAG(tasks)

    def test_failed_descendants_skip_and_independent_work_continues(self):
        graph = TaskDAG([
            {"id": "broken", "operation": "x"},
            {"id": "dependent", "operation": "x", "depends_on": ["broken"]},
            {"id": "transitive", "operation": "x", "depends_on": ["dependent"]},
            {"id": "independent", "operation": "x"},
        ])
        calls = []

        def execute(task, dependencies, remaining):
            calls.append(task["id"])
            if task["id"] == "broken":
                raise RuntimeError("Fixture failure")
            return 7

        result = graph.execute(execute)
        self.assertEqual(calls, ["broken", "independent"])
        self.assertEqual(result["tasks"]["dependent"]["reason"], "failed_dependency")
        self.assertEqual(result["tasks"]["transitive"]["reason"], "failed_dependency")
        self.assertEqual(result["counts"], {"succeeded": 1, "failed": 1, "timed_out": 0, "skipped": 2})

    def test_reported_failure_and_fail_fast(self):
        graph = TaskDAG([{"id": "first", "operation": "x"}, {"id": "second", "operation": "x"}])
        result = graph.execute(lambda *args: {"success": False}, fail_fast=True)
        self.assertEqual(result["tasks"]["first"]["status"], "failed")
        self.assertEqual(result["tasks"]["second"]["reason"], "fail_fast")

    def test_deadline_marks_overrun_and_does_not_start_more_work(self):
        now = [0.0]
        graph = TaskDAG([{"id": "slow", "operation": "x"}, {"id": "next", "operation": "x"}])

        def slow(*args):
            now[0] += 2
            return "completed late"

        result = graph.execute(slow, timeout_seconds=1, clock=lambda: now[0])
        self.assertEqual(result["tasks"]["slow"]["status"], "timed_out")
        self.assertEqual(result["tasks"]["next"]["reason"], "deadline")
        self.assertNotIn("result", result["tasks"]["slow"])

    def test_non_json_executor_result_fails(self):
        graph = TaskDAG([{"id": "bad", "operation": "x"}])
        result = graph.execute(lambda *args: float("nan"))
        self.assertEqual(result["tasks"]["bad"]["status"], "failed")

    def test_aggregate_result_budget_prevents_log_expansion(self):
        graph = TaskDAG([{"id": "first", "operation": "x"}, {"id": "second", "operation": "x"}])
        result = graph.execute(lambda *args: "x" * 600_000)
        self.assertEqual(result["tasks"]["first"]["status"], "succeeded")
        self.assertEqual(result["tasks"]["second"]["status"], "failed")
        self.assertIn("Combined plan results", result["tasks"]["second"]["error"])

    def test_node_limit_and_invalid_budgets(self):
        with self.assertRaises(ValueError):
            TaskDAG([{"id": "a", "operation": "x"}, {"id": "b", "operation": "x"}], max_nodes=1)
        graph = TaskDAG([{"id": "a", "operation": "x"}])
        for budget in [0, -1, float("nan"), True, 61]:
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                graph.execute(lambda *args: 1, timeout_seconds=budget)


class UCTTests(unittest.TestCase):
    @staticmethod
    def tree():
        return {"root": ["weak", "strong"], "weak": ["weak_a", "weak_b"],
                "strong": ["strong_a", "strong_b"], "weak_a": [], "weak_b": [],
                "strong_a": [], "strong_b": []}

    def test_uct_prefers_high_reward_branch_and_backpropagates(self):
        tree = self.tree()
        scores = {"weak_a": 0.1, "weak_b": 0.2, "strong_a": 0.9, "strong_b": 1.0}
        search = UCTSearch(tree.__getitem__, lambda state: scores[state], seed=7)
        result = search.search("root", max_iterations=400)
        self.assertEqual(result["selected"]["state"], "strong")
        self.assertEqual(result["best_evaluated"]["state"], "strong_b")
        choices = {item["state"]: item for item in result["choices"]}
        self.assertGreater(choices["strong"]["visits"], choices["weak"]["visits"])
        self.assertEqual(sum(item["visits"] for item in result["choices"]), 400)
        self.assertEqual(result["nodes"], 7)
        self.assertTrue(result["log_truncated"])

    def test_seed_is_reproducible(self):
        tree = self.tree()
        evaluator = lambda state: 0.8 if state.startswith("strong") else 0.2
        first = UCTSearch(tree.__getitem__, evaluator, seed=12).search("root", max_iterations=30)
        second = UCTSearch(tree.__getitem__, evaluator, seed=12).search("root", max_iterations=30)
        self.assertEqual(first, second)

    def test_node_and_depth_limits_with_unbounded_conceptual_tree(self):
        evaluator = lambda depth: min(depth / 10, 1)
        result = UCTSearch(lambda depth: [depth + 1, depth + 2], evaluator).search(0, max_depth=3, max_nodes=2, max_iterations=20)
        self.assertLessEqual(result["nodes"], 2)
        self.assertTrue(all(item["rollout_depth"] <= 3 for item in result["evaluations"]))
        self.assertEqual(result["iterations"], 20)

    def test_evaluator_failures_recorded_and_search_continues(self):
        def evaluate(state):
            if state == "bad":
                raise ValueError("Measurement unavailable")
            return {"reward": 0.8, "criteria": ["Passed fixture test"]}

        result = UCTSearch(lambda state: ["bad", "good"] if state == "root" else [], evaluate).search("root", max_iterations=40)
        self.assertEqual(result["iterations"], 40)
        self.assertEqual(result["best_evaluated"]["state"], "good")
        self.assertTrue(any("error" in item for item in result["evaluations"]))
        self.assertEqual(result["best_evaluated"]["criteria"], ["Passed fixture test"])

    def test_invalid_reward_never_becomes_best(self):
        result = UCTSearch(lambda state: [], lambda state: float("nan")).search("root", max_iterations=2)
        self.assertIsNone(result["best_evaluated"])
        self.assertTrue(all(item["error_type"] == "ValueError" for item in result["evaluations"]))

    def test_slow_evaluation_is_discarded_after_deadline(self):
        now = [0]

        def evaluate(state):
            now[0] = 3
            return 1

        result = UCTSearch(lambda state: [], evaluate).search("root", timeout_seconds=1, clock=lambda: now[0])
        self.assertEqual(result["stop_reason"], "deadline")
        self.assertEqual(result["iterations"], 0)
        self.assertIsNone(result["best_evaluated"])


class ReasoningCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_plan_validation_does_not_execute(self):
        result = plan_tasks({"tasks": [{"id": "step", "operation": "unknown"}]}, self.workspace)
        self.assertEqual(result["data"]["status"], "validated")
        self.assertEqual(list(self.workspace.iterdir()), [self.workspace / "plan_results.json"])

    def test_references_pass_numeric_result_between_tasks(self):
        result = plan_tasks(CAPABILITY_INFO["reasoning.plan"]["example"], self.workspace)
        self.assertEqual(result["data"]["tasks"]["next"]["result"]["data"]["value"], 50)
        self.assertEqual(result["data"]["counts"]["succeeded"], 2)
        self.assertIn("base/calculation.json", result["artifacts"])
        for artifact in result["artifacts"]:
            self.assertTrue((self.workspace / artifact).is_file())

    def test_reference_requires_declared_dependency(self):
        result = plan_tasks({"execute": True, "tasks": [
            {"id": "source", "operation": "echo", "payload": {"value": 4}},
            {"id": "other", "operation": "echo", "payload": {"value": {"$ref": "source.data.value"}}},
        ]}, self.workspace)
        self.assertEqual(result["data"]["tasks"]["other"]["status"], "failed")

    def test_unknown_operation_fails_before_side_effects(self):
        with self.assertRaises(ValueError):
            plan_tasks({"execute": True, "tasks": [
                {"id": "valid", "operation": "math.calculate", "payload": {"expression": "2 + 2"}},
                {"id": "bad", "operation": "arbitrary.code"},
            ]}, self.workspace)
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_candidate_api_and_artifact(self):
        result = search_candidates(CAPABILITY_INFO["reasoning.search"]["example"], self.workspace)
        self.assertEqual(result["data"]["best_evaluated"]["state"], "thorough")
        stored = json.loads((self.workspace / "search_results.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["score_source"], "caller_supplied_measurements")

    def test_duplicate_and_out_of_range_candidates_rejected(self):
        for candidates in [[], [{"id": "a"}], [{"id": "a", "score": 2}], [{"id": "a", "score": 0.3}, {"id": "a", "score": 0.4}]]:
            with self.subTest(candidates=candidates), self.assertRaises(ValueError):
                search_candidates({"candidates": candidates}, self.workspace)


if __name__ == "__main__":
    unittest.main()
