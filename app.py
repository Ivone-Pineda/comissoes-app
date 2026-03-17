import sqlite3
import hashlib
import pandas as pd
import streamlit as st

DB_PATH = "/tmp/comissoes.db"

st.set_page_config(page_title="Comissões", layout="wide")

# ======================
# CONEXÃO DB
# ======================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_conn()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ======================
# CRIAÇÃO DO BANCO
# ======================
def init_db():
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        username TEXT UNIQUE,
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

    # usuário RH padrão
    if not c.execute("SELECT * FROM users WHERE username='admin'").fetchone():
        c.execute("""
        INSERT INTO users VALUES (NULL, ?, ?, ?, ?, ?)
        """, ("Admin", "admin", hash_password("admin123"), "rh", ""))

    conn.commit()

init_db()

# ======================
# LOGIN
# ======================
if "user" not in st.session_state:
    st.session_state.user = None

def login():
    st.title("Login")

    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        row = conn.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()
        if row and row["password"] == hash_password(pwd):
            st.session_state.user = dict(row)
            st.rerun()
        else:
            st.error("Login inválido")

# ======================
# RH - USUÁRIOS
# ======================
def tela_usuarios():
    st.subheader("Cadastro de Usuários")

    nome = st.text_input("Nome")
    username = st.text_input("Login")
    senha = st.text_input("Senha", type="password")

    perfil = st.selectbox("Perfil", ["gerente", "diretor"])

    centro_custo = st.text_input("Centro de Custo")

    if st.button("Cadastrar"):
        try:
            conn.execute("""
                INSERT INTO users (name, username, password, role, centro_custo)
                VALUES (?, ?, ?, ?, ?)
            """, (nome, username, hash_password(senha), perfil, centro_custo))
            conn.commit()
            st.success("Usuário criado")
        except:
            st.error("Erro: usuário já existe")

# ======================
# RH - UPLOAD
# ======================
def upload_planilha():
    st.subheader("Upload de Planilha")

    file = st.file_uploader("Envie Excel", type=["xlsx"])

    if file:
        df = pd.read_excel(file)
        st.dataframe(df)

        if st.button("Salvar dados"):
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT INTO requests VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    row["Empresa"],
                    row["Estab."],
                    row["Localidade"],
                    row["Matrícula"],
                    row["Nome"],
                    row["Admissão"],
                    row["Cargo Básico-Descrição"],
                    row["Centro Custo-Descrição"],
                    0, 0, 0,
                    "Pendente Gerente"
                ))
            conn.commit()
            st.success("Upload realizado!")

# ======================
# GERENTE
# ======================
def tela_gerente(user):
    st.subheader("Comissões")

    df = pd.read_sql("""
        SELECT * FROM requests
        WHERE centro_custo = ?
        AND status = 'Pendente Gerente'
    """, conn, params=(user["centro_custo"],))

    for _, r in df.iterrows():
        st.write(f"{r['nome']} - {r['matricula']}")

        valor = st.number_input(f"Valor {r['id']}", key=f"v{r['id']}")
        dsr = st.number_input(f"% DSR {r['id']}", key=f"d{r['id']}")

        total = valor + (valor * dsr / 100)

        st.write(f"Total: R$ {total:.2f}")

        if st.button(f"Enviar {r['id']}"):
            conn.execute("""
                UPDATE requests
                SET valor_comissao=?, perc_dsr=?, valor_total=?, status='Pendente Diretor'
                WHERE id=?
            """, (valor, dsr, total, r["id"]))
            conn.commit()
            st.rerun()

        st.divider()

# ======================
# DIRETOR
# ======================
def tela_diretor():
    st.subheader("Aprovação")

    df = pd.read_sql("""
        SELECT * FROM requests
        WHERE status='Pendente Diretor'
    """, conn)

    for _, r in df.iterrows():
        st.write(r["nome"], r["valor_total"])

        if st.button(f"Aprovar {r['id']}"):
            conn.execute("UPDATE requests SET status='Aprovado' WHERE id=?", (r["id"],))
            conn.commit()
            st.rerun()

# ======================
# EXPORTAÇÃO
# ======================
def exportar_totvs():
    st.subheader("Exportar TOTVS")

    df = pd.read_sql("""
        SELECT empresa, estabelecimento, matricula, valor_total
        FROM requests
        WHERE status='Aprovado'
    """, conn)

    csv = df.to_csv(index=False, sep=";").encode("utf-8")

    st.download_button(
        "Baixar CSV",
        data=csv,
        file_name="totvs.csv",
        mime="text/csv"
    )

# ======================
# RH PRINCIPAL
# ======================
def tela_rh():
    aba = st.radio("Menu", ["Upload", "Usuários", "Exportar"])

    if aba == "Upload":
        upload_planilha()
    elif aba == "Usuários":
        tela_usuarios()
    elif aba == "Exportar":
        exportar_totvs()

# ======================
# MAIN
# ======================
def main():
    if not st.session_state.user:
        login()
        return

    user = st.session_state.user

    st.sidebar.write(user["name"])
    st.sidebar.write(user["role"])

    if st.sidebar.button("Sair"):
        st.session_state.user = None
        st.rerun()

    if user["role"] == "rh":
        tela_rh()
    elif user["role"] == "gerente":
        tela_gerente(user)
    elif user["role"] == "diretor":
        tela_diretor()

main()
