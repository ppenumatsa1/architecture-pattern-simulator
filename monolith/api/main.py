from fastapi import FastAPI

from routes import router

app = FastAPI(title="Monolith API")
app.include_router(router)
