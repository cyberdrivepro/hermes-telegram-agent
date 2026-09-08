import os
import tempfile
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from omega_api import create_router
from omega_runtime import OmegaRuntime


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = OmegaRuntime(self.temp.name)
        app = FastAPI()
        app.include_router(create_router(self.runtime))
        self.client = TestClient(app)
        self.env = patch.dict(os.environ, {"OMEGA_API_KEY": "test-operator-key"})
        self.env.start()
        self.headers = {"Authorization": "Bearer test-operator-key"}

    def tearDown(self):
        self.client.close()
        self.runtime.close()
        self.temp.cleanup()
        self.env.stop()

    def test_auth_validation_execution_and_artifact(self):
        self.assertEqual(self.client.get("/omega/capabilities").status_code, 401)
        response = self.client.post("/omega/run", json={"capability": "finance.amortization", "payload": {"principal": 1200}}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "succeeded", result)
        url = f"/omega/tasks/{result['task_id']}"
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.get(url, headers=self.headers).json(), result)
        download = self.client.get(url + "/artifacts/amortization.csv", headers=self.headers)
        self.assertEqual(download.status_code, 200)
        self.assertIn("month,payment", download.text)
        self.assertEqual(self.client.post("/omega/run", json={"capability": "unknown"}, headers=self.headers).status_code, 422)
        self.assertEqual(self.client.post("/omega/run", content="invalid", headers=self.headers).status_code, 422)

    def test_unconfigured_api_disabled(self):
        with patch.dict(os.environ, {"OMEGA_API_KEY": ""}):
            self.assertEqual(self.client.get("/omega/capabilities").status_code, 503)
