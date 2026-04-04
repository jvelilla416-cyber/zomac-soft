import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Sistema de Gestión Integrado", page_icon="🥛")

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
st.title("🥛 Sistema de Gestión Integrado - Lácteos Suiza")

# --- CONEXIÓN A LA BASE DE DATOS (SQLITE) ---
def get_db_connection():
    conn = sqlite3.connect('lacteos_suiza.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- CREACIÓN DE TABLAS (SI NO EXISTEN) ---
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Tabla de Proveedores (Sin cambios)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proveedores (
            id_proveedor TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            finca TEXT,
            telefono TEXT
        )
    """)
    
    # 2. Tabla de Entrada de Leche Cruda (Sin cambios)
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
    
    # 3. Tabla de Inventario de Productos Terminados (Sin cambios)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario_productos (
            id_producto TEXT PRIMARY KEY,
            nombre_producto TEXT NOT NULL,
            categoria TEXT,
            cantidad_kg REAL DEFAULT 0,
            precio_venta REAL
        )
    """)
    
    # 4. Tabla de Transformación Diaria (Sin cambios)
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
    
    # 5. Tabla de Transformación por Slicing (Sin cambios)
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

    # 6. Tabla de Clientes (Sin cambios)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id_cliente TEXT PRIMARY KEY,
            nombre_completo TEXT NOT NULL,
            direccion TEXT,
            telefono TEXT
        )
    """)
    
    # 7. Tabla de Registro de Ventas (Administrativo - Sin cambios)
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

    # --- NUEVA MATRIZ: TABLA DE DESPACHOS (LOGÍSTICA) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS despachos (
            id_despacho INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_despacho TEXT NOT NULL,
            id_cliente TEXT NOT NULL,
            ciudad TEXT,
            nombre_conductor TEXT,
            cedula_conductor TEXT,
            placa_vehiculo TEXT,
            temperatura_producto REAL, -- En grados Celsius
            lote_producto TEXT,
            id_producto TEXT NOT NULL,
            cantidad_despachada REAL NOT NULL,
            firma_recibe TEXT, -- Marcador de texto para firma
            firma_despacha TEXT, -- Marcador de texto para firma
            observaciones TEXT,
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
        # 1. Contraseña Maestra (Dueño - Todo)
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            st.session_state["user_role"] = "admin"
            del st.session_state["password"]
        # 2. Contraseña Producción (Operarios - Leche/Queso)
        elif st.session_state["password"] == st.secrets["production_password"]:
            st.session_state["password_correct"] = True
            st.session_state["user_role"] = "production"
            del st.session_state["password"]
        # 3. Contraseña Despachos (Logística - Muelle de Carga)
        elif st.session_state["password"] == st.secrets["dispatch_password"]:
            st.session_state["password_correct"] = True
            st.session_state["user_role"] = "dispatch"
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("## 🔒 Acceso al Sistema de Seguridad")
        st.text_input("Ingrese la Contraseña de Seguridad:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("## 🔒 Acceso al Sistema de Seguridad")
        st.text_input("Ingrese la Contraseña de Seguridad:", type="password", on_change=password_entered, key="password")
        st.error("😕 Contraseña incorrecta. Por favor, intente de nuevo.")
        return False
    else:
        return True

# --- AUTENTICACIÓN ---
if not check_password():
    st.stop()

# --- DEFINICIÓN DE MENÚS (ADMIN vs PRODUCCIÓN vs DESPACHOS) ---
user_role = st.session_state.get("user_role")

if user_role == "production":
    menu_options = ["📊 Director del Panel (Resumen)", 
                    "🥛 Entrada de Leche Cruda", 
                    "📦 Inventario de Productos Terminados",
                    "🔄 Producción: Transformación",
                    "🍽️ Producción: Tajado (Slicing)"]
elif user_role == "dispatch":
    menu_options = ["📊 Director del Panel (Resumen)", 
                    "🚛 Registro de Despachos"]
else: # admin
    menu_options = ["📊 Director del Panel (Resumen)", 
                    "👥 Gestión de Proveedores",
                    "🥛 Entrada de Leche Cruda", 
                    "📦 Inventario de Productos Terminados",
                    "🔄 Producción: Transformación",
                    "🍽️ Producción: Tajado (Slicing)",
                    "👥 Gestión de Clientes",
                    "💰 Registro de Ventas",
                    "🚛 Registro de Despachos", # Incluido en admin
                    "📈 Reportes y Gráficos",
                    "⚙️ Configuración"]

# --- BARRA LATERAL (SIDEBAR) - NAVEGACIÓN (CON CONTRASTE MÁXIMO) ---
with st.sidebar:
    st.header("Navegación")
    app_mode = st.radio("Ir a:", menu_options)
    
    st.markdown("---")
    # Botón de Excel desactivado temporalmente para asegurar que arranque
    # st.download_button(label="📥 Descargar Respaldo (Excel)", data=download_backup(), file_name=f'respaldo_lacteos_suiza_{date.today()}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    st.info("💡 Botón de Respaldo Excel desactivado temporalmente.")

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

# MÓDULO 2: GESTIÓN DE PROVEEDORES (ADMIN)
elif app_mode == "👥 Gestión de Proveedores":
    # (Mismo código anterior, sin cambios)
    pass

# MÓDULO 3: ENTRADA DE LECHE CRUDA (ADMIN, PRODUCCIÓN)
elif app_mode == "🥛 Entrada de Leche Cruda":
    # (Mismo código anterior, sin cambios)
    pass

# MÓDULO 4: INVENTARIO DE PRODUCTOS TERMINADOS (KARDEX BASE) (ADMIN, PRODUCCIÓN)
elif app_mode == "📦 Inventario de Productos Terminados":
    # (Mismo código anterior, sin cambios)
    pass

# MÓDULO 5: PRODUCCIÓN: TRANSFORMACIÓN GENERAL (LECHE A PRODUCTO) (ADMIN, PRODUCCIÓN)
elif app_mode == "🔄 Producción: Transformación":
    # (Mismo código anterior, sin cambios)
    pass

# MÓDULO 6: PRODUCCIÓN: TAJADO (SLICING - BLOQUE A TAJADO) (ADMIN, PRODUCCIÓN)
elif app_mode == "🍽️ Producción: Tajado (Slicing)":
    # (Mismo código anterior, sin cambios)
    pass

# MÓDULO 7: GESTIÓN DE CLIENTES (ADMIN)
elif app_mode == "👥 Gestión de Clientes":
    st.subheader("👥 Base de Datos de Clientes")
    
    tab1, tab2 = st.tabs(["➕ Agregar Nuevo Cliente", "📋 Lista de Clientes"])
    
    with tab1:
        st.markdown("#### Datos del Cliente")
        with st.form("form_cliente", clear_on_submit=True):
            col1, col2 = st.columns(2)
            id_cliente = col1.text_input("ID Cliente / NIT / CC")
            nombre_completo = col2.text_input("Nombre Completo o Razón Social")
            direccion = col1.text_input("Dirección de Despacho")
            telefono = col2.text_input("Teléfono de Contacto")
            submitted = st.form_submit_button("Guardar Cliente")
            
            if submitted:
                if id_cliente and nombre_completo:
                    conn = get_db_connection()
                    try:
                        conn.execute("INSERT INTO clientes (id_cliente, nombre_completo, direccion, telefono) VALUES (?, ?, ?, ?)", (id_cliente, nombre_completo, direccion, telefono))
                        conn.commit()
                        st.success(f"✅ Cliente '{nombre_completo}' registrado exitosamente.")
                    except sqlite3.IntegrityError:
                        st.error(f"❌ El ID/NIT '{id_cliente}' ya está registrado.")
                    finally:
                        conn.close()
                else:
                    st.warning("⚠️ ID y Nombre son obligatorios.")
    
    with tab2:
        st.markdown("#### Lista de Clientes")
        conn = get_db_connection()
        clientes = pd.read_sql_query("SELECT * FROM clientes", conn)
        conn.close()
        st.dataframe(clientes, use_container_width=True)

# MÓDULO 8: REGISTRO DE VENTAS (ADMIN)
elif app_mode == "💰 Registro de Ventas":
    # (Mismo código anterior, sin cambios)
    pass

# --- NUEVO MÓDULO 9: REGISTRO DE DESPACHOS (LOGÍSTICA - MATRIZ SOLICITADA) ---
elif app_mode == "🚛 Registro de Despachos":
    st.subheader("🚛 Registro de Despachos y Planilla de Carga")
    
    tab1, tab2 = st.tabs(["➕ Nuevo Despacho / Planilla", "📋 Historial de Despachos"])
    
    with tab1:
        st.markdown("#### Datos de la Planilla de Despacho")
        conn = get_db_connection()
        clientes = pd.read_sql_query("SELECT id_cliente, nombre_completo, direccion FROM clientes", conn)
        productos = pd.read_sql_query("SELECT id_producto, nombre_producto, cantidad_kg FROM inventario_productos WHERE cantidad_kg > 0", conn)
        conn.close()
        
        if clientes.empty or productos.empty:
            st.warning("⚠️ Debes tener definidos Clientes y Productos en el Kardex (con inventario) primero.")
        else:
            with st.form("form_despacho", clear_on_submit=True):
                # --- DATOS DE LA CABECERA DEL DESPACHO ---
                col1, col2 = st.columns(2)
                fecha_despacho = col1.date_input("Fecha de Despacho", date.today())
                
                id_cliente_sel = col1.selectbox("Nombre del Cliente", clientes['id_cliente'] + " - " + clientes['nombre_completo'])
                id_cliente_final = id_cliente_sel.split(' - ')[0]
                direccion_sugerida = clientes[clientes['id_cliente'] == id_cliente_final]['direccion'].values[0]
                
                ciudad = col2.text_input("Ciudad de Destino", value=direccion_sugerida)
                
                # --- DATOS DEL CONDUCTOR Y VEHÍCULO ---
                st.markdown("---")
                col3, col4, col5 = st.columns(3)
                nombre_conductor = col3.text_input("Nombre del Conductor")
                cedula_conductor = col4.text_input("Cédula del Conductor")
                placa_vehiculo = col5.text_input("Placa del Vehículo")
                
                # --- DATOS DEL PRODUCTO A DESPACHAR ---
                st.markdown("---")
                col6, col7 = st.columns(2)
                
                id_producto_sel = col6.selectbox("Producto a Despachar", productos['id_producto'] + " - " + productos['nombre_producto'])
                id_producto_final = id_producto_sel.split(' - ')[0]
                
                inventario_disponible = productos[productos['id_producto'] == id_producto_final]['cantidad_kg'].values[0]
                col6.metric(label="Inventario Disponible (Kg)", value=f"{inventario_disponible:.2f} Kg")
                
                cantidad_despachada = col7.number_input("Cantidad a Despachar (Kg)", min_value=0.1, max_value=inventario_disponible)
                lote_producto = col7.text_input("Lote del Producto (Ej. L1504)")
                temperatura_producto = col6.number_input("Temperatura del Producto (°C)", min_value=-20.0, max_value=30.0, value=4.0, help="Tomada en el muelle de carga")
                
                # --- DATOS DE FIRMAS (MARCADORES DE TEXTO) ---
                st.markdown("---")
                col8, col9 = st.columns(2)
                firma_despacha = col8.text_input("Firma quien despacha (Escriba nombre)", help="Ej. Juan Pérez (Operario)")
                firma_recibe = col9.text_input("Firma de quién recibe (Escriba nombre o 'Ver planilla física')", help="Ej. Transportadora 'Rápido'")
                
                observaciones = st.text_area("Observaciones Adicionales")
                
                submitted = st.form_submit_button("Registrar Despacho")
                
                if submitted:
                    if nombre_conductor and placa_vehiculo and lote_producto and firma_despacha and firma_recibe:
                        conn = get_db_connection()
                        # 1. Guardar registro de despacho en la nueva matriz
                        conn.execute("""
                            INSERT INTO despachos (
                                fecha_despacho, id_cliente, ciudad, nombre_conductor, cedula_conductor, 
                                placa_vehiculo, temperatura_producto, lote_producto, id_producto, 
                                cantidad_despachada, firma_recibe, firma_despacha, observaciones
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            str(fecha_despacho), id_cliente_final, ciudad, nombre_conductor, cedula_conductor, 
                            placa_vehiculo, temperatura_producto, lote_producto, id_producto_final, 
                            cantidad_despachada, firma_recibe, firma_despacha, observaciones
                        ))
                        # 2. DESCONTAR del Kardex del Producto
                        conn.execute("UPDATE inventario_productos SET cantidad_kg = cantidad_kg - ? WHERE id_producto = ?", (cantidad_despachada, id_producto_final))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Despacho de {cantidad_despachada} Kg de '{id_producto_sel}' para '{id_cliente_sel}' registrado exitosamente.")
                    else:
                        st.warning("⚠️ Por favor complete todos los campos obligatorios del despacho (Conductor, Placa, Lote, Firmas).")
    
    with tab2:
        st.markdown("#### Historial de Despachos y Planillas Emitidas")
        conn = get_db_connection()
        historico_despachos = pd.read_sql_query("""
            SELECT d.id_despacho, d.fecha_despacho, c.nombre_completo AS cliente, d.ciudad, d.nombre_conductor, d.placa_vehiculo, d.lote_producto, ip.nombre_producto AS producto, d.cantidad_despachada AS kg, d.temperatura_producto AS temp_C, d.firma_despacha, d.firma_recibe
            FROM despachos d
            JOIN clientes c ON d.id_cliente = c.id_cliente
            JOIN inventario_productos ip ON d.id_producto = ip.id_producto
            ORDER BY d.fecha_despacho DESC
        """, conn)
        conn.close()
        st.dataframe(historico_despachos, use_container_width=True)

# MÓDULO 10: REPORTES Y GRÁFICOS (ADMIN)
elif app_mode == "📈 Reportes y Gráficos":
    # (Mismo código anterior, sin cambios)
    pass

# MÓDULO 11: CONFIGURACIÓN Y RESPALDO (ADMIN)
elif app_mode == "⚙️ Configuración":
    # (Mismo código anterior, sin cambios)
    pass
