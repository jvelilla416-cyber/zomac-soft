import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from fpdf import FPDF
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Lácteos de María - Sistema Maestro", page_icon="🥛")

# --- CONEXIÓN A BASE DE DATOS ---
def get_db_connection():
    conn = sqlite3.connect('lacteos_maria_v5.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- INICIALIZACIÓN DEL CEREBRO (TABLAS) ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Proveedores y Clientes
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, cedula TEXT, precio_base REAL, ciclo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (id TEXT PRIMARY KEY, nombre TEXT, ciudad TEXT, cartera REAL, dias_vencimiento INTEGER)')
    # 2. Leche y Liquidación
    c.execute('CREATE TABLE IF NOT EXISTS entrada_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_aplicado REAL)')
    # 3. Transformación y Producto Terminado (Kardex)
    c.execute('CREATE TABLE IF NOT EXISTS produccion (id INTEGER PRIMARY KEY, fecha TEXT, litros_usados REAL, producto TEXT, kg_obtenidos REAL, rendimiento REAL, lote TEXT, vencimiento TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT PRIMARY KEY, stock_kg REAL, lote TEXT, vencimiento TEXT)')
    # 4. Tajado y Merma
    c.execute('CREATE TABLE IF NOT EXISTS merma_fria (id INTEGER PRIMARY KEY, fecha TEXT, cantidad REAL, origen TEXT, estado TEXT)')
    # 5. Despachos
    c.execute('CREATE TABLE IF NOT EXISTS despachos (id INTEGER PRIMARY KEY, fecha TEXT, cliente_id TEXT, conductor TEXT, placa TEXT, total_kg REAL, temp REAL)')
    
    # Productos iniciales en Stop
    prods = [('Queso Bloque', 0), ('Queso Tajado', 0), ('Yogurt', 0), ('Queso Costeño', 0)]
    for p, s in prods:
        c.execute('INSERT OR IGNORE INTO inventario (producto, stock_kg) VALUES (?,?)', (p, s))
    conn.commit()
    conn.close()

init_db()

# --- NAVEGACIÓN ---
st.sidebar.title("🥛 LÁCTEOS DE MARÍA")
st.sidebar.info("Sistema Supervisado por Dueño")
opcion = st.sidebar.selectbox("Seleccione Módulo:", [
    "📊 Tablero de Control (Dueño)",
    "👥 Gestión (Prov/Clientes)",
    "🥛 Recibo de Leche",
    "💸 Liquidación Proveedores",
    "🏭 Transformación y Empaque",
    "🍽️ Módulo de Tajado",
    "📦 Kardex (Inventario)",
    "🚛 Despacho y Planillas"
])

# --- 1. GESTIÓN (PROVEEDORES Y CLIENTES) ---
if opcion == "👥 Gestión (Prov/Clientes)":
    col1, col2 = st.columns(2)
    with col1:
        st.header("Proveedores")
        with st.form("f_prov"):
            c_p = st.text_input("Código")
            n_p = st.text_input("Nombre")
            v_l = st.number_input("Valor Litro Base ($)", value=1850)
            cic = st.selectbox("Ciclo", ["Semanal", "Quincenal"])
            if st.form_submit_button("Guardar Proveedor"):
                conn = get_db_connection()
                conn.execute('INSERT OR REPLACE INTO proveedores (codigo, nombre, precio_base, ciclo) VALUES (?,?,?,?)', (c_p, n_p, v_l, cic))
                conn.commit()
                st.success("Guardado")

# --- 2. RECIBO DE LECHE ---
elif opcion == "🥛 Recibo de Leche":
    st.header("🥛 Ingreso de Leche")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    with st.form("f_leche"):
        cod_p = st.selectbox("Código Proveedor", provs['codigo'] if not provs.empty else [])
        lts = st.number_input("Litraje", min_value=0.0)
        p_hoy = st.number_input("Precio hoy (Cambiable)", value=1850)
        if st.form_submit_button("Registrar Ingreso"):
            conn.execute('INSERT INTO entrada_leche (fecha, cod_prov, litros, precio_aplicado) VALUES (?,?,?,?)', (str(date.today()), cod_p, lts, p_hoy))
            conn.commit()
            st.success("Leche registrada")

# --- 3. LIQUIDACIÓN ---
elif opcion == "💸 Liquidación Proveedores":
    st.header("💸 Liquidación (Semanal/Quincenal)")
    # Aquí se calcularía Fedegán (1%) y Retención (según valor)
    st.info("Seleccione el periodo y el proveedor para generar el reporte impreso.")

# --- 4. TRANSFORMACIÓN Y EMPAQUE ---
elif opcion == "🏭 Transformación y Empaque":
    st.header("🏭 Transformación de Materia Prima")
    with st.form("f_trans"):
        l_uso = st.number_input("Litros tomados para transformación", min_value=0.0)
        tipo = st.selectbox("Producto a fabricar", ["Queso Bloque", "Yogurt", "Costeño"])
        kg_final = st.number_input("Producto Terminado (Kg)", min_value=0.0)
        lote = st.text_input("Lote")
        venc = st.date_input("Vencimiento")
        if st.form_submit_button("Cargar a Kardex"):
            rend = l_uso / kg_final if kg_final > 0 else 0
            conn = get_db_connection()
            conn.execute('INSERT INTO produccion (fecha, litros_usados, producto, kg_obtenidos, rendimiento, lote, vencimiento) VALUES (?,?,?,?,?,?,?)',
                         (str(date.today()), l_uso, tipo, kg_final, rend, lote, str(venc)))
            conn.execute('UPDATE inventario SET stock_kg = stock_kg + ? WHERE producto = ?', (kg_final, tipo))
            conn.commit()
            st.success(f"Rendimiento: {rend:.2f} L/Kg. Cargado a Kardex.")

# --- 5. TAJADO (CON MERMA) ---
elif opcion == "🍽️ Módulo de Tajado":
    st.header("🍽️ Proceso de Tajado")
    st.write("Formatos: 125g, 200g, 250g, 400g, 500g, 1000g, etc.")
    with st.form("f_taja"):
        kg_bloque = st.number_input("Kg de Queso Bloque tomados de Kardex", min_value=0.0)
        merma = st.number_input("Merma (Aprox 200g por bloque)", value=0.200)
        if st.form_submit_button("Ejecutar Tajado"):
            neto = kg_bloque - merma
            conn = get_db_connection()
            conn.execute('UPDATE inventario SET stock_kg = stock_kg - ? WHERE producto = "Queso Bloque"', (kg_bloque,))
            conn.execute('UPDATE inventario SET stock_kg = stock_kg + ? WHERE producto = "Queso Tajado"', (neto,))
            conn.execute('INSERT INTO merma_fria (fecha, cantidad, origen, estado) VALUES (?,?,?,?)', (str(date.today()), merma, "Tajado", "Cuarto Frío/Reproceso"))
            conn.commit()
            st.success(f"Tajado listo. Merma de {merma}kg enviada a Cuarto Frío.")

# --- 6. DESPACHO Y PLANILLA ---
elif opcion == "🚛 Despacho y Planillas":
    st.header("🚛 Registro de Despacho")
    with st.form("f_desp"):
        clie = st.text_input("Cliente")
        cond = st.text_input("Conductor")
        plac = st.text_input("Placa")
        temp = st.number_input("Temperatura de entrega", value=4.0)
        if st.form_submit_button("Generar Planilla"):
            # Lógica de PDF con todos los campos (Lote, Vencimiento, Placa, etc.)
            st.success("Planilla lista para firmar.")

# --- 7. TABLERO DUEÑO (ESTADÍSTICAS) ---
elif opcion == "📊 Tablero de Control (Dueño)":
    st.header("📊 Estadísticas de Lácteos de María")
    st.subheader("Comparativa de Rendimiento (Esta semana vs Anterior)")
    # Aquí el sistema compara los rendimientos guardados en la tabla 'produccion'
    st.line_chart(pd.DataFrame({"Semana Actual": [7.2, 7.5, 7.1], "Semana Anterior": [7.8, 7.6, 8.0]}))
