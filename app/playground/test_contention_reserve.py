"""
test_contention.py

Contention and Deadlock benchmark for the PostgreSQL multi-item inventory reservation engine.

Simulates N concurrent buyers checking out overlapping products.
Product order in carts is randomized per user to trigger potential multi-item deadlocks
if row-locking is non-deterministic.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import List, Union
from uuid import UUID

import faker
import faker_commerce
from sqlalchemy import delete, insert, select

from app.core.database import session_manager
from app.core.logging import configure_logging
from app.core.security.jwt import hash_password
from app.domain.auth import UserBase
from app.dto.cart import AddItemDto
from app.models import Cart, CartItem, CartReservation, Inventory, Product
from app.repositories.cart_repository import CartRepository
from app.repositories.user_repository import UserRepository
from app.services.checkout import CheckoutService

configure_logging()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# A pool of product UUIDs used to create overlapping cart contents across users
PRODUCT_IDS = [
    UUID("05b42ace-71c3-4172-b2d8-9d608cf93da1"),
    UUID("05b42ace-71c3-4172-b2d8-9d608cf93da2"),
    UUID("05b42ace-71c3-4172-b2d8-9d608cf93da3"),
    UUID("05b42ace-71c3-4172-b2d8-9d608cf93da4"),
]
INITIAL_STOCK_PER_PRODUCT = 30


@dataclass
class RunResult:
    num_buyers: int
    attempted: int = 0
    successful: int = 0
    rejected: int = 0
    deadlocks: int = 0
    elapsed: float = 0.0
    invariant_violations: int = 0

    @property
    def throughput(self) -> float:
        return self.attempted / self.elapsed if self.elapsed > 0 else 0.0


def create_user(id_sequence: str, number_sequence: int) -> UserBase:
    return UserBase(
        id=UUID("3cd57e13-93e1-4d54-ac68-a23a541b9" + id_sequence),
        full_name=f"Buyer {number_sequence}",
        email=f"u{number_sequence}@example.com",
        hashed_password=hash_password("123456"),
    )


def _ecommerce_price(as_int: bool = True) -> Union[int, float]:
    n = random.randint(100, 1000)
    return round(n, 2) if as_int else n / 100


async def setup_test_environment(number_of_users: int) -> List[UserBase]:
    # await reset_db()
    async with session_manager.session() as session:
        await session.execute(delete(CartItem))
        await session.execute(delete(CartReservation))
        await session.execute(delete(Cart))
        await session.execute(delete(Inventory))
        await session.execute(delete(Product))
        await session.commit()

    async with session_manager.session() as session:
        fake = faker.Faker(providers=[faker_commerce.__name__])

        prods: list[Product] = [
            Product(
                id=prod_id,
                name=fake.ecommerce_name(),
                price_cents=_ecommerce_price(),
                sku=fake.bothify(text="??##-####-?#").upper(),
            ).dict()
            for prod_id in PRODUCT_IDS
        ]
        # 1. Seed Inventory Products with initial stock
        stmt = insert(Product).returning(Product.id)
        await session.execute(stmt, prods)

        for prod_id in PRODUCT_IDS:
            session.add(Inventory(product_id=prod_id, stock=INITIAL_STOCK_PER_PRODUCT))

        # 2. Seed Test Users
        user_repo = UserRepository(session)
        suffix = 478
        users_payload = []
        for i in range(number_of_users):
            users_payload.append(create_user(str(suffix), i + 1))
            suffix += 1
        users = await user_repo.upsert(users_payload, ["id"], commit=False)

        # 3. Seed Carts with overlapping products inserted in RANDOM order
        cart_repo = CartRepository(session)
        for user in users:
            # Pick 2 to 3 random products for each user's cart
            chosen_products = random.sample(PRODUCT_IDS, k=random.randint(2, 3))

            # Intentionally shuffle insertion order to attempt reverse-order locking
            random.shuffle(chosen_products)

            for prod_id in chosen_products:
                await cart_repo.add_item(
                    AddItemDto(product_id=prod_id),
                    user_id=str(user.id),
                )

        await session.commit()
        return users


async def simulate_checkout_for_user(user_id: str, result: RunResult) -> None:
    is_success = False
    is_rejected = False
    is_deadlock = False

    # Introduce subtle jitter so requests arrive concurrently with random phase alignment
    await asyncio.sleep(random.uniform(0.001, 0.05))

    async with session_manager.session() as session:
        checkout_service = CheckoutService(session)
        try:
            await checkout_service.create_cart_reservation(user_id)
            is_success = True
        except Exception as e:
            is_rejected = True
            err_msg = str(e).lower()
            if "deadlock" in err_msg or "40001" in err_msg:
                is_deadlock = True
                logger.error(f"[CheckoutSimulator]: Deadlock detected for user {user_id}: {e}")
            else:
                logger.debug(f"[CheckoutSimulator]: Checkout rejected for user {user_id}: {e}")

    result.attempted += 1
    if is_success:
        result.successful += 1
    if is_rejected:
        result.rejected += 1
    if is_deadlock:
        result.deadlocks += 1


async def verify_inventory_invariants(result: RunResult) -> None:
    """Post-run invariant check: stock must never drop below 0."""
    async with session_manager.session() as session:
        stmt = select(Inventory)
        records = (await session.scalars(stmt)).all()
        for inv in records:
            if inv.stock < 0:
                result.invariant_violations += 1
                logger.error(f"[INVARIANT VIOLATION]: Product {inv.product_id} has negative stock: {inv.stock}")


async def run_contention_test(num_buyers: int = 50) -> RunResult:
    buyers = await setup_test_environment(num_buyers)
    result = RunResult(num_buyers=num_buyers)

    print(f"\nAttempting {len(buyers)} concurrent multi-item checkouts against overlapping inventory...")
    start_time = time.perf_counter()

    tasks = [simulate_checkout_for_user(str(u.id), result) for u in buyers]
    await asyncio.gather(*tasks)

    result.elapsed = time.perf_counter() - start_time

    await verify_inventory_invariants(result)

    print("\n================ BENCHMARK RESULTS ================")
    print(f"Buyers:                 {result.num_buyers}")
    print(f"Total Checkouts:        {result.attempted}")
    print(f"Successful Checkouts:   {result.successful}")
    print(f"Rejected / Out of Stock:{result.rejected - result.deadlocks}")
    print(f"Deadlocks Detected:     {result.deadlocks}")
    print(f"Invariant Violations:   {result.invariant_violations}")
    print(f"Elapsed Time:           {result.elapsed:.3f} seconds")
    print(f"Throughput:             {result.throughput:.1f} req/sec")
    print("====================================================\n")

    return result


async def main() -> None:
    # Run high-concurrency contention test
    res = await run_contention_test(num_buyers=50)

    if res.deadlocks > 0:
        print(f"FAILED: {res.deadlocks} deadlocks occurred during high contention!")
    elif res.invariant_violations > 0:
        print(f"FAILED: {res.invariant_violations} inventory invariant violations detected!")
    else:
        print("SUCCESS: 0 deadlocks and 0 invariant violations under high contention!")


if __name__ == "__main__":
    asyncio.run(main())
