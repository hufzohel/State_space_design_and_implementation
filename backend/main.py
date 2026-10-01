from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router


app = FastAPI(
    title="AI Search API",
    description="Backend for Pipes and Minesweeper AI Search",
    version="1.0.0"
)


# Allow the frontend (Live Server) to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routes
app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "AI Search API is running"
    }