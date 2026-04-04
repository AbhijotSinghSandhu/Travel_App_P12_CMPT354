# Travel_App_P12_CMPT354
A Vancouver-focused travel discovery and review app inspired by TripAdvisor.

The app now serves a React front end from Flask and uses MySQL for data storage, session-based auth, trip planning, listing claims, and moderation workflows.

## Main Features

- User registration and login
- Browse, search, and filter places by category
- View place details, photos, and community reviews
- Write, edit, delete, hide, and restore reviews
- Create, edit, delete, and reorder trip lists
- Browse public trip lists shared by other users
- Business owner listing creation and claim requests
- Business owner listing updates after a claim is approved
- Admin moderation for claim requests, listing visibility, reviews, and photos

## Local Setup

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies:

```
pip install -r requirements.txt
```
4. Create a local .env file in the project root using .env.example.

5. Make sure MySQL is running.

6. Create the database:
```
CREATE DATABASE travel_app;
```

7. Load the schema and seed data:
```
mysql -u root -p travel_app < sql/schema.sql
mysql -u root -p travel_app < sql/seed.sql
```

8. Start the app:
```
python3 run.py
```

9. Open `http://127.0.0.1:5001`

## Demo Login

After seeding, you can sign in with:

- Traveler: `samuel14@example.com` / `password123`
- Traveler: `miachan@example.com` / `password123`
- Business owner: `owenwang@example.com` / `owner123`
- Admin: `admin01@example.com` / `admin123`

## Important Reset Note

Because the schema now includes claim-request and photo-moderation tables, reset the database with both commands whenever you pull these changes:

```bash
mysql -u root -p travel_app < sql/schema.sql
mysql -u root -p travel_app < sql/seed.sql
```

## Database Schema Setup

1. To create the database schema, run:

```
mysql -u root -p travel_app < sql/schema.sql
```
To verify the schema in MySQL:
```
USE travel_app;
SHOW TABLES;
```

## Seed Data Setup

1. After creating the schema, populate the database with sample data by running:

```
mysql -u root -p travel_app < sql/seed.sql
```
This script inserts:

- sample users

- Vancouver places

- categories and place-category mappings

- reviews

- trip lists and trip list items

- claim requests

- moderated and pending place photos

2. To verify the data in MySQL:
```
USE travel_app;
SELECT * FROM User;
SELECT * FROM Place;
SELECT * FROM Category;
SELECT * FROM Review;
SELECT * FROM TripList;
SELECT * FROM TripListItem;
SELECT * FROM PlaceCategory;
SELECT * FROM PlaceClaimRequest;
SELECT * FROM PlacePhoto;
```
