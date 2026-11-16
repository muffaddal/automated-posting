from fastapi import FastAPI

from app.schemas import PostingResponse, PostRequest

app = FastAPI(title="Automated Posting")


@app.post("/posting", response_model=PostingResponse)
async def posting(body: PostRequest):
    return PostingResponse(success=True, results=[])
