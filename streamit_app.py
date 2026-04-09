import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Control de Planta")

def get_db_connection():
    conn = sqlite3.connect('suiza_planta_v3.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, precio_base REAL, fedegan INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, tanque TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    c.execute('CREATE TABLE IF NOT EXISTS tanques (nombre TEXT PRIMARY KEY, capacidad REAL, saldo REAL)')
    
    # Inicializar 3 tanques de 2000L si no existen
    for t in ["Tanque 1", "Tanque 2", "Tanque 3"]:
        c.execute('INSERT OR IGNORE INTO tanques VALUES (?, 2000, 0)')
    conn.commit()
    conn.close()

init_db()

# --- SIDEBAR ---
st.sidebar.image("logo_suiza.png", width=150)
st.sidebar.title("🥛 PLANTA SUIZA")
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

# --- 2. RECIBO DE LECHE (Llenar Tanques) ---
elif menu == "🥛 Recibo Leche":
    st.header("🥛 Ingreso de Leche a Tanques")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    tanques_disp = pd.read_sql_query("SELECT nombre FROM tanques", conn)

    with st.form("f_recibo", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Proveedor", provs['codigo'] if not provs.empty else ["Cree un proveedor"])
        t_sel = c2.selectbox("¿A qué tanque ingresa?", tanques_disp['nombre'])
        lts = st.number_input("Litros a ingresar", min_value=0.0)
        
        if st.form_submit_button("✅ Registrar y Llenar Tanque"):
            # Sumar al tanque
            conn.execute('UPDATE tanques SET saldo = saldo + ? WHERE nombre = ?', (lts, t_sel))
            # Guardar recibo
            conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, tanque) VALUES (?,?,?,?)', 
                         (str(date.today()), p_sel, lts, t_sel))
            conn.commit()
            st.success(f"Ingresados {lts}L al {t_sel}")

# --- 3. PRODUCCIÓN (Vaciar Tanques) ---
elif menu == "🏭 Producción":
    st.header("🏭 Transformación de Materia Prima")
    conn = get_db_connection()
    tanques_disp = pd.read_sql_query("SELECT * FROM tanques WHERE saldo > 0", conn)
    
    variedades = ["Queso Costeño", "Yogurt", "Cuajada", "Cheddar", "Parmesano", "Palmita", "Suero Costeño", "Arequipe", "Quesillo", "Queso Pera"]
    
    with st.form("f_prod", clear_on_submit=True):
        c1, c2 = st.columns(2)
        t_uso = c1.selectbox("¿De qué tanque saca la leche?", tanques_disp['nombre'] if not tanques_disp.empty else ["No hay leche"])
        lts_vaca = c2.number_input("Litros a utilizar", min_value=0.0)
        prod = c1.selectbox("Producto a fabricar", variedades)
        pres = c2.selectbox("Presentación", ["125g", "250g", "500g", "1000g", "2500g", "5000g"])
        cant = st.number_input("Cantidad obtenida (Kg/Und)", min_value=0.0)
        
        if st.form_submit_button("⚙️ Procesar Producción"):
            # 1. Restar del tanque
            conn.execute('UPDATE tanques SET saldo = saldo - ? WHERE nombre = ?', (lts_vaca, t_uso))
            # 2. Sumar al Kardex
            c = conn.cursor()
            c.execute('SELECT stock FROM inventario WHERE producto=? AND presentacion=?', (prod, pres))
            res = c.fetchone()
            if res:
                conn.execute('UPDATE inventario SET stock = stock + ? WHERE producto=? AND presentacion=?', (cant, prod, pres))
            else:
                conn.execute('INSERT INTO inventario VALUES (?,?,?)', (prod, pres, cant))
            conn.commit()
            st.success(f"Se utilizaron {lts_vaca}L de {t_uso} para sacar {cant} de {prod}")

elif menu == "📦 Kardex":
    st.header("📦 Inventario Total")
    conn = get_db_connection()
    st.dataframe(pd.read_sql_query("SELECT * FROM inventario", conn), use_container_width=True)
