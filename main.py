from fastapi import FastAPI, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import logging
import os
from database.database import Base, engine
from routers import register,login, protected, logout, refresh, demo  
from routers.predict_router import router as predict_router
from routers.redacted_router import router as redacted_router


app = FastAPI(title="PII Sentinel", description="Real-Time PII Detection and Refaction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(register.router)
app.include_router(login.router)
app.include_router(protected.router)
app.include_router(predict_router)
app.include_router(logout.router)
app.include_router(refresh.router)
app.include_router(demo.router)
app.include_router(redacted_router)

Base.metadata.create_all(bind=engine)

@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"details": str(exc)})

logging.basicConfig(filename="logs/api.log", level=logging.INFO, format='%(asctime)s - %(message)s')
os.makedirs("uploads", exist_ok=True)
os.makedirs("redacted", exist_ok=True)

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("EMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("STMP_PASS")
SMTP_EMAIL = os.getenv("STMP_EMAIL")
FRONTEND_URL = os.getenv("FRONTEND_URL")

if not os.path.exists("DejaVuSans.ttf"):
    raise FileNotFoundError("Missing DejaVuSans.ttf — place it in the project root for PDF export.")



@app.get("/")
def root():
    return {"message": "Welcome to PII Sentinel API. Upload a CSV to detect and redact PII."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
