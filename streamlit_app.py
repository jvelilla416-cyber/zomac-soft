import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Zomac - Finanzas y Operación", page_icon="💰")

def get_db_connection():
    conn = sqlite3.connect('zomac_contable.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- MOTOR DE BASE DE DATOS (ACTUALIZADO CON PRECIOS Y DESCUENTOS) ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Proveedores con precio acordado y tipo de pago
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, precio_litro REAL, tipo_pago TEXT)''')
    # Entrada de leche con registro de precio al momento del recibo
    c.execute('''CREATE TABLE IF NOT EXISTS entrada_leche 
                 (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_pactado REAL)''')
    # Inventario y Clientes con Precios de Venta
    c.execute('CREATE TABLE IF NOT EXISTS clientes (id TEXT PRIMARY KEY, nombre TEXT, precio_especial REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT PRIMARY KEY, stock REAL, precio_venta REAL)')
    
    # Productos iniciales
    prods = [('Queso Bloque', 0, 22000), ('Queso Tajado', 0, 25000), ('Yogurt', 0, 8000)]
    c.executemany('INSERT OR IGNORE INTO inventario VALUES (?,?,?)', prods)
    conn.commit()
    conn.close()

init_db()

# --- NAVEGACIÓN ---
st.sidebar.title("🥛 LÁCTEOS ZOMAC 2026")
opcion = st.sidebar.selectbox("Ir a:", [
    "👥 Gestión (Prov/Clientes)",
    "🥛 Recibo de Leche",
    "💸 Liquidación a Proveedores",
    "🏭 Producción y Rendimiento",
    "🚛 Despacho y Ventas"
])

# --- 1. GESTIÓN (PRECIOS ACORDADOS) ---
if opcion == "👥 Gestión (Prov/Clientes)":
    col1, col2 = st.columns(2)
    with col1:
        st.header("Gestión de Proveedores")
        with st.form("f_prov"):
            c_p = st.text_input("Código")
            n_p = st.text_input("Nombre")
            p_l = st.number_input("Precio por Litro ($)", value=1800)
            t_p = st.selectbox("Ciclo de Pago", ["Semanal", "Quincenal"])
            if st.form_submit_button("Guardar Proveedor"):
                conn = get_db_connection()
                conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?)', (c_p, n_p, p_l, t_p))
                conn.commit()
                st.success("Proveedor Guardado con Precio Pactado")

# --- 2. RECIBO DE LECHE ---
elif opcion == "🥛 Recibo de Leche":
    st.header("🥛 Registro de Litrajes")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    
    with st.form("f_leche"):
        f_l = st.date_input("Fecha", date.today())
        p_sel = st.selectbox("Proveedor", provs['codigo'] + " - " + provs['nombre'] if not provs.empty else ["No hay proveedores"])
        litros = st.number_input("Litros", min_value=0.0)
        if st.form_submit_button("Registrar"):
            cod = p_sel.split(" - ")[0]
            precio = provs[provs['codigo']==cod]['precio_litro'].values[0]
            conn.execute('INSERT INTO entrada_leche (fecha, cod_prov, litros, precio_pactado) VALUES (?,?,?,?)', 
                         (str(f_l), cod, litros, precio))
            conn.commit()
            st.success(f"Registrado: {litros} Lts a ${precio}")

# --- 3. LIQUIDACIÓN (LO QUE ME PEDISTE) ---
elif opcion == "💸 Liquidación a Proveedores":
    st.header("💸 Liquidación y Pagos")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    
    p_liq = st.selectbox("Seleccione Proveedor", provs['codigo'] + " - " + provs['nombre'])
    f_inicio = st.date_input("Desde", date.today())
    f_fin = st.date_input("Hasta", date.today())
    
    if st.button("Calcular Liquidación"):
        cod = p_liq.split(" - ")[0]
        query = f"SELECT * FROM entrada_leche WHERE cod_prov='{cod}' AND fecha BETWEEN '{f_inicio}' AND '{f_fin}'"
        df_liq = pd.read_sql_query(query, conn)
        
        if not df_liq.empty:
            total_lts = df_liq['litros'].sum()
            subtotal = (df_liq['litros'] * df_liq['precio_pactado']).sum()
            
            # --- DESCUENTOS ---
            desc_fedegan = total_lts * 10 # Ejemplo: $10 por litro
            retencion = subtotal * 0.015  # Ejemplo: 1.5%
            total_pagar = subtotal - desc_fedegan - retencion
            
            st.write(f"### Resumen para: {p_liq}")
            st.write(f"**Total Litros:** {total_lts} Lts")
            st.write(f"**Subtotal:** ${subtotal:,.0f}")
            st.error(f"**Descuento Fedegán:** -${desc_fedegan:,.0f}")
            st.error(f"**Retención:** -${retencion:,.0f}")
            st.success(f"**TOTAL A PAGAR:** ${total_pagar:,.0f}")
            
            # GENERAR PDF DE LIQUIDACIÓN
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(190, 10, "LACTEOS DE MARIA ZOMAC S.A.S.", ln=True, align='C')
            pdf.cell(190, 10, "COMPROBANTE DE LIQUIDACION DE LECHE", ln=True, align='C')
            pdf.ln(5)
            pdf.set_font("Arial", '', 11)
            pdf.cell(190, 8, f"Proveedor: {p_liq}", ln=True)
            pdf.cell(190, 8, f"Periodo: {f_inicio} al {f_fin}", ln=True)
            pdf.ln(5)
            pdf.cell(60, 8, "Concepto", 1)
            pdf.cell(60, 8, "Valor", 1, ln=True)
            pdf.cell(60, 8, "Total Litros", 1); pdf.cell(60, 8, f"{total_lts}", 1, ln=True)
            pdf.cell(60, 8, "Subtotal", 1); pdf.cell(60, 8, f"${subtotal:,.0f}", 1, ln=True)
            pdf.cell(60, 8, "Fedegan", 1); pdf.cell(60, 8, f"-${desc_fedegan:,.0f}", 1, ln=True)
            pdf.cell(60, 8, "Retencion", 1); pdf.cell(60, 8, f"-${retencion:,.0f}", 1, ln=True)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(60, 8, "TOTAL NETO", 1); pdf.cell(60, 8, f"${total_pagar:,.0f}", 1, ln=True)
            
            pdf_out = pdf.output(dest='S').encode('latin-1')
            st.download_button("🖨️ IMPRIMIR LIQUIDACIÓN", pdf_out, f"Liq_{cod}.pdf", "application/pdf")
