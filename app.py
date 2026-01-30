import streamlit as st
import pandas as pd
import sqlite3

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Bolão Copa 2026", page_icon="⚽", layout="centered")

# --- BANCO DE DADOS ---
def get_connection():
    return sqlite3.connect('bolao_dados.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, pontos INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS jogos (id INTEGER PRIMARY KEY, time1 TEXT, time2 TEXT, gols1 INTEGER, gols2 INTEGER, finalizado INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS palpites (user_id INTEGER, jogo_id INTEGER, palpite1 INTEGER, palpite2 INTEGER, PRIMARY KEY(user_id, jogo_id))')
    c.execute('CREATE TABLE IF NOT EXISTS apostas_especiais (user_id INTEGER, tipo TEXT, palpite TEXT, PRIMARY KEY(user_id, tipo))')
    conn.commit()
    conn.close()

init_db()

# --- LÓGICA DE PONTUAÇÃO ---
def calcular_pontos(p1, p2, r1, r2):
    if p1 == r1 and p2 == r2: return 25  # Placar Exato
    v_p = 1 if p1 > p2 else 2 if p2 > p1 else 0
    v_r = 1 if r1 > r2 else 2 if r2 > r1 else 0
    if v_p == v_r:
        return 15 if (p1 - p2) == (r1 - r2) else 10 # Vendedor+Saldo ou Apenas Vendedor
    return 0

# --- INTERFACE DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("⚽ Bolão Copa 2026")
    tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])
    
    with tab1:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Login"):
            conn = get_connection()
            res = conn.execute('SELECT id FROM usuarios WHERE username=? AND password=?', (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.user_id, st.session_state.username = True, res[0], u
                st.rerun()
            else: st.error("Usuário ou senha incorretos")
            conn.close()

    with tab2:
        new_u = st.text_input("Novo Usuário", key="new_u")
        new_p = st.text_input("Nova Senha", type="password", key="new_p")
        if st.button("Cadastrar"):
            conn = get_connection()
            try:
                conn.execute('INSERT INTO usuarios (username, password) VALUES (?,?)', (new_u, new_p))
                conn.commit()
                st.success("Conta criada! Vá para a aba Entrar.")
            except: st
