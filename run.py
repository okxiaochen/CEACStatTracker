from tracker.app import app
from tracker.route import mod as router
from tracker.route import scheduler

app.register_blueprint(router)

if __name__ == '__main__':
    scheduler.init_app(app)
    scheduler.start()
    app.run()
