from pydantic import BaseModel, EmailStr


class Customer(BaseModel):
    id: int
    name: str
    email: EmailStr
    tier: str = "standard"


class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    tier: str = "standard"

