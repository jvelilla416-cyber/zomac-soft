import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Planta Central")

def get_db_connection():
    conn = sqlite3.connect('suiza_planta_v14.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, cedula TEXT, 
                  fedegan_bool INTEGER, valor_litro REAL, ciclo TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros INTEGER, precio_pactado REAL, silo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS silos (nombre TEXT PRIMARY KEY, saldo REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS kardex (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    c.execute('CREATE TABLE IF NOT EXISTS log_tajado (id INTEGER PRIMARY KEY, fecha TEXT, producto TEXT, bloques INTEGER, merma REAL, neto REAL)')
    for s in ["Silo 1", "Silo 2", "Silo 3", "Silo 4"]:
        c.execute('INSERT OR IGNORE INTO silos VALUES (?, 0)', (s,))
    conn.commit()
    conn.close()

init_db()

# --- FUNCIONES DE IMPRESIÓN (PDF) ---
def generar_pdf_volante(datos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "LÁCTEOS SUIZA - VOLANTE DE PAGO", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Fecha: {date.today()}", ln=True)
    pdf.cell(200, 10, f"Proveedor: {datos['nombre']} ({datos['codigo']})", ln=True)
    pdf.cell(200, 10, f"Finca: {datos['finca']}", ln=True)
    pdf.cell(200, 10, f"Litros Puestos: {datos['total_lts']}", ln=True)
    pdf.cell(200, 10, f"Valor Litro: ${datos['precio_avg']:,.2f}", ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, f"Subtotal: ${datos['Subtotal']:,.0f}", ln=True)
    pdf.cell(200, 10, f"Descuento Fedegan (0.75%): -${datos['Fedegan']:,.0f}", ln=True)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, f"TOTAL A PAGAR: ${datos['Neto_Pagar']:,.0f}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR ---
st.sidebar.title("🥛 LÁCTEOS SUIZA")
menu = st.sidebar.selectbox("Módulo Planta:", [
    "🆕 Nuevo Proveedor", 
    "🥛 Ingreso de Leche", 
    "📊 Silos (10.000L)",
    "💰 Liquidación y Volantes",
    "🏭 Producción", 
    "🍽️ Tajado y Merma",
    "📦 Kardex"
])

# --- 1. NUEVO PROVEEDOR ---
if menu == "🆕 Nuevo Proveedor":
    st.header("🆕 Registro de Proveedores")
    with st.form("f_p", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cod = c1.text_input("Código")
        nom = c2.text_input("Nombre Completo")
        finca = c3.text_input("Nombre Finca")
        ced = c1.text_input("Cédula / NIT")
        val = c2.number_input("Valor Litro Base ($)", value=1850.0)
        ciclo = c3.selectbox("Ciclo de Pago", ["Semanal", "Quincenal"])
        fede = st.checkbox("Aplica Fedegán (0.75%)")
        if st.form_submit_button("✅ Guardar Proveedor"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?,?,?)', (cod, nom, finca, ced, 1 if fede else 0, val, ciclo))
            conn.commit()
            st.success("Proveedor guardado.")

# --- 2. INGRESO DE LECHE (CON LIMPIEZA AUTOMÁTICA) ---
elif menu == "🥛 Ingreso de Leche":
    st.header("🥛 Ingreso de Leche")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    
    with st.form("f_recibo", clear_on_submit=True):
        p_sel = st.selectbox("Proveedor", ["Seleccione..."] + list(provs['codigo'] + " - " + provs['nombre']) if not provs.empty else [])
        lts = st.number_input("Cantidad de Litros (Enteros)", min_value=0, step=1, value=0)
        silo = st.selectbox("Silo Destino", ["Silo 1", "Silo 2", "Silo 3", "Silo 4"])
        
        p_final = st.number_input("Cambio de precio (opcional)", value=1850.0)
        
        if st.form_submit_button("🚀 Registrar y Limpiar"):
            if p_sel != "Seleccione...":
                cod_p = p_sel.split(" - ")[0]
                conn.execute('UPDATE silos SET saldo = saldo + ? WHERE nombre = ?', (lts, silo))
                conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, precio_pactado, silo) VALUES (?,?,?,?,?)', (str(date.today()), cod_p, lts, p_final, silo))
                conn.commit()
                st.success(f"Ingreso exitoso. Formulario listo para el siguiente.")
            else:
                st.error("Debe seleccionar un proveedor.")

# --- 3. LIQUIDACIÓN Y VOLANTES ---
elif menu == "💰 Liquidación y Volantes":
    st.header("💰 Liquidación de Pagos")
    ciclo_sel = st.radio("Ciclo:", ["Semanal", "Quincenal"], horizontal=True)
    conn = get_db_connection()
    query = f'''SELECT p.*, SUM(r.litros) as total_lts, AVG(r.precio_pactado) as precio_avg 
               FROM recibo_leche r JOIN proveedores p ON r.cod_prov = p.codigo 
               WHERE p.ciclo = '{ciclo_sel}' GROUP BY p.codigo'''
    df = pd.read_sql_query(query, conn)
    
    if not df.empty:
        df['Subtotal'] = df['total_lts'] * df['precio_avg']
        df['Fedegan'] = df.apply(lambda x: x['Subtotal'] * 0.0075 if x['fedegan_bool'] == 1 else 0, axis=1)
        df['Neto_Pagar'] = df['Subtotal'] - df['Fedegan']
        
        st.dataframe(df[['codigo', 'nombre', 'finca', 'total_lts', 'precio_avg', 'Fedegan', 'Neto_Pagar']], use_container_width=True)
        
        st.divider()
        st.subheader("🖨️ Generar Volante Individual")
        p_vol = st.selectbox("Seleccione Proveedor para Liquidar:", df['nombre'])
        if st.button("📥 Descargar Volante PDF"):
            row = df[df['nombre'] == p_vol].to_dict('records')[0]
            pdf_data = generar_pdf_volante(row)
            st.download_button(label="Click para Guardar e Imprimir", data=pdf_data, file_name=f"Volante_{p_vol}.pdf", mime="application/pdf")
    else:
        st.info("No hay registros.")

# --- 4. TAJADO Y MERMA (CON REGISTRO DE IMPRESIÓN) ---
elif menu == "🍽️ Tajado y Merma":
    st.header("🍽️ Proceso de Tajado")
    with st.form("f_taja", clear_on_submit=True):
        queso = st.selectbox("Tipo de Queso:", ["Mozzarella", "Sábana", "Pera", "Doble Crema", "Cheddar"])
        bloques = st.number_input("Bloques de 2.5kg", min_value=0, step=1)
        pres_sal = st.selectbox("Porción:", ["125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g"])
        
        if st.form_submit_button("⚖️ Ejecutar y Generar Registro"):
            merma = bloques * 0.200
            neto = (bloques * 2.5) - merma
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (queso + " Tajado", pres_sal, queso + " Tajado", pres_sal, neto))
            conn.execute('INSERT INTO log_tajado (fecha, producto, bloques, merma, neto) VALUES (?,?,?,?,?)', (str(date.today()), queso, bloques, merma, neto))
            conn.commit()
            st.success(f"Tajado Exitoso. Merma: {merma}kg | Neto: {neto}kg")
            st.info(f"Registro guardado. Puede consultarlo en el Kardex o reportes.")

# --- 5. SILOS (10.000L) ---
elif menu == "📊 Silos (10.000L)":
    st.header("📊 Nivel de Silos")
    conn = get_db_connection()
    df_s = pd.read_sql_query("SELECT * FROM silos", conn)
    cols = st.columns(4)
    for i, row in df_s.iterrows():
        cols[i].metric(row['nombre'], f"{row['saldo']:.0f} L")
        cols[i].progress(min(row['saldo']/10000, 1.0))

# --- 6. PRODUCCIÓN ---
elif menu == "🏭 Producción":
    st.header("🏭 Transformación")
    variedades = ["Queso Costeño Pasteurizado", "Queso Mozzarella", "Queso Pera", "Queso Sábana", "Queso Costeño Industrializado", "Queso Cheddar", "Suero Costeño", "Yogurt (Vaso)", "Yogurt (Bolsa)", "Arequipe", "Quesadillo"]
    with st.form("f_p"):
        s_u = st.selectbox("Silo:", ["Silo 1", "Silo 2", "Silo 3", "Silo 4"])
        lts_u = st.number_input("Litros usados:", min_value=0)
        p_f = st.selectbox("Producto:", variedades)
        pre_f = st.selectbox("Presentación:", ["Bloque 2.5Kg", "Bloque 5Kg", "Litro", "Vaso"])
        cant_f = st.number_input("Cantidad sacada:", min_value=0.0)
        if st.form_submit_button("Guardar Producción"):
            conn = get_db_connection()
            conn.execute('UPDATE silos SET saldo = saldo - ? WHERE nombre = ?', (lts_u, s_u))
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (p_f, pre_f, p_f, pre_f, cant_f))
            conn.commit()
            st.success("Kardex actualizado.")

elif menu == "📦 Kardex":
    st.header("📦 Inventario Actual")
    conn = get_db_connection()
    st.dataframe(pd.read_sql_query("SELECT * FROM kardex WHERE stock > 0", conn), use_container_width=True)
