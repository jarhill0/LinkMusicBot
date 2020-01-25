from flask import (
    Flask,
    jsonify,
    request,
)
from pawt import Telegram
from pawt.models import Update
from config import secrets

from handler import handle_update

TOKEN = secrets["telegram_token"]
PATH = secrets.get("webhook_path", "").lstrip('/')
TELEGRAM = Telegram(TOKEN)

app = Flask(__name__)


def log(thing):
    try:
        with open('/home/joe/LinkMusicBot/messages.log', 'a') as f:
            f.write(thing)
            f.write('\n')
    except IOError:
        pass


@app.before_first_request
def set_up():
    print(request.url_root)
    # set_webhooks()


def set_webhooks():
    hostname = request.url_root
    full_path = hostname + PATH
    TELEGRAM.post(path="setWebhook", data={"url": full_path})


@app.route("/" + PATH, methods=["POST"])
def handle():
    update = Update(TELEGRAM, request.get_json())
    response = handle_update(update)
    return jsonify(response)
