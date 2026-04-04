from flask import render_template
from app.db import get_db_connection


def register_main_routes(app):
    @app.route("/")
    def home():
        return render_template("spa.html")

    @app.route("/health")
    def health():
        try:
            connection = get_db_connection()
            connection.close()
            return {"status": "ok", "database": "connected"}
        except Exception as e:
            return {"status": "error", "database": str(e)}, 500
