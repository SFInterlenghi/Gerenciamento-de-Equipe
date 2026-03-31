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
-st.html("""
+GLOBAL_CSS = '''
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
 
@@ -112,75 +112,77 @@ st.html("""
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
-""")
+'''
+st.html(GLOBAL_CSS)
 
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
-    "categoria_tarefa": ["Projetos", "Projetos internos", "Prospecções"],
+    "categoria_tarefa": ["Projeto", "Projeto Interno", "Prospecção"],
+    "finalizado_tarefa": ["Sim", "Não"],
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
@@ -241,122 +243,334 @@ def generate_mock_projects():
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
+        data_criacao = today - timedelta(days=random.randint(0, 20))
         rows.append({
             "categoria": random.choice(ENUMS["categoria_tarefa"]),
             "identificacao": f"[{random.choice(clients)}] {random.choice(projects)}",
             "atividade": f"Atividade de exemplo #{i+1}",
             "prazo": today + timedelta(days=days_offset),
             "execucao": random.choice(ENUMS["gestores"]),
             "apoio": random.choice(ENUMS["gestores"] + [None, None]),
             "finalizado": random.choice(["Sim", "Não", "Não", "Não"]),
+            "observacao": random.choice(["", "", "Dependência de fornecedor", "Aguardando validação interna"]),
+            "id": f"T-{i+1:04d}",
+            "data_criacao": data_criacao,
+            "data_atualizacao": data_criacao,
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
-    if row.get("finalizado") == "Sim":
+    finalizado = str(row.get("finalizado", "Não")).strip().title()
+    if finalizado == "Sim":
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
 
 
+def prepare_task_dataframe(df: pd.DataFrame) -> pd.DataFrame:
+    required_defaults = {
+        "id": "",
+        "categoria": "Projeto",
+        "identificacao": "",
+        "atividade": "",
+        "prazo": pd.NaT,
+        "execucao": "",
+        "apoio": "",
+        "finalizado": "Não",
+        "observacao": "",
+        "status": "",
+        "data_criacao": pd.NaT,
+        "data_atualizacao": pd.NaT,
+    }
+    prepared = df.copy()
+    for col, default in required_defaults.items():
+        if col not in prepared.columns:
+            prepared[col] = default
+
+    categoria_map = {
+        "Projetos": "Projeto",
+        "Projetos internos": "Projeto Interno",
+        "Prospecções": "Prospecção",
+    }
+    prepared["categoria"] = (
+        prepared["categoria"]
+        .replace(categoria_map)
+        .fillna("Projeto")
+    )
+    prepared["categoria"] = prepared["categoria"].where(
+        prepared["categoria"].isin(ENUMS["categoria_tarefa"]), "Projeto"
+    )
+
+    prepared["finalizado"] = (
+        prepared["finalizado"]
+        .fillna("Não")
+        .astype(str)
+        .str.strip()
+        .str.title()
+    )
+    prepared["finalizado"] = prepared["finalizado"].where(
+        prepared["finalizado"].isin(ENUMS["finalizado_tarefa"]), "Não"
+    )
+
+    prepared["prazo"] = pd.to_datetime(prepared["prazo"], errors="coerce")
+    prepared["data_criacao"] = pd.to_datetime(prepared["data_criacao"], errors="coerce")
+    prepared["data_atualizacao"] = pd.to_datetime(prepared["data_atualizacao"], errors="coerce")
+
+    now = pd.Timestamp(datetime.now())
+    if prepared["id"].eq("").any() or prepared["id"].isna().any():
+        max_id = (
+            prepared["id"]
+            .dropna()
+            .astype(str)
+            .str.extract(r"T-(\d+)", expand=False)
+            .dropna()
+            .astype(int)
+            .max()
+        )
+        next_id = 1 if pd.isna(max_id) else int(max_id) + 1
+        for idx in prepared.index:
+            if pd.isna(prepared.at[idx, "id"]) or str(prepared.at[idx, "id"]).strip() == "":
+                prepared.at[idx, "id"] = f"T-{next_id:04d}"
+                next_id += 1
+
+    prepared["data_criacao"] = prepared["data_criacao"].fillna(now)
+    prepared["data_atualizacao"] = prepared["data_atualizacao"].fillna(now)
+    prepared["status"] = prepared.apply(compute_task_status, axis=1)
+    return prepared
+
+
+def render_task_kpis(df: pd.DataFrame):
+    ativos = df[df["finalizado"] != "Sim"]
+    with st.container(horizontal=True):
+        st.metric("Atividades ativas", len(ativos), border=True)
+        st.metric(":red-background[:red[Atrasadas]]", len(ativos[ativos["status"] == "Atrasado"]), border=True)
+        st.metric(":orange-background[:orange[Esta semana]]", len(ativos[ativos["status"] == "Esta semana"]), border=True)
+        st.metric(":green-background[:green[No prazo]]", len(ativos[ativos["status"] == "No prazo"]), border=True)
+        st.metric("Finalizadas", len(df[df["status"] == "Finalizado"]), border=True)
+
+
+def render_task_filters(df: pd.DataFrame) -> dict:
+    pessoas = sorted(set(df["execucao"].dropna().tolist()) | set(df["apoio"].dropna().tolist()))
+    identificacoes = sorted(df["identificacao"].dropna().astype(str).unique().tolist())
+    with st.container(border=True):
+        st.subheader("Filtros", anchor=False)
+        col1, col2, col3 = st.columns(3)
+        with col1:
+            pessoa = st.multiselect("Pessoa (Execução/Apoio)", pessoas, default=[], key="task_filter_pessoa")
+            categoria = st.multiselect("Categoria", ENUMS["categoria_tarefa"], default=ENUMS["categoria_tarefa"], key="task_filter_categoria")
+        with col2:
+            identificacao = st.multiselect("Identificação", identificacoes, default=[], key="task_filter_identificacao")
+            status = st.multiselect("Status", ENUMS["status_tarefa"], default=["Atrasado", "Esta semana", "No prazo"], key="task_filter_status")
+        with col3:
+            apenas_ativas = st.toggle("Mostrar apenas ativas", value=True, key="task_filter_ativas")
+            incluir_historico = st.toggle("Incluir histórico (finalizadas)", value=False, key="task_filter_historico")
+    return {
+        "pessoa": pessoa,
+        "categoria": categoria,
+        "identificacao": identificacao,
+        "status": status,
+        "apenas_ativas": apenas_ativas,
+        "incluir_historico": incluir_historico,
+    }
+
+
+def render_new_task_form(df: pd.DataFrame):
+    with st.container(border=True):
+        st.subheader("Nova atividade", anchor=False)
+        identificacoes_existentes = sorted(df["identificacao"].dropna().astype(str).unique().tolist())
+        with st.form("nova_atividade_form", clear_on_submit=True):
+            col1, col2 = st.columns(2)
+            with col1:
+                categoria = st.selectbox("Categoria", ENUMS["categoria_tarefa"])
+                sugestao_identificacao = st.selectbox("Identificação existente (opcional)", [""] + identificacoes_existentes)
+                atividade = st.text_input("Atividade")
+                prazo = st.date_input("Prazo", value=datetime.today())
+            with col2:
+                identificacao_nova = st.text_input("Nova identificação (opcional)")
+                execucao = st.selectbox("Execução", ENUMS["gestores"])
+                apoio = st.selectbox("Apoio (opcional)", [""] + ENUMS["gestores"])
+                finalizado = st.selectbox("Finalizado", ENUMS["finalizado_tarefa"], index=1)
+            observacao = st.text_area("Observação")
+            submitted = st.form_submit_button("Adicionar atividade", type="primary", use_container_width=True)
+
+        if submitted:
+            identificacao = identificacao_nova.strip() if identificacao_nova.strip() else sugestao_identificacao.strip()
+            if not identificacao:
+                st.warning("Informe uma Identificação existente ou preencha uma nova identificação.")
+            elif not atividade.strip():
+                st.warning("Informe a descrição da atividade antes de adicionar.")
+            else:
+                now = pd.Timestamp(datetime.now())
+                id_nums = (
+                    df["id"]
+                    .dropna()
+                    .astype(str)
+                    .str.extract(r"T-(\d+)", expand=False)
+                    .dropna()
+                    .astype(int)
+                )
+                next_id = int(id_nums.max()) + 1 if len(id_nums) else 1
+                new_row = pd.DataFrame([{
+                    "id": f"T-{next_id:04d}",
+                    "categoria": categoria,
+                    "identificacao": identificacao,
+                    "atividade": atividade.strip(),
+                    "prazo": pd.Timestamp(prazo),
+                    "execucao": execucao,
+                    "apoio": apoio if apoio else "",
+                    "finalizado": finalizado,
+                    "observacao": observacao.strip(),
+                    "data_criacao": now,
+                    "data_atualizacao": now,
+                }])
+                updated = pd.concat([df, new_row], ignore_index=True)
+                st.session_state.df_tasks = prepare_task_dataframe(updated)
+                st.success("Atividade adicionada com sucesso.")
+                st.rerun()
+
+
+def render_grouped_task_dashboard(df: pd.DataFrame):
+    st.subheader("Painel operacional consolidado", anchor=False)
+    ativos = df[df["finalizado"] != "Sim"].copy()
+    if ativos.empty:
+        st.info("Não há atividades ativas para exibir.")
+        return
+
+    color_map = {"Atrasado": "🔴", "Esta semana": "🟡", "No prazo": "🟢"}
+    for identificacao, id_df in ativos.groupby("identificacao", sort=True):
+        status_counts = id_df["status"].value_counts()
+        resumo_status = " | ".join([f"{color_map.get(s, '⚪')} {s}: {n}" for s, n in status_counts.items()])
+        with st.expander(f"{identificacao} • {len(id_df)} atividade(s)"):
+            st.caption(resumo_status if resumo_status else "Sem status")
+            for categoria, cat_df in id_df.groupby("categoria", sort=True):
+                prazo_mais_proximo = cat_df["prazo"].min()
+                prazo_txt = pd.Timestamp(prazo_mais_proximo).strftime("%d/%m/%Y") if pd.notna(prazo_mais_proximo) else "-"
+                st.markdown(f"**{categoria}** — {len(cat_df)} atividade(s) • Prazo mais próximo: `{prazo_txt}`")
+                exibir = cat_df[["atividade", "prazo", "execucao", "apoio", "status", "observacao"]].copy()
+                exibir["status"] = exibir["status"].map(lambda s: f"{color_map.get(s, '⚪')} {s}")
+                st.dataframe(
+                    exibir,
+                    hide_index=True,
+                    use_container_width=True,
+                    column_config={"prazo": st.column_config.DateColumn("Prazo")},
+                )
+
+
+def render_task_history(df: pd.DataFrame):
+    historico = df[df["finalizado"] == "Sim"].copy()
+    with st.expander(f"Histórico de atividades finalizadas ({len(historico)})", icon=":material/history:"):
+        if historico.empty:
+            st.caption("Ainda não há atividades finalizadas.")
+        else:
+            st.dataframe(
+                historico[["id", "categoria", "identificacao", "atividade", "prazo", "execucao", "apoio", "observacao", "data_atualizacao"]],
+                hide_index=True,
+                use_container_width=True,
+                column_config={
+                    "prazo": st.column_config.DateColumn("Prazo"),
+                    "data_atualizacao": st.column_config.DatetimeColumn("Última atualização", format="DD/MM/YYYY HH:mm"),
+                },
+            )
+
+
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
@@ -593,133 +807,142 @@ def render_execution_pipeline():
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
-    st.header("Weekly planner", anchor=False)
-    st.caption("Actionable task tracking with automated status logic from the legacy Excel formula.")
+    st.header("Planejamento semanal", anchor=False)
+    st.caption("Planejamento operacional da equipe técnica com foco em execução, visibilidade de prazos e histórico.")
 
+    st.session_state.df_tasks = prepare_task_dataframe(st.session_state.df_tasks)
     df = st.session_state.df_tasks.copy()
-    df["status"] = df.apply(compute_task_status, axis=1)
-
-    # Sidebar filters
-    with st.sidebar:
-        st.subheader("Filtros de tarefas", anchor=False)
-        sel_cat = st.multiselect("Categoria", ENUMS["categoria_tarefa"],
-                                  default=ENUMS["categoria_tarefa"], key="task_cat")
-        sel_status = st.multiselect("Status", ENUMS["status_tarefa"],
-                                     default=["Atrasado", "Esta semana", "No prazo"], key="task_status")
-        sel_exec = st.multiselect("Executor", sorted(df["execucao"].dropna().unique()),
-                                    default=[], key="task_exec")
-
-    mask = df["categoria"].isin(sel_cat) & df["status"].isin(sel_status)
-    if sel_exec:
-        mask &= df["execucao"].isin(sel_exec)
-    fdf = df[mask]
-
-    # KPI cards
-    with st.container(horizontal=True):
-        st.metric(":red-background[:red[Atrasadas]]", len(df[df["status"] == "Atrasado"]), border=True)
-        st.metric(":orange-background[:orange[Esta semana]]", len(df[df["status"] == "Esta semana"]), border=True)
-        st.metric(":green-background[:green[No prazo]]", len(df[df["status"] == "No prazo"]), border=True)
-        st.metric("Finalizadas", len(df[df["status"] == "Finalizado"]), border=True)
-
-    col_chart, col_table = st.columns([1, 2])
 
+    render_task_kpis(df)
+    filtros = render_task_filters(df)
+    render_new_task_form(df)
+
+    mask = df["categoria"].isin(filtros["categoria"]) & df["status"].isin(filtros["status"])
+    if filtros["identificacao"]:
+        mask &= df["identificacao"].isin(filtros["identificacao"])
+    if filtros["pessoa"]:
+        mask &= (df["execucao"].isin(filtros["pessoa"]) | df["apoio"].isin(filtros["pessoa"]))
+    if filtros["apenas_ativas"]:
+        mask &= df["finalizado"] != "Sim"
+    if not filtros["incluir_historico"] and not filtros["apenas_ativas"]:
+        mask &= df["finalizado"] != "Sim"
+    fdf = df[mask].copy()
+
+    col_chart, col_resumo = st.columns([1, 1])
     with col_chart:
         with st.container(border=True):
-            st.subheader("Carga por categoria", anchor=False)
+            st.subheader("Distribuição por categoria e status", anchor=False)
             chart_src = (
-                df[df["status"].isin(["Atrasado", "Esta semana"])]
-                .groupby(["categoria", "status"]).size()
-                .reset_index(name="count")
+                fdf.groupby(["categoria", "status"]).size()
+                .reset_index(name="quantidade")
             )
             if not chart_src.empty:
                 fig = px.bar(
-                    chart_src, x="count", y="categoria", color="status",
-                    orientation="h", barmode="stack",
-                    color_discrete_map={"Atrasado": "#C00000", "Esta semana": "#BF8F00"},
-                    labels={"count": "Tarefas", "categoria": ""},
+                    chart_src,
+                    x="quantidade",
+                    y="categoria",
+                    color="status",
+                    orientation="h",
+                    barmode="stack",
+                    color_discrete_map={
+                        "Atrasado": "#C00000",
+                        "Esta semana": "#BF8F00",
+                        "No prazo": "#008A3B",
+                        "Finalizado": "#808080",
+                    },
+                    labels={"quantidade": "Atividades", "categoria": ""},
                 )
                 fig.update_layout(
-                    margin=dict(l=0, r=0, t=10, b=0), height=260,
-                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
+                    margin=dict(l=0, r=0, t=10, b=0),
+                    height=280,
+                    paper_bgcolor="rgba(0,0,0,0)",
+                    plot_bgcolor="rgba(0,0,0,0)",
                     legend_title_text="",
                 )
                 st.plotly_chart(fig, use_container_width=True)
             else:
-                st.success("Nenhuma tarefa atrasada ou da semana.", icon=":material/check_circle:")
+                st.info("Sem dados para os filtros selecionados.")
 
-    with col_table:
+    with col_resumo:
         with st.container(border=True):
-            st.subheader("Tarefas", anchor=False)
-            status_emoji = {"Atrasado": "🔴", "Esta semana": "🟡", "No prazo": "🟢", "Finalizado": "⚪"}
-            display = fdf.copy()
-            display["status_ui"] = display["status"].map(lambda s: f"{status_emoji.get(s, '')} {s}")
-            show_cols = ["categoria", "identificacao", "atividade", "prazo", "execucao", "status_ui"]
-            st.dataframe(
-                display[show_cols],
-                column_config={
-                    "prazo": st.column_config.DateColumn("Prazo"),
-                    "status_ui": "Status",
-                },
-                hide_index=True, use_container_width=True, height=350,
+            st.subheader("Resumo por executor", anchor=False)
+            resumo_exec = (
+                fdf[fdf["finalizado"] != "Sim"]
+                .groupby("execucao")
+                .size()
+                .reset_index(name="atividades")
+                .sort_values("atividades", ascending=False)
             )
+            if resumo_exec.empty:
+                st.caption("Sem atividades ativas para resumir.")
+            else:
+                st.dataframe(resumo_exec, hide_index=True, use_container_width=True)
 
-    with st.expander("Editar tarefas (atualiza status automaticamente)", icon=":material/edit:"):
+    render_grouped_task_dashboard(fdf if filtros["incluir_historico"] else fdf[fdf["finalizado"] != "Sim"])
+
+    with st.expander("Detalhamento e manutenção das atividades", icon=":material/edit:"):
         edited = st.data_editor(
-            df[["categoria", "identificacao", "atividade", "prazo", "execucao", "apoio", "finalizado"]],
+            df[["id", "categoria", "identificacao", "atividade", "prazo", "execucao", "apoio", "finalizado", "observacao"]],
             column_config={
                 "categoria": st.column_config.SelectboxColumn("Categoria", options=ENUMS["categoria_tarefa"]),
-                "finalizado": st.column_config.SelectboxColumn("Finalizado?", options=["Sim", "Não"]),
+                "finalizado": st.column_config.SelectboxColumn("Finalizado", options=ENUMS["finalizado_tarefa"]),
                 "prazo": st.column_config.DateColumn("Prazo"),
+                "id": st.column_config.TextColumn("ID", disabled=True),
             },
-            use_container_width=True, hide_index=True, num_rows="dynamic",
+            use_container_width=True,
+            hide_index=True,
+            num_rows="dynamic",
             key="tasks_editor",
         )
-        for col in edited.columns:
-            st.session_state.df_tasks[col] = edited[col]
+        edited["data_atualizacao"] = pd.Timestamp(datetime.now())
+        edited = edited.merge(df[["id", "data_criacao"]], on="id", how="left")
+        st.session_state.df_tasks = prepare_task_dataframe(edited)
+
+    render_task_history(st.session_state.df_tasks)
 
 
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
@@ -746,40 +969,40 @@ def render_team_allocation():
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
-    ":material/checklist: Weekly planner": render_weekly_tracker,
+    ":material/checklist: Planejamento semanal": render_weekly_tracker,
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
