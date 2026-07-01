from pydantic import BaseModel, Field


class Product(BaseModel):
    id: int
    sku: str
    name: str
    price: float = Field(gt=0)
    inventory: int = Field(ge=0)


class ProductCreate(BaseModel):
    sku: str
    name: str
    price: float = Field(gt=0)
    inventory: int = Field(ge=0)

