import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from fpdf import FPDF
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Planta Maestro")

def get_db_connection():
    conn = sqlite3.connect('suiza_v17_final.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Proveedores con todos los campos solicitados
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, cedula TEXT, ciudad TEXT,
                  valor_litro REAL, ciclo TEXT, fedegan_bool INTEGER)''')
    # Recibo de Leche (Sin decimales)
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros INTEGER, precio REAL, silo TEXT)')
    # Silos 10.000 Litros
    c.execute('CREATE TABLE IF NOT EXISTS silos (nombre TEXT PRIMARY KEY, saldo REAL)')
    # Kardex para Inventario
    c.execute('CREATE TABLE IF NOT EXISTS kardex (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    # Registro de Tajado
    c.execute('CREATE TABLE IF NOT EXISTS log_tajado (id INTEGER PRIMARY KEY, fecha TEXT, producto TEXT, bloques INTEGER, merma REAL, neto REAL)')
    
    for s in ["Silo 1", "Silo 2", "Silo 3", "Silo 4"]:
        c.execute('INSERT OR IGNORE INTO silos VALUES (?, 0)', (s,))
    conn.commit()
    conn.close()

init_db()

# --- GENERADOR DE VOLANTE PDF PROFESIONAL ---
def generar_volante_pdf(p_data, historial):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado / Logo
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "LÁCTEOS SUIZA S.A.S.", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 7, "VOLANTE DE PAGO DE LECHE", ln=True, align='C')
    pdf.ln(5)
    
    # Bloque de Información General (Organizado)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(30, 8, "FECHA:", 1, 0, 'L', True); pdf.cell(65, 8, f"{date.today()}", 1)
    pdf.cell(30, 8, "CIUDAD:", 1, 0, 'L', True); pdf.cell(65, 8, f"{p_data['ciudad']}", 1, ln=True)
    pdf.cell(30, 8, "PROVEEDOR:", 1, 0, 'L', True); pdf.cell(65, 8, f"{p_data['nombre']}", 1)
    pdf.cell(30, 8, "CÓDIGO:", 1, 0, 'L', True); pdf.cell(65, 8, f"{p_data['codigo']}", 1, ln=True)
    pdf.cell(30, 8, "FINCA:", 1, 0, 'L', True); pdf.cell(160, 8, f"{p_data['finca']}", 1, ln=True)
    pdf.ln(5)
    
    # Tabla de Detalle de Leche
    pdf.set_font("Arial", 'B', 10)
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
    # Retención 1.5% tras tope 3.6M
    rete = (subtotal - fede) * 0.015 if (subtotal - fede) > 3666000 else 0
    total = subtotal - fede - rete
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 8, "SUBTOTAL BRUTO:", 0, 0, 'R'); pdf.cell(50, 8, f"${subtotal:,.0f}", 1, 1, 'R')
    pdf.cell(140, 8, "DCTO. FEDEGAN (0.75%):", 0, 0, 'R'); pdf.cell(50, 8, f"-${fede:,.0f}", 1, 1, 'R')
    pdf.cell(140, 8, "RETENCIÓN FUENTE:", 0, 0, 'R'); pdf.cell(50, 8, f"-${rete:,.0f}", 1, 1, 'R')
    pdf.set_font("Arial", 'B', 13)
    pdf.set_fill_color(255, 255, 150)
    pdf.cell(140, 10, "TOTAL NETO A PAGAR:", 0, 0, 'R'); pdf.cell(50, 10, f"${total:,.0f}", 1, 1, 'R', True)
    
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR ---
st.sidebar.image("logo_suiza.png", width=150)
menu = st.sidebar.selectbox("MENÚ PLANTA:", [
    "🆕 Nuevo Proveedor", 
    "🥛 Ingreso de Leche", 
    "💰 Liquidación y Volantes", 
    "📊 Silos (10k L)", 
    "🏭 Producción", 
    "🍽️ Tajado"
])

# --- 1. NUEVO PROVEEDOR ---
if menu == "🆕 Nuevo Proveedor":
    st.header("🆕 Registro (Salto con Enter)")
    with st.form("f_p", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cod = c1.text_input("1. Código (Enter)")
        nom = c2.text_input("2. Nombre Proveedor (Enter)")
        finca = c1.text_input("3. Finca (Enter)")
        ced = c2.text_input("4. Cédula (Enter)")
        ciu = c1.text_input("5. Ciudad/Municipio (Enter)")
        val = c2.number_input("6. Valor Litro (Enter)", value=1850.0)
        ciclo = st.selectbox("7. Ciclo de Pago", ["Semanal", "Quincenal"])
        fede = st.checkbox("Aplica Fedegán (0.75%)")
        if st.form_submit_button("✅ GUARDAR"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?,?,?,?)', (cod, nom, finca, ced, ciu, val, ciclo, 1 if fede else 0))
            conn.commit()
            st.success("Proveedor Guardado.")

# --- 2. INGRESO DE LECHE (LIMPIEZA TOTAL) ---
elif menu == "🥛 Ingreso de Leche":
    st.header("🥛 Recibo de Leche (Limpia al Guardar)")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    
    with st.form("f_recibo", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        p_sel = col1.selectbox("1. Código / Nombre", [""] + list(provs['codigo'] + " - " + provs['nombre']) if not provs.empty else [""])
        # value=None hace que el campo aparezca en blanco
        lts = col2.number_input("2. Cantidad de Litros", min_value=0, step=1, value=None, placeholder="Ingrese Litros")
        p_hoy = col3.number_input("3. Cambio de Precio", value=1850.0)
        silo = st.selectbox("4. Silo Destino", ["Silo 1", "Silo 2", "Silo 3", "Silo 4"])
        
        if st.form_submit_button("🚀 REGISTRAR E INGRESA SIGUIENTE"):
            if p_sel != "" and lts is not None:
                cod_p = p_sel.split(" - ")[0]
                conn.execute('UPDATE silos SET saldo = saldo + ? WHERE nombre = ?', (lts, silo))
                conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, precio, silo) VALUES (?,?,?,?,?)', (str(date.today()), cod_p, int(lts), p_hoy, silo))
                conn.commit()
                st.success("Registrado correctamente. Campos limpios para nuevo ingreso.")
                st.rerun()

# --- 3. LIQUIDACIÓN E IMPRESIÓN ---
elif menu == "💰 Liquidación y Volantes":
    st.header("💰 Liquidación y Volantes PDF")
    ciclo_sel = st.radio("Ver Ciclo:", ["Semanal", "Quincenal"], horizontal=True)
    conn = get_db_connection()
    query = f'''SELECT p.*, SUM(r.litros) as total_lts FROM recibo_leche r 
               JOIN proveedores p ON r.cod_prov = p.codigo WHERE p.ciclo = '{ciclo_sel}' GROUP BY p.codigo'''
    df = pd.read_sql_query(query, conn)
    
    if not df.empty:
        st.dataframe(df[['codigo', 'nombre', 'finca', 'total_lts']], use_container_width=True)
        st.divider()
        st.subheader("🖨️ Selección para Volante Individual")
        p_escogido = st.selectbox("Elija Proveedor de la lista:", df['nombre'])
        
        if st.button("📄 Generar Volante PDF Organizado"):
            p_data = df[df['nombre'] == p_escogido].iloc[0].to_dict()
            hist = pd.read_sql_query(f"SELECT fecha, litros, precio FROM recibo_leche WHERE cod_prov = '{p_data['codigo']}'", conn)
            pdf_bytes = generar_volante_pdf(p_data, hist)
            st.download_button(f"📥 Descargar e Imprimir Volante - {p_escogido}", pdf_bytes, f"Volante_{p_escogido}.pdf", "application/pdf")
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
        s_u = st.selectbox("Silo Origen:", ["Silo 1", "Silo 2", "Silo 3", "Silo 4"])
        lts_u = st.number_input("Litros usados:", min_value=0)
        prod = st.selectbox("Variedad a Transformar:", variedades)
        cant = st.number_input("Cantidad final (Kg/Und):", min_value=0.0)
        if st.form_submit_button("Guardar y Cargar a Kardex"):
            conn = get_db_connection()
            conn.execute('UPDATE silos SET saldo = saldo - ? WHERE nombre = ?', (lts_u, s_u))
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (prod, "Bloque", prod, "Bloque", cant))
            conn.commit()
            st.success("Producción ingresada.")

# --- 5. TAJADO ---
elif menu == "🍽️ Tajado":
    st.header("🍽️ Proceso de Tajado")
    with st.form("f_t", clear_on_submit=True):
        q = st.selectbox("Queso a Tajar:", ["Mozzarella", "Sábana", "Pera", "Cheddar", "Doble Crema"])
        bl = st.number_input("Número de Bloques (2.5kg):", min_value=0, step=1)
        por = st.selectbox("Porción final:", ["125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g"])
        if st.form_submit_button("⚖️ Tajar y Registrar"):
            merma = bl * 0.200
            neto = (bl * 2.5) - merma
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (q + " Tajado", por, q + " Tajado", por, neto))
            conn.commit()
            st.warning(f"Merma: {merma}kg | Neto: {neto}kg registrados en Kardex.")

# --- 6. SILOS VISUAL ---
elif menu == "📊 Silos (10k L)":
    st.header("📊 Nivel de Silos")
    conn = get_db_connection()
    df_s = pd.read_sql_query("SELECT * FROM silos", conn)
    cols = st.columns(4)
    for i, row in df_s.iterrows():
        cols[i].metric(row['nombre'], f"{row['saldo']:.0f} L")
        cols[i].progress(min(row['saldo']/10000, 1.0))
