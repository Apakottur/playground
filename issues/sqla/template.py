import asyncio
from typing import override

import sqlalchemy.orm.decl_api
import sqlalchemy.orm.decl_base
import sqlalchemy.orm.loading
import sqlalchemy.orm.properties
import sqlalchemy.sql.sqltypes
from sqlalchemy import BigInteger, func, insert, select, sql
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_HOST = "localhost"
_PORT = 2345
_USERNAME = ""
_PASSWORD = ""
_DB_NAME = "sqla_test"
_META_DB_NAME = "postgres"

_DB_STRING = f"postgresql+asyncpg://{_USERNAME}:{_PASSWORD}@{_HOST}:{_PORT}/{_DB_NAME}"
_META_DB_STRING = f"postgresql+asyncpg://{_USERNAME}:{_PASSWORD}@{_HOST}:{_PORT}/{_META_DB_NAME}"

engine = create_async_engine(_DB_STRING)
meta_engine = create_async_engine(_META_DB_STRING, isolation_level="AUTOCOMMIT")


class BigInt(int):
    # Proprietary type with some custom logic.
    pass


class DbBase(DeclarativeBase):
    pass


class _BigIntIdColumn(sqlalchemy.types.TypeDecorator[BigInt]):
    impl = BigInteger

    cache_ok = True

    @property
    def python_type(self) -> type[BigInt]:
        return BigInt

    @override
    def process_result_value(self, value: int | None, dialect: Dialect) -> BigInt | None:
        if value is None:
            return None
        else:
            return BigInt(value)


class Actor(DbBase):
    __tablename__ = "actor"

    id: Mapped[BigInt] = mapped_column(_BigIntIdColumn, primary_key=True)


async def _recreate_db():
    async with meta_engine.connect() as conn:
        await conn.execute(sql.text(f"DROP DATABASE IF EXISTS {_DB_NAME}"))
        await conn.execute(sql.text(f"CREATE DATABASE {_DB_NAME}"))

    async with engine.connect() as conn:
        await conn.run_sync(DbBase.metadata.create_all)
        await conn.commit()


async def _run():
    await _recreate_db()

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        b = BigInt(195471636076429315)

        # Works.
        result = await session.execute(
            insert(Actor)
            .values(
                [
                    {"id": b},
                ]
            )
            .returning(Actor.id),
        )
        assert result.scalars().all() == [b]

        # Works.
        result = await session.execute(select(Actor.id).where(Actor.id == b))
        assert result.scalars().all() == [b]

        # Doesn't work.
        result = await session.execute(select(Actor.id).where(Actor.id == func.least(b, b)))
        assert result.scalars().all() == [b]


if __name__ == "__main__":
    asyncio.run(_run())
