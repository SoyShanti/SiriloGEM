from pydantic_settings import BaseSettings
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")


class Settings(BaseSettings):
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")

    LM_STUDIO_BASE_URL: str = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    LM_STUDIO_API_KEY: str = os.getenv("LM_STUDIO_API_KEY", "lm-studio")

    ACE_STEP_MODEL_PATH: str = os.getenv(
        "ACE_STEP_MODEL_PATH",
        str(Path(__file__).resolve().parent.parent.parent.parent / "models" / "ace-step"),
    )
    ACE_STEP_DEVICE: str = os.getenv("ACE_STEP_DEVICE", "cuda")
    ACE_STEP_VRAM_LIMIT_GB: int = int(os.getenv("ACE_STEP_VRAM_LIMIT_GB", "10"))

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:///" + str(Path(__file__).resolve().parent.parent.parent.parent / "data" / "spotigem_v2.db")
    )

    DATA_RAW_DIR: str = os.getenv(
        "DATA_RAW_DIR", str(Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw")
    )
    DATA_PROCESSED_DIR: str = os.getenv(
        "DATA_PROCESSED_DIR", str(Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed")
    )
    OUTPUT_DIR: str = os.getenv(
        "OUTPUT_DIR", str(Path(__file__).resolve().parent.parent.parent.parent / "output" / "generated")
    )

    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "True").lower() == "true"

    class Config:
        extra = "ignore"


settings = Settings()
