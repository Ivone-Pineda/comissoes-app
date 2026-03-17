import streamlit as st
import pandas as pd
import sqlite3

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Comissões Consigaz", layout="wide")

# ------------------ ESTILO ------------------
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

# ------------------ BANCO ------------------
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT,
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
    valor_comissao REAL,
    perc_dsr REAL,
    valor_total REAL,
    status TEXT
)
""")

conn.commit()

# ------------------ CENTROS DE CUSTO ------------------
CENTROS = list(set([
"COMERCIAL",
"COMERCIAL - GESTÃO GRANDES CONTAS",
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
]))

# ------------------ LOGIN ------------------
def login():
    st.title("🔐 Login")

    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()

        if user:
            st.session_state.user = {
                "username": user[0],
                "role": user[2],
                "centro_custo": user[3]
            }
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

# ------------------ RH ------------------
def tela_rh():
    st.title("👩‍💼 RH")

    st.subheader("➕ Criar gerente")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    centro = st.selectbox("Centro de Custo", CENTROS)

    if st.button("Criar usuário"):
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        if c.fetchone():
            st.warning("Usuário já existe")
        else:
            c.execute("INSERT INTO users VALUES (?,?,?,?)",
                      (username, password, "gerente", centro))
            conn.commit()
            st.success("Criado com sucesso!")

    st.divider()

    st.subheader("📤 Upload Planilha")
    file = st.file_uploader("Subir Excel")

    if file:
        df = pd.read_excel(file)

        for _, row in df.iterrows():
            c.execute("""
            INSERT INTO requests (
                empresa, estabelecimento, localidade,
                matricula, nome, admissao, cargo,
                centro_custo, valor_comissao, perc_dsr,
                valor_total, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["Empresa"], row["Estab."], row["Localidade"],
                row["Matrícula"], row["Nome"], row["Admissão"],
                row["Cargo Básico-Descrição"], row["Centro Custo-Descrição"],
                0, 0, 0, "Pendente Gerente"
            ))

        conn.commit()
        st.success("Upload realizado!")

    st.divider()

    df = pd.read_sql("SELECT * FROM requests", conn)
    st.dataframe(df)

# ------------------ GERENTE ------------------
def tela_gerente():
    user = st.session_state.user

    st.title("👨‍💼 Gerente")

    df = pd.read_sql(
        f"SELECT * FROM requests WHERE centro_custo = '{user['centro_custo']}'",
        conn
    )

    for i, row in df.iterrows():
        with st.container():
            st.markdown(f"### {row['nome']}")

            valor = st.number_input(f"Valor Comissão {i}", key=f"v{i}")
            dsr = st.number_input(f"% DSR {i}", key=f"d{i}")

            if st.button(f"Salvar {i}"):
                total = valor + (valor * dsr / 100)

                c.execute("""
                UPDATE requests
                SET valor_comissao=?, perc_dsr=?, valor_total=?, status='Pendente RH'
                WHERE id=?
                """, (valor, dsr, total, row["id"]))

                conn.commit()
                st.success("Salvo!")

# ------------------ MAIN ------------------
def main():
    if "user" in st.session_state and not isinstance(st.session_state.user, dict):
        del st.session_state.user

    if "user" not in st.session_state:
        login()
        return

    user = st.session_state.user

    st.sidebar.write(f"👤 {user['username']}")
    st.sidebar.write(f"🔐 {user['role']}")

    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

    if user["role"] == "rh":
        tela_rh()
    else:
        tela_gerente()

# ------------------ START ------------------
main()
