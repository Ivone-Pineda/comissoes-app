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

div[data-testid="metric-container"] {
    background: #f0f4f8;
    border-left: 4px solid #0A3D62;
    border-radius: 10px;
    padding: 18px 22px;
}

.section-title {
    font-size: 1.3rem; font-weight: 700; color: #0A3D62;
    margin-bottom: 0.5rem;
    border-bottom: 2px solid #0A3D62; padding-bottom: 6px;
}

/* Badges de status */
.badge { display:inline-block; padding:4px 12px; border-radius:20px; font-size:.78rem; font-weight:600; }
.badge-gerente  { background:#fff3cd; color:#856404; }
.badge-diretor  { background:#cfe2ff; color:#084298; }
.badge-aprovado { background:#d1e7dd; color:#0a3622; }
.badge-rejeitado{ background:#f8d7da; color:#842029; }

/* Stepper de fluxo */
.stepper { display:flex; align-items:center; margin: 16px 0 24px 0; }
.step {
    display:flex; flex-direction:column; align-items:center;
    flex:1; position:relative;
}
.step-circle {
    width:36px; height:36px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-weight:700; font-size:.85rem; z-index:1;
}
.step-done   .step-circle { background:#0A3D62; color:white; }
.step-active .step-circle { background:#1a6fa8; color:white; box-shadow:0 0 0 4px rgba(26,111,168,.25); }
.step-idle   .step-circle { background:#dee2e6; color:#666; }
.step-label { font-size:.72rem; margin-top:6px; color:#555; font-weight:500; text-align:center; }
.step-line {
    flex:1; height:3px; margin-top:-18px;
}
.line-done { background:#0A3D62; }
.line-idle { background:#dee2e6; }

.func-card {
    background:white; border:1px solid #dee2e6;
    border-radius:12px; padding:18px 22px;
    margin-bottom:12px; box-shadow:0 1px 4px rgba(0,0,0,.06);
}

/* Botão aprovar / rejeitar */
.btn-success > div > button { background: linear-gradient(135deg,#1e8449,#27ae60) !important; }
.btn-danger  > div > button { background: linear-gradient(135deg,#c0392b,#e74c3c) !important; }
</style>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────────
#  BANCO
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
    obs_diretor      TEXT DEFAULT '',
    atualizado_em    TEXT DEFAULT ''
);
""")
conn.commit()

# Adicionar coluna obs_diretor se não existir (migração)
try:
    c.execute("ALTER TABLE requests ADD COLUMN obs_diretor TEXT DEFAULT ''")
    conn.commit()
except:
    pass

# Usuários padrão
DEFAULTS = [
    ("admin",   "admin123",   "rh",      "",                        "Administrador RH"),
    ("diretor", "diretor123", "diretor", "",                        "Diretor Geral"),
    ("gerente", "gerente123", "gerente", "COMERCIAL",               "Gerente Comercial"),
]
for u, p, r, cc, nm in DEFAULTS:
    c.execute("SELECT 1 FROM users WHERE username=?", (u,))
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?,?,?,?)",
                  (u, p, r, cc, nm, datetime.now().strftime("%d/%m/%Y %H:%M")))
conn.commit()

# ───────────────────────────────────────────────
#  CONSTANTES
# ───────────────────────────────────────────────
CENTROS = [
    "COMERCIAL",
    "GERENTE DE BASE - (Barueri)",
    "VENDAS - (Barueri)",
    "POS VENDAS - (Barueri)",
]

# Mapeamento de status → etapa do fluxo (0-based)
STATUS_STEP = {
    "Pendente Gerente": 0,
    "Pendente Diretor": 1,
    "Aprovado":         2,
    "Rejeitado":        1,
}

def fmt_brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except:
        return "R$ 0,00"

def badge(status):
    m = {
        "Pendente Gerente": ("badge-gerente",  status),
        "Pendente Diretor": ("badge-diretor",  status),
        "Aprovado":         ("badge-aprovado", "✅ Aprovado"),
        "Rejeitado":        ("badge-rejeitado","❌ Rejeitado"),
    }
    cls, txt = m.get(status, ("badge-gerente", status))
    return f'<span class="badge {cls}">{txt}</span>'

def stepper_html(status):
    etapas = ["RH Upload", "Gerente Lança", "Diretor Aprova", "RH Exporta"]
    step   = STATUS_STEP.get(status, 0)
    if status == "Aprovado": step = 3
    html = '<div class="stepper">'
    for i, label in enumerate(etapas):
        cls = "step-done" if i < step else ("step-active" if i == step else "step-idle")
        icon = "✓" if i < step else str(i+1)
        html += f'<div class="step {cls}"><div class="step-circle">{icon}</div><div class="step-label">{label}</div></div>'
        if i < len(etapas)-1:
            line_cls = "line-done" if i < step else "line-idle"
            html += f'<div class="step-line {line_cls}"></div>'
    html += '</div>'
    return html

# ───────────────────────────────────────────────
#  SIDEBAR
# ───────────────────────────────────────────────
def render_sidebar():
    user = st.session_state.user
    icons = {"rh":"👩‍💼","gerente":"👨‍💼","diretor":"🏢"}
    with st.sidebar:
        try: st.image("logo.png", width=160)
        except: st.markdown("## 💼 Consigaz")
        st.markdown("---")
        st.markdown(f"**{icons.get(user['role'],'👤')} {user.get('nome_completo') or user['username']}**")
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
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        try: st.image("logo.png", width=180)
        except: st.markdown("## 💼 Consigaz")
        st.markdown("### Bem-vindo ao Sistema de Comissões")
        st.markdown("Selecione seu perfil:")
        st.markdown("<br>", unsafe_allow_html=True)

        if "perfil_sel" not in st.session_state:
            st.session_state.perfil_sel = "rh"

        p1, p2, p3 = st.columns(3)
        perfis = [("rh","👩‍💼","RH","#1a6fa8"),("gerente","👨‍💼","Gerente","#27ae60"),("diretor","🏢","Diretor","#8e44ad")]
        for col_btn, (p, ic, nm, cor) in zip([p1,p2,p3], perfis):
            sel = st.session_state.perfil_sel == p
            borda = f"3px solid {cor}" if sel else "2px solid #dee2e6"
            bg    = f"rgba({','.join(str(int(cor[i:i+2],16)) for i in (1,3,5))},0.08)" if sel else "white"
            col_btn.markdown(f"""<div style="border:{borda};border-radius:12px;padding:16px;
                text-align:center;background:{bg};">
                <div style="font-size:2rem">{ic}</div>
                <div style="font-weight:600;color:{cor}">{nm}</div></div>""", unsafe_allow_html=True)
            if col_btn.button(f"{nm}", key=f"sel_{p}"):
                st.session_state.perfil_sel = p
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        usuario = st.text_input("Usuário")
        senha   = st.text_input("Senha", type="password")
        if st.button("🔐 Entrar", use_container_width=True):
            c.execute("SELECT * FROM users WHERE username=? AND password=? AND role=?",
                      (usuario, senha, st.session_state.perfil_sel))
            r = c.fetchone()
            if r:
                st.session_state.user = {"username":r[0],"role":r[2],"centro_custo":r[3],"nome_completo":r[4]}
                st.rerun()
            else:
                st.error("❌ Credenciais inválidas para este perfil.")

# ───────────────────────────────────────────────
#  DASHBOARD
# ───────────────────────────────────────────────
def dashboard(df=None):
    if df is None:
        df = pd.read_sql("SELECT * FROM requests", conn)
    st.markdown('<p class="section-title">📊 Dashboard</p>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("📋 Total",          len(df))
    c2.metric("⏳ Pend. Gerente",  len(df[df["status"]=="Pendente Gerente"]))
    c3.metric("🔵 Pend. Diretor",  len(df[df["status"]=="Pendente Diretor"]))
    c4.metric("✅ Aprovados",      len(df[df["status"]=="Aprovado"]))
    c5.metric("❌ Rejeitados",     len(df[df["status"]=="Rejeitado"]))
    if not df.empty:
        aprovados = df[df["status"]=="Aprovado"]["valor_total"].sum()
        st.info(f"💰 **Total aprovado para pagamento:** {fmt_brl(aprovados)}")

# ───────────────────────────────────────────────
#  TELA RH
# ───────────────────────────────────────────────
def tela_rh():
    st.title("👩‍💼 Painel RH")
    menu = st.radio("", ["📊 Dashboard","👤 Usuários","📤 Upload","🗃️ Base / Exportar"], horizontal=True)
    st.markdown("---")

    if menu == "📊 Dashboard":
        dashboard()

    elif menu == "👤 Usuários":
        tab1, tab2 = st.tabs(["➕ Criar","📋 Listar"])
        with tab1:
            col1,col2 = st.columns(2)
            nome = col1.text_input("Nome Completo")
            usr  = col2.text_input("Usuário (login)")
            pwd  = col1.text_input("Senha", type="password")
            role = col2.selectbox("Perfil", ["gerente","rh","diretor"],
                                  format_func=lambda x:{"gerente":"👨‍💼 Gerente","rh":"👩‍💼 RH","diretor":"🏢 Diretor"}[x])
            cc   = st.selectbox("Centro de Custo", [""]+CENTROS)
            if st.button("✅ Criar Usuário"):
                if not all([nome,usr,pwd]):
                    st.warning("Preencha todos os campos.")
                elif len(pwd)<6:
                    st.warning("Senha mínimo 6 caracteres.")
                else:
                    try:
                        c.execute("INSERT INTO users VALUES (?,?,?,?,?,?)",
                                  (usr,pwd,role,cc,nome,datetime.now().strftime("%d/%m/%Y %H:%M")))
                        conn.commit()
                        st.success(f"✅ Usuário **{usr}** criado!")
                    except sqlite3.IntegrityError:
                        st.error("Usuário já existe.")
        with tab2:
            df_u = pd.read_sql("SELECT nome_completo Nome, username Usuário, role Perfil, "
                               "centro_custo [Centro de Custo], criado_em [Criado em] "
                               "FROM users WHERE username!='admin'", conn)
            st.dataframe(df_u, use_container_width=True, hide_index=True)
            if not df_u.empty:
                sel = st.selectbox("Remover", df_u["Usuário"].tolist())
                if st.button("🗑️ Remover Usuário"):
                    c.execute("DELETE FROM users WHERE username=?", (sel,))
                    conn.commit()
                    st.success(f"Usuário **{sel}** removido.")
                    st.rerun()

    elif menu == "📤 Upload":
        st.markdown('<p class="section-title">Upload de Planilha</p>', unsafe_allow_html=True)
        file = st.file_uploader("Arquivo Excel", type=["xlsx"])
        if file:
            try:
                df = pd.read_excel(file)
                st.dataframe(df.head(5), use_container_width=True)
                st.caption(f"{len(df)} linhas encontradas")
                if st.button("📥 Importar"):
                    now = datetime.now().strftime("%d/%m/%Y %H:%M")
                    for _, row in df.iterrows():
                        c.execute("""INSERT INTO requests
                            (empresa,estabelecimento,localidade,matricula,nome,
                             admissao,cargo,centro_custo,status,atualizado_em)
                            VALUES (?,?,?,?,?,?,?,?,?,?)""",
                            (row.get("Empresa",""),row.get("Estab.",""),
                             row.get("Localidade",""),row.get("Matrícula",""),
                             row.get("Nome",""),row.get("Admissão",""),
                             row.get("Cargo Básico-Descrição",""),
                             row.get("Centro Custo-Descrição",""),
                             "Pendente Gerente",now))
                    conn.commit()
                    st.success(f"✅ {len(df)} registros importados!")
            except Exception as e:
                st.error(f"Erro: {e}")

    elif menu == "🗃️ Base / Exportar":
        st.markdown('<p class="section-title">Base de Dados & Exportação</p>', unsafe_allow_html=True)
        df = pd.read_sql("SELECT * FROM requests", conn)

        col1,col2,col3 = st.columns(3)
        f_s = col1.selectbox("Status", ["Todos"]+df["status"].dropna().unique().tolist())
        f_c = col2.selectbox("Centro", ["Todos"]+df["centro_custo"].dropna().unique().tolist())
        f_n = col3.text_input("Nome", placeholder="Buscar...")
        if f_s!="Todos": df = df[df["status"]==f_s]
        if f_c!="Todos": df = df[df["centro_custo"]==f_c]
        if f_n: df = df[df["nome"].str.contains(f_n,case=False,na=False)]

        st.dataframe(df, use_container_width=True, hide_index=True)

        # Exportar apenas aprovados para subir no sistema interno
        df_aprov = pd.read_sql("SELECT * FROM requests WHERE status='Aprovado'", conn)
        st.markdown("---")
        st.markdown("### ⬇️ Exportar para Sistema Interno")
        if df_aprov.empty:
            st.info("Nenhum registro aprovado pelo Diretor ainda.")
        else:
            st.success(f"✅ **{len(df_aprov)} registros aprovados** prontos para exportação.")
            cols_export = ["matricula","nome","cargo","centro_custo",
                           "valor_comissao","perc_dsr","valor_total","atualizado_em"]
            st.dataframe(df_aprov[cols_export], use_container_width=True, hide_index=True)
            st.metric("💰 Total a pagar", fmt_brl(df_aprov["valor_total"].sum()))
            st.download_button(
                "⬇️ Baixar CSV — Aprovados",
                df_aprov[cols_export].to_csv(index=False).encode("utf-8-sig"),
                "comissoes_aprovadas.csv", "text/csv"
            )

# ───────────────────────────────────────────────
#  TELA GERENTE
# ───────────────────────────────────────────────
def tela_gerente():
    user = st.session_state.user
    st.title(f"👨‍💼 Gerente — {user['centro_custo']}")
    tab1, tab2 = st.tabs(["📝 Lançar Comissões","📊 Meu Resumo"])

    df_all = pd.read_sql("SELECT * FROM requests WHERE centro_custo=?", conn,
                         params=(user["centro_custo"],))

    with tab1:
        pendentes = df_all[df_all["status"]=="Pendente Gerente"]
        rejeitados = df_all[df_all["status"]=="Rejeitado"]

        # Rejeitados pelo diretor para revisão
        if not rejeitados.empty:
            st.warning(f"⚠️ **{len(rejeitados)} registro(s) rejeitado(s) pelo Diretor** — revisão necessária.")
            with st.expander("Ver rejeitados"):
                for _, row in rejeitados.iterrows():
                    st.markdown(f"""<div class="func-card" style="border-left:4px solid #e74c3c">
                        <strong>{row['nome']}</strong> — Obs. Diretor: <em>{row['obs_diretor'] or 'Sem observação'}</em>
                    </div>""", unsafe_allow_html=True)
                    col1,col2,col3 = st.columns([2,2,1])
                    valor = col1.number_input("💰 Novo Valor (R$)", min_value=0.0, format="%.2f", key=f"rv_{row['id']}")
                    dsr   = col2.number_input("📊 % DSR",           min_value=0.0, format="%.2f", key=f"rd_{row['id']}")
                    total = valor + (valor * dsr / 100)
                    col3.metric("Total", fmt_brl(total))
                    if st.button("🔄 Reenviar ao Diretor", key=f"rr_{row['id']}"):
                        c.execute("""UPDATE requests SET valor_comissao=?,perc_dsr=?,valor_total=?,
                            status='Pendente Diretor',obs_diretor='',atualizado_em=? WHERE id=?""",
                            (valor,dsr,total,datetime.now().strftime("%d/%m/%Y %H:%M"),row["id"]))
                        conn.commit()
                        st.success(f"✅ {row['nome']} reenviado ao Diretor!")
                        st.rerun()

        if pendentes.empty:
            st.success("🎉 Todos os registros preenchidos e enviados ao Diretor!")
        else:
            st.markdown(f"**{len(pendentes)} funcionário(s) aguardando lançamento**")
            for _, row in pendentes.iterrows():
                st.markdown(stepper_html(row["status"]), unsafe_allow_html=True)
                st.markdown(f"""<div class="func-card">
                    <strong>{row['nome']}</strong> &nbsp;|&nbsp;
                    Matrícula: <code>{row['matricula']}</code> &nbsp;|&nbsp;
                    Cargo: {row['cargo']}
                </div>""", unsafe_allow_html=True)
                col1,col2,col3 = st.columns([2,2,1])
                valor = col1.number_input("💰 Comissão (R$)", min_value=0.0, format="%.2f", key=f"v_{row['id']}")
                dsr   = col2.number_input("📊 % DSR",         min_value=0.0, format="%.2f", key=f"d_{row['id']}")
                total = valor + (valor * dsr / 100)
                col3.metric("Total", fmt_brl(total))
                if st.button("📤 Enviar ao Diretor", key=f"s_{row['id']}"):
                    c.execute("""UPDATE requests SET valor_comissao=?,perc_dsr=?,valor_total=?,
                        status='Pendente Diretor',atualizado_em=? WHERE id=?""",
                        (valor,dsr,total,datetime.now().strftime("%d/%m/%Y %H:%M"),row["id"]))
                    conn.commit()
                    st.success(f"✅ {row['nome']} enviado ao Diretor!")
                    st.rerun()

    with tab2:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total",           len(df_all))
        c2.metric("Pend. Lançamento",len(df_all[df_all["status"]=="Pendente Gerente"]))
        c3.metric("Pend. Diretor",   len(df_all[df_all["status"]=="Pendente Diretor"]))
        c4.metric("Aprovados",       len(df_all[df_all["status"]=="Aprovado"]))
        st.markdown("---")
        st.dataframe(df_all[["nome","cargo","valor_comissao","perc_dsr","valor_total","status"]],
                     use_container_width=True, hide_index=True)

# ───────────────────────────────────────────────
#  TELA DIRETOR
# ───────────────────────────────────────────────
def tela_diretor():
    st.title("🏢 Painel Diretor")
    menu = st.radio("", ["✅ Aprovar Comissões","📊 Visão Geral","📈 Por Centro"], horizontal=True)
    st.markdown("---")

    if menu == "✅ Aprovar Comissões":
        st.markdown('<p class="section-title">Comissões Aguardando Aprovação</p>', unsafe_allow_html=True)
        df = pd.read_sql("SELECT * FROM requests WHERE status='Pendente Diretor'", conn)

        if df.empty:
            st.success("🎉 Nenhuma comissão pendente de aprovação!")
        else:
            st.markdown(f"**{len(df)} registro(s) para analisar**")

            for _, row in df.iterrows():
                st.markdown(stepper_html(row["status"]), unsafe_allow_html=True)
                st.markdown(f"""<div class="func-card">
                    <strong>{row['nome']}</strong> &nbsp;|&nbsp;
                    <code>{row['matricula']}</code> &nbsp;|&nbsp;
                    {row['cargo']} &nbsp;|&nbsp; 📍 {row['centro_custo']}
                    <br><br>
                    💰 Comissão: <strong>{fmt_brl(row['valor_comissao'])}</strong> &nbsp;|&nbsp;
                    DSR: <strong>{row['perc_dsr']}%</strong> &nbsp;|&nbsp;
                    Total: <strong>{fmt_brl(row['valor_total'])}</strong>
                </div>""", unsafe_allow_html=True)

                obs = st.text_input("Observação (opcional)", key=f"obs_{row['id']}",
                                    placeholder="Ex.: Valor fora do padrão, revisar...")
                col_a, col_r = st.columns(2)
                with col_a:
                    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                    if st.button("✅ Aprovar", key=f"apr_{row['id']}"):
                        c.execute("""UPDATE requests SET status='Aprovado',obs_diretor=?,
                            atualizado_em=? WHERE id=?""",
                            (obs, datetime.now().strftime("%d/%m/%Y %H:%M"), row["id"]))
                        conn.commit()
                        st.success(f"✅ {row['nome']} aprovado!")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with col_r:
                    st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                    if st.button("❌ Rejeitar", key=f"rej_{row['id']}"):
                        if not obs:
                            st.warning("Informe uma observação ao rejeitar.")
                        else:
                            c.execute("""UPDATE requests SET status='Rejeitado',obs_diretor=?,
                                atualizado_em=? WHERE id=?""",
                                (obs, datetime.now().strftime("%d/%m/%Y %H:%M"), row["id"]))
                            conn.commit()
                            st.warning(f"❌ {row['nome']} rejeitado. Gerente será notificado.")
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown("---")

    elif menu == "📊 Visão Geral":
        df = pd.read_sql("SELECT * FROM requests", conn)
        dashboard(df)
        if not df.empty:
            col1,col2 = st.columns(2)
            with col1:
                st.markdown("**💰 Total por Status**")
                r = df.groupby("status")["valor_total"].sum().reset_index()
                r.columns=["Status","Total"]; r["Total"]=r["Total"].apply(fmt_brl)
                st.dataframe(r, use_container_width=True, hide_index=True)
            with col2:
                st.markdown("**📍 Total por Centro de Custo**")
                r2 = df.groupby("centro_custo")["valor_total"].sum().reset_index()
                r2.columns=["Centro","Total"]; r2["Total"]=r2["Total"].apply(fmt_brl)
                st.dataframe(r2, use_container_width=True, hide_index=True)

    elif menu == "📈 Por Centro":
        df = pd.read_sql("SELECT * FROM requests", conn)
        centros = df["centro_custo"].dropna().unique().tolist()
        if not centros:
            st.info("Nenhum dado disponível.")
        else:
            sel = st.selectbox("Centro de Custo", centros)
            df_c = df[df["centro_custo"]==sel]
            c1,c2,c3 = st.columns(3)
            c1.metric("Funcionários",   len(df_c))
            c2.metric("Total Comissões",fmt_brl(df_c["valor_total"].sum()))
            c3.metric("Aprovados",      len(df_c[df_c["status"]=="Aprovado"]))
            st.dataframe(df_c[["nome","cargo","valor_comissao","perc_dsr","valor_total","status","obs_diretor"]],
                         use_container_width=True, hide_index=True)

# ───────────────────────────────────────────────
#  MAIN
# ───────────────────────────────────────────────
def main():
    if "user" not in st.session_state:
        login()
        return
    render_sidebar()
    role = st.session_state.user["role"]
    if   role == "rh":      tela_rh()
    elif role == "gerente": tela_gerente()
    elif role == "diretor": tela_diretor()
    else: st.error("Perfil desconhecido.")

main()
