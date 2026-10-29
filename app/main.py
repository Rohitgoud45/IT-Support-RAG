import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config
from .generate import answer_question
from .ingest import ingest
from .store import get_collection

log = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Build the index on first boot so a fresh container works with no manual step.
    if get_collection().count() == 0:
        ingest(reset=False)
    yield


app = FastAPI(title="IT Support Assistant", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@app.get("/api/health")
def health():
    from .llm import get_active_provider
    provider = get_active_provider()
    return {
        "status": "ok",
        "chunks": get_collection().count(),
        "provider": provider,
        "model": config.LLM_MODEL or config.get_default_model(provider),
    }


@app.post("/api/ask")
def ask(req: AskRequest):
    try:
        result = answer_question(req.question.strip())
    except Exception as exc:  # log the details, give the UI a clean message
        log.exception("Answer generation failed")
        raise HTTPException(
            status_code=502, detail="Answer generation failed. Please try again in a moment."
        ) from exc
    result.pop("retrieved", None)  # internal, used by the eval harness
    return result


if config.FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=config.FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse(config.FRONTEND_DIST / "index.html")
