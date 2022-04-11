import asyncio

from sqlalchemy import Integer, insert, sql, BigInteger, select, tuple_, func
from sqlalchemy import Column, String
from sqlalchemy.event import listens_for
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    sessionmaker,
    declarative_mixin,
    declared_attr,
    Session,
    ORMExecuteState,
    with_loader_criteria,
)

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


@declarative_mixin
class HasNumber:
    @declared_attr
    def number(self):
        return Column(BigInteger)


class Actor(base, HasNumber):
    __tablename__ = "actor"

    id = Column(BigInteger, primary_key=True)


big_int = 2**31 + 123


@listens_for(Session, "do_orm_execute")
def _do_orm_execute(orm_execute_state: ORMExecuteState) -> None:
    if orm_execute_state.is_select:
        if orm_execute_state.is_column_load or orm_execute_state.is_relationship_load:
            return

        # This breaks the query:
        orm_execute_state.statement = orm_execute_state.statement.options(
            with_loader_criteria(HasNumber, lambda cls: cls.number == 2**31 + 123, include_aliases=True)
        )

        # This is a hack around it that works:
        orm_execute_state.statement = orm_execute_state.statement.options(
            *(
                with_loader_criteria(
                    subclass,
                    subclass.number == big_int,
                    include_aliases=True,
                )
                for subclass in HasNumber.__subclasses__()
            )
        )


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

    session.add(Actor(id=big_int, number=big_int))
    await session.commit()

    s = select(Actor.id).where(Actor.id == big_int)
    result = await session.execute(s)
    assert result.scalars().all() == [big_int]

    await session.commit()


def main():
    asyncio.run(_run())


if __name__ == "__main__":
    main()
