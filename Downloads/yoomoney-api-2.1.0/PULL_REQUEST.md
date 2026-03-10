# feat: payment checker, history cache, webhook support, CLI

## What's added

### `yoomoney/checker/` — PaymentChecker
Polling loop that watches for an incoming payment by `label` and fires a
callback when it arrives. Supports both sync and async usage.

```python
checker = PaymentChecker(token=TOKEN, interval=5)
paid = checker.watch(label="order_42", callback=on_paid, amount=299.0, timeout=600)
```

- `watch(label, callback, amount, timeout)` — synchronous blocking poll
- `watch_async(...)` — async coroutine version
- `check_label(label, amount)` — single one-shot check
- `make_label(prefix)` — generates a unique timestamped label

---

### `yoomoney/cache/` — SQLiteCache & JSONCache
Local caching of operation history to reduce API calls.

```python
cache = SQLiteCache("payments.db")
cache.save(history.operations)
ops = cache.load(label="order_42")
print(cache.is_fresh(timedelta(minutes=5)))
```

Both backends share the same `BaseCache` interface:
- `save(operations)` — upsert by `operation_id`
- `load(label, from_date, till_date)` — filtered local query
- `clear()` — wipe all cached data
- `is_fresh(max_age)` — check if cache is recent enough

---

### `yoomoney/webhook/` — Flask & FastAPI notification endpoints
Ready-to-use handlers for YooMoney HTTP notifications with SHA-1 signature
verification.

```python
# Flask
@app.route("/", methods=["POST"])
def notify():
    return flask_webhook(secret=SECRET, on_payment=handle)

# FastAPI
@app.post("/")
async def notify(request: Request):
    return await fastapi_webhook(request=request, secret=SECRET, on_payment=handle)
```

Flask and FastAPI are optional dependencies — not required for core usage.

---

### `yoomoney/cli.py` — CLI tool
A `yoomoney` console command is registered via `[project.scripts]`.

```shell
yoomoney account
yoomoney balance
yoomoney history --records 10 --label order_42
yoomoney details --id <operation_id>
yoomoney watch --label order_42 --amount 500 --timeout 300
yoomoney make-label --prefix order
```

Token is read from `--token` flag or `YOOMONEY_TOKEN` environment variable.

---

## pyproject.toml changes
- Version bumped: `2.0.0` → `2.1.0`
- Added `[project.optional-dependencies]`: `flask`, `fastapi`, `all`
- Added `[project.scripts]`: `yoomoney = "yoomoney.cli:main"`
- Updated `keywords` and `description`

## Files changed
```
yoomoney/
  checker/
    __init__.py         (new)
    checker.py          (new)
  cache/
    __init__.py         (new)
    cache.py            (new)
  webhook/
    __init__.py         (new)
    webhook.py          (new)
  cli.py                (new)
  __init__.py           (updated — new exports added)
examples/
  payment_checker.py    (new)
  cache_history.py      (new)
  webhook_server.py     (new)
pyproject.toml          (updated)
README.rst              (updated)
README_RU.rst           (updated)
requirements.txt        (new)
requirements-flask.txt  (new)
requirements-fastapi.txt(new)
```

## Tested
- PaymentChecker: label generation, SQLiteCache, JSONCache, signature verification
- Flask webhook: confirmed working with real YooMoney test notification
- CLI: all subcommands work with live token
