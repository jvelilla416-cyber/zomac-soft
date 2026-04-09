import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Gestión Operativa", page_icon="🥛")

def get_db_connection():
    conn = sqlite3.connect('lacteos_suiza_v3.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- INICIALIZACIÓN DE TABLAS (MOTOR DE CÁLCULO) ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (id TEXT PRIMARY KEY, nombre TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT PRIMARY KEY, stock REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS despachos (id INTEGER PRIMARY KEY, fecha TEXT, cliente TEXT, producto TEXT, cantidad REAL, conductor TEXT, placa TEXT)')
    # Insertar productos base si no existen para que el Kardex funcione
    productos_base = [('Queso Bloque', 0), ('Queso Tajado', 0), ('Yogurt', 0)]
    c.executemany('INSERT OR IGNORE INTO inventario VALUES (?,?)', productos_base)
    conn.commit()
    conn.close()

init_db()

st.sidebar.header("MENÚ DE PLANTA")
opcion = st.sidebar.radio("Seleccione Operación:", [
    "📊 Tablero de Control",
    "🥛 Entrada de Leche",
    "🍽️ Tajadora (Slicing y Merma)",
    "📦 Kardex / Inventario",
    "🚛 Registro de Despacho y Planilla"
])

# --- MÓDULO: TAJADORA (EL QUE ME PEDISTE) ---
if opcion == "🍽️ Tajadora (Slicing y Merma)":
    st.header("🍽️ Proceso de Tajado (Slicing)")
    st.info("Este módulo calcula la merma automática del proceso.")
    
    with st.form("proceso_tajado"):
        col1, col2 = st.columns(2)
        with col1:
            bloques = st.number_input("Cantidad de Bloques a tajar", min_value=0, step=1)
            peso_bloque = st.number_input("Peso por bloque (Kg)", value=2.5)
        
        with col2:
            merma_por_bloque = st.number_input("Merma técnica por bloque (Kg)", value=0.200) # 200 gramos
            
        peso_total_esperado = bloques * peso_bloque
        merma_total = bloques * merma_por_bloque
        produccion_neta = peso_total_esperado - merma_total
        
        st.warning(f"📊 Cálculo: Esperado {peso_total_esperado}kg | Merma {merma_total}kg | Neto {produccion_neta}kg")
        
        if st.form_submit_button("Finalizar y Cargar a Inventario"):
            conn = get_db_connection()
            # Descontamos bloques y sumamos tajado
            conn.execute('UPDATE inventario SET stock = stock - ? WHERE producto = "Queso Bloque"', (peso_total_esperado,))
            conn.execute('UPDATE inventario SET stock = stock + ? WHERE producto = "Queso Tajado"', (produccion_neta,))
            conn.commit()
            st.success("✅ Inventario actualizado: Bloques descontados y Tajado cargado.")

# --- MÓDULO: DESPACHO Y PLANILLA (PDF) ---
elif opcion == "🚛 Registro de Despacho y Planilla":
    st.header("🚛 Registro de Despachos (Planilla Imprimible)")
    
    with st.form("registro_despacho"):
        f_desp = st.date_input("Fecha de Despacho", date.today())
        clie = st.text_input("Cliente / Destino")
        prod = st.selectbox("Producto", ["Queso Bloque", "Queso Tajado", "Yogurt"])
        cant = st.number_input("Cantidad (Kg/Und)", min_value=0.0)
        cond = st.text_input("Nombre del Conductor")
        plac = st.text_input("Placa del Vehículo")
        
        if st.form_submit_button("Registrar y Generar Planilla"):
            conn = get_db_connection()
            conn.execute('INSERT INTO despachos (fecha, cliente, producto, cantidad, conductor, placa) VALUES (?,?,?,?,?,?)',
                         (str(f_desp), clie, prod, cant, cond, plac))
            conn.execute('UPDATE inventario SET stock = stock - ? WHERE producto = ?', (cant, prod))
            conn.commit()
            st.success("Despacho registrado en sistema.")
            
            # --- GENERACIÓN DE PDF (PLANILLA) ---
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, "LACTEOS DE MARIA ZOMAC S.A.S.", ln=True, align='C')
            pdf.set_font("Arial", '', 12)
            pdf.cell(190, 10, "PLANILLA DE DESPACHO Y CONTROL DE CARGA", ln=True, align='C')
            pdf.ln(10)
            pdf.cell(100, 10, f"Fecha: {f_desp}")
            pdf.cell(90, 10, f"Placa: {plac}", ln=True)
            pdf.cell(190, 10, f"Cliente: {clie}", ln=True)
            pdf.cell(190, 10, f"Producto: {prod} - Cantidad: {cant} Kg", ln=True)
            pdf.cell(190, 10, f"Conductor: {cond}", ln=True)
            pdf.ln(20)
            pdf.cell(90, 10, "___________________", ln=False)
            pdf.cell(90, 10, "___________________", ln=True)
            pdf.cell(90, 10, "Firma Despacha", ln=False)
            pdf.cell(90, 10, "Firma Recibe", ln=True)
            
            pdf_output = pdf.output(dest='S').encode('latin-1')
            st.download_button(label="🖨️ DESCARGAR PLANILLA PARA IMPRIMIR", data=pdf_output, file_name=f"Planilla_{clie}.pdf", mime="application/pdf")

# --- MÓDULO: KARDEX ---
elif opcion == "📦 Kardex / Inventario":
    st.header("📦 Control de Inventario Real")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM inventario", conn)
    st.dataframe(df, use_container_width=True)

# --- RESUMEN ---
elif opcion == "📊 Tablero de Control":
    st.header("📊 Resumen de Operación")
    st.write("Bienvenido, aquí verás el estado de la planta en tiempo real.")
