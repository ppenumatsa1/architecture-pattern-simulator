from fastapi import FastAPI

from routes import router

app = FastAPI(title="Command API")
app.include_router(router)
