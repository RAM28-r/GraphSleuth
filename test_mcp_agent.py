
from investigator import investigate_incident, get_dependency_edges
from mcp_agent import answer_question_with_mcp

findings = investigate_incident("INC001", display=False)

edges = get_dependency_edges("Payment API")

question = (
    "Use the graph tools to investigate Payment API. "
    "Which services depend on it directly or indirectly? "
    "Explain the paths and do not claim that a dependency proves a service failed."
)

try:
    answer = answer_question_with_mcp(
        question=question,
        findings=findings,
        graph_edges=edges,
    )
    print("\n--- GraphSleuth MCP Agent Answer ---\n")
    print(answer)
except Exception:
    import traceback
    traceback.print_exc()
