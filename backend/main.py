from fastapi import FastAPI
from app.core.config import settings
from app.core.logger import logger

app = FastAPI()


@app.get("/")
def root():
    return {
        "message": "JobPilot Backend Running!"
    }

logger.info("JobPilot started successfully!")
@app.get("/")
def root():
    return {
        "model": settings.MODEL_NAME
    }