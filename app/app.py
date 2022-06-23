from flask import Flask
from flask_mongoengine import MongoEngine

app = Flask(__name__)
app.secret_key = "eawfopawjfoawe"
app.config['MONGODB_SETTINGS'] = {
    'host': 'mongodb://localhost/CEACStateTracker',
    'connect': False,
}
db = MongoEngine(app)

from app.route import scheduler

scheduler.init_app(app)
scheduler.start()
