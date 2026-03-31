import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

# ==========================================
# 0. PAGE CONFIGURATION & UI SETUP
# ==========================================
# Setting layout to wide to mimic a professional managerial dashboard.
st.set_page_config(page_title="Unified Project Lifecycle Dashboard", layout="wide", page_icon="📊")

# Custom CSS for Material Design 3 tweaks (cleaner fonts, card-like containers)
st.markdown("""
    <style>
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; }
    .st-emotion-cache-1wivap2 { padding-top: 2rem; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. ENUMS & SHARED CONSTANTS
# ==========================================
# Extracted from Blueprint Section 1.5
ENUMS = {
    "coordenacoes": ["CIF", "CIN", "CPQ", "CBT"],
    "linhas_pesquisa": ["DAP", "ESP", "IMS", "SQR", "TAP", "TVB"],
    "financiamento": ["Contratação direta", "EMBRAPII - CG", "EMBRAPII - BFA", "ANP", "Edital SENAI"],
    "tipo_projeto": ["Com fomento", "Sem fomento"],
    "etapa_proposta": ["Prospecção", "Negociação", "Contratação", "Contratado", "Recusado"],
    "status_projeto": ["Inicialização", "Execução", "Finalização", "Encerrado", "Cancelado"],
    "status_tarefa": ["Finalizado", "Atrasado", "Esta semana", "No prazo"],
    "categoria_tarefa": ["Projetos", "Projetos internos", "Prospecções"],
    "status_notion": ["Aguardando", "Em execução", "Finalizado", "Cancelado"],
    "gestores": ["Gustavo", "Raquel", "Sabrina", "Ana", "Igor", "Stefano", "Julliana", "Lidiane"]
}

# ==========================================
# 2. MOCK DATA GENERATION
# ==========================================
# We generate realistic data so the PoC works immediately without files.
def load_mock_data():
    np.random.seed(42)
    random.seed(42)
    
    # Shared Project Names to link across DataFrames
    projects = [f"Project {name}" for name in ["Alpha", "Beta", "Gamma", "Delta", "Echo", "Zeta", "Omega", "Sigma", "Tau", "Phi", "Chi", "Psi", "Rho", "Kappa", "Mu", "Nu"]]
    clients = ["Petrobras", "Eldorado", "Braskem", "Vale", "Natura", "Ambev", "WEG"]

    # --- df_proposals (Sales Pipeline) ---
    proposals_data = {
        "codinome_projeto": projects,
        "cliente": [random.choice(clients) for _ in projects],
        "coordenacao_responsavel": [random.choice(ENUMS["coordenacoes"]) for _ in projects],
        "linha_pesquisa_cpq": [random.choice(ENUMS["linhas_pesquisa"]) for _ in projects],
        "etapa_atual": [random.choice(ENUMS["etapa_proposta"]) for _ in projects],
        "orcamento_total": np.random.uniform(100000, 2000000, len(projects)),
        "orcamento_cpq": np.random.uniform(50000, 1000000, len(projects)),
        "meses_execucao_total": np.random.randint(6, 36, len(projects)),
    }
    df_proposals = pd.DataFrame(proposals_data)

    # --- df_projects (Execution Pipeline) ---
    # Only "Contratado" proposals become projects
    exec_projects = df_proposals[df_proposals["etapa_atual"] == "Contratado"]["codinome_projeto"].tolist()
    # Add a few active ones manually for the dashboard to look populated
    exec_projects += [projects[0], projects[1], projects[2], projects[3], projects[4]] 
    exec_projects = list(set(exec_projects))
    
    today = datetime.today()
    projects_data = {
        "codinome_projeto": exec_projects,
        "status_projeto": [random.choice(ENUMS["status_projeto"]) for _ in exec_projects],
        "orcamento_atualizado": np.random.uniform(500000, 3000000, len(exec_projects)),
        "receita_externa_atualizada": np.random.uniform(400000, 2500000, len(exec_projects)),
        "competencia_acumulada": np.random.uniform(100000, 1500000, len(exec_projects)),
        "linha_pesquisa_cpq": [random.choice(ENUMS["linhas_pesquisa"]) for _ in exec_projects],
        "inicio_escopo_tecnico": [today - timedelta(days=random.randint(30, 300)) for _ in exec_projects],
        "termino_previsto": [today + timedelta(days=random.randint(30, 365)) for _ in exec_projects],
    }
    df_projects = pd.DataFrame(projects_data)

    # --- df_tasks (Weekly Planner) ---
    tasks_data = []
    for i in range(40):
        # Create dates: Some past (Overdue), some this week, some future
        days_offset = random.choice([-10, -5, -1, 0, 2, 4, 15, 30]) 
        tasks_data.append({
            "categoria": random.choice(ENUMS["categoria_tarefa"]),
            "identificacao": f"[{random.choice(clients)}] {random.choice(projects)}",
            "atividade": f"Task description {i}",
            "prazo": today + timedelta(days=days_offset),
            "execucao": random.choice(ENUMS["gestores"]),
            "finalizado": random.choice(["Sim", "Não", "Não", "Não"]), # Weight towards 'Não'
        })
    df_tasks = pd.DataFrame(tasks_data)

    # --- df_allocation (Team Allocation) ---
    allocation_data = []
    for i in range(25):
        start = today + timedelta(days=random.randint(-60, 30))
        allocation_data.append({
            "projeto": random.choice(projects),
            "executor": random.choice(ENUMS["gestores"]),
            "data_inicio": start,
            "data_fim": start + timedelta(days=random.randint(15, 90)),
            "status_notion": random.choice(ENUMS["status_notion"]),
        })
    df_allocation = pd.DataFrame(allocation_data)

    return df_proposals, df_projects, df_tasks, df_allocation

# Initialize Session State Database
if "db_initialized" not in st.session_state:
    p, pr, t, a = load_mock_data()
    st.session_state.df_proposals = p
    st.session_state.df_projects = pr
    st.session_state.df_tasks = t
    st.session_state.df_allocation = a
    st.session_state.db_initialized = True

# Helper to reset data
def reset_database():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==========================================
# 3. BUSINESS LOGIC & CALCS (From Blueprint)
# ==========================================

def compute_task_status(row):
    """Replicates Blueprint Section 2.1 Excel Formula logic."""
    if row.get("finalizado") == "Sim":
        return "Finalizado"
    
    prazo = row.get("prazo")
    if pd.isna(prazo):
        return ""
    
    today = datetime.today().date()
    prazo_date = pd.Timestamp(prazo).date()
    
    if prazo_date < today:
        return "Atrasado"
    
    # Current week boundaries (Monday=0 to Sunday=6)
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    if monday <= prazo_date <= sunday:
        return "Esta semana"
    
    return "No prazo"

def add_status_emoji(status):
    """Blueprint Section 2.2.3: Visual indicator for Streamlit native."""
    mapping = {
        "Atrasado": "🔴 Atrasado",
        "Esta semana": "🟡 Esta semana",
        "No prazo": "🟢 No prazo",
        "Finalizado": "⚪ Finalizado",
    }
    return mapping.get(status, status)

# Update task statuses dynamically based on current data
st.session_state.df_tasks["status"] = st.session_state.df_tasks.apply(compute_task_status, axis=1)
st.session_state.df_tasks["status_ui"] = st.session_state.df_tasks["status"].apply(add_status_emoji)


# ==========================================
# 4. PAGES RENDERING FUNCTIONS
# ==========================================

def render_sales_pipeline():
    st.title("📈 Sales Pipeline (Funil de Vendas)")
    st.markdown("Manage proposals, track budget extrapolations, and convert to active projects.")
    
    df = st.session_state.df_proposals

    # Top KPIs
    c1, c2, c3, c4 = st.columns(4)
    active_mask = df["etapa_atual"].isin(["Prospecção", "Negociação", "Contratação"])
    
    c1.metric("Propostas Ativas", len(df[active_mask]))
    c2.metric("Contratadas", len(df[df["etapa_atual"] == "Contratado"]))
    c3.metric("Orçamento Total (Ativo)", f"R$ {df[active_mask]['orcamento_total'].sum():,.2f}")
    
    ticket_medio = df["orcamento_cpq"].sum() / df["meses_execucao_cpq"].sum() if df["meses_execucao_cpq"].sum() > 0 else 0
    c4.metric("Ticket Médio (CPQ)", f"R$ {ticket_medio:,.2f} / mês")

    st.divider()

    col_chart, col_data = st.columns([1, 1.5])
    
    with col_chart:
        st.subheader("Funnel Visualization")
        # Funnel Logic (Blueprint 4.1.1)
        funnel_data = df[active_mask].groupby("etapa_atual").agg(
            count=("codinome_projeto", "count"),
            orcamento=("orcamento_total", "sum")
        ).reindex(["Prospecção", "Negociação", "Contratação"]).reset_index()

        fig = go.Figure(go.Funnel(
            y=funnel_data["etapa_atual"],
            x=funnel_data["count"],
            textinfo="value+percent initial",
            customdata=funnel_data["orcamento"],
            hovertemplate="Stage: %{y}<br>Count: %{x}<br>Budget: R$ %{customdata:,.2f}<extra></extra>",
            marker={"color": ["#4C78A8", "#F58518", "#54A24B"]}
        ))
        fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with col_data:
        st.subheader("Data Management")
        st.info("💡 Edit cells below to update the database and charts instantly.")
        
        # Editable dataframe acting as our Notion/Excel replacement
        edited_df = st.data_editor(
            df,
            column_config={
                "etapa_atual": st.column_config.SelectboxColumn("Etapa Atual", options=ENUMS["etapa_proposta"], required=True),
                "orcamento_total": st.column_config.NumberColumn("Orçamento (R$)", format="$ %d"),
                "meses_execucao_total": st.column_config.NumberColumn("Meses")
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic" # Allows adding new proposals!
        )
        # Save state back to "DB"
        st.session_state.df_proposals = edited_df

def render_execution_pipeline():
    st.title("🚀 Execution Pipeline (Funil de Projetos)")
    st.markdown("Track active project health, financial execution, and schedules.")

    df = st.session_state.df_projects
    active_mask = df["status_projeto"].isin(["Inicialização", "Execução", "Finalização"])

    # KPIs (Blueprint 4.2.2)
    c1, c2, c3 = st.columns(3)
    carteira_ativa = df[active_mask]["orcamento_atualizado"].sum()
    receita_externa = df[active_mask]["receita_externa_atualizada"].sum()
    competencia = df[active_mask]["competencia_acumulada"].sum()
    
    c1.metric("Carteira Ativa (Orçamento)", f"R$ {carteira_ativa:,.2f}")
    c2.metric("Projetos Ativos", len(df[active_mask]))
    
    # Realização financeira KPI
    realizacao_pct = (competencia / receita_externa * 100) if receita_externa > 0 else 0
    c3.metric("Realização Financeira Geral", f"{realizacao_pct:.1f}%", help="Competência / Receita Externa")

    st.divider()

    # Timeline / Gantt (Blueprint 4.2.4)
    st.subheader("Project Timeline (Gantt)")
    timeline_df = df.dropna(subset=["inicio_escopo_tecnico", "termino_previsto"])
    if not timeline_df.empty:
        fig = px.timeline(
            timeline_df, 
            x_start="inicio_escopo_tecnico", 
            x_end="termino_previsto", 
            y="codinome_projeto",
            color="linha_pesquisa_cpq",
            title="Schedules by Research Line (Linha de Pesquisa)"
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No date data available for timeline.")

    # Data Editor
    st.subheader("Project Execution Data")
    edited_df = st.data_editor(
        df,
        column_config={
            "status_projeto": st.column_config.SelectboxColumn("Status", options=ENUMS["status_projeto"]),
            "orcamento_atualizado": st.column_config.NumberColumn("Orçamento", format="$ %d"),
            "inicio_escopo_tecnico": st.column_config.DateColumn("Início"),
            "termino_previsto": st.column_config.DateColumn("Término")
        },
        use_container_width=True, hide_index=True
    )
    st.session_state.df_projects = edited_df

def render_weekly_tracker():
    st.title("✅ Weekly Planner (Planejamento Semanal)")
    st.markdown("Actionable task tracking with conditional formatting and automated status logic.")

    df = st.session_state.df_tasks

    # Metrics Summary (Blueprint 4.3.1)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 Atrasadas", len(df[df["status"] == "Atrasado"]))
    c2.metric("🟡 Esta Semana", len(df[df["status"] == "Esta semana"]))
    c3.metric("🟢 No Prazo", len(df[df["status"] == "No prazo"]))
    c4.metric("⚪ Finalizadas", len(df[df["status"] == "Finalizado"]))

    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Workload by Category")
        # Stacked Bar (Blueprint 4.3.2)
        chart_data = df[df["status"].isin(["Atrasado", "Esta semana"])].groupby(["categoria", "status"]).size().unstack(fill_value=0).reset_index()
        
        if not chart_data.empty:
            fig = px.bar(
                chart_data, 
                x=["Atrasado", "Esta semana"] if "Atrasado" in chart_data and "Esta semana" in chart_data else chart_data.columns[1:], 
                y="categoria", 
                orientation="h",
                color_discrete_map={"Atrasado": "#C00000", "Esta semana": "#BF8F00"},
                barmode="stack"
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("No delayed or current week tasks! 🎉")

    with col2:
        st.subheader("Task Manager (Edit to Update)")
        # Editable Data Grid with native Streamlit column configurations to emulate styling
        display_cols = ["categoria", "identificacao", "atividade", "prazo", "execucao", "finalizado", "status_ui"]
        
        edited_df = st.data_editor(
            df[display_cols],
            column_config={
                "categoria": st.column_config.SelectboxColumn("Categoria", options=ENUMS["categoria_tarefa"]),
                "finalizado": st.column_config.SelectboxColumn("Finalizado?", options=["Sim", "Não"]),
                "prazo": st.column_config.DateColumn("Prazo"),
                "status_ui": st.column_config.TextColumn("Status Automático", disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic"
        )
        
        # Sync changes back to main dataframe
        # Note: status and status_ui recalculate automatically at the top of the script on next run.
        if not edited_df.equals(df[display_cols]):
            # Merge updates based on index for PoC purposes
            for col in ["categoria", "identificacao", "atividade", "prazo", "execucao", "finalizado"]:
                st.session_state.df_tasks[col] = edited_df[col]
            st.rerun() # Trigger recalculation of task logic

def render_team_allocation():
    st.title("🧑‍🤝‍🧑 Team Allocation (Notion Data)")
    st.markdown("Visualize resource bandwidth, member availability, and project assignments.")

    df = st.session_state.df_allocation
    
    st.subheader("Allocation Gantt Chart")
    
    # Timeline (Blueprint 4.4.1)
    clean_df = df.dropna(subset=["data_inicio", "data_fim"])
    if not clean_df.empty:
        fig = px.timeline(
            clean_df,
            x_start="data_inicio",
            x_end="data_fim",
            y="executor",
            color="status_notion",
            hover_name="projeto",
            color_discrete_map={
                "Em execução": "#2196F3",
                "Aguardando": "#FFC107",
                "Finalizado": "#9E9E9E",
                "Cancelado": "#F44336",
            }
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=500)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Resource Database Editor")
    edited_df = st.data_editor(
        df,
        column_config={
            "status_notion": st.column_config.SelectboxColumn("Status", options=ENUMS["status_notion"]),
            "executor": st.column_config.SelectboxColumn("Executor", options=ENUMS["gestores"]),
            "data_inicio": st.column_config.DateColumn("Início"),
            "data_fim": st.column_config.DateColumn("Fim")
        },
        use_container_width=True, hide_index=True, num_rows="dynamic"
    )
    st.session_state.df_allocation = edited_df

# ==========================================
# 5. SIDEBAR NAVIGATION & ROUTING
# ==========================================
with st.sidebar:
    st.image("https://streamlit.io/images/brand/streamlit-mark-color.png", width=50)
    st.title("Lifecycle PoC")
    st.markdown("Consolidated view of 4 legacy tools.")
    
    page = st.radio(
        "Navigation Menu",
        options=[
            "📈 Sales Pipeline (Vendas)",
            "🚀 Execution Pipeline (Projetos)",
            "✅ Weekly Planner (Tarefas)",
            "🧑‍🤝‍🧑 Team Allocation (Notion)"
        ]
    )
    
    st.divider()
    st.markdown("⚙️ **System Actions**")
    if st.button("Reset Database to Default"):
        reset_database()
    st.caption("Data is stored in Session State. Refreshing the browser or clicking Reset will restore original mock data.")

# Route to the correct page
if page == "📈 Sales Pipeline (Vendas)":
    render_sales_pipeline()
elif page == "🚀 Execution Pipeline (Projetos)":
    render_execution_pipeline()
elif page == "✅ Weekly Planner (Tarefas)":
    render_weekly_tracker()
elif page == "🧑‍🤝‍🧑 Team Allocation (Notion)":
    render_team_allocation()
