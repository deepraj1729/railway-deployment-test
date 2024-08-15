from fastapi import FastAPI,Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from redis import Redis
from urllib.parse import urlparse
import os

#? Read Redis URL from environment variable
RATE_LIMIT = int(os.getenv('RATE_LIMIT', 20))
EXPIRY_TIME = int(os.getenv('EXPIRY_TIME', 120))  # 2 minutes in seconds
REDIS_URL = os.getenv('REDIS_URL')
parsed_url = urlparse(REDIS_URL)

#? Create Redis connection
redis = Redis.from_url(
    REDIS_URL,
    decode_responses=True
)

def get_client_ip(request: Request):
    # Check for X-Forwarded-For header first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs; we want the first one
        return forwarded_for.split(',')[0].strip()
    
    # If X-Forwarded-For is not present, try X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # If neither header is present, fall back to the direct client IP
    return request.client.host

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = get_client_ip(request)
        redis_key = f"rate_limit:{client_ip}"

        #? Get the current request count for this IP
        requests = redis.get(redis_key)
        
        if requests is None:
            #? If key doesn't exist, create it with initial value 1
            redis.setex(redis_key, EXPIRY_TIME, 1)
        elif int(requests) >= RATE_LIMIT:
            #? If request count exceeds limit, raise an exception
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        else:
            #? Increment the request count
            redis.incr(redis_key)
            #? Refresh the expiry time
            redis.expire(redis_key, EXPIRY_TIME)

        response = await call_next(request)
        return response


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

#? Add Rate-limitter middleware
app.add_middleware(RateLimitMiddleware)




@app.get(path="/health",response_model=HealthCheck,status_code=200)
async def health_check(request:Request):
    return HealthCheck(status="OK")