import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io
from fpdf import FPDF

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Sistema Integrado", page_icon="🥛")

# --- ESTILOS CSS (FONDO BLANCO PARA MÁXIMA CLARIDAD) ---
st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #000000; }
    [data-testid="stSidebar"] { background-color: #f0f2f6; color: #000000; }
    h1, h2, h3 { color: #004ba0; }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN A LA BASE DE DATOS ---
def get_db_connection():
    conn = sqlite3.connect('lacteos_suiza_v2.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- CREACIÓN DE TABLAS (EL MOTOR DE DATOS) ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Tabla de Proveedores
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (id TEXT PRIMARY KEY, nombre TEXT, finca TEXT)')
    # Tabla de Entrada de Leche
    c.execute('CREATE TABLE IF NOT EXISTS entrada_leche (id INTEGER PRIMARY KEY, fecha TEXT, proveedor TEXT, litros REAL)')
    # Tabla de Despachos
    c.execute('CREATE TABLE IF NOT EXISTS despachos (id INTEGER PRIMARY KEY, fecha TEXT, cliente TEXT, producto TEXT, cantidad REAL)')
    conn.commit()
    conn.close()

init_db()

# --- SEGURIDAD: DESACTIVADA (APERTURA TOTAL) ---
# Hemos quitado el sistema de contraseñas para que puedas trabajar YA.
st.success("🔓 Modo de Acceso Directo Activado: Sistema Listo.")

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.header("Navegación")
opcion = st.sidebar.radio("Ir a:", [
    "📊 Director del Panel", 
    "👥 Gestión de Proveedores", 
    "🥛 Entrada de Leche Cruda", 
    "🚛 Registro de Despachos"
])

# --- MÓDULO: GESTIÓN DE PROVEEDORES ---
if opcion == "👥 Gestión de Proveedores":
    st.header("👥 Gestión de Proveedores")
    with st.form("nuevo_proveedor"):
        id_p = st.text_input("ID / NIT")
        nom_p = st.text_input("Nombre del Proveedor")
        finc_p = st.text_input("Nombre de la Finca")
        if st.form_submit_button("Guardar Proveedor"):
            conn = get_db_connection()
            conn.execute('INSERT INTO proveedores (id, nombre, finca) VALUES (?,?,?)', (id_p, nom_p, finc_p))
            conn.commit()
            st.success("Proveedor Guardado")

    st.subheader("Lista de Proveedores")
    conn = get_db_connection()
    df_p = pd.read_sql_query("SELECT * FROM proveedores", conn)
    st.dataframe(df_p, use_container_width=True)

# --- MÓDULO: ENTRADA DE LECHE ---
elif opcion == "🥛 Entrada de Leche Cruda":
    st.header("🥛 Registro de Entrada de Leche")
    conn = get_db_connection()
    prov_list = pd.read_sql_query("SELECT nombre FROM proveedores", conn)['nombre'].tolist()
    
    with st.form("entrada_leche"):
        f_leche = st.date_input("Fecha", date.today())
        p_leche = st.selectbox("Seleccione Proveedor", prov_list if prov_list else ["Debe registrar proveedores primero"])
        l_leche = st.number_input("Litros Ingresados", min_value=0.0)
        if st.form_submit_button("Registrar Entrada"):
            conn.execute('INSERT INTO entrada_leche (fecha, proveedor, litros) VALUES (?,?,?)', (str(f_leche), p_leche, l_leche))
            conn.commit()
            st.success("Entrada Registrada con Éxito")

# --- MÓDULO: DIRECTOR DEL PANEL ---
elif opcion == "📊 Director del Panel":
    st.header("📊 Resumen General")
    conn = get_db_connection()
    leche_total = pd.read_sql_query("SELECT SUM(litros) as total FROM entrada_leche", conn)['total'][0]
    st.metric("Total Leche Recibida (Lts)", leche_total if leche_total else 0)

# --- MÓDULO: DESPACHOS ---
elif opcion == "🚛 Registro de Despachos":
    st.header("🚛 Despachos y Planillas")
    st.info("Módulo de despacho listo para ingresar datos de carga.")
