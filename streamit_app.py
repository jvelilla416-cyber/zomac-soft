import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Control de Planta")

def get_db_connection():
    # CAMBIAMOS EL NOMBRE DE LA DB PARA QUE ARRANQUE LIMPIA
    conn = sqlite3.connect('suiza_v4_tanques.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Tablas básicas
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, precio_base REAL, fedegan INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, tanque TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    c.execute('CREATE TABLE IF NOT EXISTS tanques (nombre TEXT PRIMARY KEY, capacidad REAL, saldo REAL)')
    
    # Lógica segura para los tanques
    for t in ["Tanque 1", "Tanque 2", "Tanque 3"]:
        c.execute('INSERT OR IGNORE INTO tanques VALUES (?, 2000, 0)')
    conn.commit()
    conn.close()

# Intentar inicializar; si hay error, no bloquea la app
try:
    init_db()
except:
    st.error("Error al conectar la base de datos. Por favor reinicie la App.")

# --- SIDEBAR ---
try:
    st.sidebar.image("logo_suiza.png", width=150)
except:
    st.sidebar.write("🥛 **LÁCTEOS SUIZA**")

menu = st.sidebar.selectbox("Módulo:", ["📊 Estado de Tanques", "👥 Proveedores", "🥛 Recibo Leche", "🏭 Producción", "📦 Kardex"])

# --- 1. ESTADO DE TANQUES (VISUAL) ---
if menu == "📊 Estado de Tanques":
    st.header("📊 Disponibilidad de Leche en Tanques")
    conn = get_db_connection()
    df_t = pd.read_sql_query("SELECT * FROM tanques", conn)
    
    cols = st.columns(len(df_t))
    for i, row in df_t.iterrows():
        porcentaje = (row['saldo'] / row['capacidad'])
        cols[i].metric(row['nombre'], f"{row['saldo']} L", f"Capacidad: {row['capacidad']} L")
        cols[i].progress(min(porcentaje, 1.0))

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
            conn.execute('INSERT OR REPLACE INTO proveedores (codigo, nombre, precio_base) VALUES (?,?,?)', (cod, nom, pre))
            conn.commit()
            st.success("Guardado.")

# --- 3. RECIBO DE LECHE (Llenar Tanques) ---
elif menu == "🥛 Recibo Leche":
    st.header("🥛 Ingreso de Leche a Tanques")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    tanques_disp = pd.read_sql_query("SELECT nombre FROM tanques", conn)

    with st.form("f_recibo", clear_on_submit=True):
        p_sel = st.selectbox("Proveedor", provs['codigo'] if not provs.empty else ["Cree un proveedor primero"])
        t_sel = st.selectbox("¿A qué tanque ingresa?", tanques_disp['nombre'])
        lts = st.number_input("Litros a ingresar", min_value=0.0)
        if st.form_submit_button("✅ Registrar"):
            conn.execute('UPDATE tanques SET saldo = saldo + ? WHERE nombre = ?', (lts, t_sel))
            conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, tanque) VALUES (?,?,?,?)', 
                         (str(date.today()), p_sel, lts, t_sel))
            conn.commit()
            st.success(f"Ingresados {lts}L al {t_sel}")

# --- 4. PRODUCCIÓN (Descontar de Tanques) ---
elif menu == "🏭 Producción":
    st.header("🏭 Producción y Transformación")
    conn = get_db_connection()
    tanques_act = pd.read_sql_query("SELECT * FROM tanques WHERE saldo > 0", conn)
    
    with st.form("f_prod", clear_on_submit=True):
        t_uso = st.selectbox("Tanque de Origen", tanques_act['nombre'] if not tanques_act.empty else ["Sin leche"])
        lts_u = st.number_input("Litros a utilizar", min_value=0.0)
        prod = st.selectbox("Producto", ["Queso Costeño", "Queso Pera", "Yogurt", "Cuajada"])
        cant = st.number_input("Cantidad sacada (Kg/Und)", min_value=0.0)
        
        if st.form_submit_button("⚙️ Procesar"):
            conn.execute('UPDATE tanques SET saldo = saldo - ? WHERE nombre = ?', (lts_u, t_uso))
            conn.commit()
            st.success("Producción registrada y tanque actualizado.")
