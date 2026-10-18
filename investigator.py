import os
from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv(override=True)

MAX_DEPTH = 10
GRAPH_NAME = "graphsleuth"


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def connect_db():
    """Connect to FalkorDB and select the GraphSleuth graph."""

    db = FalkorDB(
        host=os.environ["FALKORDB_HOST"],
        port=int(os.environ["FALKORDB_PORT"]),
        username=os.environ["FALKORDB_USERNAME"],
        password=os.environ["FALKORDB_PASSWORD"],
        ssl=False,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    return db, db.select_graph(GRAPH_NAME)


# --------------------------------------------------
# SERVICE DEPENDENCY TRAVERSAL
# --------------------------------------------------

def get_service_chain(graph, service, direction):
    """
    Find services connected through DEPENDS_ON relationships.

    upstream:
        Services that the selected service depends on.

    downstream:
        Services that depend directly or indirectly on
        the selected service.
    """

    if direction == "upstream":
        path_pattern = (
            "(s:Service {name: $service})"
            "-[:DEPENDS_ON*1.." + str(MAX_DEPTH) + "]->(d:Service)"
        )

    elif direction == "downstream":
        path_pattern = (
            "(d:Service)"
            "-[:DEPENDS_ON*1.." + str(MAX_DEPTH) + "]->"
            "(s:Service {name: $service})"
        )

    else:
        raise ValueError(
            "Direction must be 'upstream' or 'downstream'."
        )

    query = f"""
    MATCH p = {path_pattern}
    WITH d, min(length(p)) AS depth
    RETURN DISTINCT d.name, d.status, depth
    ORDER BY depth
    """

    result = graph.query(
        query,
        {"service": service},
    )

    return [
        {
            "name": row[0],
            "status": row[1],
            "depth": row[2],
        }
        for row in result.result_set
    ]


# --------------------------------------------------
# ACTUAL DEPENDENCY EDGES FOR VISUALIZATION
# --------------------------------------------------

def get_dependency_edges(service):
    """
    Return actual DEPENDS_ON edges along the upstream
    and downstream paths surrounding the selected service.

    Each edge represents:
        source DEPENDS_ON target

    Example:
        Notification Service -> Payment API
    """

    db, graph = connect_db()

    try:
        query = """
        MATCH (s:Service {name: $service})

        OPTIONAL MATCH
            (s)-[:DEPENDS_ON*1..10]->(upstream:Service)

        WITH s, collect(DISTINCT upstream.name) AS upstream_names

        OPTIONAL MATCH
            (downstream:Service)-[:DEPENDS_ON*1..10]->(s)

        WITH s,
             upstream_names,
             collect(DISTINCT downstream.name) AS downstream_names

        WITH [s.name] + upstream_names + downstream_names AS names

        UNWIND names AS service_name

        WITH DISTINCT service_name
        WHERE service_name IS NOT NULL

        MATCH (source:Service)-[:DEPENDS_ON]->(target:Service)

        WHERE source.name IN collect(service_name)
           OR target.name IN collect(service_name)

        RETURN DISTINCT source.name, target.name
        """

        # Use a two-stage query for reliable edge retrieval.
        service_query = """
        MATCH (s:Service {name: $service})
        RETURN s.name
        """

        service_result = graph.query(
            service_query,
            {"service": service},
        )

        if not service_result.result_set:
            return []

        upstream = get_service_chain(
            graph,
            service,
            "upstream",
        )

        downstream = get_service_chain(
            graph,
            service,
            "downstream",
        )

        service_names = {
            service,
            *[item["name"] for item in upstream],
            *[item["name"] for item in downstream],
        }

        edge_query = """
        MATCH (source:Service)-[:DEPENDS_ON]->(target:Service)
        RETURN DISTINCT source.name, target.name
        """

        edge_result = graph.query(edge_query)

        edges = []

        for row in edge_result.result_set:
            source = row[0]
            target = row[1]

            if source in service_names and target in service_names:
                edges.append({
                    "source": source,
                    "target": target,
                    "relationship": "DEPENDS_ON",
                })

        return edges

    finally:
        db.close()


# --------------------------------------------------
# INCIDENT INVESTIGATION
# --------------------------------------------------

def investigate_incident(
    incident_id="INC001",
    display=True,
):
    """
    Retrieve incident details, associated alerts,
    and multi-hop service dependencies.
    """

    db, graph = connect_db()

    try:
        incident_query = """
        MATCH (i:Incident {id: $incident_id})-[:AFFECTS]->(s:Service)
        OPTIONAL MATCH (i)-[:HAS_ALERT]->(a:Alert)

        RETURN
            i.id,
            i.title,
            i.severity,
            i.status,
            s.name,
            s.status,
            a.type,
            a.message
        """

        result = graph.query(
            incident_query,
            {"incident_id": incident_id},
        )

        if not result.result_set:
            return {
                "found": False,
                "incident_id": incident_id,
                "message": (
                    f"No incident found with ID {incident_id}."
                ),
            }

        (
            inc_id,
            title,
            severity,
            status,
            service,
            service_status,
            alert_type,
            alert_message,
        ) = result.result_set[0]

        upstream = get_service_chain(
            graph,
            service,
            "upstream",
        )

        downstream = get_service_chain(
            graph,
            service,
            "downstream",
        )

        dependencies = [
            item["name"]
            for item in upstream
            if item["depth"] == 1
        ]

        findings = {
            "found": True,
            "incident_id": inc_id,
            "title": title,
            "severity": severity,
            "status": status,
            "affected_service": service,
            "service_status": service_status,
            "alert_type": alert_type,
            "alert_message": alert_message,
            "dependencies": dependencies,
            "upstream_services": upstream,
            "downstream_services": downstream,
            "max_depth": MAX_DEPTH,
            "finding": (
                f"{service} is recorded as {service_status}."
            ),
            "recommendation": (
                "Review linked alerts, upstream dependencies, "
                "and downstream impact before taking action."
            ),
            "root_cause_confirmed": False,
        }

        if display:
            print("\n========== GRAPHSLEUTH ==========")
            print(f"Incident: {inc_id}")
            print(f"Title: {title}")
            print(f"Severity: {severity}")
            print(f"Incident Status: {status}")
            print(f"Affected Service: {service}")
            print(f"Service Status: {service_status}")

            print("\n--- UPSTREAM DEPENDENCIES ---")

            if upstream:
                for item in upstream:
                    print(
                        f"Level {item['depth']}: "
                        f"{item['name']} "
                        f"({item['status']})"
                    )
            else:
                print("No upstream dependencies found.")

            print("\n--- DOWNSTREAM BLAST RADIUS ---")

            if downstream:
                for item in downstream:
                    print(
                        f"Level {item['depth']}: "
                        f"{item['name']} "
                        f"({item['status']})"
                    )
            else:
                print("No downstream dependents found.")

            print("\n--- ALERT DETAILS ---")
            print(f"Alert Type: {alert_type}")
            print(f"Alert Message: {alert_message}")

            print("\nRoot cause confirmed: No")
            print("================================")

        return findings

    finally:
        db.close()


# --------------------------------------------------
# DIRECT EXECUTION
# --------------------------------------------------

if __name__ == "__main__":
    investigate_incident()