import re
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, TypeAdapter, ValidationError, field_validator

URL_RE = re.compile(r"https?://\S+")
_url = TypeAdapter(HttpUrl)


def find_links(text: str) -> list[str]:
    return [m.rstrip(".,!?;:)'\"") for m in URL_RE.findall(text)]


class PostRequest(BaseModel):
    message: str = Field(examples=[
        "Check out our latest business platform and grow your online visibility. https://example.com"
    ])

    @field_validator("message")
    @classmethod
    def check_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message cannot be empty")
        if len(v) > 200:
            raise ValueError(f"message is {len(v)} characters, max is 200")

        links = find_links(v)
        if len(links) != 1:
            raise ValueError(f"message must contain exactly one CTA link, found {len(links)}")

        try:
            url = _url.validate_python(links[0])
        except ValidationError:
            raise ValueError(f"invalid URL: {links[0]}")
        if not url.host or "." not in url.host:
            raise ValueError(f"invalid URL host: {links[0]}")
        return v

    @property
    def link(self) -> str:
        return find_links(self.message)[0]


class PostResult(BaseModel):
    platform: str
    status: Literal["success", "failed"]
    posted_url: str | None = None
    public_access: bool = False
    date: str | None = None
    time: str | None = None
    error: str | None = None


class PostingResponse(BaseModel):
    success: bool
    results: list[PostResult]
