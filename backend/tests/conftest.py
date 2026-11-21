import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
os.environ.setdefault("FAL_KEY", "test-fal-key")
# Both features ship on by default (2026-11-21). Tests run baseline unless they opt in with monkeypatch.
os.environ.setdefault("ENABLE_TEACHER_MODERATION_REVIEW", "false")
os.environ.setdefault("ENABLE_MAGIC_PENCIL", "false")
