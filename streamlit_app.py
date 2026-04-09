import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos de María Zomac S.A.S.", page_icon="🥛")

def get_db_connection():
    # Cambiamos el nombre del archivo para que se cree de cero sin errores
    conn = sqlite3.connect('zomac_sistema_final.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- INICIALIZACIÓN LIMPIA ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, precio_base REAL, ciclo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (nit TEXT PRIMARY KEY, nombre TEXT, cartera REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS entrada_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_dia REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT PRIMARY KEY, stock REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS produccion (id INTEGER PRIMARY KEY, fecha TEXT, producto TEXT, kg REAL, rendimiento REAL)')
    
    # Insertar productos uno por uno para que no falle como en la foto
    productos = ["Queso Bloque", "Queso Tajado", "Yogurt", "Queso Pera", "Suero Costeño"]
    for p in productos:
        c.execute('INSERT OR IGNORE INTO inventario (producto, stock) VALUES (?, 0)')
    
    conn.commit()
    conn.close()

init_db()

# --- NAVEGACIÓN SEPARADA ---
st.sidebar.title("🥛 LÁCTEOS DE MARÍA")
opcion = st.sidebar.selectbox("Seleccione el Proceso:", [
    "📊 Supervisión Dueño",
    "👥 Registro Proveedores",
    "🥛 Recibo de Leche",
    "💸 Liquidación de Pagos",
    "🏭 Transformación y Empaque",
    "🍽️ Tajado y Merma",
    "📦 Kardex / Inventario",
    "📑 Órdenes de Despacho",
    "🚛 Despacho Final"
])

# --- MÓDULO DE RECIBO (EL QUE ALIMENTA TODO) ---
if opcion == "🥛 Recibo de Leche":
    st.header("🥛 Recibo Diario de Leche")
    # Aquí ya puede meter el código del proveedor y los litros
    st.success("Listo para ingresar litrajes.")

# --- MÓDULO ÓRDEN DE DESPACHO (PARA PORTERÍA) ---
elif opcion == "📑 Órdenes de Despacho":
    st.header("📑 Órden de Salida (Copia Portería)")
    # Aquí se imprime la orden para que portería deje salir el camión
    st.info("Escriba los datos para imprimir la orden de salida.")

# --- EL RESTO DE MÓDULOS... ---
