from fastapi import APIRouter, Query, Response, status

from app.config import get_settings
from app.models.customer import Customer, CustomerCreate
from app.models.order import Order, OrderCreate, OrderStatus
from app.models.product import Product, ProductCreate
from app.observability.logging import get_logger
from app.observability.metrics import (
    CUSTOMERS_RETRIEVED_TOTAL,
    ORDERS_CREATED_TOTAL,
    PRODUCTS_RETRIEVED_TOTAL,
    inc_counter,
)
from app.observability.tracing import get_tracer
from app.services.store import store

router = APIRouter(prefix="/api", tags=["business"])
settings = get_settings()
tracer = get_tracer(__name__)
logger = get_logger("business")


@router.get("/customers", response_model=list[Customer])
async def list_customers() -> list[Customer]:
    with tracer.start_as_current_span("customers.list"):
        inc_counter(CUSTOMERS_RETRIEVED_TOTAL.labels(service=settings.service_name))
        return store.list_customers()


@router.get("/customers/{customer_id}", response_model=Customer)
async def get_customer(customer_id: int) -> Customer:
    with tracer.start_as_current_span("customers.get") as span:
        span.set_attribute("customer.id", customer_id)
        inc_counter(CUSTOMERS_RETRIEVED_TOTAL.labels(service=settings.service_name))
        return store.get_customer(customer_id)


@router.post("/customers", response_model=Customer, status_code=status.HTTP_201_CREATED)
async def create_customer(payload: CustomerCreate) -> Customer:
    with tracer.start_as_current_span("customers.create"):
        customer = store.create_customer(payload)
        logger.info("customer created", customer_id=customer.id, tier=customer.tier)
        return customer


@router.put("/customers/{customer_id}", response_model=Customer)
async def update_customer(customer_id: int, payload: CustomerCreate) -> Customer:
    with tracer.start_as_current_span("customers.update") as span:
        span.set_attribute("customer.id", customer_id)
        return store.update_customer(customer_id, payload)


@router.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(customer_id: int) -> Response:
    with tracer.start_as_current_span("customers.delete") as span:
        span.set_attribute("customer.id", customer_id)
        store.delete_customer(customer_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/products", response_model=list[Product])
async def list_products() -> list[Product]:
    with tracer.start_as_current_span("products.list"):
        inc_counter(PRODUCTS_RETRIEVED_TOTAL.labels(service=settings.service_name))
        return store.list_products()


@router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: int) -> Product:
    with tracer.start_as_current_span("products.get") as span:
        span.set_attribute("product.id", product_id)
        inc_counter(PRODUCTS_RETRIEVED_TOTAL.labels(service=settings.service_name))
        return store.get_product(product_id)


@router.post("/products", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate) -> Product:
    with tracer.start_as_current_span("products.create"):
        product = store.create_product(payload)
        logger.info("product created", product_id=product.id, sku=product.sku)
        return product


@router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: int, payload: ProductCreate) -> Product:
    with tracer.start_as_current_span("products.update") as span:
        span.set_attribute("product.id", product_id)
        return store.update_product(product_id, payload)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int) -> Response:
    with tracer.start_as_current_span("products.delete") as span:
        span.set_attribute("product.id", product_id)
        store.delete_product(product_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/orders", response_model=list[Order])
async def list_orders(status_filter: OrderStatus | None = Query(default=None, alias="status")) -> list[Order]:
    with tracer.start_as_current_span("orders.list") as span:
        span.set_attribute("orders.status_filter", status_filter or "")
        orders = store.list_orders()
        if status_filter:
            orders = [order for order in orders if order.status == status_filter]
        return orders


@router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: int) -> Order:
    with tracer.start_as_current_span("orders.get") as span:
        span.set_attribute("order.id", order_id)
        return store.get_order(order_id)


@router.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderCreate) -> Order:
    with tracer.start_as_current_span("orders.create") as span:
        order = store.create_order(payload)
        span.set_attribute("order.id", order.id)
        span.set_attribute("order.total", order.total)
        inc_counter(ORDERS_CREATED_TOTAL.labels(service=settings.service_name))
        logger.info("order created", order_id=order.id, total=order.total)
        return order


@router.patch("/orders/{order_id}/status", response_model=Order)
async def update_order_status(order_id: int, status_value: OrderStatus) -> Order:
    with tracer.start_as_current_span("orders.update_status") as span:
        span.set_attribute("order.id", order_id)
        return store.update_order_status(order_id, status_value)


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(order_id: int) -> Response:
    with tracer.start_as_current_span("orders.delete") as span:
        span.set_attribute("order.id", order_id)
        store.delete_order(order_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
