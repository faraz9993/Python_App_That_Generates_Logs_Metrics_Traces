from collections.abc import Iterable
from threading import RLock

from fastapi import HTTPException, status

from app.models.customer import Customer, CustomerCreate
from app.models.order import Order, OrderCreate, OrderItem, OrderStatus
from app.models.product import Product, ProductCreate


class InMemoryStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._customers: dict[int, Customer] = {
            1: Customer(id=1, name="Ada Lovelace", email="ada@example.com", tier="enterprise"),
            2: Customer(id=2, name="Grace Hopper", email="grace@example.com", tier="premium"),
            3: Customer(id=3, name="Katherine Johnson", email="katherine@example.com"),
        }
        self._products: dict[int, Product] = {
            1: Product(id=1, sku="OBS-001", name="Trace Explorer", price=49.0, inventory=50),
            2: Product(id=2, sku="OBS-002", name="Metric Beacon", price=29.0, inventory=120),
            3: Product(id=3, sku="OBS-003", name="Log Compass", price=19.0, inventory=250),
        }
        self._orders: dict[int, Order] = {
            1: Order(
                id=1,
                customer_id=1,
                items=[OrderItem(product_id=1, quantity=1), OrderItem(product_id=3, quantity=2)],
                total=87.0,
                status=OrderStatus.paid,
            )
        }
        self._customer_id = max(self._customers)
        self._product_id = max(self._products)
        self._order_id = max(self._orders)

    def list_customers(self) -> list[Customer]:
        with self._lock:
            return list(self._customers.values())

    def get_customer(self, customer_id: int) -> Customer:
        with self._lock:
            customer = self._customers.get(customer_id)
        if not customer:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "customer not found")
        return customer

    def create_customer(self, payload: CustomerCreate) -> Customer:
        with self._lock:
            self._customer_id += 1
            customer = Customer(id=self._customer_id, **payload.model_dump())
            self._customers[customer.id] = customer
            return customer

    def update_customer(self, customer_id: int, payload: CustomerCreate) -> Customer:
        with self._lock:
            if customer_id not in self._customers:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "customer not found")
            customer = Customer(id=customer_id, **payload.model_dump())
            self._customers[customer_id] = customer
            return customer

    def delete_customer(self, customer_id: int) -> None:
        with self._lock:
            if self._customers.pop(customer_id, None) is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "customer not found")

    def list_products(self) -> list[Product]:
        with self._lock:
            return list(self._products.values())

    def get_product(self, product_id: int) -> Product:
        with self._lock:
            product = self._products.get(product_id)
        if not product:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
        return product

    def create_product(self, payload: ProductCreate) -> Product:
        with self._lock:
            self._product_id += 1
            product = Product(id=self._product_id, **payload.model_dump())
            self._products[product.id] = product
            return product

    def update_product(self, product_id: int, payload: ProductCreate) -> Product:
        with self._lock:
            if product_id not in self._products:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
            product = Product(id=product_id, **payload.model_dump())
            self._products[product_id] = product
            return product

    def delete_product(self, product_id: int) -> None:
        with self._lock:
            if self._products.pop(product_id, None) is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")

    def list_orders(self) -> list[Order]:
        with self._lock:
            return list(self._orders.values())

    def get_order(self, order_id: int) -> Order:
        with self._lock:
            order = self._orders.get(order_id)
        if not order:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
        return order

    def create_order(self, payload: OrderCreate) -> Order:
        with self._lock:
            if payload.customer_id not in self._customers:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "customer does not exist")
            total = self._reserve_products(payload.items)
            self._order_id += 1
            order = Order(
                id=self._order_id,
                customer_id=payload.customer_id,
                items=payload.items,
                total=total,
            )
            self._orders[order.id] = order
            return order

    def update_order_status(self, order_id: int, status_value: OrderStatus) -> Order:
        with self._lock:
            if order_id not in self._orders:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
            order = self._orders[order_id].model_copy(update={"status": status_value})
            self._orders[order_id] = order
            return order

    def delete_order(self, order_id: int) -> None:
        with self._lock:
            if self._orders.pop(order_id, None) is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")

    def _reserve_products(self, items: Iterable[OrderItem]) -> float:
        total = 0.0
        for item in items:
            product = self._products.get(item.product_id)
            if not product:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "product does not exist")
            if product.inventory < item.quantity:
                raise HTTPException(status.HTTP_409_CONFLICT, "insufficient inventory")
            total += product.price * item.quantity

        for item in items:
            product = self._products[item.product_id]
            self._products[item.product_id] = product.model_copy(
                update={"inventory": product.inventory - item.quantity}
            )
        return round(total, 2)


store = InMemoryStore()

