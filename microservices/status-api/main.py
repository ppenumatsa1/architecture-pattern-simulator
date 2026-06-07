from fastapi import FastAPI

from sse import router

app = FastAPI(title="Status API")
app.include_router(router)
