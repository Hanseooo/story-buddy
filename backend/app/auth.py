from fastapi import APIRouter, Depends, Header, HTTPException, Path

from app.db import get_supabase_client


async def get_current_user(authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing token")
    jwt = authorization.removeprefix("Bearer ")
    result = get_supabase_client().auth.get_user(jwt)
    if not result.user:
        raise HTTPException(401, "invalid token")
    return result.user


def require_teacher(user=Depends(get_current_user)) -> dict:
    rows = (get_supabase_client().table("profiles")
            .select("id, role").eq("id", user.id).execute().data)
    if not rows or rows[0]["role"] != "teacher":
        raise HTTPException(403, "teachers only")
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
        .select("id, status, failure_reason, approved_at, rejected_at, classroom_id, profile_id")
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
