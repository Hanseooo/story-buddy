import re

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_supabase_client

_AVATAR_RE = re.compile(r"^(peeps|pixel|lorelei|thumbs)-\d{2}$")


class AvatarRequest(BaseModel):
    avatar_id: str | None


def patch_avatar(payload: AvatarRequest, user=Depends(get_current_user)) -> dict:
    if payload.avatar_id is not None and not _AVATAR_RE.match(payload.avatar_id):
        raise HTTPException(422, "invalid avatar_id")
    get_supabase_client().table("profiles").update(
        {"avatar_id": payload.avatar_id}
    ).eq("id", user.id).execute()
    return {}
