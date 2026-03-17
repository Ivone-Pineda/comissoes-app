# app.py
# Plataforma de Gestão de Comissões

import sqlite3
import hashlib
from datetime import datetime, date
import pandas as pd
import streamlit as st

DB_PATH = "/tmp/comissoes.db"
APP_TITLE = "Plataforma de Gestão de Comissões"

st.set_page_config(page_title=APP_TITLE, layout="wide")

# =========================
# DB
# =========================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_conn()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        nome TEXT,
        matricula TEXT,
        centro_custo TEXT,
        valor REAL,
        status TEXT
    )
    """)

    # Admin
    if not c.execute("SELECT * FROM users WHERE username='admin'").fetchone():
        c.execute("INSERT INTO users VALUES (NULL, ?, ?, ?, ?, ?)",
                  ("Admin", "admin", hash_password("admin123"), "rh", ""))

    # Gerente
    if not c.execute("SELECT * FROM users WHERE username='gerente1'").fetchone():
        c.execute("INSERT INTO users VALUES (NULL, ?, ?, ?, ?, ?)",
                  ("Gerente", "gerente1", hash_password("123"), "gerente", "1001"))

    # Diretor
    if not c.execute("SELECT * FROM users WHERE username='diretor1'").fetchone():
        c.execute("INSERT INTO users VALUES (NULL, ?, ?, ?, ?, ?)",
                  ("Diretor", "diretor1", hash_password("123"), "diretor", "1001"))

    conn.commit()

init_db()

# =========================
# LOGIN
# =========================
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
            st.success("Login realizado")
            st.rerun()
        else:
            st.error("Login inválido")

# =========================
# RH
# =========================
def tela_rh():
    st.subheader("RH - Criar Solicitação")

    nome = st.text_input("Nome")
    mat = st.text_input("Matrícula")
    cc = st.text_input("Centro de custo")

    if st.button("Criar"):
        conn.execute("INSERT INTO requests VALUES (NULL, ?, ?, ?, ?, ?)",
                     (nome, mat, cc, 0, "Pendente Gerente"))
        conn.commit()
        st.success("Criado!")

    st.markdown("### Todas solicitações")
    df = pd.read_sql("SELECT * FROM requests", conn)
    st.dataframe(df)

# =========================
# GERENTE
# =========================
def tela_gerente(user):
    st.subheader("Gerente")

    df = pd.read_sql("SELECT * FROM requests WHERE status='Pendente Gerente'", conn)

    for _, r in df.iterrows():
        st.write(r["nome"])

        valor = st.number_input(f"Valor {r['id']}", key=r["id"])

        if st.button(f"Aprovar {r['id']}"):
            conn.execute("UPDATE requests SET valor=?, status='Pendente Diretor' WHERE id=?",
                         (valor, r["id"]))
            conn.commit()
            st.rerun()

# =========================
# DIRETOR
# =========================
def tela_diretor():
    st.subheader("Diretor")

    df = pd.read_sql("SELECT * FROM requests WHERE status='Pendente Diretor'", conn)

    for _, r in df.iterrows():
        st.write(r["nome"], r["valor"])

        if st.button(f"Aprovar Final {r['id']}"):
            conn.execute("UPDATE requests SET status='Aprovado' WHERE id=?", (r["id"],))
            conn.commit()
            st.rerun()

# =========================
# MAIN
# =========================
def main():
    st.title(APP_TITLE)

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