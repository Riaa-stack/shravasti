from fastapi import APIRouter

from app.api.v1 import auth, users, papers, knowledge_graph, agents, search, analytics, export

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(knowledge_graph.router, prefix="/knowledge-graph", tags=["knowledge_graph"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
