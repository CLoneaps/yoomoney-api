"""Example: cache operation history locally to reduce API calls."""

from datetime import timedelta

from yoomoney import Client, SQLiteCache, JSONCache

TOKEN = "YOUR_TOKEN"

client = Client(token=TOKEN)

# --- SQLite cache (recommended) -------------------------------------------
cache = SQLiteCache("my_payments.db")

# Check if cache is fresh (updated within last 5 minutes)
if cache.is_fresh(max_age=timedelta(minutes=5)):
    print("Using cached history...")
    operations = cache.load()
else:
    print("Fetching fresh history from API...")
    history = client.operation_history(records=50)
    cache.save(history.operations)
    operations = history.operations

for op in operations[:5]:
    print(f"{op.datetime}  {op.direction:>8}  {op.amount:>10.2f} ₽  {op.label or '—'}")

# Filter from cache by label without hitting the API
label_ops = cache.load(label="order_123")
print(f"\nOperations with label 'order_123': {len(label_ops)}")


# --- JSON cache (lightweight alternative) ----------------------------------
json_cache = JSONCache("my_payments.json")
json_cache.save(operations)
loaded = json_cache.load()
print(f"\nLoaded {len(loaded)} operations from JSON cache")
