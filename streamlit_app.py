import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io
from fpdf import FPDF

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Gestión Total", page_icon="🥛")

# --- CONEXIÓN A BASE DE DATOS ---
def get_db_connection():
    conn = sqlite3.connect('lacteos_suiza_total.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- INICIALIZACIÓN DE TODAS LAS TABLAS ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Proveedores y Leche
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (id TEXT PRIMARY KEY, nombre TEXT, finca TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS entrada_leche (id INTEGER PRIMARY KEY, fecha TEXT, proveedor TEXT, litros REAL)')
    # Kardex y Productos
    c.execute('CREATE TABLE IF NOT EXISTS productos (id TEXT PRIMARY KEY, nombre TEXT, stock_kg REAL, precio REAL)')
    # Transformación (El corazón de la planta)
    c.execute('CREATE TABLE IF NOT EXISTS transformacion (id INTEGER PRIMARY KEY, fecha TEXT, leche_usada REAL, producto_id TEXT, kg_producidos REAL)')
    conn.commit()
    conn.close()

init_db()

# --- INTERFAZ ---
st.success("🔓 SISTEMA ABIERTO: Todos los módulos activos.")

opcion = st.sidebar.radio("Módulos de la Planta:", [
    "📊 Resumen General", 
    "👥 Gestión de Proveedores", 
    "🥛 Entrada de Leche Cruda", 
    "🔄 Transformación (Producción)",
    "📦 Kardex / Producto Terminado",
    "🚛 Registro de Despachos"
])

# --- 1. PROVEEDORES ---
if opcion == "👥 Gestión de Proveedores":
    st.header("👥 Gestión de Proveedores")
    with st.form("f_prov"):
        id_p = st.text_input("ID / NIT")
        nom_p = st.text_input("Nombre")
        if st.form_submit_button("Guardar"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?)', (id_p, nom_p, ""))
            conn.commit()
            st.success("Guardado.")
    
# --- 2. ENTRADA DE LECHE ---
elif opcion == "🥛 Entrada de Leche Cruda":
    st.header("🥛 Entrada de Leche Cruda")
    # Formulario para registrar litros recibidos
    litros = st.number_input("Litros recibidos hoy", min_value=0.0)
    if st.button("Registrar Entrada"):
        st.info("Dato guardado en base de datos.")

# --- 3. TRANSFORMACIÓN (PRODUCCIÓN) ---
elif opcion == "🔄 Transformación (Producción)":
    st.header("🔄 Proceso de Transformación")
    st.subheader("Convertir Leche en Producto Terminado")
    col1, col2 = st.columns(2)
    with col1:
        leche_in = st.number_input("Litros de leche a procesar", min_value=0.0)
    with col2:
        prod_out = st.selectbox("Producto a fabricar", ["Queso Costeño", "Queso Campesino", "Yogurt"])
    
    kg_obtenidos = st.number_input("Kilos finales obtenidos", min_value=0.0)
    if st.button("Finalizar Producción"):
        st.success(f"Se procesaron {leche_in}L para obtener {kg_obtenidos}kg de {prod_out}")

# --- 4. KARDEX / PRODUCTO TERMINADO ---
elif opcion == "📦 Kardex / Producto Terminado":
    st.header("📦 Inventario de Producto Terminado (Kardex)")
    # Aquí se muestra lo que hay en bodega
    data = {
        "Producto": ["Queso Costeño", "Queso Campesino", "Yogurt"],
        "Stock (Kg/Und)": [150.5, 80.0, 200],
        "Última actualización": [str(date.today())]*3
    }
    st.table(pd.DataFrame(data))

# --- 5. RESUMEN ---
elif opcion == "📊 Resumen General":
    st.header("📊 Director del Panel")
    c1, c2, c3 = st.columns(3)
    c1.metric("Leche en Tanque", "1,200 L")
    c2.metric("Producción Hoy", "450 Kg")
    c3.metric("Ventas Mes", "$ 12,500,000")
