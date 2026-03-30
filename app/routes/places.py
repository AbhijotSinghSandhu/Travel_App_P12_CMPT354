from flask import render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection


def register_place_routes(app):
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