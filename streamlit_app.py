import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout="wide", page_title="Lácteos María Zomac - Sistema de Gestión Integrado", page_icon="🥛")

# --- URL DEL LOGO DE LA EMPRESA (Reemplazar con URL real del logo Suiza) ---
LOGO_URL = "https://i.imgur.com/8Qp4w6i.png" # Ejemplo de URL del logo Suiza

# --- ESTILOS CSS PERSONALIZADOS (MODO CLARO Y LEGIBLE DEFINITIVO) ---
st.markdown("""
<style>
    /* Estilos generales para modo CLARO (Legibilidad máxima) */
    .stApp {
        background-color: #ffffff;
        color: #000000;
    }
    /* Estilos para la barra lateral (Sidebar) - CONTRASTE MÁXIMO */
    [data-testid="stSidebar"] {
        background-color: #f0f2f6; /* Gris muy claro */
        color: #000000; /* Letras NEGRAS */
    }
    /* Asegurar que los radio buttons y textos de la barra lateral sean negros */
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        color: #000000 !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #000000 !important;
    }
    /* Estilos para los títulos y subtítulos del área principal */
    h1, h2, h3, .stHeader {
        color: #004ba0;
    }
    /* Estilos para las tarjetas de métricas */
    .stMetric {
        background-color: #f7f9fc;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #dcdcdc;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    .stMetric div[data-testid="stMetricValue"] > div {
        color: #000000;
    }
    .stMetric div[data-testid="stMetricLabel"] > div {
        color: #5f6368;
    }
    /* Estilos para las tablas (DataFrames) */
    .stDataFrame {
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #dcdcdc;
    }
    /* Estilos para los formularios y entradas de texto */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stDateInput>div>div>input, .stSelectbox>div>div>select {
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #b0bec5;
    }
    /* Estilos para los botones */
    .stButton>button {
        background-color: #1976d2;
        color: #ffffff;
        border: none;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #1565c0;
    }
</style>
""", unsafe_allow_html=True)

# --- TÍTULO PRINCIPAL ---
st.title("🥛 Sistema de Gestión Integrado - Lácteos María Zomac")

# --- CONEXIÓN A LA BASE DE DATOS (SQLITE) ---
def get_db_connection():
    conn = sqlite3.connect('lacteos_zomac.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- CREACIÓN DE TABLAS (SI NO EXISTEN) ---
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    # (Mismo código de creación de tablas que el anterior, sin cambios)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proveedores (
            id_proveedor TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            finca TEXT,
            telefono TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entrada_leche (
            id_entrada INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            id_proveedor TEXT NOT NULL,
            litros REAL NOT NULL,
            precio_litro REAL NOT NULL,
            total REAL NOT NULL,
            FOREIGN KEY (id_proveedor) REFERENCES proveedores (id_proveedor)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario_productos (
            id_producto TEXT PRIMARY KEY,
            nombre_producto TEXT NOT NULL,
            categoria TEXT,
            cantidad_kg REAL DEFAULT 0,
            precio_venta REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transformacion_diaria (
            id_transformacion INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            litros_leche_cruda_usados REAL NOT NULL,
            producto_terminado_id TEXT NOT NULL,
            cantidad_kg_producidos REAL NOT NULL,
            merma_kg REAL DEFAULT 0,
            observaciones TEXT,
            FOREIGN KEY (producto_terminado_id) REFERENCES inventario_productos (id_producto)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transformacion_slicing (
            id_slicing INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            producto_origen_id TEXT NOT NULL,
            cantidad_origen_kg REAL NOT NULL,
            producto_destino_id TEXT NOT NULL,
            cantidad_destino_kg REAL NOT NULL,
            merma_sensor_kg REAL DEFAULT 0.2,
            merma_adicional_kg REAL DEFAULT 0,
            total_merma_kg REAL NOT NULL,
            observaciones TEXT,
            FOREIGN KEY (producto_origen_id) REFERENCES inventario_productos (id_producto),
            FOREIGN KEY (producto_destino_id) REFERENCES inventario_productos (id_producto)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id_cliente TEXT PRIMARY KEY,
            nombre_completo TEXT NOT NULL,
            direccion TEXT,
            telefono TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            id_cliente TEXT NOT NULL,
            id_producto TEXT NOT NULL,
            cantidad REAL NOT NULL,
            precio_unitario REAL NOT NULL,
            total_venta REAL NOT NULL,
            FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente),
            FOREIGN KEY (id_producto) REFERENCES inventario_productos (id_producto)
        )
    """)
    conn.commit()
    conn.close()

create_tables()

# --- FUNCIONES DE AYUDA (HELPER FUNCTIONS) ---
def check_password():
    """Maneja el checkeo de contraseña con st.secrets."""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("## 🔒 Acceso al Sistema de Seguridad")
        st.text_input("Ingrese la Contraseña de Seguridad Maestra:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("## 🔒 Acceso al Sistema de Seguridad")
        st.text_input("Ingrese la Contraseña de Seguridad Maestra:", type="password", on_change=password_entered, key="password")
        st.error("😕 Contraseña incorrecta. Por favor, intente de nuevo.")
        return False
    else:
        return True

# --- AUTENTICACIÓN ---
if not check_password():
    st.stop()

# --- BARRA LATERAL (SIDEBAR) - NAVEGACIÓN (CON LOGO SUIZA Y CONTRASTE MÁXIMO) ---
with st.sidebar:
    # INTEGRACIÓN DEL LOGO DE LÁCTEOS SUIZA
    # Reemplazar con URL real del logo subido a la nube
    try:
        st.image(LOGO_URL, use_column_width=True) 
    except:
        st.image("https://via.placeholder.com/150x80.png?text=LÁCTEOS+SUIZA", use_column_width=True)
        st.warning("⚠️ Error al cargar el logo Suiza. Mostrando marcador de posición.")
    
    st.header("Navegación")
    app_mode = st.radio("Ir a:", 
        ["📊 Director del Panel (Resumen)", 
         "👥 Gestión de Proveedores",
         "🥛 Entrada de Leche Cruda", 
         "📦 Inventario de Productos Terminados",
         "🔄 Producción: Transformación",
         "🍽️ Producción: Tajado (Slicing)",
         "👥 Gestión de Clientes",
         "💰 Registro de Ventas",
         "📈 Reportes y Gráficos",
         "⚙️ Configuración"])
    
    st.markdown("---")
    # Botón de Excel desactivado temporalmente para asegurar que arranque
    # st.download_button(label="📥 Descargar Respaldo (Excel)", data=download_backup(), file_name=f'respaldo_lacteos_zomac_{date.today()}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    st.info("💡 Botón de Respaldo Excel desactivado temporalmente.")

# --- CÓDIGO DE LOS MÓDULOS (Sin cambios) ---
# MÓDULO 1: DIRECTOR DEL PANEL (RESUMEN)
if app_mode == "📊 Director del Panel (Resumen)":
    st.subheader("Resumen General del Negocio")
    col1, col2, col3, col4 = st.columns(4)
    # ... (El resto del código de los módulos es idéntico)
