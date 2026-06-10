#!/usr/bin/env python3

"""
Seed script to create the first Owner account for Mountain Gardens POS.
Run once, then log in via the web UI with this PIN.
"""

from POS_CORE import create_employee, get_employee_path

print("Using employee file:", get_employee_path())

# 👇 Edit these if you want different details
name  = "Rich"
role  = "Owner"          # one of: Cashier, Manager, Owner, Admin
pin   = "8008"           # 4-digit PIN
phone = "707-386-9709"
email = "1m.rich.gee@gmail.com"

ok, msg, emp_id = create_employee(
    name,
    role,
    pin,
    phone=phone,
    email=email,
)

print("Success:", ok)
print("Message:", msg)
print("New Employee ID:", emp_id)
