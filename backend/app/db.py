from functools import lru_cache

import httpx
from supabase import Client, create_client

from app.config import settings


@lru_cache
def get_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def change_auth_password(user_id, email, current_password, password, bearer, operation) -> str | None:
    """Transient proof session. Never mutate the shared service-role client's session.

    The native update keeps the caller's session. Its transaction consumes the
    private operation; an exposed metadata receipt has already been consumed.
    Explicit sign-in also checks current proof when the hosted native flag is off.
    """
    base = settings.supabase_url.rstrip("/") + "/auth/v1"
    headers = {"apikey": settings.supabase_service_role_key}
    with httpx.Client(timeout=15) as client:
        proof = client.post(base + "/token?grant_type=password", headers=headers,
                            json={"email": email, "password": current_password})
        if proof.status_code == 429:
            return "password_rate_limited"
        if proof.status_code >= 400:
            return "current_password_mismatch" if proof.status_code == 400 else "password_unavailable"
        data = proof.json()
        proof_token = data.get("access_token")
        try:
            if data.get("user", {}).get("id") != str(user_id) or not proof_token:
                return "current_password_mismatch"
            result = client.put(base + "/user", headers={**headers, "Authorization": bearer}, json={
                "current_password": current_password, "password": password,
                "data": {"storybuddy_password_operation": str(operation)},
            })
            if result.status_code >= 500:
                return "password_outcome_unknown"  # The Auth transaction may have committed.
            if result.status_code >= 400:
                try:
                    return result.json().get("code", "password_unavailable")
                except ValueError:
                    return "password_unavailable"
            return None
        finally:
            if proof_token:
                try:
                    client.post(base + "/logout?scope=local", headers={
                        **headers, "Authorization": "Bearer " + proof_token,
                    })
                except httpx.HTTPError:
                    pass  # Password update may already have revoked this temporary session.
