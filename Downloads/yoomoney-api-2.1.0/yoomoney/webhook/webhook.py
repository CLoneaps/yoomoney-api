"""Webhook helpers for YooMoney payment notifications.

YooMoney can POST a form-encoded notification to your server when a payment
arrives.  This module provides ready-to-use endpoint factories for both
**Flask** and **FastAPI**.

Flask example::

    from flask import Flask
    from yoomoney.webhook import flask_webhook

    app = Flask(__name__)

    @app.route("/yoomoney/notify", methods=["POST"])
    def notify():
        return flask_webhook(
            secret="MY_SECRET",
            on_payment=lambda n: print(f"Got {n.amount} from {n.sender}"),
        )

FastAPI example::

    from fastapi import FastAPI, Request
    from yoomoney.webhook import fastapi_webhook

    app = FastAPI()

    @app.post("/yoomoney/notify")
    async def notify(request: Request):
        return await fastapi_webhook(
            request=request,
            secret="MY_SECRET",
            on_payment=lambda n: print(f"Got {n.amount}"),
        )
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)



class Notification(BaseModel):
    """Parsed YooMoney HTTP-notification payload.

    Reference:
    https://yoomoney.ru/docs/payment-buttons/using-api/notifications
    """

    notification_type: str
    operation_id: str
    amount: float
    currency: str = "643"
    datetime: str
    sender: str = ""
    codepro: bool = False
    label: str = ""
    sha1_hash: str = Field(alias="sha1_hash", default="")

    model_config = {"populate_by_name": True}

    def verify_signature(self, secret: str) -> bool:
        """Return ``True`` if the SHA-1 signature matches *secret*.

        The signature is built from::

            notification_type&operation_id&amount&currency&datetime
            &sender&codepro&secret&label

        joined with ``&`` (no spaces).
        """
        codepro_str = "true" if self.codepro else "false"
        raw = "&".join(
            [
                self.notification_type,
                self.operation_id,
                str(self.amount),
                self.currency,
                self.datetime,
                self.sender,
                codepro_str,
                secret,
                self.label,
            ]
        )
        expected = hashlib.sha1(raw.encode()).hexdigest()  # noqa: S324
        return expected == self.sha1_hash


def flask_webhook(
    secret: str,
    on_payment: Callable[[Notification], Any],
    *,
    verify: bool = True,
) -> Any:
    """Handle a YooMoney notification inside a **Flask** view function.

    Call this directly from your route handler and return its result::

        @app.route("/notify", methods=["POST"])
        def notify():
            return flask_webhook(secret="...", on_payment=handle)

    Parameters
    ----------
    secret:
        The notification secret configured in your YooMoney settings.
    on_payment:
        Callable invoked with a :class:`Notification` when a valid payment
        notification arrives.
    verify:
        If ``True`` (default), reject notifications with invalid signatures.

    Returns
    -------
    flask.Response
        200 OK on success, 400 on bad signature.
    """
    try:
        from flask import request, make_response  # type: ignore[import-untyped]
    except ImportError as exc:
        msg = "Flask is not installed. Run: pip install flask"
        raise ImportError(msg) from exc

    form: dict[str, Any] = request.form.to_dict()
    notification = Notification.model_validate(form)

    if verify and not notification.verify_signature(secret):
        logger.warning("Invalid YooMoney signature from %s", request.remote_addr)
        return make_response("Bad signature", 400)

    logger.info(
        "YooMoney payment: operation_id=%s, amount=%s, label=%r",
        notification.operation_id,
        notification.amount,
        notification.label,
    )
    on_payment(notification)
    return make_response("OK", 200)


async def fastapi_webhook(
    request: Any,
    secret: str,
    on_payment: Callable[[Notification], Any],
    *,
    verify: bool = True,
) -> Any:
    """Handle a YooMoney notification inside a **FastAPI** route.

    ::

        @app.post("/notify")
        async def notify(request: Request):
            return await fastapi_webhook(request, secret="...", on_payment=handle)

    Parameters
    ----------
    request:
        The ``fastapi.Request`` object from your route handler.
    secret:
        The notification secret configured in your YooMoney settings.
    on_payment:
        Callable (sync or async) invoked with :class:`Notification`.
    verify:
        If ``True`` (default), reject notifications with invalid signatures.

    Returns
    -------
    fastapi.responses.PlainTextResponse
    """
    try:
        from fastapi.responses import PlainTextResponse  # type: ignore[import-untyped]
    except ImportError as exc:
        msg = "FastAPI is not installed. Run: pip install fastapi"
        raise ImportError(msg) from exc

    import inspect

    form = await request.form()
    form_dict: dict[str, Any] = dict(form)
    notification = Notification.model_validate(form_dict)

    if verify and not notification.verify_signature(secret):
        logger.warning("Invalid YooMoney signature")
        return PlainTextResponse("Bad signature", status_code=400)

    logger.info(
        "YooMoney payment: operation_id=%s, amount=%s, label=%r",
        notification.operation_id,
        notification.amount,
        notification.label,
    )

    result = on_payment(notification)
    if inspect.isawaitable(result):
        await result

    return PlainTextResponse("OK", status_code=200)
