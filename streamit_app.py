import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from fpdf import FPDF
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Sistema Profesional")

def get_db_connection():
    # Nueva versión para asegurar limpieza total de tablas
    conn = sqlite3.connect('suiza_v16_maestra.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Proveedores con Ciudad
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, cedula TEXT, ciudad TEXT,
                  valor_litro REAL, ciclo TEXT, fedegan_bool INTEGER)''')
    # 2. Recibo de Leche (Litros Enteros)
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros INTEGER, precio REAL, silo TEXT)')
    # 3. Silos 10k
    c.execute('CREATE TABLE IF NOT EXISTS silos (nombre TEXT PRIMARY KEY, saldo REAL)')
    # 4. Kardex
    c.execute('CREATE TABLE IF NOT EXISTS kardex (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    
    for s in ["Silo 1", "Silo 2", "Silo 3", "Silo 4"]:
        c.execute('INSERT OR IGNORE INTO silos VALUES (?, 0)', (s,))
    conn.commit()
    conn.close()

init_db()

# --- FUNCIÓN VOLANTE DE PAGO PDF ---
def generar_volante_pdf(p_data, historial):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado / Logo
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "LÁCTEOS SUIZA S.A.S.", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 7, "VOLANTE DE PAGO DE LECHE", ln=True, align='C')
    pdf.ln(5)
    
    # Cuadro de Información General
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 7, "FECHA:", 1); pdf.cell(65, 7, f"{date.today()}", 1)
    pdf.cell(30, 7, "CIUDAD:", 1); pdf.cell(65, 7, f"{p_data['ciudad']}", 1, ln=True)
    pdf.cell(30, 7, "PROVEEDOR:", 1); pdf.cell(65, 7, f"{p_data['nombre']}", 1)
    pdf.cell(30, 7, "CÓDIGO:", 1); pdf.cell(65, 7, f"{p_data['codigo']}", 1, ln=True)
    pdf.cell(30, 7, "FINCA:", 1); pdf.cell(160, 7, f"{p_data['finca']}", 1, ln=True)
    pdf.ln(5)
    
    # Tabla de Detalle
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(40, 7, "Fecha Ingreso", 1, 0, 'C', True)
    pdf.cell(50, 7, "Cantidad (Lts)", 1, 0, 'C', True)
    pdf.cell(50, 7, "Valor Litro", 1, 0, 'C', True)
    pdf.cell(50, 7, "Subtotal", 1, 1, 'C', True)
    
    pdf.set_font("Arial", '', 10)
    for _, r in historial.iterrows():
        pdf.cell(40, 7, f"{r['fecha']}", 1)
        pdf.cell(50, 7, f"{r['litros']}", 1, 0, 'R')
        pdf.cell(50, 7, f"${r['precio']:,.0f}", 1, 0, 'R')
        pdf.cell(50, 7, f"${r['litros']*r['precio']:,.0f}", 1, 1, 'R')
    
    # Cálculos Finales
    subtotal = (historial['litros'] * historial['precio']).sum()
    fede = subtotal * 0.0075 if p_data['fedegan_bool'] == 1 else 0
    rete = (subtotal - fede) * 0.015 if (subtotal - fede) > 3666000 else 0
    total = subtotal - fede - rete
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 7, "SUBTOTAL BRUTO:", 0, 0, 'R'); pdf.cell(50, 7, f"${subtotal:,.0f}", 1, 1, 'R')
    pdf.cell(140, 7, "DCTO. FEDEGAN (0.75%):", 0, 0, 'R'); pdf.cell(50, 7, f"-${fede:,.0f}", 1, 1, 'R')
    pdf.cell(140, 7, "RETENCION FUENTE:", 0, 0, 'R'); pdf.cell(50, 7, f"-${rete:,.0f}", 1, 1, 'R')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(140, 10, "TOTAL NETO A PAGAR:", 0, 0, 'R'); pdf.cell(50, 10, f"${total:,.0f}", 1, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR ---
st.sidebar.image("logo_suiza.png", width=150)
menu = st.sidebar.selectbox("MENÚ PLANTA:", [
    "🆕 Nuevo Proveedor", 
    "🥛 Ingreso de Leche", 
    "📊 Silos (10k L)", 
    "💰 Liquidación y Volantes", 
    "🏭 Producción", 
    "🍽️ Tajado"
])

# --- 1. NUEVO PROVEEDOR ---
if menu == "🆕 Nuevo Proveedor":
    st.header("🆕 Registro con Salto de Casilla (Enter)")
    with st.form("f_p", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cod = c1.text_input("1. Código")
        nom = c2.text_input("2. Nombre")
        finca = c1.text_input("3. Finca")
        ced = c2.text_input("4. Cédula")
        ciu = c1.text_input("5. Ciudad/Municipio")
        val = c2.number_input("6. Valor Litro Base", value=1850.0)
        ciclo = st.selectbox("7. Ciclo de Pago", ["Semanal", "Quincenal"])
        fede = st.checkbox("Aplica Fedegán (0.75%)")
        if st.form_submit_button("✅ GUARDAR PROVEEDOR"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?,?,?,?)', (cod, nom, finca, ced, ciu, val, ciclo, 1 if fede else 0))
            conn.commit()
            st.success("Proveedor Guardado Correctamente")

# --- 2. INGRESO DE LECHE (Limpia al instante) ---
elif menu == "🥛 Ingreso de Leche":
    st.header("🥛 Recibo Diario (Efecto Enter)")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    
    with st.form("f_recibo", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        p_sel = col1.selectbox("1. Proveedor", [""] + list(provs['codigo'] + " - " + provs['nombre']) if not provs.empty else [""])
        lts = col2.number_input("2. Litros (Sin decimales)", min_value=0, step=1, value=0)
        p_hoy = col3.number_input("3. Precio Hoy ($)", value=1850.0)
        silo = st.selectbox("4. Silo Destino", ["Silo 1", "Silo 2", "Silo 3", "Silo 4"])
        
        if st.form_submit_button("🚀 REGISTRAR E INGRESAR SIGUIENTE"):
            if p_sel != "":
                cod_p = p_sel.split(" - ")[0]
                conn.execute('UPDATE silos SET saldo = saldo + ? WHERE nombre = ?', (lts, silo))
                conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, precio, silo) VALUES (?,?,?,?,?)', (str(date.today()), cod_p, lts, p_hoy, silo))
                conn.commit()
                st.success("Registro Exitoso. Campos limpios.")
                st.rerun() # Fuerza la limpieza visual inmediata

# --- 3. LIQUIDACIÓN E IMPRESIÓN ---
elif menu == "💰 Liquidación y Volantes":
    st.header("💰 Liquidación Profesional")
    ciclo_sel = st.radio("Ciclo:", ["Semanal", "Quincenal"], horizontal=True)
    conn = get_db_connection()
    query = f'''SELECT p.*, SUM(r.litros) as total_lts FROM recibo_leche r 
               JOIN proveedores p ON r.cod_prov = p.codigo WHERE p.ciclo = '{ciclo_sel}' GROUP BY p.codigo'''
    df = pd.read_sql_query(query, conn)
    
    if not df.empty:
        st.dataframe(df[['codigo', 'nombre', 'finca', 'total_lts']], use_container_width=True)
        st.divider()
        st.subheader("🖨️ Selección Individual para Volante")
        p_escogido = st.selectbox("Elija Proveedor:", df['nombre'])
        
        if st.button("📄 Generar Volante PDF"):
            p_data = df[df['nombre'] == p_escogido].iloc[0].to_dict()
            hist = pd.read_sql_query(f"SELECT fecha, litros, precio FROM recibo_leche WHERE cod_prov = '{p_data['codigo']}'", conn)
            pdf_bytes = generar_volante_pdf(p_data, hist)
            st.download_button(f"📥 Descargar Volante {p_escogido}", pdf_bytes, f"Volante_{p_escogido}.pdf", "application/pdf")
    else:
        st.info("No hay datos en este ciclo.")

# --- 4. PRODUCCIÓN ---
elif menu == "🏭 Producción":
    st.header("🏭 Transformación de Silos")
    variedades = [
        "Queso Costeño Pasteurizado", "Queso Mozzarella", "Queso Pera", 
        "Queso Sábana", "Queso Costeño Industrializado", "Queso Cheddar",
        "Suero Costeño", "Yogurt (Vaso)", "Yogurt (Bolsa)", "Arequipe", "Quesadillo"
    ]
    with st.form("f_prod", clear_on_submit=True):
        silo_u = st.selectbox("Silo Origen:", ["Silo 1", "Silo 2", "Silo 3", "Silo 4"])
        lts_u = st.number_input("Litros usados:", min_value=0)
        prod = st.selectbox("Transformar a:", variedades)
        cant = st.number_input("Cantidad final (Kg/Und):", min_value=0.0)
        if st.form_submit_button("Guardar Producción"):
            conn = get_db_connection()
            conn.execute('UPDATE silos SET saldo = saldo - ? WHERE nombre = ?', (lts_u, silo_u))
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (prod, "Bloque", prod, "Bloque", cant))
            conn.commit()
            st.success("Kardex actualizado.")

# --- 5. TAJADO ---
elif menu == "🍽️ Tajado":
    st.header("🍽️ Tajado de Bloques")
    with st.form("f_t", clear_on_submit=True):
        q = st.selectbox("Queso:", ["Mozzarella", "Sábana", "Pera", "Cheddar", "Doble Crema"])
        bl = st.number_input("Bloques (2.5kg):", min_value=0, step=1)
        por = st.selectbox("Porción:", ["125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g"])
        if st.form_submit_button("Tajar y Registrar"):
            merma = bl * 0.200
            neto = (bl * 2.5) - merma
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (q + " Tajado", por, q + " Tajado", por, neto))
            conn.commit()
            st.warning(f"Merma: {merma}kg | Neto: {neto}kg")

# --- 6. SILOS VISUAL ---
elif menu == "📊 Silos (10k L)":
    st.header("📊 Nivel de Silos")
    conn = get_db_connection()
    df_s = pd.read_sql_query("SELECT * FROM silos", conn)
    cols = st.columns(4)
    for i, row in df_s.iterrows():
        cols[i].metric(row['nombre'], f"{row['saldo']:.0f} L")
        cols[i].progress(min(row['saldo']/10000, 1.0))
