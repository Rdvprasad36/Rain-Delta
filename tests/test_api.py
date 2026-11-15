"""
Tests for api/main.py using FastAPI TestClient.

Uses offline fixture data — no network, no GRIB parsing.
"""

import sys
import os
import json
import pytest
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Point store to test fixture dir
os.environ["STORE_DIR"] = str(Path(__file__).parent / "data" / "store")

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_returns_200(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_has_disclaimer(self):
        resp = client.get("/api/health")
        body = resp.json()
        assert "disclaimer" in body
        assert len(body["disclaimer"]) > 20

    def test_has_attribution(self):
        resp = client.get("/api/health")
        body = resp.json()
        assert "attribution" in body
        assert "ECMWF" in body["attribution"]

    def test_schema(self):
        resp = client.get("/api/health")
        body = resp.json()
        assert "models" in body
        assert "ifs" in body["models"]
        assert "aifs" in body["models"]


class TestLatestEndpoint:
    def test_returns_200(self):
        resp = client.get("/api/latest?lat=17.7&lon=83.2")
        assert resp.status_code == 200

    def test_has_required_fields(self):
        resp = client.get("/api/latest?lat=17.7&lon=83.2")
        body = resp.json()
        assert "disclaimer" in body
        assert "attribution" in body
        assert "windows" in body
        assert "location" in body

    def test_location_echoed(self):
        resp = client.get("/api/latest?lat=17.7&lon=83.2")
        body = resp.json()
        assert abs(body["location"]["lat"] - 17.7) < 0.01
        assert abs(body["location"]["lon"] - 83.2) < 0.01

    def test_cache_header(self):
        resp = client.get("/api/latest")
        assert "cache-control" in resp.headers


class TestRevisionEndpoint:
    def test_returns_200(self):
        resp = client.get("/api/revision?model=ifs&step_end=24")
        assert resp.status_code == 200

    def test_has_revision_key(self):
        resp = client.get("/api/revision?model=ifs&step_end=24")
        body = resp.json()
        assert "revision" in body

    def test_revision_schema(self):
        resp = client.get("/api/revision?model=ifs&step_end=24")
        body = resp.json()
        rev = body["revision"]
        assert "direction" in rev
        assert rev["direction"] in ["up", "down", "steady", "insufficient_data"]

    def test_disclaimer_present(self):
        resp = client.get("/api/revision")
        body = resp.json()
        assert "disclaimer" in body


class TestDisagreementEndpoint:
    def test_returns_200(self):
        resp = client.get("/api/disagreement?step_end=24")
        assert resp.status_code == 200

    def test_has_disagreement(self):
        resp = client.get("/api/disagreement?step_end=24")
        body = resp.json()
        assert "disagreement" in body

    def test_disagreement_schema(self):
        resp = client.get("/api/disagreement?step_end=24")
        body = resp.json()
        d = body["disagreement"]
        assert "diff_mm" in d
        assert "wetter_model" in d
        assert d["wetter_model"] in ["IFS", "AIFS", "equal"]
        assert "close" in d

    def test_has_explanation(self):
        resp = client.get("/api/disagreement?step_end=24")
        body = resp.json()
        assert "explanation" in body
        expl = body["explanation"]
        assert "forecast" in expl
        assert "disclaimer" in expl
