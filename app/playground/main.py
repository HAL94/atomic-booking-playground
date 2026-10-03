import asyncio
import logging
import random
from typing import Union
import uuid
from uuid import UUID

import faker
import faker_commerce
from sqlalchemy import ScalarResult
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import session_manager
from app.core.logging import configure_logging
from app.core.security.jwt import hash_password
from app.domain.auth import UserBase
from app.models import CartItem, Inventory, Product  # noqa: F403
from app.playground.reset_db import reset_db
from app.repositories.user_repository import UserRepository

configure_logging()
logger = logging.getLogger(__name__)
PRODUCT_ID = UUID("4a4a1f75-c61d-4bc4-a92a-8c0d2b75a1e1")


def create_user(id_sequence: str, number_sequence: int):
    id_input = f"3cd57e13-93e1-4d54-ac68-a23a541b9{id_sequence}"
    return UserBase(
        id=id_input,
        full_name=f"Booker {number_sequence}",
        email=f"u{number_sequence}@example.com",
        hashed_password=hash_password("123456"),
    )


async def upsert_users(number_of_users: int = 3) -> list[UserBase]:
    async with session_manager.session() as session:
        user_repo = UserRepository(session)
        SUFFIX = 478
        payload = []
        for i in range(number_of_users):
            payload.append(create_user(str(SUFFIX), i + 1))
            SUFFIX += 1

        index_elements = ["id"]
        return await user_repo.upsert(payload, index_elements, commit=True)

def _ecommerce_price(as_int: bool = True) -> Union[int, float]:
    n = random.randint(100, 1000)
    return round(n, 2) if as_int else n / 100

async def upsert_product() -> list[Product]:
    fake = faker.Faker(providers=[faker_commerce.__name__])

    prod_ids = [
        uuid.UUID("f6d6b0b3-8400-4c38-9970-a1052d2510cf"),
        uuid.UUID("76b99940-5345-4158-aafc-711043c9b014"),
        uuid.UUID("c7f0f509-d8a5-4471-a0fa-7c6855cd11a6"),
        uuid.UUID("b92610f0-6318-4c51-850b-231d4e4e9ef0"),
        uuid.UUID("e7a2c082-35fb-40ed-9af4-32dbbb064f46"),
        uuid.UUID("26686e66-efdc-497a-a711-3c153416847e"),
        uuid.UUID("7e910da6-29de-477b-a1c2-71eabe81f543"),
        uuid.UUID("5b50667f-6296-4dfb-a759-457b7955ccb2"),
        uuid.UUID("6557e588-41c1-491a-ac8b-bee3cedb61b6"),
        uuid.UUID("e1c25f47-f11a-487a-8c9b-5e5dafd02c13"),
    ]
    prods: list[Product] = [
        Product(
            id=prod_id,
            name=fake.ecommerce_name(),
            price_cents=_ecommerce_price(),
            sku=fake.bothify(text="??##-####-?#").upper(),
        ).dict()
        for prod_id in prod_ids
    ]
    async with session_manager.session() as session:
        statement = pg_insert(Product)
        statement = statement.on_conflict_do_update(
            index_elements=[Product.id],
            set_={
                "name": statement.excluded.name,
                "sku": statement.excluded.sku,
                "price_cents": statement.excluded.price_cents,
            },
        ).returning(Product)
        result_scalar: ScalarResult[Product] = await session.scalars(
            statement, prods, execution_options={"populate_existing": True}
        )
        products = result_scalar.all()
        await session.commit()
        return products


async def upsert_inventory(products: list[Product]) -> Inventory:
    async with session_manager.session() as session:
        inventory_ls: list[Inventory] = [
            Inventory(
                product_id=prod.id, stock=random.uniform(10, 1000), reserved_stock=random.uniform(10, 1000)
            ).dict()
            for prod in products
        ]
        statement = pg_insert(Inventory)
        statement = statement.on_conflict_do_update(
            index_elements=[Inventory.product_id],
            set_={
                "stock": statement.excluded.stock,
                "reserved_stock": statement.excluded.reserved_stock,
            },
        ).returning(Inventory)
        inventory = await session.scalars(statement, inventory_ls)
        await session.commit()
        return inventory


async def upsert_customer_cart(user_id: UUID, products: list[Product]) -> list[CartItem]:
    """
    Upsert cart items for a customer
    """
    user_cart = random.sample(products, random.randint(2, len(products)))

    customer_cart: list[CartItem] = [
        CartItem(
            id=uuid.uuid4(),
            product_id=prod.id,
            customer_id=user_id,
            quantity=random.uniform(1, 10),
            unit_price_cents=random.uniform(100, 10000),
        ).dict()
        for prod in user_cart
    ]

    async with session_manager.session() as session:
        stmt = pg_insert(CartItem)
        stmt = stmt.returning(CartItem)

        cart_items = await session.scalars(stmt, customer_cart)
        await session.commit()
        logger.info(f"[CustomerCart]: created customer cart for {user_id} with {len(customer_cart)} items")
        return cart_items


async def main_pg():
    await reset_db()
    await upsert_users()
    products = await upsert_product()
    await upsert_inventory(products)

    # for customer in customers:
    #     await upsert_customer_cart(user_id=customer.id, products=products)

    logger.info("[Seeder]: finished..")


if __name__ == "__main__":
    asyncio.run(main_pg())
