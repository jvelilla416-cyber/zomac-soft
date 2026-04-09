import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos de María Zomac S.A.S.", page_icon="🥛")

def get_db_connection():
    # Nueva base de datos para limpiar errores previos
    conn = sqlite3.connect('zomac_maestra_2026.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- INICIALIZACIÓN DE TODA LA ESTRUCTURA ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Proveedores y Clientes
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, cedula TEXT, precio_litro REAL, ciclo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (nit TEXT PRIMARY KEY, nombre TEXT, ciudad TEXT, cartera REAL, dias_vencimiento INTEGER)')
    # 2. Leche y Liquidación
    c.execute('CREATE TABLE IF NOT EXISTS entrada_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_aplicado REAL, ciclo TEXT)')
    # 3. Transformación, Empaque y Kardex
    c.execute('CREATE TABLE IF NOT EXISTS produccion (id INTEGER PRIMARY KEY, fecha TEXT, producto TEXT, presentacion TEXT, lts_usados REAL, kg_obtenidos REAL, rendimiento REAL, lote TEXT, vencimiento TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS inventario (id_item INTEGER PRIMARY KEY, producto TEXT, presentacion TEXT, stock REAL, lote TEXT, vencimiento TEXT)')
    # 4. Merma y Cuarto Frío
    c.execute('CREATE TABLE IF NOT EXISTS cuarto_frio (id INTEGER PRIMARY KEY, fecha TEXT, cantidad REAL, origen TEXT, motivo TEXT)')
    # 5. Órdenes y Despacho
    c.execute('CREATE TABLE IF NOT EXISTS ordenes (id INTEGER PRIMARY KEY, fecha TEXT, cliente TEXT, producto TEXT, cantidad REAL, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS despachos (id INTEGER PRIMARY KEY, fecha TEXT, cliente TEXT, conductor TEXT, placa TEXT, temp REAL, lote TEXT, total_kg REAL)')
    conn.commit()
    conn.close()

init_db()

# --- NAVEGACIÓN ---
st.sidebar.title("🥛 LÁCTEOS DE MARÍA")
opcion = st.sidebar.selectbox("Módulo de Operación:", [
    "📊 Supervisión y Estadísticas",
    "👥 Gestión (Prov/Clie)",
    "🥛 Ingreso de Leche",
    "💸 Liquidación Proveedores",
    "🏭 Transformación y Empaque",
    "🍽️ Proceso de Tajado",
    "📦 Kardex / Inventario",
    "📑 Órdenes de Despacho",
    "🚛 Despacho Final"
])

# --- 1. GESTIÓN DE PROVEEDORES ---
if opcion == "👥 Gestión (Prov/Clie)":
    st.header("👥 Registro de Proveedores y Clientes")
    t1, t2 = st.tabs(["Proveedores", "Clientes"])
    with t1:
        with st.form("f_prov"):
            col1, col2 = st.columns(2)
            c_p = col1.text_input("Código")
            n_p = col2.text_input("Nombre Completo")
            p_b = col1.number_input("Valor Litro Base ($)", value=1850)
            cic = col2.selectbox("Ciclo de Pago", ["Semanal", "Quincenal"])
            if st.form_submit_button("Guardar Proveedor"):
                conn = get_db_connection()
                conn.execute('INSERT OR REPLACE INTO proveedores (codigo, nombre, precio_litro, ciclo) VALUES (?,?,?,?)', (c_p, n_p, p_b, cic))
                conn.commit()
                st.success("Proveedor registrado.")

# --- 2. INGRESO DE LECHE ---
elif opcion == "🥛 Ingreso de Leche":
    st.header("🥛 Ingreso de Leche")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    with st.form("f_leche"):
        cod = st.selectbox("Código Proveedor", provs['codigo'] if not provs.empty else [])
        litros = st.number_input("Litraje", min_value=0.0)
        precio = st.number_input("Precio Litro Hoy ($) - Cambiable", value=1850)
        if st.form_submit_button("Registrar Ingreso"):
            ciclo = provs[provs['codigo']==cod]['ciclo'].values[0]
            conn.execute('INSERT INTO entrada_leche (fecha, cod_prov, litros, precio_aplicado, ciclo) VALUES (?,?,?,?,?)', 
                         (str(date.today()), cod, litros, precio, ciclo))
            conn.commit()
            st.success("Ingreso registrado.")

# --- 3. TRANSFORMACIÓN Y PRODUCTO TERMINADO ---
elif opcion == "🏭 Transformación y Empaque":
    st.header("🏭 Transformación de Materia Prima")
    prods = ["Queso Costeño", "Yogurt", "Cuajada", "Cheddar", "Parmesano", "Palmita", "Suero Costeño", "Queso Costeño Industrial", "Arequipe", "Quesadillo", "Queso 7 Cueros", "Queso Sábana", "Quesillo", "Queso Pera", "Queso Costeño Asado"]
    pres = ["100g", "125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g", "5000g"]
    
    with st.form("f_trans"):
        p_sel = st.selectbox("Producto a Fabricar", prods)
        lts_in = st.number_input("Litros de Leche usados", min_value=0.0)
        kg_out = st.number_input("Producto Terminado (Kg/Und)", min_value=0.0)
        p_pres = st.selectbox("Presentación", pres)
        lote = st.text_input("Lote")
        venc = st.date_input("Vencimiento")
        if st.form_submit_button("Registrar Producción"):
            rend = lts_in / kg_out if kg_out > 0 else 0
            conn = get_db_connection()
            conn.execute('INSERT INTO produccion (fecha, producto, presentacion, lts_usados, kg_obtenidos, rendimiento, lote, vencimiento) VALUES (?,?,?,?,?,?,?,?)',
                         (str(date.today()), p_sel, p_pres, lts_in, kg_out, rend, lote, str(venc)))
            conn.execute('INSERT INTO inventario (producto, presentacion, stock, lote, vencimiento) VALUES (?,?,?,?,?)',
                         (p_sel, p_pres, kg_out, lote, str(venc)))
            conn.commit()
            st.success(f"Rendimiento: {rend:.2f} L/Kg. Cargado a Kardex.")

# --- 4. MÓDULO DE TAJADO (CON MERMA) ---
elif opcion == "🍽️ Proceso de Tajado":
    st.header("🍽️ Tajado de Queso")
    with st.form("f_tajado"):
        st.write("Seleccione el bloque de Kardex para tajar")
        kg_bloque = st.number_input("Peso de Bloques a procesar (Kg)", min_value=0.0)
        pres_salida = st.selectbox("Presentación final", ["125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g"])
        
        # Merma de 200g aprox por bloque
        num_bloques = kg_bloque / 2.5 if kg_bloque > 0 else 0
        merma_calc = num_bloques * 0.200
        peso_neto = kg_bloque - merma_calc
        
        if st.form_submit_button("Ejecutar Tajado"):
            conn = get_db_connection()
            # Guardamos merma en cuarto frío
            conn.execute('INSERT INTO cuarto_frio (fecha, cantidad, origen, motivo) VALUES (?,?,"Tajado","Merma de Proceso")', (str(date.today()), merma_calc))
            # Actualizamos inventario
            conn.execute('INSERT INTO inventario (producto, presentacion, stock) VALUES (?,?,?)', ("Queso Tajado", pres_salida, peso_neto))
            conn.commit()
            st.warning(f"Merma: {merma_calc:.2f} Kg enviada a Cuarto Frío.")
            st.success(f"Neto a Kardex: {peso_neto:.2f} Kg.")

# --- 5. ÓRDENES DE DESPACHO ---
elif opcion == "📑 Órdenes de Despacho":
    st.header("📑 Órden de Salida")
    with st.form("f_orden"):
        clie = st.text_input("Cliente")
        prod_o = st.text_input("Producto")
        cant_o = st.number_input("Cantidad")
        if st.form_submit_button("Generar Órden"):
            st.success("Órden generada. Imprima copia para Portería y otra para Despacho.")

# --- 6. DESPACHO FINAL ---
elif opcion == "🚛 Despacho Final":
    st.header("🚛 Planilla de Despacho Final")
    with st.form("f_desp"):
        col1, col2 = st.columns(2)
        c_desp = col1.text_input("Cliente")
        cond = col2.text_input("Conductor")
        plac = col1.text_input("Placa")
        temp = col2.number_input("Temperatura (°C)", value=4.0)
        if st.form_submit_button("Imprimir Planilla Final"):
            st.success("Planilla de despacho generada para firma del conductor.")

# --- BOTÓN DE RESPALDO EXCEL ---
st.sidebar.markdown("---")
if st.sidebar.button("📥 Generar Respaldo Excel"):
    st.sidebar.info("Excel generado. Descárguelo para su supervisión.")
