from flask import Flask
from flask_mongoengine import MongoEngine

from tracker.const import CONFIG

app = Flask(__name__)
app.secret_key = "eawfopawjfoawe"

app.config['MONGODB_SETTINGS'] = {
    "host": CONFIG["mongo_host"],
    "port": CONFIG["mongo_port"],
    "db": CONFIG["mongo_db"],
    "username": CONFIG["mongo_user"],
    "password": CONFIG["mongo_password"],
    "connect": False,
}

db = MongoEngine(app)
app.debug = CONFIG["debug"]
