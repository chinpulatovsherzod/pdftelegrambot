from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, func
from datetime import datetime
from config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="ru")
    docs_used: Mapped[int] = mapped_column(Integer, default=0)
    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    subscribed_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_or_create_user(telegram_id: int, username: str = None) -> User:
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=telegram_id, username=username)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


async def increment_docs_used(telegram_id: int):
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.docs_used += 1
            await session.commit()


async def set_subscribed(telegram_id: int, until: datetime):
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.is_subscribed = True
            user.subscribed_until = until
            await session.commit()


async def can_generate(telegram_id: int) -> bool:
    from config import FREE_DOCS_LIMIT, ADMIN_IDS
    if telegram_id in ADMIN_IDS:
        return True

    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return True
        if user.is_subscribed:
            if user.subscribed_until and user.subscribed_until > datetime.now():
                return True
            else:
                user.is_subscribed = False
                await session.commit()
        return user.docs_used < FREE_DOCS_LIMIT