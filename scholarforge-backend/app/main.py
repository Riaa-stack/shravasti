from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.websockets.progress_ws import router as progress_router
from app.websockets.chat_ws import router as chat_router

app = FastAPI(
    title="ScholarForge AI API",
    description="AI-Powered Research Assistant Platform",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(progress_router)
app.include_router(chat_router)

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.APP_ENV}
