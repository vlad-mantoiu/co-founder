"""Fix stale data: abandon orphan sessions, delete ghost projects."""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        # 1. Show current state
        result = await conn.execute(
            text("SELECT id, status, idea_text, project_id FROM onboarding_sessions ORDER BY created_at")
        )
        rows = result.fetchall()
        print(f"Found {len(rows)} onboarding session(s):")
        for row in rows:
            print(f"  {row[0]} | status={row[1]} | project_id={row[3]} | idea={str(row[2])[:50]}")

        result = await conn.execute(
            text("SELECT id, name, status, clerk_user_id FROM projects ORDER BY created_at")
        )
        projects = result.fetchall()
        print(f"\nFound {len(projects)} project(s):")
        for p in projects:
            print(f"  {p[0]} | name={p[1]} | status={p[2]}")

        # 2. Delete projects that were created from sessions that failed
        # (the old session from before the ThesisSnapshot fix)
        if projects:
            for p in projects:
                await conn.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": p[0]})
                print(f"\n  Deleted project {p[0]}")

        # 3. Clear project_id references from onboarding sessions
        await conn.execute(
            text("UPDATE onboarding_sessions SET project_id = NULL WHERE project_id IS NOT NULL")
        )
        print("Cleared project_id references from sessions.")

        # 4. Abandon all non-completed sessions
        result = await conn.execute(
            text(
                "UPDATE onboarding_sessions SET status = 'abandoned' "
                "WHERE status NOT IN ('completed', 'abandoned') "
                "RETURNING id"
            )
        )
        abandoned = result.fetchall()
        print(f"Abandoned {len(abandoned)} stale session(s).")

    await engine.dispose()
    print("\nALL DONE")


if __name__ == "__main__":
    asyncio.run(main())
