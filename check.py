import sqlite3
import pandas as pd

DB_PATH = "station_data.db"  # Make sure the path matches your app

conn = sqlite3.connect(DB_PATH)

try:
    df = pd.read_sql("SELECT Zone, [SPS Name] FROM station_logs LIMIT 10", conn)
    print(df)
except Exception as e:
    print("Error:", e)
finally:
    conn.close()
