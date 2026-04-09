import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Sistema Integral")

def get_db_connection():
    # Usamos V9 para que el Kardex y la Producción se sincronicen de verdad
    conn = sqlite3.connect('suiza_v9_maestro.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Proveedores
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, ruta TEXT, 
                  precio_base REAL, ciclo TEXT, forma_pago TEXT, fedegan INTEGER, retencion INTEGER)''')
    # 2. Recibo de Leche
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, tanque TEXT, precio_aplicado REAL)')
    # 3. Producción (Historial de lo elaborado)
    c.execute('CREATE TABLE IF NOT EXISTS produccion_final (id INTEGER PRIMARY KEY, fecha TEXT, litros_usados REAL, producto TEXT, presentacion TEXT, cantidad REAL)')
    # 4. Kardex (Stock actual)
    c.execute('CREATE TABLE IF NOT EXISTS kardex (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    # 5. Tanques
    c.execute('CREATE TABLE IF NOT EXISTS tanques (nombre TEXT PRIMARY KEY, saldo REAL)')
    for t in ["Tanque 1", "Tanque 2", "Tanque 3"]:
        c.execute('INSERT OR IGNORE INTO tanques VALUES (?, 0)', (t,))
    conn.commit()
    conn.close()

init_db()

# --- SIDEBAR ---
st.sidebar.image("logo_suiza.png", width=150)
menu = st.sidebar.selectbox("Menú Principal:", ["📊 Tanques", "👥 Proveedores", "🥛 Recibo", "🏭 Producción", "📦 Kardex (Producto Final)", "💰 Liquidación"])

# --- 1. TANQUES ---
if menu == "📊 Tanques":
    st.header("📊 Estado de Tanques (Capacidad 2000L)")
    conn = get_db_connection()
    df_t = pd.read_sql_query("SELECT * FROM tanques", conn)
    cols = st.columns(3)
    for i, row in df_t.iterrows():
        cols[i].metric(row['nombre'], f"{row['saldo']} L")
        cols[i].progress(min(row['saldo']/2000, 1.0))

# --- 2. PRODUCCIÓN (TRANSFORMACIÓN) ---
elif menu == "🏭 Producción":
    st.header("🏭 Área de Transformación y Elaboración")
    conn = get_db_connection()
    tanques_leche = pd.read_sql_query("SELECT * FROM tanques WHERE saldo > 0", conn)
    
    with st.form("f_prod", clear_on_submit=True):
        c1, c2 = st.columns(2)
        t_uso = c1.selectbox("Tanque de Origen", tanques_leche['nombre'] if not tanques_leche.empty else ["No hay leche"])
        lts_vaca = c2.number_input("Litros a utilizar", min_value=0.0)
        
        st.write("---")
        variedad = c1.selectbox("Producto Elaborado", ["Queso Costeño", "Queso Pera", "Yogurt", "Cuajada", "Arequipe", "Quesillo"])
        pres = c2.selectbox("Presentación", ["125g", "250g", "500g", "1000g", "2500g", "5000g"])
        cant = st.number_input("Cantidad obtenida (Kg/Und)", min_value=0.0)
        
        if st.form_submit_button("⚙️ Finalizar Producción"):
            if t_uso != "No hay leche" and lts_vaca > 0:
                conn = get_db_connection()
                # 1. Restar leche del tanque
                conn.execute('UPDATE tanques SET saldo = saldo - ? WHERE nombre = ?', (lts_vaca, t_uso))
                # 2. Guardar en Historial de Producción
                conn.execute('INSERT INTO produccion_final (fecha, litros_usados, producto, presentacion, cantidad) VALUES (?,?,?,?,?)',
                             (str(date.today()), lts_vaca, variedad, pres, cant))
                # 3. Sumar al Kardex
                c = conn.cursor()
                c.execute('SELECT stock FROM kardex WHERE producto=? AND presentacion=?', (variedad, pres))
                res = c.fetchone()
                if res:
                    conn.execute('UPDATE kardex SET stock = stock + ? WHERE producto=? AND presentacion=?', (cant, variedad, pres))
                else:
                    conn.execute('INSERT INTO kardex VALUES (?,?,?)', (variedad, pres, cant))
                conn.commit()
                st.success(f"Producción Exitosa: {cant} de {variedad} ({pres}) cargados al Kardex.")
            else:
                st.error("No hay leche suficiente o no ingresó litraje.")

    st.subheader("📋 Últimos Productos Elaborados")
    df_his = pd.read_sql_query("SELECT * FROM produccion_final ORDER BY id DESC LIMIT 5", conn)
    st.table(df_his)

# --- 3. KARDEX (PRODUCTO FINAL) ---
elif menu == "📦 Kardex (Producto Final)":
    st.header("📦 Inventario Actual (Kardex)")
    conn = get_db_connection()
    df_k = pd.read_sql_query("SELECT * FROM kardex", conn)
    if not df_k.empty:
        st.dataframe(df_k, use_container_width=True)
        st.info("Este inventario se alimenta automáticamente desde el módulo de Producción.")
    else:
        st.warning("No hay productos en inventario. Debe registrar una producción primero.")

# (Los módulos de Proveedores, Recibo y Liquidación se mantienen igual que la V8)
