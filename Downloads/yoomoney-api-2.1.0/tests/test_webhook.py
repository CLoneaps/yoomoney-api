from flask import Flask
from yoomoney.webhook import flask_webhook, Notification

app = Flask(__name__)
SECRET = "NEW_SECREN_TOKEN"

def on_payment(n: Notification) -> None:
    print(f"✓ Платёж получен!")
    print(f"  Сумма:        {n.amount} ₽")
    print(f"  Label:        {n.label}")
    print(f"  Operation ID: {n.operation_id}")
    print(f"  Отправитель:  {n.sender}")

@app.route("/", methods=["POST"])
def notify():
    return flask_webhook(secret=SECRET, on_payment=on_payment)

if __name__ == "__main__":
    print("Сервер запущен на http://localhost:5000/notify")
    app.run(port=5000, debug=True)