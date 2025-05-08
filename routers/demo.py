from fastapi import APIRouter, Request, Response, File, UploadFile, HTTPException
from routers.predict import predict as full_predict
from utils.session_cookies import create_demo_cookie, has_used_demo

router = APIRouter(prefix="/demo", tags=["demo"])

@router.post("/predict")
async def demo_predict(
    request: Request, 
    response: Response,
    file: UploadFile = File(...),
):
    #Check if demo has been used before
    cookie = request.cookies.get("demo_used")
    
    if cookie and has_used_demo("demo_used"):
        raise HTTPException(status_code=403, detail="Demo scan already used for today")
    
    #delegate the work to existing predict function
    result = await full_predict(file)
    
    #set cookie so they can't use demo again for 24 hours
    response.set_cookie(
        key="demo_used",
        value=create_demo_cookie,
        httponly=True,
        samesite="strict",
        max_age=60*60*24,  # 24 hours
        secure=True
        
    )
    return result