import csv
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from omega_data import (
    CAPABILITY_INFO, analyze_logs, calculate, evaluate_arithmetic, linear_algebra,
    scan_python, sql_playground, symbolic_math,
)


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()


class SQLTests(WorkspaceTest):
    def test_aggregation_query_plan_and_csv(self):
        result = sql_playground(CAPABILITY_INFO["data.sql"]["example"], self.workspace)
        self.assertEqual(result["data"]["rows"], [["East", 200.0], ["West", 90.0]])
        self.assertTrue(result["data"]["query_plan"])
        with (self.workspace / "query_results.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(rows[0], ["region", "total"])
        self.assertEqual(rows[1], ["East", "200.0"])

    def test_explicit_schema_indexes_bound_rows_and_window_query(self):
        result = sql_playground({
            "schema": "CREATE TABLE sales(region TEXT, amount INTEGER); CREATE INDEX sales_region ON sales(region);",
            "rows": {"sales": [{"region": "East", "amount": 7}, {"region": "East", "amount": 3}, {"region": "West", "amount": 8}]},
            "query": "SELECT amount, ROW_NUMBER() OVER (PARTITION BY region ORDER BY amount DESC) AS ranking FROM sales WHERE region=:region ORDER BY amount DESC",
            "params": {"region": "East"},
        }, self.workspace)
        self.assertEqual(result["data"]["rows"], [[7, 1], [3, 2]])
        self.assertTrue(any("INDEX sales_region" in row[-1] for row in result["data"]["query_plan"]))

    def test_values_stay_data_and_csv_formula_prefix_is_escaped(self):
        attack = "x'); DROP TABLE records;--"
        result = sql_playground({
            "tables": [{"name": "records", "columns": [{"name": "text", "type": "TEXT"}], "rows": [[attack], ["=SUM(1,1)"]]}],
            "query": "SELECT text FROM records ORDER BY rowid",
        }, self.workspace)
        self.assertEqual(result["data"]["rows"], [[attack], ["=SUM(1,1)"]])
        with (self.workspace / "query_results.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(rows[2][0], "'=SUM(1,1)")

    def test_output_truncation_and_bytes_serialization(self):
        result = sql_playground({"query": "SELECT X'6162' AS bytes UNION ALL SELECT X'6364'", "max_rows": 1}, self.workspace)
        self.assertTrue(result["data"]["truncated"])
        self.assertEqual(result["data"]["rows"], [[{"hex": "6162"}]])

    def test_external_access_and_query_writes_are_denied(self):
        cases = [
            {"schema": "ATTACH DATABASE 'external.db' AS external;", "query": "SELECT 1"},
            {"schema": "CREATE VIRTUAL TABLE anything USING fts5(text);", "query": "SELECT 1"},
            {"schema": "CREATE TABLE t(x); CREATE TRIGGER tr AFTER INSERT ON t BEGIN SELECT 1; END;", "query": "SELECT 1"},
            {"query": "SELECT load_extension('anything')"},
            {"query": "PRAGMA database_list"},
            {"schema": "CREATE TABLE t(x);", "query": "INSERT INTO t VALUES (1) RETURNING x"},
            {"schema": "CREATE TABLE t(x);", "query": "DELETE FROM t RETURNING x"},
        ]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                sql_playground(payload, self.workspace)
        self.assertFalse((self.workspace / "external.db").exists())

    def test_instruction_budget_stops_recursive_query(self):
        with self.assertRaises(TimeoutError):
            sql_playground({
                "query": "WITH RECURSIVE numbers(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM numbers WHERE n<1000000000) SELECT SUM(n) FROM numbers",
                "max_instructions": 1000,
            }, self.workspace)

    def test_bad_identifiers_column_counts_and_parameters(self):
        bad_tables = [
            {"name": "t; DROP TABLE x", "columns": [{"name": "x"}]},
            {"name": "t", "columns": [{"name": "x"}, {"name": "X"}]},
            {"name": "t", "columns": [{"name": "x"}], "rows": [[1, 2]]},
            {"name": "t", "columns": [{"name": "x", "type": "TEXT); ATTACH 'x' AS a;--"}]},
        ]
        for table in bad_tables:
            with self.subTest(table=table), self.assertRaises(ValueError):
                sql_playground({"tables": [table], "query": "SELECT 1"}, self.workspace)
        with self.assertRaises(ValueError):
            sql_playground({"query": "SELECT ?", "params": [2**65]}, self.workspace)

    def test_database_is_ephemeral_across_calls(self):
        sql_playground({"schema": "CREATE TABLE t(x);", "query": "SELECT * FROM t"}, self.workspace)
        with self.assertRaises(ValueError):
            sql_playground({"query": "SELECT * FROM t"}, self.workspace)

    def test_large_generated_output_is_rejected_before_artifact_creation(self):
        with self.assertRaises(ValueError):
            sql_playground({"query": "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<30) SELECT hex(zeroblob(50000)) FROM n"}, self.workspace)
        self.assertEqual(list(self.workspace.iterdir()), [])


class ArithmeticTests(WorkspaceTest):
    def test_calculation_variables_and_functions(self):
        self.assertEqual(evaluate_arithmetic("sqrt(81) + 2**3"), 17)
        self.assertAlmostEqual(evaluate_arithmetic("sin(pi / 2) + amount * 2", {"amount": 3.5}), 8.0)
        self.assertEqual(calculate({"expression": "(21 // 2) % 3"}, self.workspace)["data"]["value"], 1)

    def test_execution_syntax_and_excessive_work_rejected(self):
        invalid = ["__import__('os').getcwd()", "(1).__class__", "[x for x in range(9)]",
                   "2 ** 10000000", "2 ** (2 ** 20)", "float('nan')",
                   "True + 1", "[1,2][0]", "unknown + 1", "lambda: 1", "1 / 0", "sqrt(-1)"]
        for expression in invalid:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                evaluate_arithmetic(expression)
        for variables in [[], {"x": float("inf")}, {"pi": 1}, {"x": "4"}]:
            with self.subTest(variables=variables), self.assertRaises(ValueError):
                evaluate_arithmetic("1", variables)

    def test_size_depth_and_nonfinite_results_rejected(self):
        for expression in ["1+" * 500 + "1", "-" * 30 + "1", "1e309", "exp(10000)"]:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                evaluate_arithmetic(expression)


class OptionalDependencyTests(WorkspaceTest):
    def test_missing_symbolic_dependency_is_actionable(self):
        with patch.dict(sys.modules, {"sympy": None}), self.assertRaisesRegex(RuntimeError, "sympy"):
            symbolic_math({"expression": "x**2"}, self.workspace)

    def test_missing_numpy_dependency_is_actionable(self):
        with patch.dict(sys.modules, {"numpy": None}), self.assertRaisesRegex(RuntimeError, "numpy"):
            linear_algebra({"matrix": [[1]], "operation": "inverse"}, self.workspace)

    @unittest.skipUnless(importlib.util.find_spec("sympy"), "optional sympy not installed")
    def test_symbolic_derivative_integral_and_series(self):
        import sympy as sp
        derivative = symbolic_math({"operation": "differentiate", "expression": "x**3 + sin(x)"}, self.workspace)
        self.assertEqual(derivative["data"]["result"], "3*x**2 + cos(x)")
        integral = symbolic_math({"operation": "integrate", "expression": "x**2", "bounds": [0, 3]}, self.workspace)
        self.assertEqual(integral["data"]["result"], "9")
        series = symbolic_math({"operation": "series", "expression": "sin(x)", "order": 5}, self.workspace)
        self.assertIn("x**3/6", series["data"]["result"])

    @unittest.skipUnless(importlib.util.find_spec("sympy"), "optional sympy not installed")
    def test_symbolic_injection_undeclared_names_and_exponents_rejected(self):
        for expression in ["__import__('os').system('echo unsafe')", "x.__class__", "x**(2**12)", "x**99", "y + 1"]:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                symbolic_math({"expression": expression}, self.workspace)

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "optional numpy not installed")
    def test_svd_reconstruction_and_linear_solve(self):
        result = linear_algebra({"matrix": [[1, 2], [3, 4], [5, 6]], "operation": "svd"}, self.workspace)
        self.assertLess(result["data"]["reconstruction_error"], 1e-12)
        solved = linear_algebra(CAPABILITY_INFO["math.linear_algebra"]["example"], self.workspace)
        self.assertAlmostEqual(solved["data"]["solution"][0], 2)
        self.assertAlmostEqual(solved["data"]["solution"][1], 3)
        self.assertLess(solved["data"]["residual_norm"], 1e-12)

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "optional numpy not installed")
    def test_complex_eigenvalues_are_json_serializable(self):
        result = linear_algebra({"operation": "eigen", "matrix": [[0, -1], [1, 0]]}, self.workspace)
        self.assertIn("imag", result["data"]["eigenvalues"])
        self.assertEqual(sorted(result["data"]["eigenvalues"]["imag"]), [-1.0, 1.0])
        json.dumps(result, allow_nan=False)

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "optional numpy not installed")
    def test_bad_shapes_singular_and_nonfinite_matrices_fail(self):
        cases = [
            {"matrix": [[1, 2], [3]], "operation": "svd"},
            {"matrix": [[1, 2]], "operation": "inverse"},
            {"matrix": [[1, 2], [2, 4]], "operation": "inverse"},
            {"matrix": [[float("nan")]], "operation": "svd"},
            {"matrix": [[True]], "operation": "svd"},
        ]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                linear_algebra(payload, self.workspace)


class DefensiveAnalysisTests(WorkspaceTest):
    def test_ast_aliases_shell_sql_deserialization_and_redacted_secrets(self):
        source = """import subprocess as proc
from pickle import loads as restore
import requests
password = 'DO_NOT_ECHO_THIS_SECRET'
proc.run(command, shell=True)
restore(blob)
cursor.execute(f'SELECT * FROM users WHERE name={name}')
requests.get(url, verify=False)
"""
        result = scan_python({"source": source}, self.workspace)
        rules = {finding["rule"] for finding in result["data"]["findings"]}
        self.assertTrue({"PY002", "PY003", "PY005", "PY006", "PY008"}.issubset(rules))
        self.assertNotIn("DO_NOT_ECHO_THIS_SECRET", json.dumps(result))
        self.assertTrue(all(finding["line"] > 0 for finding in result["data"]["findings"]))

    def test_parameterized_sql_safe_yaml_and_argument_list_do_not_trigger(self):
        source = """import subprocess
import yaml
subprocess.run(['echo', message], shell=False)
cursor.execute('SELECT * FROM users WHERE name=?', (name,))
data = yaml.safe_load(text)
other = yaml.load(text, Loader=yaml.SafeLoader)
"""
        result = scan_python({"source": source}, self.workspace)
        self.assertEqual(result["data"]["findings"], [])

    def test_syntax_error_does_not_execute_source(self):
        with self.assertRaises(ValueError):
            scan_python({"source": "def broken(:\n"}, self.workspace)

    def test_auth_access_logs_ipv6_and_failure_threshold(self):
        lines = [f"Sep 7 12:00:0{i} host sshd[10]: Failed password for invalid user test from 192.0.2.4 port 4321 ssh2" for i in range(5)]
        lines.extend([
            "Sep 7 12:00:08 host sshd[10]: Accepted publickey for test from 2001:db8::1 port 4321 ssh2",
            '192.0.2.8 - - [07/Sep/2026:12:00:01 +0000] "GET /.env?token=DO_NOT_ECHO HTTP/1.1" 403 10 "-" "client"',
            "unstructured diagnostic line",
        ])
        result = analyze_logs({"text": "\n".join(lines)}, self.workspace)
        self.assertEqual(result["data"]["sources"]["192.0.2.4"]["failed_logins"], 5)
        self.assertEqual(result["data"]["sources"]["2001:db8::1"]["accepted_logins"], 1)
        self.assertEqual(result["data"]["counts"]["unparsed"], 1)
        self.assertEqual(len(result["data"]["findings"]), 2)
        self.assertNotIn("DO_NOT_ECHO", json.dumps(result))

    def test_malformed_ip_status_and_nonlog_lines_remain_unparsed(self):
        text = '\n'.join([
            '999.1.1.1 - - [07/Sep/2026:12:00:01 +0000] "GET / HTTP/1.1" 200 10',
            '192.0.2.1 - - [07/Sep/2026:12:00:01 +0000] "GET / HTTP/1.1" 999 10',
            "text without a supported log format",
        ])
        result = analyze_logs({"text": text}, self.workspace)
        self.assertEqual(result["data"]["counts"]["unparsed"], 3)
        self.assertEqual(result["data"]["sources"], {})


if __name__ == "__main__":
    unittest.main()
