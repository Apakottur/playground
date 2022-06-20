import asyncio

from sqlalchemy import Column, Integer, String, insert, sql
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

_HOST = "localhost"
_PORT = 2345
_USERNAME = "inch"
_PASSWORD = "inch"
_DB_NAME = "sqla_test"
_META_DB_NAME = "postgres"

_DB_STRING = f"postgresql+asyncpg://{_USERNAME}:{_PASSWORD}@{_HOST}:{_PORT}/{_DB_NAME}"
_META_DB_STRING = f"postgresql+asyncpg://{_USERNAME}:{_PASSWORD}@{_HOST}:{_PORT}/{_META_DB_NAME}"

engine = create_async_engine(_DB_STRING)
meta_engine = create_async_engine(_META_DB_STRING, isolation_level="AUTOCOMMIT")

base = declarative_base()


class Actor(base):
    __tablename__ = "actor"

    id = Column(Integer, primary_key=True)
    name = Column(String)


async def _recreate_db():
    async with meta_engine.connect() as conn:
        await conn.execute(sql.text(f"DROP DATABASE IF EXISTS {_DB_NAME}"))
        await conn.execute(sql.text(f"CREATE DATABASE {_DB_NAME}"))

    async with engine.connect() as conn:
        await conn.run_sync(base.metadata.create_all)
        await conn.commit()


async def _run():
    await _recreate_db()

    session = sessionmaker(engine, class_=AsyncSession)()

    # Working syntax.
    result = await session.execute(
        insert(Actor)
        .values(
            [
                {"id": 1, "name": "first"},
                {"id": 2, "name": "second"},
            ]
        )
        .returning(Actor.id),
    )
    assert result.scalars().all() == [1, 2]

    # Broken syntax.
    result = await session.execute(
        insert(Actor).returning(Actor.id),
        [
            {"id": 3, "name": "first"},
            {"id": 4, "name": "second"},
        ],
    )
    assert result.scalars().all() == [3, 4]  # Fails!


def main():
    asyncio.run(_run())


if __name__ == "__main__":
    main()
