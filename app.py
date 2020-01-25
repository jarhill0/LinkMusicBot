from flask import (
    Flask,
    jsonify,
    request,
)
from pawt import Telegram
from config import secrets

TOKEN = secrets["telegram_token"]
PATH = secrets.get("webhook_path", "").lstrip('/')

TELEGRAM = Telegram(TOKEN)

app = Flask(__name__)


@app.before_first_request
def set_up():
    print(request.url_root)
    set_webhooks()


def set_webhooks():
    hostname = request.url_root
    full_path = hostname + PATH
    TELEGRAM.post(path="setWebhook", data={"url": full_path})


@app.route("/" + PATH, methods=["GET", "POST"])
def handle():
    try:
        with open('/home/joe/LinkMusicBot/requests.log', 'a') as f:
            f.write(request.get_data(as_text=True))
    except IOError:
        pass
    return jsonify({'this is a dict': 23, 'with some stuff': [1, 2, 3, "seven", {1: 2, 3: 4, 5: [6, 7, 8]}]})
