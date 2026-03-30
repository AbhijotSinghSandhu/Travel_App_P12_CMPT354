from flask import Flask, render_template, request, redirect, url_for, flash, session

from config import Config
from app.db import get_db_connection
from app.auth import hash_password, verify_password


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

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form["username"]
            email = request.form["email"]
            display_name = request.form["display_name"]
            password = request.form["password"]
            password_hash = hash_password(password)

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                "SELECT UserID FROM `User` WHERE Username = %s OR Email = %s",
                (username, email)
            )
            existing_user = cursor.fetchone()

            if existing_user:
                cursor.close()
                connection.close()
                flash("Username or email already exists.")
                return redirect(url_for("register"))

            cursor.execute(
                """
                INSERT INTO `User` (Username, Email, PasswordHash, DisplayName, Role)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (username, email, password_hash, display_name, "tourist")
            )
            connection.commit()

            cursor.close()
            connection.close()

            flash("Registration successful. Please log in.")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form["email"]
            password = request.form["password"]

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                "SELECT UserID, Username, Email, PasswordHash, DisplayName, Role FROM `User` WHERE Email = %s",
                (email,)
            )
            user = cursor.fetchone()

            cursor.close()
            connection.close()

            if user and verify_password(password, user["PasswordHash"]):
                session["user_id"] = user["UserID"]
                session["username"] = user["Username"]
                session["role"] = user["Role"]
                flash("Login successful.")
                return redirect(url_for("home"))

            flash("Invalid email or password.")
            return redirect(url_for("login"))

        return render_template("login.html")
    
    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.")
        return redirect(url_for("login"))
    
    @app.route("/places")
    def places():
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT PlaceID, Name, Address, AvgRating, IsActive
            FROM Place
            WHERE IsActive = TRUE
            ORDER BY Name ASC
        """)
        places = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template("places.html", places=places)
    
    @app.route("/places/<int:place_id>")
    def place_detail(place_id):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT PlaceID, Name, Description, Address, Hours, ContactInfo, Website, AvgRating, IsActive
            FROM Place
            WHERE PlaceID = %s AND IsActive = TRUE
        """, (place_id,))
        place = cursor.fetchone()

        if not place:
            cursor.close()
            connection.close()
            flash("Place not found.")
            return redirect(url_for("places"))

        cursor.execute("""
            SELECT c.TagName
            FROM Category c
            JOIN PlaceCategory pc ON c.CategoryID = pc.CategoryID
            WHERE pc.PlaceID = %s
            ORDER BY c.TagName ASC
        """, (place_id,))
        categories = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template("place_detail.html", place=place, categories=categories)

    @app.route("/places")
    def places():
        search = request.args.get("search", "").strip()
        category = request.args.get("category", "").strip()

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        category_query = """
            SELECT TagName
            FROM Category
            ORDER BY TagName ASC
        """
        cursor.execute(category_query)
        categories = cursor.fetchall()

        places_query = """
            SELECT DISTINCT p.PlaceID, p.Name, p.Address, p.AvgRating, p.IsActive
            FROM Place p
            LEFT JOIN PlaceCategory pc ON p.PlaceID = pc.PlaceID
            LEFT JOIN Category c ON pc.CategoryID = c.CategoryID
            WHERE p.IsActive = TRUE
        """
        params = []

        if search:
            places_query += " AND p.Name LIKE %s"
            params.append(f"%{search}%")

        if category:
            places_query += " AND c.TagName = %s"
            params.append(category)

        places_query += " ORDER BY p.Name ASC"

        cursor.execute(places_query, tuple(params))
        places = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template(
            "places.html",
            places=places,
            categories=categories,
            selected_category=category,
            search_query=search
        )
    
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