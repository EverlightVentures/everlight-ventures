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


# === Receipt Scanner ===
class ScanResult(BaseModel):
    vendor: Optional[str] = None
    date: Optional[str] = None
    items: list[dict] = []
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    raw_text: str = ""
    confidence: float = 0.0
    scanned_at: str = ""


# === Vendor Bill Scanner ===
class VendorBillUpdate(BaseModel):
    vendor_name: Optional[str] = None
    expense_category: Optional[str] = None
    due_date: Optional[date] = None
    paid: Optional[bool] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


# === Receipt Lottery ===
class LotteryCheckRequest(BaseModel):
    lottery_code: str

class LotteryRedeemRequest(BaseModel):
    lottery_code: str
    transaction_id: Optional[str] = None


# === Earned Wage Access ===
class WageAdvanceRequest(BaseModel):
    employee_id: str
    advance_amount: float

class WageAdvanceApproval(BaseModel):
    approved: bool
    denial_reason: Optional[str] = None


# === Neighborhood Commerce Network ===
class NetworkJoinRequest(BaseModel):
    latitude: float
    longitude: float
    neighborhood: Optional[str] = None
    city: str
    state: str
    business_type: str
    business_tags: list[str] = []
    promo_discount_pct: float = 10.0
    promo_budget_monthly: float = 50.0


# === Dead Stock Marketplace ===
class DeadStockListing(BaseModel):
    product_id: Optional[str] = None
    product_name: str
    description: Optional[str] = None
    original_price: float
    clearance_price: float
    quantity_available: int = 1
    category: Optional[str] = None
    condition: str = "new"
    days_in_stock: Optional[int] = None

class DeadStockClaim(BaseModel):
    listing_id: str
    quantity: int = 1


# === Customer / Loyalty ===
class CustomerLookup(BaseModel):
    phone: str
    display_name: Optional[str] = None

class PointsAction(BaseModel):
    customer_id: str
    points: int
    reason: str


# === Social Clout ===
class SocialPostCreate(BaseModel):
    customer_id: str
    post_type: str  # purchase_share, lottery_win, streak_milestone, review, photo, drop_cop, prediction_win
    content_text: Optional[str] = None
    platforms: list[str] = []
    reference_id: Optional[str] = None


# === Prediction Market ===
class PredictionEventCreate(BaseModel):
    title: str
    category: str = "sports"  # sports, local, weather, pop_culture, merchant, crypto
    options: list[dict]  # [{id, label, odds}]
    locks_at: str
    event_time: Optional[str] = None

class PredictionBetCreate(BaseModel):
    customer_id: str
    event_id: str
    option_id: str
    points_wagered: int

class PredictionResolve(BaseModel):
    correct_option_id: str


# === Fashion Drops ===
class DropCreate(BaseModel):
    title: str
    products: list[dict]  # [{product_id, name, price, quantity, image_url}]
    drop_time: str
    drop_type: str = "fcfs"  # fcfs, raffle, auction, invite_only
    max_per_customer: int = 1
    collab_tenant_id: Optional[str] = None

class WaitlistJoin(BaseModel):
    customer_id: str
    bid_amount: Optional[int] = None  # for auction drops


# === Voice Commerce ===
class VoiceOrderCreate(BaseModel):
    customer_id: Optional[str] = None
    channel: str = "web_chat"  # sms, voice, web_chat, whatsapp, instagram_dm
    message: str
    tenant_id: Optional[str] = None
