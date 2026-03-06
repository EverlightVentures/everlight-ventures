import openpyxl
import pandas as pd

# Create a new workbook
workbook = openpyxl.Workbook()

# Define the sheets and headers
sheets = [
    ("Rich's Contact Book", [
        "Full Name", "Email Address", "Phone Number", "Mailing Address",
        "Device Type", "Operating System", "IP Address", "MAC Address",
        "Billing Address", "Payment Method", "Account Number", "Invoice Details",
        "Card Number", "Expiration Date", "CVV", "Cardholder Name"
    ]),
    ("Everlight Logistics Contacts", [
        "Full Name", "Email Address", "Phone Number", "Mailing Address",
        "Device Type", "Operating System", "IP Address", "MAC Address",
        "Billing Address", "Payment Method", "Account Number", "Invoice Details",
        "Card Number", "Expiration Date", "CVV", "Cardholder Name"
    ]),
    ("Network Security Private Eye", [
        "Full Name", "Email Address", "Phone Number", "Mailing Address",
        "Device Type", "Operating System", "IP Address", "MAC Address",
        "Billing Address", "Payment Method", "Account Number", "Invoice Details",
        "Card Number", "Expiration Date", "CVV", "Cardholder Name"
    ])
]

# Create the sheets and add the headers
for sheet_name, headers in sheets:
    sheet = workbook.create_sheet(sheet_name)
    sheet.append(["Client Name"])
    sheet.append(headers)

    # Create a Pandas DataFrame with the same headers
    df = pd.DataFrame(columns=["Client Name"] + headers)
    df.to_csv(f"{sheet_name}.csv", index=False)

# Remove the default blank sheet
workbook.remove(workbook.active)

# Save the workbook
workbook.save("contacts_workbook.xlsx")
import os
import hashlib
from collections import defaultdict
from shutil import copy2
import datetime

def get_file_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as file:
        buf = file.read()
        hasher.update(buf)
    return hasher.hexdigest()

def organize_photos(directory):
    file_hashes = defaultdict(list)
    organized_folder = os.path.join(directory, "Organized_Photos")

    if not os.path.exists(organized_folder):
        os.makedirs(organized_folder)

    for subdir, _, files in os.walk(directory):
        for file_name in files:
            file_path = os.path.join(subdir, file_name)
            file_hash = get_file_hash(file_path)
            file_hashes[file_hash].append(file_path)

    for file_hash, file_paths in file_hashes.items():
        if len(file_paths) > 1:
            print(f"Found duplicates: {file_paths}")
            file_paths = sorted(file_paths, key=lambda x: os.path.getmtime(x), reverse=True)
            for file_path in file_paths[1:]:
                os.remove(file_path)
                print(f"Deleted {file_path}")

        main_file_path = file_paths[0]
        timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(main_file_path))
        timestamp_folder = os.path.join(organized_folder, timestamp.strftime("%Y-%m-%d"))
        if not os.path.exists(timestamp_folder):
            os.makedirs(timestamp_folder)

        size_folder = os.path.join(timestamp_folder, str(os.path.getsize(main_file_path)))
        if not os.path.exists(size_folder):
            os.makedirs(size_folder)

        copy2(main_file_path, size_folder)
        print(f"Organized {main_file_path}")

directory = "/storage/emulated/0/USB DRIVE/File_Explorer/Rich_File_Tree/MEDIA_SERVER"
organize_photos(directory)
