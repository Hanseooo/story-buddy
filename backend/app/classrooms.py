import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from app.auth import owned_classroom, require_teacher, teacher_router
from app.db import get_supabase_client
from app.nickname import normalize_nickname
from app.wordlist import mint_password

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _mint_unique_code(supabase) -> str:
    for _ in range(10):
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
        rows = (
            supabase.table("classrooms")
            .select("id")
            .eq("code", code)
            .execute()
            .data
        )
        if not rows:
            return code
    raise HTTPException(500, "could not mint a unique classroom code")


# ── classroom CRUD ────────────────────────────────────────────────────────────

class CreateClassroomRequest(BaseModel):
    name: str


@teacher_router.post("/classrooms", status_code=201)
def create_classroom(
    payload: CreateClassroomRequest,
    teacher=Depends(require_teacher),
):
    supabase = get_supabase_client()
    code = _mint_unique_code(supabase)
    result = (
        supabase.table("classrooms")
        .insert({"name": payload.name, "owner_id": teacher["id"], "code": code})
        .execute()
    )
    return result.data[0]


class RenameClassroomRequest(BaseModel):
    name: str


@teacher_router.patch("/classrooms/{classroom_id}")
def rename_classroom(
    payload: RenameClassroomRequest,
    classroom=Depends(owned_classroom),
):
    supabase = get_supabase_client()
    result = (
        supabase.table("classrooms")
        .update({"name": payload.name})
        .eq("id", classroom["id"])
        .execute()
    )
    return result.data[0]


@teacher_router.delete("/classrooms/{classroom_id}", status_code=204)
def delete_classroom(classroom=Depends(owned_classroom)):
    get_supabase_client().table("classrooms").delete().eq("id", classroom["id"]).execute()


# ── student provisioning ──────────────────────────────────────────────────────

class _StudentIn(BaseModel):
    display_nickname: str
    nickname: str  # client-sent; ignored — server re-derives from display_nickname


class AddStudentsRequest(BaseModel):
    students: list[_StudentIn]


def _create_one(supabase, classroom_id: str, code: str, student_in: _StudentIn) -> dict:
    display = student_in.display_nickname.strip()
    try:
        nickname = normalize_nickname(display)
    except ValueError as exc:
        return {"rejected": True, "display_nickname": display, "reason": str(exc)}

    password = mint_password()
    email = f"{nickname}@{code}.students.storybuddy.invalid"
    try:
        result = supabase.auth.admin.create_user(
            {
                "email": email,
                "password": password,
                "app_metadata": {
                    "role": "student",
                    "classroom_id": classroom_id,
                    "nickname": nickname,
                    "display_nickname": display,
                },
                "email_confirm": True,
            }
        )
        if not result.user:
            return {"rejected": True, "display_nickname": display, "reason": "creation failed"}
        return {
            "rejected": False,
            "profile_id": result.user.id,
            "display_nickname": display,
            "nickname": nickname,
            "password": password,
        }
    except Exception as exc:
        msg = str(exc).lower()
        reason = "nickname already taken" if "duplicate" in msg or "unique" in msg else "creation failed"
        return {"rejected": True, "display_nickname": display, "reason": reason}


@teacher_router.post("/classrooms/{classroom_id}/students")
def add_students(
    payload: AddStudentsRequest,
    classroom=Depends(owned_classroom),
):
    if len(payload.students) > 60:
        raise HTTPException(422, "at most 60 students per request")

    supabase = get_supabase_client()
    classroom_id = classroom["id"]
    code = classroom["code"]

    # ponytail: 5 concurrent creates keeps a 40-name class under ~3s. Upgrade path
    # is a streamed response if the cap ever exceeds 60.
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(
            pool.map(lambda s: _create_one(supabase, classroom_id, code, s), payload.students)
        )

    return {
        "created": [r for r in results if not r["rejected"]],
        "rejected": [r for r in results if r["rejected"]],
    }


def _get_student(supabase, profile_id: str, classroom_id: str) -> dict:
    rows = (
        supabase.table("profiles")
        .select("id, nickname, display_nickname")
        .eq("id", profile_id)
        .eq("classroom_id", classroom_id)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(404, "student not found")
    return rows[0]


@teacher_router.post("/classrooms/{classroom_id}/students/{profile_id}/reset")
def reset_student(
    profile_id: str,
    classroom=Depends(owned_classroom),
):
    supabase = get_supabase_client()
    profile = _get_student(supabase, profile_id, classroom["id"])
    password = mint_password()
    supabase.auth.admin.update_user_by_id(profile_id, {"password": password})
    return {
        "profile_id": profile_id,
        "display_nickname": profile["display_nickname"],
        "nickname": profile["nickname"],
        "password": password,
    }


@teacher_router.post("/classrooms/{classroom_id}/students/{profile_id}/remove", status_code=204)
def remove_student(
    profile_id: str,
    classroom=Depends(owned_classroom),
):
    supabase = get_supabase_client()
    _get_student(supabase, profile_id, classroom["id"])  # 404 guard
    # Both halves are required and neither is sufficient alone (spec invariant 4).
    supabase.table("profiles").update(
        {"removed_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", profile_id).execute()
    supabase.auth.admin.update_user_by_id(profile_id, {"ban_duration": "876000h"})


@teacher_router.post("/classrooms/{classroom_id}/students/{profile_id}/restore")
def restore_student(
    profile_id: str,
    classroom=Depends(owned_classroom),
):
    supabase = get_supabase_client()
    profile = _get_student(supabase, profile_id, classroom["id"])
    password = mint_password()
    supabase.table("profiles").update({"removed_at": None}).eq("id", profile_id).execute()
    supabase.auth.admin.update_user_by_id(
        profile_id, {"ban_duration": "none", "password": password}
    )
    return {
        "profile_id": profile_id,
        "display_nickname": profile["display_nickname"],
        "nickname": profile["nickname"],
        "password": password,
    }
