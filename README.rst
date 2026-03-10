YooMoney API
============

*Unofficial Python library for the YooMoney API*

|pypi| |python| |license|

.. |pypi| image:: https://img.shields.io/pypi/v/yoomoney?color=blue&label=PyPI
   :target: https://pypi.org/project/yoomoney/
.. |python| image:: https://img.shields.io/pypi/pyversions/yoomoney
   :target: https://pypi.org/project/yoomoney/
.. |license| image:: https://img.shields.io/github/license/AlekseyKorshuk/yoomoney-api
   :target: https://github.com/AlekseyKorshuk/yoomoney-api/blob/master/LICENSE

`🇷🇺 Версия на русском языке <README_RU.rst>`_

----

.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none

Introduction
============

This library provides a convenient Python wrapper around the
`YooMoney Wallet API <https://yoomoney.ru/docs/wallet>`__.
Both **synchronous** (``Client``) and **asynchronous** (``AsyncClient``) clients
are included out of the box.

Features
========

+-----------------------------+---------------------------------------------------------------+
| Method                      | Description                                                   |
+=============================+===============================================================+
| `Access token`_             | Obtain an OAuth access token.                                 |
+-----------------------------+---------------------------------------------------------------+
| `Account information`_      | Retrieve the current status of the user account.             |
+-----------------------------+---------------------------------------------------------------+
| `Operation history`_        | View the full or partial history of operations (paginated,    |
|                             | reverse-chronological order).                                 |
+-----------------------------+---------------------------------------------------------------+
| `Operation details`_        | Get detailed information about a single operation.            |
+-----------------------------+---------------------------------------------------------------+
| `Quickpay forms`_           | Generate a payment form for any website or blog.              |
+-----------------------------+---------------------------------------------------------------+
| `Payment checker`_          | Poll for incoming payments by label (sync & async).           |
+-----------------------------+---------------------------------------------------------------+
| `History cache`_            | Cache operation history locally (SQLite or JSON).             |
+-----------------------------+---------------------------------------------------------------+
| `Webhook notifications`_    | Receive payment notifications via Flask or FastAPI.           |
+-----------------------------+---------------------------------------------------------------+
| `CLI`_                      | Command-line tool for balance, history, and payment watching. |
+-----------------------------+---------------------------------------------------------------+

Installation
============

**From PyPI** (recommended):

.. code-block:: shell

   pip install yoomoney --upgrade

Or with `uv <https://docs.astral.sh/uv/>`_:

.. code-block:: shell

   uv add yoomoney

**With optional webhook support:**

.. code-block:: shell

   pip install yoomoney[flask]    # Flask webhook
   pip install yoomoney[fastapi]  # FastAPI webhook
   pip install yoomoney[all]      # both

**From source**:

.. code-block:: shell

   git clone https://github.com/AlekseyKorshuk/yoomoney-api --recursive
   cd yoomoney-api
   uv sync

Quick start
===========

Access token
------------

First of all you need to receive an access token.

.. image:: docs/assets/token.gif
   :alt: Getting an access token

1. Log in to your YooMoney wallet. If you do not have one,
   `create it <https://yoomoney.ru/reg>`_.
2. Go to the `App registration <https://yoomoney.ru/myservices/new>`_ page.
3. Set the application parameters. Save **CLIENT_ID** and **REDIRECT_URI**.
4. Click **Confirm**.
5. Replace the placeholders below with your real credentials and run the code.
6. Follow the on-screen instructions.

.. code-block:: python

   from yoomoney import Authorize

   Authorize(
       client_id="YOUR_CLIENT_ID",
       redirect_uri="YOUR_REDIRECT_URI",
       client_secret="YOUR_CLIENT_SECRET",
       scope=[
           "account-info",
           "operation-history",
           "operation-details",
           "incoming-transfers",
           "payment-p2p",
           "payment-shop",
       ],
   )

Account information
-------------------

.. code-block:: python

   from yoomoney import Client

   client = Client("YOUR_TOKEN")
   user = client.account_info()

   print("Account number:", user.account)
   print("Balance:", user.balance, user.currency)
   print("Status:", user.account_status)
   print("Type:", user.account_type)

Operation history
-----------------

.. code-block:: python

   from yoomoney import Client

   client = Client("YOUR_TOKEN")
   history = client.operation_history(records=10)

   for op in history.operations:
       print(f"{op.datetime}  {op.direction:>4}  {op.amount} ₽  {op.label or '—'}")

Operation details
-----------------

.. code-block:: python

   from yoomoney import Client

   client = Client("YOUR_TOKEN")
   details = client.operation_details(operation_id="OPERATION_ID")

   for key, value in vars(details).items():
       if not key.startswith("_"):
           print(f"{key:20s} : {str(value).replace(chr(10), ' ')}")

Quickpay forms
--------------

.. code-block:: python

   from yoomoney import Quickpay

   quickpay = Quickpay(
       receiver="410019014512803",
       quickpay_form="shop",
       targets="Sponsor this project",
       paymentType="SB",
       sum=150,
   )
   print(quickpay.base_url)

Payment checker
---------------

``PaymentChecker`` polls the operation history and fires a callback as soon as
an incoming payment with the expected label (and optionally amount) arrives.

.. code-block:: python

   from yoomoney import Quickpay, PaymentChecker
   from yoomoney.operation.operation import Operation

   TOKEN    = "YOUR_TOKEN"
   RECEIVER = "YOUR_WALLET"

   # 1. Generate a unique label for this order
   label = PaymentChecker.make_label("order")

   # 2. Build a payment link
   quickpay = Quickpay(
       receiver=RECEIVER,
       quickpay_form="shop",
       targets="Order payment",
       paymentType="AC",
       sum=299.0,
       label=label,
   )
   print("Payment URL:", quickpay.base_url)

   # 3. Wait up to 10 minutes for the payment
   def on_paid(op: Operation) -> None:
       print(f"✓ Received {op.amount} ₽  label={op.label}")

   checker = PaymentChecker(token=TOKEN, interval=5)
   paid = checker.watch(label=label, callback=on_paid, amount=299.0, timeout=600)

Async version:

.. code-block:: python

   import asyncio
   from yoomoney import PaymentChecker
   from yoomoney.operation.operation import Operation

   async def main() -> None:
       checker = PaymentChecker(token="YOUR_TOKEN", interval=5)

       async def on_paid(op: Operation) -> None:
           print(f"✓ Received {op.amount} ₽")

       await checker.watch_async(label="order_123", callback=on_paid, timeout=300)

   asyncio.run(main())

History cache
-------------

Cache operation history locally to reduce the number of API calls.
Two backends: ``SQLiteCache`` (recommended for production) and ``JSONCache`` (scripts).

.. code-block:: python

   from datetime import timedelta
   from yoomoney import Client, SQLiteCache

   client = Client("YOUR_TOKEN")
   cache  = SQLiteCache("payments.db")

   if cache.is_fresh(max_age=timedelta(minutes=5)):
       operations = cache.load()              # served from disk
   else:
       history = client.operation_history(records=50)
       cache.save(history.operations)         # persist to disk
       operations = history.operations

   # Filter locally — zero API calls
   label_ops = cache.load(label="order_123")
   print(f"Operations for order_123: {len(label_ops)}")

Webhook notifications
---------------------

YooMoney can POST a notification to your server when a payment arrives.

**Flask:**

.. code-block:: shell

   pip install yoomoney[flask]

.. code-block:: python

   from flask import Flask
   from yoomoney.webhook import flask_webhook, Notification

   app    = Flask(__name__)
   SECRET = "YOUR_NOTIFICATION_SECRET"

   def on_payment(n: Notification) -> None:
       print(f"✓ {n.amount} ₽  op={n.operation_id}  label={n.label}")

   @app.route("/", methods=["POST"])
   def notify():
       return flask_webhook(secret=SECRET, on_payment=on_payment)

   if __name__ == "__main__":
       app.run(port=5000)

**FastAPI:**

.. code-block:: shell

   pip install yoomoney[fastapi]

.. code-block:: python

   from fastapi import FastAPI, Request
   from yoomoney.webhook import fastapi_webhook, Notification

   app    = FastAPI()
   SECRET = "YOUR_NOTIFICATION_SECRET"

   def on_payment(n: Notification) -> None:
       print(f"✓ {n.amount} ₽  op={n.operation_id}  label={n.label}")

   @app.post("/")
   async def notify(request: Request):
       return await fastapi_webhook(request=request, secret=SECRET, on_payment=on_payment)

The ``Notification`` model validates the SHA-1 signature automatically.
Pass ``verify=False`` to skip signature checking during local development.

**Setting up notifications in YooMoney**

1. Go to `yoomoney.ru/transfer/myservices/http-notification <https://yoomoney.ru/transfer/myservices/http-notification>`_.
2. Enter your server URL in the **"Куда отправлять (URL сайта)"** field.
3. Copy the value from **"Секрет для проверки подлинности"** — use it as ``SECRET`` in your code.
4. Check **"Отправлять HTTP-уведомления"** and save.

**Testing without a real payment**

For local development you can expose your server via
`ngrok <https://ngrok.com>`_ and use the built-in test button:

.. code-block:: shell

   # 1. Install and start your webhook server
   pip install flask yoomoney[flask]
   python examples/webhook_server.py

   # 2. In a second terminal — expose it to the internet
   ngrok http 5000

   # 3. Copy the public URL from ngrok (e.g. https://abc123.ngrok-free.app)
   #    Paste it into the YooMoney notification settings page
   #    Then click "Протестировать" — you should see the payment in your terminal

Expected terminal output after clicking **"Протестировать"**:

.. code-block:: text

   ✓ Платёж получен!
     Сумма:        200.39 ₽
     Label:
     Operation ID: test-notification
     Отправитель:  41001000040

CLI
---

After installation a ``yoomoney`` command becomes available.
Set the token once via environment variable:

.. code-block:: shell

   export YOOMONEY_TOKEN="YOUR_TOKEN"   # Linux / macOS
   set    YOOMONEY_TOKEN=YOUR_TOKEN     # Windows

.. code-block:: shell

   yoomoney account                              # account info
   yoomoney balance                              # balance only
   yoomoney history --records 10                 # last 10 operations
   yoomoney history --label order_42             # filter by label
   yoomoney details --id 670244335488002312      # operation details
   yoomoney watch --label order_42 --amount 500  # wait for payment
   yoomoney make-label --prefix order            # generate unique label

Async client
============

.. code-block:: python

   import asyncio
   from yoomoney import AsyncClient

   async def main():
       async with AsyncClient("YOUR_TOKEN") as client:
           user    = await client.account_info()
           history = await client.operation_history(records=5)

           print("Balance:", user.balance)
           for op in history.operations:
               print(f"  {op.datetime}  {op.amount} ₽")

   asyncio.run(main())

----

License
=======

This project is licensed under the
`GPL-3.0 <https://github.com/AlekseyKorshuk/yoomoney-api/blob/master/LICENSE>`_.
