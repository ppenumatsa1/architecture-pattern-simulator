from fastapi import FastAPI

from routes import router

app = FastAPI(title="Query API")
app.include_router(router)
