================================================================================
     🌿  MOUNTAIN GARDENS NURSERY & PET  🌿
        MANAGEMENT SYSTEM v3.0 - USER GUIDE
================================================================================

              SALES • TIME CLOCK • TIME OFF
          Growing Naturally with You Since 1980

================================================================================
                    TABLE OF CONTENTS
================================================================================

   1.  WHAT DOES THIS PROGRAM DO?
   2.  INSTALLING PYTHON (FIRST TIME ONLY)
   3.  SETTING UP THE PROGRAM
   4.  HOW TO START THE PROGRAM EVERY DAY
   5.  RECORDING A SALE (STEP BY STEP)
   6.  CANCELING A SALE
   7.  TIME CLOCK - CLOCKING IN AND OUT
   8.  REQUESTING TIME OFF
   9.  DAILY REPORTS
  10.  WHERE ARE FILES SAVED?
  11.  EMAILING FILES AT END OF DAY
  12.  TROUBLESHOOTING
  13.  QUICK REFERENCE CHEAT SHEET


================================================================================
   1.  WHAT DOES THIS PROGRAM DO?
================================================================================

This is an all-in-one management system that handles:

   🛒  SALES
       • Record every transaction with categories
       • Calculate tax automatically (8.25%)
       • Calculate change for cash payments
       • Print receipts
       • Organize by month/week automatically

   ⏰  TIME CLOCK
       • Employees clock in and out
       • Track breaks and lunch (California labor law compliant!)
       • Calculate hours worked and overtime
       • Friendly messages when clocking in/out

   📅  TIME OFF
       • Request vacation, sick days, etc.
       • Must be 2 weeks in advance (California rule)
       • Manager can view all requests

   📊  REPORTS
       • Daily sales summary
       • Employee hours summary


================================================================================
   2.  INSTALLING PYTHON (FIRST TIME ONLY)
================================================================================

This program needs Python to run. Here's how to install it:

╔════════════════════════════════════════════════════════════════════════════╗
║                              WINDOWS                                        ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                             ║
║   1. Open your web browser                                                  ║
║                                                                             ║
║   2. Go to: https://www.python.org/downloads/                               ║
║                                                                             ║
║   3. Click the big yellow "Download Python 3.x.x" button                    ║
║                                                                             ║
║   4. Run the downloaded file                                                ║
║                                                                             ║
║   5. ⚠️  IMPORTANT: Check the box that says:                                ║
║      ☑️  "Add Python to PATH"                                                ║
║                                                                             ║
║   6. Click "Install Now"                                                    ║
║                                                                             ║
║   7. Wait for installation to complete                                      ║
║                                                                             ║
║   8. Click "Close"                                                          ║
║                                                                             ║
║   Done! Python is installed.                                                ║
║                                                                             ║
╚════════════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════════════╗
║                                MAC                                          ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                             ║
║   Good news! Macs usually have Python already installed.                    ║
║                                                                             ║
║   To check:                                                                 ║
║   1. Press Command + Space (Spotlight opens)                                ║
║   2. Type: Terminal                                                         ║
║   3. Press Enter                                                            ║
║   4. Type: python3 --version                                                ║
║   5. Press Enter                                                            ║
║                                                                             ║
║   If you see "Python 3.x.x" - you're good!                                  ║
║                                                                             ║
║   If not, download from: https://www.python.org/downloads/                  ║
║                                                                             ║
╚════════════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════════════╗
║                              ANDROID                                        ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                             ║
║   Option 1: Termux (Free, Recommended)                                      ║
║   -------------------------------------                                     ║
║   1. Install "Termux" from F-Droid (NOT Play Store - it's outdated)         ║
║      Website: https://f-droid.org/packages/com.termux/                      ║
║                                                                             ║
║   2. Open Termux                                                            ║
║                                                                             ║
║   3. Type these commands (one at a time, press Enter after each):           ║
║                                                                             ║
║      pkg update                                                             ║
║      pkg install python                                                     ║
║                                                                             ║
║   4. Type 'y' when asked to confirm                                         ║
║                                                                             ║
║   5. Done! Python is installed                                              ║
║                                                                             ║
║   Option 2: Pydroid 3 (Easier but has ads)                                  ║
║   -----------------------------------------                                 ║
║   1. Install "Pydroid 3" from the Google Play Store                         ║
║   2. Open the app                                                           ║
║   3. Open the .py file directly in the app                                  ║
║   4. Press the Play button to run                                           ║
║                                                                             ║
╚════════════════════════════════════════════════════════════════════════════╝


================================================================================
   3.  SETTING UP THE PROGRAM
================================================================================

STEP 1: CREATE A FOLDER
-----------------------

   1. Go to your Desktop
   2. Right-click and choose "New Folder"
   3. Name it: Mountain_Gardens_Sales

STEP 2: ADD THE FILES
---------------------

   Copy these files into the folder:
   
   📂 Mountain_Gardens_Sales/
   ├── 📜 Mountain_Gardens_POS.py    <-- The program
   └── 📖 README.txt                  <-- This help file

That's it! You're ready to go!


================================================================================
   4.  HOW TO START THE PROGRAM EVERY DAY
================================================================================

Every morning when you open the store:

╔════════════════════════════════════════════════════════════════════════════╗
║                              WINDOWS                                        ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                             ║
║   METHOD 1: Double-Click (Easiest)                                          ║
║   ---------------------------------                                         ║
║   1. Open the Mountain_Gardens_Sales folder                                 ║
║   2. Double-click on Mountain_Gardens_POS.py                                ║
║   3. If asked "How to open?" - select Python                                ║
║                                                                             ║
║   METHOD 2: Command Prompt                                                  ║
║   -------------------------                                                 ║
║   1. Press the Windows key                                                  ║
║   2. Type: cmd                                                              ║
║   3. Press Enter                                                            ║
║   4. Type (or copy/paste):                                                  ║
║                                                                             ║
║      cd Desktop\Mountain_Gardens_Sales                                      ║
║                                                                             ║
║   5. Press Enter                                                            ║
║   6. Type:                                                                  ║
║                                                                             ║
║      python Mountain_Gardens_POS.py                                         ║
║                                                                             ║
║   7. Press Enter                                                            ║
║   8. The program starts! 🎉                                                 ║
║                                                                             ║
╚════════════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════════════╗
║                                MAC                                          ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                             ║
║   1. Press Command + Space                                                  ║
║   2. Type: Terminal                                                         ║
║   3. Press Enter                                                            ║
║   4. Type (or copy/paste):                                                  ║
║                                                                             ║
║      cd ~/Desktop/Mountain_Gardens_Sales                                    ║
║                                                                             ║
║   5. Press Enter                                                            ║
║   6. Type:                                                                  ║
║                                                                             ║
║      python3 Mountain_Gardens_POS.py                                        ║
║                                                                             ║
║   7. Press Enter                                                            ║
║   8. The program starts! 🎉                                                 ║
║                                                                             ║
╚════════════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════════════╗
║                   LINUX / ANDROID (Termux)                                  ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                             ║
║   1. Open Terminal (or Termux on Android)                                   ║
║   2. Navigate to where you saved the file:                                  ║
║                                                                             ║
║      cd /path/to/Mountain_Gardens_Sales                                     ║
║                                                                             ║
║   3. Run:                                                                   ║
║                                                                             ║
║      python3 Mountain_Gardens_POS.py                                        ║
║                                                                             ║
╚════════════════════════════════════════════════════════════════════════════╝


================================================================================
   5.  RECORDING A SALE (STEP BY STEP)
================================================================================

When a customer is ready to pay:

STEP 1: START NEW SALE
----------------------
   At the main menu, press: 1
   Press Enter

STEP 2: SELECT CATEGORY
-----------------------
   You'll see:
   
      🐾  [A]  Animal
      📦  [P]  Product
      🌱  [L]  Plant
      🚫  [X]  CANCEL
   
   Press A, P, or L then Enter

STEP 3: SELECT SUBCATEGORY
--------------------------
   Example for Products:
   
      🌍  [S]  Soil & Amendments
      🧪  [F]  Fertilizer
      🪴  [P]  Pots & Containers
      ...etc
   
   Press the letter then Enter

STEP 4: ENTER ITEM INFO
-----------------------
   1. Item Name: Type what it is (e.g., "Japanese Maple")
   2. Description: Optional details (e.g., "5 gallon, red leaves")
   3. Quantity: How many? (e.g., 1)
   4. Size: Optional (e.g., "5 gal")
   5. Price: Price BEFORE tax (e.g., 49.99)

STEP 5: ADD MORE OR FINISH
--------------------------
   After each item:
   
      [Y]  Add another item
      [N]  Done, go to payment
      [X]  Cancel entire sale

STEP 6: PAYMENT
---------------
      [C]  Cash
      [D]  Card
      [X]  Cancel
   
   For cash: Enter amount received
   The program shows change and which bills/coins to give!

STEP 7: FINAL DETAILS
---------------------
   1. Cashier initials (e.g., "JD")
   2. Note (optional)
   3. Print receipt? Y or N

DONE! Sale is saved!


================================================================================
   6.  CANCELING A SALE
================================================================================

You can cancel at ANY TIME during a sale!

   • Type X and press Enter at any prompt
   • You'll be asked to confirm
   • If you confirm, the sale is discarded
   • NOTHING is saved if you cancel

This is useful if:
   • Customer changes their mind
   • You made a mistake
   • Customer's card declines
   • Any other reason!


================================================================================
   7.  TIME CLOCK - CLOCKING IN AND OUT
================================================================================

California Labor Law Reminders:
   • 30-minute lunch required after 5 hours
   • 10-minute breaks every 4 hours
   • Overtime after 8 hours

HOW TO CLOCK IN:
----------------
   1. Press 4 at main menu
   2. Enter your Employee ID
   3. Press Y to clock in
   4. You'll see a friendly welcome message!

HOW TO TAKE A BREAK:
--------------------
   1. Press 4 at main menu
   2. Enter your Employee ID
   3. Choose:
      [B] Take break (10 minutes)
      [L] Take lunch (30 minutes)
   
   When you return:
   1. Press 4 again
   2. Enter your ID
   3. The program knows you're on break
   4. Press Y to end break

HOW TO CLOCK OUT:
-----------------
   1. Press 4 at main menu
   2. Enter your Employee ID
   3. Press O to clock out
   4. You'll see your total hours!
   5. Friendly goodbye message!

FIRST TIME? ADD YOURSELF:
-------------------------
   1. Press 7 at main menu
   2. Press A to add employee
   3. Enter your name
   4. You'll get an ID number
   5. Remember your ID!


================================================================================
   8.  REQUESTING TIME OFF
================================================================================

IMPORTANT RULE: Must request 2 WEEKS in advance!

HOW TO REQUEST:
---------------
   1. Press 5 at main menu
   2. Enter your Employee ID
   3. Enter START date (format: 2025-12-15)
   4. Enter END date (format: 2025-12-20)
   5. Select reason:
      [V] Vacation
      [P] Personal
      [S] Sick/Medical
      [F] Family
      [O] Other
   6. Confirm to submit

Your request will be marked "PENDING" until a manager approves it.

TO VIEW REQUESTS:
-----------------
   Press 6 at main menu to see all requests and their status.


================================================================================
   9.  DAILY REPORTS
================================================================================

At the end of each day:

   1. Press 2 at main menu
   
   You'll see:
   • Total transactions
   • Total revenue
   • Cash vs card breakdown
   • Employee hours worked
   • Overtime hours


================================================================================
  10.  WHERE ARE FILES SAVED?
================================================================================

Everything is saved in the SAME FOLDER as the program:

   📂 Mountain_Gardens_Sales/
   │
   ├── 📜 Mountain_Gardens_POS.py     (the program)
   ├── 📖 README.txt                   (this file)
   ├── 📋 employees.json               (employee list)
   │
   ├── 📂 Sales_Logs/
   │   └── 2025/
   │       └── 11_November/
   │           └── Week_4_Nov_24-Nov_30/
   │               └── 2025-11-25_Tuesday_sales.csv
   │
   ├── 📂 Receipts/
   │   └── (same structure)
   │
   ├── 📂 Time_Clock/
   │   └── (same structure)
   │
   ├── 📂 Daily_Reports/
   │   └── (same structure)
   │
   └── 📂 Time_Off_Requests/
       └── 2025_time_off_requests.csv

IMPORTANT:
   • Each DAY creates a NEW file
   • Each WEEK creates a new folder
   • Each MONTH creates a new folder
   • Previous data is NEVER deleted!


================================================================================
  11.  EMAILING FILES AT END OF DAY
================================================================================

To send the daily sales log:

   1. Press 8 at main menu (File Locations)
   2. Press Y to open the folder
   3. Navigate to: Sales_Logs → Year → Month → Week
   4. Find today's CSV file
   5. Attach it to an email!

The file opens in Excel or Google Sheets.


================================================================================
  12.  TROUBLESHOOTING
================================================================================

PROBLEM: "python is not recognized"
-----------------------------------
SOLUTION: 
   • Python not installed, or
   • PATH wasn't checked during install
   • Reinstall Python and CHECK "Add to PATH"

PROBLEM: Program won't open when I double-click
----------------------------------------------
SOLUTION:
   • Use the command prompt/terminal method instead
   • See Section 4 for step-by-step

PROBLEM: Can't find my files
----------------------------
SOLUTION:
   • Press 8 at main menu
   • Press Y to open the folder

PROBLEM: Employee not found
---------------------------
SOLUTION:
   • Press 7 → V to view employees
   • Check the correct ID number
   • Add yourself if not in the list

PROBLEM: Time off request rejected - not 2 weeks
-----------------------------------------------
SOLUTION:
   • California requires 2 weeks advance notice
   • Choose a date at least 14 days away

PROBLEM: Weird characters showing
---------------------------------
SOLUTION:
   • Terminal might not support fancy characters
   • Program still works! Just looks different


================================================================================
  13.  QUICK REFERENCE CHEAT SHEET
================================================================================

STARTING THE PROGRAM:
---------------------
   Windows:  cd Desktop\Mountain_Gardens_Sales
             python Mountain_Gardens_POS.py
   
   Mac:      cd ~/Desktop/Mountain_Gardens_Sales
             python3 Mountain_Gardens_POS.py

MAIN MENU:
----------
   1 = New Sale
   2 = Daily Report
   3 = View Sales Log
   4 = Clock In/Out
   5 = Request Time Off
   6 = View Time Off
   7 = Manage Employees
   8 = File Locations
   Q = Quit

DURING A SALE:
--------------
   A = Animal
   P = Product
   L = Plant
   X = CANCEL (works anytime!)
   
   C = Cash payment
   D = Card payment

TIME CLOCK:
-----------
   B = Take Break
   L = Take Lunch
   O = Clock Out
   C = Cancel

FILES:
------
   Sales: Sales_Logs/YYYY/MM_Month/Week_N/
   Time:  Time_Clock/YYYY/MM_Month/Week_N/


================================================================================

     NEED HELP? Contact the store owner or manager.
     
     🌿 Mountain Gardens Nursery & Pet
     503 S. Curry Street
     Tehachapi, CA 93561
     (661) 822-4960
     
     Growing Naturally with You Since 1980

================================================================================
