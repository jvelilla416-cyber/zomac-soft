import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from fpdf import FPDF
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Sistema Maestro")

def get_db_connection():
    conn = sqlite3.connect('suiza_v18_maestra.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, cedula TEXT, ciudad TEXT,
                  valor_litro REAL, ciclo TEXT, fedegan_bool INTEGER)''')
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros INTEGER, precio REAL, silo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS silos (nombre TEXT PRIMARY KEY, saldo REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS kardex (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    
    for s in ["Silo 1", "Silo 2", "Silo 3", "Silo 4"]:
        c.execute('INSERT OR IGNORE INTO silos VALUES (?, 0)', (s,))
    conn.commit()
    conn.close()

init_db()

# --- GENERADOR DE PDF (VOLANTE) ---
def generar_volante_pdf(p_data, historial):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "LÁCTEOS SUIZA S.A.S.", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 7, "VOLANTE DE PAGO DE LECHE", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(30, 8, "FECHA:", 1, 0, 'L', True); pdf.cell(65, 8, f"{date.today()}", 1)
    pdf.cell(30, 8, "CIUDAD:", 1, 0, 'L', True); pdf.cell(65, 8, f"{p_data['ciudad']}", 1, ln=True)
    pdf.cell(30, 8, "PROVEEDOR:", 1, 0, 'L', True); pdf.cell(65, 8, f"{p_data['nombre']}", 1)
    pdf.cell(30, 8, "CÓDIGO:", 1, 0, 'L', True); pdf.cell(65, 8, f"{p_data['codigo']}", 1, ln=True)
    pdf.cell(30, 8, "FINCA:", 1, 0, 'L', True); pdf.cell(160, 8, f"{p_data['finca']}", 1, ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(40, 7, "Fecha", 1, 0, 'C', True)
    pdf.cell(50, 7, "Litros", 1, 0, 'C', True)
    pdf.cell(50, 7, "Precio", 1, 0, 'C', True)
    pdf.cell(50, 7, "Subtotal", 1, 1, 'C', True)
    
    pdf.set_font("Arial", '', 10)
    for _, r in historial.iterrows():
        pdf.cell(40, 7, f"{r['fecha']}", 1)
        pdf.cell(50, 7, f"{r['litros']}", 1, 0, 'R')
        pdf.cell(50, 7, f"${r['precio']:,.0f}", 1, 0, 'R')
        pdf.cell(50, 7, f"${r['litros']*r['precio']:,.0f}", 1, 1, 'R')
    
    subtotal = (historial['litros'] * historial['precio']).sum()
    fede = subtotal * 0.0075 if p_data['fedegan_bool'] == 1 else 0
    rete = (subtotal - fede) * 0.015 if (subtotal - fede) > 3666000 else 0
    total = subtotal - fede - rete
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 8, "SUBTOTAL BRUTO:", 0, 0, 'R'); pdf.cell(50, 8, f"${subtotal:,.0f}", 1, 1, 'R')
    pdf.cell(140, 8, "FEDEGAN (0.75%):", 0, 0, 'R'); pdf.cell(50, 8, f"-${fede:,.0f}", 1, 1, 'R')
    pdf.cell(140, 8, "RETENCION:", 0, 0, 'R'); pdf.cell(50, 8, f"-${rete:,.0f}", 1, 1, 'R')
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(140, 10, "TOTAL NETO:", 0, 0, 'R'); pdf.cell(50, 10, f"${total:,.0f}", 1, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR ---
st.sidebar.image("logo_suiza.png", width=150)
menu = st.sidebar.selectbox("MÓDULOS:", ["🆕 Nuevo Proveedor", "🥛 Ingreso de Leche", "💰 Liquidación", "🏭 Producción", "🍽️ Tajado", "📊 Silos (10k)"])

# --- 1. NUEVO PROVEEDOR ---
if menu == "🆕 Nuevo Proveedor":
    st.header("🆕 Registro de Proveedores")
    with st.form("f_p", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cod = c1.text_input("1. Código")
        nom = c2.text_input("2. Nombre")
        finca = c1.text_input("3. Finca")
        ced = c2.text_input("4. Cédula")
        ciu = c1.text_input("5. Ciudad")
        val = c2.number_input("6. Valor Litro", value=1850.0)
        ciclo = st.selectbox("7. Ciclo", ["Semanal", "Quincenal"])
        fede = st.checkbox("Aplica Fedegán (0.75%)")
        if st.form_submit_button("✅ GUARDAR"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?,?,?,?)', (cod, nom, finca, ced, ciu, val, ciclo, 1 if fede else 0))
            conn.commit()
            st.success("Guardado.")

# --- 2. INGRESO DE LECHE (FLUJO RÁPIDO) ---
elif menu == "🥛 Ingreso de Leche":
    st.header("🥛 Recibo de Leche")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    
    with st.form("f_recibo", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        p_sel = col1.selectbox("1. Proveedor", [""] + list(provs['codigo'] + " - " + provs['nombre']) if not provs.empty else [""])
        # value=None hace que el campo aparezca vacío
        lts = col2.number_input("2. Litros (Enter)", min_value=0, step=1, value=None, placeholder="0")
        p_hoy = col3.number_input("3. Precio hoy", value=1850.0)
        silo = st.selectbox("4. Silo", ["Silo 1", "Silo 2", "Silo 3", "Silo 4"])
        
        if st.form_submit_button("🚀 REGISTRAR"):
            if p_sel != "" and lts is not None:
                cod_p = p_sel.split(" - ")[0]
                conn.execute('UPDATE silos SET saldo = saldo + ? WHERE nombre = ?', (lts, silo))
                conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, precio, silo) VALUES (?,?,?,?,?)', (str(date.today()), cod_p, lts, p_hoy, silo))
                conn.commit()
                st.success("Ingreso registrado. Formulario limpio.")
                st.rerun()

# --- 3. LIQUIDACIÓN (BOTÓN DE DESCARGA ARREGLADO) ---
elif menu == "💰 Liquidación":
    st.header("💰 Liquidación y Volantes")
    ciclo_sel = st.radio("Ciclo:", ["Semanal", "Quincenal"], horizontal=True)
    conn = get_db_connection()
    query = f'''SELECT p.*, SUM(r.litros) as total_lts FROM recibo_leche r 
               JOIN proveedores p ON r.cod_prov = p.codigo WHERE p.ciclo = '{ciclo_sel}' GROUP BY p.codigo'''
    df_res = pd.read_sql_query(query, conn)
    
    if not df_res.empty:
        st.dataframe(df_res[['codigo', 'nombre', 'finca', 'total_lts']], use_container_width=True)
        
        # Descarga general
        csv = df_res.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Relación Grupal (Excel/CSV)", csv, f"Relacion_{ciclo_sel}.csv", "text/csv")
        
        st.divider()
        st.subheader("🖨️ Volante Individual")
        p_vol = st.selectbox("Seleccione Ganadero:", df_res['nombre'])
        
        if st.button("📄 Generar Volante"):
            p_data = df_res[df_res['nombre'] == p_vol].iloc[0].to_dict()
            hist = pd.read_sql_query(f"SELECT fecha, litros, precio FROM recibo_leche WHERE cod_prov = '{p_data['codigo']}'", conn)
            pdf_bytes = generar_volante_pdf(p_data, hist)
            st.download_button(f"📥 GUARDAR VOLANTE {p_vol}", pdf_bytes, f"Volante_{p_vol}.pdf", "application/pdf")
    else:
        st.info("Sin datos.")

# --- 4. PRODUCCIÓN Y TAJADO ---
elif menu == "🏭 Producción":
    st.header("🏭 Transformación")
    variedades = ["Queso Costeño Pasteurizado", "Queso Mozzarella", "Queso Pera", "Queso Sábana", "Queso Costeño Industrializado", "Queso Cheddar", "Suero Costeño", "Yogurt (Vaso)", "Yogurt (Bolsa)", "Arequipe", "Quesadillo"]
    with st.form("f_prod", clear_on_submit=True):
        s_u = st.selectbox("Silo:", ["Silo 1", "Silo 2", "Silo 3", "Silo 4"])
        lts_u = st.number_input("Litros:", min_value=0)
        prod = st.selectbox("Variedad:", variedades)
        cant = st.number_input("Cantidad (Kg/Und):", min_value=0.0)
        if st.form_submit_button("Guardar"):
            conn = get_db_connection()
            conn.execute('UPDATE silos SET saldo = saldo - ? WHERE nombre = ?', (lts_u, s_u))
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (prod, "Bloque", prod, "Bloque", cant))
            conn.commit()
            st.success("Kardex actualizado.")

elif menu == "🍽️ Tajado":
    st.header("🍽️ Tajado y Merma")
    with st.form("f_t", clear_on_submit=True):
        q = st.selectbox("Queso:", ["Mozzarella", "Sábana", "Pera", "Cheddar", "Doble Crema"])
        bl = st.number_input("Bloques (2.5kg):", min_value=0, step=1)
        por = st.selectbox("Porción:", ["125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g"])
        if st.form_submit_button("Tajar"):
            merma = bl * 0.200
            neto = (bl * 2.5) - merma
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (q + " Tajado", por, q + " Tajado", por, neto))
            conn.commit()
            st.warning(f"Merma: {merma}kg | Neto: {neto}kg registrados.")

elif menu == "📊 Silos (10k)":
    st.header("📊 Nivel de Silos")
    conn = get_db_connection()
    df_s = pd.read_sql_query("SELECT * FROM silos", conn)
    cols = st.columns(4)
    for i, row in df_s.iterrows():
        cols[i].metric(row['nombre'], f"{row['saldo']:.0f} L")
        cols[i].progress(min(row['saldo']/10000, 1.0))
