from yoomoney import Authorize

Authorize(
    client_id="TEST_CLIENT_ID",
    redirect_uri="https://example.com/callback",
    client_secret="TEST_CLIENT_SECRET",
    scope=[
        "account-info",
        "operation-history",
        "operation-details",
        "incoming-transfers",
        "payment-p2p",
        "payment-shop",
    ],
)
