from flask import Flask, jsonify
import requests
import mysql.connector
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    'host': 'db', # Oder 'localhost', falls nicht in Docker
    'user': 'root',
    'password': 'password123',
    'database': 'sbb_data'
}
API_CONNECTOR_URL = "http://api:5000/api/radar"

@app.route('/sync-trains', methods=['GET'])
def sync_trains():
    try:
        response = requests.get(API_CONNECTOR_URL)
        raw_data = response.json().get('data', [])
        
        if not raw_data:
            return jsonify({"status": "error", "message": "Keine Daten von API erhalten"}), 500

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # LIVE-Tabelle leeren für frische Daten
        cursor.execute("TRUNCATE TABLE active_trains")

        live_query = """
            INSERT INTO active_trains (trip_id, origin, destination, delay, latitude, longitude, route_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE delay = VALUES(delay)
        """
        
        archive_query = """
            INSERT IGNORE INTO delay_archive (trip_id, origin, destination, delay, route_data)
            VALUES (%s, %s, %s, %s, %s)
        """

        sync_count = 0
        for item in raw_data:
            station_name = item.get('station', {}).get('name', 'Unbekannt')
            for train in item.get('stationboard', []):
                # ID erstellen: Zugname + Ziel (macht es über Hubs hinweg eindeutiger)
                train_name = f"{train.get('category', '')}{train.get('number', '')}"
                destination = train.get('to', 'Unbekannt')
                trip_id = f"{train_name}_{destination}"
                
                # Koordinaten extrahieren
                coords = train.get('stop', {}).get('station', {}).get('coordinate', {})
                lat, lon = coords.get('x'), coords.get('y')
                
                raw_delay = train.get('stop', {}).get('delay')
                delay = int(raw_delay) if raw_delay is not None else 0

                if lat and lon:
                    # 1. In Live-Tabelle schreiben
                    cursor.execute(live_query, (trip_id, station_name, destination, delay, lat, lon, json.dumps(train.get('passList', []))))
                    
                    # 2. Ins Archiv, wenn Verspätung >= 20
                    if delay >= 20:
                        cursor.execute(archive_query, (trip_id, station_name, destination, delay, json.dumps(train.get('passList', []))))
                    
                    sync_count += 1

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": f"{sync_count} Züge aktualisiert."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/view-live', methods=['GET'])
def view_live():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT trip_id, origin, destination, delay, CAST(latitude AS CHAR) as latitude, CAST(longitude AS CHAR) as longitude FROM active_trains")
        data = cursor.fetchall()
        
        # Sicherstellen, dass Koordinaten Zahlen sind für das Frontend
        for row in data:
            row['latitude'] = float(row['latitude']) if row['latitude'] else 0
            row['longitude'] = float(row['longitude']) if row['longitude'] else 0
            
        cursor.close()
        conn.close()
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)