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
def get_connection():
    return sqlite3.connect("data.db", check_same_thread=False)

conn = get_connection()
c = conn.cursor()

def init_db():
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT,
        centro_custo TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS requests (
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
        status TEXT
    )
    """)

    conn.commit()

def create_admin():
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES ('admin','admin123','rh','')")
        conn.commit()

init_db()
create_admin()

# ---------------- CENTROS ----------------
CENTROS = sorted(list(set([
"COMERCIAL","COMERCIAL - GESTÃO GRANDES CONTAS",
"COMERCIAL INDUSTRIAL - (Corporativo)",
"COMERCIAL REVENDA - (Corporativo)",
"COMERCIAL REVENDAS",
"GERENTE DE BASE - (Barueri)",
"GERENTE DE BASE - (Cariacica)",
"GERENTE DE BASE - (D. de Caxias)",
"GERENTE DE BASE - (Maua)",
"GERENTE DE BASE - (Paulinia)",
"GERENTE DE BASE - (S. J. Campos)",
"GERENTE DE BASE - (S. Vicente)",
"GERENTE DE BASE - (Sen. Canedo)",
"GERENTE DE BASE (ARAUCARIA)",
"GERENTE DE BASE (ITU)",
"GERENTE DE BASE (JANDAIA DO SUL)",
"GERENTE DE BASE (UBERLÂNDIA)",
"INOVACAO (CORPORATIVO)",
"LICITACOES (CORPORATIVO)",
"POS VENDAS - (Corporativo)",
"POS VENDAS - (Barueri)",
"POS VENDAS - (Canoas)",
"POS VENDAS - (Cariacica)",
"POS VENDAS - (D. de Caxias)",
"POS VENDAS - (Maua)",
"POS VENDAS - (Paulinia)",
"POS VENDAS - (S. J. Campos)",
"POS VENDAS - (S. Vicente)",
"POS VENDAS - (Sen. Canedo)",
"POS VENDAS (ARAUCARIA)",
"POS VENDAS (BRASÍLIA)",
"POS VENDAS (RIB. PRETO)",
"POS VENDAS (UBERLÂNDIA)",
"REVENDA - (Barueri)",
"REVENDA - (Canoas)",
"REVENDA - (Cariacica)",
"REVENDA - (D. de Caxias)",
"REVENDA - (Maua)",
"REVENDA - (Paulinia)",
"REVENDA - (S. J. Campos)",
"REVENDA - (S. Vicente)",
"REVENDA - (Sen. Canedo)",
"REVENDA (ARAUCARIA)",
"REVENDA (BRASÍLIA)",
"REVENDA (RIB. PRETO)",
"REVENDA (UBERLÂNDIA)",
"REVENDA GASBOM - (Barueri)",
"VENDAS - (Barueri)",
"VENDAS - (Canoas)",
"VENDAS - (Cariacica)",
"VENDAS - (D. de Caxias)",
"VENDAS - (Maua)",
"VENDAS - (Paulinia)",
"VENDAS - (Propangas)",
"VENDAS - (S. J. Campos)",
"VENDAS - (S. Vicente)",
"VENDAS - (Sen. Canedo)",
"VENDAS (ARAUCARIA)",
"VENDAS (BETIM)",
"VENDAS (BRASÍLIA)",
"VENDAS (JANDAIA DO SUL)",
"VENDAS (RIB. PRETO)",
"VENDAS (UBERLÂNDIA)"
])))

# ---------------- LOGIN ----------------
def login():
    st.title("🔐 Login")

    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pwd))
        result = c.fetchone()

        if result:
            st.session_state.user = {
                "username": result[0],
                "role": result[2],
                "centro_custo": result[3]
            }
            st.rerun()
        else:
            st.error("Credenciais inválidas")

# ---------------- RH ----------------
def tela_rh():
    st.title("👩‍💼 RH")

    st.subheader("Criar gerente")
    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")
    cc = st.selectbox("Centro de Custo", CENTROS)

    if st.button("Criar usuário"):
        if not u or not p:
            st.warning("Preencha tudo")
            return

        try:
            c.execute("INSERT INTO users VALUES (?,?,?,?)", (u, p, "gerente", cc))
            conn.commit()
            st.success("Criado com sucesso")
        except:
            st.error("Usuário já existe")

    st.divider()

    st.subheader("Upload planilha")
    file = st.file_uploader("Excel", type=["xlsx"])

    if file:
        df = pd.read_excel(file)

        colunas_esperadas = [
            "Empresa","Estab.","Localidade","Matrícula","Nome",
            "Admissão","Cargo Básico-Descrição","Centro Custo-Descrição"
        ]

        if not all(col in df.columns for col in colunas_esperadas):
            st.error("Planilha fora do padrão")
            return

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

    st.divider()

    df = pd.read_sql("SELECT * FROM requests", conn)
    st.dataframe(df)

# ---------------- GERENTE ----------------
def tela_gerente():
    user = st.session_state.user

    df = pd.read_sql(
        "SELECT * FROM requests WHERE centro_custo=?",
        conn,
        params=(user["centro_custo"],)
    )

    st.title("👨‍💼 Gerente")

    if df.empty:
        st.info("Nenhum registro")
        return

    for i, row in df.iterrows():
        st.markdown(f"### {row['nome']}")

        valor = st.number_input("Valor Comissão", key=f"v{i}")
        dsr = st.number_input("% DSR", key=f"d{i}")

        if st.button("Salvar", key=f"s{i}"):
            total = valor + (valor * dsr / 100)

            c.execute("""
            UPDATE requests
            SET valor_comissao=?, perc_dsr=?, valor_total=?, status='Pendente RH'
            WHERE id=?
            """, (valor, dsr, total, row["id"]))

            conn.commit()
            st.success("Atualizado")

# ---------------- MAIN ----------------
def main():
    if "user" not in st.session_state:
        login()
        return

    user = st.session_state.user

    st.sidebar.write(f"👤 {user['username']}")
    st.sidebar.write(f"🔐 {user['role']}")

    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    if user["role"] == "rh":
        tela_rh()
    else:
        tela_gerente()

main()
