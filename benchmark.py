import asyncio
import time
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# --- Setup Mock Database ---
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    phone_number = Column(String)
    user_type = Column(String)

engine = create_async_engine("sqlite+aiosqlite:///:memory:")
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    test_id = uuid4()
    async with async_session() as session:
        session.add(User(id=test_id, phone_number="1234567890", user_type="admin"))
        await session.commit()
    return test_id

# --- Method A: Core ---
async def fetch_core(session, target_id):
    stmt = select(User.__table__).where(User.__table__.c.id == target_id)
    result = await session.execute(stmt)
    return result.mappings().one_or_none()

# --- Method B: Standard ORM ---
async def fetch_orm(session, target_id):
    stmt = select(User).where(User.id == target_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

# --- Method C: Include populate_existing=True ---
async def fetch_with_populate(session, target_id):
    stmt = select(User).where(User.id == target_id)
    result = await session.execute(stmt, execution_options={"populate_existing": True})
    return result.scalar_one_or_none()

# --- Method D: Include populate_existing=False ---
async def fetch_without_populate(session, target_id):
    stmt = select(User).where(User.id == target_id)
    result = await session.execute(stmt, execution_options={"populate_existing": False})
    return result.scalar_one_or_none()


# --- The Benchmark Runner ---
async def run_benchmark(iterations=10000, total_runs=10):
    test_id = await setup_db()
    
    # Accumulators for total execution time across all runs
    total_time_core = 0.0
    total_time_orm = 0.0
    total_time_populate = 0.0
    total_time_no_populate = 0.0

    # Warmup (compile queries inside SQLAlchemy once before starting)
    async with async_session() as session:
        await fetch_core(session, test_id)
        await fetch_orm(session, test_id)
        await fetch_with_populate(session, test_id)
        await fetch_without_populate(session, test_id)

    print(f"Starting benchmark: {total_runs} runs of {iterations} iterations each...\n")

    for run in range(1, total_runs + 1):
        # 1. Test Core
        start_core = time.perf_counter()
        for _ in range(iterations):
            async with async_session() as session:
                await fetch_core(session, test_id)
        total_time_core += (time.perf_counter() - start_core)
        
        # 2. Test ORM
        start_orm = time.perf_counter()
        for _ in range(iterations):
            async with async_session() as session:
                await fetch_orm(session, test_id)
        total_time_orm += (time.perf_counter() - start_orm)

        # 3. Test ORM with populate_existing=True
        start_populate = time.perf_counter()
        for _ in range(iterations):
            async with async_session() as session:
                await fetch_with_populate(session, test_id)
        total_time_populate += (time.perf_counter() - start_populate)

        # 4. Test ORM with populate_existing=False
        start_no_populate = time.perf_counter()
        for _ in range(iterations):
            async with async_session() as session:
                await fetch_without_populate(session, test_id)
        total_time_no_populate += (time.perf_counter() - start_no_populate)
        
        print(f"✔ Run {run}/{total_runs} finalized.")

    # Calculate final averages
    avg_core = total_time_core / total_runs
    avg_orm = total_time_orm / total_runs
    avg_populate = total_time_populate / total_runs
    avg_no_populate = total_time_no_populate / total_runs
    
    # --- Print Averaged Results ---
    print("\n" + "="*60)
    print(f"--- FINAL AVERAGED RESULTS OVER {total_runs} RUNS ({iterations} iterations/run) ---")
    print("="*60)
    print(f"Method A: Core (Your Optimization)  : {avg_core:.4f} seconds")
    print(f"Method B: Standard ORM              : {avg_orm:.4f} seconds")
    print(f"Method C: ORM (populate_existing)   : {avg_populate:.4f} seconds")
    print(f"Method D: ORM (no populate override): {avg_no_populate:.4f} seconds")
    print("-" * 60)
    print(f"Core Gain over Standard ORM         : {((avg_orm - avg_core) / avg_orm) * 100:.2f}% faster")
    print(f"Core Gain over Populate Existing    : {((avg_populate - avg_core) / avg_populate) * 100:.2f}% faster")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
