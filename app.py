import json
from pathlib import Path

import gspread
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from google.oauth2.service_account import Credentials
from yaml.loader import SafeLoader

# ── Page config
st.set_page_config(
    page_title="RAR Dash · Perfumes",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Styles
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600;700&family=Jost:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Jost', sans-serif;
    background-color: #0c0c0c;
    color: #e8e0d5;
}
.main { background-color: #0c0c0c; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }

.title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 3rem;
    font-weight: 300;
    letter-spacing: 0.15em;
    color: #e8e0d5;
    text-transform: uppercase;
}
.subtitle {
    font-size: 0.75rem;
    letter-spacing: 0.3em;
    color: #6b6560;
    text-transform: uppercase;
    margin-bottom: 2.5rem;
}
.kpi-box {
    background: #161616;
    border: 1px solid #2a2520;
    border-radius: 4px;
    padding: 1.2rem 1.5rem;
}
.kpi-label {
    font-size: 0.65rem;
    letter-spacing: 0.25em;
    color: #6b6560;
    text-transform: uppercase;
}
.kpi-value {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2rem;
    font-weight: 600;
    color: #e8e0d5;
    margin-top: 0.2rem;
}
.kpi-value-accent { color: #c9a96e; }
.section-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.3rem;
    font-weight: 400;
    letter-spacing: 0.1em;
    color: #e8e0d5;
    border-bottom: 1px solid #2a2520;
    padding-bottom: 0.5rem;
    margin-bottom: 1.2rem;
    text-transform: uppercase;
}
.product-card {
    background: #161616;
    border: 1px solid #2a2520;
    border-radius: 4px;
    padding: 1rem;
    margin-bottom: 0.8rem;
}
.product-card:hover { border-color: #c9a96e; }
.product-name {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.1rem;
    color: #e8e0d5;
    margin-bottom: 0.5rem;
}
.product-detail { font-size: 0.75rem; color: #6b6560; letter-spacing: 0.08em; }
.badge-low {
    background: #2a1515; color: #c97070;
    border-radius: 999px; padding: 1px 8px;
    font-size: 0.68rem; letter-spacing: 0.05em;
}
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {
    background: #161616 !important;
    border: 1px solid #2a2520 !important;
    border-radius: 4px !important;
    color: #e8e0d5 !important;
    font-family: 'Jost', sans-serif !important;
}
.stButton > button {
    background: #c9a96e !important;
    color: #0c0c0c !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'Jost', sans-serif !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    padding: 0.5rem 1.5rem !important;
}
.stButton > button:hover { background: #e0c080 !important; }
</style>
""",
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).resolve().parent
AUTH_PATH = BASE_DIR / "auth.yaml"
DATA_PATH = BASE_DIR / "data" / "PLANILHA PERFUMES.xlsx"

PLOTLY_THEME = dict(
    paper_bgcolor="#0c0c0c",
    plot_bgcolor="#0c0c0c",
    font=dict(family="Jost", color="#e8e0d5"),
    colorway=["#c9a96e", "#8b7355", "#e8e0d5", "#6b6560", "#c97070"],
)

# ── Auth setup
if "credentials" in st.secrets:
    # Streamlit Cloud — lê dos Secrets
    config = {
        "credentials": {"usernames": {}},
        "cookie": {
            "name": st.secrets["cookie"]["name"],
            "key": st.secrets["cookie"]["key"],
            "expiry_days": st.secrets["cookie"]["expiry_days"],
        },
    }
    for username, data in st.secrets["credentials"]["usernames"].items():
        config["credentials"]["usernames"][username] = dict(data)
else:
    # Local — lê do auth.yaml
    with open(AUTH_PATH, "r", encoding="utf-8") as f:
        config = yaml.load(f, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

st.markdown('<div class="title">RAR Dash</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Catálogo · Perfumes</div>', unsafe_allow_html=True)

authenticator.login(
    location="main",
    fields={
        "Form name": "Entrar",
        "Username": "Usuário",
        "Password": "Senha",
        "Login": "Entrar",
    },
)

authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")

if authentication_status is False:
    st.error("Usuário ou senha incorretos.")
    st.stop()

if authentication_status is None:
    st.stop()

with st.sidebar:
    st.markdown(f"**{name or ''}**")
    authenticator.logout(button_name="Sair", location="sidebar")


# ── Data
USE_GSHEETS = "gcp_service_account" in st.secrets


@st.cache_data(ttl=30)
def load_data() -> pd.DataFrame:
    if USE_GSHEETS:
        ws = _get_worksheet()
        data = ws.get_all_records(numericise_ignore=["all"])
        df = pd.DataFrame(data)
    else:
        df = pd.read_excel(DATA_PATH)

    df = df.replace(r"^\s*$", pd.NA, regex=True)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def save_data(df: pd.DataFrame) -> None:
    if USE_GSHEETS:
        ws = _get_worksheet()
        # Limpa a planilha e reescreve com o dataframe atualizado
        ws.clear()
        ws.update([df.columns.tolist()] + df.fillna("").values.tolist())
    else:
        with pd.ExcelWriter(DATA_PATH, engine="openpyxl", mode="w") as writer:
            df.to_excel(writer, index=False)

    st.cache_data.clear()


df = load_data()


def find_col(df: pd.DataFrame, keys: list[str], default=None):
    for c in df.columns:
        low = str(c).lower()
        if any(k in low for k in keys):
            return c
    return default


col_perfume = find_col(df, ["perfume", "nome", "produto"], df.columns[0])
col_custo = find_col(df, ["custo", "cost"])
col_estoque = find_col(df, ["estoque", "stock"])
col_venda = find_col(df, ["venda", "preco", "valor"])
col_imagem = find_col(df, ["imagem", "image", "foto"])

for col in [col_custo, col_estoque, col_venda]:
    if col:
        df[col] = pd.to_numeric(df[col], errors="coerce")

if col_custo and col_venda:
    df["_margem_pct"] = ((df[col_venda] - df[col_custo]) / df[col_custo] * 100).round(1)
    df["_lucro_unit"] = (df[col_venda] - df[col_custo]).round(2)

# ── KPIs
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        f'<div class="kpi-box"><div class="kpi-label">Produtos</div><div class="kpi-value">{len(df)}</div></div>',
        unsafe_allow_html=True,
    )

with k2:
    total_estoque = int(df[col_estoque].fillna(0).sum()) if col_estoque else 0
    st.markdown(
        f'<div class="kpi-box"><div class="kpi-label">Total em estoque</div><div class="kpi-value">{total_estoque} un.</div></div>',
        unsafe_allow_html=True,
    )

with k3:
    avg_margem = df["_margem_pct"].mean() if "_margem_pct" in df.columns else None
    val = (
        f"{avg_margem:.1f}%" if avg_margem is not None and pd.notna(avg_margem) else "—"
    )
    st.markdown(
        f'<div class="kpi-box"><div class="kpi-label">Margem média</div><div class="kpi-value kpi-value-accent">{val}</div></div>',
        unsafe_allow_html=True,
    )

with k4:
    capital = (
        ((df[col_custo].fillna(0) * df[col_estoque].fillna(0)).sum())
        if col_custo and col_estoque
        else None
    )
    val = f"R$ {capital:,.2f}" if capital is not None else "—"
    st.markdown(
        f'<div class="kpi-box"><div class="kpi-label">Capital em estoque</div><div class="kpi-value">{val}</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs
tab1, tab2, tab3 = st.tabs(["Catálogo", "Simulador de Venda", "Editar Dados"])

# ── Tab 1 — Catálogo
with tab1:
    search = st.text_input("🔍 Buscar perfume", placeholder="Digite o nome...")
    filtered = (
        df[df[col_perfume].astype(str).str.contains(search, case=False, na=False)]
        if search
        else df
    )

    col_cards, col_charts = st.columns([1, 1.6], gap="large")

    with col_cards:
        st.markdown('<div class="section-title">Produtos</div>', unsafe_allow_html=True)

        for _, row in filtered.iterrows():
            nome = row[col_perfume] if pd.notna(row[col_perfume]) else "—"
            custo = (
                f"R$ {row[col_custo]:.2f}"
                if col_custo and pd.notna(row.get(col_custo))
                else "—"
            )
            venda = (
                f"R$ {row[col_venda]:.2f}"
                if col_venda and pd.notna(row.get(col_venda))
                else "—"
            )
            estoque = (
                int(row[col_estoque])
                if col_estoque and pd.notna(row.get(col_estoque))
                else 0
            )
            margem = (
                f"{row['_margem_pct']:.1f}%"
                if "_margem_pct" in df.columns and pd.notna(row.get("_margem_pct"))
                else "—"
            )
            badge = (
                f'<span class="badge-low">{estoque} un.</span>'
                if estoque <= 5
                else f'<span style="color:#6b6560;font-size:0.75rem;">{estoque} un.</span>'
            )

            st.markdown(
                f"""
                <div class="product-card">
                    <div class="product-name">{nome}</div>
                    <div style="display:flex;gap:1.5rem;flex-wrap:wrap;">
                        <span class="product-detail">Custo: <strong style="color:#e8e0d5">{custo}</strong></span>
                        <span class="product-detail">Venda: <strong style="color:#c9a96e">{venda}</strong></span>
                        <span class="product-detail">Margem: <strong style="color:#c9a96e">{margem}</strong></span>
                        <span class="product-detail">Estoque: {badge}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_charts:
        st.markdown('<div class="section-title">Análise</div>', unsafe_allow_html=True)

        if "_margem_pct" in df.columns and col_custo and col_venda:
            chart_df = filtered[
                [col_perfume, "_margem_pct", "_lucro_unit", col_custo, col_venda]
            ].dropna()

            if not chart_df.empty:
                fig1 = go.Figure(
                    go.Bar(
                        x=chart_df[col_perfume],
                        y=chart_df["_margem_pct"],
                        marker_color=[
                            "#c9a96e"
                            if v >= chart_df["_margem_pct"].mean()
                            else "#8b7355"
                            for v in chart_df["_margem_pct"]
                        ],
                        text=[f"{v:.1f}%" for v in chart_df["_margem_pct"]],
                        textposition="outside",
                    )
                )
                fig1.update_layout(
                    **PLOTLY_THEME,
                    title=dict(
                        text="Margem de Lucro (%)",
                        font=dict(family="Cormorant Garamond", size=16),
                    ),
                    xaxis=dict(showgrid=False, tickangle=-30),
                    yaxis=dict(showgrid=True, gridcolor="#1e1e1e", title=""),
                    margin=dict(t=50, b=60, l=20, r=20),
                    height=280,
                    showlegend=False,
                )
                st.plotly_chart(fig1, use_container_width=True)

                fig2 = go.Figure()
                fig2.add_trace(
                    go.Bar(
                        name="Custo",
                        x=chart_df[col_perfume],
                        y=chart_df[col_custo],
                        marker_color="#2a2520",
                    )
                )
                fig2.add_trace(
                    go.Bar(
                        name="Venda",
                        x=chart_df[col_perfume],
                        y=chart_df[col_venda],
                        marker_color="#c9a96e",
                    )
                )
                fig2.update_layout(
                    **PLOTLY_THEME,
                    title=dict(
                        text="Custo vs Preço de Venda",
                        font=dict(family="Cormorant Garamond", size=16),
                    ),
                    barmode="group",
                    xaxis=dict(showgrid=False, tickangle=-30),
                    yaxis=dict(showgrid=True, gridcolor="#1e1e1e", tickprefix="R$ "),
                    margin=dict(t=50, b=60, l=20, r=20),
                    height=280,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                )
                st.plotly_chart(fig2, use_container_width=True)

# ── Tab 2 — Simulador
with tab2:
    st.markdown(
        '<div class="section-title">Simulador de Venda</div>', unsafe_allow_html=True
    )
    st.markdown(
        '<p style="color:#6b6560;font-size:0.8rem;margin-bottom:1.5rem;">Calcule a margem e o lucro para qualquer valor de venda em tempo real.</p>',
        unsafe_allow_html=True,
    )

    produtos = df[col_perfume].dropna().tolist()
    produto_sel = st.selectbox("Perfume", produtos)
    row_sel = df[df[col_perfume] == produto_sel].iloc[0]

    custo_base = (
        float(row_sel[col_custo])
        if col_custo and pd.notna(row_sel.get(col_custo))
        else 0.0
    )
    estoque_atual = (
        int(row_sel[col_estoque])
        if col_estoque and pd.notna(row_sel.get(col_estoque))
        else 0
    )

    col_sim1, col_sim2 = st.columns([1, 1], gap="large")

    with col_sim1:
        venda_sim = st.number_input(
            "Valor de venda (R$)",
            min_value=0.0,
            value=float(row_sel[col_venda])
            if col_venda and pd.notna(row_sel.get(col_venda))
            else custo_base,
            step=0.50,
            format="%.2f",
        )
        qtd_sim = st.number_input(
            "Quantidade vendida",
            min_value=1,
            max_value=estoque_atual if estoque_atual > 0 else 999,
            value=1,
        )

    lucro_unit = venda_sim - custo_base
    margem_sim = (lucro_unit / custo_base * 100) if custo_base > 0 else 0
    lucro_total = lucro_unit * qtd_sim
    color_margem = "#c9a96e" if margem_sim >= 0 else "#c97070"

    with col_sim2:
        st.markdown(
            f"""
            <div class="kpi-box" style="margin-bottom:0.8rem">
                <div class="kpi-label">Custo unitário</div>
                <div class="kpi-value">R$ {custo_base:.2f}</div>
            </div>
            <div class="kpi-box" style="margin-bottom:0.8rem">
                <div class="kpi-label">Lucro por unidade</div>
                <div class="kpi-value" style="color:{color_margem}">R$ {lucro_unit:.2f}</div>
            </div>
            <div class="kpi-box" style="margin-bottom:0.8rem">
                <div class="kpi-label">Margem</div>
                <div class="kpi-value" style="color:{color_margem}">{margem_sim:.1f}%</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Lucro total ({qtd_sim} un.)</div>
                <div class="kpi-value" style="color:{color_margem}">R$ {lucro_total:.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=margem_sim,
            number=dict(
                suffix="%",
                font=dict(family="Cormorant Garamond", size=40, color="#e8e0d5"),
            ),
            delta=dict(
                reference=float(df["_margem_pct"].mean())
                if "_margem_pct" in df.columns
                else 0,
                suffix="%",
            ),
            gauge=dict(
                axis=dict(range=[-20, 100], tickcolor="#6b6560"),
                bar=dict(color="#c9a96e"),
                bgcolor="#161616",
                bordercolor="#2a2520",
                steps=[
                    dict(range=[-20, 0], color="#2a1515"),
                    dict(range=[0, 30], color="#1e1a15"),
                    dict(range=[30, 100], color="#1a1e15"),
                ],
                threshold=dict(
                    line=dict(color="#e8e0d5", width=2),
                    thickness=0.75,
                    value=margem_sim,
                ),
            ),
            title=dict(
                text="Margem de Lucro",
                font=dict(family="Cormorant Garamond", size=18, color="#6b6560"),
            ),
        )
    )
    fig_gauge.update_layout(
        **PLOTLY_THEME, height=300, margin=dict(t=40, b=20, l=40, r=40)
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

# ── Tab 3 — Editar
with tab3:
    st.markdown(
        '<div class="section-title">Editar Estoque & Preço de Venda</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="color:#6b6560;font-size:0.8rem;margin-bottom:1.5rem;">Apenas estoque e valor de venda podem ser editados aqui. Demais informações devem ser alteradas na planilha base.</p>',
        unsafe_allow_html=True,
    )

    cols_edit = [col_perfume] + [c for c in [col_estoque, col_venda] if c]
    edited_view = st.data_editor(
        df[cols_edit].copy(),
        use_container_width=True,
        num_rows="fixed",
        column_config={
            col_perfume: st.column_config.TextColumn(col_perfume, disabled=True),
            **(
                {
                    col_estoque: st.column_config.NumberColumn(
                        "Estoque", min_value=0, step=1, format="%d un."
                    )
                }
                if col_estoque
                else {}
            ),
            **(
                {
                    col_venda: st.column_config.NumberColumn(
                        "Valor de Venda (R$)",
                        min_value=0.0,
                        step=0.50,
                        format="R$ %.2f",
                    )
                }
                if col_venda
                else {}
            ),
        },
        hide_index=True,
    )

    if st.button("💾 Salvar alterações"):
        if col_estoque:
            df[col_estoque] = edited_view[col_estoque]
        if col_venda:
            df[col_venda] = edited_view[col_venda]
        try:
            save_data(df)
            st.success("Planilha atualizada com sucesso.")
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
