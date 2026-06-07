from fastapi import FastAPI

from routes import router

app = FastAPI(title="Submission API")
app.include_router(router)
