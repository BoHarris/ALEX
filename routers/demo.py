from fastapi import APIRouter, Request, Response, File, UploadFile, HTTPException
from routers.predict_router import predict as full_predict

router = APIRouter(prefix="/demo", tags=["demo"])

@router.post("/predict")
async def demo_predict(
    request: Request, 
    response: Response,
    file: UploadFile = File(...),
):
    #Check if demo has been used before
    if request.cookies.get("demo_used"):
        raise HTTPException(status_code=403, detail="Demo scan already used for today")
    
    #delegate the work to existing predict function
    result = await full_predict(file)
    
    #set cookie so they can't use demo again for 24 hours
    response.set_cookie(
        key="demo_used",
        value=1,
        max_age=60*60*24,  # 24 hours
        httponly=True,
        samesite="strict"
    )
    return result