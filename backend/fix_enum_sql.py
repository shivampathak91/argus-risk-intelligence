import sqlite3

db_path = r"C:\Users\Shivam\OneDrive\Pictures\Documents\kaggle capstone project\argus.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check current values
cursor.execute("SELECT id, incident_type FROM incidents")
rows = cursor.fetchall()
print(f"Found {len(rows)} incidents:")
for row in rows:
    print(f"  {row[0]}: {row[1]}")

# Update enum values
updates = [
    ("IncidentType.BRIDGE_FAILURE", "bridge_failure"),
    ("IncidentType.URBAN_FLOOD", "urban_flood"),
    ("IncidentType.WILDFIRE", "wildfire"),
    ("IncidentType.POWER_GRID_FAILURE", "power_grid_failure"),
    ("IncidentType.EARTHQUAKE", "earthquake"),
    ("IncidentType.LANDSLIDE", "landslide"),
    ("IncidentType.UNKNOWN", "unknown"),
]

for old_val, new_val in updates:
    cursor.execute("UPDATE incidents SET incident_type = ? WHERE incident_type = ?", (new_val, old_val))
    affected = cursor.rowcount
    if affected > 0:
        print(f"Updated {affected} incidents from {old_val} to {new_val}")

conn.commit()
print("Database updated successfully")
conn.close()
