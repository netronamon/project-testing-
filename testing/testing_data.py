import requests
import sqlite3
import tkinter as tk
from tkinter import ttk

# Server URL
SERVER_URL = "http://localhost:3000"  # Replace with your server's IP if remote

# SQLite database file
LOCAL_DB = "local_data.db"

# Create or connect to the SQLite database
def initialize_local_database():
    conn = sqlite3.connect(LOCAL_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Fetch data from the server
def fetch_data_from_server():
    try:
        response = requests.get(f"{SERVER_URL}/getCoordinates")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data from server: {e}")
        return []

# Store fetched data into the local SQLite database
def store_data_locally(data):
    conn = sqlite3.connect(LOCAL_DB)
    cursor = conn.cursor()

    # Clear old data
    cursor.execute("DELETE FROM locations")

    # Insert new data
    for record in data:
        cursor.execute("""
            INSERT INTO locations (type, latitude, longitude)
            VALUES (?, ?, ?)
        """, (record['type'], record['latitude'], record['longitude']))

    conn.commit()
    conn.close()

# Fetch and store data
def update_local_database():
    data = fetch_data_from_server()
    if data:
        store_data_locally(data)
        print("Local database updated successfully.")
    else:
        print("No data to update.")

# Fetch data from local database for display
def fetch_local_data():
    conn = sqlite3.connect(LOCAL_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations")
    data = cursor.fetchall()
    conn.close()
    return data

# Display data in a GUI window
def display_data_in_window():
    data = fetch_local_data()

    root = tk.Tk()
    root.title("Local Database Viewer")

    # Table
    table = ttk.Treeview(root, columns=("ID", "Type", "Latitude", "Longitude"), show="headings")
    table.heading("ID", text="ID")
    table.heading("Type", text="Type")
    table.heading("Latitude", text="Latitude")
    table.heading("Longitude", text="Longitude")

    # Insert data into table
    for row in data:
        table.insert("", tk.END, values=row)

    table.pack(fill=tk.BOTH, expand=True)

    root.mainloop()

# Main function
if __name__ == "__main__":
    # Initialize the local database
    initialize_local_database()

    # Update local database with server data
    update_local_database()

    # Display the data in a GUI window
    display_data_in_window()
