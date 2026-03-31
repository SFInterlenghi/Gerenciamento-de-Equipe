import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

# ==========================================
# 0. PAGE CONFIG (must be first st call)
# ==========================================
st.set_page_config(
    page_title="PSE — Lifecycle Dashboard",
    layout="wide",
    page_icon=":material/analytics:",
)

# ==========================================
# 1. GLOBAL CSS — scoped to our own classes
# ==========================================
# No targeting of Streamlit internals (.stHorizontalBlock, .st-emotion-cache-*).
# All selectors use our own `.pse-*` namespace for forward-compatibility.
st.html("""
<style>
/* ── Funnel stage header ── */
.pse-stage-header {
    text-align: center;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 10px 0;
    border-radius: 8px;
    margin-bottom: 12px;
}
.pse-stage-header.prospeccao {
    background: linear-gradient(135deg, #1e3a5f, #2b5ea7);
    color: #e0ecff;
}
.pse-stage-header.negociacao {
    background: linear-gradient(135deg, #5f4b1e, #a7862b);
    color: #fff5d6;
}
.pse-stage-header.contratacao {
    background: linear-gradient(135deg, #1e5f3a, #2ba75e);
    color: #d6ffe5;
}

/* ── Project card ── */
.pse-card {
    background: var(--secondary-background-color, #f8f9fb);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
    border-left: 5px solid var(--primary-color, #0969da);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    cursor: default;
}
.pse-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}
.pse-card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    gap: 8px;
}
.pse-card-logo {
    height: 28px;
    max-width: 80px;
    object-fit: contain;
    border-radius: 4px;
    flex-shrink: 0;
}
.pse-card-budget {
    font-size: 0.92rem;
    font-weight: 700;
    color: #1a7f37;
    white-space: nowrap;
}
.pse-card-project {
    font-weight: 600;
    font-size: 0.95rem;
    margin-bottom: 2px;
}
.pse-card-client {
    font-size: 0.82rem;
    opacity: 0.65;
}
.pse-card-meta {
    display: flex;
    gap: 6px;
    margin-top: 6px;
    flex-wrap: wrap;
}
.pse-tag {
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: 500;
    background: rgba(128,128,128,0.12);
}
.pse-tag.fomento   { background: #dbeafe; color: #1e40af; }
.pse-tag.direto    { background: #fef3c7; color: #92400e; }
.pse-tag.embrapii  { background: #d1fae5; color: #065f46; }

/* ── Empty stage ── */
.pse-empty {
    text-align: center;
    padding: 24px 12px;
    opacity: 0.45;
    font-size: 0.85rem;
}

/* ── Stage count badge ── */
.pse-count {
    display: inline-block;
    background: rgba(255,255,255,0.25);
    padding: 1px 10px;
    border-radius: 12px;
    font-size: 0.78rem;
    margin-left: 6px;
    font-weight: 400;
}

/* ── Stage total (budget bar) ── */
.pse-stage-total {
    text-align: center;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 6px 0 2px;
    opacity: 0.7;
}
</style>
""")

# ==========================================
# 2. ENUMS & CONSTANTS (Blueprint §1.5)
# ==========================================
ENUMS = {
    "coordenacoes": ["CIF", "CIN", "CPQ", "CBT"],
    "linhas_pesquisa": [
        "Desenvolvimento Avançado de Processos",
        "Engenharia de Sistemas em Processos",
        "Inovação em Materiais Sustentáveis",
        "Síntese Química Renovável",
        "Tecnologia Analítica de Processos",
        "Transformação e Valorização da Biomassa",
    ],
    "linhas_pesquisa_short": ["DAP", "ESP", "IMS", "SQR", "TAP", "TVB"],
    "financiamento": [
        "Contratação direta", "EMBRAPII - CG", "EMBRAPII - BFA",
        "EMBRAPII - Outros", "ANP", "Edital SENAI", "ANEEL",
    ],
    "tipo_projeto": ["Com fomento", "Sem fomento"],
    "etapa_proposta": ["Prospecção", "Negociação", "Contratação", "Contratado", "Recusado"],
    "status_projeto": ["Inicialização", "Execução", "Finalização", "Encerrado", "Cancelado"],
    "status_tarefa": ["Finalizado", "Atrasado", "Esta semana", "No prazo"],
    "categoria_tarefa": ["Projetos", "Projetos internos", "Prospecções"],
    "status_notion": ["Aguardando", "Em execução", "Finalizado", "Cancelado"],
    "gestores": ["Gustavo", "Raquel", "Sabrina", "Ana", "Igor", "Stefano", "Julliana", "Lidiane"],
}

STAGE_CSS_CLASS = {
    "Prospecção": "prospeccao",
    "Negociação": "negociacao",
    "Contratação": "contratacao",
}

# ==========================================
# 3. MOCK DATA (self-contained, no file deps)
# ==========================================
@st.cache_data
def generate_mock_proposals():
    np.random.seed(42)
    random.seed(42)
    clients = ["Petrobras", "Eldorado", "Braskem", "Vale", "Natura", "Ambev",
               "WEG", "Klabin", "Suzano", "BASF", "Raízen", "Cenibra", "Nitro"]
    codenames = [
        "CO2 to Methanol", "Fibra de Coco", "DT Café", "Biobutanol BFA",
        "Anodos Sustentáveis", "Pirólise Plasma", "Centro Catálise",
        "ATJ Aditivo", "Sensor Virtual", "RTO Celulose", "Caldeira ML",
        "Zeolignin III", "Monitoramento pH", "Alcoxilação", "Silicato",
        "Valvula Borboleta", "BRS Integrado", "Antioxidantes HPLC",
    ]
    etapas = (
        ["Prospecção"] * 5 + ["Negociação"] * 6 + ["Contratação"] * 3
        + ["Contratado"] * 3 + ["Recusado"] * 1
    )
    random.shuffle(etapas)
    n = len(codenames)
    etapas = (etapas * ((n // len(etapas)) + 1))[:n]
    # Dummy logo — uses a small public placeholder per client initial
    logo_base = "https://ui-avatars.com/api/?background=0D8ABC&color=fff&bold=true&size=64&name="
    rows = []
    for i, cod in enumerate(codenames):
        cl = random.choice(clients)
        orc_total = round(random.uniform(50_000, 5_000_000), 2)
        orc_cpq = round(orc_total * random.uniform(0.3, 0.9), 2)
        meses = random.randint(3, 36)
        meses_cpq = max(1, meses - random.randint(0, 6))
        financ = random.choice(ENUMS["financiamento"])
        rows.append({
            "coordenacao_responsavel": random.choice(ENUMS["coordenacoes"]),
            "responsavel_cpq": random.choice(ENUMS["gestores"]),
            "codinome_projeto": cod,
            "tipo_projeto": random.choice(ENUMS["tipo_projeto"]),
            "linha_pesquisa_cpq": random.choice(ENUMS["linhas_pesquisa_short"]),
            "cliente": cl,
            "logo_url": f"{logo_base}{cl.replace(' ', '+')}",
            "financiamento": financ,
            "etapa_atual": etapas[i],
            "orcamento_total": orc_total,
            "orcamento_cpq": orc_cpq,
            "meses_execucao_total": meses,
            "meses_execucao_cpq": meses_cpq,
        })
    return pd.DataFrame(rows)


@st.cache_data
def generate_mock_projects():
    np.random.seed(42)
    random.seed(42)
    today = datetime.today()
    codenames = [
        "CO2 to Methanol", "Fibra de Coco", "Biobutanol BFA",
        "Sensor Virtual", "RTO Celulose", "Caldeira ML",
        "ATJ Aditivo", "Zeolignin III", "BRS Integrado",
    ]
    rows = []
    for cod in codenames:
        orc = round(random.uniform(300_000, 3_000_000), 2)
        rec_ext = round(orc * random.uniform(0.5, 1.0), 2)
        comp = round(rec_ext * random.uniform(0.1, 0.95), 2)
        inicio = today - timedelta(days=random.randint(30, 400))
        termino = today + timedelta(days=random.randint(30, 500))
        rows.append({
            "codinome_projeto": cod,
            "cliente": random.choice(["Petrobras", "Eldorado", "Braskem", "Klabin", "BASF"]),
            "lider_tecnico": random.choice(ENUMS["gestores"]),
            "status_projeto": random.choice(ENUMS["status_projeto"]),
            "orcamento_atualizado": orc,
            "receita_externa_atualizada": rec_ext,
            "competencia_acumulada": comp,
            "resgates_acumulados": round(comp * random.uniform(0.6, 1.0), 2),
            "linha_pesquisa_cpq": random.choice(ENUMS["linhas_pesquisa_short"]),
            "inicio_escopo_tecnico": inicio,
            "termino_previsto": termino,
        })
    return pd.DataFrame(rows)


@st.cache_data
def generate_mock_tasks():
    np.random.seed(42)
    random.seed(42)
    today = datetime.today()
    clients = ["Eldorado", "Braskem", "Petrobras", "Klabin", "BASF"]
    projects = ["Caldeira", "ATJ", "BFA", "Zeolignin", "RTO", "Sensor Virtual"]
    rows = []
    for i in range(45):
        days_offset = random.choice([-15, -7, -3, -1, 0, 1, 3, 5, 10, 20, 40])
        rows.append({
            "categoria": random.choice(ENUMS["categoria_tarefa"]),
            "identificacao": f"[{random.choice(clients)}] {random.choice(projects)}",
            "atividade": f"Atividade de exemplo #{i+1}",
            "prazo": today + timedelta(days=days_offset),
            "execucao": random.choice(ENUMS["gestores"]),
            "apoio": random.choice(ENUMS["gestores"] + [None, None]),
            "finalizado": random.choice(["Sim", "Não", "Não", "Não"]),
        })
    return pd.DataFrame(rows)


@st.cache_data
def generate_mock_allocation():
    np.random.seed(42)
    random.seed(42)
    today = datetime.today()
    projects = ["CO2 to Methanol", "Caldeira ML", "ATJ Aditivo", "Sensor Virtual",
                "Zeolignin III", "RTO Celulose", "BRS Integrado", "Fibra de Coco"]
    rows = []
    for _ in range(28):
        start = today + timedelta(days=random.randint(-90, 30))
        rows.append({
            "projeto": random.choice(projects),
            "executor": random.choice(ENUMS["gestores"]),
            "gestor": random.choice(ENUMS["gestores"]),
            "data_inicio": start,
            "data_fim": start + timedelta(days=random.randint(14, 120)),
            "status_notion": random.choice(ENUMS["status_notion"]),
        })
    return pd.DataFrame(rows)

# ==========================================
# 4. SESSION STATE INIT
# ==========================================
if "db_init" not in st.session_state:
    st.session_state.df_proposals = generate_mock_proposals()
    st.session_state.df_projects = generate_mock_projects()
    st.session_state.df_tasks = generate_mock_tasks()
    st.session_state.df_allocation = generate_mock_allocation()
    st.session_state.db_init = True


def reset_database():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    generate_mock_proposals.clear()
    generate_mock_projects.clear()
    generate_mock_tasks.clear()
    generate_mock_allocation.clear()
    st.rerun()

# ==========================================
# 5. BUSINESS LOGIC (Blueprint §2)
# ==========================================
def compute_task_status(row: pd.Series) -> str:
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


def _financiamento_tag_class(financ: str) -> str:
    if pd.isna(financ):
        return "pse-tag"
    f = financ.lower()
    if "embrapii" in f:
        return "pse-tag embrapii"
    if "diret" in f:
        return "pse-tag direto"
    return "pse-tag fomento"

# ==========================================
# 6. PAGE: SALES PIPELINE (Vendas)
# ==========================================
def render_sales_pipeline():
    st.header("Sales pipeline", anchor=False)
    st.caption("Manage proposals from prospecting through contracting. Edit data inline; charts update instantly.")

    df = st.session_state.df_proposals

    # ── Sidebar filters ──
    with st.sidebar:
        st.subheader("Filtros de vendas", anchor=False)
        sel_coord = st.selectbox(
            "Coordenação",
            ["Todas"] + ENUMS["coordenacoes"],
            key="vendas_coord",
        )
        sel_linha = st.selectbox(
            "Linha de pesquisa",
            ["Todas"] + ENUMS["linhas_pesquisa_short"],
            key="vendas_linha",
        )
        sel_tipo = st.selectbox(
            "Tipo de projeto",
            ["Todos"] + ENUMS["tipo_projeto"],
            key="vendas_tipo",
        )

    # Apply filters
    mask = pd.Series(True, index=df.index)
    if sel_coord != "Todas":
        mask &= df["coordenacao_responsavel"] == sel_coord
    if sel_linha != "Todas":
        mask &= df["linha_pesquisa_cpq"] == sel_linha
    if sel_tipo != "Todos":
        mask &= df["tipo_projeto"] == sel_tipo
    fdf = df[mask]

    # ── KPI row ──
    active_mask = fdf["etapa_atual"].isin(["Prospecção", "Negociação", "Contratação"])
    active_df = fdf[active_mask]
    contracted_df = fdf[fdf["etapa_atual"] == "Contratado"]
    refused_df = fdf[fdf["etapa_atual"] == "Recusado"]

    total_active_budget = active_df["orcamento_total"].sum()
    total_contracted = contracted_df["orcamento_total"].sum()
    n_active = len(active_df)
    n_contracted = len(contracted_df)
    n_refused = len(refused_df)
    taxa_contrat = n_contracted / (n_contracted + n_refused) if (n_contracted + n_refused) > 0 else 0
    meses_sum = active_df["meses_execucao_cpq"].sum()
    ticket_medio = active_df["orcamento_cpq"].sum() / meses_sum if meses_sum > 0 else 0

    with st.container(horizontal=True):
        st.metric("Propostas ativas", n_active, border=True)
        st.metric("Contratadas", n_contracted, border=True)
        st.metric("Carteira ativa", f"R$ {total_active_budget:,.0f}", border=True)
        st.metric("Ticket médio CPQ", f"R$ {ticket_medio:,.0f}/mês", border=True)
        st.metric("Taxa de contratação", f"{taxa_contrat:.0%}", border=True)

    # ── FUNNEL CARDS (premium horizontal layout) ──
    st.subheader("Funil de vendas", anchor=False)

    funnel_stages = ["Prospecção", "Negociação", "Contratação"]
    cols = st.columns(len(funnel_stages), border=True)

    for i, stage in enumerate(funnel_stages):
        stage_df = fdf[fdf["etapa_atual"] == stage].sort_values("orcamento_total", ascending=False)
        css_cls = STAGE_CSS_CLASS[stage]
        stage_total = stage_df["orcamento_total"].sum()

        with cols[i]:
            # Stage header via scoped HTML
            st.html(
                f'<div class="pse-stage-header {css_cls}">'
                f'{stage}<span class="pse-count">{len(stage_df)}</span></div>'
            )

            if stage_df.empty:
                st.html('<div class="pse-empty">Nenhuma proposta neste estágio</div>')
            else:
                # Budget total for the stage
                st.html(f'<div class="pse-stage-total">R$ {stage_total:,.0f}</div>')
                # Render each card
                for _, row in stage_df.iterrows():
                    tag_cls = _financiamento_tag_class(row.get("financiamento"))
                    financ_label = row.get("financiamento", "")
                    if pd.isna(financ_label):
                        financ_label = ""
                    tipo_label = row.get("tipo_projeto", "")
                    if pd.isna(tipo_label):
                        tipo_label = ""

                    card_html = f"""
                    <div class="pse-card">
                        <div class="pse-card-top">
                            <img class="pse-card-logo"
                                 src="{row['logo_url']}"
                                 alt="{row['cliente']}"
                                 onerror="this.style.display='none'">
                            <div class="pse-card-budget">R$ {row['orcamento_total']:,.0f}</div>
                        </div>
                        <div class="pse-card-project">{row['codinome_projeto']}</div>
                        <div class="pse-card-client">{row['cliente']}</div>
                        <div class="pse-card-meta">
                            <span class="{tag_cls}">{financ_label}</span>
                            <span class="pse-tag">{tipo_label}</span>
                        </div>
                    </div>
                    """
                    st.html(card_html)

    # ── Aggregate charts ──
    chart_left, chart_right = st.columns(2)

    with chart_left:
        with st.container(border=True):
            st.subheader("Propostas por linha de pesquisa", anchor=False)
            by_linha = (
                active_df.groupby("linha_pesquisa_cpq")
                .agg(count=("codinome_projeto", "count"), budget=("orcamento_total", "sum"))
                .reset_index()
                .sort_values("budget", ascending=True)
            )
            if not by_linha.empty:
                fig = px.bar(
                    by_linha, x="budget", y="linha_pesquisa_cpq",
                    orientation="h", text="count",
                    labels={"budget": "Orçamento (R$)", "linha_pesquisa_cpq": ""},
                )
                fig.update_traces(textposition="inside", marker_color="#2b5ea7")
                fig.update_layout(
                    margin=dict(l=0, r=0, t=10, b=0), height=300,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("Sem dados para exibir.")

    with chart_right:
        with st.container(border=True):
            st.subheader("Funil agregado", anchor=False)
            funnel_agg = (
                fdf[fdf["etapa_atual"].isin(funnel_stages)]
                .groupby("etapa_atual")
                .agg(n=("codinome_projeto", "count"), total=("orcamento_total", "sum"))
                .reindex(funnel_stages)
                .reset_index()
            )
            if not funnel_agg.empty:
                fig = go.Figure(go.Funnel(
                    y=funnel_agg["etapa_atual"], x=funnel_agg["n"],
                    textinfo="value+percent initial",
                    customdata=funnel_agg["total"],
                    hovertemplate="%{y}<br>Propostas: %{x}<br>R$ %{customdata:,.0f}<extra></extra>",
                    marker=dict(color=["#2b5ea7", "#a7862b", "#2ba75e"]),
                ))
                fig.update_layout(
                    margin=dict(l=0, r=0, t=10, b=0), height=300,
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("Sem dados para exibir.")

    # ── Editable table ──
    with st.expander("Detalhamento e edição de propostas", icon=":material/edit:"):
        edited = st.data_editor(
            df,
            column_config={
                "etapa_atual": st.column_config.SelectboxColumn("Etapa", options=ENUMS["etapa_proposta"], required=True),
                "coordenacao_responsavel": st.column_config.SelectboxColumn("Coord.", options=ENUMS["coordenacoes"]),
                "linha_pesquisa_cpq": st.column_config.SelectboxColumn("Linha pesq.", options=ENUMS["linhas_pesquisa_short"]),
                "tipo_projeto": st.column_config.SelectboxColumn("Tipo", options=ENUMS["tipo_projeto"]),
                "financiamento": st.column_config.SelectboxColumn("Financ.", options=ENUMS["financiamento"]),
                "orcamento_total": st.column_config.NumberColumn("Orçamento total (R$)", format="R$ %.0f"),
                "orcamento_cpq": st.column_config.NumberColumn("Orçamento CPQ (R$)", format="R$ %.0f"),
                "logo_url": None,  # hide from editor
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="proposals_editor",
        )
        st.session_state.df_proposals = edited


# ==========================================
# 7. PAGE: EXECUTION PIPELINE (Projetos)
# ==========================================
def render_execution_pipeline():
    st.header("Execution pipeline", anchor=False)
    st.caption("Track project health, financial execution, and timelines.")

    df = st.session_state.df_projects
    active_mask = df["status_projeto"].isin(["Inicialização", "Execução", "Finalização"])
    active_df = df[active_mask]

    carteira = active_df["orcamento_atualizado"].sum()
    receita_ext = active_df["receita_externa_atualizada"].sum()
    competencia = active_df["competencia_acumulada"].sum()
    realizacao = (competencia / receita_ext * 100) if receita_ext > 0 else 0
    receita_missing = receita_ext - active_df["resgates_acumulados"].sum()

    with st.container(horizontal=True):
        st.metric("Carteira ativa", f"R$ {carteira:,.0f}", border=True)
        st.metric("Projetos ativos", len(active_df), border=True)
        st.metric("Realização financeira", f"{realizacao:.1f}%", border=True,
                   help="Competência acumulada / Receita externa")
        st.metric("Receita a realizar", f"R$ {receita_missing:,.0f}", border=True)

    # Gantt
    with st.container(border=True):
        st.subheader("Timeline de projetos", anchor=False)
        gantt_df = df.dropna(subset=["inicio_escopo_tecnico", "termino_previsto"])
        if not gantt_df.empty:
            fig = px.timeline(
                gantt_df, x_start="inicio_escopo_tecnico", x_end="termino_previsto",
                y="codinome_projeto", color="linha_pesquisa_cpq",
                hover_data=["cliente", "status_projeto"],
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(
                margin=dict(l=0, r=0, t=10, b=0), height=400,
                paper_bgcolor="rgba(0,0,0,0)", legend_title_text="",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Sem datas disponíveis para timeline.")

    # Per-project financial health
    with st.container(border=True):
        st.subheader("Saúde financeira por projeto", anchor=False)
        health = active_df.copy()
        health["realizacao_pct"] = (health["competencia_acumulada"] / health["receita_externa_atualizada"]).fillna(0)
        health["receita_faltante"] = (health["receita_externa_atualizada"] - health["resgates_acumulados"]).fillna(0)
        display_cols = ["codinome_projeto", "cliente", "status_projeto", "orcamento_atualizado",
                        "receita_externa_atualizada", "competencia_acumulada", "realizacao_pct", "receita_faltante"]
        st.dataframe(
            health[display_cols],
            column_config={
                "orcamento_atualizado": st.column_config.NumberColumn("Orçamento", format="R$ %.0f"),
                "receita_externa_atualizada": st.column_config.NumberColumn("Receita ext.", format="R$ %.0f"),
                "competencia_acumulada": st.column_config.NumberColumn("Competência", format="R$ %.0f"),
                "realizacao_pct": st.column_config.ProgressColumn("Realização", min_value=0, max_value=1.5, format="%.0f%%"),
                "receita_faltante": st.column_config.NumberColumn("Receita faltante", format="R$ %.0f"),
            },
            hide_index=True, use_container_width=True,
        )

    with st.expander("Editar dados de projetos", icon=":material/edit:"):
        edited = st.data_editor(
            df,
            column_config={
                "status_projeto": st.column_config.SelectboxColumn("Status", options=ENUMS["status_projeto"]),
                "orcamento_atualizado": st.column_config.NumberColumn("Orçamento", format="R$ %.0f"),
                "inicio_escopo_tecnico": st.column_config.DateColumn("Início"),
                "termino_previsto": st.column_config.DateColumn("Término"),
            },
            use_container_width=True, hide_index=True, num_rows="dynamic",
            key="projects_editor",
        )
        st.session_state.df_projects = edited


# ==========================================
# 8. PAGE: WEEKLY PLANNER (Tarefas)
# ==========================================
def render_weekly_tracker():
    st.header("Weekly planner", anchor=False)
    st.caption("Actionable task tracking with automated status logic from the legacy Excel formula.")

    df = st.session_state.df_tasks.copy()
    df["status"] = df.apply(compute_task_status, axis=1)

    # Sidebar filters
    with st.sidebar:
        st.subheader("Filtros de tarefas", anchor=False)
        sel_cat = st.multiselect("Categoria", ENUMS["categoria_tarefa"],
                                  default=ENUMS["categoria_tarefa"], key="task_cat")
        sel_status = st.multiselect("Status", ENUMS["status_tarefa"],
                                     default=["Atrasado", "Esta semana", "No prazo"], key="task_status")
        sel_exec = st.multiselect("Executor", sorted(df["execucao"].dropna().unique()),
                                    default=[], key="task_exec")

    mask = df["categoria"].isin(sel_cat) & df["status"].isin(sel_status)
    if sel_exec:
        mask &= df["execucao"].isin(sel_exec)
    fdf = df[mask]

    # KPI cards
    with st.container(horizontal=True):
        st.metric(":red-background[:red[Atrasadas]]", len(df[df["status"] == "Atrasado"]), border=True)
        st.metric(":orange-background[:orange[Esta semana]]", len(df[df["status"] == "Esta semana"]), border=True)
        st.metric(":green-background[:green[No prazo]]", len(df[df["status"] == "No prazo"]), border=True)
        st.metric("Finalizadas", len(df[df["status"] == "Finalizado"]), border=True)

    col_chart, col_table = st.columns([1, 2])

    with col_chart:
        with st.container(border=True):
            st.subheader("Carga por categoria", anchor=False)
            chart_src = (
                df[df["status"].isin(["Atrasado", "Esta semana"])]
                .groupby(["categoria", "status"]).size()
                .reset_index(name="count")
            )
            if not chart_src.empty:
                fig = px.bar(
                    chart_src, x="count", y="categoria", color="status",
                    orientation="h", barmode="stack",
                    color_discrete_map={"Atrasado": "#C00000", "Esta semana": "#BF8F00"},
                    labels={"count": "Tarefas", "categoria": ""},
                )
                fig.update_layout(
                    margin=dict(l=0, r=0, t=10, b=0), height=260,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend_title_text="",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("Nenhuma tarefa atrasada ou da semana.", icon=":material/check_circle:")

    with col_table:
        with st.container(border=True):
            st.subheader("Tarefas", anchor=False)
            status_emoji = {"Atrasado": "🔴", "Esta semana": "🟡", "No prazo": "🟢", "Finalizado": "⚪"}
            display = fdf.copy()
            display["status_ui"] = display["status"].map(lambda s: f"{status_emoji.get(s, '')} {s}")
            show_cols = ["categoria", "identificacao", "atividade", "prazo", "execucao", "status_ui"]
            st.dataframe(
                display[show_cols],
                column_config={
                    "prazo": st.column_config.DateColumn("Prazo"),
                    "status_ui": "Status",
                },
                hide_index=True, use_container_width=True, height=350,
            )

    with st.expander("Editar tarefas (atualiza status automaticamente)", icon=":material/edit:"):
        edited = st.data_editor(
            df[["categoria", "identificacao", "atividade", "prazo", "execucao", "apoio", "finalizado"]],
            column_config={
                "categoria": st.column_config.SelectboxColumn("Categoria", options=ENUMS["categoria_tarefa"]),
                "finalizado": st.column_config.SelectboxColumn("Finalizado?", options=["Sim", "Não"]),
                "prazo": st.column_config.DateColumn("Prazo"),
            },
            use_container_width=True, hide_index=True, num_rows="dynamic",
            key="tasks_editor",
        )
        for col in edited.columns:
            st.session_state.df_tasks[col] = edited[col]


# ==========================================
# 9. PAGE: TEAM ALLOCATION (Notion)
# ==========================================
def render_team_allocation():
    st.header("Team allocation", anchor=False)
    st.caption("Resource bandwidth and project assignments sourced from Notion export.")

    df = st.session_state.df_allocation

    with st.container(border=True):
        st.subheader("Allocation timeline", anchor=False)
        clean = df.dropna(subset=["data_inicio", "data_fim"])
        if not clean.empty:
            fig = px.timeline(
                clean, x_start="data_inicio", x_end="data_fim",
                y="executor", color="status_notion", hover_name="projeto",
                color_discrete_map={
                    "Em execução": "#2196F3", "Aguardando": "#FFC107",
                    "Finalizado": "#9E9E9E", "Cancelado": "#F44336",
                },
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(
                margin=dict(l=0, r=0, t=10, b=0), height=450,
                paper_bgcolor="rgba(0,0,0,0)", legend_title_text="",
            )
            st.plotly_chart(fig, use_container_width=True)

    # Workload summary
    with st.container(border=True):
        st.subheader("Carga por executor", anchor=False)
        active_alloc = df[df["status_notion"].isin(["Em execução", "Aguardando"])]
        if not active_alloc.empty:
            load_summary = active_alloc.groupby("executor").size().reset_index(name="projetos_ativos").sort_values("projetos_ativos", ascending=True)
            fig = px.bar(
                load_summary, x="projetos_ativos", y="executor",
                orientation="h", text="projetos_ativos",
                labels={"projetos_ativos": "Projetos ativos", "executor": ""},
            )
            fig.update_traces(marker_color="#2196F3", textposition="inside")
            fig.update_layout(
                margin=dict(l=0, r=0, t=10, b=0), height=300,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Editar alocações", icon=":material/edit:"):
        edited = st.data_editor(
            df,
            column_config={
                "status_notion": st.column_config.SelectboxColumn("Status", options=ENUMS["status_notion"]),
                "executor": st.column_config.SelectboxColumn("Executor", options=ENUMS["gestores"]),
                "data_inicio": st.column_config.DateColumn("Início"),
                "data_fim": st.column_config.DateColumn("Fim"),
            },
            use_container_width=True, hide_index=True, num_rows="dynamic",
            key="alloc_editor",
        )
        st.session_state.df_allocation = edited


# ==========================================
# 10. SIDEBAR NAV & ROUTING
# ==========================================
PAGES = {
    ":material/monitoring: Sales pipeline": render_sales_pipeline,
    ":material/rocket_launch: Execution pipeline": render_execution_pipeline,
    ":material/checklist: Weekly planner": render_weekly_tracker,
    ":material/group: Team allocation": render_team_allocation,
}

with st.sidebar:
    st.title("PSE Dashboard", anchor=False)
    st.caption("Proof of Concept — v0.2")
    page = st.radio("Navegação", list(PAGES.keys()), label_visibility="collapsed")
    st.divider()
    if st.button("Resetar dados", icon=":material/refresh:", use_container_width=True):
        reset_database()
    st.caption("Dados em session state. Refresh do browser restaura os valores originais.")

# Route
PAGES[page]()
