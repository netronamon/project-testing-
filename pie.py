import cv2
import torch
import sqlite3
import time
from gpsdclient import GPSDClient
import requests

# Initialize database
def init_db():
    print("Initializing the local database...")
    conn = sqlite3.connect("detections.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class TEXT,
            confidence REAL,
            latitude REAL,
            longitude REAL,
            timestamp TEXT
        )
    """)
    conn.commit()
    return conn

# Get GPS coordinates
def get_gps_coordinates():
    print("Fetching GPS coordinates...")
    with GPSDClient() as client:
        for result in client.dict_stream():
            if 'lat' in result and 'lon' in result:
                return result['lat'], result['lon']
    return None, None

# Initialize YOLOv5 model
def load_model():
    print("Loading YOLOv5 model...")
    model = torch.hub.load('ultralytics/yolov5', 'custom', path='best.pt')  # Replace 'best.pt' with your model path
    model.conf = 0.6  # Set confidence threshold
    return model

# Save detection to database
def save_detection(conn, detected_class, confidence, latitude, longitude):
    print("Saving detection to the local database...")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO detections (class, confidence, latitude, longitude, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (detected_class, confidence, latitude, longitude, time.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

# Fetch data from server
def fetch_data_from_server():
    print("Fetching data from the server...")
    try:
        response = requests.get('http://192.168.0.102:3000/get_all_data')
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from server: {e}")
        return []

# Compare and send missing data
def compare_and_send_missing_data(server_data):
    print("Comparing local data with server data...")
    conn = init_db()
    cursor = conn.cursor()

    # Get local data
    cursor.execute("SELECT class, latitude, longitude FROM detections")
    local_data = set([(row[0], row[1], row[2]) for row in cursor.fetchall()])

    # Compare and send missing data
    for entry in server_data:
        if (entry['type'], entry['latitude'], entry['longitude']) not in local_data:
            try:
                response = requests.post('http://192.168.0.102:3000/add_data', json=entry)
                response.raise_for_status()
                print(f"Sent missing data: {entry}")
                # Save the entry locally
                save_detection(conn, entry['type'], 1.0, entry['latitude'], entry['longitude'])
            except requests.exceptions.RequestException as e:
                print(f"Error sending data to server: {e}")

    conn.close()

# Main function
def main():
    print("Initializing components...")
    conn = init_db()
    model = load_model()
    cap = cv2.VideoCapture(0)  # Use Pi Camera or a USB camera (index 0)

    print("Fetching data from the server to update the local database...")
    server_data = fetch_data_from_server()
    compare_and_send_missing_data(server_data)

    print("Starting video capture and detection. Type 'exit' or 'end' to terminate the program.")
    
    while True:
        user_input = input("Enter command ('exit' or 'end' to quit): ").strip().lower()
        if user_input in ["exit", "end"]:
            print("Exiting the program...")
            break

        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            continue

        print("Performing inference...")
        results = model(frame)
        detections = results.pandas().xyxy[0]  # Get detections as pandas DataFrame

        for _, row in detections.iterrows():
            detected_class = row['name']
            confidence = row['confidence']

            if confidence >= 0.6:
                latitude, longitude = get_gps_coordinates()
                if latitude and longitude:
                    print(f"Detected: {detected_class}, Confidence: {confidence:.2f}, GPS: ({latitude}, {longitude})")
                    save_detection(conn, detected_class, confidence, latitude, longitude)
                else:
                    print("GPS coordinates not available.")

        # Display the frame with detections
        cv2.imshow("Detection", results.render()[0])

        # Break on 'q' key press during frame display
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Stopping video capture...")
            break

    # Clean up
    print("Releasing resources...")
    cap.release()
    cv2.destroyAllWindows()
    conn.close()

if __name__ == "__main__":
    main()
