"""Local photo restoration studio, backed by the existing PyTorch model."""
import asyncio
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from .demo import checkpoint_path
from .restore import load_generator, restore_image

ASSETS = Path(__file__).with_name("studio_assets")
MAX_BYTES = 24 * 1024 * 1024
MAX_PIXELS = 25_000_000


def create_studio(checkpoint=None):
    model = load_generator(checkpoint_path(checkpoint))
    lock = asyncio.Lock()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/studio", StaticFiles(directory=ASSETS), name="studio")

    @app.get("/")
    def home():
        return FileResponse(ASSETS / "archive.html", headers={"Cache-Control": "no-cache"})

    @app.get("/workbench")
    def workbench():
        return FileResponse(ASSETS / "index.html", headers={"Cache-Control": "no-cache"})

    def render(upload, refine):
        try:
            with Image.open(upload, formats=["JPEG", "PNG", "WEBP"]) as photo:
                if photo.width * photo.height > MAX_PIXELS:
                    raise HTTPException(413, "Choose an image of 25 megapixels or less.")
                result = restore_image(photo, model, refine=refine)
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise HTTPException(400, "Choose a readable JPEG, PNG, or WebP image.") from exc
        output = BytesIO()
        result.save(output, format="PNG", compress_level=1)
        return output.getvalue()

    @app.post("/api/restore")
    async def restore(request: Request, refine: bool = False):
        if request.headers.get("content-type") != "application/octet-stream":
            raise HTTPException(415, "Send the image as application/octet-stream.")
        if lock.locked():
            raise HTTPException(503, "The studio is busy. Try again in a moment.")
        async with lock:
            upload = BytesIO()
            async for chunk in request.stream():
                if upload.tell() + len(chunk) > MAX_BYTES:
                    raise HTTPException(413, "Choose a file no larger than 24 MB.")
                upload.write(chunk)
            upload.seek(0)
            result = await run_in_threadpool(render, upload, refine)
        return Response(result, media_type="image/png", headers={"Cache-Control": "no-store"})

    return app
