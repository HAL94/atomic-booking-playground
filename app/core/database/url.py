from sqlalchemy import URL

from app.core.config import settings

DATABASE_URL = URL.create(
    drivername="postgresql+asyncpg",
    username=settings.PG_USER,
    password=settings.PG_PW,
    host=settings.PG_SERVER,
    database=settings.PG_DB,
    port=settings.PG_PORT,
)
