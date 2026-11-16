import re
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, TypeAdapter, ValidationError, field_validator

URL_PATTERN = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


def extract_links(message: str) -> list[str]:
    return [m.rstrip(".,!?;:)]}'\"") for m in URL_PATTERN.findall(message)]


class PostRequest(BaseModel):
    message: str = Field(
        description="Message to publish. Max 200 characters, exactly one CTA link.",
        examples=["Check out our latest business platform and grow your online visibility. https://example.com"],
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message must not be empty.")
        if len(value) > 200:
            raise ValueError(f"Message must not exceed 200 characters (got {len(value)}).")
        links = extract_links(value)
        if len(links) != 1:
            raise ValueError(f"Message must contain exactly one CTA link (found {len(links)}).")
        link = links[0]
        if not link.lower().startswith(("http://", "https://")):
            raise ValueError("CTA link must start with http:// or https://.")
        try:
            TypeAdapter(HttpUrl).validate_python(link)
        except ValidationError:
            raise ValueError("CTA link is not a valid URL.")
        if "." not in (urlparse(link).hostname or ""):
            raise ValueError("CTA link must have a valid domain (e.g. example.com).")
        return value


class PlatformResult(BaseModel):
    platform: str
    status: Literal["success", "failed"]
    posted_url: str | None
    public_access: bool
    date: str | None
    time: str | None
    error: str | None


class PostResponse(BaseModel):
    success: bool
    results: list[PlatformResult]
