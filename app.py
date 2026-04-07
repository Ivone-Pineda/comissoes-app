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
/* Importa fonte */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A3D62 0%, #1a5276 100%);
    color: white;
}
section[data-testid="stSidebar"] * { color: white !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.2); }

/* Botões primários */
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

/* Cards de métricas */
div[data-testid="metric-container"] {
    background: #f0f4f8;
    border-left: 4px solid #0A3D62;
    border-radius: 10px;
    padding: 18px 22px;
}

/* Tabela */
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* Inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    border-radius: 6px;
}

/* Títulos de seção */
.section-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #0A3D62;
    margin-bottom: 0.5rem;
    border-bottom: 2px solid #0A3D62;
    padding-bottom: 6px;
}

/* Badge de status */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
}
.badge-pendente  { background:#fff3cd; color:#856404; }
.badge-rh        { background:#cfe2ff; color:#084298; }
.badge-concluido { background:#d1e7dd; color:#0a3622; }

/* Card funcionário */
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
    conn = sqlite3.connect("data.db", check_same_thread=False)
    return conn

conn = get_conn()
c    = conn.cursor()

c.executescript("""
CREATE TABLE IF NOT EXISTS users (
    username    TEXT PRIMARY KEY,
    password    TEXT NOT NULL,
    role        TEXT NOT NULL,
    centro_custo TEXT DEFAULT '',
    nome_completo TEXT DEFAULT '',
    criado_em   TEXT DEFAULT ''
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

# Admin padrão
c.execute("SELECT 1 FROM users WHERE username='admin'")
if not c.fetchone():
    c.execute("INSERT INTO users VALUES ('admin','admin123','rh','','Administrador',?)",
              (datetime.now().strftime("%d/%m/%Y %H:%M"),))
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

# ───────────────────────────────────────────────
#  HELPERS
# ───────────────────────────────────────────────
def badge_status(status):
    cls = {
        "Pendente Gerente": "badge-pendente",
        "Pendente RH":      "badge-rh",
        "Concluído":        "badge-concluido",
    }.get(status, "badge-pendente")
    return f'<span class="badge {cls}">{status}</span>'

def fmt_brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

# ───────────────────────────────────────────────
#  SIDEBAR
# ───────────────────────────────────────────────
def render_sidebar():
    user = st.session_state.user
    with st.sidebar:
        try:
            st.image("logo.png", width=160)
        except:
            st.markdown("## 💼 Consigaz")
        st.markdown("---")
        st.markdown(f"**👤 {user.get('nome_completo') or user['username']}**")
        st.caption(f"Perfil: `{user['role'].upper()}`")
        if user.get("centro_custo"):
            st.caption(f"📍 {user['centro_custo']}")
        st.markdown("---")
        if st.button("🚪 Sair"):
            st.session_state.clear()
            st.rerun()

# ───────────────────────────────────────────────
#  LOGIN
# ───────────────────────────────────────────────
def login():
    col_l, col_c, col_r = st.columns([1, 1.4, 1])
    with col_c:
        try:
            st.image("logo.png", width=180)
        except:
            st.markdown("## 💼 Consigaz")

        st.markdown("### 🔐 Acesso ao Sistema")
        st.markdown("---")

        user = st.text_input("Usuário", placeholder="Digite seu usuário")
        pwd  = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Entrar", use_container_width=True):
            c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pwd))
            r = c.fetchone()
            if r:
                st.session_state.user = {
                    "username":     r[0],
                    "role":         r[2],
                    "centro_custo": r[3],
                    "nome_completo": r[4],
                }
                st.rerun()
            else:
                st.error("❌ Usuário ou senha inválidos.")

# ───────────────────────────────────────────────
#  DASHBOARD
# ───────────────────────────────────────────────
def dashboard(df=None):
    if df is None:
        df = pd.read_sql("SELECT * FROM requests", conn)

    st.markdown('<p class="section-title">📊 Dashboard</p>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Total de Registros",  len(df))
    c2.metric("⏳ Pendente Gerente",    len(df[df["status"] == "Pendente Gerente"]))
    c3.metric("🔵 Pendente RH",         len(df[df["status"] == "Pendente RH"]))
    c4.metric("✅ Concluídos",          len(df[df["status"] == "Concluído"]))

    st.markdown("<br>", unsafe_allow_html=True)
    if not df.empty:
        total_comissoes = df["valor_total"].sum()
        st.info(f"💰 **Total de comissões na base:** {fmt_brl(total_comissoes)}")

# ───────────────────────────────────────────────
#  TELA RH / ADMIN
# ───────────────────────────────────────────────
def tela_rh():
    st.title("👩‍💼 Painel RH — Consigaz")

    menu = st.radio(
        "Navegação",
        ["📊 Dashboard", "👤 Usuários", "📤 Upload", "🗃️ Base de Dados"],
        horizontal=True,
    )
    st.markdown("---")

    # ── DASHBOARD ──────────────────────────────
    if menu == "📊 Dashboard":
        dashboard()

    # ── USUÁRIOS ───────────────────────────────
    elif menu == "👤 Usuários":
        tab1, tab2 = st.tabs(["➕ Criar Usuário", "📋 Listar Usuários"])

        # Criar
        with tab1:
            st.markdown('<p class="section-title">Novo Gerente</p>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                nome_completo = st.text_input("Nome Completo", placeholder="Ex.: João Silva")
                usuario       = st.text_input("Usuário (login)", placeholder="Ex.: joao.silva")
            with col2:
                senha         = st.text_input("Senha", type="password", placeholder="Mínimo 6 caracteres")
                centro_custo  = st.selectbox("Centro de Custo", CENTROS)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✅ Criar Usuário"):
                if not usuario or not senha or not nome_completo:
                    st.warning("⚠️ Preencha todos os campos.")
                elif len(senha) < 6:
                    st.warning("⚠️ A senha deve ter ao menos 6 caracteres.")
                else:
                    try:
                        c.execute(
                            "INSERT INTO users VALUES (?,?,?,?,?,?)",
                            (usuario, senha, "gerente", centro_custo,
                             nome_completo, datetime.now().strftime("%d/%m/%Y %H:%M"))
                        )
                        conn.commit()
                        st.success(f"✅ Usuário **{usuario}** criado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error("❌ Esse nome de usuário já existe.")

        # Listar
        with tab2:
            st.markdown('<p class="section-title">Gerentes Cadastrados</p>', unsafe_allow_html=True)
            df_u = pd.read_sql(
                "SELECT nome_completo AS Nome, username AS Usuário, centro_custo AS [Centro de Custo], criado_em AS [Criado em] FROM users WHERE role='gerente'",
                conn
            )
            if df_u.empty:
                st.info("Nenhum gerente cadastrado ainda.")
            else:
                st.dataframe(df_u, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("**🗑️ Remover Usuário**")
                col_u, col_b = st.columns([3, 1])
                users_list = df_u["Usuário"].tolist()
                sel = col_u.selectbox("Selecione o usuário", users_list, label_visibility="collapsed")
                if col_b.button("Remover"):
                    c.execute("DELETE FROM users WHERE username=?", (sel,))
                    conn.commit()
                    st.success(f"Usuário **{sel}** removido.")
                    st.rerun()

    # ── UPLOAD ─────────────────────────────────
    elif menu == "📤 Upload":
        st.markdown('<p class="section-title">Upload de Planilha</p>', unsafe_allow_html=True)
        st.markdown("Envie um arquivo `.xlsx` com as colunas: **Empresa, Estab., Localidade, Matrícula, Nome, Admissão, Cargo Básico-Descrição, Centro Custo-Descrição**")

        file = st.file_uploader("Selecionar arquivo Excel", type=["xlsx"])
        if file:
            try:
                df = pd.read_excel(file)
                st.dataframe(df.head(5), use_container_width=True)
                st.caption(f"Prévia — {len(df)} linhas encontradas")

                if st.button("📥 Importar para o sistema"):
                    now = datetime.now().strftime("%d/%m/%Y %H:%M")
                    for _, row in df.iterrows():
                        c.execute("""
                        INSERT INTO requests
                            (empresa, estabelecimento, localidade, matricula, nome,
                             admissao, cargo, centro_custo, status, atualizado_em)
                        VALUES (?,?,?,?,?,?,?,?,?,?)
                        """, (
                            row.get("Empresa",""),
                            row.get("Estab.",""),
                            row.get("Localidade",""),
                            row.get("Matrícula",""),
                            row.get("Nome",""),
                            row.get("Admissão",""),
                            row.get("Cargo Básico-Descrição",""),
                            row.get("Centro Custo-Descrição",""),
                            "Pendente Gerente",
                            now,
                        ))
                    conn.commit()
                    st.success(f"✅ {len(df)} registros importados com sucesso!")
            except Exception as e:
                st.error(f"Erro ao processar arquivo: {e}")

    # ── BASE ───────────────────────────────────
    elif menu == "🗃️ Base de Dados":
        st.markdown('<p class="section-title">Base de Dados Completa</p>', unsafe_allow_html=True)
        df = pd.read_sql("SELECT * FROM requests", conn)

        # Filtros
        col_f1, col_f2, col_f3 = st.columns(3)
        status_opts = ["Todos"] + df["status"].dropna().unique().tolist()
        centro_opts = ["Todos"] + df["centro_custo"].dropna().unique().tolist()

        f_status = col_f1.selectbox("Filtrar por Status", status_opts)
        f_centro = col_f2.selectbox("Filtrar por Centro", centro_opts)
        f_nome   = col_f3.text_input("Buscar por Nome", placeholder="Digite parte do nome...")

        if f_status != "Todos":
            df = df[df["status"] == f_status]
        if f_centro != "Todos":
            df = df[df["centro_custo"] == f_centro]
        if f_nome:
            df = df[df["nome"].str.contains(f_nome, case=False, na=False)]

        st.markdown(f"**{len(df)} registros encontrados**")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Export
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Exportar CSV", csv, "comissoes.csv", "text/csv")

# ───────────────────────────────────────────────
#  TELA GERENTE
# ───────────────────────────────────────────────
def tela_gerente():
    user = st.session_state.user
    st.title(f"👨‍💼 Gerente — {user['centro_custo']}")

    tab1, tab2 = st.tabs(["📝 Lançar Comissões", "📊 Meu Resumo"])

    df = pd.read_sql(
        "SELECT * FROM requests WHERE centro_custo=?",
        conn,
        params=(user["centro_custo"],)
    )

    # ── Lançar ─────────────────────────────────
    with tab1:
        pendentes = df[df["status"] == "Pendente Gerente"]
        if pendentes.empty:
            st.success("🎉 Todos os registros já foram preenchidos!")
        else:
            st.markdown(f"**{len(pendentes)} funcionário(s) aguardando lançamento**")
            st.markdown("---")
            for i, row in pendentes.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="func-card">
                        <strong>{row['nome']}</strong> &nbsp;|&nbsp;
                        Matrícula: <code>{row['matricula']}</code> &nbsp;|&nbsp;
                        Cargo: {row['cargo']}
                    </div>
                    """, unsafe_allow_html=True)

                    col1, col2, col3 = st.columns([2, 2, 1])
                    valor = col1.number_input(
                        "💰 Valor Comissão (R$)", min_value=0.0,
                        format="%.2f", key=f"v_{row['id']}"
                    )
                    dsr   = col2.number_input(
                        "📊 % DSR", min_value=0.0, max_value=100.0,
                        format="%.2f", key=f"d_{row['id']}"
                    )
                    total = valor + (valor * dsr / 100)
                    col3.metric("Total", fmt_brl(total))

                    if st.button("💾 Salvar", key=f"s_{row['id']}"):
                        c.execute("""
                            UPDATE requests
                            SET valor_comissao=?, perc_dsr=?, valor_total=?,
                                status='Pendente RH', atualizado_em=?
                            WHERE id=?
                        """, (valor, dsr, total,
                              datetime.now().strftime("%d/%m/%Y %H:%M"),
                              row["id"]))
                        conn.commit()
                        st.success(f"✅ Comissão de **{row['nome']}** salva!")
                        st.rerun()

    # ── Resumo ─────────────────────────────────
    with tab2:
        st.markdown('<p class="section-title">Resumo do meu Centro</p>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total funcionários", len(df))
        c2.metric("Pendentes",          len(df[df["status"] == "Pendente Gerente"]))
        c3.metric("Enviados ao RH",     len(df[df["status"] == "Pendente RH"]))

        if not df.empty:
            st.markdown("---")
            st.dataframe(
                df[["nome","cargo","valor_comissao","perc_dsr","valor_total","status"]],
                use_container_width=True, hide_index=True
            )

# ───────────────────────────────────────────────
#  MAIN
# ───────────────────────────────────────────────
def main():
    if "user" not in st.session_state:
        login()
        return

    render_sidebar()

    if st.session_state.user["role"] == "rh":
        tela_rh()
    else:
        tela_gerente()

main()
