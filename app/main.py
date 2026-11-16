from fastapi import FastAPI

from app.schemas import PostingResponse, PostRequest
from app.services.posting_service import post_everywhere

app = FastAPI(title="Automated Posting")


@app.post("/posting", response_model=PostingResponse)
async def posting(body: PostRequest):
    results = await post_everywhere(body.message, body.link)
    return PostingResponse(success=any(r.status == "success" for r in results), results=results)
