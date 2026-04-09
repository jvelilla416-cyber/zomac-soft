import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - PLANTA")

def get_db_connection():
    # Nombre nuevo para que no arrastre errores de las versiones que fallaron
    conn = sqlite3.connect('suiza_v10_funcional.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Proveedores con todo: Finca, Ruta, Fedegan, Retención
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, ruta TEXT, 
                  precio_base REAL, ciclo TEXT, forma_pago TEXT, fedegan INTEGER, retencion INTEGER)''')
    # 2. Recibo de Leche
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, tanque TEXT, precio REAL)')
    # 3. Tanques
    c.execute('CREATE TABLE IF NOT EXISTS tanques (nombre TEXT PRIMARY KEY, saldo REAL)')
    # 4. Kardex y Producción
    c.execute('CREATE TABLE IF NOT EXISTS kardex (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    c.execute('CREATE TABLE IF NOT EXISTS produccion_log (id INTEGER PRIMARY KEY, fecha TEXT, litros REAL, producto TEXT, cantidad REAL)')
    
    for t in ["Tanque 1", "Tanque 2", "Tanque 3"]:
        c.execute('INSERT OR IGNORE INTO tanques VALUES (?, 0)', (t,))
    conn.commit()
    conn.close()

init_db()

# --- INTERFAZ ---
st.sidebar.image("logo_suiza.png", width=150)
menu = st.sidebar.selectbox("Módulo:", ["👥 Proveedores y Rutas", "🥛 Recibo Leche", "🏭 Producción", "📦 Kardex", "💰 Liquidación"])

# --- 1. PROVEEDORES ---
if menu == "👥 Proveedores y Rutas":
    st.header("👥 Gestión de Proveedores")
    with st.form("f_p", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cod = c1.text_input("Código")
        nom = c2.text_input("Nombre Dueño")
        finca = c3.text_input("Nombre Finca")
        ruta = c1.text_input("Ruta (Ej: Molonga)")
        pre = c2.number_input("Precio Base", value=1850.0)
        ciclo = c3.selectbox("Ciclo", ["Semanal", "Quincenal"])
        pago = st.selectbox("Forma de Pago", ["Efectivo", "Transferencia"])
        fede = st.checkbox("Descontar Fedegán")
        rete = st.checkbox("Aplica Retención (Tope 3.6M)")
        if st.form_submit_button("✅ Guardar"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?,?,?,?,?)', 
                         (cod, nom, finca, ruta, pre, ciclo, pago, 1 if fede else 0, 1 if rete else 0))
            conn.commit()
            st.success("Guardado.")
    
    st.subheader("📋 Lista de Proveedores")
    conn = get_db_connection()
    st.dataframe(pd.read_sql_query("SELECT codigo, nombre, finca, ruta FROM proveedores", conn), use_container_width=True)

# --- 2. RECIBO (PRECIO CORREGIBLE) ---
elif menu == "🥛 Recibo Leche":
    st.header("🥛 Ingreso de Leche")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    with st.form("f_r", clear_on_submit=True):
        p_sel = st.selectbox("Proveedor", provs['codigo'] + " - " + provs['finca'] if not provs.empty else [])
        lts = st.number_input("Litros", min_value=0.0)
        tanq = st.selectbox("Tanque", ["Tanque 1", "Tanque 2", "Tanque 3"])
        p_hoy = st.number_input("Precio a pagar hoy", value=1850.0)
        if st.form_submit_button("🚀 Registrar"):
            cod_p = p_sel.split(" - ")[0]
            conn.execute('UPDATE tanques SET saldo = saldo + ? WHERE nombre = ?', (lts, tanq))
            conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, tanque, precio) VALUES (?,?,?,?,?)', (str(date.today()), cod_p, lts, tanq, p_hoy))
            conn.commit()
            st.success("Ingreso exitoso.")

# --- 3. PRODUCCIÓN (SACA DE TANQUE Y METE A KARDEX) ---
elif menu == "🏭 Producción":
    st.header("🏭 Producción")
    conn = get_db_connection()
    tanques = pd.read_sql_query("SELECT * FROM tanques WHERE saldo > 0", conn)
    with st.form("f_prod", clear_on_submit=True):
        t_uso = st.selectbox("Tanque", tanques['nombre'] if not tanques.empty else ["Vacío"])
        lts_u = st.number_input("Litros a usar", min_value=0.0)
        prod = st.selectbox("Producto", ["Queso Costeño", "Queso Pera", "Yogurt", "Cuajada"])
        pres = st.selectbox("Presentación", ["125g", "500g", "1000g", "2500g"])
        cant = st.number_input("Cantidad obtenida (Kg/Und)", min_value=0.0)
        if st.form_submit_button("⚙️ Procesar"):
            conn.execute('UPDATE tanques SET saldo = saldo - ? WHERE nombre = ?', (lts_u, t_uso))
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,?)', (prod, pres, cant))
            conn.execute('INSERT INTO produccion_log (fecha, litros, producto, cantidad) VALUES (?,?,?,?)', (str(date.today()), lts_u, prod, cant))
            conn.commit()
            st.success("Producción cargada al Kardex.")

elif menu == "📦 Kardex":
    st.header("📦 Kardex (Producto Terminado)")
    conn = get_db_connection()
    st.dataframe(pd.read_sql_query("SELECT * FROM kardex", conn), use_container_width=True)

elif menu == "💰 Liquidación":
    st.header("💰 Liquidación")
    conn = get_db_connection()
    # Muestra un resumen rápido de lo que se debe pagar por proveedor
    query = '''SELECT p.codigo, p.nombre, p.finca, SUM(r.litros) as total_lts, AVG(r.precio) as precio_prom, 
               SUM(r.litros * r.precio) as total_valor, p.forma_pago
               FROM recibo_leche r JOIN proveedores p ON r.cod_prov = p.codigo
               GROUP BY p.codigo'''
    df = pd.read_sql_query(query, conn)
    st.dataframe(df, use_container_width=True)
