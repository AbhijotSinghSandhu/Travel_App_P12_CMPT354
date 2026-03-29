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