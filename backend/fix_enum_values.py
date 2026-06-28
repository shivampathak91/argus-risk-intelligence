from app.database.session import get_db
from app.database.models import Incident

with get_db() as db:
    incidents = db.query(Incident).all()
    print(f'Found {len(incidents)} incidents')
    
    for incident in incidents:
        old_type = str(incident.incident_type)
        new_type = old_type.replace('IncidentType.', '').lower()
        
        # Map to valid enum values
        type_mapping = {
            'bridge_failure': 'bridge_failure',
            'urban_flood': 'urban_flood',
            'wildfire': 'wildfire',
            'power_grid_failure': 'power_grid_failure',
            'earthquake': 'earthquake',
            'landslide': 'landslide',
            'unknown': 'unknown',
        }
        
        if new_type in type_mapping:
            incident.incident_type = type_mapping[new_type]
            print(f'Updated incident {incident.id}: {old_type} -> {incident.incident_type}')
        else:
            print(f'Unknown type for incident {incident.id}: {old_type}, setting to unknown')
            incident.incident_type = 'unknown'
    
    db.commit()
    print('Database updated successfully')
