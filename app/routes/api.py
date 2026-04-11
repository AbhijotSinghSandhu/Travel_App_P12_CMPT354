from flask import jsonify, request, session

from app.auth import hash_password, verify_password
from app.db import get_db_connection
from app.routes.reviews import update_place_avg_rating


VALID_ROLES = {"tourist", "business_owner", "admin"}
MODERATION_STATUSES = {"pending", "approved", "rejected"}


def json_error(message, status_code=400):
    return jsonify({"error": message}), status_code


def get_json_payload():
    return request.get_json(silent=True) or {}


def current_user_payload():
    if not session.get("user_id"):
        return None

    return {
        "user_id": session["user_id"],
        "username": session["username"],
        "display_name": session.get("display_name", session["username"]),
        "role": session["role"],
    }


def is_admin():
    return session.get("role") == "admin"


def is_business_owner():
    return session.get("role") == "business_owner"


def require_login():
    if not session.get("user_id"):
        return json_error("You must be logged in to continue.", 401)
    return None


def require_role(*roles):
    if not session.get("user_id"):
        return json_error("You must be logged in to continue.", 401)
    if session.get("role") not in roles:
        return json_error("You do not have permission for this action.", 403)
    return None


def can_manage_place(place_row):
    if not session.get("user_id"):
        return False
    if is_admin():
        return True
    return (
        session.get("role") == "business_owner"
        and place_row.get("ClaimedByUserID") == session["user_id"]
    )


def parse_category_ids(raw_value):
    category_ids = []
    for value in raw_value or []:
        try:
            category_ids.append(int(value))
        except (TypeError, ValueError):
            continue
    return sorted(set(category_ids))


def normalize_trip_list_positions(connection, list_id):
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT PlaceID
        FROM TripListItem
        WHERE ListID = %s
        ORDER BY Position ASC, PlaceID ASC
        """,
        (list_id,),
    )
    items = cursor.fetchall()

    for index, item in enumerate(items, start=1):
        cursor.execute(
            """
            UPDATE TripListItem
            SET Position = %s
            WHERE ListID = %s AND PlaceID = %s
            """,
            (index, list_id, item["PlaceID"]),
        )

    connection.commit()
    cursor.close()


def fetch_categories(cursor):
    cursor.execute(
        """
        SELECT CategoryID, TagName
        FROM Category
        ORDER BY TagName ASC
        """
    )
    return cursor.fetchall()


def fetch_public_lists(cursor):
    cursor.execute(
        """
        SELECT tl.ListID, tl.Title, tl.Description, tl.IsPublic, tl.CreatedAt,
               u.DisplayName, COUNT(tli.PlaceID) AS ItemCount
        FROM TripList tl
        JOIN `User` u ON u.UserID = tl.UserID
        LEFT JOIN TripListItem tli ON tli.ListID = tl.ListID
        WHERE tl.IsPublic = TRUE
        GROUP BY tl.ListID, tl.Title, tl.Description, tl.IsPublic, tl.CreatedAt, u.DisplayName
        ORDER BY tl.CreatedAt DESC
        """
    )
    return cursor.fetchall()


def fetch_admin_overview(cursor):
    cursor.execute(
        """
        SELECT c.ClaimID, c.Status, c.Message, c.CreatedAt,
               p.PlaceID, p.Name AS PlaceName,
               u.UserID, u.DisplayName, u.Email
        FROM PlaceClaimRequest c
        JOIN Place p ON p.PlaceID = c.PlaceID
        JOIN `User` u ON u.UserID = c.UserID
        ORDER BY
            CASE WHEN c.Status = 'pending' THEN 0 ELSE 1 END,
            c.CreatedAt DESC
        """
    )
    claims = cursor.fetchall()

    cursor.execute(
        """
        SELECT ph.PhotoID, ph.PhotoURL, ph.Caption, ph.Status, ph.CreatedAt,
               p.PlaceID, p.Name AS PlaceName,
               u.DisplayName
        FROM PlacePhoto ph
        JOIN Place p ON p.PlaceID = ph.PlaceID
        JOIN `User` u ON u.UserID = ph.UserID
        ORDER BY
            CASE WHEN ph.Status = 'pending' THEN 0 ELSE 1 END,
            ph.CreatedAt DESC
        """
    )
    photos = cursor.fetchall()

    cursor.execute(
        """
        SELECT r.ReviewID, r.Rating, r.Title, r.Body, r.IsVisible, r.CreatedAt,
               p.PlaceID, p.Name AS PlaceName,
               u.DisplayName
        FROM Review r
        JOIN Place p ON p.PlaceID = r.PlaceID
        JOIN `User` u ON u.UserID = r.UserID
        ORDER BY r.CreatedAt DESC
        LIMIT 50
        """
    )
    reviews = cursor.fetchall()

    cursor.execute(
        """
        SELECT PlaceID, Name, Address, IsActive, ClaimedByUserID
        FROM Place
        ORDER BY Name ASC
        """
    )
    places = cursor.fetchall()

    return {
        "claim_requests": claims,
        "photos": photos,
        "reviews": reviews,
        "places": places,
    }


def fetch_places_payload(search="", category="", include_inactive=False):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    categories = fetch_categories(cursor)

    places_query = """
        SELECT DISTINCT p.PlaceID, p.Name, p.Description, p.Address, p.Hours,
               p.ContactInfo, p.Website, p.AvgRating, p.IsActive, p.ClaimedByUserID
        FROM Place p
        LEFT JOIN PlaceCategory pc ON p.PlaceID = pc.PlaceID
        LEFT JOIN Category c ON pc.CategoryID = c.CategoryID
        WHERE 1 = 1
    """
    params = []

    if not include_inactive:
        places_query += " AND p.IsActive = TRUE"

    if search:
        places_query += " AND p.Name LIKE %s"
        params.append(f"%{search}%")

    if category:
        places_query += " AND c.TagName = %s"
        params.append(category)

    places_query += " ORDER BY p.Name ASC"

    cursor.execute(places_query, tuple(params))
    places = cursor.fetchall()
    public_lists = fetch_public_lists(cursor)
    admin_overview = fetch_admin_overview(cursor) if is_admin() else None

    cursor.close()
    connection.close()

    return {
        "places": places,
        "categories": categories,
        "filters": {"search": search, "category": category},
        "public_lists": public_lists,
        "admin_overview": admin_overview,
    }


def fetch_place_detail_payload(place_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT p.PlaceID, p.Name, p.Description, p.Address, p.Hours, p.ContactInfo,
               p.Website, p.AvgRating, p.IsActive, p.CreatedByUserID, p.ClaimedByUserID,
               creator.DisplayName AS CreatedByName,
               owner.DisplayName AS ClaimedByName
        FROM Place p
        LEFT JOIN `User` creator ON creator.UserID = p.CreatedByUserID
        LEFT JOIN `User` owner ON owner.UserID = p.ClaimedByUserID
        WHERE p.PlaceID = %s
        """,
        (place_id,),
    )
    place = cursor.fetchone()

    if not place:
        cursor.close()
        connection.close()
        return None

    if not place["IsActive"] and not is_admin() and place["ClaimedByUserID"] != session.get("user_id"):
        cursor.close()
        connection.close()
        return None

    cursor.execute(
        """
        SELECT c.CategoryID, c.TagName
        FROM Category c
        JOIN PlaceCategory pc ON c.CategoryID = pc.CategoryID
        WHERE pc.PlaceID = %s
        ORDER BY c.TagName ASC
        """,
        (place_id,),
    )
    categories = cursor.fetchall()

    reviews_query = """
        SELECT r.ReviewID, r.Rating, r.Title, r.Body, r.CreatedAt, r.UpdatedAt, r.IsVisible,
               u.UserID, u.Username, u.DisplayName
        FROM Review r
        JOIN `User` u ON r.UserID = u.UserID
        WHERE r.PlaceID = %s
    """
    if not is_admin():
        reviews_query += " AND r.IsVisible = TRUE"
    reviews_query += " ORDER BY r.CreatedAt DESC"
    cursor.execute(reviews_query, (place_id,))
    reviews = cursor.fetchall()

    photos_query = """
        SELECT ph.PhotoID, ph.PhotoURL, ph.Caption, ph.Status, ph.CreatedAt,
               u.DisplayName
        FROM PlacePhoto ph
        JOIN `User` u ON u.UserID = ph.UserID
        WHERE ph.PlaceID = %s
    """
    if not is_admin():
        photos_query += " AND ph.Status = 'approved'"
    photos_query += " ORDER BY ph.CreatedAt DESC"
    cursor.execute(photos_query, (place_id,))
    photos = cursor.fetchall()

    user_trip_lists = []
    if session.get("user_id"):
        cursor.execute(
            """
            SELECT ListID, Title
            FROM TripList
            WHERE UserID = %s
            ORDER BY CreatedAt DESC
            """,
            (session["user_id"],),
        )
        user_trip_lists = cursor.fetchall()

    claim_request = None
    if session.get("user_id"):
        cursor.execute(
            """
            SELECT ClaimID, Status, Message, CreatedAt
            FROM PlaceClaimRequest
            WHERE PlaceID = %s AND UserID = %s
            ORDER BY CreatedAt DESC
            LIMIT 1
            """,
            (place_id, session["user_id"]),
        )
        claim_request = cursor.fetchone()

    all_categories = fetch_categories(cursor)

    cursor.close()
    connection.close()

    return {
        "place": place,
        "categories": categories,
        "all_categories": all_categories,
        "reviews": reviews,
        "photos": photos,
        "user_trip_lists": user_trip_lists,
        "claim_request": claim_request,
        "permissions": {
            "can_manage_place": can_manage_place(place),
            "can_claim_place": (
                bool(session.get("user_id"))
                and is_business_owner()
                and not place["ClaimedByUserID"]
            ),
            "is_admin": is_admin(),
        },
    }


def register_api_routes(app):
    @app.get("/api/health")
    def api_health():
        try:
            connection = get_db_connection()
            connection.close()
            return jsonify({"status": "ok", "database": "connected"})
        except Exception as exc:
            return jsonify({"status": "error", "database": str(exc)}), 500

    @app.get("/api/session")
    def api_session():
        return jsonify({"user": current_user_payload()})

    @app.post("/api/register")
    def api_register():
        payload = get_json_payload()
        username = payload.get("username", "").strip()
        email = payload.get("email", "").strip()
        display_name = payload.get("display_name", "").strip()
        password = payload.get("password", "")
        role = payload.get("role", "tourist").strip() or "tourist"

        if role not in VALID_ROLES or role == "admin":
            role = "tourist"

        if not username or not email or not display_name or not password:
            return json_error("All registration fields are required.")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT UserID FROM `User` WHERE Username = %s OR Email = %s",
            (username, email),
        )
        existing_user = cursor.fetchone()

        if existing_user:
            cursor.close()
            connection.close()
            return json_error("Username or email already exists.", 409)

        cursor.execute(
            """
            INSERT INTO `User` (Username, Email, PasswordHash, DisplayName, Role)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (username, email, hash_password(password), display_name, role),
        )
        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({"message": "Registration successful. Please log in."}), 201

    @app.post("/api/login")
    def api_login():
        payload = get_json_payload()
        email = payload.get("email", "").strip()
        password = payload.get("password", "")

        if not email or not password:
            return json_error("Email and password are required.")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT UserID, Username, Email, PasswordHash, DisplayName, Role
            FROM `User`
            WHERE Email = %s
            """,
            (email,),
        )
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if not user or not verify_password(password, user["PasswordHash"]):
            return json_error("Invalid email or password.", 401)

        session["user_id"] = user["UserID"]
        session["username"] = user["Username"]
        session["display_name"] = user["DisplayName"]
        session["role"] = user["Role"]

        return jsonify(
            {
                "message": "Login successful.",
                "user": {
                    "user_id": user["UserID"],
                    "username": user["Username"],
                    "display_name": user["DisplayName"],
                    "role": user["Role"],
                },
            }
        )

    @app.post("/api/logout")
    def api_logout():
        session.clear()
        return jsonify({"message": "Logged out."})

    @app.get("/api/bootstrap")
    def api_bootstrap():
        search = request.args.get("search", "").strip()
        category = request.args.get("category", "").strip()
        include_inactive = is_admin()
        payload = fetch_places_payload(search, category, include_inactive=include_inactive)
        payload["user"] = current_user_payload()
        return jsonify(payload)

    @app.get("/api/places")
    def api_places():
        search = request.args.get("search", "").strip()
        category = request.args.get("category", "").strip()
        include_inactive = is_admin()
        return jsonify(fetch_places_payload(search, category, include_inactive=include_inactive))

    @app.post("/api/places")
    def api_create_place():
        permission_error = require_role("business_owner", "admin")
        if permission_error:
            return permission_error

        payload = get_json_payload()
        name = payload.get("name", "").strip()
        address = payload.get("address", "").strip()
        description = payload.get("description", "").strip()
        hours = payload.get("hours", "").strip()
        contact_info = payload.get("contact_info", "").strip()
        website = payload.get("website", "").strip()
        category_ids = parse_category_ids(payload.get("category_ids", []))

        if not name or not address:
            return json_error("Place name and address are required.")

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO Place
            (Name, Description, Address, Hours, ContactInfo, Website, CreatedByUserID, ClaimedByUserID)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                name,
                description,
                address,
                hours,
                contact_info,
                website,
                session["user_id"],
                session["user_id"] if is_business_owner() else None,
            ),
        )
        place_id = cursor.lastrowid

        for category_id in category_ids:
            cursor.execute(
                """
                INSERT INTO PlaceCategory (PlaceID, CategoryID)
                VALUES (%s, %s)
                """,
                (place_id, category_id),
            )

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({"message": "Place created successfully.", "place_id": place_id}), 201

    @app.get("/api/places/<int:place_id>")
    def api_place_detail(place_id):
        payload = fetch_place_detail_payload(place_id)
        if not payload:
            return json_error("Place not found.", 404)

        payload["user"] = current_user_payload()
        return jsonify(payload)

    @app.put("/api/places/<int:place_id>")
    def api_update_place(place_id):
        permission_error = require_login()
        if permission_error:
            return permission_error

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT PlaceID, ClaimedByUserID
            FROM Place
            WHERE PlaceID = %s
            """,
            (place_id,),
        )
        place = cursor.fetchone()
        if not place:
            cursor.close()
            connection.close()
            return json_error("Place not found.", 404)

        if not can_manage_place(place):
            cursor.close()
            connection.close()
            return json_error("You cannot edit this place.", 403)

        payload = get_json_payload()
        name = payload.get("name", "").strip()
        address = payload.get("address", "").strip()
        description = payload.get("description", "").strip()
        hours = payload.get("hours", "").strip()
        contact_info = payload.get("contact_info", "").strip()
        website = payload.get("website", "").strip()
        category_ids = parse_category_ids(payload.get("category_ids", []))

        if not name or not address:
            cursor.close()
            connection.close()
            return json_error("Place name and address are required.")

        cursor.execute(
            """
            UPDATE Place
            SET Name = %s,
                Description = %s,
                Address = %s,
                Hours = %s,
                ContactInfo = %s,
                Website = %s
            WHERE PlaceID = %s
            """,
            (name, description, address, hours, contact_info, website, place_id),
        )

        cursor.execute("DELETE FROM PlaceCategory WHERE PlaceID = %s", (place_id,))
        for category_id in category_ids:
            cursor.execute(
                "INSERT INTO PlaceCategory (PlaceID, CategoryID) VALUES (%s, %s)",
                (place_id, category_id),
            )

        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({"message": "Place updated successfully."})

    @app.put("/api/admin/places/<int:place_id>/status")
    def api_admin_place_status(place_id):
        permission_error = require_role("admin")
        if permission_error:
            return permission_error

        payload = get_json_payload()
        is_active = bool(payload.get("is_active"))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT PlaceID FROM Place WHERE PlaceID = %s",
            (place_id,),
        )
        place = cursor.fetchone()

        if not place:
            cursor.close()
            connection.close()
            return json_error("Place not found.", 404)
        
        cursor.execute(
            """
            UPDATE Place
            SET IsActive = %s
            WHERE PlaceID = %s
            """,
            (is_active, place_id),
        )
        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({"message": "Listing moderation updated."})

    @app.post("/api/places/<int:place_id>/claim-requests")
    def api_claim_place(place_id):
        permission_error = require_role("business_owner")
        if permission_error:
            return permission_error

        payload = get_json_payload()
        message = payload.get("message", "").strip()

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT PlaceID, ClaimedByUserID
            FROM Place
            WHERE PlaceID = %s
            """,
            (place_id,),
        )
        place = cursor.fetchone()
        if not place:
            cursor.close()
            connection.close()
            return json_error("Place not found.", 404)

        if place["ClaimedByUserID"]:
            cursor.close()
            connection.close()
            return json_error("This place is already claimed.", 409)

        cursor.execute(
            """
            SELECT ClaimID, Status
            FROM PlaceClaimRequest
            WHERE PlaceID = %s AND UserID = %s AND Status = 'pending'
            """,
            (place_id, session["user_id"]),
        )
        existing_request = cursor.fetchone()
        if existing_request:
            cursor.close()
            connection.close()
            return json_error("You already have a pending claim request for this place.", 409)

        cursor.execute(
            """
            INSERT INTO PlaceClaimRequest (PlaceID, UserID, Message)
            VALUES (%s, %s, %s)
            """,
            (place_id, session["user_id"], message),
        )
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({"message": "Claim request submitted."}), 201

    @app.put("/api/admin/claim-requests/<int:claim_id>")
    def api_admin_update_claim(claim_id):
        permission_error = require_role("admin")
        if permission_error:
            return permission_error

        payload = get_json_payload()
        status = payload.get("status", "").strip()
        if status not in {"approved", "rejected"}:
            return json_error("Status must be approved or rejected.")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT ClaimID, PlaceID, UserID, Status
            FROM PlaceClaimRequest
            WHERE ClaimID = %s
            """,
            (claim_id,),
        )
        claim = cursor.fetchone()
        if not claim:
            cursor.close()
            connection.close()
            return json_error("Claim request not found.", 404)

        cursor.execute(
            """
            UPDATE PlaceClaimRequest
            SET Status = %s,
                ReviewedAt = CURRENT_TIMESTAMP,
                ReviewedByUserID = %s
            WHERE ClaimID = %s
            """,
            (status, session["user_id"], claim_id),
        )

        if status == "approved":
            cursor.execute(
                """
                UPDATE Place
                SET ClaimedByUserID = %s
                WHERE PlaceID = %s
                """,
                (claim["UserID"], claim["PlaceID"]),
            )
            cursor.execute(
                """
                UPDATE PlaceClaimRequest
                SET Status = 'rejected',
                    ReviewedAt = CURRENT_TIMESTAMP,
                    ReviewedByUserID = %s
                WHERE PlaceID = %s AND ClaimID <> %s AND Status = 'pending'
                """,
                (session["user_id"], claim["PlaceID"], claim_id),
            )

        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({"message": "Claim request updated."})

    @app.post("/api/places/<int:place_id>/photos")
    def api_add_photo(place_id):
        permission_error = require_login()
        if permission_error:
            return permission_error

        payload = get_json_payload()
        photo_url = payload.get("photo_url", "").strip()
        caption = payload.get("caption", "").strip()

        if not photo_url:
            return json_error("Photo URL is required.")

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT PlaceID FROM Place WHERE PlaceID = %s",
            (place_id,),
        )
        place = cursor.fetchone()

        if not place:
            cursor.close()
            connection.close()
            return json_error("Place not found.", 404)
        
        cursor.execute(
            """
            INSERT INTO PlacePhoto (PlaceID, UserID, PhotoURL, Caption)
            VALUES (%s, %s, %s, %s)
            """,
            (place_id, session["user_id"], photo_url, caption),
        )
        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({"message": "Photo submitted for moderation."}), 201

    @app.put("/api/admin/photos/<int:photo_id>")
    def api_admin_update_photo(photo_id):
        permission_error = require_role("admin")
        if permission_error:
            return permission_error

        payload = get_json_payload()
        status = payload.get("status", "").strip()
        if status not in MODERATION_STATUSES - {"pending"}:
            return json_error("Status must be approved or rejected.")

        connection = get_db_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    "SELECT PhotoID FROM PlacePhoto WHERE PhotoID = %s",
                    (photo_id,),
                )
                photo = cursor.fetchone()

                if not photo:
                    return json_error("Photo not found.", 404)

                cursor.execute(
                    """
                    UPDATE PlacePhoto
                    SET Status = %s,
                        ModeratedAt = CURRENT_TIMESTAMP,
                        ModeratedByUserID = %s
                    WHERE PhotoID = %s
                    """,
                    (status, session["user_id"], photo_id),
                )
                connection.commit()

            return jsonify({"message": "Photo moderation updated."})
        finally:
            connection.close()

    @app.post("/api/places/<int:place_id>/reviews")
    def api_create_review(place_id):
        permission_error = require_login()
        if permission_error:
            return permission_error

        payload = get_json_payload()
        rating_raw = str(payload.get("rating", "")).strip()
        title = payload.get("title", "").strip()
        body = payload.get("body", "").strip()

        try:
            rating = int(rating_raw)
        except ValueError:
            return json_error("Rating must be a number between 1 and 5.")

        if rating < 1 or rating > 5:
            return json_error("Rating must be between 1 and 5.")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # verify if place exist check
        cursor.execute(
            "SELECT PlaceID FROM Place WHERE PlaceID = %s",
            (place_id,),
        )
        place = cursor.fetchone()

        if not place:
            cursor.close()
            connection.close()
            return json_error("Place not found.", 404)
        
        cursor.execute(
            """
            SELECT ReviewID
            FROM Review
            WHERE UserID = %s AND PlaceID = %s
            """,
            (session["user_id"], place_id),
        )
        existing_review = cursor.fetchone()

        if existing_review:
            cursor.close()
            connection.close()
            return json_error("You have already reviewed this place.", 409)

        cursor.execute(
            """
            INSERT INTO Review (UserID, PlaceID, Rating, Title, Body)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (session["user_id"], place_id, rating, title, body),
        )
        connection.commit()
        cursor.close()
        connection.close()
        update_place_avg_rating(place_id)
        return jsonify({"message": "Review created successfully."}), 201

    @app.put("/api/reviews/<int:review_id>")
    def api_edit_review(review_id):
        permission_error = require_login()
        if permission_error:
            return permission_error

        payload = get_json_payload()
        rating_raw = str(payload.get("rating", "")).strip()
        title = payload.get("title", "").strip()
        body = payload.get("body", "").strip()

        try:
            rating = int(rating_raw)
        except ValueError:
            return json_error("Rating must be a number between 1 and 5.")

        if rating < 1 or rating > 5:
            return json_error("Rating must be between 1 and 5.")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT ReviewID, UserID, PlaceID
            FROM Review
            WHERE ReviewID = %s
            """,
            (review_id,),
        )
        review = cursor.fetchone()
        if not review:
            cursor.close()
            connection.close()
            return json_error("Review not found.", 404)

        if review["UserID"] != session["user_id"]:
            cursor.close()
            connection.close()
            return json_error("You can only edit your own reviews.", 403)

        cursor.execute(
            """
            UPDATE Review
            SET Rating = %s,
                Title = %s,
                Body = %s,
                UpdatedAt = CURRENT_TIMESTAMP
            WHERE ReviewID = %s
            """,
            (rating, title, body, review_id),
        )
        connection.commit()
        place_id = review["PlaceID"]
        cursor.close()
        connection.close()
        update_place_avg_rating(place_id)
        return jsonify({"message": "Review updated successfully."})

    @app.delete("/api/reviews/<int:review_id>")
    def api_delete_review(review_id):
        permission_error = require_login()
        if permission_error:
            return permission_error

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT ReviewID, UserID, PlaceID
            FROM Review
            WHERE ReviewID = %s
            """,
            (review_id,),
        )
        review = cursor.fetchone()
        if not review:
            cursor.close()
            connection.close()
            return json_error("Review not found.", 404)

        if review["UserID"] != session["user_id"]:
            cursor.close()
            connection.close()
            return json_error("You can only delete your own reviews.", 403)

        cursor.execute("DELETE FROM Review WHERE ReviewID = %s", (review_id,))
        connection.commit()
        place_id = review["PlaceID"]
        cursor.close()
        connection.close()
        update_place_avg_rating(place_id)
        return jsonify({"message": "Review deleted successfully."})

    @app.put("/api/admin/reviews/<int:review_id>")
    def api_admin_review_visibility(review_id):
        permission_error = require_role("admin")
        if permission_error:
            return permission_error

        payload = get_json_payload()
        is_visible = bool(payload.get("is_visible"))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT PlaceID
            FROM Review
            WHERE ReviewID = %s
            """,
            (review_id,),
        )
        review = cursor.fetchone()
        if not review:
            cursor.close()
            connection.close()
            return json_error("Review not found.", 404)

        cursor.execute(
            """
            UPDATE Review
            SET IsVisible = %s
            WHERE ReviewID = %s
            """,
            (is_visible, review_id),
        )
        connection.commit()
        place_id = review["PlaceID"]
        cursor.close()
        connection.close()
        update_place_avg_rating(place_id)
        return jsonify({"message": "Review moderation updated."})

    @app.get("/api/lists")
    def api_lists():
        permission_error = require_login()
        if permission_error:
            return permission_error

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT ListID, Title, Description, IsPublic, CreatedAt
            FROM TripList
            WHERE UserID = %s
            ORDER BY CreatedAt DESC
            """,
            (session["user_id"],),
        )
        trip_lists = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify({"lists": trip_lists})

    @app.get("/api/explore/lists")
    def api_explore_lists():
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        public_lists = fetch_public_lists(cursor)
        cursor.close()
        connection.close()
        return jsonify({"lists": public_lists})

    @app.post("/api/lists")
    def api_create_list():
        permission_error = require_login()
        if permission_error:
            return permission_error

        payload = get_json_payload()
        title = payload.get("title", "").strip()
        description = payload.get("description", "").strip()
        is_public = 1 if payload.get("is_public") else 0

        if not title:
            return json_error("Title is required.")

        connection = get_db_connection()

        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT UserID FROM `User` WHERE UserID = %s", (session["user_id"],))
                existing_user = cursor.fetchone()

                if not existing_user:
                    session.clear()
                    return json_error("Your session is no longer valid. Please log in again.", 401)

                cursor.execute(
                    """
                    INSERT INTO TripList (UserID, Title, Description, IsPublic)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (session["user_id"], title, description, is_public),
                )
                connection.commit()
                list_id = cursor.lastrowid

            return jsonify({"message": "Trip list created successfully.", "list_id": list_id}), 201

        finally:
            connection.close()

    @app.get("/api/lists/<int:list_id>")
    def api_trip_list_detail(list_id):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT tl.ListID, tl.UserID, tl.Title, tl.Description, tl.IsPublic, tl.CreatedAt,
                   u.DisplayName
            FROM TripList tl
            JOIN `User` u ON u.UserID = tl.UserID
            WHERE tl.ListID = %s
            """,
            (list_id,),
        )
        trip_list = cursor.fetchone()
        if not trip_list:
            cursor.close()
            connection.close()
            return json_error("Trip list not found.", 404)

        is_owner = trip_list["UserID"] == session.get("user_id")
        if not trip_list["IsPublic"] and not is_owner and not is_admin():
            cursor.close()
            connection.close()
            return json_error("You cannot view this trip list.", 403)

        cursor.execute(
            """
            SELECT tli.ListID, tli.PlaceID, tli.Position, tli.Note,
                   p.Name, p.Address, p.AvgRating
            FROM TripListItem tli
            JOIN Place p ON tli.PlaceID = p.PlaceID
            WHERE tli.ListID = %s
            ORDER BY tli.Position ASC
            """,
            (list_id,),
        )
        items = cursor.fetchall()
        cursor.close()
        connection.close()

        return jsonify({"list": trip_list, "items": items, "can_edit": is_owner})

    @app.put("/api/lists/<int:list_id>")
    def api_update_list(list_id):
        permission_error = require_login()
        if permission_error:
            return permission_error

        payload = get_json_payload()
        title = payload.get("title", "").strip()
        description = payload.get("description", "").strip()
        is_public = 1 if payload.get("is_public") else 0

        if not title:
            return json_error("Title is required.")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT UserID
            FROM TripList
            WHERE ListID = %s
            """,
            (list_id,),
        )
        trip_list = cursor.fetchone()
        if not trip_list:
            cursor.close()
            connection.close()
            return json_error("Trip list not found.", 404)

        if trip_list["UserID"] != session["user_id"]:
            cursor.close()
            connection.close()
            return json_error("You can only edit your own trip lists.", 403)

        cursor.execute(
            """
            UPDATE TripList
            SET Title = %s,
                Description = %s,
                IsPublic = %s
            WHERE ListID = %s
            """,
            (title, description, is_public, list_id),
        )
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({"message": "Trip list updated successfully."})

    @app.delete("/api/lists/<int:list_id>")
    def api_delete_list(list_id):
        permission_error = require_login()
        if permission_error:
            return permission_error

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT UserID FROM TripList WHERE ListID = %s", (list_id,))
        trip_list = cursor.fetchone()
        if not trip_list:
            cursor.close()
            connection.close()
            return json_error("Trip list not found.", 404)

        if trip_list["UserID"] != session["user_id"]:
            cursor.close()
            connection.close()
            return json_error("You can only delete your own trip lists.", 403)

        cursor.execute("DELETE FROM TripListItem WHERE ListID = %s", (list_id,))
        cursor.execute("DELETE FROM TripList WHERE ListID = %s", (list_id,))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({"message": "Trip list deleted."})

    @app.put("/api/lists/<int:list_id>/reorder")
    def api_reorder_list(list_id):
        permission_error = require_login()
        if permission_error:
            return permission_error

        payload = get_json_payload()

        try:
            ordered_place_ids = [int(place_id) for place_id in payload.get("ordered_place_ids", [])]
        except (TypeError, ValueError):
            return json_error("Invalid reorder payload.")
        
        if not ordered_place_ids:
            return json_error("A reordered place list is required.")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT UserID
            FROM TripList
            WHERE ListID = %s
            """,
            (list_id,),
        )
        trip_list = cursor.fetchone()
        if not trip_list:
            cursor.close()
            connection.close()
            return json_error("Trip list not found.", 404)

        if trip_list["UserID"] != session["user_id"]:
            cursor.close()
            connection.close()
            return json_error("You can only reorder your own trip lists.", 403)

        cursor.execute(
            """
            SELECT PlaceID
            FROM TripListItem
            WHERE ListID = %s
            ORDER BY Position ASC
            """,
            (list_id,),
        )
        existing_ids = [row["PlaceID"] for row in cursor.fetchall()]
        if sorted(existing_ids) != sorted(ordered_place_ids):
            cursor.close()
            connection.close()
            return json_error("Reorder payload must contain the exact places already in the list.")

        for index, place_id in enumerate(ordered_place_ids, start=1):
            cursor.execute(
                """
                UPDATE TripListItem
                SET Position = %s
                WHERE ListID = %s AND PlaceID = %s
                """,
                (index, list_id, place_id),
            )

        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({"message": "Trip list reordered."})

    @app.post("/api/places/<int:place_id>/lists")
    def api_add_place_to_list(place_id):
        permission_error = require_login()
        if permission_error:
            return permission_error

        payload = get_json_payload()
        list_id = str(payload.get("list_id", "")).strip()
        note = payload.get("note", "").strip()

        if not list_id:
            return json_error("Please select a trip list.")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT ListID, UserID
            FROM TripList
            WHERE ListID = %s
            """,
            (list_id,),
        )
        trip_list = cursor.fetchone()
        if not trip_list or trip_list["UserID"] != session["user_id"]:
            cursor.close()
            connection.close()
            return json_error("Invalid trip list selection.", 403)

        cursor.execute(
            """
            SELECT PlaceID
            FROM Place
            WHERE PlaceID = %s
            """,
            (place_id,),
        )
        place = cursor.fetchone()
        if not place:
            cursor.close()
            connection.close()
            return json_error("Place not found.", 404)

        cursor.execute(
            """
            SELECT ListID, PlaceID
            FROM TripListItem
            WHERE ListID = %s AND PlaceID = %s
            """,
            (list_id, place_id),
        )
        existing_item = cursor.fetchone()
        if existing_item:
            cursor.close()
            connection.close()
            return json_error("This place is already in the selected trip list.", 409)

        cursor.execute(
            """
            SELECT COALESCE(MAX(Position), 0) + 1 AS next_position
            FROM TripListItem
            WHERE ListID = %s
            """,
            (list_id,),
        )
        next_position = cursor.fetchone()["next_position"]

        cursor.execute(
            """
            INSERT INTO TripListItem (ListID, PlaceID, Position, Note)
            VALUES (%s, %s, %s, %s)
            """,
            (list_id, place_id, next_position, note),
        )
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({"message": "Place added to trip list."}), 201

    @app.delete("/api/lists/<int:list_id>/places/<int:place_id>")
    def api_remove_place_from_list(list_id, place_id):
        permission_error = require_login()
        if permission_error:
            return permission_error

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT ListID, UserID
            FROM TripList
            WHERE ListID = %s
            """,
            (list_id,),
        )
        trip_list = cursor.fetchone()
        if not trip_list or trip_list["UserID"] != session["user_id"]:
            cursor.close()
            connection.close()
            return json_error("You can only modify your own trip lists.", 403)

        cursor.execute(
            """
            DELETE FROM TripListItem
            WHERE ListID = %s AND PlaceID = %s
            """,
            (list_id, place_id),
        )
        connection.commit()
        normalize_trip_list_positions(connection, list_id)
        cursor.close()
        connection.close()
        return jsonify({"message": "Place removed from trip list."})
