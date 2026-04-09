import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Gestión Planta")

def get_db_connection():
    conn = sqlite3.connect('suiza_v15_final.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Proveedores con ciudad y retención
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, cedula TEXT, ciudad TEXT,
                  fedegan_bool INTEGER, valor_litro REAL, ciclo TEXT)''')
    # Recibo de Leche con registro de fecha exacta
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros INTEGER, precio REAL, silo TEXT)')
    # Silos 10k
    c.execute('CREATE TABLE IF NOT EXISTS silos (nombre TEXT PRIMARY KEY, saldo REAL)')
    # Kardex
    c.execute('CREATE TABLE IF NOT EXISTS kardex (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    
    for s in ["Silo 1", "Silo 2", "Silo 3", "Silo 4"]:
        c.execute('INSERT OR IGNORE INTO silos VALUES (?, 0)', (s,))
    conn.commit()
    conn.close()

init_db()

# --- FUNCIÓN GENERAR VOLANTE PDF PROFESIONAL ---
def generar_volante_pdf(p_data, historial_leche):
    pdf = FPDF()
    pdf.add_page()
    # Encabezado con Logo (simulado con texto si no hay archivo)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "LÁCTEOS SUIZA S.A.S.", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, f"Fecha de Liquidación: {date.today()}", ln=True, align='C')
    pdf.ln(10)
    
    # Datos del Proveedor
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(95, 7, f"PROVEEDOR: {p_data['nombre']}", border=1)
    pdf.cell(95, 7, f"CÓDIGO: {p_data['codigo']}", border=1, ln=True)
    pdf.cell(95, 7, f"FINCA: {p_data['finca']}", border=1)
    pdf.cell(95, 7, f"CIUDAD: {p_data['ciudad']}", border=1, ln=True)
    pdf.ln(5)
    
    # Tabla de Días de Ingreso
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 7, "Fecha", 1); pdf.cell(50, 7, "Litros", 1); pdf.cell(50, 7, "Precio", 1); pdf.cell(50, 7, "Subtotal", 1, ln=True)
    pdf.set_font("Arial", '', 10)
    
    for _, fila in historial_leche.iterrows():
        pdf.cell(40, 7, str(fila['fecha']), 1)
        pdf.cell(50, 7, str(fila['litros']), 1)
        pdf.cell(50, 7, f"${fila['precio']:,.0f}", 1)
        pdf.cell(50, 7, f"${fila['litros']*fila['precio']:,.0f}", 1, ln=True)
    
    # Totales y Descuentos
    pdf.ln(5)
    subtotal = (historial_leche['litros'] * historial_leche['precio']).sum()
    fedegan = subtotal * 0.0075 if p_data['fedegan_bool'] == 1 else 0
    # Retención 1.5% si supera el monto mínimo sugerido de 3.6M
    retencion = (subtotal - fedegan) * 0.015 if (subtotal - fedegan) > 3666000 else 0
    total = subtotal - fedegan - retencion
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 7, "SUBTOTAL BRUTO:", 0, 0, 'R'); pdf.cell(50, 7, f"${subtotal:,.0f}", 1, ln=True)
    pdf.cell(140, 7, "DESCUENTO FEDEGAN (0.75%):", 0, 0, 'R'); pdf.cell(50, 7, f"-${fedegan:,.0f}", 1, ln=True)
    pdf.cell(140, 7, "RETENCIÓN EN LA FUENTE:", 0, 0, 'R'); pdf.cell(50, 7, f"-${retencion:,.0f}", 1, ln=True)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(140, 10, "TOTAL NETO A PAGAR:", 0, 0, 'R'); pdf.cell(50, 10, f"${total:,.0f}", 1, 1, 'L', fill=True)
    
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR ---
st.sidebar.image("logo_suiza.png", width=150)
menu = st.sidebar.selectbox("Módulos:", ["🆕 Proveedor", "🥛 Ingreso Rápido", "📊 Silos 10k", "💰 Liquidación PDF", "🏭 Producción", "🍽️ Tajado"])

# --- 1. NUEVO PROVEEDOR ---
if menu == "🆕 Proveedor":
    st.header("🆕 Registro de Nuevo Proveedor")
    with st.form("f_p", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cod = c1.text_input("Código")
        nom = c2.text_input("Nombre Completo")
        finca = c3.text_input("Finca")
        ced = c1.text_input("Cédula")
        ciu = c2.text_input("Ciudad/Municipio")
        val = c3.number_input("Valor Litro Base", value=1850.0)
        ciclo = c1.selectbox("Ciclo", ["Semanal", "Quincenal"])
        fede = st.checkbox("Aplica Fedegán (0.75%)")
        if st.form_submit_button("Guardar"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?,?,?,?)', (cod, nom, finca, ced, ciu, 1 if fede else 0, val, ciclo))
            conn.commit()
            st.success("Proveedor Guardado")

# --- 2. INGRESO DE LECHE (EFECTO ENTER) ---
elif menu == "🥛 Ingreso Rápido":
    st.header("🥛 Recibo de Leche (Ingreso con Enter)")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    
    # El formulario se limpia solo al enviar
    with st.form("f_recibo", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        p_sel = col1.selectbox("1. Proveedor (Enter para saltar)", ["Seleccione..."] + list(provs['codigo'] + " - " + provs['nombre']) if not provs.empty else [])
        lts = col2.number_input("2. Litros (Enter)", min_value=0, step=1, value=0)
        p_hoy = col3.number_input("3. Precio Hoy (Enter)", value=1850.0)
        silo = st.selectbox("4. Silo Destino", ["Silo 1", "Silo 2", "Silo 3", "Silo 4"])
        
        if st.form_submit_button("🚀 REGISTRAR E INGRESAR SIGUIENTE"):
            if p_sel != "Seleccione...":
                cod_p = p_sel.split(" - ")[0]
                conn.execute('UPDATE silos SET saldo = saldo + ? WHERE nombre = ?', (lts, silo))
                conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, precio, silo) VALUES (?,?,?,?,?)', (str(date.today()), cod_p, lts, p_hoy, silo))
                conn.commit()
                st.success("Registro Exitoso. Campos limpios para el siguiente.")
                st.rerun()

# --- 3. LIQUIDACIÓN E IMPRESIÓN ---
elif menu == "💰 Liquidación PDF":
    st.header("💰 Liquidación y Volantes")
    ciclo_sel = st.radio("Filtrar Ciclo:", ["Semanal", "Quincenal"], horizontal=True)
    conn = get_db_connection()
    
    # Consulta de todos los proveedores del ciclo
    query = f'''SELECT p.*, SUM(r.litros) as total_lts FROM recibo_leche r 
               JOIN proveedores p ON r.cod_prov = p.codigo WHERE p.ciclo = '{ciclo_sel}' GROUP BY p.codigo'''
    df = pd.read_sql_query(query, conn)
    
    if not df.empty:
        st.subheader(f"Relación de {ciclo_sel}")
        st.dataframe(df[['codigo', 'nombre', 'finca', 'total_lts']], use_container_width=True)
        
        st.divider()
        st.subheader("🖨️ Generar Volante Individual")
        p_liq = st.selectbox("Escoger Proveedor de la lista:", df['nombre'])
        
        if st.button("📄 Preparar Volante de Pago"):
            p_data = df[df['nombre'] == p_liq].iloc[0].to_dict()
            hist = pd.read_sql_query(f"SELECT fecha, litros, precio FROM recibo_leche WHERE cod_prov = '{p_data['codigo']}'", conn)
            
            pdf_bytes = generar_volante_pdf(p_data, hist)
            st.download_button(label="📥 DESCARGAR E IMPRIMIR VOLANTE", data=pdf_bytes, file_name=f"Volante_{p_liq}.pdf", mime="application/pdf")
    else:
        st.info("No hay datos para liquidar.")

# --- 4. TAJADO Y MERMA ---
elif menu == "🍽️ Tajado":
    st.header("🍽️ Tajado de Bloques")
    with st.form("f_taja", clear_on_submit=True):
        queso = st.selectbox("Producto:", ["Mozzarella", "Sábana", "Pera", "Cheddar", "Doble Crema"])
        bloques = st.number_input("Bloques de 2.5kg", min_value=0, step=1)
        porcion = st.selectbox("Porción:", ["125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g"])
        
        if st.form_submit_button("⚖️ Tajar y Registrar"):
            merma = bloques * 0.200
            neto = (bloques * 2.5) - merma
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (queso + " Tajado", porcion, queso + " Tajado", porcion, neto))
            conn.commit()
            st.warning(f"REGISTRO: Merma de {merma}kg. Neto de {neto}kg cargado al Kardex.")

# --- 5. PRODUCCIÓN ---
elif menu == "🏭 Producción":
    st.header("🏭 Producción y Transformación")
    variedades = ["Queso Costeño Pasteurizado", "Queso Mozzarella", "Queso Pera", "Queso Sábana", "Queso Costeño Industrializado", "Queso Cheddar", "Suero Costeño", "Yogurt (Vaso)", "Yogurt (Bolsa)", "Arequipe", "Quesadillo"]
    with st.form("f_prod"):
        s_u = st.selectbox("Silo (10.000L):", ["Silo 1", "Silo 2", "Silo 3", "Silo 4"])
        lts_u = st.number_input("Litros usados:", min_value=0)
        p_f = st.selectbox("Variedad:", variedades)
        cant_f = st.number_input("Cantidad final (Kg/Und):", min_value=0.0)
        if st.form_submit_button("Finalizar y Guardar"):
            conn = get_db_connection()
            conn.execute('UPDATE silos SET saldo = saldo - ? WHERE nombre = ?', (lts_u, s_u))
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (p_f, "Bloque", p_f, "Bloque", cant_f))
            conn.commit()
            st.success("Producción ingresada.")
