import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Control Total")

def get_db_connection():
    # Usamos la V7 para forzar una base de datos limpia y sin errores de tabla
    conn = sqlite3.connect('suiza_v7_final.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Proveedores con Ruta y Finca
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, ruta TEXT, 
                  precio_base REAL, ciclo TEXT, fedegan INTEGER, retencion INTEGER)''')
    # 2. Recibo de Leche
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, tanque TEXT, precio REAL)')
    # 3. Tanques de 2000L
    c.execute('CREATE TABLE IF NOT EXISTS tanques (nombre TEXT PRIMARY KEY, saldo REAL)')
    # 4. Inventario y Mermas
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    c.execute('CREATE TABLE IF NOT EXISTS mermas (id INTEGER PRIMARY KEY, fecha TEXT, cantidad REAL, motivo TEXT)')
    
    # Inicializar tanques de forma segura
    for t in ["Tanque 1", "Tanque 2", "Tanque 3"]:
        c.execute('INSERT OR IGNORE INTO tanques VALUES (?, 0)', (t,))
    conn.commit()
    conn.close()

# Inicialización a prueba de fallos
try:
    init_db()
except Exception as e:
    st.error(f"Iniciando sistema... Por favor refresque la página. ({e})")

# --- INTERFAZ ---
st.sidebar.image("logo_suiza.png", width=150)
menu = st.sidebar.selectbox("Módulo:", ["📊 Tanques", "👥 Proveedores/Rutas", "🥛 Recibo", "📈 Reporte Diario", "🏭 Producción", "🍽️ Tajado", "📦 Kardex"])

# --- 1. TANQUES (VISUAL) ---
if menu == "📊 Tanques":
    st.header("📊 Disponibilidad en Tanques (Capacidad 2000L)")
    conn = get_db_connection()
    df_t = pd.read_sql_query("SELECT * FROM tanques", conn)
    cols = st.columns(3)
    for i, row in df_t.iterrows():
        porc = row['saldo'] / 2000
        cols[i].metric(row['nombre'], f"{row['saldo']} L", "Capacidad 2000L")
        cols[i].progress(min(porc, 1.0))

# --- 2. PROVEEDORES (NUEVA RUTA Y FINCA) ---
elif menu == "👥 Proveedores/Rutas":
    st.header("👥 Gestión de Proveedores y Rutas")
    with st.form("f_p", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cod = c1.text_input("Código")
        nom = c2.text_input("Nombre Dueño")
        finca = c3.text_input("Nombre Finca")
        ruta = c1.text_input("Ruta (Ej: Molonga)")
        pre = c2.number_input("Precio Base", value=1850)
        ciclo = c3.selectbox("Ciclo", ["Semanal", "Quincenal"])
        fede = st.checkbox("Descuento Fedegán")
        rete = st.checkbox("Aplica Retención (Tope $3.666.000)")
        if st.form_submit_button("✅ Guardar"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?,?,?,?)', (cod, nom, finca, ruta, pre, ciclo, 1 if fede else 0, 1 if rete else 0))
            conn.commit()
            st.success("Guardado con éxito.")
    
    st.subheader("📋 Lista de Proveedores")
    conn = get_db_connection()
    st.dataframe(pd.read_sql_query("SELECT codigo, nombre, finca, ruta FROM proveedores", conn), use_container_width=True)

# --- 3. RECIBO (POR CÓDIGO) ---
elif menu == "🥛 Recibo":
    st.header("🥛 Ingreso de Leche")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    with st.form("f_r", clear_on_submit=True):
        p_sel = st.selectbox("Proveedor", provs['codigo'] + " - " + provs['finca'] if not provs.empty else [])
        lts = st.number_input("Litros", min_value=0.0)
        tanq = st.selectbox("Tanque", ["Tanque 1", "Tanque 2", "Tanque 3"])
        if st.form_submit_button("🚀 Registrar"):
            cod_p = p_sel.split(" - ")[0]
            conn.execute('UPDATE tanques SET saldo = saldo + ? WHERE nombre = ?', (lts, tanq))
            conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, tanque) VALUES (?,?,?,?)', (str(date.today()), cod_p, lts, tanq))
            conn.commit()
            st.success("Ingreso registrado.")

# --- 4. REPORTE DIARIO ---
elif menu == "📈 Reporte Diario":
    st.header(f"📈 Reporte de Hoy {date.today()}")
    conn = get_db_connection()
    query = "SELECT r.fecha, p.ruta, p.finca, r.litros FROM recibo_leche r JOIN proveedores p ON r.cod_prov = p.codigo WHERE r.fecha = ?"
    df = pd.read_sql_query(query, conn, params=(str(date.today()),))
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.metric("TOTAL LITROS DÍA", f"{df['litros'].sum()} L")
    else:
        st.info("No hay leche registrada hoy.")

# --- 5. TAJADO (CON MERMA 200G) ---
elif menu == "🍽️ Tajado":
    st.header("🍽️ Proceso de Tajado")
    with st.form("f_t"):
        kg = st.number_input("Kilos de bloque a tajar", min_value=0.0)
        prod = st.selectbox("Variedad", ["Queso Tajado", "Cuajada Tajada"])
        pres = st.selectbox("Presentación", ["125g", "250g", "500g", "1000g", "2500g"])
        merma = (kg / 2.5) * 0.200 if kg > 0 else 0
        if st.form_submit_button("⚙️ Tajar"):
            conn = get_db_connection()
            conn.execute('INSERT INTO mermas (fecha, cantidad, motivo) VALUES (?,?,"Tajado")', (str(date.today()), merma))
            conn.execute('INSERT OR REPLACE INTO inventario (producto, presentacion, stock) VALUES (?,?,?)', (prod, pres, kg - merma))
            conn.commit()
            st.warning(f"Merma: {merma:.2f} kg enviada a Cuarto Frío.")
            st.success("Listo.")

elif menu == "📦 Kardex":
    st.header("📦 Kardex")
    conn = get_db_connection()
    st.dataframe(pd.read_sql_query("SELECT * FROM inventario", conn), use_container_width=True)
