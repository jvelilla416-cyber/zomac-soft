import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Zomac - Sistema Maestro", page_icon="🥛")

def get_db_connection():
    conn = sqlite3.connect('zomac_maestro.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- MOTOR DE BASE DE DATOS (NUEVAS TABLAS) ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (id TEXT PRIMARY KEY, nombre TEXT, ciudad TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS entrada_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS produccion (id INTEGER PRIMARY KEY, fecha TEXT, producto TEXT, kg REAL, rendimiento REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT PRIMARY KEY, stock REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS merma_tajado (id INTEGER PRIMARY KEY, fecha TEXT, cantidad REAL, estado TEXT)') # Reproceso o Frío
    
    # Inicializar productos en Kardex
    prods = [('Queso Bloque', 0), ('Queso Tajado', 0), ('Yogurt', 0), ('Merma Tajado', 0)]
    c.executemany('INSERT OR IGNORE INTO inventario VALUES (?,?)', prods)
    conn.commit()
    conn.close()

init_db()

# --- NAVEGACIÓN ---
st.sidebar.title("🥛 LÁCTEOS ZOMAC S.A.S.")
opcion = st.sidebar.selectbox("Ir a:", [
    "👥 Gestión (Prov/Clientes)",
    "🥛 Entrada de Leche",
    "🏭 Producción y Rendimiento",
    "🍽️ Tajadora y Merma",
    "📦 Kardex / Inventario",
    "🚛 Despacho y Planillas"
])

# --- 1. GESTIÓN (PROVEEDORES Y CLIENTES) ---
if opcion == "👥 Gestión (Prov/Clientes)":
    col1, col2 = st.columns(2)
    with col1:
        st.header("Gestión de Proveedores")
        with st.form("f_prov"):
            c_p = st.text_input("Código del Proveedor")
            n_p = st.text_input("Nombre")
            if st.form_submit_button("Guardar Proveedor"):
                conn = get_db_connection()
                conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?)', (c_p, n_p, ""))
                conn.commit()
                st.success("Proveedor Creado")
    with col2:
        st.header("Gestión de Clientes")
        with st.form("f_clie"):
            id_c = st.text_input("ID Cliente")
            nom_c = st.text_input("Nombre Cliente")
            if st.form_submit_button("Guardar Cliente"):
                conn = get_db_connection()
                conn.execute('INSERT OR REPLACE INTO clientes VALUES (?,?,?)', (id_c, nom_c, ""))
                conn.commit()
                st.success("Cliente Creado")

# --- 2. ENTRADA DE LECHE ---
elif opcion == "🥛 Entrada de Leche":
    st.header("🥛 Registro de Litrajes del Día")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT codigo, nombre FROM proveedores", conn)
    
    with st.form("f_leche"):
        f_l = st.date_input("Fecha", date.today())
        p_l = st.selectbox("Proveedor", provs['codigo'] + " - " + provs['nombre'] if not provs.empty else ["No hay proveedores"])
        litros = st.number_input("Litros Recibidos", min_value=0.0)
        if st.form_submit_button("Registrar Litraje"):
            cod = p_l.split(" - ")[0]
            conn.execute('INSERT INTO entrada_leche (fecha, cod_prov, litros) VALUES (?,?,?)', (str(f_l), cod, litros))
            conn.commit()
            st.success("Litraje Guardado")

# --- 3. PRODUCCIÓN Y RENDIMIENTO ---
elif opcion == "🏭 Producción y Rendimiento":
    st.header("🏭 Producción del Día")
    conn = get_db_connection()
    # Calcular total leche hoy para el rendimiento
    total_leche = pd.read_sql_query(f"SELECT SUM(litros) as t FROM entrada_leche WHERE fecha='{date.today()}'", conn)['t'][0] or 0
    st.info(f"Leche disponible hoy: {total_leche} Lts")
    
    with st.form("f_prod"):
        prod = st.selectbox("Producto Fabricado", ["Queso Bloque", "Yogurt", "Queso Campesino"])
        kg = st.number_input("Kilogramos Obtenidos", min_value=0.0)
        if st.form_submit_button("Cargar Producción al Kardex"):
            # CÁLCULO DE RENDIMIENTO: (Total leche / Kg obtenidos)
            rend = total_leche / kg if kg > 0 else 0
            conn.execute('INSERT INTO produccion (fecha, producto, kg, rendimiento) VALUES (?,?,?,?)', (str(date.today()), prod, kg, rend))
            conn.execute('UPDATE inventario SET stock = stock + ? WHERE producto = ?', (kg, prod))
            conn.commit()
            st.success(f"Producción guardada. Rendimiento: {rend:.2f} Lts/Kg")

# --- 4. TAJADORA Y MERMA ---
elif opcion == "🍽️ Tajadora y Merma":
    st.header("🍽️ Tajadora (Slicing)")
    with st.form("f_taja"):
        peso_bloque_in = st.number_input("Peso de Bloques sacados de Kardex (Kg)", min_value=0.0)
        merma = st.number_input("Merma del proceso (Kg)", min_value=0.0)
        estado_merma = st.selectbox("Destino de la Merma", ["Cuarto Frío", "Reproceso"])
        if st.form_submit_button("Ejecutar Tajado"):
            neto = peso_bloque_in - merma
            conn = get_db_connection()
            # Descuenta bloque, suma tajado, registra merma
            conn.execute('UPDATE inventario SET stock = stock - ? WHERE producto = "Queso Bloque"', (peso_bloque_in,))
            conn.execute('UPDATE inventario SET stock = stock + ? WHERE producto = "Queso Tajado"', (neto,))
            conn.execute('INSERT INTO merma_tajado (fecha, cantidad, estado) VALUES (?,?,?)', (str(date.today()), merma, estado_merma))
            conn.commit()
            st.success(f"Tajado listo. Neto: {neto}kg. Merma de {merma}kg enviada a {estado_merma}")

# --- 5. DESPACHO Y PLANILLAS ---
elif opcion == "🚛 Despacho y Planillas":
    st.header("🚛 Despacho de Producto")
    with st.form("f_desp"):
        clie = st.text_input("Cliente")
        prod = st.selectbox("Producto", ["Queso Bloque", "Queso Tajado", "Yogurt"])
        cant = st.number_input("Cantidad a Despachar", min_value=0.0)
        lote = st.text_input("Lote")
        venc = st.date_input("Vencimiento")
        temp = st.number_input("Temperatura (°C)", value=4.0)
        cond = st.text_input("Conductor")
        plac = st.text_input("Placa")
        
        if st.form_submit_button("Registrar y Generar Planilla"):
            conn = get_db_connection()
            conn.execute('UPDATE inventario SET stock = stock - ? WHERE producto = ?', (cant, prod))
            conn.commit()
            
            # GENERACIÓN DE PDF PROFESIONAL
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(190, 10, "LACTEOS DE MARIA ZOMAC S.A.S. - PLANILLA DE DESPACHO", ln=True, align='C')
            pdf.set_font("Arial", '', 11)
            pdf.ln(5)
            pdf.cell(95, 8, f"Cliente: {clie}")
            pdf.cell(95, 8, f"Fecha: {date.today()}", ln=True)
            pdf.cell(95, 8, f"Conductor: {cond}")
            pdf.cell(95, 8, f"Placa: {plac}", ln=True)
            pdf.ln(5)
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(50, 8, "Producto", 1, 0, 'C', True)
            pdf.cell(30, 8, "Cant", 1, 0, 'C', True)
            pdf.cell(40, 8, "Lote", 1, 0, 'C', True)
            pdf.cell(40, 8, "Venc", 1, 0, 'C', True)
            pdf.cell(30, 8, "Temp", 1, 1, 'C', True)
            pdf.cell(50, 8, prod, 1)
            pdf.cell(30, 8, str(cant), 1)
            pdf.cell(40, 8, lote, 1)
            pdf.cell(40, 8, str(venc), 1)
            pdf.cell(30, 8, f"{temp}C", 1, 1)
            
            pdf_out = pdf.output(dest='S').encode('latin-1')
            st.download_button("🖨️ DESCARGAR PLANILLA PDF", pdf_out, f"Planilla_{clie}.pdf", "application/pdf")

# --- 6. KARDEX ---
elif opcion == "📦 Kardex / Inventario":
    st.header("📦 Inventario de Productos (Kardex)")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM inventario", conn)
    st.table(df)
