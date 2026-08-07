-- 0010_profiles_removed_at.sql
-- spec: docs/specs/teacher-provisioning-and-shell.md §7
-- Adds the removed_at column used by removal and restore flows.
-- ADR-gated: do not apply until ADR is accepted.

alter table profiles add column removed_at timestamptz;
