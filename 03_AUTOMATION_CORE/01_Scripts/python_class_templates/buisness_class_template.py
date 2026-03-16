#,create personal and buisness accounts with email, number,  social media accounts, banks and credit cards.

#create a class for each buisness

class buisness:
    def __init__(self, biz_name, owner_name , email, p_num, p_carrier, ig, fb, main_bank, second_bank, cc_limit, cc_lev, item, qty, buy_price, sell_price, profit, cc_pay, expenses, income):
     self.biz_name = biz_name
     self.owner_name = owner_name
     self.email = email
     self.p_num= p_num
     self.p_carrier = p_carrier
     self.ig = ig
     self.fb= fb
     self.main_bank = main_bank
     self.sec_bank = second_bank
     self.cc_limit = cc_limit
     self.cc_lev = cc_lev
     self.item = item
     self.qty = qty
     self.buy_price = buy_price
     self.sell_price = sell_price
     self.profit = profit
     self.cc_pay = cc_pay
     self.expense = expenses
     self.income = income
     
    
buis_1 = buisness ( "Buisness name: Buisness One", "Buisness Owner: Rich Gillies" , "Email: rich_gee@buisnessone.com", "Phone Number: sim ", "Phone Method: Google Voice", "Instagram: Buisness_One", "Facebook: Buisness_One", "Main Bank: Varo" , "Secondary Bank: Coin Base" , "Credit Limit :10,000" ,"Credit Leverage: 1000", "Item : Alibaba" , "Quantity: 100", "Buy Price:  4.99" , "Sell Price: 19.99" , "Profit: 15×100 = 1,500 ", "Credit Payment: 1,000 " "Expenses : Ads, Shipping Amazon Fees" , "Income: 500")