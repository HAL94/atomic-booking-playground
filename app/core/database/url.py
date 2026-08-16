from sqlalchemy import URL

from app.core.config import settings

DATABASE_URL = URL.create(
    drivername="postgresql+asyncpg",
    username=settings.DB_USER,
    password=settings.DB_PW,
    host=settings.DB_SERVER,
    database=settings.DB_NAME,
    port=settings.DB_PORT,
)
