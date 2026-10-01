"""Small language model backend served by a local llama-server child process.

Each question becomes one chat prompt whose next token is an option label. Answers come
from the probabilities of those label tokens, so no text is generated or parsed.
"""

import json
import logging
import math
import os
import socket
import string
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# One manifest per bundled model; SYSTEM_ONE_SLM_MODEL names the one to serve.
MODELS_DIR = Path("model/slm")
WEIGHTS_DIR = Path("checkpoints/slm")
# One single-token label per option: choices allow 32 options and scores 10 levels.
CHOICE_LABELS = string.ascii_uppercase + "abcdef"
SCORE_LABELS = string.digits
TOP_LOGPROBS = 100
RULES = "Answer the question about the input below. Reply with only the label of the best option."
NOUL_DEFAULTS = {"true": "Yes, condition holds true.", "false": "No, condition is false."}


def to_text(value: Any) -> str:
    """Serialise structured values as Von does: canonical JSON for objects and arrays."""
    if isinstance(value, dict | list):
        return json.dumps(value, sort_keys=isinstance(value, dict))
    return str(value)


def format_state(state: Any) -> str:
    """Flatten an object state into `key: value` lines, as Von does."""
    if isinstance(state, dict):
        return "\n".join(f"{key}: {value}" for key, value in state.items())
    return str(state)


def level_text(level: str | dict[str, Any]) -> str:
    if isinstance(level, dict):
        examples = level.get("examples", [])
        suffix = f" Examples: {', '.join(examples)}" if examples else ""
        return f"{level.get('what', '')}{suffix}".strip()
    return str(level).strip()


def options(question: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return answer keys and option descriptions in wire order."""
    criteria = question.get("criteria")
    if question["type"] == "choice":
        keys = list(criteria)
        texts = ["" if criteria[key] is None else to_text(criteria[key]) for key in keys]
        return keys, [text.strip() or key.strip() for key, text in zip(keys, texts, strict=True)]
    if question["type"] == "noul":
        criteria = criteria or {}
        return ["true", "false"], [criteria.get(key) or NOUL_DEFAULTS[key] for key in NOUL_DEFAULTS]
    return [str(index) for index in range(len(criteria))], [level_text(item) for item in criteria]


def labels_for(question_type: str, count: int) -> str:
    return (SCORE_LABELS if question_type == "score" else CHOICE_LABELS)[:count]


def messages(
    state_text: str, question: dict[str, Any], descriptions: list[str], labels: str
) -> list[dict[str, str]]:
    # The state stays in the system message: llama.cpp restores Qwen3.5's cache only from
    # the start of the last user message, so later questions reuse the processed state.
    listed = "\n".join(f"{label}. {text}" for label, text in zip(labels, descriptions, strict=True))
    question_text = (
        f"{to_text(question['instructions'])}\n\nOptions:\n{listed}\n\n"
        f"Reply with one of: {', '.join(labels)}."
    )
    return [
        {"role": "system", "content": f"{RULES}\n\nInput:\n{state_text}"},
        {"role": "user", "content": question_text},
    ]


def label_probabilities(top_logprobs: list[dict[str, Any]], labels: str) -> list[float]:
    """Renormalise next-token probabilities over the labels.

    Tokens match after stripping whitespace, so "A" and " A" both count for A. A label
    missing from the candidates gets the smallest returned probability, an upper bound.
    """
    found = dict.fromkeys(labels, 0.0)
    for candidate in top_logprobs:
        token = candidate["token"].strip()
        if token in found:
            found[token] += math.exp(candidate["logprob"])
    floor = min((math.exp(candidate["logprob"]) for candidate in top_logprobs), default=1.0)
    raw = [found[label] or floor for label in labels]
    total = sum(raw)
    return [probability / total for probability in raw]


def margin_confidence(probabilities: list[float]) -> float:
    """Von's confidence, (n * p_max - 1) / (n - 1), clamped to [0, 1]."""
    n = len(probabilities)
    return round(max(0.0, min(1.0, (n * max(probabilities) - 1) / (n - 1))), 3)


def answer(
    question_type: str, keys: list[str], descriptions: list[str], probabilities: list[float]
) -> dict[str, Any]:
    rounded = {key: round(p, 4) for key, p in zip(keys, probabilities, strict=True)}
    if question_type == "noul":
        return {"type": "noul", "noul": rounded["true"]}
    confidence = margin_confidence(probabilities)
    if question_type == "choice":
        best = max(range(len(keys)), key=probabilities.__getitem__)
        return {
            "type": "choice",
            "choice": keys[best],
            "probabilities": rounded,
            "confidence": confidence,
        }
    return {
        "type": "score",
        "score": round(sum(index * p for index, p in enumerate(probabilities)), 2),
        "confidence": confidence,
        "legend": dict(zip(keys, descriptions, strict=True)),
        "probabilities": rounded,
    }


class SlmAdapter:
    """Score questions with the pinned GGUF model through llama-server on localhost."""

    def __init__(self) -> None:
        name = os.environ.get("SYSTEM_ONE_SLM_MODEL", "qwen3.5-4b")
        path = MODELS_DIR / f"{name}.json"
        if not path.is_file():
            available = sorted(manifest.stem for manifest in MODELS_DIR.glob("*.json"))
            raise ValueError(f"SYSTEM_ONE_SLM_MODEL must be one of {available}, not {name!r}")
        manifest = json.loads(path.read_text())
        (self._model_file,) = manifest["files"]
        self.metadata = {
            "backend": "slm",
            "backend_version": "llama.cpp",
            "weights_repository": manifest["repository"],
            "weights_revision": manifest["revision"],
            "weights_file": self._model_file,
        }
        self._process: subprocess.Popen | None = None
        self._client: httpx.Client | None = None
        self._closing = False

    def warm(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        command = [
            "llama-server",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--model",
            str(WEIGHTS_DIR / self._model_file),
            "--parallel",
            "1",
            "--ctx-size",
            os.environ.get("SYSTEM_ONE_SLM_CTX_SIZE", "1024"),
            "--cache-ram",
            "0",
        ]
        if threads := os.environ.get("SYSTEM_ONE_SLM_THREADS"):
            command += ["--threads", threads]
        self._process = subprocess.Popen(command)
        client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=120)
        while not self._healthy(client):
            if self._process.poll() is not None:
                raise RuntimeError(f"llama-server exited with code {self._process.returncode}")
            time.sleep(0.5)
        self.metadata["backend_version"] = f"llama.cpp {client.get('/props').json()['build_info']}"
        self._client = client
        threading.Thread(target=self._exit_with_server, daemon=True).start()

    @staticmethod
    def _healthy(client: httpx.Client) -> bool:
        try:
            return client.get("/health").status_code == 200
        except httpx.TransportError:
            return False

    def _exit_with_server(self) -> None:
        code = self._process.wait()
        if not self._closing:
            # Exit with an error so the container's restart policy brings the model back.
            logger.error("llama-server exited with code %s; stopping the service", code)
            os._exit(1)

    def close(self) -> None:
        self._closing = True
        if self._process is not None:
            self._process.terminate()
            self._process.wait(timeout=10)

    def evaluate(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("model is not ready")
        state_text = format_state(state)
        answers = {}
        input_tokens = 0
        for name, question in questions.items():
            keys, descriptions = options(question)
            labels = labels_for(question["type"], len(keys))
            response = self._client.post(
                "/v1/chat/completions",
                json={
                    "messages": messages(state_text, question, descriptions, labels),
                    "max_tokens": 1,
                    "logprobs": True,
                    "top_logprobs": TOP_LOGPROBS,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            )
            error = response.json().get("error", {}) if response.is_error else {}
            if error.get("type") == "exceed_context_size_error":
                raise ValueError(
                    f"request of {error['n_prompt_tokens']} tokens exceeds the "
                    f"{error['n_ctx']}-token context window; refusing rather than truncating"
                )
            response.raise_for_status()
            body = response.json()
            input_tokens += body["usage"]["prompt_tokens"]
            top_logprobs = body["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
            probabilities = label_probabilities(top_logprobs, labels)
            answers[name] = answer(question["type"], keys, descriptions, probabilities)
        return {
            "answers": answers,
            "usage": {"input_tokens": input_tokens, "output_tokens": len(answers)},
        }
