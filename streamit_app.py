import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Planta")

def get_db_connection():
    conn = sqlite3.connect('zomac_planta_v2.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- MOTOR DE DATOS ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, precio_base REAL, fedegan INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_dia REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS kardex (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    c.execute('CREATE TABLE IF NOT EXISTS produccion_log (id INTEGER PRIMARY KEY, fecha TEXT, litros_usados REAL, producto_resultado TEXT, cantidad_obtenida REAL)')
    conn.commit()
    conn.close()

init_db()

# --- INTERFAZ ---
st.sidebar.image("logo_suiza.png", width=150)
st.sidebar.title("🥛 MÓDULO PLANTA")

menu = st.sidebar.selectbox("Seleccione:", ["👥 Proveedores", "🥛 Recibo Leche", "🏭 Producción (Transformación)", "📦 Kardex (Inventario)", "🍽️ Tajado y Merma"])

# --- 1. PROVEEDORES ---
if menu == "👥 Proveedores":
    st.header("👥 Maestros de Proveedores")
    with st.form("form_p", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cod = c1.text_input("Código")
        nom = c2.text_input("Nombre")
        pre = c1.number_input("Precio Base", value=1850)
        fed = c2.checkbox("Descuento Fedegán")
        if st.form_submit_button("✅ Guardar Proveedor"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?)', (cod, nom, pre, 1 if fed else 0))
            conn.commit()
            st.success("Guardado.")
    
    st.subheader("📋 Relación de Proveedores")
    conn = get_db_connection()
    df_p = pd.read_sql_query("SELECT * FROM proveedores", conn)
    st.dataframe(df_p, use_container_width=True)

# --- 2. RECIBO DE LECHE ---
elif menu == "🥛 Recibo Leche":
    st.header("🥛 Ingreso de Leche Diario")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    with st.form("form_l", clear_on_submit=True):
        p_sel = st.selectbox("Código Proveedor", provs['codigo'] if not provs.empty else ["Cree un proveedor primero"])
        lts = st.number_input("Litros recibidos", min_value=0.0)
        p_hoy = st.number_input("Precio hoy ($)", value=1850.0)
        if st.form_submit_button("🚀 Registrar Entrada"):
            conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, precio_dia) VALUES (?,?,?,?)', 
                         (str(date.today()), p_sel, lts, p_hoy))
            conn.commit()
            st.success("Litraje guardado.")

# --- 3. PRODUCCIÓN (TRANSFORMACIÓN) ---
elif menu == "🏭 Producción (Transformación)":
    st.header("🏭 Transformación de Materia Prima")
    variedades = ["Queso Costeño", "Yogurt", "Cuajada", "Cheddar", "Parmesano", "Palmita", "Suero Costeño", "Arequipe", "Quesillo", "Queso Pera"]
    presentaciones = ["125g", "250g", "500g", "1000g", "2500g", "5000g"]
    
    with st.form("form_prod", clear_on_submit=True):
        col1, col2 = st.columns(2)
        lts_uso = col1.number_input("Litros de leche utilizados hoy", min_value=0.0)
        p_sacado = col2.selectbox("¿Qué producto fabricó?", variedades)
        pres_sacada = col1.selectbox("Presentación", presentaciones)
        cant_obtenida = col2.number_input("Cantidad obtenida (Kg o Unidades)", min_value=0.0)
        
        if st.form_submit_button("⚙️ Procesar y Cargar a Kardex"):
            conn = get_db_connection()
            # Guardar log de producción
            conn.execute('INSERT INTO produccion_log (fecha, litros_usados, producto_resultado, cantidad_obtenida) VALUES (?,?,?,?)',
                         (str(date.today()), lts_uso, p_sacado, cant_obtenida))
            # Actualizar Kardex (Suma al stock)
            c = conn.cursor()
            c.execute('SELECT stock FROM kardex WHERE producto=? AND presentacion=?', (p_sacado, pres_sacada))
            row = c.fetchone()
            if row:
                nuevo_stock = row[0] + cant_obtenida
                conn.execute('UPDATE kardex SET stock=? WHERE producto=? AND presentacion=?', (nuevo_stock, p_sacado, pres_sacada))
            else:
                conn.execute('INSERT INTO kardex VALUES (?,?,?)', (p_sacado, pres_sacada, cant_obtenida))
            conn.commit()
            st.success(f"¡Éxito! Se descontaron {lts_uso}L y se sumaron {cant_obtenida} de {p_sacado} al Kardex.")

# --- 4. KARDEX ---
elif menu == "📦 Kardex (Inventario)":
    st.header("📦 Inventario de Producto Terminado")
    conn = get_db_connection()
    df_k = pd.read_sql_query("SELECT * FROM kardex", conn)
    if not df_k.empty:
        st.dataframe(df_k, use_container_width=True)
    else:
        st.info("El inventario está vacío. Registre una producción primero.")
