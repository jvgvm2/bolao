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
    # Criamos as tabelas garantindo a coluna 'grupo'
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, pontos INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS jogos (id INTEGER PRIMARY KEY, time1 TEXT, time2 TEXT, grupo TEXT, gols1 INTEGER, gols2 INTEGER, finalizado INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS palpites (user_id INTEGER, jogo_id INTEGER, palpite1 INTEGER, palpite2 INTEGER, PRIMARY KEY(user_id, jogo_id))')
    c.execute('CREATE TABLE IF NOT EXISTS apostas_especiais (user_id INTEGER, tipo TEXT, palpite TEXT, PRIMARY KEY(user_id, tipo))')
    conn.commit()
    conn.close()

init_db()

# --- REGRA DE PONTUAÇÃO (3 pts e 1 pt) ---
def calcular_pontos(p1, p2, r1, r2):
    if p1 == r1 and p2 == r2:
        return 3  # Acertou placar exato
    
    v_palp = 1 if p1 > p2 else 2 if p2 > p1 else 0
    v_real = 1 if r1 > r2 else 2 if r2 > r1 else 0
    
    if v_palp == v_real:
        return 1  # Acertou apenas o vencedor ou empate
    return 0

# --- LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("⚽ Bolão Copa 2026")
    t1, t2 = st.tabs(["Login", "Criar Conta"])
    with t1:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            conn = get_connection()
            res = conn.execute('SELECT id, username FROM usuarios WHERE username=? AND password=?', (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.user_id, st.session_state.username = True, res[0], res[1]
                st.rerun()
            else: st.error("Usuário não encontrado.")
            conn.close()
    with t2:
        new_u = st.text_input("Novo Usuário")
        new_p = st.text_input("Nova Senha", type="password")
        if st.button("Cadastrar"):
            conn = get_connection()
            try:
                conn.execute('INSERT INTO usuarios (username, password) VALUES (?,?)', (new_u, new_p))
                conn.commit()
                st.success("Conta criada!")
            except: st.error("Erro: Usuário já existe.")
            conn.close()
else:
    # --- APP ---
    st.sidebar.title(f"Olá, {st.session_state.username}")
    menu = st.sidebar.radio("Navegação", ["Palpites", "Ranking", "Admin"])
    if st.sidebar.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()

    conn = get_connection()

    if menu == "Palpites":
        st.header("🎯 Seus Palpites")
        tab1, tab2 = st.tabs(["Jogos", "Bônus Final"])
        
        with tab1:
            df_g = pd.read_sql_query('SELECT DISTINCT grupo FROM jogos WHERE finalizado=0', conn)
            if df_g.empty:
                st.info("O administrador ainda não subiu os jogos no Painel Admin.")
            else:
                sel_g = st.selectbox("Selecione o Grupo", df_g['grupo'].unique())
                jogos = conn.execute('SELECT * FROM jogos WHERE grupo=? AND finalizado=0', (sel_g,)).fetchall()
                for j in jogos:
                    with st.container():
                        c1, c2, c3, c4 = st.columns([2,1,1,2])
                        c1.write(f"**{j[1]}**")
                        # Busca palpite existente
                        ant = conn.execute('SELECT palpite1, palpite2 FROM palpites WHERE user_id=? AND jogo_id=?', (st.session_state.user_id, j[0])).fetchone()
                        v1, v2 = (ant[0], ant[1]) if ant else (0, 0)
                        p1 = c2.number_input("", 0, 20, v1, key=f"p1_{j[0]}", label_visibility="collapsed")
                        p2 = c3.number_input("", 0, 20, v2, key=f"p2_{j[0]}", label_visibility="collapsed")
                        c4.write(f"**{j[2]}**")
                        if st.button("Salvar", key=f"s_{j[0]}"):
                            conn.execute('INSERT OR REPLACE INTO palpites VALUES (?,?,?,?)', (st.session_state.user_id, j[0], p1, p2))
                            conn.commit()
                            st.toast("Salvo!")

        with tab2:
            st.write("Bônus de 50 pontos!")
            for tipo in ["Campeão", "Artilheiro"]:
                exis = conn.execute('SELECT palpite FROM apostas_especiais WHERE user_id=? AND tipo=?', (st.session_state.user_id, tipo)).fetchone()
                val = exis[0] if exis else ""
                pb = st.text_input(f"Seu {tipo}:", value=val, key=f"b_{tipo}")
                if st.button(f"Salvar {tipo}"):
                    conn.execute('INSERT OR REPLACE INTO apostas_especiais VALUES (?,?,?)', (st.session_state.user_id, tipo, pb))
                    conn.commit()
                    st.success("Salvo!")

    elif menu == "Ranking":
        st.header("🏆 Ranking")
        df_r = pd.read_sql_query('SELECT username as Usuário, pontos as Pontos FROM usuarios ORDER BY pontos DESC', conn)
        if df_r.empty: st.write("Ninguém cadastrado.")
        else: st.table(df_r)

    elif menu == "Admin":
        if st.session_state.username.lower() == "admin":
            st.subheader("⚙️ Painel Admin")
            with st.expander("Importar Jogos (CSV)"):
                st.write("Colunas: time1, time2, grupo")
                f = st.file_uploader("Arquivo", type="csv")
                if f:
                    df_up = pd.read_csv(f)
                    st.dataframe(df_up)
                    if st.button("Importar"):
                        for _, r in df_up.iterrows():
                            conn.execute('INSERT INTO jogos (time1, time2, grupo) VALUES (?,?,?)', (r['time1'], r['time2'], r['grupo']))
                        conn.commit()
                        st.success("Jogos importados!")
                        st.rerun()

            st.divider()
            st.subheader("Encerrar Partidas")
            abertos = conn.execute('SELECT * FROM jogos WHERE finalizado=0').fetchall()
            for j in abertos:
                with st.expander(f"{j[3]} - {j[1]} x {j[2]}"):
                    c1, c2 = st.columns(2)
                    r1 = c1.number_input("Gols Casa", 0, key=f"r1_{j[0]}")
                    r2 = c2.number_input("Gols Fora", 0, key=f"r2_{j[0]}")
                    if st.button("Finalizar", key=f"f_{j[0]}"):
                        palps = conn.execute('SELECT user_id, palpite1, palpite2 FROM palpites WHERE jogo_id=?', (j[0],)).fetchall()
                        for p in palps:
                            pts = calcular_pontos(p[1], p[2], r1, r2)
                            conn.execute('UPDATE usuarios SET pontos = pontos + ? WHERE id = ?', (pts, p[0]))
                        conn.execute('UPDATE jogos SET gols1=?, gols2=?, finalizado=1 WHERE id=?', (r1, r2, j[0]))
                        conn.commit()
                        st.rerun()
        else:
            st.warning("Área restrita ao usuário 'admin'.")
    conn.close()
