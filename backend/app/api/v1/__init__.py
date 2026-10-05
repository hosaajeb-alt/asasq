from fastapi import APIRouter

from app.api.v1 import admin, auth, collections, datasets, entities, evidence, graph, imports, investigations, quality, search

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(collections.router)
api_router.include_router(datasets.router)
api_router.include_router(imports.router)
api_router.include_router(search.router)
api_router.include_router(entities.router)
api_router.include_router(graph.router)
api_router.include_router(investigations.router)
api_router.include_router(evidence.router)
api_router.include_router(quality.router)
api_router.include_router(admin.router)
