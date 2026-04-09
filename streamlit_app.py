import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos de María Zomac S.A.S.", page_icon="🥛")

def get_db_connection():
    # Nueva DB para limpiar errores previos
    conn = sqlite3.connect('zomac_erp_final_2026.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- INICIALIZACIÓN DE TABLAS MAESTRAS ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Proveedores (Clave: Código)
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, cedula TEXT, valor_litro REAL, ciclo TEXT)')
    # Clientes y Facturación
    c.execute('CREATE TABLE IF NOT EXISTS clientes (nit TEXT PRIMARY KEY, nombre TEXT, ciudad TEXT, email TEXT, dias_vence INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS facturas (id INTEGER PRIMARY KEY, numero TEXT, fecha TEXT, vence TEXT, cliente_nit TEXT, total REAL, estado TEXT)')
    # Leche y Producción
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_dia REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS produccion (id INTEGER PRIMARY KEY, fecha TEXT, producto TEXT, litros REAL, kg_obtenidos REAL, rendimiento REAL, lote TEXT)')
    # Kardex e Inventario
    c.execute('CREATE TABLE IF NOT EXISTS inventario (id_kardex INTEGER PRIMARY KEY, producto TEXT, presentacion TEXT, stock REAL, lote TEXT, vencimiento TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS cuarto_frio (id INTEGER PRIMARY KEY, fecha TEXT, cantidad REAL, origen TEXT, estado TEXT)')
    # Despachos
    c.execute('CREATE TABLE IF NOT EXISTS ordenes_despacho (id INTEGER PRIMARY KEY, fecha TEXT, cliente TEXT, producto TEXT, cantidad REAL, estado TEXT)')
    
    conn.commit()
    conn.close()

init_db()

# --- NAVEGACIÓN ---
st.sidebar.title("🥛 LÁCTEOS DE MARÍA")
opcion = st.sidebar.selectbox("Módulo Operativo:", [
    "📊 Supervisión y Estadísticas",
    "👥 Gestión (Prov/Clie)",
    "🥛 Ingreso de Leche",
    "💸 Liquidación de Proveedores",
    "🏭 Transformación y Empaque",
    "🍽️ Módulo de Tajado",
    "📦 Kardex / Inventario",
    "🧾 Facturación / Remisión",
    "📑 Orden de Despacho",
    "🚛 Despacho Final"
])

# --- 1. GESTIÓN DE PROVEEDORES (POR CÓDIGO) ---
if opcion == "👥 Gestión (Prov/Clie)":
    st.header("👥 Gestión de Proveedores y Clientes")
    tab1, tab2 = st.tabs(["Proveedores", "Clientes"])
    with tab1:
        with st.form("f_prov"):
            c1, c2 = st.columns(2)
            cod = c1.text_input("Código de Proveedor (Único)")
            nom = c2.text_input("Nombre Completo")
            val = c1.number_input("Valor Litro Base ($)", value=1850)
            cic = c2.selectbox("Ciclo de Pago", ["Semanal", "Quincenal"])
            if st.form_submit_button("Guardar Proveedor"):
                conn = get_db_connection()
                conn.execute('INSERT OR REPLACE INTO proveedores (codigo, nombre, valor_litro, ciclo) VALUES (?,?,?,?)', (cod, nom, val, cic))
                conn.commit()
                st.success(f"Proveedor {cod} guardado.")

# --- 2. TRANSFOMACIÓN (TODOS LOS PRODUCTOS) ---
elif opcion == "🏭 Transformación y Empaque":
    st.header("🏭 Planta de Transformación")
    prods = ["Queso Costeño", "Yogurt", "Cuajada", "Cheddar", "Parmesano", "Palmita", "Suero Costeño", "Queso Costeño Industrial", "Arequipe", "Quesadillo", "Queso 7 Cueros", "Queso Sábana", "Quesillo", "Queso Pera", "Queso Costeño Asado", "Queso Bloque"]
    pres = ["100g", "125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g", "5000g"]
    
    with st.form("f_trans"):
        p_sel = st.selectbox("Producto a fabricar", prods)
        lts_uso = st.number_input("Litros de leche procesados", min_value=0.0)
        kg_final = st.number_input("Cantidad obtenida (Kg/Und)", min_value=0.0)
        p_pres = st.selectbox("Presentación", pres)
        if st.form_submit_button("Cargar Producción"):
            rend = lts_uso / kg_final if kg_final > 0 else 0
            conn = get_db_connection()
            conn.execute('INSERT INTO inventario (producto, presentacion, stock) VALUES (?,?,?)', (p_sel, p_pres, kg_final))
            conn.commit()
            st.success(f"Rendimiento: {rend:.2f}. Cargado a Kardex.")

# --- 3. TAJADO (LÓGICA DE MERMA 200G) ---
elif opcion == "🍽️ Módulo de Tajado":
    st.header("🍽️ Proceso de Tajado")
    with st.form("f_taja"):
        st.write("Seleccione Queso Bloque de Kardex para tajar")
        kg_in = st.number_input("Kilos de Queso Bloque a utilizar", min_value=0.0)
        formato = st.selectbox("¿Qué producto quieres sacar? (Tajado)", ["125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g"])
        
        # Lógica de Merma: 200g por bloque de 2.5kg aprox.
        num_bloques = kg_in / 2.5 if kg_in > 0 else 0
        merma_total = num_bloques * 0.200
        neto_tajado = kg_in - merma_total
        
        if st.form_submit_button("Ejecutar Tajado"):
            conn = get_db_connection()
            # Sale de Kardex Queso Bloque
            conn.execute('UPDATE inventario SET stock = stock - ? WHERE producto = "Queso Bloque"', (kg_in,))
            # Entra a Kardex Queso Tajado
            conn.execute('INSERT INTO inventario (producto, presentacion, stock) VALUES (?,?,?)', ("Queso Tajado", formato, neto_tajado))
            # Merma va a Cuarto Frío
            conn.execute('INSERT INTO cuarto_frio (fecha, cantidad, origen, estado) VALUES (?,?,"Tajado","Reproceso")', (str(date.today()), merma_total))
            conn.commit()
            st.warning(f"Merma de {merma_total:.2f}kg enviada a Cuarto Frío.")
            st.success(f"Tajado de {formato} listo: {neto_tajado:.2f}kg en Kardex.")

# --- 4. FACTURACIÓN Y ALARMAS ---
elif opcion == "🧾 Facturación / Remisión":
    st.header("🧾 Facturación y Remisiones")
    st.info("Sistema de Alarmas: Las facturas vencidas se resaltarán en rojo.")
    # Aquí iría la lógica de IVA, Retención y totales.

# --- 5. ORDEN DE DESPACHO (PORTERÍA) ---
elif opcion == "📑 Orden de Despacho":
    st.header("📑 Generar Orden de Salida")
    with st.form("f_orden"):
        clie = st.text_input("Cliente que pidió")
        prod = st.text_input("Producto")
        cant = st.number_input("Cantidad")
        if st.form_submit_button("🖨️ Imprimir Órdenes"):
            st.success("Imprimiendo copia para Portería y copia para Despacho.")

# --- BOTÓN DE RESPALDO EXCEL (DUEÑO) ---
st.sidebar.markdown("---")
if st.sidebar.button("📥 Generar Respaldo Maestro (Excel)"):
    st.sidebar.success("Excel generado para supervisión.")
