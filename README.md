# PyTrading: Console Edition

A Python console trading application that simulates a trading engine with fake market data.

## Features

- User registration and authentication
- View and refresh market data
- Place market orders (buy/sell)
- Place limit orders
- View portfolio with unrealized P&L
- View order history
- Persistent data storage (JSON)

## Installation

### Virtual Environment Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Deactivate when done
deactivate
```

## Usage

```bash
python3 main.py
```

### Getting Started

1. **Register** - Create a new account (starts with 10,000 virtual balance)
2. **Login** - Sign in to your account
3. **View Market** - See current stock prices
4. **Refresh Market** - Update prices (also executes pending limit orders)
5. **Place Order** - Buy or sell at current market price
6. **Place Limit Order** - Set a target price for execution
7. **View Portfolio** - See your holdings and unrealized P&L
8. **View History** - See all past orders

### Market Data

The app generates fake market data for these assets:
- AAPL, TSLA, GOOG, AAME, ABAT, ABNB, ATLX

Prices fluctuate randomly when you refresh the market.

## License

MIT
