from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Automated Posting")


class PostRequest(BaseModel):
    message: str


@app.post("/posting")
async def posting(body: PostRequest):
    return {"success": True, "results": [], "message": body.message}
