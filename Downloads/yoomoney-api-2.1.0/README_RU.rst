YooMoney API
============

*Неофициальная Python-библиотека для YooMoney API*

|pypi| |python| |license|

.. |pypi| image:: https://img.shields.io/pypi/v/yoomoney?color=blue&label=PyPI
   :target: https://pypi.org/project/yoomoney/
.. |python| image:: https://img.shields.io/pypi/pyversions/yoomoney
   :target: https://pypi.org/project/yoomoney/
.. |license| image:: https://img.shields.io/github/license/AlekseyKorshuk/yoomoney-api
   :target: https://github.com/AlekseyKorshuk/yoomoney-api/blob/master/LICENSE

`🇬🇧 English version <README.rst>`_

----

.. contents:: Содержание
   :depth: 2
   :local:
   :backlinks: none

----

Введение
========

Библиотека предоставляет удобную Python-обёртку над
`API кошелька YooMoney <https://yoomoney.ru/docs/wallet>`__.
В комплекте идут **синхронный** (``Client``) и **асинхронный** (``AsyncClient``)
клиенты.

Возможности
===========

+-------------------------------------+-----------------------------------------------------------+
| Метод                               | Описание                                                  |
+=====================================+===========================================================+
| `Получение токена`_                 | Получение OAuth-токена доступа.                           |
+-------------------------------------+-----------------------------------------------------------+
| `Информация об аккаунте`_           | Получение информации о состоянии счёта пользователя.      |
+-------------------------------------+-----------------------------------------------------------+
| `История операций`_                 | Просмотр полной или частичной истории операций             |
|                                     | (постраничная, в обратном хронологическом порядке).        |
+-------------------------------------+-----------------------------------------------------------+
| `Детали операции`_                  | Подробная информация об отдельной операции.                |
+-------------------------------------+-----------------------------------------------------------+
| `Формы быстрой оплаты (Quickpay)`_ | Создание платёжной формы для встраивания на сайт или блог. |
+-------------------------------------+-----------------------------------------------------------+
| `Проверка платежей`_                | Polling входящих платежей по label (sync и async).         |
+-------------------------------------+-----------------------------------------------------------+
| `Кэш истории`_                      | Локальное кэширование истории операций (SQLite или JSON).  |
+-------------------------------------+-----------------------------------------------------------+
| `Webhook-уведомления`_              | Приём уведомлений о платежах через Flask или FastAPI.      |
+-------------------------------------+-----------------------------------------------------------+
| `CLI`_                              | Консольный инструмент для баланса, истории и ожидания      |
|                                     | платежей.                                                  |
+-------------------------------------+-----------------------------------------------------------+

Установка
=========

**Из PyPI** (рекомендуется):

.. code-block:: shell

   pip install yoomoney --upgrade

Или с помощью `uv <https://docs.astral.sh/uv/>`_:

.. code-block:: shell

   uv add yoomoney

**С поддержкой webhook:**

.. code-block:: shell

   pip install yoomoney[flask]    # Flask webhook
   pip install yoomoney[fastapi]  # FastAPI webhook
   pip install yoomoney[all]      # оба

**Из исходников**:

.. code-block:: shell

   git clone https://github.com/AlekseyKorshuk/yoomoney-api --recursive
   cd yoomoney-api
   uv sync

Быстрый старт
==============

Получение токена
----------------

Для начала работы необходимо получить токен доступа.

.. image:: docs/assets/token.gif
   :alt: Получение токена доступа

1. Войдите в свой кошелёк YooMoney. Если у вас его нет —
   `создайте <https://yoomoney.ru/reg>`_.
2. Перейдите на страницу `регистрации приложения <https://yoomoney.ru/myservices/new>`_.
3. Задайте параметры приложения. Сохраните **CLIENT_ID** и **REDIRECT_URI**.
4. Нажмите **Подтвердить**.
5. Вставьте свои реальные данные в код ниже и запустите скрипт.
6. Следуйте инструкциям на экране.

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

Самая сложная часть позади!

Информация об аккаунте
----------------------

.. code-block:: python

   from yoomoney import Client

   client = Client("YOUR_TOKEN")
   user = client.account_info()

   print("Номер счёта:", user.account)
   print("Баланс:", user.balance, user.currency)
   print("Статус:", user.account_status)
   print("Тип:", user.account_type)

История операций
----------------

.. code-block:: python

   from yoomoney import Client

   client = Client("YOUR_TOKEN")
   history = client.operation_history(records=10)

   for op in history.operations:
       print(f"{op.datetime}  {op.direction:>4}  {op.amount} ₽  {op.label or '—'}")

Детали операции
---------------

.. code-block:: python

   from yoomoney import Client

   client = Client("YOUR_TOKEN")
   details = client.operation_details(operation_id="OPERATION_ID")

   for key, value in vars(details).items():
       if not key.startswith("_"):
           print(f"{key:20s} : {str(value).replace(chr(10), ' ')}")

Формы быстрой оплаты (Quickpay)
--------------------------------

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

Проверка платежей
-----------------

``PaymentChecker`` опрашивает историю операций и вызывает колбэк сразу после
поступления входящего платежа с нужным label (и опционально суммой).

.. code-block:: python

   from yoomoney import Quickpay, PaymentChecker
   from yoomoney.operation.operation import Operation

   TOKEN    = "YOUR_TOKEN"
   RECEIVER = "YOUR_WALLET"

   # 1. Генерируем уникальный label для заказа
   label = PaymentChecker.make_label("order")

   # 2. Создаём ссылку на оплату
   quickpay = Quickpay(
       receiver=RECEIVER,
       quickpay_form="shop",
       targets="Оплата заказа",
       paymentType="AC",
       sum=299.0,
       label=label,
   )
   print("Ссылка на оплату:", quickpay.base_url)

   # 3. Ждём платёж до 10 минут
   def on_paid(op: Operation) -> None:
       print(f"✓ Получено {op.amount} ₽  label={op.label}")

   checker = PaymentChecker(token=TOKEN, interval=5)
   paid = checker.watch(label=label, callback=on_paid, amount=299.0, timeout=600)

Асинхронная версия:

.. code-block:: python

   import asyncio
   from yoomoney import PaymentChecker
   from yoomoney.operation.operation import Operation

   async def main() -> None:
       checker = PaymentChecker(token="YOUR_TOKEN", interval=5)

       async def on_paid(op: Operation) -> None:
           print(f"✓ Получено {op.amount} ₽")

       await checker.watch_async(label="order_123", callback=on_paid, timeout=300)

   asyncio.run(main())

Кэш истории
-----------

Кэширование истории операций локально — чтобы не дёргать API при каждом запросе.
Два бэкенда: ``SQLiteCache`` (рекомендуется) и ``JSONCache`` (для скриптов).

.. code-block:: python

   from datetime import timedelta
   from yoomoney import Client, SQLiteCache

   client = Client("YOUR_TOKEN")
   cache  = SQLiteCache("payments.db")

   if cache.is_fresh(max_age=timedelta(minutes=5)):
       operations = cache.load()              # из диска
   else:
       history = client.operation_history(records=50)
       cache.save(history.operations)         # сохранить на диск
       operations = history.operations

   # Фильтрация локально — без обращения к API
   label_ops = cache.load(label="order_123")
   print(f"Операций для order_123: {len(label_ops)}")

Webhook-уведомления
-------------------

YooMoney умеет отправлять POST-уведомление на ваш сервер при поступлении платежа.

**Flask:**

.. code-block:: shell

   pip install yoomoney[flask]

.. code-block:: python

   from flask import Flask
   from yoomoney.webhook import flask_webhook, Notification

   app    = Flask(__name__)
   SECRET = "ВАШ_СЕКРЕТ"   # указать в YooMoney → HTTP-уведомления

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
   SECRET = "ВАШ_СЕКРЕТ"

   def on_payment(n: Notification) -> None:
       print(f"✓ {n.amount} ₽  op={n.operation_id}  label={n.label}")

   @app.post("/")
   async def notify(request: Request):
       return await fastapi_webhook(request=request, secret=SECRET, on_payment=on_payment)

Модель ``Notification`` автоматически проверяет SHA-1 подпись.
Передайте ``verify=False`` чтобы отключить проверку во время локальной разработки.

**Настройка уведомлений в YooMoney**

1. Перейдите на страницу `yoomoney.ru/transfer/myservices/http-notification <https://yoomoney.ru/transfer/myservices/http-notification>`_.
2. В поле **"Куда отправлять (URL сайта)"** укажите URL вашего сервера.
3. Скопируйте значение из **"Секрет для проверки подлинности"** — используйте его как ``SECRET`` в коде.
4. Поставьте галочку **"Отправлять HTTP-уведомления"** и сохраните.

**Тестирование без реального платежа**

Для локальной разработки удобно пробросить сервер через
`ngrok <https://ngrok.com>`_ и использовать встроенную кнопку тестирования:

.. code-block:: shell

   # 1. Установить и запустить сервер
   pip install flask yoomoney[flask]
   python examples/webhook_server.py

   # 2. В другом терминале — пробросить наружу
   ngrok http 5000

   # 3. Скопировать публичный URL из ngrok (например https://abc123.ngrok-free.app)
   #    Вставить в настройки уведомлений YooMoney
   #    Нажать "Протестировать" — в терминале появится платёж

Ожидаемый вывод в терминале после нажатия **"Протестировать"**:

.. code-block:: text

   ✓ Платёж получен!
     Сумма:        200.39 ₽
     Label:
     Operation ID: test-notification
     Отправитель:  41001000040

CLI
---

После установки в терминале появляется команда ``yoomoney``.
Токен удобно задать один раз через переменную окружения:

.. code-block:: shell

   export YOOMONEY_TOKEN="YOUR_TOKEN"   # Linux / macOS
   set    YOOMONEY_TOKEN=YOUR_TOKEN     # Windows

.. code-block:: shell

   yoomoney account                              # информация об аккаунте
   yoomoney balance                              # только баланс
   yoomoney history --records 10                 # последние 10 операций
   yoomoney history --label order_42             # фильтр по label
   yoomoney details --id 670244335488002312      # детали операции
   yoomoney watch --label order_42 --amount 500  # ждать платёж
   yoomoney make-label --prefix order            # сгенерировать label

Асинхронный клиент
==================

.. code-block:: python

   import asyncio
   from yoomoney import AsyncClient

   async def main():
       async with AsyncClient("YOUR_TOKEN") as client:
           user    = await client.account_info()
           history = await client.operation_history(records=5)

           print("Баланс:", user.balance)
           for op in history.operations:
               print(f"  {op.datetime}  {op.amount} ₽")

   asyncio.run(main())

----

Лицензия
========

Проект распространяется под лицензией
`GPL-3.0 <https://github.com/AlekseyKorshuk/yoomoney-api/blob/master/LICENSE>`_.
