# Travel_App_P12_CMPT354
A travel app which helps people by serving them with cool spots to visit around Vancouver

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

7. Start the app:
```
python3 run.py
```

## Database Schema Setup

1. To create the database schema, run:

```
mysql -u root -p < sql/schema.sql
```
To verify the schema in MySQL:
```
USE travel_app;
SHOW TABLES;
```

## Seed Data Setup

1. After creating the schema, populate the database with sample data by running:

```
mysql -u root -p < sql/seed.sql
```
This script inserts:

- sample users

- Vancouver places

- categories and place-category mappings

- reviews

- trip lists and trip list items

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
```
