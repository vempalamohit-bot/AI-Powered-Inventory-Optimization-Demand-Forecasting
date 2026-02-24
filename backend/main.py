from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api.routes import router
from app.api.integrations import router as integrations_router
from app.api.chat import router as chat_router
from app.services.alert_scheduler import get_alert_scheduler

# Create database tables (ignore if connection fails)
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")
except Exception as e:
    print(f"Warning: Could not create database tables: {e}")
    print("Continuing without database tables...")

app = FastAPI(
    title="AI-Powered Inventory Optimization API",
    description="Demand forecasting and inventory optimization system",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ],
    allow_origin_regex=r"https://.*\.(ngrok-free\.app|loca\.lt|trycloudflare\.com)",  # Allow tunnels (Colab)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)
app.include_router(integrations_router)
app.include_router(chat_router)

alert_scheduler = get_alert_scheduler()


@app.on_event("startup")
async def start_background_services():
    await alert_scheduler.start()


@app.on_event("shutdown")
async def stop_background_services():
    await alert_scheduler.stop()

@app.get("/")
def read_root():
    return {
        "message": "AI-Powered Inventory Optimization API",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
