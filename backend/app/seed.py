import asyncio

from sqlalchemy import select

from app.db.models import Scheme
from app.db.session import async_session_factory

SEED_SCHEMES = (
    ("PRE_MATRIC", "Pre-Matric Scholarship"),
    ("POST_MATRIC", "Post-Matric Scholarship"),
    ("NATIONAL_FELLOWSHIP", "National Fellowship"),
    ("NATIONAL_OVERSEAS", "National Overseas Scholarship"),
)


async def seed_schemes() -> None:
    async with async_session_factory() as session:
        for code, name in SEED_SCHEMES:
            existing = await session.scalar(select(Scheme).where(Scheme.code == code))
            if existing is None:
                session.add(Scheme(code=code, name=name))
        await session.commit()


def main() -> None:
    asyncio.run(seed_schemes())


if __name__ == "__main__":
    main()
