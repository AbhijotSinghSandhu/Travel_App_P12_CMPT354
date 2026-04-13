from sqlalchemy import text

def create_triggers(db):
    duplicate_trigger = """
    CREATE TRIGGER IF NOT EXISTS prevent_duplicate_trip_list_place
    BEFORE INSERT ON trip_list_places
    FOR EACH ROW
    WHEN EXISTS (
        SELECT 1
        FROM trip_list_places
        WHERE trip_list_id = NEW.trip_list_id
          AND place_id = NEW.place_id
    )
    BEGIN
        SELECT RAISE(FAIL, 'This place is already in the trip list.');
    END;
    """

    position_trigger = """
    CREATE TRIGGER IF NOT EXISTS auto_set_trip_list_position
    AFTER INSERT ON trip_list_places
    FOR EACH ROW
    WHEN NEW.position IS NULL
    BEGIN
        UPDATE trip_list_places
        SET position = (
            SELECT COALESCE(MAX(position), 0)
            FROM trip_list_places
            WHERE trip_list_id = NEW.trip_list_id
              AND id != NEW.id
        ) + 1
        WHERE id = NEW.id;
    END;
    """

    with db.engine.connect() as connection:
        connection.execute(text(duplicate_trigger))
        connection.execute(text(position_trigger))
        connection.commit()