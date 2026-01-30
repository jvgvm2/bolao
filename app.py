import streamlit as st
import pandas as pd
import sqlite3

# --- CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Bolão Copa 2026", page_icon="⚽", layout="centered")

# CSS para temática de futebol
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #008751; color: white; }
    .stTextInput>div>div>input { border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def get_connection():
    conn = sqlite3.connect('bolao_dados.db', check_same_thread=False)
    return conn

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
    if p1 == r1 and p2 == r2: return 25
    v_p = 1 if p1 > p2 else 2 if p2 > p1 else 0
    v_r = 1 if r1 > r2 else 2 if r2 > r1 else 0
    if v_p == v_r:
        return 15 if (p1 - p2) == (r1 - r2) else 10
    return 0

# --- SISTEMA DE LOGIN ---
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
            except: st.error("Este nome já existe.")
            conn.close()
else:
    # --- APP PRINCIPAL ---
    st.sidebar.title(f"Olá, {st.session_state.username}!")
    menu = st.sidebar.radio("Menu", ["Palpites", "Ranking", "Admin"])
    if st.sidebar.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()

    conn = get_connection()

    if menu == "Palpites":
        st.header("Faça seus Jogos")
        t_jogos, t_bonus = st.tabs(["Partidas", "Bônus Final"])
        
        with t_jogos:
            jogos = conn.execute('SELECT * FROM jogos WHERE finalizado=0').fetchall()
            for j in jogos:
                with st.container():
                    col1, col2, col3, col4 = st.columns([2,1,1,2])
                    col1.write(f"**{j[1]}**")
                    p1 = col2.number_input("", min_value=0, step=1, key=f"j1_{j[0]}", label_visibility="collapsed")
                    p2 = col3.number_input("", min_value=0, step=1, key=f"j2_{j[0]}", label_visibility="collapsed")
                    col4.write(f"**{j[2]}**")
                    if st.button("Salvar Placar", key=f"btn_{j[0]}"):
                        conn.execute('INSERT OR REPLACE INTO palpites VALUES (?,?,?,?)', (st.session_state.user_id, j[0], p1, p2))
                        conn.commit()
                        st.toast("Salvo!")

        with t_bonus:
            for tipo in ["Campeão", "Artilheiro"]:
                existente = conn.execute('SELECT palpite FROM apostas_especiais WHERE user_id=? AND tipo=?', (st.session_state.user_id, tipo)).fetchone()
                val = existente[0] if existente else ""
                p_bonus = st.text_input(f"Seu palpite para {tipo}:", value=val, key=f"b_{tipo}")
                if st.button(f"Salvar {tipo}"):
                    conn.execute('INSERT OR REPLACE INTO apostas_especiais VALUES (?,?,?)', (st.session_state.user_id, tipo, p_bonus))
                    conn.commit()
                    st.success("Bônus salvo!")

    elif menu == "Ranking":
        st.header("🏆 Classificação")
        df = pd.read_sql_query('SELECT username as Usuário, pontos as Pontos FROM usuarios ORDER BY pontos DESC', conn)
        st.dataframe(df, use_container_width=True)
        st.download_button("Exportar Excel", df.to_csv(index=False).encode('utf-8'), "ranking.csv")

    elif menu == "Admin":
        if st.session_state.username == "admin": # Defina seu user como 'admin' no cadastro
            st.subheader("Gerenciar Jogos")
            with st.expander("Adicionar Novo Jogo"):
                t1, t2 = st.text_input("Time Casa"), st.text_input("Time Fora")
                if st.button("Criar Jogo"):
                    conn.execute('INSERT INTO jogos (time1, time2) VALUES (?,?)', (t1, t2))
                    conn.commit()
            
            st.subheader("Encerrar Jogo e Pontuar")
            abertos = conn.execute('SELECT * FROM jogos WHERE finalizado=0').fetchall()
            for j in abertos:
                c1, c2, c3 = st.columns([2,1,1])
                r1 = c2.number_input("Gols Casa", min_value=0, key=f"r1_{j[0]}")
                r2 = c3.number_input("Gols Fora", min_value=0, key=f"r2_{j[0]}")
                if c1.button(f"Finalizar {j[1]}x{j[2]}"):
                    palps = conn.execute('SELECT user_id, palpite1, palpite2 FROM palpites WHERE jogo_id=?', (j[0],)).fetchall()
                    for p in palps:
                        pts = calcular_pontos(p[1], p[2], r1, r2)
                        conn.execute('UPDATE usuarios SET pontos = pontos + ? WHERE id = ?', (pts, p[0]))
                    conn.execute('UPDATE jogos SET gols1=?, gols2=?, finalizado=1 WHERE id=?', (r1, r2, j[0]))
                    conn.commit()
                    st.rerun()
            
            st.divider()
            st.subheader("Validar Bônus (50 pts)")
            tipo_b = st.selectbox("Tipo", ["Campeão", "Artilheiro"])
            resp = st.text_input("Resposta Oficial")
            if st.button("Distribuir Pontos Bônus"):
                venc = conn.execute('SELECT user_id FROM apostas_especiais WHERE tipo=? AND UPPER(palpite)=UPPER(?)', (tipo_b, resp)).fetchall()
                for v in venc:
                    conn.execute('UPDATE usuarios SET pontos = pontos + 50 WHERE id = ?', (v[0],))
                conn.commit()
                st.success(f"Premiados {len(venc)} usuários!")
        else:
            st.warning("Acesso restrito ao administrador.")
    conn.close()
