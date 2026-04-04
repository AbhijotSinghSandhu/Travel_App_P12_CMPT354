from flask import render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection

def update_place_avg_rating(place_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE Place
        SET AvgRating = (
            SELECT COALESCE(ROUND(AVG(Rating), 1), 0.0)
            FROM Review
            WHERE PlaceID = %s AND IsVisible = TRUE
        )
        WHERE PlaceID = %s
    """, (place_id, place_id))

    connection.commit()
    cursor.close()
    connection.close()

def register_review_routes(app):
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
