
from investigator import connect_db, investigate_incident

db, graph = connect_db()

try:
    graph.query("""
        MERGE (:Service {
            name: 'Customer Portal',
            status: 'Healthy'
        })
    """)

    graph.query("""
        MATCH (portal:Service {name: 'Customer Portal'})
        MATCH (notification:Service {
            name: 'Notification Service'
        })
        MERGE (portal)-[:DEPENDS_ON]->(notification)
    """)

    print("Test relationship added successfully.")

finally:
    db.close()

findings = investigate_incident("INC001")

print("\n--- LEVEL-TWO TEST ---")

for service in findings.get("downstream_services", []):
    print(
        f"Level {service['depth']}: "
        f"{service['name']} ({service['status']})"
    )
