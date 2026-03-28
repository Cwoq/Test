from flask import Flask

from src.db.database import init_db

from .routes import bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-key-change-in-production"

    init_db()
    app.register_blueprint(bp)

    return app


def main():
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
