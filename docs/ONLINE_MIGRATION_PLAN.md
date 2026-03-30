# Online Migration Plan (Foundation)

## Goal
Move from local-only SQLite app to online-capable architecture while keeping current app stable.

## Scope of this branch
- Add online module skeleton.
- Add environment variable template.
- No runtime behavior changes to existing local app.

## Target architecture
- Flet UI (desktop/laptop input).
- Mobile: view-focused usage.
- Backend/service layer in Python.
- Supabase PostgreSQL as central database.

## Planned phases
1. Foundation
- Config loading and Supabase client bootstrap.
- APP_MODE switch (`local` or `online`).

2. Data layer split
- Keep current `db.py` for local mode.
- Add online repository methods for companies and inspections.

3. Auth and session
- Basic login flow for online mode.
- Session handling and secure key usage.

4. UI integration
- Reuse current UI.
- Wire Save/Update/Delete to selected data mode.

5. Stabilization
- Migration script from SQLite to PostgreSQL.
- Backup/restore and error logging checks.
- Pilot rollout and rollback procedure.

## Safety rules
- Never break local mode while online mode is incomplete.
- Release in small PRs.
- Keep clear rollback path for each deployment.
