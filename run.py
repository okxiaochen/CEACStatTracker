from app.app import app
from app.route import mod as router

app.register_blueprint(router)


if __name__ == '__main__':

    app.run()
