import sqlite3

def clear_tables(db_name, table1, table2):
    try:
        # Connect to the SQLite database
        connection = sqlite3.connect(db_name)
        cursor = connection.cursor()

        # Execute DELETE statements for both tables
        cursor.execute(f"DELETE FROM {table1};")
        cursor.execute(f"DELETE FROM {table2};")

        # Commit the changes
        connection.commit()

        print(f"All data cleared from tables '{table1}' and '{table2}'.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the connection
        if connection:
            connection.close()

# Usage
if __name__ == "__main__":
    database_name = "organ_donation.db"  # The name of your database
    table1_name = "donors"                # The first table name
    table2_name = "recipients"            # The second table name

    clear_tables(database_name, table1_name, table2_name)