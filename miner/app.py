"""Hosted miner HTTP app: one service that acts as every player's miner."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from miner import routes_player, routes_public, routes_validator
from miner.deps import AppState


def create_app(state: AppState) -> FastAPI:
    app = FastAPI(title="bittesnor hosted miner")
    app.add_middleware(
        CORSMiddleware, allow_origins=list(state.config.allowed_origins), allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    for module in (routes_public, routes_player, routes_validator):
        app.include_router(module.build_router(state))
    return app
