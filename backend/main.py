import os
from dotenv import load_dotenv

load_dotenv()  # MUST run before any imports that trigger genai.configure()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import audit

app = FastAPI(title="InsightScrape API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For 24h assignment keep it simple, or specify Vercel domains later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "InsightScrape backend is running"}

app.include_router(audit.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
