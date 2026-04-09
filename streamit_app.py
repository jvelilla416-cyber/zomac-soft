import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Planta")

def get_db_connection():
    # CAMBIAMOS EL NOMBRE PARA QUE ARRANQUE LIMPIO Y SIN ERRORES
    conn = sqlite3.connect('suiza_v5_definitivo.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, precio_base REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, tanque TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    c.execute('CREATE TABLE IF NOT EXISTS tanques (nombre TEXT PRIMARY KEY, capacidad REAL, saldo REAL)')
    
    # Inicializar tanques
    for t in ["Tanque 1", "Tanque 2", "Tanque 3"]:
        c.execute('INSERT OR IGNORE INTO tanques VALUES (?, 2000, 0)')
    conn.commit()
    conn.close()

# Inicialización segura
try:
    init_db()
except:
    st.error("Iniciando base de datos... Por favor refresque la página.")

# --- SIDEBAR ---
st.sidebar.image("logo_suiza.png", width=150)
st.sidebar.title("🥛 PLANTA SUIZA")
menu = st.sidebar.selectbox("Módulo:", ["📊 Estado de Tanques", "👥 Proveedores", "🥛 Recibo Leche", "🏭 Producción", "📦 Kardex"])

# --- 1. ESTADO DE TANQUES ---
if menu == "📊 Estado de Tanques":
    st.header("📊 Disponibilidad de Leche en Tanques")
    conn = get_db_connection()
    df_t = pd.read_sql_query("SELECT * FROM tanques", conn)
    
    if not df_t.empty:
        # ARREGLO PARA EL ERROR DE LA FOTO:
        n_cols = len(df_t)
        cols = st.columns(n_cols)
        for i, row in df_t.iterrows():
            porcentaje = (row['saldo'] / row['capacidad'])
            cols[i].metric(row['nombre'], f"{row['saldo']} L", f"Capacidad: {row['capacidad']} L")
            cols[i].progress(min(porcentaje, 1.0))
    else:
        st.info("Inicializando tanques... Refresque la página en un momento.")

# --- 2. PROVEEDORES ---
elif menu == "👥 Proveedores":
    st.header("👥 Registro de Proveedores")
    with st.form("f_p", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cod = c1.text_input("Código")
        nom = c2.text_input("Nombre")
        pre = c1.number_input("Precio Base", value=1850)
        if st.form_submit_button("✅ Guardar"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?)', (cod, nom, pre))
            conn.commit()
            st.success("Guardado correctamente.")

# --- 3. RECIBO LECHE ---
elif menu == "🥛 Recibo Leche":
    st.header("🥛 Ingreso de Leche a Tanques")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    tanques_disp = pd.read_sql_query("SELECT nombre FROM tanques", conn)

    with st.form("f_recibo", clear_on_submit=True):
        p_sel = st.selectbox("Proveedor", provs['codigo'] if not provs.empty else ["Cree un proveedor"])
        t_sel = st.selectbox("Tanque", tanques_disp['nombre'])
        lts = st.number_input("Litros", min_value=0.0)
        if st.form_submit_button("✅ Registrar"):
            conn.execute('UPDATE tanques SET saldo = saldo + ? WHERE nombre = ?', (lts, t_sel))
            conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, tanque) VALUES (?,?,?,?)', 
                         (str(date.today()), p_sel, lts, t_sel))
            conn.commit()
            st.success("Leche ingresada al tanque.")

# --- 4. PRODUCCIÓN ---
elif menu == "🏭 Producción":
    st.header("🏭 Transformación")
    conn = get_db_connection()
    tanques_act = pd.read_sql_query("SELECT * FROM tanques WHERE saldo > 0", conn)
    
    with st.form("f_prod", clear_on_submit=True):
        t_uso = st.selectbox("Tanque Origen", tanques_act['nombre'] if not tanques_act.empty else ["Sin leche"])
        lts_u = st.number_input("Litros a usar", min_value=0.0)
        prod = st.selectbox("Variedad", ["Queso Costeño", "Queso Pera", "Yogurt", "Cuajada"])
        cant = st.number_input("Cantidad obtenida (Kg/Und)", min_value=0.0)
        if st.form_submit_button("⚙️ Procesar"):
            conn.execute('UPDATE tanques SET saldo = saldo - ? WHERE nombre = ?', (lts_u, t_uso))
            conn.commit()
            st.success("Producción lista y descontada del tanque.")

elif menu == "📦 Kardex":
    st.header("📦 Kardex")
    conn = get_db_connection()
    st.dataframe(pd.read_sql_query("SELECT * FROM inventario", conn), use_container_width=True)
