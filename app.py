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
st.set_page_config(page_title="Unified Project Lifecycle Dashboard", layout="wide", page_icon="📊")

# Custom CSS for Material Design 3 tweaks
# Using native Streamlit CSS variables (var(--...)) to support both Light and Dark modes natively.
st.markdown("""
    <style>
    [data-testid="stMetric"] { 
        background-color: var(--secondary-background-color); 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid rgba(128, 128, 128, 0.2); 
    }
    .st-emotion-cache-1wivap2 { padding-top: 2rem; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. ENUMS & SHARED CONSTANTS
# ==========================================
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
def load_mock_data():
    np.random.seed(42)
    random.seed(42)
    
    projects = [f"Project {name}" for name in ["Alpha", "Beta", "Gamma", "Delta", "Echo", "Zeta", "Omega", "Sigma", "Tau", "Phi", "Chi", "Psi", "Rho", "Kappa", "Mu", "Nu"]]
    clients = ["Petrobras", "Eldorado", "Braskem", "Vale", "Natura", "Ambev", "WEG"]

    # --- df_proposals ---
    proposals_data = {
        "codinome_projeto": projects,
        "cliente": [random.choice(clients) for _ in projects],
        "coordenacao_responsavel": [random.choice(ENUMS["coordenacoes"]) for _ in projects],
        "linha_pesquisa_cpq": [random.choice(ENUMS["linhas_pesquisa"]) for _ in projects],
        "etapa_atual": [random.choice(ENUMS["etapa_proposta"]) for _ in projects],
        "orcamento_total": np.random.uniform(100000, 2000000, len(projects)),
        "orcamento_cpq": np.random.uniform(50000, 1000000, len(projects)),
        "meses_execucao_total": np.random.randint(6, 36, len(projects)),
        "meses_execucao_cpq": np.random.randint(3, 24, len(projects)),
    }
    df_proposals = pd.DataFrame(proposals_data)

    # --- df_projects ---
    exec_projects = df_proposals[df_proposals["etapa_atual"] == "Contratado"]["codinome_projeto"].tolist()
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
        days_offset = random.choice([-10, -5, -1, 0, 2, 4, 15, 30]) 
        tasks_data.append({
            "categoria": random.choice(ENUMS["categoria_tarefa"]),
            "identificacao": f"[{random.choice(clients)}] {random.choice(projects)}",
            "atividade": f"Atividade descritiva {i}",
            "prazo": today + timedelta(days=days_offset),
            "execucao": random.choice(ENUMS["gestores"]),
            "apoio": random.choice([None, "", random.choice(ENUMS["gestores"])]),
            "observacao": random.choice(["", "Aguardando aprovação", "Revisão pendente do cliente", ""]),
            "finalizado": random.choice(["Sim", "Não", "Não", "Não"]),
        })
    df_tasks = pd.DataFrame(tasks_data)

    # --- df_allocation ---
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

def reset_database():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==========================================
# 3. BUSINESS LOGIC & CALCS
# ==========================================

def compute_task_status(row):
    if row.get("finalizado") == "Sim":
        return "Finalizado"
    
    prazo = row.get("prazo")
    if pd.isna(prazo):
        return ""
    
    today = datetime.today().date()
    prazo_date = pd.Timestamp(prazo).date()
    
    if prazo_date < today:
        return "Atrasado"
    
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    if monday <= prazo_date <= sunday:
        return "Esta semana"
    
    return "No prazo"

def add_status_emoji(status):
    mapping = {
        "Atrasado": "🔴 Atrasado",
        "Esta semana": "🟡 Esta semana",
        "No prazo": "🟢 No prazo",
        "Finalizado": "⚪ Finalizado",
    }
    return mapping.get(status, status)

st.session_state.df_tasks["status"] = st.session_state.df_tasks.apply(compute_task_status, axis=1)
st.session_state.df_tasks["status_ui"] = st.session_state.df_tasks["status"].apply(add_status_emoji)


# ==========================================
# 4. WEEKLY PLANNER REFACTOR HELPERS
# ==========================================

def init_team_members():
    """Initializes and updates the dynamic team members list in session state."""
    if "team_members" not in st.session_state:
        base = set(ENUMS["gestores"])
        df = st.session_state.df_tasks
        if "execucao" in df.columns:
            base.update(df["execucao"].dropna().unique())
        if "apoio" in df.columns:
            base.update(df["apoio"].dropna().unique())
        
        # Clean up nulls or empty strings
        base = {str(m).strip() for m in base if pd.notna(m) and str(m).strip()}
        st.session_state.team_members = sorted(list(base))

def render_team_management():
    """Renders the UI for managing dynamic team members."""
    with st.expander("👥 Gestão de equipe", expanded=False):
        st.write("Membros atuais da equipe:")
        # Render as nice inline tags
        st.markdown(
            " ".join([f"<span style='background-color: var(--secondary-background-color); padding: 4px 8px; border-radius: 12px; font-size: 13px; border: 1px solid rgba(128,128,128,0.2); margin-right: 4px;'>{m}</span>" for m in st.session_state.team_members]), 
            unsafe_allow_html=True
        )
        st.write("")
        c1, c2, c3 = st.columns([2, 1, 2])
        new_member = c1.text_input("Novo membro", key="new_team_member", label_visibility="collapsed", placeholder="Digite o nome...")
        if c2.button("Adicionar", use_container_width=True):
            new_member = new_member.strip()
            if new_member and new_member not in st.session_state.team_members:
                st.session_state.team_members.append(new_member)
                st.session_state.team_members.sort()
                st.success(f"Membro '{new_member}' adicionado!")
                st.rerun()
            elif new_member in st.session_state.team_members:
                st.warning("Este membro já existe.")

def filter_tasks(df):
    """Applies filters to the tasks dataframe."""
    st.markdown("##### 🔍 Filtros de Visualização")
    c1, c2, c3, c4 = st.columns(4)
    
    id_opts = sorted([str(x) for x in df["identificacao"].dropna().unique() if x])
    exec_opts = st.session_state.team_members
    cat_opts = ENUMS["categoria_tarefa"]
    status_opts = ["Atrasado", "Esta semana", "No prazo", "Finalizado"]

    f_id = c1.multiselect("Identificação (Projeto)", id_opts)
    f_exec = c2.multiselect("Executor / Apoio", exec_opts)
    f_cat = c3.multiselect("Categoria", cat_opts)
    f_status = c4.multiselect("Status", status_opts)
        
    mask = pd.Series(True, index=df.index)
    if f_id:
        mask = mask & df["identificacao"].isin(f_id)
    if f_exec:
        # Match Executor OR Apoio
        mask = mask & (df["execucao"].isin(f_exec) | df["apoio"].isin(f_exec))
    if f_cat:
        mask = mask & df["categoria"].isin(f_cat)
    if f_status:
        mask = mask & df["status"].isin(f_status)
        
    return df[mask]

def render_flow_panel(df_active):
    """Renders the continuous operational panel for active tasks."""
    if df_active.empty:
        st.info("Nenhuma atividade ativa corresponde aos filtros no momento.")
        return

    # Sort by Prazo ascending. Naturally puts Atrasado first, then Esta semana, then No prazo
    df_active = df_active.sort_values(by="prazo", ascending=True)
    
    # Group by Identificação
    grouped = df_active.groupby("identificacao")
    
    for ident in sorted(grouped.groups.keys()):
        group_df = grouped.get_group(ident)
        
        # Group Header
        st.markdown(f"<h4 style='margin-bottom: 5px; margin-top: 20px;'>📁 {ident} <span style='font-size: 14px; font-weight: normal; color: gray;'>({len(group_df)} atividades)</span></h4>", unsafe_allow_html=True)
        
        html_rows = []
        for _, row in group_df.iterrows():
            status = row.get("status", "")
            
            # Status Badge Styling
            if status == "Atrasado":
                color = "rgba(255, 75, 75, 0.15)"
                text_color = "#ff4b4b"
                border_color = "#ff4b4b"
            elif status == "Esta semana":
                color = "rgba(250, 202, 43, 0.15)"
                text_color = "#b28d0e" 
                border_color = "#faca2b"
            else:
                color = "rgba(9, 171, 59, 0.15)"
                text_color = "#09ab3b"
                border_color = "#09ab3b"
            
            badge = f"<span style='background-color: {color}; color: {text_color}; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 800; text-transform: uppercase;'>{status}</span>"
            
            # Field parsing
            prazo_str = pd.to_datetime(row['prazo']).strftime('%d/%m/%Y') if pd.notna(row['prazo']) else "-"
            apoio_str = f" | <b>Apoio:</b> {row['apoio']}" if pd.notna(row.get('apoio')) and str(row.get('apoio')).strip() else ""
            obs_str = f"<div style='color: gray; font-size: 13px; margin-top: 4px;'><i>Obs: {row.get('observacao', '')}</i></div>" if pd.notna(row.get('observacao')) and str(row.get('observacao')).strip() else ""
            
            # Row HTML Container
            html_rows.append(f"""
            <div style='border-left: 4px solid {border_color}; margin-bottom: 8px; background-color: var(--secondary-background-color); padding: 12px 16px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
                <div style='margin-bottom: 6px;'>{badge} <strong style='font-size: 15px; margin-left: 8px;'>{row['atividade']}</strong></div>
                <div style='font-size: 14px; color: var(--text-color);'>
                    <b>Prazo:</b> {prazo_str} | <b>Execução:</b> {row['execucao']}{apoio_str} | <b>Cat:</b> {row['categoria']}
                </div>
                {obs_str}
            </div>
            """)
        
        st.markdown("".join(html_rows), unsafe_allow_html=True)


# ==========================================
# 5. PAGES RENDERING FUNCTIONS
# ==========================================

def render_sales_pipeline():
    st.title("📈 Sales Pipeline (Funil de Vendas)")
    st.markdown("Manage proposals, track budget extrapolations, and convert to active projects.")
    
    df = st.session_state.df_proposals

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
        
        edited_df = st.data_editor(
            df,
            column_config={
                "etapa_atual": st.column_config.SelectboxColumn("Etapa Atual", options=ENUMS["etapa_proposta"], required=True),
                "orcamento_total": st.column_config.NumberColumn("Orçamento (R$)", format="$ %d"),
                "meses_execucao_total": st.column_config.NumberColumn("Meses")
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic"
        )
        st.session_state.df_proposals = edited_df

def render_execution_pipeline():
    st.title("🚀 Execution Pipeline (Funil de Projetos)")
    st.markdown("Track active project health, financial execution, and schedules.")

    df = st.session_state.df_projects
    active_mask = df["status_projeto"].isin(["Inicialização", "Execução", "Finalização"])

    c1, c2, c3 = st.columns(3)
    carteira_ativa = df[active_mask]["orcamento_atualizado"].sum()
    receita_externa = df[active_mask]["receita_externa_atualizada"].sum()
    competencia = df[active_mask]["competencia_acumulada"].sum()
    
    c1.metric("Carteira Ativa (Orçamento)", f"R$ {carteira_ativa:,.2f}")
    c2.metric("Projetos Ativos", len(df[active_mask]))
    
    realizacao_pct = (competencia / receita_externa * 100) if receita_externa > 0 else 0
    c3.metric("Realização Financeira Geral", f"{realizacao_pct:.1f}%", help="Competência / Receita Externa")

    st.divider()

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
    st.title("✅ Planejamento Semanal")
    st.markdown("Painel operacional contínuo para acompanhamento e gestão de equipe.")

    # Initialize dynamic team members based on data
    init_team_members()
    df = st.session_state.df_tasks

    # Metrics Summary
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 Atrasadas", len(df[df["status"] == "Atrasado"]))
    c2.metric("🟡 Esta Semana", len(df[df["status"] == "Esta semana"]))
    c3.metric("🟢 No Prazo", len(df[df["status"] == "No prazo"]))
    c4.metric("⚪ Finalizadas", len(df[df["status"] == "Finalizado"]))

    st.divider()

    # Pre-render filters
    filtered_df = filter_tasks(df)
    
    st.divider()

    # Dynamic Team Management
    render_team_management()

    # Collapsible Editor / Creator
    with st.expander("📝 Nova atividade / Editar atividades", expanded=False):
        st.info("Utilize a tabela abaixo para editar tarefas existentes ou adicionar uma nova linha ao final.")
        
        display_cols = ["categoria", "identificacao", "atividade", "prazo", "execucao", "apoio", "observacao", "finalizado", "status_ui"]
        
        # Ensure all columns exist to prevent KeyError
        for col in display_cols:
            if col not in df.columns:
                df[col] = None

        edited_df = st.data_editor(
            df[display_cols],
            column_config={
                "categoria": st.column_config.SelectboxColumn("Categoria", options=ENUMS["categoria_tarefa"]),
                "finalizado": st.column_config.SelectboxColumn("Finalizado?", options=["Sim", "Não"]),
                "prazo": st.column_config.DateColumn("Prazo"),
                "execucao": st.column_config.SelectboxColumn("Execução", options=st.session_state.team_members),
                "apoio": st.column_config.SelectboxColumn("Apoio", options=st.session_state.team_members),
                "observacao": st.column_config.TextColumn("Observação"),
                "status_ui": st.column_config.TextColumn("Status Automático", disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic"
        )
        
        # Sync changes back to main dataframe safely
        if not edited_df.equals(df[display_cols]):
            for col in display_cols:
                if col != "status_ui":
                    st.session_state.df_tasks[col] = edited_df[col]
            st.rerun()

    st.divider()

    # Continuous Operational Panel
    st.subheader("Painel Operacional Consolidado")
    
    df_active = filtered_df[filtered_df["finalizado"] != "Sim"]
    df_finished = filtered_df[filtered_df["finalizado"] == "Sim"]
    
    # Render main flowing panel
    render_flow_panel(df_active)

    st.write("")
    
    # Finished Tasks History
    with st.expander("🗄️ Histórico de atividades finalizadas", expanded=False):
        if df_finished.empty:
            st.info("Nenhuma atividade finalizada corresponde aos filtros.")
        else:
            st.dataframe(
                df_finished[["identificacao", "atividade", "prazo", "execucao", "apoio", "categoria"]].sort_values("prazo", ascending=False), 
                use_container_width=True, 
                hide_index=True
            )


def render_team_allocation():
    st.title("🧑‍🤝‍🧑 Team Allocation (Notion Data)")
    st.markdown("Visualize resource bandwidth, member availability, and project assignments.")

    df = st.session_state.df_allocation
    
    st.subheader("Allocation Gantt Chart")
    
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
# 6. SIDEBAR NAVIGATION & ROUTING
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
            "✅ Planejamento Semanal (Tarefas)",
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
elif page == "✅ Planejamento Semanal (Tarefas)":
    render_weekly_tracker()
elif page == "🧑‍🤝‍🧑 Team Allocation (Notion)":
    render_team_allocation()
