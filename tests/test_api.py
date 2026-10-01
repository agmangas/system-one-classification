"""Exercise the public wire contract with an injected model adapter."""

import pytest
from fastapi.testclient import TestClient

from system_one_service.app import MODEL_ALIAS, create_app


class FakeAdapter:
    metadata = {"backend": "fake"}

    def __init__(self) -> None:
        self.warmed = False
        self.received = None

    def warm(self) -> None:
        self.warmed = True

    def evaluate(self, state, questions):
        self.received = (state, questions)
        return {
            "answers": {
                "material": {
                    "type": "choice",
                    "choice": "unknown",
                    "probabilities": {"steel": 0.1, "unknown": 0.9},
                    "confidence": 0.8,
                }
            },
            "usage": {"input_tokens": 20, "output_tokens": 1},
        }


def test_choice_wire_contract_and_readiness():
    adapter = FakeAdapter()
    with TestClient(create_app(adapter)) as client:
        assert adapter.warmed
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/ready").json() == {"status": "ready"}
        model = client.get("/v1/models").json()["data"][0]
        assert (model["id"], model["metadata"]) == (MODEL_ALIAS, {"backend": "fake"})
        response = client.post(
            "/v1/systemone",
            json={
                "model": MODEL_ALIAS,
                "state": {"name": "alumnium"},
                "questions": {
                    "material": {
                        "type": "choice",
                        "instructions": "Identify the material.",
                        "criteria": {"steel": "Iron alloy", "unknown": "None applies"},
                    }
                },
            },
        )
        assert response.status_code == 200
        assert response.json()["model"] == MODEL_ALIAS
        assert response.json()["answers"]["material"]["choice"] == "unknown"
        assert adapter.received[0] == {"name": "alumnium"}
        assert adapter.received[1]["material"]["criteria"]["unknown"] == "None applies"


def test_rejects_bad_model_and_malformed_questions():
    with TestClient(create_app(FakeAdapter())) as client:
        for body in (
            {
                "model": "von-1.3.0",
                "state": "x",
                "questions": {
                    "q": {"type": "choice", "instructions": "x", "criteria": {"a": "a", "b": "b"}}
                },
            },
            {"state": "x", "questions": {}},
            {
                "state": "x",
                "questions": {
                    "q": {"type": "noul", "instructions": "x", "criteria": {"true": "yes"}}
                },
            },
            {
                "state": "x",
                "questions": {
                    "q": {"type": "score", "instructions": "x", "criteria": ["only one"]}
                },
            },
        ):
            assert client.post("/v1/systemone", json=body).status_code == 422


def test_backend_is_chosen_at_deploy_time(monkeypatch):
    monkeypatch.setenv("SYSTEM_ONE_BACKEND", "slm")
    with TestClient(create_app(eager_load=False)) as client:
        metadata = client.get("/v1/models").json()["data"][0]["metadata"]
        assert (metadata["backend"], metadata["weights_file"]) == ("slm", "Qwen3.5-4B-Q4_K_M.gguf")
    monkeypatch.setenv("SYSTEM_ONE_SLM_MODEL", "bonsai-4b")
    with TestClient(create_app(eager_load=False)) as client:
        metadata = client.get("/v1/models").json()["data"][0]["metadata"]
        assert metadata["weights_file"] == "Bonsai-4B-Q1_0.gguf"
    monkeypatch.setenv("SYSTEM_ONE_BACKEND", "gpu")
    with pytest.raises(ValueError, match="SYSTEM_ONE_BACKEND"):
        create_app(eager_load=False)
