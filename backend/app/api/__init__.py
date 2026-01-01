from fastapi import APIRouter

from app.api.players import router as players_router
from app.api.predictions import router as predictions_router
from app.api.optimiser import router as optimiser_router
from app.api.scrape import router as scrape_router
from app.api.import_data import router as import_router

api_router = APIRouter()

api_router.include_router(players_router, prefix="/players", tags=["players"])
api_router.include_router(predictions_router, prefix="/predictions", tags=["predictions"])
api_router.include_router(optimiser_router, prefix="/optimise", tags=["optimiser"])
api_router.include_router(scrape_router, prefix="/scrape", tags=["scraping"])
api_router.include_router(import_router, prefix="/import", tags=["import"])
