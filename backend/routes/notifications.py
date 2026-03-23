from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/subscribe")
def subscribe_push():
    return JSONResponse(
        status_code=501,
        content={"detail": "Push notifications not yet implemented. Coming soon."},
    )
