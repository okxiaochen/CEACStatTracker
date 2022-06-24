from flask import Flask
from flask_mongoengine import MongoEngine

from tracker.const import CONFIG

app = Flask(__name__)
app.secret_key = "eawfopawjfoawe"
app.config['MONGODB_SETTINGS'] = {
    'host': CONFIG["mongoDBUri"],
    'connect': False,
}
db = MongoEngine(app)
app.debug = CONFIG["debug"]
