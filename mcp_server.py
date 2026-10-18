
"""Read-only MCP tools for GraphSleuth."""

import json

from mcp.server.mcpserver import MCPServer
from investigator import (
    connect_db,
    investigate_incident,
    get_service_chain,
    get_dependency_edges,
)

mcp = MCPServer("GraphSleuth")


@mcp.tool()
def investigate_incident_tool(incident_id: str = "INC001") -> str:
    """Retrieve incident details, linked alerts, and service impact evidence."""
    findings = investigate_incident(
        incident_id=incident_id,
        display=False,
    )
    return json.dumps(findings, default=str)


@mcp.tool()
def trace_service_dependencies(
    service_name: str,
    direction: str = "downstream",
) -> str:
    """
    Trace multi-hop service relationships.

    Use downstream to find services that depend on this service.
    Use upstream to find services this service depends on.
    """
    if direction not in {"upstream", "downstream"}:
        return json.dumps({
            "error": "direction must be 'upstream' or 'downstream'"
        })

    db, graph = connect_db()
    try:
        results = get_service_chain(graph, service_name, direction)
        return json.dumps({
            "service": service_name,
            "direction": direction,
            "results": results,
            "interpretation": (
                "DEPENDS_ON edges point from a dependent service "
                "to its dependency. These paths indicate potential "
                "impact, not confirmed operational failure."
            ),
        }, default=str)
    finally:
        db.close()


@mcp.tool()
def get_service_dependency_edges(service_name: str) -> str:
    """Return actual DEPENDS_ON edges surrounding a service."""
    edges = get_dependency_edges(service_name)
    return json.dumps({
        "service": service_name,
        "edges": edges,
        "edge_meaning": "source DEPENDS_ON target",
    }, default=str)


if __name__ == "__main__":
    mcp.run(transport="stdio")
