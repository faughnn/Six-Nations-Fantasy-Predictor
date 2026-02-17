from fastapi import APIRouter

from app.api.players import router as players_router
from app.api.predictions import router as predictions_router
from app.api.stats import router as stats_router
from app.api.matches import router as matches_router
from app.api.scrape import router as scrape_router
from app.api.auth import router as auth_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(players_router, prefix="/players", tags=["players"])
api_router.include_router(predictions_router, prefix="/predictions", tags=["predictions"])
api_router.include_router(stats_router, prefix="/stats", tags=["stats"])
api_router.include_router(matches_router, prefix="/matches", tags=["matches"])
api_router.include_router(scrape_router, prefix="/scrape", tags=["scrape"])
