
import os
from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv(override=True)

print("Connecting to FalkorDB...", flush=True)

try:
    db = FalkorDB(
        host=os.environ["FALKORDB_HOST"],
        port=int(os.environ["FALKORDB_PORT"]),
        username=os.environ["FALKORDB_USERNAME"],
        password=os.environ["FALKORDB_PASSWORD"],
        ssl=False,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    print("Client created. Testing database...", flush=True)

    graph = db.select_graph("graphsleuth")
    result = graph.query("RETURN 1 AS test")

    print("SUCCESS: FalkorDB connection works!", flush=True)
    print("Response:", result.result_set, flush=True)

    db.close()

except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}", flush=True)
