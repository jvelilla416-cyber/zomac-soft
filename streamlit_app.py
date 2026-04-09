import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos de María Zomac S.A.S.", page_icon="🥛")

def get_db_connection():
    # Nueva base de datos para arrancar de cero sin errores
    conn = sqlite3.connect('zomac_sistema_final_v1.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- MOTOR DE DATOS (TABLAS INDEPENDIENTES) ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Maestros
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, cedula TEXT, precio_base REAL, ciclo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (nit TEXT PRIMARY KEY, nombre TEXT, ciudad TEXT, email TEXT, dias_pago INTEGER)')
    # 2. Operación Leche
    c.execute('CREATE TABLE IF NOT EXISTS entrada_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_aplicado REAL)')
    # 3. Kardex y Cuarto Frío
    c.execute('CREATE TABLE IF NOT EXISTS inventario (id_kardex INTEGER PRIMARY KEY, producto TEXT, presentacion TEXT, stock REAL, lote TEXT, vencimiento TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS cuarto_frio (id INTEGER PRIMARY KEY, fecha TEXT, cantidad REAL, origen TEXT, motivo TEXT)')
    # 4. Facturación y Despacho
    c.execute('CREATE TABLE IF NOT EXISTS facturas (id INTEGER PRIMARY KEY, numero TEXT, fecha_emision TEXT, vence TEXT, cliente_nit TEXT, total REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS ordenes_despacho (id INTEGER PRIMARY KEY, fecha TEXT, cliente TEXT, producto TEXT, cantidad REAL)')
    
    conn.commit()
    conn.close()

init_db()

# --- NAVEGACIÓN ---
st.sidebar.title("🥛 LÁCTEOS DE MARÍA")
opcion = st.sidebar.selectbox("Seleccione el Módulo:", [
    "📊 Supervisión Dueño", "👥 Gestión (Prov/Clie)", "🥛 Recibo de Leche", 
    "💸 Liquidación de Pagos", "🏭 Transformación/Empaque", 
    "🍽️ Tajado (Slicing)", "📦 Kardex / Inventario", 
    "🧾 Facturación/Remisión", "📑 Orden de Despacho", "🚛 Despacho Final"
])

# --- MÓDULO GESTIÓN (PARA QUE PUEDAS CREAR POR CÓDIGO) ---
if opcion == "👥 Gestión (Prov/Clie)":
    st.header("👥 Administración de Base de Datos")
    t1, t2 = st.tabs(["Crear Proveedores", "Crear Clientes"])
    with t1:
        with st.form("f_prov"):
            c1, c2 = st.columns(2)
            cod = c1.text_input("Código de Proveedor (EJ: 001)")
            nom = c2.text_input("Nombre del Proveedor")
            val = c1.number_input("Precio Litro Pactado ($)", value=1850)
            cic = c2.selectbox("Ciclo de Pago", ["Semanal", "Quincenal"])
            if st.form_submit_button("✅ Guardar Proveedor"):
                if cod and nom:
                    conn = get_db_connection()
                    conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?,?)', (cod, nom, "", "", val, cic))
                    conn.commit()
                    st.success(f"Proveedor {cod} guardado correctamente.")
                else: st.error("Llene el Código y el Nombre.")

# --- MÓDULO RECIBO (POR CÓDIGO) ---
elif opcion == "🥛 Recibo de Leche":
    st.header("🥛 Ingreso de Leche por Código")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT codigo, nombre FROM proveedores", conn)
    with st.form("f_leche"):
        p_sel = st.selectbox("Seleccione Código de Proveedor", provs['codigo'] if not provs.empty else ["Cree un proveedor primero"])
        lts = st.number_input("Litros recibidos", min_value=0.0)
        p_hoy = st.number_input("Precio aplicado hoy ($)", value=1850)
        if st.form_submit_button("🚀 Registrar Ingreso"):
            conn.execute('INSERT INTO entrada_leche (fecha, cod_prov, litros, precio_aplicado) VALUES (?,?,?,?)', 
                         (str(date.today()), p_sel, lts, p_hoy))
            conn.commit()
            st.success("Litraje guardado. Ya puedes liquidarlo.")

# --- MÓDULO TAJADO (LÓGICA DE MERMA 200G) ---
elif opcion == "🍽️ Tajado (Slicing)":
    st.header("🍽️ Tajado y Merma de Bloque")
    with st.form("f_taja"):
        st.write("Se descuenta Queso Bloque del Kardex")
        kg_in = st.number_input("Peso de Bloques a tajar (Kg)", min_value=0.0)
        formato = st.selectbox("Presentación de salida", ["125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g"])
        # Merma automática de 200g por bloque de 2.5kg
        num_bloques = kg_in / 2.5 if kg_in > 0 else 0
        merma_tot = num_bloques * 0.200
        neto = kg_in - merma_tot
        
        if st.form_submit_button("Ejecutar Tajado"):
            conn = get_db_connection()
            # 1. Resta del Kardex el Bloque
            conn.execute('INSERT INTO inventario (producto, presentacion, stock) VALUES (?,?,?)', ("Queso Bloque", "Bloque", -kg_in))
            # 2. Suma al Kardex el Tajado
            conn.execute('INSERT INTO inventario (producto, presentacion, stock) VALUES (?,?,?)', ("Queso Tajado", formato, neto))
            # 3. Merma al Cuarto Frío
            conn.execute('INSERT INTO cuarto_frio (fecha, cantidad, origen, motivo) VALUES (?,?,"Tajado","Merma")', (str(date.today()), merma_tot))
            conn.commit()
            st.warning(f"Merma de {merma_tot:.2f} Kg enviada a CUARTO FRÍO.")
            st.success(f"Neto de {neto:.2f} Kg cargado a Kardex.")

# --- MÓDULO ORDEN DE DESPACHO (PORTERÍA) ---
elif opcion == "📑 Orden de Despacho":
    st.header("📑 Orden de Salida (Copia Portería)")
    with st.form("f_orden"):
        clie = st.text_input("Cliente Destino")
        prod = st.text_input("Producto")
        cant = st.number_input("Cantidad")
        if st.form_submit_button("🖨️ Imprimir Orden"):
            st.info("Generando copia para Portería y otra para Despacho...")
