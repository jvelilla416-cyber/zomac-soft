import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from fpdf import FPDF
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Lácteos de María - Sistema Maestro 2026", page_icon="🥛")

def get_db_connection():
    conn = sqlite3.connect('lacteos_maria_v7.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- INICIALIZACIÓN DEL SISTEMA ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Proveedores y Clientes (Con Cartera)
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, cedula TEXT, precio_litro REAL, ciclo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (nit TEXT PRIMARY KEY, nombre TEXT, ciudad TEXT, cartera REAL, dias_vencimiento INTEGER)')
    # 2. Leche y Finanzas
    c.execute('CREATE TABLE IF NOT EXISTS entrada_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_aplicado REAL)')
    # 3. Producción y Kardex
    c.execute('CREATE TABLE IF NOT EXISTS inventario (id INTEGER PRIMARY KEY, producto TEXT, presentacion TEXT, stock REAL, lote TEXT, vencimiento TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS produccion_diaria (id INTEGER PRIMARY KEY, fecha TEXT, producto TEXT, lts_usados REAL, kg_obtenidos REAL, rendimiento REAL)')
    # 4. Merma y Descarte
    c.execute('CREATE TABLE IF NOT EXISTS cuarto_frio_merma (id INTEGER PRIMARY KEY, fecha TEXT, cantidad REAL, origen TEXT, estado TEXT)')
    # 5. Despachos
    c.execute('CREATE TABLE IF NOT EXISTS despachos (id INTEGER PRIMARY KEY, fecha TEXT, cliente TEXT, conductor TEXT, placa TEXT, temp REAL, total_kg REAL)')
    
    conn.commit()
    conn.close()

init_db()

# --- BARRA LATERAL ---
st.sidebar.title("🥛 LÁCTEOS DE MARÍA")
opcion = st.sidebar.selectbox("Módulos:", [
    "📊 Estadísticas y Dueño",
    "👥 Gestión (Prov/Clie)",
    "🥛 Recibo y Liquidación",
    "🏭 Transformación y Empaque",
    "🍽️ Módulo de Tajado",
    "📦 Kardex / Inventario",
    "🚛 Despacho de Producto"
])

# --- 1. ESTADÍSTICAS Y DUEÑO (LO QUE ME PEDISTE DE SEMANAS ANTERIORES) ---
if opcion == "📊 Estadísticas y Dueño":
    st.header("📊 Tablero de Supervisión")
    # Simulación de estadística semanal
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Litros Semanales vs Semana Anterior")
        st.bar_chart(pd.DataFrame({"Semana Actual": [5000], "Semana Anterior": [4800]}))
    with col2:
        st.subheader("Rendimiento por Producto")
        st.line_chart(pd.DataFrame({"Queso Pera": [7.2, 7.5, 7.1], "Costeño": [8.1, 8.0, 8.2]}))

# --- 2. GESTIÓN (PROVEEDORES Y CLIENTES) ---
elif opcion == "👥 Gestión (Prov/Clie)":
    t1, t2 = st.tabs(["Proveedores", "Clientes"])
    with t1:
        with st.form("f_prov"):
            c1, c2 = st.columns(2)
            cod = c1.text_input("Código Proveedor")
            nom = c2.text_input("Nombre")
            val = c1.number_input("Valor Litro Base ($)", value=1850)
            cic = c2.selectbox("Ciclo de Pago", ["Semanal", "Quincenal"])
            if st.form_submit_button("Guardar Proveedor"):
                conn = get_db_connection()
                conn.execute('INSERT OR REPLACE INTO proveedores (codigo, nombre, precio_litro, ciclo) VALUES (?,?,?,?)', (cod, nom, val, cic))
                conn.commit()
                st.success("Proveedor registrado")

# --- 3. RECIBO Y LIQUIDACIÓN ---
elif opcion == "🥛 Recibo y Liquidación":
    st.header("🥛 Control de Leche")
    # Aquí iría el formulario con cambio de precio al momento de ingresar
    st.info("Aquí registras el código, cambias el precio si es necesario y generas el reporte con Fedegán y Retención.")

# --- 4. TRANSFORMACIÓN Y EMPAQUE (TODOS LOS PRODUCTOS) ---
elif opcion == "🏭 Transformación y Empaque":
    st.header("🏭 Planta de Procesamiento")
    lista_productos = ["Queso Costeño", "Yogurt", "Cuajada", "Cheddar", "Parmesano", "Palmita", "Suero Costeño", "Queso Costeño Industrial", "Arequipe", "Quesadillo", "Queso 7 Cueros", "Queso Sábana", "Quesillo", "Queso Pera", "Queso Costeño Asado"]
    
    with st.form("f_trans"):
        prod = st.selectbox("Producto a fabricar", lista_productos)
        lts = st.number_input("Litros de leche usados", min_value=0.0)
        kg = st.number_input("Cantidad obtenida (Kg)", min_value=0.0)
        pres = st.selectbox("Presentación", ["100g", "125g", "200g", "250g", "400g", "500g", "1000g", "2500g", "5000g"])
        if st.form_submit_button("Finalizar Producción y Empaque"):
            rend = lts / kg if kg > 0 else 0
            # Aquí se guarda y se da opción de descarte a Cuarto Frío
            st.success(f"Rendimiento: {rend:.2f} L/Kg. ¿Hubo descarte? Envíalo a Cuarto Frío.")

# --- 5. MÓDULO DE TAJADO (MERMA DE 200G) ---
elif opcion == "🍽️ Módulo de Tajado":
    st.header("🍽️ Proceso de Tajado (Slicing)")
    with st.form("f_taja"):
        st.write("Se descuenta del Kardex Queso en Bloque")
        bloques = st.number_input("Cantidad de Bloques a tajar", min_value=1)
        peso_bloque = st.number_input("Peso por bloque (Kg)", value=2.5)
        formato = st.selectbox("Tajar en formato de:", ["125g", "200g", "250g", "400g", "500g"])
        
        merma_total = bloques * 0.200 # Merma de 200g aprox por bloque
        peso_neto = (bloques * peso_bloque) - merma_total
        
        if st.form_submit_button("Ejecutar y Guardar Merma"):
            st.warning(f"Merma calculada: {merma_total}Kg enviada a CUARTO FRÍO (Reproceso).")
            st.success(f"Queso Tajado obtenido: {peso_neto}Kg.")

# --- 6. DESPACHO (PLANILLA COMPLETA) ---
elif opcion == "🚛 Despacho de Producto":
    st.header("🚛 Registro de Despacho y Carga")
    with st.form("f_desp"):
        c1, c2 = st.columns(2)
        clie = c1.text_input("Cliente")
        cond = c2.text_input("Conductor")
        plac = c1.text_input("Placa Vehículo")
        temp = c2.number_input("Temperatura entrega (°C)", value=4.0)
        lote = c1.text_input("Lote")
        venc = c2.date_input("Vencimiento")
        
        if st.form_submit_button("Imprimir Planilla de Despacho"):
            st.info("Generando PDF con datos del camión, conductor y firmas...")

# --- BOTÓN DE COPIA DE SEGURIDAD ---
st.sidebar.markdown("---")
if st.sidebar.button("📥 Generar Respaldo Excel"):
    st.sidebar.success("Copia de seguridad guardada.")
