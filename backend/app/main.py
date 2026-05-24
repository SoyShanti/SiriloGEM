import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.config import settings
from backend.app.core.database import engine, Base, init_db
from backend.app.api.router import router as api_router
from backend.app.services.registry import lm_studio, ace_step, knowledge_base, hit_predictor

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spotigem")

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SpotiGem backend...")
    await init_db()
    await knowledge_base.initialize()

    lm_ok = await lm_studio.check_availability()
    logger.info(f"LM Studio: {'available' if lm_ok else 'not available'}")

    if lm_ok:
        new_models = await lm_studio.scan_and_build_profiles()
        if new_models:
            logger.info(f"Auto-detected profiles for {len(new_models)} new model(s): {new_models}")
        active = lm_studio.get_active_profile()
        if active:
            logger.info(f"Active model profile: {active.model_id} (family={active.family}, json={active.json_reliability})")

    ace_ok = await ace_step.check_available()
    logger.info(f"ACE Step: {'available' if ace_ok else 'not available'}")

    logger.info("SpotiGem backend ready")
    yield
    logger.info("Shutting down SpotiGem backend...")
    await ace_step.unload()


app = FastAPI(
    title="SpotiGem API",
    description="AI-powered hit music generation backend using ACE Step + Spotify knowledge base",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

app.mount("/audio", StaticFiles(directory=str(OUTPUT_DIR)), name="audio")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "lm_studio": lm_studio.is_available(),
        "ace_step": ace_step.is_loaded(),
        "knowledge_base": knowledge_base.is_ready(),
    }
