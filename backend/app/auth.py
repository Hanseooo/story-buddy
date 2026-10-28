from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request

from app.db import get_supabase_client


async def get_current_user(request: Request, authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing token")
    jwt = authorization.removeprefix("Bearer ")
    try:
        result = get_supabase_client().auth.get_user(jwt)
        if not result.user:
            raise HTTPException(401, "invalid token")
    except Exception:
        raise HTTPException(401, "invalid token") from None
    if request.url.path not in ("/me/password", "/me/onboarding"):
        rows = (get_supabase_client().table("profiles")
                .select("role, classroom_id, removed_at, password_reset_version, password_completed_version")
                .eq("id", result.user.id).execute().data)
        if not rows:
            raise HTTPException(403, "account_unavailable")
        profile = rows[0]
        if profile.get("role") not in ("student", "teacher", "researcher"):
            raise HTTPException(403, "account_unavailable")
        if profile.get("role") == "student":
            reset, completed = profile.get("password_reset_version"), profile.get("password_completed_version")
            if type(reset) is not int or type(completed) is not int or not 0 <= completed <= reset:
                raise HTTPException(503, "onboarding_unavailable")
            if profile.get("removed_at") or not profile.get("classroom_id"):
                raise HTTPException(403, "account_unavailable")
            if completed < reset:
                raise HTTPException(403, "password_change_required")
    return result.user


def require_teacher(user=Depends(get_current_user)) -> dict:
    rows = (get_supabase_client().table("profiles")
            .select("id, role").eq("id", user.id).execute().data)
    if not rows or rows[0]["role"] != "teacher":
        raise HTTPException(403, "teachers only")
    return rows[0]


def require_researcher(user=Depends(get_current_user)) -> dict:
    rows = (get_supabase_client().table("profiles")
            .select("id, role, is_adjudicator").eq("id", user.id).execute().data)
    if not rows or rows[0]["role"] != "researcher":
        raise HTTPException(403, "researchers_only")
    return rows[0]


def owned_classroom(classroom_id: str = Path(...), teacher=Depends(require_teacher)) -> dict:
    rows = (get_supabase_client().table("classrooms").select("*")
            .eq("id", classroom_id).eq("owner_id", teacher["id"]).execute().data)
    if not rows:
        raise HTTPException(404, "classroom not found")
    return rows[0]


def owned_job(job_id: str = Path(...), teacher=Depends(require_teacher)) -> dict:
    rows = (
        get_supabase_client().table("jobs")
        .select("id, status, failure_reason, approved_at, rejected_at, classroom_id, profile_id, moderation_mode")
        .eq("id", job_id)
        .execute().data
    )
    if not rows:
        raise HTTPException(404, "not found")
    job = rows[0]
    cls_rows = (
        get_supabase_client().table("classrooms")
        .select("id")
        .eq("id", job["classroom_id"])
        .eq("owner_id", teacher["id"])
        .execute().data
    )
    if not cls_rows:
        raise HTTPException(404, "not found")
    return job


# ponytail: no routes — S2 and S3 own endpoint paths. The router check is structural
# so a new endpoint inherits require_teacher by existing, not by remembering.
teacher_router = APIRouter(dependencies=[Depends(require_teacher)])
