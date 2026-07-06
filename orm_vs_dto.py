import asyncio
import time
from uuid import uuid4, UUID
import msgspec
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# --- Setup msgspec DTO ---
# This is exactly how your production DTO operates at C-speed
class UserAuthDTO(msgspec.Struct):
    id: UUID
    phone_number: str
    user_type: str

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

# --- Method A: Core + msgspec DTO (Your Exact Production Flow) ---
async def fetch_core(session, target_id):
    stmt = select(User.__table__).where(User.__table__.c.id == target_id)
    result = await session.execute(stmt)
    row = result.mappings().one_or_none()
    if not row:
        return None
    # Pull raw mappings and instantiate the C-based msgspec Struct
    return UserAuthDTO(
        id=row["id"],
        phone_number=row["phone_number"],
        user_type=row["user_type"]
    )

# --- Method B: Standard ORM + msgspec DTO ---
async def fetch_orm(session, target_id):
    stmt = select(User).where(User.id == target_id)
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()
    if not obj:
        return None
   

# --- Method C: ORM (populate_existing) + msgspec DTO ---
async def fetch_with_populate(session, target_id):
    stmt = select(User).where(User.id == target_id)
    result = await session.execute(stmt, execution_options={"populate_existing": True})
    obj = result.scalar_one_or_none()
    if not obj:
        return None
    return UserAuthDTO(
        id=obj.id,
        phone_number=obj.phone_number,
        user_type=obj.user_type
    )

# --- Method D: ORM (no populate) + msgspec DTO ---
async def fetch_without_populate(session, target_id):
    stmt = select(User).where(User.id == target_id)
    result = await session.execute(stmt, execution_options={"populate_existing": False})
    obj = result.scalar_one_or_none()
    if not obj:
        return None
    return UserAuthDTO(
        id=obj.id,
        phone_number=obj.phone_number,
        user_type=obj.user_type
    )


# --- The Benchmark Runner ---
async def run_benchmark(iterations=1000, total_runs=10):
    test_id = await setup_db()
    
    total_time_core = 0.0
    total_time_orm = 0.0
    total_time_populate = 0.0
    total_time_no_populate = 0.0

    # Warmup
    async with async_session() as session:
        await fetch_core(session, test_id)
        await fetch_orm(session, test_id)
        await fetch_with_populate(session, test_id)
        await fetch_without_populate(session, test_id)

    print(f"Starting End-to-End DTO Benchmark: {total_runs} runs of {iterations} iterations...\n")

    for run in range(1, total_runs + 1):
        # 1. Test Core + msgspec
        start_core = time.perf_counter()
        for _ in range(iterations):
            async with async_session() as session:
                await fetch_core(session, test_id)
        total_time_core += (time.perf_counter() - start_core)
        
        # 2. Test ORM + msgspec
        start_orm = time.perf_counter()
        for _ in range(iterations):
            async with async_session() as session:
                await fetch_orm(session, test_id)
        total_time_orm += (time.perf_counter() - start_orm)

        # 3. Test ORM Populate + msgspec
        start_populate = time.perf_counter()
        for _ in range(iterations):
            async with async_session() as session:
                await fetch_with_populate(session, test_id)
        total_time_populate += (time.perf_counter() - start_populate)

        # 4. Test ORM No Populate + msgspec
        start_no_populate = time.perf_counter()
        for _ in range(iterations):
            async with async_session() as session:
                await fetch_without_populate(session, test_id)
        total_time_no_populate += (time.perf_counter() - start_no_populate)
        
        print(f"✔ Run {run}/{total_runs} finalized.")

    avg_core = total_time_core / total_runs
    avg_orm = total_time_orm / total_runs
    avg_populate = total_time_populate / total_runs
    avg_no_populate = total_time_no_populate / total_runs
    
    print("\n" + "="*60)
    print(f"--- FINAL AVERAGED RESULTS WITH MSGSPEC DTO INCLUDED ---")
    print("="*60)
    print(f"Method A: Core + msgspec Struct     : {avg_core:.4f} seconds")
    print(f"Method B: ORM       : {avg_orm:.4f} seconds")
    print(f"Method C: ORM Populate + msgspec    : {avg_populate:.4f} seconds")
    print(f"Method D: ORM No Populate + msgspec : {avg_no_populate:.4f} seconds")
    print("-" * 60)
    print(f"True Production Performance Gain    : {((avg_orm - avg_core) / avg_orm) * 100:.2f}% faster")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
