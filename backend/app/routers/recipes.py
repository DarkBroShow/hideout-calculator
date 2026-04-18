from fastapi import APIRouter

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("/ping")
async def recipes_ping():
    return {
        "message": "recipes router is alive"
    }