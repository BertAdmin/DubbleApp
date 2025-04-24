import numpy as np
import pandas as pd
from datetime import date
import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('dubble.db')
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    balance REAL
)
''')
conn.commit()

option = -1

def blow_new_bubble():
    cursor.execute('INSERT INTO accounts (balance) VALUES (?)', (0.01,))
    conn.commit()
    print(f'Account {cursor.lastrowid} created with initial balance $0.01.')

def dubble_bubble(account_number):
    cursor.execute('SELECT balance FROM accounts WHERE id = ?', (account_number,))
    row = cursor.fetchone()
    if row:
        balance = row[0] * 2
        cursor.execute('UPDATE accounts SET balance = ? WHERE id = ?', (balance, account_number))
        conn.commit()
        print(f'Account {account_number} balance doubled to ${balance:.2f}.')
    else:
        print("This account doesn't exist.")

def save_and_show_savings_report():
    cursor.execute('SELECT id, balance FROM accounts')
    rows = cursor.fetchall()
    savings_report = pd.DataFrame(rows, columns=['ACCOUNT', 'AMOUNT'])
    savings_report['DATE'] = date.today()
    savings_report.to_csv('savings.csv', index=False)
    print(savings_report)

def combine_accounts(account_number1, account_number2):
    cursor.execute('SELECT balance FROM accounts WHERE id = ?', (account_number1,))
    row1 = cursor.fetchone()
    cursor.execute('SELECT balance FROM accounts WHERE id = ?', (account_number2,))
    row2 = cursor.fetchone()

    if row1 and row2:
        balance1 = row1[0]
        balance2 = row2[0]
        new_balance = balance1 + balance2
        cursor.execute('UPDATE accounts SET balance = ? WHERE id = ?', (new_balance, account_number1))
        cursor.execute('DELETE FROM accounts WHERE id = ?', (account_number2,))
        conn.commit()
        print(f'Account {account_number2} merged into account {account_number1}. New balance is ${new_balance:.2f}.')
    else:
        print("One or both of the accounts don't exist.")

while(option != 0):
    print('Welcome to Dubble!')
    print('1. Blow a new Bubble')
    print('2. Dubble a Bubble')
    print('3. Save and Show Savings Report')
    print('4. Combine Accounts')
    print('0. Exit')
    try:
        option = int(input('Choose an option:\n'))
    except ValueError:
        print('Invalid input. Please enter a number between 0 and 4.')
        continue
    print()

    if option == 0:
        print('Popping Bubble')
        break
    elif option == 1:
        blow_new_bubble()
    elif option == 2:
        try:
            account_number = int(input('Enter account number: '))
            dubble_bubble(account_number)
        except ValueError:
            print('Invalid account number. Please enter a valid number.')
    elif option == 3:
        save_and_show_savings_report()
    elif option == 4:
        try:
            account_number1 = int(input('Enter the first account number: '))
            account_number2 = int(input('Enter the second account number: '))
            combine_accounts(account_number1, account_number2)
        except ValueError:
            print('Invalid account number. Please enter a valid number.')
    else:
        print('You chose an incorrect option. Please choose 0-4')

conn.close()
print("Done Running")