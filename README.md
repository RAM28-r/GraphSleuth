
# GraphSleuth
### AI-Powered, Graph-Based Incident Investigation

GraphSleuth is an AI-assisted incident investigation prototype that uses graph relationships to help investigators understand incidents, trace service dependencies, and identify potential downstream impact.

Built with **FalkorDB, Python, Streamlit, Groq, and the Model Context Protocol (MCP)**, GraphSleuth combines graph-based evidence retrieval with an AI agent that can invoke read-only graph investigation tools.

## Problem

During an incident, understanding which services depend on an affected service can be difficult when relationships are spread across multiple systems.

GraphSleuth uses a graph representation of incidents, services, alerts, and dependencies to make these relationships easier to investigate.

## Solution

GraphSleuth provides:

- Incident retrieval using an incident ID.
- Linked alert and affected-service information.
- Upstream and downstream dependency analysis.
- Multi-hop service dependency tracing.
- Graph-edge evidence for explaining dependency paths.
- An AI assistant that answers questions using supplied investigation evidence.
- An MCP execution trace showing tool calls and their results.
- A Streamlit dashboard for incident investigation.

## Architecture

```text
Analyst
   |
   v
Streamlit Dashboard
   |
   v
Incident Investigator
   |
   v
FalkorDB Graph
   |
   +--> Incident and alert evidence
   +--> Upstream dependencies
   +--> Downstream dependents
   +--> Multi-hop dependency paths
                  |
                  v
             MCP Server
                  |
                  v
             MCP Agent
                  |
                  v
             Groq LLM
                  |
                  v
       Evidence-grounded answer
       and MCP execution trace
```

The dashboard and investigation code retrieve graph evidence. The MCP-enabled agent can call the exposed graph investigation tools and use their results when answering analyst questions.

## Technology Stack

- **Python** — application and investigation logic
- **Streamlit** — interactive dashboard
- **FalkorDB** — graph database
- **Cypher** — graph queries and relationship traversal
- **MCP** — standardized tool discovery and invocation
- **Groq API** — language-model responses
- **Pandas** — tabular data processing and presentation

## Graph Data Model

GraphSleuth uses the following node labels:

| Node | Purpose |
|---|---|
| `Incident` | Stores incident information such as ID, title, severity, and status |
| `Service` | Represents an application or service and its recorded status |
| `Alert` | Stores alert type and message information |

The relationships used by the investigation logic are:

| Relationship | Meaning |
|---|---|
| `(:Incident)-[:AFFECTS]->(:Service)` | Identifies the service associated with an incident |
| `(:Incident)-[:HAS_ALERT]->(:Alert)` | Links an incident to its alert |
| `(:Service)-[:DEPENDS_ON]->(:Service)` | Records that the source service depends on the target service |

**Important:** `A DEPENDS_ON B` means that A depends on B. Consequently, downstream tracing finds services that depend directly or indirectly on the selected service.

The application selects the graph named `graphsleuth`.

## MCP Tools

The MCP server exposes three read-only investigation tools:

### 1. `investigate_incident_tool`
Retrieves incident details, linked alert information, and affected-service evidence.

### 2. `trace_service_dependencies`
Traces multi-hop service relationships. It supports:
- `upstream`: services the selected service depends on.
- `downstream`: services that depend on the selected service.

The traversal is bounded to a maximum depth of 10 in the investigation implementation.

### 3. `get_service_dependency_edges`
Retrieves graph-edge evidence around a selected service to help establish direct relationships and explain dependency paths.

The agent uses an allowlist of these tools. Tool results are evidence for investigation, not proof that a service has failed.

## Example Investigation

The prototype includes a sample incident identified as `INC001`, involving a degraded Payment API.

A downstream dependency investigation can identify:

- **Notification Service** — direct dependent of Payment API.
- **Customer Portal** — indirect dependent through Notification Service.

These paths identify potential impact. They do not independently establish that either downstream service is failing.

Actual findings depend on the data stored in FalkorDB.

## Requirements

- Python 3.12 or a compatible Python version supported by the installed dependencies
- Access to a configured FalkorDB instance
- A valid Groq API key for AI-generated answers
- Git
- Internet access where required for database connectivity and the Groq API

## Installation and Setup

### 1. Clone the repository

```bash
git clone <YOUR_PUBLIC_GITHUB_REPOSITORY_URL>
cd GraphSleuth
```

Replace the placeholder with the HTTPS URL of your public repository.

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

Install the project's required packages:

```powershell
python -m pip install streamlit pandas falkordb python-dotenv groq mcp
```

If a `requirements.txt` is provided, prefer installing from it:

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file in the project root.

Use the variable names expected by the application:

```dotenv
FALKORDB_HOST=your_falkordb_host
FALKORDB_PORT=your_falkordb_port
FALKORDB_USERNAME=your_falkordb_username
FALKORDB_PASSWORD=your_falkordb_password

GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
```

Replace the placeholders with your actual configuration. Do not commit `.env` or share API keys and database credentials publicly.

### 5. Prepare the graph data

The application expects the `graphsleuth` graph to contain the required nodes, properties, and relationships.

If the repository includes `setup_graph.py`, inspect its configuration and use it to initialize the sample graph when appropriate:

```powershell
python setup_graph.py
```

Do not run the setup script against an existing graph without checking whether it creates, replaces, or duplicates data.

### 6. Start the dashboard

```powershell
python -m streamlit run app.py
```

Streamlit will display the local dashboard URL in the terminal.

## Running the MCP Server

The MCP server uses standard input/output transport.

To launch it directly:

```powershell
python mcp_server.py
```

A blank terminal can be normal for a running stdio server because it waits for MCP client communication. Stop it with `Ctrl+C` when running it manually.

The MCP client test launches the server as a subprocess.

## Running Tests

The repository includes the following test files:

| Test file | Intended coverage |
|---|---|
| `test_connection.py` | Database connection |
| `test_investigator.py` | Incident investigation logic |
| `test_mcp_agent.py` | MCP-enabled agent execution |
| `test_mcp_client.py` | MCP server connection and tool discovery |
| `test_multihop.py` | Multi-hop dependency tracing |

Run individual tests from the project root:

```powershell
python test_connection.py
python test_investigator.py
python test_mcp_client.py
python test_mcp_agent.py
python test_multihop.py
```

Tests requiring live database or AI access need the corresponding configuration and services available.

## Evidence and Safety

GraphSleuth is an investigation-support prototype.

- Dependency relationships describe potential impact paths, not confirmed failures.
- Root cause must remain unconfirmed unless supported by explicit evidence.
- AI-generated explanations should be checked against graph results.
- The prototype does not replace monitoring, logs, metrics, or an incident-response process.
- Validate findings against operational telemetry before taking remediation action.
- Keep database credentials and API keys out of source control.

## Current Limitations

- Results depend on the completeness and correctness of the graph data.
- The AI assistant requires valid Groq API access.
- Graph relationships alone cannot confirm runtime service health or root cause.
- Operational telemetry and remediation actions are outside the scope of the documented read-only investigation tools.

## Project Status

GraphSleuth is a working prototype demonstrating graph-based incident investigation, multi-hop dependency tracing, MCP tool integration, and evidence-grounded AI responses.

## License

Add the license required by your team or hackathon before distributing the project under an open-source license.
