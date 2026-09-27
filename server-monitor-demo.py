import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import textwrap

# --- ページ設定 ---
st.set_page_config(
    page_title="Infrastructure NOC Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- カスタム CSS (フォーマル・ダークテーマ) ---
st.markdown("""
<style>
    .stApp {
        background-color: #0b0e14;
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    .dashboard-header {
        border-bottom: 1px solid #21262d;
        padding-bottom: 16px;
        margin-bottom: 24px;
    }
    .dashboard-title {
        font-size: 1.55rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        color: #f0f6fc;
        margin: 0;
    }
    .dashboard-subtitle {
        font-size: 0.85rem;
        color: #8b949e;
        margin-top: 4px;
        letter-spacing: 0.3px;
    }
    .kpi-container {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 14px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3);
    }
    .kpi-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #8b949e;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #f0f6fc;
        margin-top: 4px;
    }
    .server-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 8px;
        min-height: 220px;
        box-sizing: border-box;
    }
    .server-card.nominal { border-top: 3px solid #238636; }
    .server-card.elevated { border-top: 3px solid #d29922; }
    .server-card.critical { border-top: 3px solid #da3633; }
    .server-card.offline  { border-top: 3px solid #6e7681; }

    .node-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #f0f6fc;
        margin-bottom: 2px;
    }
    .node-ip {
        font-size: 0.75rem;
        color: #8b949e;
        font-family: monospace;
        margin-bottom: 12px;
    }
    .badge {
        display: inline-block;
        padding: 2px 8px;
        font-size: 0.72rem;
        font-weight: 600;
        border-radius: 4px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 12px;
    }
    .badge-nominal  { background: rgba(35, 134, 54, 0.2); color: #3fb950; border: 1px solid #238636; }
    .badge-elevated { background: rgba(210, 153, 34, 0.2); color: #e3b341; border: 1px solid #bb8009; }
    .badge-critical { background: rgba(218, 54, 51, 0.2);  color: #f85149; border: 1px solid #da3633; }
    .badge-offline  { background: rgba(110, 118, 129, 0.2); color: #8b949e; border: 1px solid #484f58; }

    .metric-row {
        display: flex;
        justify-content: space-between;
        font-size: 0.82rem;
        padding: 4px 0 2px 0;
        border-bottom: 1px solid #21262d;
        color: #c9d1d9;
    }
    .metric-label { color: #8b949e; }
    .metric-val { font-family: monospace; font-weight: 600; }

    .bar-bg {
        width: 100%;
        background-color: #21262d;
        height: 5px;
        border-radius: 3px;
        margin-top: 4px;
        margin-bottom: 10px;
        overflow: hidden;
    }
    .bar-fill {
        height: 100%;
        border-radius: 3px;
    }
    .section-header {
        font-size: 1.05rem;
        font-weight: 600;
        letter-spacing: 0.3px;
        color: #f0f6fc;
        border-bottom: 1px solid #30363d;
        padding-bottom: 8px;
        margin-top: 24px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# --- サーバ定義 ---
SERVER_DEFINITIONS = [
    {"id": "srv-01", "name": "PRD-WEB-01", "ip": "10.100.1.10", "role": "Edge Gateway"},
    {"id": "srv-02", "name": "PRD-APP-01", "ip": "10.100.2.11", "role": "Microservice Host"},
    {"id": "srv-03", "name": "PRD-APP-02", "ip": "10.100.2.12", "role": "Microservice Host"},
    {"id": "srv-04", "name": "PRD-DAT-01", "ip": "10.100.3.20", "role": "Database Primary"},
    {"id": "srv-05", "name": "PRD-WRK-01", "ip": "10.100.4.31", "role": "Queue Worker"},
]

def get_node_metrics(server_id):
    np.random.seed(int(server_id.split("-")[1]) + int(time.time() // 8))
    if server_id == "srv-05":
        status = np.random.choice(["CRITICAL", "OFFLINE"], p=[0.75, 0.25])
        cpu = np.random.uniform(94.0, 99.8)
        mem = np.random.uniform(92.0, 98.5)
        disk = 92.4
        latency = np.random.uniform(320.0, 850.0) if status == "CRITICAL" else 0.0
    elif server_id == "srv-03":
        status = "ELEVATED"
        cpu = np.random.uniform(78.0, 87.5)
        mem = np.random.uniform(81.0, 89.0)
        disk = 79.1
        latency = np.random.uniform(45.0, 90.0)
    else:
        status = "NOMINAL"
        cpu = np.random.uniform(15.0, 42.0)
        mem = np.random.uniform(32.0, 58.0)
        disk = 52.3
        latency = np.random.uniform(4.0, 18.0)
        
    return {
        "status": status,
        "cpu": round(cpu, 1),
        "mem": round(mem, 1),
        "disk": round(disk, 1),
        "latency": round(latency, 1),
        "checked_at": datetime.now().strftime("%H:%M:%S UTC")
    }

def get_historical_metrics(server_id, base_cpu, base_mem):
    now = datetime.now()
    timestamps = [now - timedelta(minutes=5 * i) for i in range(36)][::-1]
    noise_cpu = np.random.normal(0, 4, len(timestamps))
    noise_mem = np.random.normal(0, 2, len(timestamps))
    return pd.DataFrame({
        "Timestamp": timestamps,
        "CPU Utilization (%)": np.clip(base_cpu + noise_cpu, 2, 100),
        "Memory Allocated (%)": np.clip(base_mem + noise_mem, 5, 100)
    })

nodes = []
for item in SERVER_DEFINITIONS:
    m = get_node_metrics(item["id"])
    nodes.append({**item, **m})
df_nodes = pd.DataFrame(nodes)

# --- ヘッダー ---
col_head, col_ctrl = st.columns([3, 1])
with col_head:
    st.markdown("""
    <div class="dashboard-header">
        <h1 class="dashboard-title">OPERATIONAL INFRASTRUCTURE MONITOR</h1>
        <div class="dashboard-subtitle">MISSION CRITICAL CLUSTER TELEMETRY & NODE HEALTH DIAGNOSTICS</div>
    </div>
    """, unsafe_allow_html=True)

with col_ctrl:
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        auto_refresh = st.checkbox("Auto Refresh (10s)", value=False)
    with col_c2:
        if st.button("Manual Sync", use_container_width=True):
            st.rerun()

# --- KPI カウンター ---
nominal_cnt = (df_nodes["status"] == "NOMINAL").sum()
elevated_cnt = (df_nodes["status"] == "ELEVATED").sum()
critical_cnt = (df_nodes["status"].isin(["CRITICAL", "OFFLINE"])).sum()
avg_ping = df_nodes[df_nodes["status"] != "OFFLINE"]["latency"].mean()

k1, k2, k3, k4 = st.columns(4)
k1.markdown(textwrap.dedent(f"""
<div class="kpi-container">
    <div class="kpi-label">System State</div>
    <div class="kpi-value" style="color: {'#f85149' if critical_cnt > 0 else ('#e3b341' if elevated_cnt > 0 else '#3fb950')};">
        {'DEGRADED' if critical_cnt > 0 else ('WARNING' if elevated_cnt > 0 else 'OPERATIONAL')}
    </div>
</div>
"""), unsafe_allow_html=True)

k2.markdown(textwrap.dedent(f"""
<div class="kpi-container">
    <div class="kpi-label">Active Nodes</div>
    <div class="kpi-value">{nominal_cnt} <span style="font-size: 0.9rem; color: #8b949e; font-weight: normal;">/ 5 NODES</span></div>
</div>
"""), unsafe_allow_html=True)

k3.markdown(textwrap.dedent(f"""
<div class="kpi-container">
    <div class="kpi-label">Anomalies Detected</div>
    <div class="kpi-value" style="color: {'#f85149' if critical_cnt > 0 else '#8b949e'};">{critical_cnt + elevated_cnt}</div>
</div>
"""), unsafe_allow_html=True)

k4.markdown(textwrap.dedent(f"""
<div class="kpi-container">
    <div class="kpi-label">Avg Cluster Latency</div>
    <div class="kpi-value">{avg_ping:.1f} <span style="font-size: 0.9rem; color: #8b949e; font-weight: normal;">ms</span></div>
</div>
"""), unsafe_allow_html=True)

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# --- ノード死活一覧 (5カラム表示) ---
st.markdown('<div class="section-header">NODE FLEET STATUS OVERVIEW</div>', unsafe_allow_html=True)

status_meta = {
    "NOMINAL": {"badge_cls": "badge-nominal", "cls": "nominal", "label": "NOMINAL", "bar_color": "#238636"},
    "ELEVATED": {"badge_cls": "badge-elevated", "cls": "elevated", "label": "ELEVATED", "bar_color": "#bb8009"},
    "CRITICAL": {"badge_cls": "badge-critical", "cls": "critical", "label": "CRITICAL", "bar_color": "#da3633"},
    "OFFLINE": {"badge_cls": "badge-offline", "cls": "offline", "label": "OFFLINE", "bar_color": "#484f58"}
}

card_cols = st.columns(5)
for i, node in enumerate(nodes):
    meta = status_meta.get(node["status"])
    with card_cols[i]:
        # textwrap.dedentによりMarkdownインデント誤判定を防止
        card_content = textwrap.dedent(f"""
        <div class="server-card {meta['cls']}">
            <div class="node-title">{node['name']}</div>
            <div class="node-ip">{node['ip']} &bull; {node['role']}</div>
            <span class="badge {meta['badge_cls']}">{meta['label']}</span>
            <div class="metric-row">
                <span class="metric-label">CPU LOAD</span>
                <span class="metric-val">{node['cpu']}%</span>
            </div>
            <div class="bar-bg">
                <div class="bar-fill" style="width: {node['cpu']}%; background-color: {meta['bar_color']};"></div>
            </div>
            <div class="metric-row">
                <span class="metric-label">MEMORY</span>
                <span class="metric-val">{node['mem']}%</span>
            </div>
            <div class="bar-bg">
                <div class="bar-fill" style="width: {node['mem']}%; background-color: {meta['bar_color']};"></div>
            </div>
            <div class="metric-row" style="border: none; padding-top: 6px;">
                <span class="metric-label">RTT</span>
                <span class="metric-val">{node['latency']} ms</span>
            </div>
        </div>
        """).strip()
        st.markdown(card_content, unsafe_allow_html=True)

# --- 詳細ドリルダウン ---
st.markdown('<div class="section-header">TELEMETRY DEEP-DIVE & DIAGNOSTIC INSPECTOR</div>', unsafe_allow_html=True)

critical_nodes = [n["name"] for n in nodes if n["status"] in ["CRITICAL", "OFFLINE"]]
warning_nodes = [n["name"] for n in nodes if n["status"] == "ELEVATED"]
default_selected_name = critical_nodes[0] if critical_nodes else (warning_nodes[0] if warning_nodes else nodes[0]["name"])

node_names = [n["name"] for n in nodes]
selected_node_name = st.selectbox(
    "Target Node Inspection Selector:",
    options=node_names,
    index=node_names.index(default_selected_name)
)

selected = next(n for n in nodes if n["name"] == selected_node_name)

if selected["status"] in ["CRITICAL", "OFFLINE"]:
    st.markdown(f"""
    <div style="background: rgba(218, 54, 51, 0.12); border-left: 4px solid #da3633; padding: 12px 16px; border-radius: 4px; margin-bottom: 16px;">
        <span style="font-weight: 700; color: #f85149;">ALERT LEVEL 1: CRITICAL INCIDENT DETECTED</span><br>
        <span style="font-size: 0.85rem; color: #c9d1d9;">Target node <b>{selected['name']}</b> ({selected['ip']}) exceeds thermal/resource ceiling or fails heartbeat check. Recommended triage: Inspect process stack & active worker queues.</span>
    </div>
    """, unsafe_allow_html=True)
elif selected["status"] == "ELEVATED":
    st.markdown(f"""
    <div style="background: rgba(210, 153, 34, 0.12); border-left: 4px solid #d29922; padding: 12px 16px; border-radius: 4px; margin-bottom: 16px;">
        <span style="font-weight: 700; color: #e3b341;">ALERT LEVEL 2: CAPACITY WARNING</span><br>
        <span style="font-size: 0.85rem; color: #c9d1d9;">Target node <b>{selected['name']}</b> exhibits sustained pressure beyond 75% operational threshold.</span>
    </div>
    """, unsafe_allow_html=True)

m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
with m_col1:
    st.metric("CPU UTILIZATION", f"{selected['cpu']}%", delta=f"{selected['cpu']-50.0:+.1f}%" if selected['cpu']>50 else None, delta_color="inverse")
with m_col2:
    st.metric("MEMORY ALLOCATION", f"{selected['mem']}%", delta=f"{selected['mem']-60.0:+.1f}%" if selected['mem']>60 else None, delta_color="inverse")
with m_col3:
    st.metric("STORAGE VOLUME", f"{selected['disk']}%")
with m_col4:
    st.metric("ICMP ROUNDTRIP", f"{selected['latency']} ms")
with m_col5:
    st.metric("TELEMETRY SYNC", selected['checked_at'])

# チャート
c_left, c_right = st.columns([7, 3])
df_hist = get_historical_metrics(selected["id"], selected["cpu"], selected["mem"])

with c_left:
    st.markdown("<div style='font-size: 0.85rem; font-weight: 600; color: #8b949e; margin-bottom: 8px;'>REAL-TIME HISTORICAL UTILIZATION (LAST 3 HOURS)</div>", unsafe_allow_html=True)
    fig = px.line(
        df_hist,
        x="Timestamp",
        y=["CPU Utilization (%)", "Memory Allocated (%)"],
        color_discrete_map={"CPU Utilization (%)": "#58a6ff", "Memory Allocated (%)": "#3fb950"}
    )
    fig.add_hline(y=85, line_dash="dot", line_color="#da3633", annotation_text="CRITICAL THRESHOLD (85%)", annotation_font_color="#f85149", annotation_position="top right")
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        font=dict(color="#8b949e", family="monospace", size=10),
        margin=dict(l=30, r=20, t=10, b=20),
        height=280,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None, font=dict(size=11, color="#c9d1d9")),
        xaxis=dict(showgrid=True, gridcolor="#21262d"),
        yaxis=dict(showgrid=True, gridcolor="#21262d", range=[0, 105])
    )
    st.plotly_chart(fig, use_container_width=True)

with c_right:
    st.markdown("<div style='font-size: 0.85rem; font-weight: 600; color: #8b949e; margin-bottom: 8px;'>ROOT STORAGE ALLOCATION</div>", unsafe_allow_html=True)
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=selected["disk"],
        number={'suffix': "%", 'font': {'color': '#f0f6fc', 'family': 'monospace', 'size': 26}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': '#8b949e', 'tickwidth': 1},
            'bar': {'color': '#da3633' if selected["disk"] > 85 else ('#d29922' if selected["disk"] > 70 else '#238636'), 'thickness': 0.3},
            'bgcolor': '#21262d',
            'borderwidth': 0,
            'steps': [
                {'range': [0, 70], 'color': '#0d1117'},
                {'range': [70, 85], 'color': '#1f1a14'},
                {'range': [85, 100], 'color': '#2a1415'}
            ],
            'threshold': {'line': {'color': '#f85149', 'width': 2}, 'thickness': 0.8, 'value': 90}
        }
    ))
    fig_gauge.update_layout(
        template="plotly_dark",
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        margin=dict(l=20, r=20, t=20, b=20),
        height=280
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

# システムログ
with st.expander("TERMINAL EXECUTION LOG / AUDIT TRAIL", expanded=(selected["status"] in ["CRITICAL", "OFFLINE"])):
    curr_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    if selected["status"] in ["CRITICAL", "OFFLINE"]:
        log_sample = f"""[{curr_time}.012Z] [CRIT] [sys-telemetry] Heartbeat timeout on {selected['ip']}: icmp_seq=3 Destination Host Unreachable
[{curr_time}.084Z] [WARN] [kernel] high loadavg detected: 14.82, 11.20, 8.44
[{curr_time}.129Z] [EMERG] [oom-killer] Node memory budget exhausted (used: {selected['mem']}%). Invoking oom-reaper on cgroup /system.slice/worker.service
[{curr_time}.201Z] [ALERT] [daemon] Process [pid:4812] terminated with SIGKILL (Exit code 137)
[{curr_time}.340Z] [INFO] [orchestrator] Automated remediation triggered: restarting worker service"""
    elif selected["status"] == "ELEVATED":
        log_sample = f"""[{curr_time}.010Z] [WARN] [sys-telemetry] CPU threshold trigger (>75%) on core 0, 1, 2
[{curr_time}.045Z] [INFO] [traffic-shaper] Re-routing 20% inbound connections to cluster peer
[{curr_time}.090Z] [INFO] [audit] GC sweep completed in 142ms, reclaimed 340MB"""
    else:
        log_sample = f"""[{curr_time}.001Z] [INFO] [sys-telemetry] Status probe OK. 0 packet loss, 12ms jitter.
[{curr_time}.050Z] [INFO] [systemd] Service health-check daemon reports all units healthy.
[{curr_time}.100Z] [INFO] [audit] Security baseline verified. SHA-256 integrity passed."""
    st.code(log_sample, language="log")

if auto_refresh:
    time.sleep(10)
    st.rerun()