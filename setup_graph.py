
import os
from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv(override=True)

db = FalkorDB(
    host=os.environ["FALKORDB_HOST"],
    port=int(os.environ["FALKORDB_PORT"]),
    username=os.environ["FALKORDB_USERNAME"],
    password=os.environ["FALKORDB_PASSWORD"],
    ssl=False,
    socket_connect_timeout=5,
    socket_timeout=5,
)

graph = db.select_graph("graphsleuth")

# Create fictional services
graph.query("""
MERGE (p:Service {name: 'Payment API'})
SET p.status = 'Degraded'
MERGE (d:Service {name: 'Payment Database'})
SET d.status = 'Healthy'
MERGE (n:Service {name: 'Notification Service'})
SET n.status = 'Healthy'

MERGE (p)-[:DEPENDS_ON]->(d)
MERGE (n)-[:DEPENDS_ON]->(p)

MERGE (i:Incident {id: 'INC001'})
SET i.title = 'Payment API latency spike',
    i.severity = 'High',
    i.status = 'Investigating'

MERGE (a:Alert {id: 'ALT001'})
SET a.type = 'HighLatency',
    a.message = 'Payment API latency exceeded threshold'

MERGE (i)-[:AFFECTS]->(p)
MERGE (i)-[:HAS_ALERT]->(a)
""")

print("GraphSleuth sample graph created successfully!")

result = graph.query("""
MATCH (s:Service)
RETURN s.name, s.status
""")

print("Services:")
for row in result.result_set:
    print(row)

db.close()
