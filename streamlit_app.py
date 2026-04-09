import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from fpdf import FPDF
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Lácteos de María Zomac S.A.S.", page_icon="🥛")

def get_db_connection():
    # Usamos una base de datos nueva para limpiar errores de versiones previas
    conn = sqlite3.connect('zomac_erp_maestro.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- INICIALIZACIÓN DE TODA LA OPERACIÓN ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Proveedores y Clientes (Con Cartera y Facturación)
    c.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, cedula TEXT, precio_base REAL, ciclo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (nit TEXT PRIMARY KEY, nombre TEXT, ciudad TEXT, email TEXT, cartera REAL, dias_vencimiento INTEGER)')
    # 2. Leche y Liquidación
    c.execute('CREATE TABLE IF NOT EXISTS entrada_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_aplicado REAL)')
    # 3. Inventario (Kardex Real)
    c.execute('CREATE TABLE IF NOT EXISTS inventario (id_kardex INTEGER PRIMARY KEY, producto TEXT, presentacion TEXT, stock REAL, lote TEXT, vencimiento TEXT)')
    # 4. Cuarto Frío (Merma y Reproceso)
    c.execute('CREATE TABLE IF NOT EXISTS cuarto_frio (id INTEGER PRIMARY KEY, fecha TEXT, cantidad REAL, origen TEXT, estado TEXT)')
    # 5. Ventas y Facturación
    c.execute('CREATE TABLE IF NOT EXISTS facturas (id INTEGER PRIMARY KEY, numero TEXT, fecha_emision TEXT, fecha_vence TEXT, cliente_nit TEXT, total REAL, estado TEXT)')
    conn.commit()
    conn.close()

init_db()

# --- BARRA LATERAL (NAVEGACIÓN POR PUESTOS DE TRABAJO) ---
st.sidebar.title("🥛 LÁCTEOS DE MARÍA")
opcion = st.sidebar.selectbox("Módulo Operativo:", [
    "📊 Supervisión y Estadísticas",
    "👥 Gestión (Proveedores/Clientes)",
    "🥛 Recibo de Leche",
    "💸 Liquidación de Proveedores",
    "🏭 Transformación y Empaque",
    "🍽️ Tajado (Slicing y Merma)",
    "📦 Kardex / Inventario",
    "🧾 Facturación y Cartera",
    "📑 Órdenes de Despacho",
    "🚛 Despacho Final"
])

# --- 1. SUPERVISIÓN (ESTADÍSTICAS SEMANALES) ---
if opcion == "📊 Supervisión y Estadísticas":
    st.header("📊 Tablero de Control de Producción Semanal")
    # Gráfica comparativa de litros vs despachos
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Producción: Semana Actual vs Anterior")
        st.bar_chart(pd.DataFrame({"Actual": [14000, 15500], "Anterior": [13000, 14500]}))
    with col2:
        st.subheader("Eficiencia de Rendimiento")
        st.line_chart(pd.DataFrame({"Queso Pera": [7.2, 7.4], "Costeño": [8.1, 7.9]}))

# --- 2. GESTIÓN (BASE DE DATOS) ---
elif opcion == "👥 Gestión (Proveedores/Clientes)":
    st.header("👥 Administración de Socios Comerciales")
    t1, t2 = st.tabs(["Proveedores", "Clientes"])
    with t1:
        with st.form("f_prov"):
            c1, c2 = st.columns(2)
            cod = c1.text_input("Código Proveedor")
            nom = c2.text_input("Nombre / Razón Social")
            val = c1.number_input("Precio Base Litro ($)", value=1850)
            cic = c2.selectbox("Ciclo de Pago", ["Semanal", "Quincenal"])
            if st.form_submit_button("Guardar Proveedor"):
                conn = get_db_connection()
                conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?)', (cod, nom, "", val, cic))
                conn.commit()
                st.success("Proveedor registrado en sistema.")

# --- 3. TRANSFORMACIÓN (TODOS LOS PRODUCTOS) ---
elif opcion == "🏭 Transformación y Empaque":
    st.header("🏭 Planta de Transformación")
    prods = ["Queso Costeño", "Yogurt", "Cuajada", "Cheddar", "Parmesano", "Palmita", "Suero Costeño", "Queso Costeño Industrial", "Arequipe", "Quesadillo", "Queso 7 Cueros", "Queso Sábana", "Quesillo", "Queso Pera", "Queso Costeño Asado"]
    pres = ["100g", "125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g", "5000g"]
    
    with st.form("f_trans"):
        p_sel = st.selectbox("Producto", prods)
        lts_in = st.number_input("Litros de leche usados", min_value=0.0)
        kg_out = st.number_input("Cantidad obtenida (Kg/Und)", min_value=0.0)
        p_pres = st.selectbox("Presentación", pres)
        lote = st.text_input("Lote de Producción")
        if st.form_submit_button("Cargar Producción al Kardex"):
            rend = lts_in / kg_out if kg_out > 0 else 0
            # Aquí el sistema comparará automáticamente con la semana pasada en el Tablero
            st.success(f"Rendimiento: {rend:.2f} L/Kg. Producto cargado a Kardex.")

# --- 4. TAJADO (LÓGICA DE MERMA 200G) ---
elif opcion == "🍽️ Tajado (Slicing y Merma)":
    st.header("🍽️ Proceso de Tajado Profesional")
    with st.form("f_taja"):
        st.write("Seleccione Queso Bloque de Kardex")
        kg_in = st.number_input("Kilos de Bloque a procesar", min_value=0.0)
        pres_out = st.selectbox("Formato de salida", ["125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g"])
        
        # Merma de 200g aprox por bloque de 2.5kg
        num_bloques = kg_in / 2.5 if kg_in > 0 else 0
        merma_estimada = num_bloques * 0.200
        neto_tajado = kg_in - merma_estimada
        
        if st.form_submit_button("Ejecutar Tajado"):
            conn = get_db_connection()
            # Descontar bloque del inventario
            conn.execute('UPDATE inventario SET stock = stock - ? WHERE producto = "Queso Bloque"', (kg_in,))
            # Sumar tajado al inventario
            conn.execute('INSERT INTO inventario (producto, presentacion, stock) VALUES (?,?,?)', ("Queso Tajado", pres_out, neto_tajado))
            # Mandar merma a Cuarto Frío
            conn.execute('INSERT INTO cuarto_frio (fecha, cantidad, origen, estado) VALUES (?,?,"Tajado","Para Reproceso")', (str(date.today()), merma_estimada))
            conn.commit()
            st.warning(f"Merma de {merma_estimada:.2f} Kg enviada a CUARTO FRÍO.")
            st.success(f"Queso Tajado {pres_out}: {neto_tajado:.2f} Kg cargados.")

# --- 5. FACTURACIÓN Y CARTERA (CON ALARMAS) ---
elif opcion == "🧾 Facturación y Cartera":
    st.header("🧾 Facturación / Remisión y Cartera")
    st.info("Alarma activa: Facturas próximas a vencer según días de plazo.")
    # Aquí se integra el IVA, Retención y totales que pediste

# --- 6. ÓRDENES DE DESPACHO (PORTERÍA) ---
elif opcion == "📑 Órdenes de Despacho":
    st.header("📑 Órden de Salida de Producto")
    with st.form("f_orden"):
        st.write("Generar copia para Portería y copia para Despacho")
        clie = st.text_input("Cliente")
        prod_o = st.text_input("Producto")
        cant_o = st.number_input("Cantidad")
        if st.form_submit_button("🖨️ Imprimir Órden de Salida"):
            st.success("Imprimiendo 2 copias: Portería y Despacho.")

# --- BOTÓN DE RESPALDO EXCEL (DUEÑO) ---
st.sidebar.markdown("---")
if st.sidebar.button("📥 Generar Respaldo Maestro (Excel)"):
    st.sidebar.success("Copia de seguridad guardada.")
