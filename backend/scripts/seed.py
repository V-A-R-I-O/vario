import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Engine and sessionmaker
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def seed_hr_data(session: AsyncSession):
    """Placeholder for HR role-pack seed data (slice-03)."""
    logger.info("Seeding HR role-pack data...")
    # TODO: Add HR intents, phrases, templates
    pass

async def seed_it_data(session: AsyncSession):
    """Placeholder for IT role-pack seed data (slice-04)."""
    logger.info("Seeding IT role-pack data...")
    # TODO: Add IT intents, phrases, templates
    pass

async def seed_admissions_data(session: AsyncSession):
    """Placeholder for Admissions role-pack seed data (slice-05)."""
    logger.info("Seeding Admissions role-pack data...")
    # TODO: Add Admissions intents, phrases, templates
    pass

async def main():
    logger.info(f"Connecting to database at {settings.DATABASE_URL}")
    async with AsyncSessionLocal() as session:
        # Run role-pack seeders
        await seed_hr_data(session)
        await seed_it_data(session)
        await seed_admissions_data(session)
        
        await session.commit()
    logger.info("Database seeding complete.")

if __name__ == "__main__":
    asyncio.run(main())
