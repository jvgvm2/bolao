import streamlit as st
import pandas as pd
import sqlite3

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Bolão Copa 2026", page_icon="⚽", layout="centered")

def get_connection():
    return sqlite3.connect('bolao_dados.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, pontos INTEGER DEFAULT 0)')
    # Coluna 'grupo' incluída para organização
    c.execute('CREATE TABLE IF NOT EXISTS jogos (id INTEGER PRIMARY KEY, time1 TEXT, time2 TEXT, grupo TEXT, gols1 INTEGER, gols2 INTEGER, finalizado INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS palpites (user_id INTEGER, jogo_id INTEGER, palpite1 INTEGER, palpite2 INTEGER, PRIMARY KEY(user_id, jogo_id))')
    c.execute('CREATE TABLE IF NOT EXISTS apostas_especiais (user_id INTEGER, tipo TEXT, palpite TEXT, PRIMARY KEY(user_id, tipo))')
    conn.commit()
    conn.close()

init_db()

# --- NOVA REGRA DE PONTUAÇÃO ---
def calcular_pontos(p1, p2, r1, r2):
    # 1. Acertar o placar exato (consequentemente o vitorioso)
    if p1 == r1 and p2 == r2:
        return 3
    
    # 2. Verificar se acertou apenas o vitorioso/empate
    vencedor_palpite = 1 if p1 > p2 else 2 if p2 > p1 else 0
    vencedor_real = 1 if r1 > r2 else 2 if r2 > r1 else 0
    
    if vencedor_palpite == vencedor_real:
        return 1
        
    return 0

# --- SISTEMA DE ACESSO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("⚽ Bolão Copa 2026")
    t1, t2 = st.tabs(["Entrar", "Criar Conta"])
    with t1:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Login"):
            conn = get_connection()
            res = conn.execute('SELECT id, username FROM usuarios WHERE username=? AND password=?', (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.user_id, st.session_state.username = True, res[0], res[1]
                st.rerun()
            else: st.error("Acesso negado.")
            conn.close()
    with t2:
        new_u = st.text_input("Novo Usuário")
        new_p = st.text_input("Nova Senha", type="password")
        if st.button("Cadastrar"):
            conn = get_connection()
            try:
                conn.execute('INSERT INTO usuarios (username, password) VALUES (?,?)', (new_u, new_p))
                conn.commit()
                st.success("Cadastrado com sucesso!")
            except: st.error("Usuário já existe.")
            conn.close()
else:
    # --- INTERFACE LOGADA ---
    st.sidebar.title(f"Olá, {st.session_state.username}!")
    menu = st.sidebar.radio("Navegação", ["Palpites", "Ranking", "Admin"])
    
    if st.sidebar.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()

    conn = get_connection()

    if menu == "Palpites":
        st.header("🎯 Seus Palpites")
        tab_j, tab_b = st.tabs(["Jogos por Grupo", "Bônus Final"])
        
        with tab_j:
            df_g = pd.read_sql_query('SELECT DISTINCT grupo FROM jogos WHERE finalizado=0', conn)
            if df_g.empty:
                st.info("Aguardando cadastro de jogos.")
            else:
                sel_g = st.selectbox("Escolha o Grupo", df_g['grupo'].tolist())
                jogos = conn.execute('SELECT * FROM jogos WHERE grupo=? AND finalizado=0', (sel_g,)).fetchall()
                for j in jogos:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([2,1,1,2])
                        col1.write(f"**{j[1]}**")
                        
                        # Carrega palpite salvo
                        ant = conn.execute('SELECT palpite1, palpite2 FROM palpites WHERE user_id=? AND jogo_id=?', (st.session_state.user_id, j[0])).fetchone()
                        v1, v2 = (ant[0], ant[1]) if ant else (0, 0)
                        
                        p1 = col2.number_input("", 0, 20, v1, key=f"p1_{j[0]}", label_visibility="collapsed")
                        p2 = col3.number_input("", 0, 20, v2, key=f"p2_{j[0]}", label_visibility="collapsed")
                        col4.write(f"**{j[2]}**")
                        if st.button("Salvar", key=f"s_{j[0]}"):
                            conn.execute('INSERT OR REPLACE INTO palpites VALUES (?,?,?,?)', (
