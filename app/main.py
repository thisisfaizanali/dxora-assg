import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.platforms import PLATFORMS
from app.schemas import PostRequest, PostResponse
from app.services.posting_service import post_to_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Automated Multi-Platform Posting API",
    version="1.0.0",
    description="Publishes a message with one CTA link to several platforms and reports per-platform results.",
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        loc = [str(p) for p in err["loc"] if p != "body"]
        message = err["msg"].removeprefix("Value error, ")
        errors.append({"field": ".".join(loc) or "body", "message": message})
    return JSONResponse(status_code=422, content={"success": False, "errors": errors})


@app.post("/posting", response_model=PostResponse, summary="Publish a message to all platforms")
async def posting(request: PostRequest) -> PostResponse:
    results = await post_to_all(request.message, PLATFORMS)
    return PostResponse(success=any(r.status == "success" for r in results), results=results)
