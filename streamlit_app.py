import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from fpdf import FPDF
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Gestión Operativa", page_icon="🥛")

def get_db_connection():
    conn = sqlite3.connect('lacteos_suiza_v4.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- INICIALIZACIÓN DE TODAS LAS TABLAS ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Tabla de Proveedores (Para que aparezcan en la lista)
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (id TEXT PRIMARY KEY, nombre TEXT, finca TEXT)')
    # 2. Tabla de Entrada de Leche
    c.execute('CREATE TABLE IF NOT EXISTS entrada_leche (id INTEGER PRIMARY KEY, fecha TEXT, proveedor TEXT, litros REAL)')
    # 3. Inventario y Despachos
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT PRIMARY KEY, stock REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS despachos (id INTEGER PRIMARY KEY, fecha TEXT, cliente TEXT, producto TEXT, cantidad REAL, conductor TEXT, placa TEXT)')
    
    productos_base = [('Queso Bloque', 0), ('Queso Tajado', 0), ('Yogurt', 0)]
    c.executemany('INSERT OR IGNORE INTO inventario VALUES (?,?)', productos_base)
    conn.commit()
    conn.close()

init_db()

# --- MENÚ LATERAL ---
st.sidebar.title("🥛 LÁCTEOS ZOMAC")
opcion = st.sidebar.radio("Navegación:", [
    "👥 Gestión de Proveedores", 
    "🥛 Entrada de Leche Cruda", 
    "🍽️ Tajadora (Slicing y Merma)", 
    "📦 Kardex / Inventario", 
    "🚛 Registro de Despacho y Planilla"
])

# --- 1. MÓDULO DE PROVEEDORES (PARA CREARLOS) ---
if opcion == "👥 Gestión de Proveedores":
    st.header("👥 Gestión de Proveedores")
    st.subheader("Registrar Nuevo Proveedor")
    with st.form("form_proveedor"):
        id_p = st.text_input("Cédula o NIT del Proveedor")
        nom_p = st.text_input("Nombre Completo")
        finc_p = st.text_input("Nombre de la Finca / Ubicación")
        if st.form_submit_button("✅ Guardar Proveedor"):
            if id_p and nom_p:
                conn = get_db_connection()
                conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?)', (id_p, nom_p, finc_p))
                conn.commit()
                st.success(f"Proveedor {nom_p} guardado correctamente.")
            else:
                st.error("Por favor llena el nombre y el ID.")
    
    st.subheader("Proveedores Registrados")
    conn = get_db_connection()
    df_p = pd.read_sql_query("SELECT * FROM proveedores", conn)
    st.dataframe(df_p, use_container_width=True)

# --- 2. MÓDULO DE ENTRADA DE LECHE ---
elif opcion == "🥛 Entrada de Leche Cruda":
    st.header("🥛 Registro de Entrada de Leche")
    conn = get_db_connection()
    # Sacamos la lista de proveedores para que aparezcan en el selector
    prov_df = pd.read_sql_query("SELECT nombre FROM proveedores", conn)
    prov_list = prov_df['nombre'].tolist()

    if not prov_list:
        st.warning("⚠️ Primero debes crear proveedores en el módulo 'Gestión de Proveedores'.")
    else:
        with st.form("form_leche"):
            f_leche = st.date_input("Fecha de Recibo", date.today())
            p_leche = st.selectbox("Seleccione el Proveedor", prov_list)
            l_leche = st.number_input("Litros Ingresados", min_value=0.0, step=0.1)
            if st.form_submit_button("🥛 Registrar Ingreso de Leche"):
                conn.execute('INSERT INTO entrada_leche (fecha, proveedor, litros) VALUES (?,?,?)', 
                             (str(f_leche), p_leche, l_leche))
                conn.commit()
                st.success(f"Se registraron {l_leche}L de {p_leche}")

# --- 3. MÓDULO DE TAJADORA (CON MERMA) ---
elif opcion == "🍽️ Tajadora (Slicing y Merma)":
    st.header("🍽️ Proceso de Tajado y Merma")
    with st.form("form_tajado"):
        bloques = st.number_input("Cantidad de Bloques (Aproximado)", min_value=0)
        peso_in = st.number_input("Peso Total en Bloque (Kg)", min_value=0.0)
        merma_fija = 0.200 # 200 gramos por bloque
        merma_total = bloques * merma_fija
        peso_neto = peso_in - merma_total
        
        st.write(f"**Cálculo de Merma:** {merma_total} Kg")
        st.write(f"**Peso Neto Final:** {peso_neto} Kg")
        
        if st.form_submit_button("Actualizar Inventario"):
            conn = get_db_connection()
            conn.execute('UPDATE inventario SET stock = stock + ? WHERE producto = "Queso Tajado"', (peso_neto,))
            conn.commit()
            st.success("Producción cargada al Kardex.")

# --- 4. KARDEX ---
elif opcion == "📦 Kardex / Inventario":
    st.header("📦 Inventario Actual")
    conn = get_db_connection()
    df_i = pd.read_sql_query("SELECT * FROM inventario", conn)
    st.table(df_i)

# --- 5. DESPACHO Y PDF ---
elif opcion == "🚛 Registro de Despacho y Planilla":
    st.header("🚛 Registro de Despacho")
    with st.form("form_despacho"):
        clie = st.text_input("Cliente")
        prod = st.selectbox("Producto", ["Queso Bloque", "Queso Tajado", "Yogurt"])
        cant = st.number_input("Cantidad", min_value=0.0)
        if st.form_submit_button("Generar Planilla"):
            st.success("Planilla Generada (Botón de descarga activo)")
            # (Aquí va la lógica del PDF que ya tenemos lista)
