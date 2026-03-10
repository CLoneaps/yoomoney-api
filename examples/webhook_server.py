"""Example: receive YooMoney payment notifications via webhook.

Flask version
-------------
Run with::

    pip install flask
    python examples/webhook_server.py

FastAPI version
---------------
Run with::

    pip install fastapi uvicorn python-multipart
    uvicorn examples.webhook_server:fastapi_app

Then configure your YooMoney notification URL to point to
http://your-server/yoomoney/notify
"""

from yoomoney.webhook import Notification

SECRET = "YOUR_NOTIFICATION_SECRET"


def handle_payment(notification: Notification) -> None:
    """Called when a valid payment notification arrives."""
    print("Payment received!")
    print(f"  operation_id : {notification.operation_id}")
    print(f"  amount       : {notification.amount}")
    print(f"  label        : {notification.label}")
    print(f"  sender       : {notification.sender}")


# Flask
try:
    from flask import Flask

    from yoomoney.webhook import flask_webhook

    flask_app = Flask(__name__)

    @flask_app.route("/yoomoney/notify", methods=["POST"])
    def flask_notify():  # type: ignore[return]
        return flask_webhook(secret=SECRET, on_payment=handle_payment)

except ImportError:
    flask_app = None  # type: ignore[assignment]
    print("Flask not installed — Flask example skipped")

# FastAPI
try:
    from fastapi import FastAPI, Request

    from yoomoney.webhook import fastapi_webhook

    fastapi_app = FastAPI()

    @fastapi_app.post("/yoomoney/notify")
    async def fastapi_notify(request: Request):
        return await fastapi_webhook(
            request=request,
            secret=SECRET,
            on_payment=handle_payment,
        )

except ImportError:
    fastapi_app = None  # type: ignore[assignment]
    print("FastAPI not installed — FastAPI example skipped")


if __name__ == "__main__":
    if flask_app:
        flask_app.run(port=8080, debug=True)
