import json
import random
from decimal import Decimal
import bcrypt
from datetime import datetime, timezone, timedelta

# Constants
TRADE_FEE_PCT = Decimal("0.002") # 0.2%

# Global state
users = {}
market = {}
session = {"user": None} # Store logged-in username

class JSONEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, Decimal):
      """
      Python json TypeError: Object of type Decimal is not JSON serializable
      Refer to
      - https://stackoverflow.com/questions/69104540/python-json-typeerror-object-of-type-decimal-is-not-json-serializable
      - https://github.com/open-contracting/spoonbill-web/issues/120
      """
      return float(obj)
      
    if isinstance(obj, bytes):
      """
      TypeError: Object of type bytes is not JSON serializable
      Refer to https://stackoverflow.com/questions/606191/convert-bytes-to-a-string-in-python-3
      """
      return obj.decode("utf-8")
      
    return json.JSONEncoder.default(self, obj)

def register():
  global session

  if session["user"] is not None and session["user"] != "":
    print("You must log out first")
    return
  
  while True:
    username = input("Enter username: ").strip()
    if username is None or username == "":
      print("Please provide a username first")
    elif " " in username:
      print("Username must not have spaces")
    elif len(username) < 3:
      print("Username must be at least 3 characters")
    elif username in users:
      print("Username already taken")
    else:
      break

  while True:
    password = input("Enter password: ").strip()
    if password is None or password == "":
      print("Please provide a password first")
    elif len(password) < 5:
      print("Password must be at least 5 characters")
    else:
      salt = bcrypt.gensalt() # We only need salt generation when hashing new passwords
      # TypeError: Strings must be encoded before hashing
      # Refer to https://stackoverflow.com/questions/76237943/bcrypt-error-typeerror-strings-must-be-encoded-before-hashing
      password_encoded = password.encode("utf-8")
      hashed_password = bcrypt.hashpw(password_encoded, salt)
      users[username] = {"password": hashed_password, "balance": Decimal(10000), "portfolio": {}, "history": []}
      break
  
  session["user"] = username
  print("Registered successfully")

def login():
  global session

  if session["user"] != None and session["user"] != "":
    print("You must log out first")
    return
  
  while True:
    while True:
      username = input("Enter username: ").strip()
      if username is None or username == "":
        print("Please provide your username first")
      else:
        break

    while True:
      password = input("Enter password: ").strip()
      if password is None or password == "":
        print("Please provide your password first")
      else:
        break

    if username not in users:
      print("Invalid username/password. Please try again.")
      continue

    # Check entered password against stored hashed value
    # Refer to https://www.geeksforgeeks.org/python/hashing-passwords-in-python-with-bcrypt/
    password_encoded = password.encode("utf-8")
    stored_password = users[username]["password"].encode("utf-8") # Already hashed
    if bcrypt.checkpw(password_encoded, stored_password): # Compares byte values
      print("Successfully logged in!\n")
      session["user"] = username
      break
    else:
      print("Invalid username/password. Please try again.")

def init_market(assets):
  for asset in assets:
    price = Decimal(random.uniform(50, 500))
    market[asset] = {"price": price, "history": []}

def update_market():
  """
  Note: Unrealized P&L for a new order is zero if this function is not called again since the market 
  price of an asset when a user placed an order hasn't changed (unless the market data update happens 
  on the background as a separate process)
  """
  for asset in market:
    change = Decimal(random.uniform(-5, 5)) # Simulate volatility
    market[asset]["price"] += change
    
    if market[asset]["price"] < 0:
      market[asset]["price"] = 0
    
    market[asset]["history"].append(market[asset]["price"])
  
  # Timezone-aware datetime object
  # Refer to https://stackoverflow.com/questions/3327946/how-can-i-get-the-current-time-now-in-utc
  utc_datetime = datetime.now(timezone.utc) 
  ph_datetime = utc_datetime + timedelta(hours=8) # Convert UTC to Philippine datetime
  iso_format = ph_datetime.strftime("%Y-%m-%d %H:%M:%S") # Example: "2026-03-01 21:25:00"
  print(f"[{iso_format}] Successfully refreshed market data")

def check_pending_orders():
  executed = []
  for username, data in users.items(): # key-value pairs
    if "pending_orders" not in data:
      data["pending_orders"] = []
      continue
    
    # Process orders (per user)
    orders = data["pending_orders"]
    new_orders = []
    for order in orders:
      current_price = market[order["asset"]]["price"]

      action = order["action"]
      asset = order["asset"]
      limit_price = order["limit_price"]
      quantity = order["quantity"]

      if action == "BUY" and current_price <= limit_price:
        execute_order(action, username, asset, limit_price, quantity, is_limit_order=True)
        executed.append((username, order))
      elif action == "SELL" and current_price >= limit_price:
        execute_order(action, username, asset, limit_price, quantity, is_limit_order=True)
        executed.append((username, order))
      else:
        new_orders.append(order)

    data["pending_orders"] = new_orders
  
  if executed:
    print(f"Executed {len(executed)} pending limit order(s)")

def place_order(current_user):
  if current_user is None or current_user == "":
    print("You must log in first")
    return

  while True:
    asset = input("Enter asset (e.g., AAPL): ").strip().upper()
    if asset is None or asset == "":
      print("Please provide an asset first") 
    elif asset not in market:
      print("Asset not found in market")
    else:
      break

  while True:
    action = input("Buy or Sell: ").strip().upper()
    if action is None or action == "":
      print("Please provide an action first")
    elif action != "BUY" and action != "SELL":
      print("Buy or sell only")
    else:
      break
  
  while True:
    quantity = input("Quantity: ").strip()
    if quantity is None or quantity == "":
      print("Please provide a quantity first")
      continue
    
    # Check if valid Decimal value
    try:
      quantity = Decimal(quantity)
    except ValueError:
      print("Invalid quantity value")
      continue
    
    if quantity <= 0:
      print("Quantity must be positive")
    else:
      break
 
  price = Decimal(market[asset]["price"])
  execute_order(action, current_user, asset, price, quantity)
  
def execute_order(action, current_user, asset, price, quantity, is_limit_order=False): 
  cost = price * quantity
  fee = cost * TRADE_FEE_PCT
  total_cost = cost + fee

  # ---------------- BUY ----------------
  if action == "BUY":
    if users[current_user]["balance"] < total_cost:
      if not is_limit_order: # Display error message if auto-execute order
        print(f"Insufficient balance (required: {total_cost:.2f} incl. {fee:.2f} fee)")
      return

    users[current_user]["balance"] -= total_cost
    
    if asset not in users[current_user]["portfolio"]:
      users[current_user]["portfolio"][asset] = {"quantity": quantity, "cost_basis": total_cost}
    else:
      users[current_user]["portfolio"][asset]["quantity"] += quantity
      users[current_user]["portfolio"][asset]["cost_basis"] += total_cost
  
  # ---------------- SELL ----------------
  elif action == "SELL":
    if asset not in users[current_user]["portfolio"] or users[current_user]["portfolio"][asset]["quantity"] < quantity:
      if not is_limit_order: # Display error message if auto-execute order
        diff = quantity - users[current_user]["portfolio"][asset]["quantity"]
        print(f"Insufficient holdings (required: at least {diff:.2f} more shares)")
      return
    
    proceeds = cost - fee
    if proceeds < 0: # Rare edge case
      proceeds = Decimal(0)

    users[current_user]["balance"] += proceeds
    users[current_user]["portfolio"][asset]["quantity"] -= quantity

    # Note: Don't change cost_basis here - it stays as total historical cost
    if users[current_user]["portfolio"][asset]["quantity"] <= 0:
      del users[current_user]["portfolio"][asset]
      
  else:
    if not is_limit_order:
      print("Invalid action")
    return

  # Save to order history
  users[current_user]["history"].append({"action": action, "asset": asset, "quantity": quantity, "price": price, "fee": fee})
  print(f"Order executed! {action} {quantity:.2f} {asset} @ {price:.2f} | Fee: {fee:.2f} | Net: {proceeds if action == "SELL" else -total_cost:+.2f}")

  save_data()

def view_market(market):
  print("\nMarket:")

  for asset in market:
    print(f"{asset} = {market[asset]["price"]:.2f}")
    
    if len(market[asset]["history"]) > 0:
      truncated_history = market[asset]["history"] 
      truncated_history = truncated_history[::-1][:5] # Take top five recent
      print("Prices (recent):")
      for prev_price in truncated_history:
        print(f"{prev_price:.2f}")
    print()

def view_portfolio(current_user):
  if current_user is None or current_user == "":
    print("You must log in first")
    return

  global users, market
  total_market_value = 0
  
  print(f"\nYour portfolio\n")
  print("Positions\t Shares\t Market Price\t Market Value\t Unrealized P&L")
  for stock, details in users[current_user]["portfolio"].items():
    qty = Decimal(details["quantity"])
    cost_basis = details["cost_basis"]
    
    market_price = market[stock]["price"]
    market_value = qty * market_price
    total_market_value += market_value

    unrealized = market_value - cost_basis # Refer to https://www.oreateai.com/blog/how-to-calculate-unrealized-gain-or-loss/1c8cab6f050c422675354911f34b28ad
    
    # Pad spaces before the values (formatting)
    print(f"{stock}\t\t {qty:>6}\t {market_price:>12.2f}\t {market_value:>12.2f}\t {unrealized:>14.2f}")
    
  print(f"\nTotal value: {total_market_value:.2f} | Balance: {users[current_user]["balance"]:.2f}")

def view_history(current_user):
  if current_user is None or current_user == "":
    print("You must log in first")
    return

  history_list = users[current_user]["history"]
  if len(history_list) == 0:
    print("You don't have any orders yet")
    return
  
  
  print("Action\t Stock\t Quantity\t Price\t\t Fee")
  for history in history_list:
    price = Decimal(history["price"])
    fee = Decimal(0)
    if "fee" in history:
      fee = history["fee"]
      
    print(f"{history["action"]}\t {history["asset"]}\t {history["quantity"]:.2f}\t\t {price:.2f}\t\t {fee:.2f}")

def save_data():
  # Note: type Decimal is not JSON serializable
  with open("data.json", "w") as f:
    json.dump({"users": users, "market": market}, f, cls=JSONEncoder)

def load_data():
  """
  This method must be called first upon starting the app
  """
  try:
    with open("data.json", "r") as f:
      global users, market
      data = json.load(f)

      # When loading users data, the balances are mapped to float type
      # Make sure to convert them to Decimal
      users = data["users"]
      for user in users:
        users[user]["balance"] = Decimal(users[user]["balance"])
      
      # Make sure to convert quantity and cost_basis to int and Decimal respectively
      for user in users:
        for asset in users[user]["portfolio"]:
          users[user]["portfolio"][asset]["quantity"] = Decimal(users[user]["portfolio"][asset]["quantity"])
          users[user]["portfolio"][asset]["cost_basis"] = Decimal(users[user]["portfolio"][asset]["cost_basis"])
      
      # When loading market data, the prices are mapped to float type
      # Make sure to convert them to Decimal
      market = data["market"]
      for asset in market:
        market[asset]["price"] = Decimal(market[asset]["price"])
  except FileNotFoundError:
    print("File cannot be found")
  except Exception as e:
    print("Corrupted save file", e)

def place_limit_order(current_user):
  if current_user is None or current_user == "":
    print("You must log in first")
    return
  
  while True:
    asset = input("Enter asset (e.g., AAPL): ").strip().upper()
    if asset is None or asset == "":
      print("Please provide an asset first")
    elif asset not in market:
      print("Asset not found in market")
    else:
      break
  
  while True:
    action = input("Buy or Sell: ").strip().upper()
    if action is None or action == "":
      print("Please provide an action first")
    elif action != "BUY" and action != "SELL":
      print("Buy or Sell only")
    else:
      break
  
  while True:
    quantity = input("Quantity: ").strip()
    if quantity is None or quantity == "":
      print("Please provide a quantity first")
      continue
    
    # Check if valid Decimal value
    try:
      quantity = Decimal(quantity)
    except ValueError:
      print("Invalid quantity value")
      continue

    if quantity <= 0:
      print("Quantity must be positive")
    else:
      break
  
  while True:
    limit_price = input("Limit Price: ").strip()
    if license is None or limit_price == "":
      print("Please provide a limit price first")
      continue
    
    # Check if valid Decimal value
    try:
      limit_price = Decimal(limit_price)
    except ValueError:
      print("Invalid limit price value")
      continue

    if limit_price <= 0:
      print("Limit price must be positive")
    else:
      break
  
  utc_datetime = datetime.now(timezone.utc) 
  ph_datetime = utc_datetime + timedelta(hours=8) # Convert UTC to Philippine datetime
  iso_format = ph_datetime.strftime("%Y-%m-%d %H:%M:%S") # Example: "2026-03-01 21:25:00"
  
  limit_order = {
    "type": "LIMIT",
    "action": action,
    "asset": asset,
    "quantity": quantity,
    "limit_price": limit_price,
    "date_entry": iso_format
  }
  
  if "pending_orders" not in users[current_user]: # If key doesn't exist yet
    users[current_user]["pending_orders"] = [limit_order]
  else:
    users[current_user]["pending_orders"].append(limit_order)

  print(f"[{iso_format}] Limit order placed! {action} {quantity:.2f} {asset} @ {limit_price:.2f}")
  
def main():
  global session, market
  
  load_data()

  if not market: # Populate if there's no market data yet
    init_market(["AAPL", "TSLA", "GOOG", "AAME", "ABAT", "ABNB", "ATLX"])
  
  while True:
    print("\nPyTrading: Console Edition")
    print("1. Register")
    print("2. Login")
    print("3. View market")
    print("4. Refresh market")
    print("5. Place order")
    print("6. View portfolio")
    print("7. View history")
    print("8. Place limit order")
    print("9. Log out")
    print("10. Exit program")

    choice = input("\nEnter choice: ")

    if choice == "1": # Register
      register()
    elif choice == "2": # Login
      login()
    elif choice == "3": # View market
      view_market(market)
    elif choice == "4": # Refresh market
      update_market()
      save_data()
    elif choice == "5": # Place order
      place_order(session["user"])
    elif choice == "6": # View portfolio
      view_portfolio(session["user"])
    elif choice == "7": # View history
      view_history(session["user"])
    elif choice == "8": # Place limit order
      place_limit_order(session["user"])
    elif choice == "9": # Log out
      if session["user"] is None or session["user"] == "":
        print("You must log in first")
        continue
      save_data()
      session["user"] = ""
      print("You have successfully logged out!")
    elif choice == "10": # Exit program
      session["user"] = "" # Make sure session is cleared
      print("Exiting program...")
      save_data()
      exit()
    else:
      print("Invalid choice")

    # Process after every refresh
    check_pending_orders()
    
if __name__ == "__main__":
  main()
