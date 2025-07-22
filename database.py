import sqlite3
from datetime import datetime
import pandas as pd
import os
def init_db():
    init_user_db()
    init_station_db()

# ----------------- DATABASE PATHS -----------------
DB_PATH = "station_data.db"       # for station logs
USER_DB_PATH = "app_data.db"      # for user login/register

# ----------------- USER TABLE -----------------
def init_user_db():
    with sqlite3.connect(USER_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT,
                section TEXT,
                registered_by TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()

# ----------------- STATION LOGS TABLE -----------------
def init_station_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS station_logs (
                entry_date TEXT,
                zone TEXT,
                username TEXT,
                sps_name TEXT,
                total_pumps INTEGER,
                working_pumps INTEGER,
                standby_pumps INTEGER,
                standby_um INTEGER,
                remarks TEXT,
                pumping_mld REAL,
                income_mld REAL,
                supply_mld REAL,
                PRIMARY KEY (entry_date, sps_name)
            )
        """)
        conn.commit()

# ----------------- USER AUTH -----------------
def register_user(username, password, section, registered_by):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(USER_DB_PATH) as conn:
        conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                     (username, password, section, registered_by, timestamp))
        conn.commit()

def authenticate_user(username, password):
    with sqlite3.connect(USER_DB_PATH) as conn:
        cursor = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        return cursor.fetchone()

def get_user_section(username):
    with sqlite3.connect(USER_DB_PATH) as conn:
        cursor = conn.execute("SELECT section FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        return result[0] if result else None

def get_all_users():
    with sqlite3.connect(USER_DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM users", conn)

# ----------------- STATION LOGGING -----------------


def save_station_entry(data, pin_entered):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        existing = cursor.execute("SELECT * FROM station_logs WHERE entry_date = ? AND sps_name = ?",
                                  (data['entry_date'], data['sps_name'])).fetchone()
        if existing:
            if pin_entered:
                cursor.execute("""
                    UPDATE station_logs SET
                        zone = ?, username = ?, total_pumps = ?, working_pumps = ?,
                        standby_pumps = ?, standby_um = ?, remarks = ?,
                        pumping_mld = ?, income_mld = ?, supply_mld = ?
                    WHERE entry_date = ? AND sps_name = ?
                """, (
                    data['zone'], data['username'], data['total_pumps'], data['working_pumps'],
                    data['standby_pumps'], data['standby_um'], data['remarks'],
                    data['pumping_mld'], data['income_mld'], data['supply_mld'],
                    data['entry_date'], data['sps_name']
                ))
        else:
            cursor.execute("""
                INSERT INTO station_logs (
                    entry_date, zone, username, sps_name, total_pumps,
                    working_pumps, standby_pumps, standby_um, remarks,
                    pumping_mld, income_mld, supply_mld
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['entry_date'], data['zone'], data['username'], data['sps_name'], data['total_pumps'],
                data['working_pumps'], data['standby_pumps'], data['standby_um'], data['remarks'],
                data['pumping_mld'], data['income_mld'], data['supply_mld']
            ))
        conn.commit()

def delete_station_entry(entry_date, sps_name):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM station_logs WHERE entry_date = ? AND sps_name = ?", (entry_date, sps_name))
        conn.commit()
# ✅ Correct Function Definition
def load_station_logs(zone=None, start_date=None, end_date=None):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM station_logs"
    filters = []
    params = []

    if zone:
        filters.append("Zone = ?")
        params.append(zone)

    if start_date and end_date:
        filters.append("Date BETWEEN ? AND ?")
        params.extend([start_date, end_date])

    if filters:
        query += " WHERE " + " AND ".join(filters)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df
def get_zone_sps_mapping():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT Zone, [SPS Name] FROM station_logs")
        rows = cursor.fetchall()
        zone_sps_map = {}

        for zone, sps in rows:
            if zone not in zone_sps_map:
                zone_sps_map[zone] = set()
            zone_sps_map[zone].add(sps)

        # Convert sets to sorted lists
        zone_sps_map = {zone: sorted(list(sps_set)) for zone, sps_set in zone_sps_map.items()}

        return zone_sps_map

    except Exception as e:
        print("Error in get_zone_sps_mapping:", e)
        return None
    finally:
        conn.close()




# ✅ Backward-compatible alias
load_station_data = load_station_logs
