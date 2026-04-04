import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout="wide", page_title="Lácteos María Zomac - Sistema de Gestión Integrado", page_icon="🥛")

# --- ESTILOS CSS PERSONALIZADOS (MODO OSCURO) ---
st.markdown("""
<style>
    /* Estilos generales para modo oscuro */
    .stApp {
        background-color: #121212;
        color: #e0e0e0;
    }
    /* Estilos para la barra lateral (Sidebar) */
    [data-testid="stSidebar"] {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }
    /* Estilos para los títulos y subtítulos */
    h1, h2, h3, .stHeader {
        color: #90caf9;
    }
    /* Estilos para las tarjetas de métricas */
    .stMetric {
        background-color: #262626;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    .stMetric div[data-testid="stMetricValue"] > div {
        color: #fff;
    }
    .stMetric div[data-testid="stMetricLabel"] > div {
        color: #b0bec5;
    }
    /* Estilos para las tablas (DataFrames) */
    .stDataFrame {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #333;
    }
    /* Estilos para los formularios y entradas de texto */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stDateInput>div>div>input, .stSelectbox>div>div>select {
        background-color: #333;
        color: #fff;
        border: 1px solid #555;
    }
    /* Estilos para los botones */
    .stButton>button {
        background-color: #1976d2;
        color: #fff;
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
    
    # Tabla de Proveedores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proveedores (
            id_proveedor TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            finca TEXT,
            telefono TEXT
        )
    """)
    
    # Tabla de Entrada de Leche Cruda
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
    
    # Tabla de Inventario de Productos Terminados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario_productos (
            id_producto TEXT PRIMARY KEY,
            nombre_producto TEXT NOT NULL,
            categoria TEXT,
            cantidad_kg REAL DEFAULT 0,
            precio_venta REAL
        )
    """)
    
    # Tabla de Transformación Diaria (Leche a Queso)
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
    
    # Tabla de Transformación por Slicing (Bloque a Tajado/Porcionado)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transformacion_slicing (
            id_slicing INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            producto_origen_id TEXT NOT NULL,
            cantidad_origen_kg REAL NOT NULL,
            producto_destino_id TEXT NOT NULL,
            cantidad_destino_kg REAL NOT NULL,
            merma_sensor_kg REAL DEFAULT 0.2, -- Merma fija de 200g por bloque
            merma_adicional_kg REAL DEFAULT 0,
            total_merma_kg REAL NOT NULL,
            observaciones TEXT,
            FOREIGN KEY (producto_origen_id) REFERENCES inventario_productos (id_producto),
            FOREIGN KEY (producto_destino_id) REFERENCES inventario_productos (id_producto)
        )
    """)

    # Tabla de Clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id_cliente TEXT PRIMARY KEY,
            nombre_completo TEXT NOT NULL,
            direccion TEXT,
            telefono TEXT
        )
    """)
    
    # Tabla de Registro de Ventas
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
    """Returns True if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        st.error("😕 Contraseña incorrecta")
        return False
    else:
        return True

# --- BARRA LATERAL (SIDEBAR) - NAVEGACIÓN ---
with st.sidebar:
    st.image("https://via.placeholder.com/150x80.png?text=MZ", width=100) # Reemplazar con logo real
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
         "⚙️ Configuración"]) # Se quitó 'Respaldo'
    
    st.markdown("---")
    # SE DESACTIVÓ EL BOTÓN DE EXCEL TEMPORALMENTE PARA ARRANCAR
    # st.download_button(label="📥 Descargar Respaldo (Excel)", data=download_backup(), file_name=f'respaldo_lacteos_zomac_{date.today()}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    st.info("💡 Botón de Respaldo Excel desactivado temporalmente.")

# --- AUTENTICACIÓN ---
if not check_password():
    st.stop()

# --- CÓDIGO DE LOS MÓDULOS ---

# MÓDULO 1: DIRECTOR DEL PANEL (RESUMEN)
if app_mode == "📊 Director del Panel (Resumen)":
    st.subheader("Resumen General del Negocio")
    col1, col2, col3, col4 = st.columns(4)
    
    conn = get_db_connection()
    
    with col1:
        total_proveedores = conn.execute("SELECT COUNT(*) FROM proveedores").fetchone()[0]
        st.metric(label="Proveedores Registrados", value=total_proveedores)
        
    with col2:
        litros_hoy = conn.execute(f"SELECT SUM(litros) FROM entrada_leche WHERE fecha='{date.today()}'").fetchone()[0]
        st.metric(label="Litros Recibidos Hoy", value=litros_hoy if litros_hoy else 0)
        
    with col3:
        total_productos = conn.execute("SELECT COUNT(*) FROM inventario_productos").fetchone()[0]
        st.metric(label="Productos Registrados", value=total_productos)

    with col4:
        ventas_hoy = conn.execute(f"SELECT SUM(total_venta) FROM ventas WHERE fecha='{date.today()}'").fetchone()[0]
        st.metric(label="Ventas Hoy (COP)", value=f"${ventas_hoy:,.0f}" if ventas_hoy else "$0")
        
    st.markdown("---")
    
    # Alertas de Inventario Bajo
    st.subheader("⚠️ Alertas de Inventario Bajo (kg)")
    inventario_bajo = pd.read_sql_query("SELECT id_producto, nombre_producto, cantidad_kg FROM inventario_productos WHERE cantidad_kg < 10", conn)
    if not inventario_bajo.empty:
        st.dataframe(inventario_bajo, use_container_width=True)
    else:
        st.success("✅ Todo el inventario está en niveles óptimos.")
        
    conn.close()

# MÓDULO 2: GESTIÓN DE PROVEEDORES
elif app_mode == "👥 Gestión de Proveedores":
    # ... (El resto del código es idéntico al anterior)
    st.subheader("👥 Gestión de Proveedores de Leche Cruda")
    # ...
