"""Classification and scoring with local models using TypeSafe's System One HTTP protocol."""

import asyncio
import logging
import os
import secrets
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import __version__
from .slm import SlmAdapter

MODEL_ALIAS = "system-one-cpu"
logger = logging.getLogger(__name__)


class ChoiceQuestion(BaseModel):
    type: Literal["choice"]
    instructions: str | dict[str, Any] | list[Any]
    criteria: dict[str, Any] = Field(min_length=2, max_length=32)


class NoulQuestion(BaseModel):
    type: Literal["noul"]
    instructions: str | dict[str, Any] | list[Any]
    criteria: dict[Literal["true", "false"], str] | None = None

    @field_validator("criteria")
    @classmethod
    def require_both_criteria(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is not None and set(value) != {"true", "false"}:
            raise ValueError("noul criteria must describe both true and false")
        return value


class ScoreQuestion(BaseModel):
    type: Literal["score"]
    instructions: str | dict[str, Any] | list[Any]
    criteria: list[str | dict[str, Any]] = Field(min_length=2, max_length=10)


class SystemOneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = MODEL_ALIAS
    state: Any
    questions: dict[str, ChoiceQuestion | NoulQuestion | ScoreQuestion]

    @field_validator("questions")
    @classmethod
    def require_questions(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("questions must contain at least one entry")
        return value

    @model_validator(mode="after")
    def validate_model(self) -> "SystemOneRequest":
        if self.model != MODEL_ALIAS:
            raise ValueError(f"only model {MODEL_ALIAS!r} is available")
        return self


class ChoiceAnswer(BaseModel):
    type: Literal["choice"]
    choice: str
    probabilities: dict[str, float]
    confidence: float


class NoulAnswer(BaseModel):
    type: Literal["noul"]
    noul: float


class ScoreAnswer(BaseModel):
    type: Literal["score"]
    score: float
    confidence: float
    legend: dict[str, str]
    probabilities: dict[str, float]


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int


class SystemOneResponse(BaseModel):
    model: str
    answers: dict[str, ChoiceAnswer | NoulAnswer | ScoreAnswer]
    usage: Usage
    truncation: dict[str, Any] | None = None


class VonAdapter:
    """The only code that imports Von; clients see the stable API above."""

    metadata = {
        "backend": "von",
        "backend_version": "von-1.3.5",
        "weights_revision": "411c44401cccddd792f341edfe033ea834557d13",
    }

    def __init__(self) -> None:
        self._engine: Any = None

    def warm(self) -> None:
        from von.engine import VonEngine  # Imported here so the SLM image needs no torch.

        self._engine = VonEngine.get_instance(device=os.environ.get("VON_DEVICE", "openvino:cpu"))
        self._engine.backend._get_model()  # Load weights and compile before readiness turns green.

    def evaluate(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        if self._engine is None:
            raise RuntimeError("model is not ready")
        result = self._engine.evaluate(state=state, questions=questions, model="von-1.3.0")
        return result.model_dump(exclude_none=True)


ADAPTERS = {"von": VonAdapter, "slm": SlmAdapter}


def default_adapter() -> Any:
    backend = os.environ.get("SYSTEM_ONE_BACKEND", "von")
    if backend not in ADAPTERS:
        raise ValueError(f"SYSTEM_ONE_BACKEND must be one of {sorted(ADAPTERS)}, not {backend!r}")
    return ADAPTERS[backend]()


def create_app(adapter: Any | None = None, *, eager_load: bool = True) -> FastAPI:
    engine = adapter or default_adapter()
    ready = False
    semaphore = asyncio.Semaphore(int(os.environ.get("SYSTEM_ONE_MAX_CONCURRENT", "1")))

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        nonlocal ready
        if eager_load:
            await asyncio.to_thread(engine.warm)
            ready = True
        else:
            ready = True
        yield
        ready = False
        if close := getattr(engine, "close", None):
            await asyncio.to_thread(close)

    api = FastAPI(
        title="Classification and Scoring Service",
        description=(
            "CPU-only API for classification, yes/no probabilities and scoring. "
            "Implements TypeSafe's System One HTTP protocol for interoperability."
        ),
        version=__version__,
        lifespan=lifespan,
    )

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/ready")
    def readiness(response: Response) -> dict[str, str]:
        if not ready:
            response.status_code = 503
            return {"status": "loading"}
        return {"status": "ready"}

    @api.get("/v1/models")
    def models() -> dict[str, Any]:
        model_entry = {
            "name": MODEL_ALIAS,
            "description": "CPU classification and scoring model",
        }
        return {
            "models": [model_entry],
            "object": "list",
            "data": [
                {
                    "id": MODEL_ALIAS,
                    "object": "model",
                    "owned_by": "system-one-classification",
                    "metadata": engine.metadata,
                }
            ],
        }

    @api.post("/v1/systemone", response_model=SystemOneResponse, response_model_exclude_none=True)
    async def system_one(
        request: SystemOneRequest,
        authorization: str | None = Header(default=None),
    ) -> SystemOneResponse:
        configured_key = os.environ.get("SYSTEM_ONE_API_KEY")
        if configured_key:
            supplied = authorization.removeprefix("Bearer ") if authorization else ""
            if (
                not authorization
                or not authorization.startswith("Bearer ")
                or not secrets.compare_digest(supplied, configured_key)
            ):
                raise HTTPException(status_code=401, detail="invalid bearer token")
        if not ready:
            raise HTTPException(status_code=503, detail="model is loading")
        wire_questions = {
            name: question.model_dump(exclude_none=True)
            for name, question in request.questions.items()
        }
        try:
            async with semaphore:
                result = await asyncio.to_thread(engine.evaluate, request.state, wire_questions)
            return SystemOneResponse.model_validate({**result, "model": MODEL_ALIAS})
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("model inference failed")
            raise HTTPException(status_code=503, detail="model inference failed") from exc

    return api


app = create_app()
