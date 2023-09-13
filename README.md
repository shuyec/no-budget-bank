# **No Budget Bank**

No security. No graphics. Just transactions.

This is a 4 days university project for the class "Sistemi Distribuiti" at University of Milano-Bicocca.

The project uses Python for the backend and Javascript+HTML for the frontend. There's also a little bit of [Jinja2](https://flask.palletsprojects.com/en/2.1.x/templating/) which is the standard template engine of Flask and it allows the use of Python inside HTML pages.

[Javascript Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API) was used to load the data without a page refresh.

The file `main.py` contains all the backend code.
The folder `templates` contains the frontend HTML pages.
The folder `static` contains JQuery and its plugin files.

## Database:
There are two databases which are created and managed by [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/en/2.x/).
1. `accounts.db` has the fields: accountId, name, surname, total.
2. `transactions.db` has the fields: uuid, senderId, receiverId, date, type, divert, amount.

## Endpoints:
1. `/api/account`:
    1. GET: returns all the data in `accounts.db`.
    2. DELETE: deletes the account from `accounts.db`. The old transactions are <u>not</u> deleted.
2. `/api/account/{accountId}`:
    1. GET: returns the name, surname and total from `accounts.db` and the transactions from `transactions.db`. The data is for a specific accountId.
    2. POST: adds a transaction to `transactions.db` if it's valid. The field type is "Withdraw" if the amount is negative, "Deposit" if it's positive and "Useless" if it's zero. It returns the completed transaction and the new total.

        The boolean `divert` is True because the transaction is not divertable.

        If the transaction is a withdrawal, the senderId is the accountId. The receiverId is empty because it might be another bank or a cash withdrawal.

        If the transaction is a deposit, the receiverId is the accountId. The senderId is empty because it can be another bank's account or a cash deposit with a bank or ATM.

        If the amount is zero, the senderId is always the accountId, but irl it should not be accepted. I had to leave this case because of the project's assignment.

    3. PATCH: changes name or surname. If the requests's body has both, then it returns a message that tells the user to use PUT.
3. `/api/transfer`:
    1. POST: if the amount is negative, it returns an error message. It also checks if the accountIds are in `accounts.db` and if "amount" is a float.

    It generates two transactions with a different uuid. One removes money from the sender's account and the other adds it to the receiver.

    It adds the transactions to `transactions.db`.

    It updates the total balance of the involved accounts.
4. `/api/divert`:
    1. POST: diverts a transaction. It's possible only if the uuid is valid, it's of type "Send" and if it's not already diverted (`divert = false`).

    It generates two transactions with different uuids. One has the type "Divert Send" and the other "Divert Receive".

    All the transactions "Divert" have the boolean `divert = True` because they're not divertable.

    The old receiver becomes the new sender and the old sender becomes the new receiver.

    It changes the divert boolean of the "Send" transaction to True because it can only be diverted once.

    Diverting a "Send" transaction which is present in the system but it's associated to a deleted account is not possible.

    It updates the total balances of the involved accounts.

## HTML pages:
1. `/`:
    it shows an input field and a button which works only if there are 20 characters.

    The button sends a GET request to `/api/account/{accountId` and it prints the result in the same page.
2. `/transfer`:
    it shows three input fields and a button which works only if the first two fields have 20 characters and the amount is a positive number.

    The button sends a POST request to `/api/transfer` and it prints the result in the same page.
3. `/account`:
    it shows two input fields and a button which works only if both fields are completed.

    The button sends a POST request to `/api/account` and it prints the new account data in the same page.
4. `/accounts`:
    it shows a table with all the accounts in `accounts.db`.
5. `/divert`:
    it shows an input field and a button which works only if there are 32 characters hyphen excluded.

    There is a mask which uses JQuery and a [plugin](https://igorescobar.github.io/jQuery-Mask-Plugin/) for the uuid input. It's for the automatic input of hyphens.

    The button sends a POST request to `/api/divert` and it prints the result in the same page.
6. `/cash`:
   it shows two radio buttons, two input fields and a confirmation button. The button works only if the id has 20 characters and the amount is a positive number.

   The transactions with amount 0 are displayed with the selected radio button value, but they're saved in the database as "Useless" because of the assignment.

   "Deposit" is the default option because of capitalism.

    The button sends a POST request to `/api/account/{accountId}` and it prints the transaction in the same page.
7. `/delete`:
   it shows an input field for the accountId with 20 characters. The account is deleted from `accounts.db` if it exists.

## Notes:
1. A transaction from one account to the same one is valid.
2. Deposits and withdrawals with amount zero are valid.
3. The reset button in the pages resets both the fields and the previous results. 










