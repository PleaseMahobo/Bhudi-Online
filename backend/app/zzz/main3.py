from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bhudi-online-6bhc4pq5j-trusts-projects-97c4157c.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ALL API ROUTES MUST LIVE UNDER /api
app.include_router(api_router, prefix="/api")


@app.get("/")
def root():
    return {"status": "backend is alive"}

print("🔥 MAIN.PY IS RUNNING")