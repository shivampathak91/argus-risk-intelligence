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

# Update to uppercase enum values
updates = [
    ("bridge_failure", "BRIDGE_FAILURE"),
    ("urban_flood", "URBAN_FLOOD"),
    ("wildfire", "WILDFIRE"),
    ("power_grid_failure", "POWER_GRID_FAILURE"),
    ("earthquake", "EARTHQUAKE"),
    ("landslide", "LANDSLIDE"),
    ("unknown", "UNKNOWN"),
]

for old_val, new_val in updates:
    cursor.execute("UPDATE incidents SET incident_type = ? WHERE incident_type = ?", (new_val, old_val))
    affected = cursor.rowcount
    if affected > 0:
        print(f"Updated {affected} incidents from {old_val} to {new_val}")

conn.commit()
print("Database updated successfully")
conn.close()
