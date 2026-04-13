from flask import render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection


def register_trip_list_routes(app):
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

        if trip_list["UserID"] != session["user_id"]:
            cursor.close()
            connection.close()
            flash("You can only view your own trip lists right now.")
            return redirect(url_for("my_lists"))

        cursor.execute("""
            SELECT tli.ListID, tli.PlaceID, tli.Position, tli.Note,
                   p.Name, p.Address, p.AvgRating
            FROM TripListItem tli
            JOIN Place p ON tli.PlaceID = p.PlaceID
            WHERE tli.ListID = %s
            ORDER BY tli.Position ASC
        """, (list_id,))
        items = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template("trip_list_detail.html", trip_list=trip_list, items=items)

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

        try:
            cursor.execute("""
                SELECT ListID, UserID
                FROM TripList
                WHERE ListID = %s
            """, (list_id,))
            trip_list = cursor.fetchone()

            if not trip_list or trip_list["UserID"] != session["user_id"]:
                flash("Invalid trip list selection.")
                return redirect(url_for("place_detail", place_id=place_id))

            cursor.execute("""
                SELECT ListID, PlaceID
                FROM TripListItem
                WHERE ListID = %s AND PlaceID = %s
            """, (list_id, place_id))
            existing_item = cursor.fetchone()

            if existing_item:
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

            flash("Place added to trip list.")

        except Exception:
            connection.rollback()
            flash("This place is already in the selected trip list.")

        finally:
            cursor.close()
            connection.close()

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