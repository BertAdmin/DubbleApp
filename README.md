# DubbleApp
A savings game that visualizes savings accounts as bubbles and lets you "Dubble" their balance! Great for demonstrating exponential growth to those new to saving and investing.

# Dubble v1

Dubble is a simple command-line application to manage accounts and their balances.

## Features

- Blow a new bubble (create a new account with an initial balance of $0.01).
- Dubble a bubble (double the balance of an existing account).
- Save and show savings report (generate a CSV file with the savings report).
- Combine accounts (merge two accounts into one).
- Delete an account (remove an account from the database).

## Usage

1. **Blow a new bubble**:
   - Choose option 1 from the menu.

2. **Dubble a bubble**:
   - Choose option 2 from the menu.
   - Enter the account number to double the balance.

3. **Save and show savings report**:
   - Choose option 3 from the menu.
   - A CSV file named `savings.csv` will be generated with the savings report.

4. **Combine accounts**:
   - Choose option 4 from the menu.
   - Enter the first account number to combine.
   - Enter the second account number to combine.
   - The account balances are combined and represented by the account number of the first account entered.


## Requirements

- Python 3.13
- numpy
- pandas
- sqlite

