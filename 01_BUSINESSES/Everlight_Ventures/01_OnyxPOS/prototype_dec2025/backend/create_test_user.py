#!/usr/bin/env python3
"""Create a test admin user for development"""
import os
import sys
from database import Session, init_db
from models import User, Tenant
from bcrypt import hashpw, gensalt
from datetime import datetime, timedelta

def create_test_admin():
    """Create a test admin user"""
    init_db()

    session = Session()

    try:
        # Test credentials
        EMAIL = "admin@test.com"
        PASSWORD = "admin123"
        BUSINESS_NAME = "Mountain Gardens Nursery"

        # Check if user already exists
        existing_user = session.query(User).filter_by(email=EMAIL).first()
        if existing_user:
            print(f"✓ Test user already exists!")
            print(f"\n{'='*60}")
            print(f"  LOGIN CREDENTIALS")
            print(f"{'='*60}")
            print(f"  Email:    {EMAIL}")
            print(f"  Password: {PASSWORD}")
            print(f"{'='*60}\n")
            return

        # Create tenant
        tenant = Tenant(
            business_name=BUSINESS_NAME,
            subdomain=BUSINESS_NAME.lower().replace(' ', '-'),
            owner_email=EMAIL
        )
        session.add(tenant)
        session.flush()

        # Hash password
        password_hash = hashpw(PASSWORD.encode('utf-8'), gensalt()).decode('utf-8')

        # Create user
        user = User(
            tenant_id=tenant.id,
            email=EMAIL,
            password_hash=password_hash,
            first_name="Admin",
            last_name="User",
            role='owner',
            is_active=True
        )
        session.add(user)

        # Commit
        session.commit()

        print(f"\n{'='*60}")
        print(f"  ✅ TEST ADMIN CREATED SUCCESSFULLY!")
        print(f"{'='*60}")
        print(f"  Email:    {EMAIL}")
        print(f"  Password: {PASSWORD}")
        print(f"  Business: {BUSINESS_NAME}")
        print(f"  Role:     Owner")
        print(f"{'='*60}")
        print(f"\n  🌐 Login at: http://localhost:5173/login")
        print(f"\n{'='*60}\n")

    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    try:
        create_test_admin()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
