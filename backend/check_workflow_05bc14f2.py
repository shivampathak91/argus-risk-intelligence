from app.database.session import get_db
from app.database.models import Workflow

workflow_id = "05bc14f2-7a23-40d1-aff1-6d8100de766a"

with get_db() as db:
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if workflow:
        print(f"Workflow {workflow_id}:")
        print(f"  Status: {workflow.status}")
        print(f"  Incident ID: {workflow.incident_id}")
        print(f"  Agent steps:")
        for step in workflow.agent_steps:
            print(f"    - {step['agent']}: {step['status']}")
            if step.get('error'):
                print(f"      Error: {step['error']}")
    else:
        print("Workflow not found")
