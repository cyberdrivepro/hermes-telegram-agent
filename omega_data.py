"""Local SQL, bounded math, and defensive source/log analysis capabilities.

Optional NumPy and SymPy imports are lazy. No functions install packages, contact
services, run supplied Python, or open external databases. Symbolic operations
must run behind the gateway's process deadline for a hard computation limit.
"""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
import csv
import io
import ipaddress
import json
import math
import operator
from pathlib import Path
import re
import sqlite3
import time
from typing import Any
import uuid


_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z")


def _int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}")
    return value


def _number(value: Any, name: str = "number", magnitude: float = 1e100) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    if abs(value) > magnitude or not math.isfinite(value):
        raise ValueError(f"{name} must be finite with magnitude at most {magnitude:g}")
    return value


def _timeout(payload: dict) -> float:
    timeout = _number(payload.get("timeout_seconds", 5), "timeout_seconds", 60)
    if timeout <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    return float(timeout)


def _check_payload(payload: Any, maximum: int = 2_000_000) -> None:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    try:
        text = json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("payload must contain finite acyclic JSON data") from exc
    if len(text) > maximum:
        raise ValueError(f"payload exceeds {maximum} characters")


def _write(workspace: Path, name: str, content: str) -> str:
    base = Path(workspace).resolve()
    base.mkdir(parents=True, exist_ok=True)
    target = base / name
    if target.resolve().parent != base:
        raise ValueError("Artifact path leaves workspace")
    temporary = base / f".{name}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="") as stream:
            stream.write(content)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return name


def _result(workspace: Path, name: str, summary: str, data: dict) -> dict:
    artifact = _write(workspace, name, json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2))
    return {"summary": summary, "data": data, "artifacts": [artifact]}


def _quoted(name: Any) -> str:
    if not isinstance(name, str) or not _IDENTIFIER.fullmatch(name):
        raise ValueError("SQL identifiers must start with a letter and contain at most 64 letters, digits or underscores")
    return '"' + name + '"'


def _cell(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if not -(2**63) <= value < 2**63:
            raise ValueError("SQL integers must fit signed 64 bits")
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    if isinstance(value, str) and len(value) <= 16_384:
        return value
    raise ValueError("SQL cells must be null, booleans, finite numbers, or strings of at most 16384 characters")


def _csv_cell(value: Any) -> Any:
    # Spreadsheet applications interpret formula prefixes in CSV text cells.
    # Preserve raw rows in JSON and neutralize only the spreadsheet export.
    if isinstance(value, str) and value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def sql_playground(payload: dict, workspace: Path) -> dict:
    """Run one read-only SELECT against a private, bounded in-memory database.

    Input: tables=[{name, columns:[{name,type}], rows:[[...]]}], query, params.
    An optional explicit schema SQL string can create tables/indexes; top-level
    rows={table_name:[{column:value,...}]} loads those tables with bound values.
    ATTACH, extensions, virtual tables, triggers, PRAGMA and query writes are
    prohibited by SQLite's authorizer. Results include EXPLAIN and CSV output.
    """
    _check_payload(payload)
    deadline = time.monotonic() + _timeout(payload)
    query = payload.get("query")
    if not isinstance(query, str) or not query.strip() or len(query) > 100_000:
        raise ValueError("query must be a nonempty SQL string of at most 100000 characters")
    max_rows = _int(payload.get("max_rows", 1000), "max_rows", 1, 10_000)
    instruction_limit = _int(payload.get("max_instructions", 2_000_000), "max_instructions", 1000, 10_000_000)
    tables = payload.get("tables", [])
    if not isinstance(tables, list) or len(tables) > 32:
        raise ValueError("tables must be a list with at most 32 entries")
    schema = payload.get("schema", "")
    if not isinstance(schema, str) or len(schema) > 100_000:
        raise ValueError("schema must be a SQL string of at most 100000 characters")
    parameters = payload.get("params", [])
    if isinstance(parameters, list):
        if len(parameters) > 128:
            raise ValueError("At most 128 query parameters are supported")
        parameters = [_cell(value) for value in parameters]
    elif isinstance(parameters, dict):
        if len(parameters) > 128 or any(not isinstance(key, str) or len(key) > 64 for key in parameters):
            raise ValueError("Query parameters require at most 128 short string keys")
        parameters = {key: _cell(value) for key, value in parameters.items()}
    else:
        raise ValueError("params must be a list or object")
    connection = sqlite3.connect(":memory:")
    phase = "setup"
    instructions = 0
    total_rows = 0
    read_actions = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
                    getattr(sqlite3, "SQLITE_RECURSIVE", 33)}
    setup_actions = read_actions | {sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_CREATE_INDEX,
                                    sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_TRANSACTION,
                                    sqlite3.SQLITE_REINDEX}

    def authorizer(action: int, arg1: str | None, arg2: str | None, database: str | None, trigger: str | None) -> int:
        if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in {"load_extension", "readfile", "writefile", "fts3_tokenizer"}:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK if action in (setup_actions if phase == "setup" else read_actions) else sqlite3.SQLITE_DENY

    def progress() -> int:
        nonlocal instructions
        instructions += 1000
        return int(instructions >= instruction_limit or time.monotonic() >= deadline)

    def add_rows(table_name: Any, columns: list[str], rows: Any) -> None:
        nonlocal total_rows
        quoted_table = _quoted(table_name)
        quoted_columns = [_quoted(column) for column in columns]
        if not columns or len(columns) > 64 or len(set(columns)) != len(columns):
            raise ValueError("Tables require 1-64 unique columns")
        if not isinstance(rows, list) or total_rows + len(rows) > 10_000:
            raise ValueError("At most 10000 input rows are supported")
        total_rows += len(rows)
        checked_rows = []
        for row in rows:
            if time.monotonic() >= deadline:
                raise TimeoutError("SQL setup deadline exceeded")
            if isinstance(row, dict):
                if set(row) - set(columns):
                    raise ValueError("Row contains unknown columns")
                row = [row.get(column) for column in columns]
            if not isinstance(row, list) or len(row) != len(columns):
                raise ValueError("Each row must match the table column count")
            checked_rows.append([_cell(value) for value in row])
        if checked_rows:
            placeholders = ",".join("?" for _ in columns)
            connection.executemany(f"INSERT INTO {quoted_table} ({','.join(quoted_columns)}) VALUES ({placeholders})", checked_rows)

    try:
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA max_page_count = 4096")
        connection.execute("PRAGMA temp_store = MEMORY")
        if hasattr(connection, "setlimit"):
            for name, limit in (("SQLITE_LIMIT_LENGTH", 1_000_000), ("SQLITE_LIMIT_SQL_LENGTH", 100_000),
                                ("SQLITE_LIMIT_COLUMN", 128), ("SQLITE_LIMIT_EXPR_DEPTH", 64),
                                ("SQLITE_LIMIT_COMPOUND_SELECT", 20), ("SQLITE_LIMIT_ATTACHED", 0),
                                ("SQLITE_LIMIT_VARIABLE_NUMBER", 128), ("SQLITE_LIMIT_VDBE_OP", 100_000)):
                connection.setlimit(getattr(sqlite3, name), limit)
        connection.set_authorizer(authorizer)
        connection.set_progress_handler(progress, 1000)
        if schema:
            connection.executescript(schema)
        table_names = set()
        for table in tables:
            if not isinstance(table, dict):
                raise ValueError("Each table must be an object")
            name = table.get("name")
            quoted_name = _quoted(name)
            if name.lower() in table_names:
                raise ValueError("Duplicate table name")
            table_names.add(name.lower())
            columns = table.get("columns")
            if not isinstance(columns, list) or not 1 <= len(columns) <= 64:
                raise ValueError("Each table requires 1-64 column definitions")
            names, definitions = [], []
            for column in columns:
                if not isinstance(column, dict):
                    raise ValueError("Column definitions must be objects containing name and type")
                quoted_column = _quoted(column.get("name"))
                kind = column.get("type", "TEXT")
                if not isinstance(kind, str) or kind.upper() not in {"TEXT", "INTEGER", "REAL", "NUMERIC", "BLOB"}:
                    raise ValueError("Column type must be TEXT, INTEGER, REAL, NUMERIC or BLOB")
                names.append(column["name"])
                definitions.append(f"{quoted_column} {kind.upper()}")
            if len({name.lower() for name in names}) != len(names):
                raise ValueError("Column names must be unique")
            connection.execute(f"CREATE TABLE {quoted_name} ({','.join(definitions)})")
            add_rows(name, names, table.get("rows", []))
        explicit_rows = payload.get("rows", {})
        if not isinstance(explicit_rows, dict) or len(explicit_rows) > 32:
            raise ValueError("rows must map at most 32 table names to lists of row objects")
        for name, rows in explicit_rows.items():
            if not isinstance(rows, list):
                raise ValueError("Schema rows must be lists")
            if rows:
                if not isinstance(rows[0], dict):
                    raise ValueError("Top-level rows must contain objects with explicit column names")
                add_rows(name, list(rows[0]), rows)
        connection.commit()
        phase = "query"
        if time.monotonic() >= deadline:
            raise TimeoutError("SQL deadline exceeded before query")
        plan = [list(row) for row in connection.execute("EXPLAIN QUERY PLAN " + query, parameters).fetchall()]
        cursor = connection.execute(query, parameters)
        if cursor.description is None:
            raise ValueError("query must return rows")
        columns = [column[0] for column in cursor.description]
        rows = []
        output_size = 0
        truncated = False
        for index in range(max_rows + 1):
            row = cursor.fetchone()
            if row is None:
                break
            if index == max_rows:
                truncated = True
                break
            row = [{"hex": value.hex()} if isinstance(value, bytes) else value for value in row]
            output_size += len(json.dumps(row))
            if output_size > 1_500_000:
                raise ValueError("SQL results exceed the 1500000 character output limit; reduce max_rows or select fewer columns")
            rows.append(row)
        # SQLite may overflow floating calculations to infinity; JSON results
        # remain standards compliant and never silently encode NaN/Infinity.
        for row in rows:
            if any(isinstance(value, float) and not math.isfinite(value) for value in row):
                raise ValueError("SQL result contains a non-finite numeric value")
        data = {"columns": columns, "rows": rows, "row_count": len(rows), "truncated": truncated,
                "input_rows": total_rows, "query_plan": plan, "query": query,
                "approximate_vm_instructions": instructions,
                "csv_formula_cells_escaped": True,
                "recommendations": ["Review full scans in EXPLAIN before adding an index; small-table scans can be efficient."]
                if any("SCAN " in str(row[-1]) for row in plan) else []}
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow([_csv_cell(column) for column in columns])
        for row in rows:
            writer.writerow([_csv_cell(json.dumps(value) if isinstance(value, dict) else value) for value in row])
        csv_path = _write(workspace, "query_results.csv", output.getvalue())
        result = _result(workspace, "query_results.json", f"Returned {len(rows)} SQL rows{' (limit reached)' if truncated else ''} with an execution plan.", data)
        result["artifacts"].insert(0, csv_path)
        return result
    except sqlite3.OperationalError as exc:
        if "interrupted" in str(exc).lower():
            raise TimeoutError("SQL exceeded its instruction or time budget") from exc
        raise ValueError(f"SQLite rejected the operation: {exc}") from exc
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"SQLite rejected the operation: {exc}") from exc
    finally:
        connection.close()


_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
_FUNCTIONS = {"abs": abs, "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
              "tan": math.tan, "log": math.log, "log10": math.log10, "exp": math.exp,
              "floor": math.floor, "ceil": math.ceil, "radians": math.radians, "degrees": math.degrees}


def _expression_tree(expression: Any, maximum_nodes: int = 128) -> ast.Expression:
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 2048:
        raise ValueError("expression must contain 1-2048 characters")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("Invalid expression syntax") from exc
    if sum(1 for _ in ast.walk(tree)) > maximum_nodes:
        raise ValueError(f"expression exceeds {maximum_nodes} AST nodes")
    return tree


def evaluate_arithmetic(expression: str, variables: dict | None = None) -> int | float:
    """Interpret an allowlisted arithmetic AST; never eval or compile input."""
    variables = {} if variables is None else variables
    if not isinstance(variables, dict) or len(variables) > 32:
        raise ValueError("variables must contain at most 32 numeric entries")
    names = {"pi": math.pi, "e": math.e, "tau": math.tau}
    for name, value in variables.items():
        if not isinstance(name, str) or not _IDENTIFIER.fullmatch(name) or name in _FUNCTIONS or name in names:
            raise ValueError("Invalid or reserved variable name")
        names[name] = _number(value, name)
    tree = _expression_tree(expression)

    def visit(node: ast.AST, depth: int = 0) -> int | float:
        if depth > 24:
            raise ValueError("expression nesting exceeds 24 levels")
        if isinstance(node, ast.Expression):
            result = visit(node.body, depth + 1)
        elif isinstance(node, ast.Constant):
            result = _number(node.value)
        elif isinstance(node, ast.Name) and node.id in names:
            result = names[node.id]
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            result = visit(node.operand, depth + 1)
            if isinstance(node.op, ast.USub):
                result = -result
        elif isinstance(node, ast.BinOp):
            left, right = visit(node.left, depth + 1), visit(node.right, depth + 1)
            if type(node.op) in _BINARY:
                result = _BINARY[type(node.op)](left, right)
            elif isinstance(node.op, ast.Pow):
                if abs(right) > 100:
                    raise ValueError("Exponent magnitude must be at most 100")
                if left and abs(left) != 1 and right * math.log10(abs(left)) > 100:
                    raise ValueError("Exponentiation result would exceed the numeric bound")
                if left < 0 and right != int(right):
                    raise ValueError("Complex numbers are not supported by arithmetic mode")
                result = left ** right
            else:
                raise ValueError("Unsupported arithmetic operator")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS:
            if node.keywords or not 1 <= len(node.args) <= (2 if node.func.id == "log" else 1):
                raise ValueError("Invalid function arguments")
            result = _FUNCTIONS[node.func.id](*[visit(arg, depth + 1) for arg in node.args])
        else:
            raise ValueError("Expression contains an unsupported name or syntax")
        return _number(result, "result")

    try:
        return visit(tree)
    except (ArithmeticError, TypeError) as exc:
        raise ValueError(f"Arithmetic operation failed: {exc}") from exc


def calculate(payload: dict, workspace: Path) -> dict:
    _check_payload(payload, 20_000)
    value = evaluate_arithmetic(payload.get("expression"), payload.get("variables"))
    data = {"expression": payload["expression"], "value": value}
    return _result(workspace, "calculation.json", f"Result: {value}", data)


def symbolic_math(payload: dict, workspace: Path) -> dict:
    """Construct SymPy objects from a restricted AST, with lazy dependency load.

    Supports differentiate, integrate and series for up to 8 declared symbols.
    Parsing is bounded; symbolic algorithms also need a process deadline.
    """
    _check_payload(payload, 20_000)
    _timeout(payload)
    tree = _expression_tree(payload.get("expression"), maximum_nodes=96)
    symbol_names = payload.get("symbols", ["x"])
    if not isinstance(symbol_names, list) or not 1 <= len(symbol_names) <= 8 or any(
        not isinstance(name, str) or not _IDENTIFIER.fullmatch(name) or len(name) > 24 for name in symbol_names
    ) or len(set(symbol_names)) != len(symbol_names):
        raise ValueError("symbols must contain 1-8 unique simple names of at most 24 characters")
    variable = payload.get("variable", symbol_names[0])
    if not isinstance(variable, str) or variable not in symbol_names:
        raise ValueError("variable must be one of the declared symbols")
    operation = payload.get("operation", "differentiate")
    if operation not in {"differentiate", "integrate", "series"}:
        raise ValueError("operation must be differentiate, integrate, or series")
    try:
        import sympy as sp
    except ImportError as exc:
        raise RuntimeError("math.symbolic requires the optional sympy dependency; install requirements-omega.txt") from exc
    functions = {name: getattr(sp, name) for name in ("sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh", "exp", "log", "sqrt", "Abs")}
    if set(symbol_names) & (functions.keys() | {"pi", "E"}):
        raise ValueError("Symbol names cannot shadow functions or constants")
    names = {name: sp.Symbol(name) for name in symbol_names}
    names.update({"pi": sp.pi, "E": sp.E})

    def construct(node: ast.AST, depth: int = 0):
        if depth > 16:
            raise ValueError("Symbolic expression nesting exceeds 16 levels")
        if isinstance(node, ast.Expression):
            return construct(node.body, depth + 1)
        if isinstance(node, ast.Constant):
            value = _number(node.value, "symbolic constant", 1e6)
            return sp.Integer(value) if isinstance(value, int) else sp.Float(value)
        if isinstance(node, ast.Name) and node.id in names:
            return names[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            item = construct(node.operand, depth + 1)
            return item if isinstance(node.op, ast.UAdd) else sp.Mul(sp.Integer(-1), item, evaluate=False)
        if isinstance(node, ast.BinOp):
            left = construct(node.left, depth + 1)
            if isinstance(node.op, ast.Pow):
                # Only literal numeric exponents; blocks exponent towers and
                # symbolic exponents that cause disproportionate computation.
                exponent_node = node.right
                sign = 1
                if isinstance(exponent_node, ast.UnaryOp) and isinstance(exponent_node.op, ast.USub):
                    sign, exponent_node = -1, exponent_node.operand
                if not isinstance(exponent_node, ast.Constant):
                    raise ValueError("Symbolic exponents must be numeric literals")
                exponent = sign * _number(exponent_node.value, "exponent", 12)
                return sp.Pow(left, sp.Integer(exponent) if isinstance(exponent, int) else sp.Float(exponent), evaluate=False)
            right = construct(node.right, depth + 1)
            if isinstance(node.op, ast.Add):
                return sp.Add(left, right, evaluate=False)
            if isinstance(node.op, ast.Sub):
                return sp.Add(left, sp.Mul(-1, right, evaluate=False), evaluate=False)
            if isinstance(node.op, ast.Mult):
                return sp.Mul(left, right, evaluate=False)
            if isinstance(node.op, ast.Div):
                return sp.Mul(left, sp.Pow(right, -1, evaluate=False), evaluate=False)
            raise ValueError("Unsupported symbolic operator")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in functions and not node.keywords and len(node.args) == 1:
            return functions[node.func.id](construct(node.args[0], depth + 1), evaluate=False)
        raise ValueError("Symbolic expression contains unsupported syntax or an undeclared symbol")

    expression = construct(tree)
    symbol = names[variable]
    if operation == "differentiate":
        order = _int(payload.get("order", 1), "order", 1, 4)
        value = sp.diff(expression, symbol, order)
    elif operation == "integrate":
        bounds = payload.get("bounds")
        if bounds is not None:
            if not isinstance(bounds, list) or len(bounds) != 2:
                raise ValueError("bounds must contain lower and upper numeric limits")
            lower, upper = [_number(bound, "integration bound", 1e6) for bound in bounds]
            value = sp.integrate(expression, (symbol, lower, upper))
        else:
            value = sp.integrate(expression, symbol)
    else:
        order = _int(payload.get("order", 6), "order", 1, 12)
        point = _number(payload.get("point", 0), "series point", 1e6)
        value = sp.series(expression, symbol, point, order)
    text = str(value)
    if len(text) > 100_000:
        raise ValueError("Symbolic result exceeds output limit")
    unresolved = bool(value.has(sp.Integral, sp.Derivative))
    data = {"operation": operation, "expression": payload["expression"], "variable": variable,
            "result": text, "latex": sp.latex(value), "contains_unevaluated_operations": unresolved}
    return _result(workspace, "symbolic_result.json", f"{operation.capitalize()} result: {text[:1000]}", data)


def linear_algebra(payload: dict, workspace: Path) -> dict:
    """Compute SVD, determinant, inverse, eigenpairs, or a linear solve."""
    _check_payload(payload, 300_000)
    matrix = payload.get("matrix")
    if not isinstance(matrix, list) or not 1 <= len(matrix) <= 64 or not isinstance(matrix[0], list) or not 1 <= len(matrix[0]) <= 64:
        raise ValueError("matrix must contain 1-64 rows and columns")
    width = len(matrix[0])
    for row in matrix:
        if not isinstance(row, list) or len(row) != width:
            raise ValueError("matrix must be rectangular")
        for value in row:
            _number(value, "matrix value")
    operation = payload.get("operation", "svd")
    if operation not in {"svd", "inverse", "determinant", "eigen", "solve"}:
        raise ValueError("operation must be svd, inverse, determinant, eigen or solve")
    if operation != "svd" and len(matrix) != width:
        raise ValueError(f"{operation} requires a square matrix")
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("math.linear_algebra requires the optional numpy dependency; install requirements-omega.txt") from exc
    array = np.array(matrix, dtype=np.float64)

    def serial(value: Any) -> Any:
        array_value = np.asarray(value)
        if not np.isfinite(array_value).all():
            raise ValueError("Linear algebra result contains non-finite values")
        if np.iscomplexobj(array_value):
            return {"real": array_value.real.tolist(), "imag": array_value.imag.tolist()}
        return array_value.tolist()

    try:
        data: dict = {"operation": operation, "shape": [len(matrix), width]}
        if operation == "svd":
            left, singular, right = np.linalg.svd(array, full_matrices=False)
            data.update({"u": serial(left), "singular_values": serial(singular), "vh": serial(right),
                         "reconstruction_error": serial(np.linalg.norm((left * singular) @ right - array))})
        elif operation == "determinant":
            data["determinant"] = serial(np.linalg.det(array))
        elif operation == "inverse":
            data["inverse"] = serial(np.linalg.inv(array))
            data["condition_number"] = serial(np.linalg.cond(array))
        elif operation == "eigen":
            values, vectors = np.linalg.eig(array)
            data.update({"eigenvalues": serial(values), "eigenvectors": serial(vectors)})
        else:
            rhs = payload.get("rhs")
            if not isinstance(rhs, list) or len(rhs) != len(matrix):
                raise ValueError("rhs must be a numeric vector matching the row count")
            rhs = [_number(value, "rhs value") for value in rhs]
            solution = np.linalg.solve(array, np.array(rhs, dtype=np.float64))
            data.update({"solution": serial(solution), "residual_norm": serial(np.linalg.norm(array @ solution - rhs)),
                         "condition_number": serial(np.linalg.cond(array))})
    except np.linalg.LinAlgError as exc:
        raise ValueError(f"Matrix computation failed: {exc}") from exc
    return _result(workspace, "linear_algebra.json", f"Computed {operation} for a {len(matrix)} by {width} matrix.", data)


def scan_python(payload: dict, workspace: Path) -> dict:
    """Heuristic AST review of supplied Python source, without execution.

    Detects selected risky APIs and direct string-built SQL; this is not complete
    taint analysis or a security certification. Findings never echo secret values.
    """
    _check_payload(payload, 600_000)
    source = payload.get("source")
    if not isinstance(source, str) or not source or len(source) > 200_000:
        raise ValueError("source must contain 1-200000 Python characters")
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError) as exc:
        raise ValueError(f"Invalid Python syntax: {getattr(exc, 'msg', type(exc).__name__)}") from exc
    if sum(1 for _ in ast.walk(tree)) > 30_000:
        raise ValueError("Source exceeds 30000 AST nodes")
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"

    def qualified(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return qualified(node.value) + "." + node.attr
        return ""

    findings: list[dict] = []
    seen: set[tuple] = set()

    def add(node: ast.AST, rule: str, severity: str, message: str, recommendation: str) -> None:
        key = (getattr(node, "lineno", 0), rule)
        if key not in seen and len(findings) < 1000:
            seen.add(key)
            findings.append({"rule": rule, "severity": severity, "line": key[0],
                             "column": getattr(node, "col_offset", 0) + 1,
                             "message": message, "recommendation": recommendation})

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            function = qualified(node.func)
            if function in {"eval", "exec", "builtins.eval", "builtins.exec"}:
                add(node, "PY001", "high", "Dynamic Python execution API used.", "Interpret a restricted input schema or explicit AST instead of executing input.")
            if function in {"os.system", "os.popen"}:
                add(node, "PY002", "high", "Shell command API used.", "Use a fixed executable and an argument list with shell=False.")
            if function.startswith("subprocess.") and any(keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True for keyword in node.keywords):
                add(node, "PY002", "high", "subprocess is configured with shell=True.", "Use a fixed executable and an argument list with shell=False.")
            if function in {"pickle.load", "pickle.loads", "dill.load", "dill.loads", "marshal.load", "marshal.loads"}:
                add(node, "PY003", "high", "Deserializer can load executable object data.", "Use validated JSON for untrusted inputs.")
            if function in {"yaml.load", "yaml.unsafe_load", "yaml.full_load"}:
                safe_loader = any(keyword.arg == "Loader" and qualified(keyword.value) in {"yaml.SafeLoader", "yaml.CSafeLoader"} for keyword in node.keywords)
                if not safe_loader:
                    add(node, "PY004", "medium", "YAML loader lacks an explicit safe loader.", "Use yaml.safe_load or SafeLoader for external documents.")
            if function.rsplit(".", 1)[-1] in {"execute", "executemany", "executescript"} and node.args:
                first = node.args[0]
                if isinstance(first, (ast.JoinedStr, ast.BinOp)) or (isinstance(first, ast.Call) and isinstance(first.func, ast.Attribute) and first.func.attr == "format"):
                    add(node, "PY005", "high", "SQL statement is constructed from a formatted expression.", "Bind values as SQL parameters and allowlist dynamic identifiers.")
            if function.startswith(("requests.", "httpx.")) and any(keyword.arg == "verify" and isinstance(keyword.value, ast.Constant) and keyword.value.value is False for keyword in node.keywords):
                add(node, "PY006", "medium", "TLS certificate verification is disabled.", "Enable verification and configure a trusted CA bundle if needed.")
            if function in {"hashlib.md5", "hashlib.sha1"}:
                add(node, "PY007", "low", "Legacy digest algorithm used; check whether the purpose is security sensitive.", "Use SHA-256 for integrity and a password hashing algorithm for passwords.")
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value and not value.value.lower().startswith(("your_", "example", "placeholder", "<")):
                for target in targets:
                    name = target.id if isinstance(target, ast.Name) else target.attr if isinstance(target, ast.Attribute) else ""
                    if re.search(r"(?:password|passwd|secret|api_?key|access_?token|private_?key)", name, re.IGNORECASE):
                        add(node, "PY008", "high", "Possible credential is stored as a string literal.", "Load credentials from a protected environment or secret store; rotate exposed values.")
    findings.sort(key=lambda item: (item["line"], item["rule"]))
    counts = dict(Counter(item["severity"] for item in findings))
    data = {"language": "python", "findings": findings, "counts": counts,
            "review_scope": "heuristic AST rules; no execution, interprocedural taint analysis or security certification",
            "source_lines": len(source.splitlines()), "max_findings": 1000}
    return _result(workspace, "source_audit.json", f"Python AST review found {len(findings)} potential issues.", data)


_ACCESS = re.compile(r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>[A-Z]+)\s+(?P<path>\S+)\s+HTTP/[^"\s]+"\s+(?P<status>\d{3})\s+(?:\d+|-)(?:\s|$)')
_AUTH = re.compile(r"\b(?P<kind>Failed password|Invalid user|Accepted password|Accepted publickey)\b.*?\bfrom\s+(?P<ip>[0-9A-Fa-f:.]+)(?=\s|$)", re.IGNORECASE)


def analyze_logs(payload: dict, workspace: Path) -> dict:
    """Summarize supplied nginx/apache combined and sshd authentication logs.

    Flags repeated failures as review candidates. Counts have no implied time
    window unless the caller has preselected one; records do not prove an attack.
    """
    _check_payload(payload, 2_100_000)
    text = payload.get("text")
    if not isinstance(text, str) or not text or len(text) > 1_000_000:
        raise ValueError("text must contain 1-1000000 log characters")
    lines = text.splitlines()
    if len(lines) > 20_000 or any(len(line) > 16_384 for line in lines):
        raise ValueError("Logs exceed 20000 lines or 16384 characters per line")
    threshold = _int(payload.get("failure_threshold", 5), "failure_threshold", 1, 1000)
    counts = Counter()
    sources: dict[str, Counter] = defaultdict(Counter)
    statuses = Counter()
    methods = Counter()
    for line in lines:
        if not line.strip():
            counts["blank"] += 1
            continue
        access = _ACCESS.match(line)
        auth = _AUTH.search(line)
        match = access or auth
        if not match:
            counts["unparsed"] += 1
            continue
        try:
            address = str(ipaddress.ip_address(match.group("ip")))
        except ValueError:
            counts["unparsed"] += 1
            continue
        if access:
            status = int(access.group("status"))
            if not 100 <= status <= 599:
                counts["unparsed"] += 1
                continue
            counts["access"] += 1
            sources[address]["requests"] += 1
            statuses[str(status)] += 1
            methods[access.group("method")] += 1
            if status in {401, 403}:
                sources[address]["access_denied"] += 1
            if status >= 500:
                sources[address]["server_errors"] += 1
            # Keep aggregate flags only; paths/query strings can contain secrets.
            if re.search(r"(?:\.\./|%2e%2e|/\.env(?:\?|$)|/wp-login\.php)", access.group("path"), re.IGNORECASE):
                sources[address]["suspicious_paths"] += 1
        else:
            counts["authentication"] += 1
            if auth.group("kind").lower().startswith("accepted"):
                sources[address]["accepted_logins"] += 1
            else:
                sources[address]["failed_logins"] += 1
    findings = []
    for address, values in sorted(sources.items()):
        if values["failed_logins"] >= threshold:
            findings.append({"source_ip": address, "rule": "repeated_authentication_failures", "count": values["failed_logins"],
                             "assessment": "Review repeated failed login records in the supplied sample; they do not establish a confirmed attack."})
        if values["suspicious_paths"]:
            findings.append({"source_ip": address, "rule": "suspicious_request_paths", "count": values["suspicious_paths"],
                             "assessment": "Review requests matching selected sensitive-path patterns."})
    data = {"line_count": len(lines), "counts": dict(counts), "http_statuses": dict(statuses),
            "http_methods": dict(methods), "sources": {address: dict(values) for address, values in sorted(sources.items())},
            "findings": findings, "failure_threshold": threshold,
            "scope": "counts over supplied sample; no time-window inference, geolocation, attribution or confirmed-attack determination"}
    return _result(workspace, "log_analysis.json", f"Analyzed {len(lines)} log lines; {len(findings)} patterns merit review.", data)


CAPABILITIES = {
    "data.sql": sql_playground,
    "math.calculate": calculate,
    "math.symbolic": symbolic_math,
    "math.linear_algebra": linear_algebra,
    "security.sast": scan_python,
    "security.logs": analyze_logs,
}

CAPABILITY_INFO = {
    "data.sql": {"description": "Private in-memory SQL with parameter binding, EXPLAIN and CSV export", "example": {
        "tables": [{"name": "sales", "columns": [{"name": "region", "type": "TEXT"}, {"name": "amount", "type": "REAL"}],
                    "rows": [["East", 120], ["West", 90], ["East", 80]]}],
        "query": "SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY total DESC"}},
    "math.calculate": {"description": "Bounded arithmetic without executing user expressions", "example": {"expression": "sqrt(81) + 2**3"}},
    "math.symbolic": {"description": "Symbolic differentiation, integration and series; optional SymPy", "dependency": "sympy",
                      "example": {"operation": "differentiate", "expression": "x**3 + sin(x)", "symbols": ["x"]}},
    "math.linear_algebra": {"description": "SVD, eigenpairs, inverse, determinant and solve; optional NumPy", "dependency": "numpy",
                            "example": {"operation": "solve", "matrix": [[3, 1], [1, 2]], "rhs": [9, 8]}},
    "security.sast": {"description": "Defensive Python AST audit of supplied source", "example": {"source": "import subprocess\nsubprocess.run(user_command, shell=True)\n"}},
    "security.logs": {"description": "Local SSH and web-server log pattern analysis", "example": {
        "text": "Sep 7 12:00:01 host sshd[10]: Failed password for invalid user test from 192.0.2.4 port 4321 ssh2", "failure_threshold": 1}},
}
