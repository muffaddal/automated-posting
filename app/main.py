import logging

from fastapi import FastAPI

from app.schemas import PostingResponse, PostRequest
from app.services.posting_service import post_everywhere

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Automated Posting",
    description="Publish one short message with a CTA link to several platforms at once.",
)


@app.post("/posting", response_model=PostingResponse)
async def posting(body: PostRequest):
    results = await post_everywhere(body.message, body.link)
    return PostingResponse(success=any(r.status == "success" for r in results), results=results)
