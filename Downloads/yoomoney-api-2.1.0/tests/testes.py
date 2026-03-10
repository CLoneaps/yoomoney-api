from yoomoney import Client, SQLiteCache, PaymentChecker
from datetime import timedelta

TOKEN = "TEST_TOKEN"  # Замените на ваш токен для тестирования

# Аккаунт
client = Client(token=TOKEN)
info = client.account_info()
print(f"Аккаунт: {info.account}")
print(f"Баланс:  {info.balance} {info.currency}")

# История
history = client.operation_history(records=5)
print(f"\nПоследние операции: {len(history.operations)}")
for op in history.operations:
    print(f"  {op.datetime}  {op.amount} ₽  {op.label or '—'}")

# Кэш
cache = SQLiteCache("test.db")
cache.save(history.operations)
print(f"\nЗакэшировано: {len(cache.load())} операций")
print(f"Кэш свежий? {cache.is_fresh(timedelta(minutes=5))}")

# Label
label = PaymentChecker.make_label("order")
print(f"\nLabel для платежа: {label}")