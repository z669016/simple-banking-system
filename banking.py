import random
import sqlite3


def generate_pin_code():
    return "{:04d}".format(random.randint(1, 9999))


class MajorIndustryIdentifier:
    industries = ['Airline',  # 1
                  'Airline',  # 2
                  'Travel or entertainment',  # 3
                  'Financial or banking',  # 4
                  'Financial or banking',  # 5
                  'Merchandising or banking',  # 6
                  'Petroleum',  # 7
                  'Telecommunications',  # 8
                  'National assignment'  # 9
                  ]

    def __init__(self, code: int):
        assert 0 < code < 10
        self.code = code

    def industry_name(self):
        return MajorIndustryIdentifier.industries[self.code]


class CreditCard:
    iin = 400000

    def __init__(self, number):
        if isinstance(number, int):
            self.iin = CreditCard.iin
            self.account_identifier = number
            self.checksum = CreditCard.calc_checksum(self.account_identifier)
        else:
            self.iin = int(number[0:6])
            self.account_identifier = int(number[6:15])
            self.checksum = int(number[-1])

    def card_number(self):
        return CreditCard.format_card_number(self.iin, self.account_identifier, self.checksum)

    @staticmethod
    def format_card_number(card_iin: int, card_account_identifier: int, card_checksum=0):
        return "{:06d}{:09d}{:01d}".format(card_iin, card_account_identifier, card_checksum)

    def major_industry_identifier(self):
        return MajorIndustryIdentifier(self.iin // 10000)

    def is_visa(self):
        code = self.iin // 100000
        return code == 4

    def is_american_express(self):
        code = self.iin // 10000
        return code == 34 or code == 37

    def is_mastercard(self):
        code = self.iin // 10000
        return code == 51 or code == 55

    @staticmethod
    def is_valid_card_number(card_number: str):
        if len(card_number) != 16:
            return False

        numbers = list(card_number)
        for i in range(len(card_number)):
            numbers[i] = int(numbers[i])
            if i % 2 == 0:
                numbers[i] *= 2
                if numbers[i] > 9:
                    numbers[i] -= 9

        return sum(numbers) % 10 == 0

    @staticmethod
    def calc_checksum(account_identifier: int):
        card_number = CreditCard.format_card_number(CreditCard.iin, account_identifier)
        numbers = list(card_number)
        for i in range(len(card_number)):
            numbers[i] = int(numbers[i])
            if i % 2 == 0:
                numbers[i] *= 2
                if numbers[i] > 9:
                    numbers[i] -= 9
        checksum = sum(numbers) % 10
        return 0 if checksum == 0 else 10 - checksum


class Account:
    def __init__(self, id: int, credit_card: CreditCard, pin: str, balance: int):
        self.id = id
        self.credit_card = credit_card
        self.pin = pin
        self.balance = balance


class AccountsRepositoryDict:
    def __init__(self):
        self.accounts = dict()
        self.last_account_identifier = 0

    def create_account(self, account_identifier: int, credit_card: CreditCard):
        account = Account(account_identifier, credit_card, generate_pin_code(), 0)
        self.accounts[credit_card.account_identifier] = account
        return account

    def read(self, account_identifier: int):
        if account_identifier not in self.accounts:
            return None
        return self.accounts[account_identifier]

    def save(self, account_from: Account, account_to: Account = None):
        self.accounts[account_from.id] = account_from
        if account_to is not None:
            self.accounts[account_to.id] = account_to

    def delete(self, account_identifier: int):
        del self.accounts[account_identifier]

    def next_account_identifier(self):
        self.last_account_identifier += 1
        return self.last_account_identifier


class AccountsRepositorySqlite:
    dbpath = ''
    dbname = 'card.s3db'

    INSERT_CARD = '''INSERT INTO card(id, number, pin, balance) VALUES(?,?,?,?)'''
    SELECT_CARD = '''SELECT id, number, pin, balance FROM card WHERE id = ? '''
    CREATE_CARD = '''CREATE TABLE IF NOT EXISTS card(id INTEGER PRIMARY KEY, number TEXT, pin TEXT, balance INTEGER DEFAULT 0) WITHOUT ROWID '''
    UPDATE_CARD = '''UPDATE card SET balance = ? WHERE id = ?'''
    DELETE_CARD = '''DELETE FROM card WHERE id = ?'''

    CREATE_COUNTER = '''CREATE TABLE IF NOT EXISTS account_id(name TEXT PRIMARY KEY, id INTEGER DEFAULT 0)'''
    INSERT_COUNTER = '''INSERT INTO account_id(name, id) VALUES('LAST_ACCOUNT_IDENTIFIER', 0)'''
    SELECT_COUNTER = '''SELECT id FROM account_id WHERE name = 'LAST_ACCOUNT_IDENTIFIER' '''
    UPDATE_COUNTER = '''UPDATE account_id SET id = ? WHERE name = 'LAST_ACCOUNT_IDENTIFIER' '''

    @staticmethod
    def init():
        conn = sqlite3.connect(AccountsRepositorySqlite.db_path())
        cursor = conn.cursor()
        cursor.execute(AccountsRepositorySqlite.CREATE_CARD)
        cursor.execute(AccountsRepositorySqlite.CREATE_COUNTER)
        try:
            cursor.execute(AccountsRepositorySqlite.SELECT_COUNTER)
            if cursor.fetchone() is None:
                cursor.execute(AccountsRepositorySqlite.INSERT_COUNTER)
        except sqlite3.Error as error:
            print(error)

        cursor.close()
        conn.commit()
        conn.close()

    @staticmethod
    def db_path():
        return AccountsRepositorySqlite.dbpath + AccountsRepositorySqlite.dbname

    def __init__(self):
        AccountsRepositorySqlite.init()

        with sqlite3.connect(AccountsRepositorySqlite.db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT SQLITE_VERSION()')
            data = cursor.fetchone()
            print('SQLite version:', data)
            self.conn = sqlite3.connect('card.s3db')

    def create_account(self, account_identifier: int, credit_card: CreditCard):
        account = Account(account_identifier, credit_card, generate_pin_code(), 0)
        cursor = self.conn.cursor()
        cursor.execute(AccountsRepositorySqlite.INSERT_CARD,
                       (account.id, account.credit_card.card_number(), account.pin, account.balance))
        cursor.close()
        self.conn.commit()
        return account

    def read(self, account_identifier: int):
        cursor = self.conn.cursor()
        cursor.execute(AccountsRepositorySqlite.SELECT_CARD, (account_identifier,))
        row = cursor.fetchone()
        cursor.close()
        return None if row is None else Account(row[0], CreditCard(row[1]), row[2], row[3])

    def save(self, account_from: Account, account_to: Account = None):
        cursor = self.conn.cursor()
        cursor.execute(AccountsRepositorySqlite.UPDATE_CARD, (account_from.balance, account_from.id))
        if account_to is not None:
            cursor.execute(AccountsRepositorySqlite.UPDATE_CARD, (account_to.balance, account_to.id))
        cursor.close()
        self.conn.commit()

    def delete(self, account_identifier: int):
        cursor = self.conn.cursor()
        cursor.execute(AccountsRepositorySqlite.DELETE_CARD, (account_identifier,))
        cursor.close()
        self.conn.commit()

    def next_account_identifier(self):
        cursor = self.conn.cursor()
        cursor.execute(AccountsRepositorySqlite.SELECT_COUNTER)
        id = cursor.fetchone()[0] + 1
        cursor.execute(AccountsRepositorySqlite.UPDATE_COUNTER, (id,))
        cursor.close()
        self.conn.commit()
        return id


class Accounts:
    def __init__(self, accounts_repository):
        self.accounts_repository = accounts_repository
        self.current_account = None

    def login(self, card_number: str, pin: str):
        credit_card = CreditCard(card_number)
        account = self.accounts_repository.read(credit_card.account_identifier)
        if account is None:
            self.logout()
            return

        if pin == account.pin:
            self.current_account = account
        else:
            self.logout()

    def logout(self):
        self.current_account = None

    def create(self):
        account_identifier = self.accounts_repository.next_account_identifier()
        credit_card = CreditCard(account_identifier)
        account = self.accounts_repository.create_account(account_identifier, credit_card)
        return account

    def add_income(self, amount: int):
        self.current_account.balance += amount
        self.accounts_repository.save(self.current_account)

    def do_transfer(self, credit_card: CreditCard, amount: int):
        if self.current_account.balance < amount:
            return 'no_balance'

        account = self.accounts_repository.read(credit_card.account_identifier)
        if account is None:
            return 'invalid_account'

        self.current_account.balance -= amount
        account.balance += amount
        self.accounts_repository.save(self.current_account, account)
        return 'transferred'

    def exists(self, credit_card: CreditCard):
        account = self.accounts_repository.read(credit_card.account_identifier)
        return False if account is None else True

    def close(self):
        self.accounts_repository.delete(self.current_account.id)
        self.logout()

class MenuOption:
    def __init__(self, choice):
        self.choice = choice

    def is_create(self):
        return self.choice == 'create'

    def is_login(self):
        return self.choice == 'login'

    def is_logout(self):
        return self.choice == 'logout'

    def is_balance(self):
        return self.choice == 'balance'

    def is_add_income(self):
        return self.choice == 'add_income'

    def is_do_transfer(self):
        return self.choice == 'do_transfer'

    def is_close_account(self):
        return self.choice == 'close_account'

    def is_exit(self):
        return self.choice == 'exit'


def no_account_selected_menu():
    choice = None
    while choice not in ['0', '1', '2']:
        print('1. Create an account')
        print('2. Log into account')
        print('0. Exit')
        choice = input('>')
        print()
    return MenuOption('create' if choice == '1' else 'login' if choice == '2' else 'exit')


def account_selected_menu():
    choice = None
    while choice not in ['0', '1', '2', '3', '4', '5']:
        print('1. Balance')
        print('2. Add income')
        print('3. Do transfer')
        print('4. Close account')
        print('5. Log out')
        print('0. Exit')
        choice = input('>')
        print()
    return MenuOption('balance' if choice == '1' else
                      'add_income' if choice == '2' else
                      'do_transfer' if choice == '3' else
                      'close_account' if choice == '4' else
                      'logout' if choice == '5' else 'exit')


def login():
    print('Enter your card number:')
    card_number = input('>')
    print('Enter your PIN:')
    pin = input('>')
    print()
    return card_number, pin


def add_income():
    print('Enter income:')
    income = int(input('>'))
    print()
    return income


def enter_card_number():
    print('Enter card number:')
    card_number = input('>')
    return card_number


def enter_transfer_amount():
    print('Enter how much money you want to transfer:')
    amount = input('>')
    return int(amount)


accounts_repository = AccountsRepositorySqlite()
#accounts_repository = AccountsRepositoryDict()
accounts = Accounts(accounts_repository)

option = no_account_selected_menu()
while not option.is_exit():
    if option.is_balance():
        print('Balance:', accounts.current_account.balance)
    elif option.is_logout():
        accounts.logout()
        if accounts.current_account is None:
            print('You have successfully logged out!')
        else:
            print('Log out failed!')
    elif option.is_login():
        card_number, pin = login()
        accounts.login(card_number, pin)
        if accounts.current_account is None:
            print('Wrong card number or PIN!')
        else:
            print('You have successfully logged in!')
    elif option.is_create():
        account = accounts.create()
        if account is not None:
            print('Your card has been created')
            print('Your card number:')
            print(account.credit_card.card_number())
            print('Your card PIN:')
            print(account.pin)
    elif option.is_add_income():
        income = add_income()
        accounts.add_income(income)
        print('Income was added!')
    elif option.is_do_transfer():
        card_number = enter_card_number()
        if not CreditCard.is_valid_card_number(card_number):
            print('Probably you made a mistake in the card number. Please try again!')
        else:
            credit_card = CreditCard(card_number)
            if not accounts.exists(credit_card):
                print('Such a card does not exist.')
            else:
                amount = enter_transfer_amount()
                result = accounts.do_transfer(credit_card, amount)
                if result == 'no_balance':
                    print('Not enough money!')
                if result == 'invalid_account':
                    print('Such a card does not exist.')
                if result == 'transferred':
                    print('Success!')
    elif option.is_close_account():
        accounts.close()
        print('The account has been closed!')

    print()
    if accounts.current_account is None:
        option = no_account_selected_menu()
    else:
        option = account_selected_menu()

print('Bey!')
