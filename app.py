def compute_task_status(row: pd.Series) -> str:
    finalizado = str(row.get("finalizado", "Não")).strip().title()
    if finalizado == "Sim":
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


def init_team_members():
    if "team_members" not in st.session_state:
        st.session_state.team_members = sorted(ENUMS["gestores"])


def get_available_team_members(df: pd.DataFrame) -> list[str]:
    dynamic_members = set(st.session_state.get("team_members", []))
    historical_members = set(df["execucao"].dropna().astype(str).str.strip()) | set(
        df["apoio"].dropna().astype(str).str.strip()
    )
    combined = {m for m in dynamic_members.union(historical_members) if m}
    return sorted(combined)


def prepare_task_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    required_defaults = {
        "id": "",
        "categoria": "Projeto",
        "identificacao": "",
        "atividade": "",
        "prazo": pd.NaT,
        "execucao": "",
        "apoio": "",
        "finalizado": "Não",
        "observacao": "",
        "status": "",
        "data_criacao": pd.NaT,
        "data_atualizacao": pd.NaT,
    }
    prepared = df.copy()
    for col, default in required_defaults.items():
        if col not in prepared.columns:
            prepared[col] = default

    categoria_map = {
        "Projetos": "Projeto",
        "Projetos internos": "Projeto Interno",
        "Prospecções": "Prospecção",
    }
    prepared["categoria"] = (
        prepared["categoria"]
        .replace(categoria_map)
        .fillna("Projeto")
    )
    prepared["categoria"] = prepared["categoria"].where(
        prepared["categoria"].isin(ENUMS["categoria_tarefa"]), "Projeto"
    )

    prepared["finalizado"] = (
        prepared["finalizado"]
        .fillna("Não")
        .astype(str)
        .str.strip()
        .str.title()
    )
    prepared["finalizado"] = prepared["finalizado"].where(
        prepared["finalizado"].isin(ENUMS["finalizado_tarefa"]), "Não"
    )

    prepared["prazo"] = pd.to_datetime(prepared["prazo"], errors="coerce")
    prepared["data_criacao"] = pd.to_datetime(prepared["data_criacao"], errors="coerce")
    prepared["data_atualizacao"] = pd.to_datetime(prepared["data_atualizacao"], errors="coerce")

    now = pd.Timestamp(datetime.now())
    if prepared["id"].eq("").any() or prepared["id"].isna().any():
        max_id = (
            prepared["id"]
            .dropna()
            .astype(str)
            .str.extract(r"T-(\d+)", expand=False)
            .dropna()
            .astype(int)
            .max()
        )
        next_id = 1 if pd.isna(max_id) else int(max_id) + 1
        for idx in prepared.index:
            if pd.isna(prepared.at[idx, "id"]) or str(prepared.at[idx, "id"]).strip() == "":
                prepared.at[idx, "id"] = f"T-{next_id:04d}"
                next_id += 1

    prepared["data_criacao"] = prepared["data_criacao"].fillna(now)
    prepared["data_atualizacao"] = prepared["data_atualizacao"].fillna(now)
    prepared["status"] = prepared.apply(compute_task_status, axis=1)
    return prepared


def render_task_kpis(df: pd.DataFrame):
    ativos = df[df["finalizado"] != "Sim"]
    with st.container(horizontal=True):
        st.metric("Atividades ativas", len(ativos), border=True)
        st.metric(":red-background[:red[Atrasadas]]", len(ativos[ativos["status"] == "Atrasado"]), border=True)
        st.metric(":orange-background[:orange[Esta semana]]", len(ativos[ativos["status"] == "Esta semana"]), border=True)
        st.metric(":green-background[:green[No prazo]]", len(ativos[ativos["status"] == "No prazo"]), border=True)
        st.metric("Finalizadas", len(df[df["status"] == "Finalizado"]), border=True)


def render_task_filters(df: pd.DataFrame, team_options: list[str]) -> dict:
    identificacoes = sorted(df["identificacao"].dropna().astype(str).unique().tolist())
    with st.container(border=True):
        st.subheader("Filtros", anchor=False)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            pessoa = st.multiselect("Pessoa (Execução/Apoio)", team_options, default=[], key="task_filter_pessoa")
        with col2:
            categoria = st.multiselect(
                "Categoria", ENUMS["categoria_tarefa"], default=ENUMS["categoria_tarefa"], key="task_filter_categoria"
            )
        with col3:
            identificacao = st.multiselect("Identificação", identificacoes, default=[], key="task_filter_identificacao")
            status = st.multiselect(
                "Status", ENUMS["status_tarefa"], default=["Atrasado", "Esta semana", "No prazo"], key="task_filter_status"
            )
        with col4:
            apenas_ativas = st.toggle("Mostrar apenas ativas", value=True, key="task_filter_ativas")
            incluir_historico = st.toggle("Incluir histórico (finalizadas)", value=False, key="task_filter_historico")
    return {
        "pessoa": pessoa,
        "categoria": categoria,
        "identificacao": identificacao,
        "status": status,
        "apenas_ativas": apenas_ativas,
        "incluir_historico": incluir_historico,
    }


def render_team_management():
    with st.expander("Gestão de equipe", expanded=False):
        col1, col2 = st.columns([2, 1])
        with col1:
            novo_membro = st.text_input(
                "Adicionar membro",
                key="novo_membro_equipe",
                placeholder="Digite o nome do novo membro",
            )
        with col2:
            add_clicked = st.button("Adicionar membro", use_container_width=True)
        if add_clicked:
            nome = novo_membro.strip()
            if not nome:
                st.warning("Informe um nome para adicionar.")
            elif nome in st.session_state.team_members:
                st.info("Este membro já está na equipe.")
            else:
                st.session_state.team_members = sorted(st.session_state.team_members + [nome])
                st.success(f"{nome} adicionado à equipe.")
                st.rerun()
        st.caption("Membros disponíveis: " + ", ".join(st.session_state.team_members))


def render_new_task_form(df: pd.DataFrame, team_options: list[str]):
    with st.expander("Nova atividade", expanded=False):
        identificacoes_existentes = sorted(df["identificacao"].dropna().astype(str).unique().tolist())
        with st.form("nova_atividade_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                categoria = st.selectbox("Categoria", ENUMS["categoria_tarefa"])
                sugestao_identificacao = st.selectbox("Identificação existente (opcional)", [""] + identificacoes_existentes)
                atividade = st.text_input("Atividade")
                prazo = st.date_input("Prazo", value=datetime.today())
            with col2:
                identificacao_nova = st.text_input("Nova identificação (opcional)")
                execucao = st.selectbox("Execução", team_options if team_options else ENUMS["gestores"])
                apoio = st.selectbox("Apoio (opcional)", [""] + (team_options if team_options else ENUMS["gestores"]))
                finalizado = st.selectbox("Finalizado", ENUMS["finalizado_tarefa"], index=1)
            observacao = st.text_area("Observação")
            submitted = st.form_submit_button("Adicionar atividade", type="primary", use_container_width=True)

        if submitted:
            identificacao = identificacao_nova.strip() if identificacao_nova.strip() else sugestao_identificacao.strip()
            if not identificacao:
                st.warning("Informe uma Identificação existente ou preencha uma nova identificação.")
            elif not atividade.strip():
                st.warning("Informe a descrição da atividade antes de adicionar.")
            else:
                now = pd.Timestamp(datetime.now())
                id_nums = (
                    df["id"]
                    .dropna()
                    .astype(str)
                    .str.extract(r"T-(\d+)", expand=False)
                    .dropna()
                    .astype(int)
                )
                next_id = int(id_nums.max()) + 1 if len(id_nums) else 1
                new_row = pd.DataFrame([{
                    "id": f"T-{next_id:04d}",
                    "categoria": categoria,
                    "identificacao": identificacao,
                    "atividade": atividade.strip(),
                    "prazo": pd.Timestamp(prazo),
                    "execucao": execucao,
                    "apoio": apoio if apoio else "",
                    "finalizado": finalizado,
                    "observacao": observacao.strip(),
                    "data_criacao": now,
                    "data_atualizacao": now,
                }])
                st.session_state.df_tasks = prepare_task_dataframe(pd.concat([df, new_row], ignore_index=True))
                st.success("Atividade adicionada com sucesso.")
                st.rerun()


def filter_active_tasks(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    mask = df["categoria"].isin(filtros["categoria"]) & df["status"].isin(filtros["status"])
    if filtros["identificacao"]:
        mask &= df["identificacao"].isin(filtros["identificacao"])
    if filtros["pessoa"]:
        mask &= (df["execucao"].isin(filtros["pessoa"]) | df["apoio"].isin(filtros["pessoa"]))
    if filtros["apenas_ativas"] or not filtros["incluir_historico"]:
        mask &= df["finalizado"] != "Sim"
    return df[mask].copy()


def sort_tasks_for_operational_view(df: pd.DataFrame) -> pd.DataFrame:
    status_ordem = {"Atrasado": 0, "Esta semana": 1, "No prazo": 2, "Finalizado": 3}
    temp = df.copy()
    temp["status_ordem"] = temp["status"].map(status_ordem).fillna(9)
    temp["prazo_ordem"] = pd.to_datetime(temp["prazo"], errors="coerce").fillna(pd.Timestamp.max)
    temp = temp.sort_values(["identificacao", "prazo_ordem", "status_ordem", "categoria", "atividade"])
    return temp.drop(columns=["status_ordem", "prazo_ordem"], errors="ignore")


def render_flowing_operational_panel(df: pd.DataFrame):
    st.subheader("Painel operacional consolidado", anchor=False)
    ativos = sort_tasks_for_operational_view(df[df["finalizado"] != "Sim"].copy())
    if ativos.empty:
        st.info("Nenhuma atividade encontrada para os filtros selecionados.")
        return

    status_style = {
        "Atrasado": ("🔴", "#f8d7da", "#842029"),
        "Esta semana": ("🟡", "#fff3cd", "#664d03"),
        "No prazo": ("🟢", "#d1e7dd", "#0f5132"),
    }
    with st.container(border=True):
        for identificacao, id_df in ativos.groupby("identificacao", sort=True):
            resumo_categorias = id_df["categoria"].value_counts()
            resumo_txt = " | ".join([f"{cat}: {qt}" for cat, qt in resumo_categorias.items()])
            st.markdown(f"**{identificacao}**")
            st.caption(f"{len(id_df)} atividade(s) • {resumo_txt}")
            for _, row in id_df.iterrows():
                emoji, bg, fg = status_style.get(row["status"], ("⚪", "#ececec", "#4a4a4a"))
                prazo_txt = pd.Timestamp(row["prazo"]).strftime("%d/%m/%Y") if pd.notna(row["prazo"]) else "-"
                apoio_txt = row["apoio"] if str(row["apoio"]).strip() else "—"
                obs_txt = f" • Obs: {row['observacao']}" if str(row["observacao"]).strip() else ""
                st.markdown(
                    f"""
                    <div style="padding:6px 8px; margin-bottom:4px; border:1px solid #e6e6e6; border-radius:6px;">
                        <div style="display:flex; justify-content:space-between; gap:8px;">
                            <div style="font-size:0.88rem;">
                                <b>{row["categoria"]}</b> · {row["atividade"]}<br>
                                <span style="opacity:0.82;">Prazo: {prazo_txt} · Execução: {row["execucao"]} · Apoio: {apoio_txt}{obs_txt}</span>
                            </div>
                            <div>
                                <span style="background:{bg}; color:{fg}; padding:2px 8px; border-radius:999px; font-size:0.78rem;">
                                    {emoji} {row["status"]}
                                </span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.divider()


def render_task_history(df: pd.DataFrame):
    historico = df[df["finalizado"] == "Sim"].copy()
    with st.expander(f"Histórico de atividades finalizadas ({len(historico)})", icon=":material/history:"):
        if historico.empty:
            st.caption("Ainda não há atividades finalizadas.")
        else:
            st.dataframe(
                historico[["id", "categoria", "identificacao", "atividade", "prazo", "execucao", "apoio", "observacao", "data_atualizacao"]],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "prazo": st.column_config.DateColumn("Prazo"),
                    "data_atualizacao": st.column_config.DatetimeColumn("Última atualização", format="DD/MM/YYYY HH:mm"),
                },
            )


def render_weekly_tracker():
    st.header("Planejamento semanal", anchor=False)
    st.caption("Acompanhamento operacional das atividades da equipe.")

    init_team_members()
    st.session_state.df_tasks = prepare_task_dataframe(st.session_state.df_tasks)
    df = st.session_state.df_tasks.copy()
    team_options = get_available_team_members(df)

    render_task_kpis(df)
    filtros = render_task_filters(df, team_options)
    render_team_management()
    render_new_task_form(df, team_options)
    fdf = filter_active_tasks(df, filtros)
    render_flowing_operational_panel(fdf)

    with st.expander("Detalhamento e manutenção das atividades", icon=":material/edit:"):
        edited = st.data_editor(
            df[["id", "categoria", "identificacao", "atividade", "prazo", "execucao", "apoio", "finalizado", "observacao"]],
            column_config={
                "categoria": st.column_config.SelectboxColumn("Categoria", options=ENUMS["categoria_tarefa"]),
                "finalizado": st.column_config.SelectboxColumn("Finalizado", options=ENUMS["finalizado_tarefa"]),
                "prazo": st.column_config.DateColumn("Prazo"),
                "execucao": st.column_config.SelectboxColumn("Execução", options=team_options),
                "apoio": st.column_config.SelectboxColumn("Apoio", options=[""] + team_options),
                "id": st.column_config.TextColumn("ID", disabled=True),
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="tasks_editor",
        )
        edited["data_atualizacao"] = pd.Timestamp(datetime.now())
        edited = edited.merge(df[["id", "data_criacao"]], on="id", how="left")
        st.session_state.df_tasks = prepare_task_dataframe(edited)

    render_task_history(st.session_state.df_tasks)
