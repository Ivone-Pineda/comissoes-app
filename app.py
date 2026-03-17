import streamlit as st
import pandas as pd
import sqlite3

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Comissões Consigaz", layout="wide")

# ---------------- ESTILO ----------------
st.markdown("""
<style>
.stButton>button {
    background-color: #0A3D62;
    color: white;
    border-radius: 8px;
    height: 3em;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# ---------------- BANCO ----------------
@st.cache_resource
def get_conn():
    return sqlite3.connect("data.db", check_same_thread=False)

conn = get_conn()
c = conn.cursor()

# Criar tabelas
c.execute("""CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT,
    centro_custo TEXT)""")

c.execute("""CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa TEXT,
    estabelecimento TEXT,
    localidade TEXT,
    matricula TEXT,
    nome TEXT,
    admissao TEXT,
    cargo TEXT,
    centro_custo TEXT,
    valor_comissao REAL DEFAULT 0,
    perc_dsr REAL DEFAULT 0,
    valor_total REAL DEFAULT 0,
    status TEXT)""")

conn.commit()

# Criar admin automático
c.execute("SELECT * FROM users WHERE username='admin'")
if not c.fetchone():
    c.execute("INSERT INTO users VALUES ('admin','admin123','rh','')")
    conn.commit()

# ---------------- CENTROS ----------------
CENTROS = ["COMERCIAL","GERENTE DE BASE - (Barueri)","VENDAS - (Barueri)","POS VENDAS - (Barueri)"]

# ---------------- LOGIN ----------------
def login():
    st.image("logo.png", width=200)
    st.title("🔐 Login")

    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pwd))
        r = c.fetchone()

        if r:
            st.session_state.user = {
                "username": r[0],
                "role": r[2],
                "centro_custo": r[3]
            }
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

# ---------------- DASHBOARD ----------------
def dashboard():
    df = pd.read_sql("SELECT * FROM requests", conn)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total", len(df))
    col2.metric("Pendentes", len(df[df["status"]=="Pendente Gerente"]))
    col3.metric("Finalizados", len(df[df["status"]=="Pendente RH"]))

# ---------------- RH ----------------
def tela_rh():
    st.title("👩‍💼 Painel RH")

    menu = st.radio("Menu", ["Dashboard", "Criar Usuário", "Upload", "Base"])

    if menu == "Dashboard":
        dashboard()

    elif menu == "Criar Usuário":
        st.subheader("➕ Novo Gerente")
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        cc = st.selectbox("Centro de Custo", CENTROS)

        if st.button("Criar"):
            try:
                c.execute("INSERT INTO users VALUES (?,?,?,?)", (u, p, "gerente", cc))
                conn.commit()
                st.success("Criado com sucesso")
            except:
                st.error("Usuário já existe")

    elif menu == "Upload":
        st.subheader("📤 Upload Planilha")
        file = st.file_uploader("Excel", type=["xlsx"])

        if file:
            df = pd.read_excel(file)

            for _, row in df.iterrows():
                c.execute("""
                INSERT INTO requests (
                    empresa, estabelecimento, localidade,
                    matricula, nome, admissao, cargo,
                    centro_custo, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["Empresa"], row["Estab."], row["Localidade"],
                    row["Matrícula"], row["Nome"], row["Admissão"],
                    row["Cargo Básico-Descrição"],
                    row["Centro Custo-Descrição"],
                    "Pendente Gerente"
                ))

            conn.commit()
            st.success("Upload concluído")

    elif menu == "Base":
        df = pd.read_sql("SELECT * FROM requests", conn)
        st.dataframe(df)

# ---------------- GERENTE ----------------
def tela_gerente():
    user = st.session_state.user

    st.title(f"👨‍💼 {user['centro_custo']}")

    df = pd.read_sql(
        "SELECT * FROM requests WHERE centro_custo=?",
        conn,
        params=(user["centro_custo"],)
    )

    for i, row in df.iterrows():
        with st.container():
            st.markdown(f"### {row['nome']}")

            col1, col2 = st.columns(2)
            valor = col1.number_input("Valor Comissão", key=f"v{i}")
            dsr = col2.number_input("% DSR", key=f"d{i}")

            if st.button("💾 Salvar", key=f"s{i}"):
                total = valor + (valor * dsr / 100)

                c.execute("""
                UPDATE requests
                SET valor_comissao=?, perc_dsr=?, valor_total=?, status='Pendente RH'
                WHERE id=?
                """, (valor, dsr, total, row["id"]))

                conn.commit()
                st.success("Salvo com sucesso")

            st.divider()

# ---------------- MAIN ----------------
def main():
    if "user" not in st.session_state:
        login()
        return

    user = st.session_state.user

    # Sidebar
    st.sidebar.image("logo.png", width=150)
    st.sidebar.write(f"👤 {user['username']}")
    st.sidebar.write(f"🔐 {user['role']}")

    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

    if user["role"] == "rh":
        tela_rh()
    else:
        tela_gerente()

main()
