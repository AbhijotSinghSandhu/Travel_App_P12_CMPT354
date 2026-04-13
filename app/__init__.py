from flask import Flask
from config import Config
from app.db import get_db_connection
from app.db_triggers import create_triggers


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    with app.app_context():
        try:
            connection = get_db_connection()
            create_triggers(connection)
            connection.close()
            print("Database connection successful.")
        except Exception as e:
            print(f"Database connection failed: {e}")

    from app.routes.main import register_main_routes
    from app.routes.auth import register_auth_routes
    from app.routes.places import register_place_routes
    from app.routes.reviews import register_review_routes
    from app.routes.trip_lists import register_trip_list_routes
    from app.routes.api import register_api_routes

    register_main_routes(app)
    register_auth_routes(app)
    register_place_routes(app)
    register_review_routes(app)
    register_trip_list_routes(app)
    register_api_routes(app)

    return app
