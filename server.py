from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

class HealthCheck(BaseModel):
    status: str = "OK"

app = FastAPI()

#? Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get(path="/health",response_model=HealthCheck,status_code=200)
async def health_check(request:Request):
    return HealthCheck(status="OK")