import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos de María Zomac S.A.S.", page_icon="🥛")

def get_db_connection():
    # Base de datos robusta para evitar bloqueos
    conn = sqlite3.connect('zomac_erp_v10.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- INICIALIZACIÓN DE TABLAS ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Proveedores: Aquí nace el PRECIO BASE
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, precio_base REAL, ciclo TEXT, cedula TEXT)')
    # Entrada de Leche: Guarda el precio que hubo ese día
    c.execute('CREATE TABLE IF NOT EXISTS entrada_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_dia REAL)')
    # Clientes y Facturación
    c.execute('CREATE TABLE IF NOT EXISTS clientes (nit TEXT PRIMARY KEY, nombre TEXT, ciudad TEXT, cartera REAL)')
    # Inventario y Merma
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT PRIMARY KEY, stock REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS cuarto_frio (id INTEGER PRIMARY KEY, fecha TEXT, cantidad REAL, motivo TEXT)')
    conn.commit()
    conn.close()

init_db()

# --- NAVEGACIÓN ---
st.sidebar.title("🥛 LÁCTEOS DE MARÍA")
opcion = st.sidebar.selectbox("Módulo:", [
    "👥 Gestión Proveedores", 
    "🥛 Recibo de Leche", 
    "💸 Liquidación de Pagos",
    "🏭 Transformación/Kardex",
    "🍽️ Tajado y Merma",
    "🧾 Facturación y Clientes",
    "📑 Orden de Despacho",
    "🚛 Despacho Final"
])

# --- 1. GESTIÓN PROVEEDORES (DONDE SE DETERMINA EL PRECIO) ---
if opcion == "👥 Gestión Proveedores":
    st.header("👥 Registro de Proveedores")
    with st.form("f_prov"):
        c1, c2 = st.columns(2)
        cod = c1.text_input("Código Proveedor (Ej: 001)")
        nom = c2.text_input("Nombre Completo")
        pre = c1.number_input("Precio Base por Litro ($)", value=1850)
        cic = c2.selectbox("Ciclo de Pago", ["Semanal", "Quincenal"])
        if st.form_submit_button("✅ Guardar Proveedor"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores (codigo, nombre, precio_base, ciclo) VALUES (?,?,?,?)', (cod, nom, pre, cic))
            conn.commit()
            st.success(f"Proveedor {cod} guardado con precio de ${pre}")

# --- 2. RECIBO DE LECHE (USA EL PRECIO DEL PROVEEDOR) ---
elif opcion == "🥛 Recibo de Leche":
    st.header("🥛 Ingreso de Leche por Código")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    
    with st.form("f_leche"):
        p_sel = st.selectbox("Código Proveedor", provs['codigo'] if not provs.empty else [])
        lts = st.number_input("Litros recibidos", min_value=0.0)
        
        # Busca el precio base que guardaste en el módulo de proveedores
        precio_sugerido = 1850
        if p_sel:
            precio_sugerido = provs[provs['codigo'] == p_sel]['precio_base'].values[0]
            
        p_hoy = st.number_input("Precio aplicado hoy ($)", value=float(precio_sugerido))
        
        if st.form_submit_button("🚀 Registrar Ingreso"):
            conn.execute('INSERT INTO entrada_leche (fecha, cod_prov, litros, precio_dia) VALUES (?,?,?,?)', 
                         (str(date.today()), p_sel, lts, p_hoy))
            conn.commit()
            st.success("Litraje guardado para liquidar.")

# --- 3. LIQUIDACIÓN DE PAGOS (EL QUE NO TE DEJABA) ---
elif opcion == "💸 Liquidación de Pagos":
    st.header("💸 Liquidación de Proveedores")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    
    p_liq = st.selectbox("Seleccione Proveedor para Liquidar", provs['codigo'] if not provs.empty else [])
    c1, c2 = st.columns(2)
    f1 = c1.date_input("Fecha Inicio", date.today() - timedelta(days=7))
    f2 = c2.date_input("Fecha Fin", date.today())
    
    if st.button("📊 Calcular Liquidación"):
        df_l = pd.read_sql_query(f"SELECT * FROM entrada_leche WHERE cod_prov='{p_liq}' AND fecha BETWEEN '{f1}' AND '{f2}'", conn)
        
        if not df_l.empty:
            total_lts = df_l['litros'].sum()
            # Calcula el dinero basado en el precio que se registró en cada ingreso
            subtotal = (df_l['litros'] * df_l['precio_dia']).sum()
            
            # Descuentos de Ley (Ajustables)
            fedegan = total_lts * 10 
            retencion = subtotal * 0.015
            neto = subtotal - fedegan - retencion
            
            st.write(f"### Reporte de Pago: {p_liq}")
            st.metric("TOTAL NETO A PAGAR", f"${neto:,.0f}")
            
            # Tabla de detalle para el reporte impreso
            st.table(df_l[['fecha', 'litros', 'precio_dia']])
            
            # --- BOTÓN PARA IMPRIMIR PDF ---
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16); pdf.cell(190, 10, "LACTEOS DE MARIA ZOMAC S.A.S.", ln=True, align='C')
            pdf.set_font("Arial", '', 12); pdf.cell(190, 10, f"Liquidacion: {p_liq} | Periodo: {f1} a {f2}", ln=True)
            pdf.ln(10)
            pdf.cell(100, 10, f"Total Litros: {total_lts}"); pdf.cell(90, 10, f"Subtotal: ${subtotal:,.0f}", ln=True)
            pdf.cell(100, 10, f"Fedegan: -${fedegan:,.0f}"); pdf.cell(90, 10, f"Rete: -${retencion:,.0f}", ln=True)
            pdf.set_font("Arial", 'B', 12); pdf.cell(190, 10, f"TOTAL A PAGAR: ${neto:,.0f}", ln=True)
            
            pdf_out = pdf.output(dest='S').encode('latin-1')
            st.download_button("🖨️ Descargar Reporte para Impresión", pdf_out, f"Liquidacion_{p_liq}.pdf")
        else:
            st.error("No hay registros de leche para este proveedor en esas fechas.")
