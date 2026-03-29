from flask import Flask, render_template
from config import Config
from app.db import get_db_connection


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    with app.app_context():
        try:
            connection = get_db_connection()
            connection.close()
            print("Database connection successful.")
        except Exception as e:
            print(f"Database connection failed: {e}")

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/health")
    def health():
        try:
            connection = get_db_connection()
            connection.close()
            return {"status": "ok", "database": "connected"}
        except Exception as e:
            return {"status": "error", "database": str(e)}, 500

    @app.route("/debug/places")
    def debug_places():
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT PlaceID, Name, AvgRating, IsActive FROM Place")
        places = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template("debug_places.html", places=places)

    @app.route("/debug/users")
    def debug_users():
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT UserID, Username, Email, Role FROM `User`")
        users = cursor.fetchall()

        cursor.close()
        connection.close()

        return {"users": users}

    return app