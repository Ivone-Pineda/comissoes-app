import streamlit as st
import pandas as pd
import sqlite3

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Comissões", layout="wide")

# ---------------- ESTILO PREMIUM ----------------
st.markdown("""
<style>
body {
    background-color: #F5F7FA;
}
h1, h2, h3 {
    color: #0A3D62;
}
.stButton>button {
    background-color: #0A3D62;
    color: white;
    border-radius: 10px;
    height: 3em;
    width: 100%;
}
.stTextInput>div>div>input {
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- BANCO ----------------
conn = sqlite3.connect("comissoes.db", check_same_thread=False)
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

# ---------------- USUÁRIOS INICIAIS ----------------
def seed_users():
    users = [
        ("admin","admin123","rh",""),
        ("gerente_barueri","123","gerente","GERENTE DE BASE - (Barueri)"),
        ("gerente_maua","123","gerente","GERENTE DE BASE - (Maua)"),
        ("diretor1","123","diretor","")
    ]
    for u in users:
        c.execute("SELECT * FROM users WHERE username=?", (u[0],))
        if not c.fetchone():
            c.execute("INSERT INTO users VALUES (?,?,?,?)", u)
    conn.commit()

seed_users()

# ---------------- LOGIN ----------------
def login():
    st.image("logo.png", width=180)
    st.markdown("<h1 style='text-align:center'>Plataforma de Comissões</h1>", unsafe_allow_html=True)

    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (user,pwd))
        result = c.fetchone()
        if result:
            st.session_state.user = {
                "username": result[0],
                "role": result[2],
                "centro": result[3]
            }
            st.rerun()
        else:
            st.error("Login inválido")

# ---------------- UPLOAD RH ----------------
def upload_planilha():
    file = st.file_uploader("📤 Subir planilha RH", type=["xlsx","csv"])
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
        st.success("Planilha carregada com sucesso!")

# ---------------- TELA RH ----------------
def tela_rh():
    st.title("👩‍💼 RH")

    upload_planilha()

    df = pd.read_sql("SELECT * FROM requests", conn)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total", len(df))
    col2.metric("Pendentes", len(df[df['status']=="Pendente Gerente"]))
    col3.metric("Aprovados", len(df[df['status']=="Aprovado Diretor"]))

# ---------------- TELA GERENTE ----------------
def tela_gerente(user):
    st.title("👨‍💼 Gerente")

    df = pd.read_sql("SELECT * FROM requests WHERE centro_custo=?", conn, params=(user["centro"],))

    for i, r in df.iterrows():
        with st.container():
            st.markdown(f"### {r['nome']}")
            st.write(f"Matrícula: {r['matricula']}")

            valor = st.number_input(f"Valor Comissão {i}", value=float(r['valor_comissao']))
            dsr = st.number_input(f"% DSR {i}", value=float(r['perc_dsr']))

            total = valor + (valor * dsr/100)

            if st.button(f"Salvar {i}"):
                c.execute("""
                UPDATE requests SET
                valor_comissao=?,
                perc_dsr=?,
                valor_total=?,
                status='Pendente Diretor'
                WHERE id=?
                """, (valor, dsr, total, r['id']))
                conn.commit()
                st.success("Atualizado!")

            st.divider()

# ---------------- TELA DIRETOR ----------------
def tela_diretor():
    st.title("👔 Diretor")

    df = pd.read_sql("SELECT * FROM requests WHERE status='Pendente Diretor'", conn)

    for i, r in df.iterrows():
        st.write(f"{r['nome']} - R$ {r['valor_total']}")

        if st.button(f"Aprovar {i}"):
            c.execute("UPDATE requests SET status='Aprovado Diretor' WHERE id=?", (r['id'],))
            conn.commit()
            st.success("Aprovado")

# ---------------- EXPORTAÇÃO ----------------
def exportar():
    st.title("📥 Exportar TOTVS")

    df = pd.read_sql("SELECT empresa, estabelecimento, matricula, valor_total FROM requests WHERE status='Aprovado Diretor'", conn)

    st.download_button("Download CSV", df.to_csv(index=False), "totvs.csv")

# ---------------- MAIN ----------------
def main():
    if "user" not in st.session_state:
        login()
        return

    user = st.session_state.user

    st.sidebar.image("logo.png", width=150)
    st.sidebar.write(f"👤 {user['username']}")
    st.sidebar.write(f"🔐 {user['role']}")

    if user["role"] == "rh":
        tela_rh()
        exportar()

    elif user["role"] == "gerente":
        tela_gerente(user)

    elif user["role"] == "diretor":
        tela_diretor()

main()
