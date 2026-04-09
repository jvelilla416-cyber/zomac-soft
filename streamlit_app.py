import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos de María Zomac", page_icon="🥛")

def get_db_connection():
    conn = sqlite3.connect('zomac_definitivo.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- MOTOR DE DATOS SEPARADO ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, cedula TEXT, precio_litro REAL, ciclo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS entrada_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_dia REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT PRIMARY KEY, stock REAL, lote TEXT, vencimiento TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS ordenes (id INTEGER PRIMARY KEY, fecha TEXT, cliente TEXT, producto TEXT, cantidad REAL, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (nit TEXT PRIMARY KEY, nombre TEXT, cartera REAL)')
    
    # Lista de productos de Lácteos de María
    prods = ["Queso Costeño", "Yogurt", "Cuajada", "Cheddar", "Parmesano", "Palmita", "Suero Costeño", "Queso Costeño Industrial", "Arequipe", "Quesadillo", "Queso 7 Cueros", "Queso Sábana", "Quesillo", "Queso Pera", "Queso Costeño Asado", "Queso Bloque"]
    for p in prods:
        c.execute('INSERT OR IGNORE INTO inventario (producto, stock) VALUES (?, 0)')
    conn.commit()
    conn.close()

init_db()

# --- NAVEGACIÓN TOTALMENTE INDEPENDIENTE ---
st.sidebar.title("🥛 LÁCTEOS DE MARÍA")
opcion = st.sidebar.selectbox("Módulo:", [
    "📊 Supervisión (Dueño)",
    "👥 Gestión de Proveedores",
    "🥛 Recibo de Leche (Planta)",
    "💸 Liquidación (Pagos)",
    "🏭 Transformación/Empaque",
    "🍽️ Tajado y Merma",
    "📦 Kardex / Inventario",
    "🤝 Gestión de Clientes",
    "📑 Órdenes de Despacho (Portería)",
    "🚛 Despacho Final (Camión)"
])

# --- 1. RECIBO DE LECHE (SOLO PARA INGRESAR DATOS) ---
if opcion == "🥛 Recibo de Leche (Planta)":
    st.header("🥛 Registro Diario de Recibo de Leche")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT codigo, nombre, precio_litro FROM proveedores", conn)
    
    with st.form("f_recibo"):
        c1, c2 = st.columns(2)
        cod_p = c1.selectbox("Código Proveedor", provs['codigo'] if not provs.empty else ["Cree proveedores primero"])
        litros = c2.number_input("Litros Recibidos", min_value=0.0)
        # Permite cambiar el precio al momento del ingreso como pediste
        precio_actual = st.number_input("Precio por Litro para este recibo ($)", value=1850)
        if st.form_submit_button("✅ Registrar Entrada"):
            conn.execute('INSERT INTO entrada_leche (fecha, cod_prov, litros, precio_dia) VALUES (?,?,?,?)', 
                         (str(date.today()), cod_p, litros, precio_actual))
            conn.commit()
            st.success(f"Registrado: {litros} Lts de Proveedor {cod_p}")

# --- 2. LIQUIDACIÓN (ESTE ES EL QUE IMPRIME PARA EL PAGO) ---
elif opcion == "💸 Liquidación (Pagos)":
    st.header("💸 Liquidación de Cuentas")
    st.info("Aquí se calcula Fedegán, Retención y el neto a pagar semanal/quincenal.")
    # (Lógica de cálculo y PDF de liquidación aquí)

# --- 3. ÓRDENES DE DESPACHO (LA COPIA PARA PORTERÍA) ---
elif opcion == "📑 Órdenes de Despacho (Portería)":
    st.header("📑 Órden de Salida de Producto")
    with st.form("f_orden"):
        clie = st.text_input("Cliente Destino")
        prod = st.selectbox("Producto a despachar", ["Queso Bloque", "Queso Tajado", "Yogurt", "Pera"])
        cant = st.number_input("Cantidad (Kg/Und)", min_value=0.0)
        if st.form_submit_button("🖨️ Generar y Firmar Orden"):
            # Lógica para imprimir 2 copias: Una para despacho y otra para portería
            st.write("Generando documento de salida...")
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, "LACTEOS DE MARIA - ORDEN DE SALIDA", ln=True, align='C')
            pdf.set_font("Arial", '', 12)
            pdf.cell(190, 10, f"Fecha: {date.today()}", ln=True)
            pdf.cell(190, 10, f"Producto: {prod} - Cantidad: {cant}", ln=True)
            pdf.ln(10)
            pdf.cell(90, 10, "Firma Autoriza (Planta)", 1); pdf.cell(90, 10, "Sello Portería", 1, ln=True)
            
            pdf_out = pdf.output(dest='S').encode('latin-1')
            st.download_button("Descargar Orden para Portería", pdf_out, "Orden_Salida.pdf")

# --- 4. DESPACHO FINAL (LA PLANILLA DEL CONDUCTOR) ---
elif opcion == "🚛 Despacho Final (Camión)":
    st.header("🚛 Planilla de Despacho (Documento del Conductor)")
    st.write("Incluye Lote, Vencimiento, Temperatura y Placa.")
    # (Lógica de despacho final con todos los detalles técnicos)
