import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ───────────────────────────────────────────────
#  CONFIG
# ───────────────────────────────────────────────
st.set_page_config(
    page_title="Comissões Consigaz",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ───────────────────────────────────────────────
#  ESTILO GLOBAL
# ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A3D62 0%, #1a5276 100%);
}
section[data-testid="stSidebar"] * { color: white !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.2); }

div.stButton > button {
    background: linear-gradient(135deg, #0A3D62, #1a6fa8);
    color: white !important;
    border: none;
    border-radius: 8px;
    padding: 0.55em 1.2em;
    font-weight: 600;
    width: 100%;
    transition: opacity .2s;
}
div.stButton > button:hover { opacity: 0.88; }

/* Botão vermelho para remover */
.btn-danger > button {
    background: linear-gradient(135deg, #c0392b, #e74c3c) !important;
}

div[data-testid="metric-container"] {
    background: #f0f4f8;
    border-left: 4px solid #0A3D62;
    border-radius: 10px;
    padding: 18px 22px;
}

.section-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #0A3D62;
    margin-bottom: 0.5rem;
    border-bottom: 2px solid #0A3D62;
    padding-bottom: 6px;
}

/* Login card por perfil */
.perfil-card {
    border: 2px solid transparent;
    border-radius: 12px;
    padding: 18px;
    text-align: center;
    cursor: pointer;
    transition: all .2s;
    background: white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.perfil-rh      { border-color: #1a6fa8; }
.perfil-gerente { border-color: #27ae60; }
.perfil-diretor { border-color: #8e44ad; }

.badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:.78rem; font-weight:600; }
.badge-pendente  { background:#fff3cd; color:#856404; }
.badge-rh        { background:#cfe2ff; color:#084298; }
.badge-concluido { background:#d1e7dd; color:#0a3622; }

.func-card {
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
</style>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────────
#  BANCO DE DADOS
# ───────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return sqlite3.connect("data.db", check_same_thread=False)

conn = get_conn()
c    = conn.cursor()

c.executescript("""
CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    password      TEXT NOT NULL,
    role          TEXT NOT NULL,
    centro_custo  TEXT DEFAULT '',
    nome_completo TEXT DEFAULT '',
    criado_em     TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS requests (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa          TEXT,
    estabelecimento  TEXT,
    localidade       TEXT,
    matricula        TEXT,
    nome             TEXT,
    admissao         TEXT,
    cargo            TEXT,
    centro_custo     TEXT,
    valor_comissao   REAL DEFAULT 0,
    perc_dsr         REAL DEFAULT 0,
    valor_total      REAL DEFAULT 0,
    status           TEXT DEFAULT 'Pendente Gerente',
    atualizado_em    TEXT DEFAULT ''
);
""")
conn.commit()

# Usuários padrão
defaults = [
    ("admin",   "admin123",   "rh",      "", "Administrador RH",   ),
    ("diretor", "diretor123", "diretor", "", "Diretor Geral",       ),
]
for u, p, r, cc, nm in defaults:
    c.execute("SELECT 1 FROM users WHERE username=?", (u,))
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?,?,?,?)",
                  (u, p, r, cc, nm, datetime.now().strftime("%d/%m/%Y %H:%M")))
conn.commit()

# ───────────────────────────────────────────────
#  CENTROS DE CUSTO
# ───────────────────────────────────────────────
CENTROS = [
    "COMERCIAL",
    "GERENTE DE BASE - (Barueri)",
    "VENDAS - (Barueri)",
    "POS VENDAS - (Barueri)",
]

ROLE_LABELS = {
    "rh":      ("👩‍💼", "RH",      "#1a6fa8"),
    "gerente": ("👨‍💼", "Gerente", "#27ae60"),
    "diretor": ("🏢",  "Diretor", "#8e44ad"),
}

# ───────────────────────────────────────────────
#  HELPERS
# ───────────────────────────────────────────────
def fmt_brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except:
        return "R$ 0,00"

# ───────────────────────────────────────────────
#  SIDEBAR
# ───────────────────────────────────────────────
def render_sidebar():
    user = st.session_state.user
    icon, label, color = ROLE_LABELS.get(user["role"], ("👤","","#333"))
    with st.sidebar:
        try:
            st.image("logo.png", width=160)
        except:
            st.markdown("## 💼 Consigaz")
        st.markdown("---")
        st.markdown(f"**{icon} {user.get('nome_completo') or user['username']}**")
        st.caption(f"Perfil: `{label}`")
        if user.get("centro_custo"):
            st.caption(f"📍 {user['centro_custo']}")
        st.markdown("---")
        if st.button("🚪 Sair"):
            st.session_state.clear()
            st.rerun()

# ───────────────────────────────────────────────
#  LOGIN  (seleção de perfil + credenciais)
# ───────────────────────────────────────────────
def login():
    col_l, col_c, col_r = st.columns([1, 1.6, 1])
    with col_c:
        try:
            st.image("logo.png", width=180)
        except:
            st.markdown("## 💼 Consigaz")

        st.markdown("### Bem-vindo ao Sistema de Comissões")
        st.markdown("Selecione seu perfil de acesso:")
        st.markdown("<br>", unsafe_allow_html=True)

        # Seleção visual de perfil
        p1, p2, p3 = st.columns(3)
        perfis = ["rh", "gerente", "diretor"]
        icons  = ["👩‍💼", "👨‍💼", "🏢"]
        nomes  = ["RH", "Gerente", "Diretor"]
        cores  = ["#1a6fa8", "#27ae60", "#8e44ad"]

        if "perfil_sel" not in st.session_state:
            st.session_state.perfil_sel = "rh"

        for col, p, ic, nm, cor in zip([p1,p2,p3], perfis, icons, nomes, cores):
            selecionado = st.session_state.perfil_sel == p
            borda = f"3px solid {cor}" if selecionado else "2px solid #dee2e6"
            bg    = f"rgba({','.join(str(int(cor[i:i+2],16)) for i in (1,3,5))},0.08)" if selecionado else "white"
            col.markdown(f"""
            <div style="border:{borda};border-radius:12px;padding:16px;
                        text-align:center;background:{bg};cursor:pointer;">
                <div style="font-size:2rem">{ic}</div>
                <div style="font-weight:600;color:{cor}">{nm}</div>
            </div>
            """, unsafe_allow_html=True)
            if col.button(f"Selecionar {nm}", key=f"sel_{p}"):
                st.session_state.perfil_sel = p
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        perfil_atual = st.session_state.perfil_sel
        ic_a, nm_a, cor_a = icons[perfis.index(perfil_atual)], nomes[perfis.index(perfil_atual)], cores[perfis.index(perfil_atual)]
        st.markdown(f"#### {ic_a} Entrar como **{nm_a}**")

        usuario = st.text_input("Usuário", placeholder="Digite seu usuário")
        senha   = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🔐 Entrar", use_container_width=True):
            c.execute(
                "SELECT * FROM users WHERE username=? AND password=? AND role=?",
                (usuario, senha, perfil_atual)
            )
            r = c.fetchone()
            if r:
                st.session_state.user = {
                    "username":      r[0],
                    "role":          r[2],
                    "centro_custo":  r[3],
                    "nome_completo": r[4],
                }
                st.rerun()
            else:
                st.error(f"❌ Credenciais inválidas para o perfil **{nm_a}**.")

# ───────────────────────────────────────────────
#  DASHBOARD (compartilhado)
# ───────────────────────────────────────────────
def dashboard(df=None):
    if df is None:
        df = pd.read_sql("SELECT * FROM requests", conn)
    st.markdown('<p class="section-title">📊 Dashboard</p>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("📋 Total",           len(df))
    c2.metric("⏳ Pend. Gerente",   len(df[df["status"]=="Pendente Gerente"]))
    c3.metric("🔵 Pend. RH",        len(df[df["status"]=="Pendente RH"]))
    c4.metric("✅ Concluídos",      len(df[df["status"]=="Concluído"]))
    if not df.empty:
        st.info(f"💰 **Total de comissões na base:** {fmt_brl(df['valor_total'].sum())}")

# ───────────────────────────────────────────────
#  TELA RH
# ───────────────────────────────────────────────
def tela_rh():
    st.title("👩‍💼 Painel RH — Consigaz")
    menu = st.radio("", ["📊 Dashboard","👤 Usuários","📤 Upload","🗃️ Base de Dados"], horizontal=True)
    st.markdown("---")

    if menu == "📊 Dashboard":
        dashboard()

    elif menu == "👤 Usuários":
        tab1, tab2 = st.tabs(["➕ Criar Usuário","📋 Listar Usuários"])

        with tab1:
            st.markdown('<p class="section-title">Novo Usuário</p>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            nome_completo = col1.text_input("Nome Completo")
            usuario       = col2.text_input("Usuário (login)")
            senha         = col1.text_input("Senha", type="password")
            perfil        = col2.selectbox("Perfil", ["gerente","rh","diretor"],
                                           format_func=lambda x: {"gerente":"👨‍💼 Gerente","rh":"👩‍💼 RH","diretor":"🏢 Diretor"}[x])
            centro_custo  = st.selectbox("Centro de Custo", [""] + CENTROS)

            if st.button("✅ Criar Usuário"):
                if not all([nome_completo, usuario, senha]):
                    st.warning("⚠️ Preencha todos os campos.")
                elif len(senha) < 6:
                    st.warning("⚠️ Senha deve ter ao menos 6 caracteres.")
                else:
                    try:
                        c.execute("INSERT INTO users VALUES (?,?,?,?,?,?)",
                                  (usuario, senha, perfil, centro_custo, nome_completo,
                                   datetime.now().strftime("%d/%m/%Y %H:%M")))
                        conn.commit()
                        st.success(f"✅ Usuário **{usuario}** ({perfil}) criado!")
                    except sqlite3.IntegrityError:
                        st.error("❌ Usuário já existe.")

        with tab2:
            df_u = pd.read_sql(
                "SELECT nome_completo AS Nome, username AS Usuário, role AS Perfil, "
                "centro_custo AS [Centro de Custo], criado_em AS [Criado em] "
                "FROM users WHERE username != 'admin'", conn)
            if df_u.empty:
                st.info("Nenhum usuário cadastrado.")
            else:
                st.dataframe(df_u, use_container_width=True, hide_index=True)
                st.markdown("---")
                col_u, col_b = st.columns([3,1])
                sel = col_u.selectbox("Remover usuário", df_u["Usuário"].tolist(), label_visibility="collapsed")
                with col_b:
                    st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                    if st.button("🗑️ Remover"):
                        c.execute("DELETE FROM users WHERE username=?", (sel,))
                        conn.commit()
                        st.success(f"Usuário **{sel}** removido.")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    elif menu == "📤 Upload":
        st.markdown('<p class="section-title">Upload de Planilha</p>', unsafe_allow_html=True)
        file = st.file_uploader("Selecionar arquivo Excel", type=["xlsx"])
        if file:
            try:
                df = pd.read_excel(file)
                st.dataframe(df.head(5), use_container_width=True)
                st.caption(f"Prévia — {len(df)} linhas")
                if st.button("📥 Importar"):
                    now = datetime.now().strftime("%d/%m/%Y %H:%M")
                    for _, row in df.iterrows():
                        c.execute("""INSERT INTO requests
                            (empresa,estabelecimento,localidade,matricula,nome,
                             admissao,cargo,centro_custo,status,atualizado_em)
                            VALUES (?,?,?,?,?,?,?,?,?,?)""",
                            (row.get("Empresa",""), row.get("Estab.",""),
                             row.get("Localidade",""), row.get("Matrícula",""),
                             row.get("Nome",""), row.get("Admissão",""),
                             row.get("Cargo Básico-Descrição",""),
                             row.get("Centro Custo-Descrição",""),
                             "Pendente Gerente", now))
                    conn.commit()
                    st.success(f"✅ {len(df)} registros importados!")
            except Exception as e:
                st.error(f"Erro: {e}")

    elif menu == "🗃️ Base de Dados":
        df = pd.read_sql("SELECT * FROM requests", conn)
        col1,col2,col3 = st.columns(3)
        f_status = col1.selectbox("Status", ["Todos"]+df["status"].dropna().unique().tolist())
        f_centro = col2.selectbox("Centro", ["Todos"]+df["centro_custo"].dropna().unique().tolist())
        f_nome   = col3.text_input("Nome", placeholder="Buscar...")
        if f_status != "Todos": df = df[df["status"]==f_status]
        if f_centro != "Todos": df = df[df["centro_custo"]==f_centro]
        if f_nome: df = df[df["nome"].str.contains(f_nome,case=False,na=False)]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Exportar CSV",
                           df.to_csv(index=False).encode("utf-8-sig"),
                           "comissoes.csv","text/csv")

# ───────────────────────────────────────────────
#  TELA GERENTE
# ───────────────────────────────────────────────
def tela_gerente():
    user = st.session_state.user
    st.title(f"👨‍💼 Gerente — {user['centro_custo']}")
    tab1, tab2 = st.tabs(["📝 Lançar Comissões","📊 Meu Resumo"])

    df = pd.read_sql("SELECT * FROM requests WHERE centro_custo=?", conn,
                     params=(user["centro_custo"],))

    with tab1:
        pendentes = df[df["status"]=="Pendente Gerente"]
        if pendentes.empty:
            st.success("🎉 Todos os registros já foram preenchidos!")
        else:
            st.markdown(f"**{len(pendentes)} funcionário(s) aguardando lançamento**")
            for _, row in pendentes.iterrows():
                st.markdown(f"""<div class="func-card">
                    <strong>{row['nome']}</strong> &nbsp;|&nbsp;
                    Matrícula: <code>{row['matricula']}</code> &nbsp;|&nbsp;
                    Cargo: {row['cargo']}
                </div>""", unsafe_allow_html=True)
                col1,col2,col3 = st.columns([2,2,1])
                valor = col1.number_input("💰 Comissão (R$)", min_value=0.0, format="%.2f", key=f"v_{row['id']}")
                dsr   = col2.number_input("📊 % DSR", min_value=0.0, max_value=100.0, format="%.2f", key=f"d_{row['id']}")
                total = valor + (valor * dsr / 100)
                col3.metric("Total", fmt_brl(total))
                if st.button("💾 Salvar", key=f"s_{row['id']}"):
                    c.execute("""UPDATE requests SET valor_comissao=?,perc_dsr=?,
                        valor_total=?,status='Pendente RH',atualizado_em=? WHERE id=?""",
                        (valor,dsr,total,datetime.now().strftime("%d/%m/%Y %H:%M"),row["id"]))
                    conn.commit()
                    st.success(f"✅ {row['nome']} salvo!")
                    st.rerun()

    with tab2:
        c1,c2,c3 = st.columns(3)
        c1.metric("Total", len(df))
        c2.metric("Pendentes", len(df[df["status"]=="Pendente Gerente"]))
        c3.metric("Enviados ao RH", len(df[df["status"]=="Pendente RH"]))
        if not df.empty:
            st.dataframe(df[["nome","cargo","valor_comissao","perc_dsr","valor_total","status"]],
                         use_container_width=True, hide_index=True)

# ───────────────────────────────────────────────
#  TELA DIRETOR  (somente leitura, visão geral)
# ───────────────────────────────────────────────
def tela_diretor():
    st.title("🏢 Painel Diretor — Visão Executiva")
    menu = st.radio("", ["📊 Visão Geral","📈 Por Centro de Custo","🗃️ Relatório Completo"], horizontal=True)
    st.markdown("---")

    df = pd.read_sql("SELECT * FROM requests", conn)

    if menu == "📊 Visão Geral":
        dashboard(df)
        st.markdown("---")
        if not df.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**💰 Comissões por Status**")
                resumo = df.groupby("status")["valor_total"].sum().reset_index()
                resumo.columns = ["Status","Total (R$)"]
                resumo["Total (R$)"] = resumo["Total (R$)"].apply(fmt_brl)
                st.dataframe(resumo, use_container_width=True, hide_index=True)
            with col2:
                st.markdown("**📍 Total por Centro de Custo**")
                por_centro = df.groupby("centro_custo")["valor_total"].sum().reset_index()
                por_centro.columns = ["Centro","Total (R$)"]
                por_centro["Total (R$)"] = por_centro["Total (R$)"].apply(fmt_brl)
                st.dataframe(por_centro, use_container_width=True, hide_index=True)

    elif menu == "📈 Por Centro de Custo":
        centros = df["centro_custo"].dropna().unique().tolist()
        if not centros:
            st.info("Nenhum dado disponível.")
        else:
            sel = st.selectbox("Centro de Custo", centros)
            df_c = df[df["centro_custo"]==sel]
            c1,c2,c3 = st.columns(3)
            c1.metric("Funcionários",    len(df_c))
            c2.metric("Total Comissões", fmt_brl(df_c["valor_total"].sum()))
            c3.metric("Concluídos",      len(df_c[df_c["status"]=="Concluído"]))
            st.dataframe(df_c[["nome","cargo","valor_comissao","perc_dsr","valor_total","status"]],
                         use_container_width=True, hide_index=True)

    elif menu == "🗃️ Relatório Completo":
        st.markdown('<p class="section-title">Relatório Geral</p>', unsafe_allow_html=True)
        if df.empty:
            st.info("Nenhum dado disponível.")
        else:
            st.metric("💰 Total Geral de Comissões", fmt_brl(df["valor_total"].sum()))
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("⬇️ Exportar CSV",
                               df.to_csv(index=False).encode("utf-8-sig"),
                               "relatorio_comissoes.csv","text/csv")

# ───────────────────────────────────────────────
#  MAIN
# ───────────────────────────────────────────────
def main():
    if "user" not in st.session_state:
        login()
        return

    render_sidebar()
    role = st.session_state.user["role"]

    if role == "rh":
        tela_rh()
    elif role == "gerente":
        tela_gerente()
    elif role == "diretor":
        tela_diretor()
    else:
        st.error("Perfil desconhecido.")

main()
