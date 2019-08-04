from app.commons.applications import FastAPI

from app.example_v1.paths.items import router as items_router

example_v1 = FastAPI(openapi_prefix="/example/api/v1")
example_v1.include_router(items_router)
