import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from fpdf import FPDF
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Sistema Maestro", page_icon="🥛")

# --- CONEXIÓN A DB (NUEVA PARA EVITAR ERRORES) ---
def get_db_connection():
    conn = sqlite3.connect('suiza_maestro_v1.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, precio_base REAL, fedegan INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (nit TEXT PRIMARY KEY, nombre TEXT, ciudad TEXT, cartera REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS entrada_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_dia REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT PRIMARY KEY, presentacion TEXT, stock REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS cuarto_frio (id INTEGER PRIMARY KEY, fecha TEXT, cantidad REAL, motivo TEXT)')
    conn.commit()
    conn.close()

init_db()

# --- INTERFAZ ---
st.sidebar.title("🥛 LÁCTEOS SUIZA")
# Aquí puedes poner el link de tu logo si lo subes a un host de imágenes
st.sidebar.image("https://via.placeholder.com/150", caption="Lácteos Suiza") 

opcion = st.sidebar.selectbox("Seleccione Módulo:", [
    "👥 Gestión (Prov/Clie)", 
    "🥛 Recibo de Leche", 
    "💸 Liquidación",
    "🏭 Producción y Kardex",
    "🍽️ Tajado y Merma",
    "🚛 Orden de Despacho",
    "🧾 Facturación y Despacho"
])

# --- 1. GESTIÓN (FORMULARIO QUE SE LIMPIA SOLO) ---
if opcion == "👥 Gestión (Prov/Clie)":
    st.header("👥 Registro de Proveedores y Clientes")
    t1, t2 = st.tabs(["Proveedores", "Clientes"])
    
    with t1:
        with st.form("form_proveedor", clear_on_submit=True):
            c1, c2 = st.columns(2)
            cod = c1.text_input("Código Proveedor")
            nom = c2.text_input("Nombre Completo")
            pre = c1.number_input("Precio Base Litro", value=1850)
            fed = c2.checkbox("Descuento Fedegán")
            if st.form_submit_button("✅ Guardar Proveedor"):
                conn = get_db_connection()
                conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?)', (cod, nom, pre, 1 if fed else 0))
                conn.commit()
                st.success(f"Proveedor {nom} guardado. Formulario listo para el siguiente.")

# --- 2. RECIBO DE LECHE (POR CÓDIGO) ---
elif opcion == "🥛 Recibo de Leche":
    st.header("🥛 Ingreso de Leche")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    with st.form("form_leche"):
        p_sel = st.selectbox("Código Proveedor", provs['codigo'] if not provs.empty else [])
        lts = st.number_input("Litros", min_value=0.0)
        p_sug = 1850
        if p_sel:
            p_sug = provs[provs['codigo']==p_sel]['precio_base'].values[0]
        p_hoy = st.number_input("Precio Hoy", value=float(p_sug))
        if st.form_submit_button("Registrar Entrada"):
            conn.execute('INSERT INTO entrada_leche (fecha, cod_prov, litros, precio_dia) VALUES (?,?,?,?)', 
                         (str(date.today()), p_sel, lts, p_hoy))
            conn.commit()
            st.success("Litraje guardado.")

# --- 3. LIQUIDACIÓN (TOPE 3.666.000) ---
elif opcion == "💸 Liquidación":
    st.header("💸 Liquidación de Pagos")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    p_liq = st.selectbox("Proveedor", provs['codigo'] if not provs.empty else [])
    f1 = st.date_input("Desde", date.today()-timedelta(days=7))
    f2 = st.date_input("Hasta", date.today())
    
    if st.button("Calcular Liquidación"):
        df = pd.read_sql_query(f"SELECT * FROM entrada_leche WHERE cod_prov='{p_liq}' AND fecha BETWEEN '{f1}' AND '{f2}'", conn)
        if not df.empty:
            lts_t = df['litros'].sum()
            subtotal = (df['litros'] * df['precio_dia']).sum()
            
            # --- LÓGICA DE RETENCIÓN ---
            rete = 0
            if subtotal >= 3666000:
                rete = subtotal * 0.015
            
            # --- LÓGICA FEDEGAN ---
            fed_aplica = provs[provs['codigo']==p_liq]['fedegan'].values[0]
            desc_fed = lts_t * 10 if fed_aplica else 0
            
            st.write(f"### Resumen de Pago")
            st.metric("NETO A PAGAR", f"${subtotal - rete - desc_fed:,.0f}")
            st.write(f"Subtotal: ${subtotal:,.0f} | Retención (1.5%): -${rete:,.0f} | Fedegán: -${desc_fed:,.0f}")
        else:
            st.warning("No hay datos para estas fechas.")

# --- 4. TAJADO (MERMA 200G) ---
elif opcion == "🍽️ Tajado y Merma":
    st.header("🍽️ Proceso de Tajado")
    with st.form("form_tajado"):
        kg_in = st.number_input("Kilos de Queso Bloque", min_value=0.0)
        # Merma 200g por bloque de 2.5kg
        merma = (kg_in / 2.5) * 0.200 if kg_in > 0 else 0
        neto = kg_in - merma
        if st.form_submit_button("Ejecutar Tajado"):
            conn = get_db_connection()
            conn.execute('INSERT INTO cuarto_frio (fecha, cantidad, motivo) VALUES (?,?,"Merma Tajado")', (str(date.today()), merma))
            conn.commit()
            st.warning(f"Merma de {merma:.2f}kg enviada a Cuarto Frío.")
            st.success(f"Neto de {neto:.2f}kg cargado a Kardex.")
