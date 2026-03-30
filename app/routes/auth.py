from flask import render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection
from app.auth import hash_password, verify_password


def register_auth_routes(app):
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