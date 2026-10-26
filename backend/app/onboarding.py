"""Caller-owned password changes and minimal onboarding state."""
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from postgrest.exceptions import APIError
from pydantic import BaseModel, SecretStr, field_validator

from app import db
from app.auth import get_current_user
from app.config import MIN_PASSWORD_CHARACTERS, MAX_PASSWORD_BYTES

onboarding_router = APIRouter()


def _profile(user_id):
    rows = (db.get_supabase_client().table("profiles")
            .select("id, role, classroom_id, removed_at, display_nickname, password_reset_version, "
                    "password_completed_version, introduction_dismissed_at")
            .eq("id", user_id).execute().data)
    if not rows:
        raise HTTPException(403, "account_unavailable")
    profile = rows[0]
    if profile.get("role") not in ("student", "teacher", "researcher"):
        raise HTTPException(403, "account_unavailable")
    reset, completed = profile.get("password_reset_version"), profile.get("password_completed_version")
    if (type(reset) is not int or type(completed) is not int or not 0 <= completed <= reset):
        raise HTTPException(503, "onboarding_unavailable")
    if profile.get("removed_at") or (profile["role"] == "student" and not profile.get("classroom_id")):
        raise HTTPException(403, "account_unavailable")
    return profile


def _state(profile):
    required = profile["password_completed_version"] < profile["password_reset_version"]
    introduction = (profile["role"] == "student" and not required
                    and profile["password_completed_version"] > 0 and not profile["introduction_dismissed_at"])
    root = f'/s/{profile["id"]}'
    next_path = root + "/change-password" if required else root + "/introduction" if introduction else root
    if profile["role"] != "student":
        next_path = "/settings"
    return {"profile_id": profile["id"], "display_nickname": profile.get("display_nickname"),
            "password_change_required": required, "introduction_required": introduction, "next_path": next_path}


@onboarding_router.get("/me/onboarding")
def onboarding_state(response: Response, user=Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return _state(_profile(user.id))


class PasswordChange(BaseModel):
    current_password: SecretStr
    password: SecretStr
    confirmation: SecretStr

    @field_validator("password")
    @classmethod
    def acceptable_password(cls, value):
        password = value.get_secret_value()
        if len(password) < MIN_PASSWORD_CHARACTERS:
            raise ValueError(f"Use at least {MIN_PASSWORD_CHARACTERS} characters. Spaces are okay.")
        try:
            size = len(password.encode("utf-8"))
        except UnicodeEncodeError:
            raise ValueError("Choose a different password.") from None
        if size > MAX_PASSWORD_BYTES:
            raise ValueError("Use fewer characters, including fewer emoji.")
        return value


@onboarding_router.post("/me/password")
def change_password(payload: PasswordChange, response: Response, authorization: str | None = Header(None), user=Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    current = payload.current_password.get_secret_value()
    password = payload.password.get_secret_value()
    if not current:
        raise HTTPException(422, "current_password_required")
    if password != payload.confirmation.get_secret_value():
        raise HTTPException(422, "password_confirmation_mismatch")
    if password == current:
        raise HTTPException(422, "same_password")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "session_required")
    _profile(user.id)
    if not user.email:
        raise HTTPException(403, "account_unavailable")
    try:
        operation = db.get_supabase_client().rpc("begin_password_operation", {
            "p_user_id": str(user.id), "p_kind": "change",
        }).execute().data
        if not isinstance(operation, str) or not operation:
            raise HTTPException(503, "password_unavailable")
        error = db.change_auth_password(user.id, user.email, current, password, authorization, operation)
    except httpx.HTTPError:
        raise HTTPException(503, "password_outcome_unknown") from None
    except APIError:
        raise HTTPException(503, "password_unavailable") from None
    if error == "password_outcome_unknown":
        raise HTTPException(503, error)
    if error:
        safe ={"current_password_mismatch", "current_password_required", "same_password", "weak_password",
                "password_rate_limited", "reauthentication_needed"}
        raise HTTPException(429 if error == "password_rate_limited" else 400,
                            error if error in safe else "password_unavailable")
    state = _state(_profile(user.id))
    return {**state, "password_changed": True}
