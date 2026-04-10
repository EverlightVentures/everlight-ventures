"""Onyx POS -- Pydantic models"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


# === Auth ===
class LoginRequest(BaseModel):
    email: str
    password: str

class PinLoginRequest(BaseModel):
    tenant_id: str
    pin: str

class SignupRequest(BaseModel):
    email: str
    password: str
    business_name: str
    full_name: str
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    tax_rate: float = 0.0825


# === Employees ===
class EmployeeCreate(BaseModel):
    full_name: str
    role: str = "employee"
    pin: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact: Optional[str] = None
    hourly_rate: Optional[float] = None

class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    pin: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    hourly_rate: Optional[float] = None


# === Products ===
class ProductCreate(BaseModel):
    name: str
    category_id: Optional[str] = None
    description: Optional[str] = None
    unit_price: float = 0.00
    sku: Optional[str] = None
    stock_quantity: Optional[int] = None
    reorder_point: int = 5

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    unit_price: Optional[float] = None
    stock_quantity: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


# === Categories ===
class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None
    sort_order: int = 0


# === Sales ===
class LineItemCreate(BaseModel):
    product_id: Optional[str] = None
    product_name: str
    category_name: Optional[str] = None
    quantity: int = 1
    unit_price: float

class SaleCreate(BaseModel):
    employee_id: str
    items: list[LineItemCreate]
    payment_method: str = "cash"
    amount_received: Optional[float] = None
    notes: Optional[str] = None


# === Time Clock ===
class PunchCreate(BaseModel):
    employee_id: str
    punch_type: str  # clock_in, clock_out, break_start, break_end, lunch_start, lunch_end

class TimeOffRequest(BaseModel):
    employee_id: str
    start_date: date
    end_date: date
    reason: Optional[str] = None


# === AI Chat ===
class ChatMessage(BaseModel):
    message: str
    employee_id: Optional[str] = None
