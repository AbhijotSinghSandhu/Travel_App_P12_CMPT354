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

        cursor.execute("""
            SELECT r.ReviewID, r.Rating, r.Title, r.Body, r.CreatedAt, r.UpdatedAt,
                   u.UserID, u.Username, u.DisplayName
            FROM Review r
            JOIN `User` u ON r.UserID = u.UserID
            WHERE r.PlaceID = %s
            ORDER BY r.CreatedAt DESC
        """, (place_id,))
        reviews = cursor.fetchall()

        user_trip_lists = []
        if session.get("user_id"):
            cursor.execute("""
                SELECT ListID, Title
                FROM TripList
                WHERE UserID = %s
                ORDER BY CreatedAt DESC
            """, (session["user_id"],))
            user_trip_lists = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template(
            "place_detail.html",
            place=place,
            categories=categories,
            reviews=reviews,
            user_trip_lists=user_trip_lists
        )

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
    
    def update_place_avg_rating(place_id):
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE Place
            SET AvgRating = (
                SELECT COALESCE(ROUND(AVG(Rating), 1), 0.0)
                FROM Review
                WHERE PlaceID = %s
            )
            WHERE PlaceID = %s
        """, (place_id, place_id))

        connection.commit()
        cursor.close()
        connection.close()

    @app.route("/places/<int:place_id>/reviews/create", methods=["POST"])
    def create_review(place_id):
        if not session.get("user_id"):
            flash("You must be logged in to submit a review.")
            return redirect(url_for("login"))

        rating = request.form.get("rating", "").strip()
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        user_id = session["user_id"]

        try:
            rating = int(rating)
        except ValueError:
            flash("Rating must be a number between 1 and 5.")
            return redirect(url_for("place_detail", place_id=place_id))

        if rating < 1 or rating > 5:
            flash("Rating must be between 1 and 5.")
            return redirect(url_for("place_detail", place_id=place_id))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT ReviewID
            FROM Review
            WHERE UserID = %s AND PlaceID = %s
        """, (user_id, place_id))
        existing_review = cursor.fetchone()

        if existing_review:
            cursor.close()
            connection.close()
            flash("You have already reviewed this place.")
            return redirect(url_for("place_detail", place_id=place_id))

        cursor.execute("""
            INSERT INTO Review (UserID, PlaceID, Rating, Title, Body)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, place_id, rating, title, body))
        connection.commit()

        cursor.close()
        connection.close()

        update_place_avg_rating(place_id)

        flash("Review created successfully.")
        return redirect(url_for("place_detail", place_id=place_id))
    
    @app.route("/reviews/<int:review_id>/edit", methods=["GET", "POST"])
    def edit_review(review_id):
        if not session.get("user_id"):
            flash("You must be logged in to edit a review.")
            return redirect(url_for("login"))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT ReviewID, UserID, PlaceID, Rating, Title, Body
            FROM Review
            WHERE ReviewID = %s
        """, (review_id,))
        review = cursor.fetchone()

        if not review:
            cursor.close()
            connection.close()
            flash("Review not found.")
            return redirect(url_for("places"))

        if review["UserID"] != session["user_id"]:
            cursor.close()
            connection.close()
            flash("You can only edit your own reviews.")
            return redirect(url_for("place_detail", place_id=review["PlaceID"]))

        if request.method == "POST":
            rating = request.form.get("rating", "").strip()
            title = request.form.get("title", "").strip()
            body = request.form.get("body", "").strip()

            try:
                rating = int(rating)
            except ValueError:
                cursor.close()
                connection.close()
                flash("Rating must be a number between 1 and 5.")
                return redirect(url_for("edit_review", review_id=review_id))

            if rating < 1 or rating > 5:
                cursor.close()
                connection.close()
                flash("Rating must be between 1 and 5.")
                return redirect(url_for("edit_review", review_id=review_id))

            cursor.execute("""
                UPDATE Review
                SET Rating = %s, Title = %s, Body = %s, UpdatedAt = CURRENT_TIMESTAMP
                WHERE ReviewID = %s
            """, (rating, title, body, review_id))
            connection.commit()

            place_id = review["PlaceID"]

            cursor.close()
            connection.close()

            update_place_avg_rating(place_id)

            flash("Review updated successfully.")
            return redirect(url_for("place_detail", place_id=place_id))

        cursor.close()
        connection.close()

        return render_template("edit_review.html", review=review)
    
    @app.route("/reviews/<int:review_id>/delete", methods=["POST"])
    def delete_review(review_id):
        if not session.get("user_id"):
            flash("You must be logged in to delete a review.")
            return redirect(url_for("login"))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT ReviewID, UserID, PlaceID
            FROM Review
            WHERE ReviewID = %s
        """, (review_id,))
        review = cursor.fetchone()

        if not review:
            cursor.close()
            connection.close()
            flash("Review not found.")
            return redirect(url_for("places"))

        if review["UserID"] != session["user_id"]:
            cursor.close()
            connection.close()
            flash("You can only delete your own reviews.")
            return redirect(url_for("place_detail", place_id=review["PlaceID"]))

        place_id = review["PlaceID"]

        cursor.execute("DELETE FROM Review WHERE ReviewID = %s", (review_id,))
        connection.commit()

        cursor.close()
        connection.close()

        update_place_avg_rating(place_id)

        flash("Review deleted successfully.")
        return redirect(url_for("place_detail", place_id=place_id))
    
    @app.route("/lists")
    def my_lists():
        if not session.get("user_id"):
            flash("You must be logged in to view your trip lists.")
            return redirect(url_for("login"))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT ListID, Title, Description, IsPublic, CreatedAt
            FROM TripList
            WHERE UserID = %s
            ORDER BY CreatedAt DESC
        """, (session["user_id"],))
        trip_lists = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template("trip_lists.html", trip_lists=trip_lists)

    @app.route("/lists/create", methods=["GET", "POST"])
    def create_list():
        if not session.get("user_id"):
            flash("You must be logged in to create a trip list.")
            return redirect(url_for("login"))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            is_public = 1 if request.form.get("is_public") == "on" else 0

            if not title:
                flash("Title is required.")
                return redirect(url_for("create_list"))

            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO TripList (UserID, Title, Description, IsPublic)
                VALUES (%s, %s, %s, %s)
            """, (session["user_id"], title, description, is_public))
            connection.commit()

            cursor.close()
            connection.close()

            flash("Trip list created successfully.")
            return redirect(url_for("my_lists"))

        return render_template("create_list.html")
    
    @app.route("/lists/<int:list_id>")
    def trip_list_detail(list_id):
        if not session.get("user_id"):
            flash("You must be logged in to view trip lists.")
            return redirect(url_for("login"))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT ListID, UserID, Title, Description, IsPublic, CreatedAt
            FROM TripList
            WHERE ListID = %s
        """, (list_id,))
        trip_list = cursor.fetchone()

        if not trip_list:
            cursor.close()
            connection.close()
            flash("Trip list not found.")
            return redirect(url_for("my_lists"))
        
    @app.route("/places/<int:place_id>/add-to-list", methods=["POST"])
    def add_place_to_list(place_id):
        if not session.get("user_id"):
            flash("You must be logged in to add a place to a trip list.")
            return redirect(url_for("login"))

        list_id = request.form.get("list_id", "").strip()
        note = request.form.get("note", "").strip()

        if not list_id:
            flash("Please select a trip list.")
            return redirect(url_for("place_detail", place_id=place_id))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT ListID, UserID
            FROM TripList
            WHERE ListID = %s
        """, (list_id,))
        trip_list = cursor.fetchone()

        if not trip_list or trip_list["UserID"] != session["user_id"]:
            cursor.close()
            connection.close()
            flash("Invalid trip list selection.")
            return redirect(url_for("place_detail", place_id=place_id))

        cursor.execute("""
            SELECT ListID, PlaceID
            FROM TripListItem
            WHERE ListID = %s AND PlaceID = %s
        """, (list_id, place_id))
        existing_item = cursor.fetchone()

        if existing_item:
            cursor.close()
            connection.close()
            flash("This place is already in the selected trip list.")
            return redirect(url_for("place_detail", place_id=place_id))

        cursor.execute("""
            SELECT COALESCE(MAX(Position), 0) + 1 AS next_position
            FROM TripListItem
            WHERE ListID = %s
        """, (list_id,))
        next_position_row = cursor.fetchone()
        next_position = next_position_row["next_position"]

        cursor.execute("""
            INSERT INTO TripListItem (ListID, PlaceID, Position, Note)
            VALUES (%s, %s, %s, %s)
        """, (list_id, place_id, next_position, note))
        connection.commit()

        cursor.close()
        connection.close()

        flash("Place added to trip list.")
        return redirect(url_for("place_detail", place_id=place_id))
    
    @app.route("/lists/<int:list_id>/remove/<int:place_id>", methods=["POST"])
    def remove_place_from_list(list_id, place_id):
        if not session.get("user_id"):
            flash("You must be logged in to modify a trip list.")
            return redirect(url_for("login"))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT ListID, UserID
            FROM TripList
            WHERE ListID = %s
        """, (list_id,))
        trip_list = cursor.fetchone()

        if not trip_list or trip_list["UserID"] != session["user_id"]:
            cursor.close()
            connection.close()
            flash("You can only modify your own trip lists.")
            return redirect(url_for("my_lists"))

        cursor.execute("""
            DELETE FROM TripListItem
            WHERE ListID = %s AND PlaceID = %s
        """, (list_id, place_id))
        connection.commit()

        cursor.close()
        connection.close()

        flash("Place removed from trip list.")
        return redirect(url_for("trip_list_detail", list_id=list_id))

    
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