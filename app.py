
import json
from html import escape

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from investigator import (
    investigate_incident,
    get_dependency_edges,
)
from mcp_agent import answer_question_with_mcp, get_last_tool_trace


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="GraphSleuth | AI Incident Investigator",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# DARK SOC DASHBOARD STYLING
# --------------------------------------------------

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b1020;
        color: #e5e7eb;
    }

    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #263449;
    }

    h1, h2, h3 {
        color: #f1f5f9 !important;
    }

    p, label, li {
        color: #cbd5e1;
    }

    [data-testid="stMetric"] {
        background: #151d2e;
        border: 1px solid #263449;
        border-radius: 12px;
        padding: 16px;
    }

    [data-testid="stMetricLabel"] {
        color: #94a3b8;
    }

    [data-testid="stMetricValue"] {
        color: #f8fafc;
    }

    .section-title {
        color: #93c5fd;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 1.5px;
        margin-top: 18px;
        margin-bottom: 12px;
    }

    .panel {
        background: #151d2e;
        border: 1px solid #263449;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 14px;
    }

    .status-pill {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 6px;
        background: #78350f;
        color: #fde68a;
        font-size: 12px;
        font-weight: 700;
    }

    .muted {
        color: #94a3b8;
        font-size: 13px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #263449;
        border-radius: 10px;
    }

    .stButton button {
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown("## 🔎 GraphSleuth")
    st.caption("GRAPH-POWERED INCIDENT INVESTIGATION")

    st.divider()

    st.markdown("### Navigation")
    st.markdown("🖥️ Incident Overview")
    st.markdown("🕸️ Dependency Analysis")
    st.markdown("🚨 Alert Correlation")
    st.markdown("📊 Blast Radius")

    st.divider()

    incident_id = st.text_input(
        "Incident ID",
        value="INC001",
        help="Enter an incident ID stored in FalkorDB.",
    )

    investigate_button = st.button(
        "🔍 Investigate Incident",
        use_container_width=True,
        type="primary",
    )

    st.divider()

    st.caption("Data source: FalkorDB")
    st.caption("Graph: graphsleuth")
    st.caption("Review findings before taking action.")


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown("# GraphSleuth")
st.markdown("### AI Incident Investigator")

st.caption(
    "Explore incident relationships, service dependencies, "
    "correlated alerts, and potential downstream impact."
)

st.divider()


# --------------------------------------------------
# LOAD INVESTIGATION RESULTS
# --------------------------------------------------

if "investigation_results" not in st.session_state:
    st.session_state.investigation_results = None

if investigate_button or st.session_state.investigation_results is None:
    try:
        with st.spinner("Investigating incident through FalkorDB..."):
            st.session_state.investigation_results = (
                investigate_incident(
                    incident_id=incident_id.strip(),
                    display=False,
                )
            )
    except Exception as exc:
        st.error(f"Investigation failed: {exc}")
        st.info(
            "Check your FalkorDB connection and "
            "investigator.py configuration."
        )
        st.stop()

findings = st.session_state.investigation_results

if not findings or not findings.get("found", False):
    st.error(
        findings.get("message", "Incident could not be found.")
        if findings
        else "No investigation results are available."
    )
    st.stop()


# --------------------------------------------------
# EXTRACT INCIDENT DATA
# --------------------------------------------------

affected_service = findings.get("affected_service", "Unknown")
service_status = findings.get("service_status", "Unknown")
severity = findings.get("severity", "Unknown")
incident_title = findings.get("title", "Incident investigation")
incident_status = findings.get("status", "Unknown")

upstream = findings.get("upstream_services", [])
downstream = findings.get("downstream_services", [])

alert_type = findings.get("alert_type")
alert_message = findings.get("alert_message")

# Combine services and deduplicate by name.
services = {
    affected_service: {
        "name": affected_service,
        "status": service_status,
        "role": "Affected service",
        "depth": 0,
    }
}

for item in upstream:
    name = item["name"]
    current = services.get(name)

    if current is None or item.get("depth", 1) < current["depth"]:
        services[name] = {
            "name": name,
            "status": item.get("status", "Unknown"),
            "role": "Upstream dependency",
            "depth": item.get("depth", 1),
        }

for item in downstream:
    name = item["name"]
    current = services.get(name)

    if current is None:
        services[name] = {
            "name": name,
            "status": item.get("status", "Unknown"),
            "role": "Downstream dependent",
            "depth": item.get("depth", 1),
        }

# Unique services other than the affected service.
total_connected = len(services) - 1

direct_downstream = [
    item for item in downstream
    if item.get("depth", 1) == 1
]

indirect_downstream = [
    item for item in downstream
    if item.get("depth", 1) > 1
]


# --------------------------------------------------
# INCIDENT OVERVIEW
# --------------------------------------------------

st.markdown(
    '<div class="section-title">INCIDENT OVERVIEW</div>',
    unsafe_allow_html=True,
)

header_col1, header_col2 = st.columns([3, 1])

with header_col1:
    st.markdown(f"## {escape(str(incident_title))}")
    st.caption(
        f"Incident ID: {findings.get('incident_id', incident_id)}"
    )

with header_col2:
    st.markdown(
        f'<span class="status-pill">'
        f'{escape(str(severity).upper())} SEVERITY'
        f'</span>',
        unsafe_allow_html=True,
    )
    st.caption(f"Incident status: {incident_status}")


# --------------------------------------------------
# TOP METRICS
# --------------------------------------------------

metric1, metric2, metric3, metric4 = st.columns(4)

with metric1:
    st.metric("Affected Service", affected_service)

with metric2:
    st.metric("Service Status", service_status)

with metric3:
    st.metric("Upstream Dependencies", len(upstream))

with metric4:
    st.metric("Downstream Dependents", len(downstream))


# --------------------------------------------------
# MAIN DASHBOARD LAYOUT
# --------------------------------------------------

left_col, right_col = st.columns([1.65, 1])


# --------------------------------------------------
# RELATIONSHIP-DRIVEN DEPENDENCY GRAPH
# --------------------------------------------------

with left_col:
    st.markdown(
        '<div class="section-title">SERVICE DEPENDENCY GRAPH</div>',
        unsafe_allow_html=True,
    )

    try:
        edges = get_dependency_edges(affected_service)
    except Exception as exc:
        edges = []
        st.warning(f"Could not load dependency edges: {exc}")

    # Keep only edges between services returned by the investigation.
    edges = [
        edge for edge in edges
        if edge.get("source") in services
        and edge.get("target") in services
    ]

    if len(services) == 1:
        st.info("Only the affected service was found.")

    elif not edges:
        st.warning(
            "No dependency edges were returned. "
            "Check the service relationships in FalkorDB."
        )

    else:
        graph_data = {
            "nodes": [
                {
                    "id": item["name"],
                    "status": item["status"],
                    "role": item["role"],
                    "depth": item["depth"],
                    "affected": item["name"] == affected_service,
                }
                for item in services.values()
            ],
            "edges": edges,
        }

        # Escape closing script sequences before embedding JSON.
        graph_json = json.dumps(graph_data).replace("</", "<\\/")

        graph_html = """
        <div style="
            background:#0f172a;
            border:1px solid #263449;
            border-radius:12px;
            overflow:hidden;
        ">
          <div style="
              padding:12px;
              color:#cbd5e1;
              font:12px Arial,sans-serif;
          ">
            Drag nodes to rearrange the graph.
            Arrows show dependency direction.
          </div>

          <svg id="gs-graph"
               viewBox="0 0 760 540"
               style="width:100%;height:auto;display:block;
                      background:#0f172a;">
          </svg>

          <div style="
              padding:10px 14px;
              color:#94a3b8;
              font:11px Arial,sans-serif;
          ">
            <span style="color:#f87171;">●</span> Affected
            &nbsp;&nbsp;
            <span style="color:#4ade80;">●</span> Healthy
            &nbsp;&nbsp;
            <span style="color:#fbbf24;">●</span> Other status
          </div>
        </div>

        <script>
        (() => {
            const data = __GRAPH_DATA__;
            const svg = document.getElementById("gs-graph");
            if (!svg) return;

            const NS = "http://www.w3.org/2000/svg";
            const W = 760, H = 540;
            const nodes = data.nodes;
            const edges = data.edges;
            const positions = {};
            const nodeWidth = 174;
            const nodeHeight = 64;

            function el(tag, attrs = {}) {
                const item = document.createElementNS(NS, tag);
                Object.entries(attrs).forEach(([key, value]) =>
                    item.setAttribute(key, value)
                );
                return item;
            }

            // Put the affected service near the center.
            positions[nodes[0].id] = {x: W / 2, y: H / 2};

            // Place other services around the center initially.
            const others = nodes.slice(1);
            others.forEach((node, index) => {
                const angle = (2 * Math.PI * index /
                    Math.max(others.length, 1)) - Math.PI / 2;
                const radius = others.length <= 2 ? 150 : 195;
                positions[node.id] = {
                    x: W / 2 + radius * Math.cos(angle),
                    y: H / 2 + radius * Math.sin(angle)
                };
            });

            const defs = el("defs");
            const marker = el("marker", {
                id: "gs-arrow",
                markerWidth: 9,
                markerHeight: 9,
                refX: 8,
                refY: 3,
                orient: "auto",
                markerUnits: "strokeWidth"
            });
            marker.appendChild(el("path", {
                d: "M0,0 L0,6 L8,3 z",
                fill: "#94a3b8"
            }));
            defs.appendChild(marker);
            svg.appendChild(defs);

            const edgeLayer = el("g");
            const nodeLayer = el("g");
            svg.appendChild(edgeLayer);
            svg.appendChild(nodeLayer);

            const edgeItems = [];
            edges.forEach(edge => {
                const line = el("line", {
                    stroke: "#94a3b8",
                    "stroke-width": 2,
                    "marker-end": "url(#gs-arrow)"
                });

                const label = el("text", {
                    fill: "#94a3b8",
                    "font-size": 10,
                    "text-anchor": "middle"
                });
                label.textContent = "DEPENDS_ON";

                edgeLayer.appendChild(line);
                edgeLayer.appendChild(label);
                edgeItems.push({edge, line, label});
            });

            const nodeItems = [];

            nodes.forEach(node => {
                const group = el("g", {cursor: "grab"});

                const healthy =
                    String(node.status).toLowerCase() === "healthy";

                const fill = node.affected
                    ? "#7f1d1d"
                    : healthy ? "#14532d" : "#78350f";

                const stroke = node.affected
                    ? "#f87171"
                    : healthy ? "#4ade80" : "#fbbf24";

                group.appendChild(el("rect", {
                    x: -nodeWidth / 2,
                    y: -nodeHeight / 2,
                    width: nodeWidth,
                    height: nodeHeight,
                    rx: 10,
                    fill,
                    stroke,
                    "stroke-width": 1.5
                }));

                const title = el("text", {
                    x: 0,
                    y: -5,
                    fill: "#f8fafc",
                    "font-size": 12,
                    "font-weight": "bold",
                    "text-anchor": "middle"
                });
                title.textContent = node.id;

                const subtitle = el("text", {
                    x: 0,
                    y: 15,
                    fill: "#cbd5e1",
                    "font-size": 11,
                    "text-anchor": "middle"
                });
                subtitle.textContent = node.affected
                    ? "Affected service"
                    : node.status + " · Level " + node.depth;

                group.appendChild(title);
                group.appendChild(subtitle);
                nodeLayer.appendChild(group);

                nodeItems.push({node, group});

                let dragging = false;

                group.addEventListener("pointerdown", event => {
                    dragging = true;
                    group.setPointerCapture(event.pointerId);
                    group.style.cursor = "grabbing";
                });

                group.addEventListener("pointermove", event => {
                    if (!dragging) return;

                    const point = svg.createSVGPoint();
                    point.x = event.clientX;
                    point.y = event.clientY;

                    const matrix = svg.getScreenCTM();
                    if (!matrix) return;

                    const local = point.matrixTransform(matrix.inverse());

                    positions[node.id] = {
                        x: Math.max(
                            nodeWidth / 2,
                            Math.min(W - nodeWidth / 2, local.x)
                        ),
                        y: Math.max(
                            nodeHeight / 2,
                            Math.min(H - nodeHeight / 2, local.y)
                        )
                    };

                    render();
                });

                function stopDragging() {
                    dragging = false;
                    group.style.cursor = "grab";
                }

                group.addEventListener("pointerup", stopDragging);
                group.addEventListener("pointercancel", stopDragging);
            });

            function render() {
                nodeItems.forEach(({node, group}) => {
                    const p = positions[node.id];
                    group.setAttribute(
                        "transform",
                        "translate(" + p.x + "," + p.y + ")"
                    );
                });

                edgeItems.forEach(({edge, line, label}) => {
                    const source = positions[edge.source];
                    const target = positions[edge.target];
                    if (!source || !target) return;

                    const dx = target.x - source.x;
                    const dy = target.y - source.y;
                    const distance = Math.max(
                        Math.sqrt(dx * dx + dy * dy), 1
                    );

                    const ux = dx / distance;
                    const uy = dy / distance;

                    const startX = source.x + ux * 88;
                    const startY = source.y + uy * 34;
                    const endX = target.x - ux * 91;
                    const endY = target.y - uy * 37;

                    line.setAttribute("x1", startX);
                    line.setAttribute("y1", startY);
                    line.setAttribute("x2", endX);
                    line.setAttribute("y2", endY);

                    label.setAttribute(
                        "x", (startX + endX) / 2
                    );
                    label.setAttribute(
                        "y", (startY + endY) / 2 - 8
                    );
                });
            }

            render();
        })();
        </script>
        """

        graph_html = graph_html.replace(
            "__GRAPH_DATA__",
            graph_json,
        )

        components.html(
            graph_html,
            height=590,
            scrolling=True,
        )

    st.caption(
        "Edges come from FalkorDB. A DEPENDS_ON arrow points "
        "from the dependent service to the service it relies on."
    )


# --------------------------------------------------
# INVESTIGATION FINDINGS
# --------------------------------------------------

with right_col:
    st.markdown(
        '<div class="section-title">INVESTIGATION FINDINGS</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="panel">
            <div style="color:#93c5fd;font-weight:700;
                        margin-bottom:8px">
                Observed Finding
            </div>
            <div>{escape(str(findings.get(
                "finding", "No finding available."
            )))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if alert_type or alert_message:
        st.markdown(
            f"""
            <div class="panel">
                <div style="color:#fbbf24;font-weight:700;
                            margin-bottom:8px">
                    Correlated Alert
                </div>
                <div><b>Type:</b>
                    {escape(str(alert_type or "Unknown"))}
                </div>
                <div style="margin-top:8px">
                    {escape(str(
                        alert_message or "No alert message available."
                    ))}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="panel">
            <div style="color:#a7f3d0;font-weight:700;
                        margin-bottom:8px">
                Recommended Next Step
            </div>
            <div>{escape(str(findings.get(
                "recommendation",
                "Review linked alerts and dependencies."
            )))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not findings.get("root_cause_confirmed", False):
        st.warning(
            "Root cause is not confirmed. These results show "
            "recorded relationships and observed service status."
        )


# --------------------------------------------------
# BLAST RADIUS SUMMARY
# --------------------------------------------------

st.divider()

st.markdown(
    '<div class="section-title">BLAST RADIUS SUMMARY</div>',
    unsafe_allow_html=True,
)

st.caption(
    "Direct and indirect relationships discovered through "
    "multi-hop graph traversal."
)

blast1, blast2, blast3, blast4 = st.columns(4)

with blast1:
    st.metric("Affected Service", affected_service)

with blast2:
    st.metric("Connected Services", total_connected)

with blast3:
    st.metric("Direct Dependents", len(direct_downstream))

with blast4:
    st.metric("Indirect Dependents", len(indirect_downstream))


blast_left, blast_right = st.columns(2)

with blast_left:
    st.markdown("#### Upstream Dependencies")

    if upstream:
        upstream_df = pd.DataFrame([
            {
                "Service": item["name"],
                "Status": item.get("status", "Unknown"),
                "Depth": item.get("depth", 1),
                "Relationship": (
                    "Direct" if item.get("depth", 1) == 1
                    else "Indirect"
                ),
            }
            for item in upstream
        ])

        st.dataframe(
            upstream_df.sort_values("Depth"),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No upstream dependencies found.")

with blast_right:
    st.markdown("#### Downstream Dependents")

    if downstream:
        downstream_df = pd.DataFrame([
            {
                "Service": item["name"],
                "Status": item.get("status", "Unknown"),
                "Depth": item.get("depth", 1),
                "Impact Level": (
                    "Direct" if item.get("depth", 1) == 1
                    else "Indirect"
                ),
            }
            for item in downstream
        ])

        st.dataframe(
            downstream_df.sort_values("Depth"),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No downstream dependents found.")

st.markdown("#### Potential Impact Paths")

if downstream:
    for item in sorted(
        downstream,
        key=lambda entry: entry.get("depth", 1),
    ):
        depth = item.get("depth", 1)
        impact_type = (
            "Direct dependent" if depth == 1
            else "Indirect dependent"
        )

        st.markdown(
            f"- **Level {depth} — {item['name']}** "
            f"({item.get('status', 'Unknown')}) · {impact_type}"
        )
else:
    st.info("No downstream impact paths were found.")

st.info(
    f"GraphSleuth found {total_connected} unique connected "
    f"service(s) around {affected_service}, including "
    f"{len(direct_downstream)} direct and "
    f"{len(indirect_downstream)} indirect downstream dependent(s). "
    "Connected services are not necessarily confirmed to be impacted."
)


# --------------------------------------------------
# DEPENDENCY ANALYSIS — PATH-FIRST VIEW
# --------------------------------------------------

st.divider()
st.markdown(
    '<div class="section-title">DEPENDENCY ANALYSIS</div>',
    unsafe_allow_html=True,
)
st.markdown("## How services connect to the affected service")
st.caption(
    "Paths are derived from recorded DEPENDS_ON relationships. "
    "A dependency indicates potential impact, not confirmed service failure."
)

path_metric1, path_metric2, path_metric3 = st.columns(3)
with path_metric1:
    st.metric("Affected service", affected_service)
with path_metric2:
    st.metric("Direct dependents", len(direct_downstream))
with path_metric3:
    st.metric("Indirect dependents", len(indirect_downstream))

if downstream:
    ordered_dependents = sorted(
        downstream,
        key=lambda item: (item.get("depth", 1), item.get("name", "")),
    )

    for item in ordered_dependents:
        service_name = str(item.get("name", "Unknown"))
        depth = int(item.get("depth", 1) or 1)
        status = str(item.get("status", "Unknown"))
        is_direct = depth == 1
        relation_label = "DIRECT DEPENDENT" if is_direct else "INDIRECT DEPENDENT"
        relation_color = "#34d399" if is_direct else "#fbbf24"
        status_color = (
            "#34d399" if status.lower() == "healthy"
            else "#f87171" if status.lower() in {"down", "failed", "unhealthy", "critical"}
            else "#fbbf24"
        )

        with st.container(border=True):
            title_col, relation_col = st.columns([3, 1])
            with title_col:
                st.markdown(f"### {escape(service_name)}")
                st.caption(f"Traversal depth: {depth} hop{'s' if depth != 1 else ''}")
            with relation_col:
                st.markdown(
                    f'<div style="text-align:right;padding-top:8px;'
                    f'color:{relation_color};font-size:11px;font-weight:800;'
                    f'letter-spacing:1px">{relation_label}</div>',
                    unsafe_allow_html=True,
                )

            if is_direct:
                path_text = f"{service_name}  →  {affected_service}"
            else:
                # The graph traversal supplies depth, not necessarily every intermediate
                # node for every result; avoid fabricating a full path here.
                path_text = f"{service_name}  →  …  →  {affected_service}"

            st.code(path_text, language=None)
            st.markdown(
                f'<span style="color:#94a3b8;font-size:12px">Observed status:</span> '
                f'<span style="color:{status_color};font-weight:700">{escape(status)}</span>',
                unsafe_allow_html=True,
            )
else:
    st.info("No downstream dependent services were returned by the graph traversal.")

with st.container(border=True):
    st.markdown("**Evidence and interpretation**")
    evidence_col1, evidence_col2 = st.columns(2)
    with evidence_col1:
        st.markdown("**Graph traversal**")
        st.caption("Finds direct and multi-hop dependent services and their depth.")
    with evidence_col2:
        st.markdown("**Relationship edges**")
        st.caption("DEPENDS_ON arrows point from the dependent service to its dependency.")
    st.warning(
        "Potential impact only: validate health checks, latency, logs, and traces "
        "before concluding that a dependent service is degraded or that root cause is confirmed."
    )


# --------------------------------------------------
# CORRELATED ALERT DETAILS
# --------------------------------------------------

st.divider()

st.markdown(
    '<div class="section-title">CORRELATED ALERT DETAILS</div>',
    unsafe_allow_html=True,
)

if alert_type or alert_message:
    alert_df = pd.DataFrame([
        {
            "Incident ID": findings.get("incident_id", incident_id),
            "Severity": severity,
            "Alert Type": alert_type or "Unknown",
            "Alert Message": alert_message or "No message",
            "Affected Service": affected_service,
            "Service Status": service_status,
        }
    ])

    st.dataframe(
        alert_df,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No linked alert details were returned for this incident.")


# --------------------------------------------------
# ANALYST WORKSPACE — GROQ AI ASSISTANT
# --------------------------------------------------

st.divider()

st.markdown(
    '<div class="section-title">AI ANALYST WORKSPACE</div>',
    unsafe_allow_html=True,
)
st.markdown(
    "Ask questions about this incident. The Groq agent can select read-only "
    "MCP tools to retrieve additional graph evidence from FalkorDB."
)
st.caption(
    "AI responses may contain hypotheses. Verify important conclusions "
    "against operational telemetry before taking action."
)

# Keep the conversation in Streamlit session state across reruns.
if "ai_chat_history" not in st.session_state:
    st.session_state.ai_chat_history = []

current_incident_id = str(findings.get("incident_id", incident_id)).strip()
if "ai_chat_incident_id" not in st.session_state:
    st.session_state.ai_chat_incident_id = current_incident_id
elif st.session_state.ai_chat_incident_id != current_incident_id:
    # Do not mix evidence or conversation from different incidents.
    st.session_state.ai_chat_history = []
    st.session_state.ai_chat_incident_id = current_incident_id

if st.button("🧹 Clear conversation", key="clear_ai_chat"):
    st.session_state.ai_chat_history = []
    st.rerun()

# Show previous messages before the input box.
for chat_item in st.session_state.ai_chat_history:
    with st.chat_message(chat_item["role"]):
        st.markdown(chat_item["content"])

question = st.chat_input(
    "Ask GraphSleuth about this incident...",
    key="graphsleuth_ai_question",
)

if question:
    clean_question = question.strip()
    if not clean_question:
        st.warning("Please enter a question.")
    else:
        # Preserve only previous turns as context for the current request.
        previous_history = list(st.session_state.ai_chat_history)
        st.session_state.ai_chat_history.append(
            {"role": "user", "content": clean_question}
        )

        with st.chat_message("user"):
            st.markdown(clean_question)

        with st.chat_message("assistant"):
            try:
                with st.spinner("GraphSleuth is analyzing the incident evidence..."):
                    ai_answer = answer_question_with_mcp(
                        question=clean_question,
                        findings=findings,
                        graph_edges=edges,
                        chat_history=previous_history,
                    )
                st.markdown(ai_answer)

                # Show the actual MCP tool calls made for this answer.
                tool_trace = get_last_tool_trace()
                st.session_state["last_mcp_tool_trace"] = tool_trace
                with st.expander(
                    f"🧰 MCP execution trace · {len(tool_trace)} tool call(s)",
                    expanded=bool(tool_trace),
                ):
                    if not tool_trace:
                        st.info(
                            "No MCP tool was called for this answer. "
                            "The agent answered using the supplied incident evidence."
                        )
                    else:
                        for index, item in enumerate(tool_trace, start=1):
                            status = item.get("status", "unknown")
                            st.markdown(
                                f"**{index}. {item.get('tool', 'Unknown tool')}** "
                                f"· Round {item.get('round', '?')} · `{status}`"
                            )
                            st.caption("Arguments selected by the agent")
                            st.json(item.get("arguments", {}), expanded=False)
                            st.caption("Returned evidence summary")
                            st.json(item.get("result", {}), expanded=False)
                        st.caption(
                            "Trace records the tool calls and returned data for this response. "
                            "A tool result is evidence, not proof of service failure."
                        )

                st.session_state.ai_chat_history.append(
                    {"role": "assistant", "content": ai_answer}
                )
            except Exception as exc:
                # Show a useful error without exposing credentials or secret values.
                error_text = str(exc)
                st.error(
                    "The AI assistant could not answer this question. "
                    "Check that mcp_agent.py and mcp_server.py are present, "
                    "GROQ_API_KEY is configured in .env, and your Groq model/API access is valid."
                )
                st.caption(f"Technical detail: {error_text[:300]}")
                st.session_state.ai_chat_history.append(
                    {
                        "role": "assistant",
                        "content": (
                            "I could not generate an answer for this request. "
                            "Please check the Groq configuration and try again."
                        ),
                    }
                )

st.caption(
    "GraphSleuth is a graph-based investigation prototype. "
    "Verify findings against operational telemetry before remediation."
)
