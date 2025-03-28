from fastapi import APIRouter

from ..api.v1 import router as v1_router

appRouter = APIRouter(prefix="/api")
appRouter.include_router(v1_router)


router= APIRouter()

@router.get("/", include_in_schema=False)
async def healthcheck():
    return {"healthcheck": "true"}

router.include_router(appRouter)
