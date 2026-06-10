# OnyxPOS Backend API

Next-generation multi-tenant POS system backend built with Flask and SQLAlchemy.

## Features

- 🔐 JWT authentication with role-based access control
- 🏢 Multi-tenant architecture with data isolation
- 📦 Inventory management
- 💰 Sales transactions
- 📊 Analytics and reporting
- 💳 Stripe subscription billing (coming soon)
- 🔒 Secure and scalable

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (production) or SQLite (development)

### Installation

```bash
# Run setup script
chmod +x setup.sh
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Start server
python3 app.py
```

The API will be available at `http://localhost:5000`

### Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python3 database.py

# Run server
python3 app.py
```

## API Documentation

### Authentication

#### Register New Tenant
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "business_name": "My Coffee Shop",
  "email": "owner@coffeeshop.com",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "owner@coffeeshop.com",
  "password": "SecurePassword123!"
}
```

Returns:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": { ... },
  "tenant": { ... }
}
```

### Inventory

#### List Items
```http
GET /api/v1/inventory?page=1&per_page=50&search=coffee
Authorization: Bearer {access_token}
```

#### Create Item
```http
POST /api/v1/inventory
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "sku": "COFFEE-001",
  "name": "House Blend Coffee",
  "category": "Beverages",
  "sell_price": 12.99,
  "cost_price": 6.50,
  "stock_on_hand": 100,
  "reorder_point": 20
}
```

#### Update Item
```http
PATCH /api/v1/inventory/{item_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "sell_price": 13.99,
  "stock_on_hand": 150
}
```

### Sales

#### Create Transaction
```http
POST /api/v1/sales
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "items": [
    {
      "item_id": "uuid-here",
      "quantity": 2,
      "price": 12.99
    }
  ],
  "payment_method": "card",
  "tax_amount": 1.88,
  "customer_email": "customer@example.com"
}
```

#### List Transactions
```http
GET /api/v1/sales?start_date=2025-01-01&end_date=2025-01-31
Authorization: Bearer {access_token}
```

### Analytics

#### Dashboard Metrics
```http
GET /api/v1/analytics/dashboard
Authorization: Bearer {access_token}
```

Returns:
```json
{
  "today": {
    "revenue": 1250.50,
    "transaction_count": 45
  },
  "month_to_date": {
    "revenue": 28450.75,
    "transaction_count": 892
  },
  "inventory": {
    "low_stock_count": 12,
    "total_value": 45000.00
  }
}
```

#### Sales Trend
```http
GET /api/v1/analytics/sales-trend?days=30
Authorization: Bearer {access_token}
```

## Database Schema

The system uses a multi-tenant architecture where all data is isolated by `tenant_id`:

- **tenants** - Business accounts
- **users** - Employees within tenants
- **items** - Inventory items
- **transactions** - Sales transactions
- **transaction_items** - Line items within transactions

## Security

- JWT tokens with 1-hour expiration
- bcrypt password hashing
- SQL injection prevention via SQLAlchemy ORM
- Role-based access control (owner, manager, cashier, laborer)
- Tenant data isolation

## Development

### Run Tests
```bash
pytest
```

### Database Migrations
```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

### Code Formatting
```bash
black .
```

## Deployment

### Using Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up
```

### Using Docker
```bash
docker build -t onyxpos-api .
docker run -p 5000:5000 onyxpos-api
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Flask secret key
- `JWT_SECRET_KEY` - JWT signing key
- `STRIPE_SECRET_KEY` - Stripe API key

## Support

For questions or issues:
- Email: support@onyxpos.com
- Documentation: https://docs.onyxpos.com

## License

Proprietary - All rights reserved
