"""On-demand export of approved classroom books, outside the generation graph."""
import logging
import re
from html import escape
from io import BytesIO
from pathlib import PurePosixPath
from threading import BoundedSemaphore

from fastapi import APIRouter, Depends, HTTPException, Response
from PIL import Image

import providers
from app import db
from app.auth import get_current_user
from app.config import (
    MAX_SCENES, MAX_TITLE_CHARS, PDF_MAX_CAPTION_CHARS, PDF_MAX_IMAGE_BYTES,
    PDF_MAX_IMAGE_PIXELS, PDF_MAX_TOTAL_IMAGE_BYTES,
)

pdf_router = APIRouter()
_render_slot = BoundedSemaphore(1)
_log = logging.getLogger(__name__)
_PRIVATE = {"Cache-Control": "private, no-store"}


def _approved_book(job_id: str, user_id: str) -> dict:
    client = db.get_supabase_client()
    viewers = (client.table("profiles").select("role, removed_at, classroom_id")
               .eq("id", user_id).execute().data)
    if not viewers:
        raise HTTPException(404, "book not found", headers=_PRIVATE)
    viewer = viewers[0]
    if (viewer.get("role") != "student" or viewer.get("removed_at") is not None
            or not viewer.get("classroom_id")):
        raise HTTPException(404, "book not found", headers=_PRIVATE)
    rows = (
        client.table("jobs")
        .select("id, profile_id, classroom_id, status, approved_at, rejected_at, title, pages, "
                "profiles!inner(role, removed_at, classroom_id)")
        .eq("id", job_id).eq("classroom_id", viewer["classroom_id"]).execute().data
    )
    if not rows:
        raise HTTPException(404, "book not found", headers=_PRIVATE)
    row = rows[0]
    profile = row.get("profiles") or {}
    if (row["classroom_id"] != viewer["classroom_id"] or profile.get("role") != "student"
            or profile.get("removed_at") is not None or not profile.get("classroom_id")
            or profile["classroom_id"] != row["classroom_id"]):
        raise HTTPException(404, "book not found", headers=_PRIVATE)
    if (row["status"] != "complete" or not row.get("approved_at")
            or row.get("rejected_at") or not row.get("pages")):
        if row["profile_id"] != user_id:
            raise HTTPException(404, "book not found", headers=_PRIVATE)
        raise HTTPException(409, "book not ready for download", headers=_PRIVATE)
    return row


def render_book_pdf(title: str, pages: list[dict], images: list[bytes]) -> bytes:
    # Lazy import: non-export routes do not load native rendering libraries.
    from weasyprint import HTML
    from weasyprint.urls import FatalURLFetchingError, URLFetcher, URLFetcherResponse

    class BookImages(URLFetcher):
        def fetch(self, url, headers=None):
            if url not in image_sources:
                raise ValueError("external PDF resources are not allowed")
            return URLFetcherResponse(url, body=image_sources[url])

    image_sources = {f"book-image:{index}": image for index, image in enumerate(images)}
    scenes = []
    for index, page in enumerate(pages):
        heading = f"<h1>{escape(title)}</h1>" if index == 0 else ""
        scenes.append(
            f'<section>{heading}<img src="book-image:{index}" alt="{escape(page["caption"], quote=True)}">'
            f'<p>{escape(page["caption"])}</p></section>'
        )
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
      <title>{escape(title)}</title><style>
      @page {{ size: A4; margin: 17mm 18mm 20mm;
        @bottom-center {{ content: counter(page) " / " counter(pages);
          font: 10pt "DejaVu Sans", sans-serif; color: #5b617a; }} }}
      body {{ margin: 0; color: #18204a; font: 14pt/1.6 "DejaVu Sans", sans-serif; }}
      section {{ break-before: page; }} section:first-child {{ break-before: auto; }}
      h1 {{ font-size: 25pt; line-height: 1.2; margin: 0 0 9mm;
        overflow-wrap: anywhere; }}
      img {{ display: block; width: auto; height: auto; max-width: 100%; max-height: 145mm;
        margin: 0 auto 8mm; }}
      p {{ margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; orphans: 3; widows: 3; }}
      </style></head><body>{''.join(scenes)}</body></html>"""
    # No base_url, default fetcher or disk cache: only the validated in-memory images are visible.
    try:
        return HTML(string=html, url_fetcher=BookImages(fail_on_errors=True)).write_pdf()
    except FatalURLFetchingError:
        raise ValueError("PDF image unavailable") from None


@pdf_router.get(
    "/jobs/{job_id}/pdf", response_class=Response,
    responses={200: {"content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}}}},
)
def download_pdf(job_id: str, user=Depends(get_current_user)) -> Response:
    acquired = False
    try:
        row = _approved_book(job_id, user.id)
        acquired = _render_slot.acquire(blocking=False)
        if not acquired:
            raise HTTPException(503, "download busy, try again", headers=_PRIVATE)
        pages = row["pages"]
        if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_SCENES:
            raise ValueError("invalid page count")
        title = row.get("title") or "Untitled"
        if not isinstance(title, str) or len(title) > MAX_TITLE_CHARS:
            raise ValueError("invalid title")
        images = []
        total_bytes = 0
        for page in pages:
            caption = page["caption"]
            path = page["image_path"]
            if not isinstance(caption, str) or not caption.strip() or len(caption) > PDF_MAX_CAPTION_CHARS:
                raise ValueError("invalid caption")
            if (not isinstance(path, str) or not path.startswith(f"{job_id}/") or "\\" in path
                    or ".." in PurePosixPath(path).parts or str(PurePosixPath(path)) != path):
                raise ValueError("invalid image path")
            image_bytes = providers.download_book_image(path)
            total_bytes += len(image_bytes)
            if len(image_bytes) > PDF_MAX_IMAGE_BYTES or total_bytes > PDF_MAX_TOTAL_IMAGE_BYTES:
                raise ValueError("image budget exceeded")
            # WeasyPrint logs missing/broken images and otherwise returns a partial PDF. Decode
            # every final image first so a broken one fails the whole download instead.
            with Image.open(BytesIO(image_bytes)) as image:
                if (image.format not in {"PNG", "JPEG", "WEBP"}
                        or image.width * image.height > PDF_MAX_IMAGE_PIXELS):
                    raise ValueError("invalid image")
                image.load()
            images.append(image_bytes)
        pdf = render_book_pdf(title, pages, images)
        _approved_book(job_id, user.id)  # Approval or membership withdrawal must stop this download too.
        slug = re.sub(r"[^A-Za-z0-9_-]+", "-", title).strip("-_") or "storybook"
        return Response(pdf, media_type="application/pdf", headers={
            **_PRIVATE, "Content-Disposition": f'attachment; filename="storybuddy-{slug}.pdf"',
        })
    except HTTPException:
        raise
    except Exception as error:
        _log.warning("PDF download failed (%s)", type(error).__name__)
        raise HTTPException(503, "download unavailable, try again", headers=_PRIVATE) from None
    finally:
        if acquired:
            _render_slot.release()
