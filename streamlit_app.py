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

# --- BARRA LATERAL (SIDEBAR) - NAVEGACIÓN (CON CONTRASTE MÁXIMO) ---
with st.sidebar:
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
    # st.download_button(label="📥 Descargar Respaldo (Excel)", data=download_backup(), file_name=f'respaldo_lacteos_suiza_{date.today()}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
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
    st.subheader("👥 Gestión de Proveedores de Leche Cruda")
    
    tab1, tab2 = st.tabs(["➕ Agregar Nuevo Proveedor", "📋 Lista Actual de Proveedores"])
    
    with tab1:
        st.markdown("#### Datos del Proveedor")
        with st.form("form_proveedor", clear_on_submit=True):
            col1, col2 = st.columns(2)
            id_proveedor = col1.text_input("ID Proveedor (Ej. P001)")
            nombre = col2.text_input("Nombre Completo o Finca")
            finca = col1.text_input("Lugar / Finca")
            telefono = col2.text_input("Teléfono de Contacto")
            submitted = st.form_submit_button("Guardar Proveedor")
            
            if submitted:
                if id_proveedor and nombre:
                    conn = get_db_connection()
                    try:
                        conn.execute("INSERT INTO proveedores (id_proveedor, nombre, finca, telefono) VALUES (?, ?, ?, ?)", (id_proveedor, nombre, finca, telefono))
                        conn.commit()
                        st.success(f"✅ Proveedor '{nombre}' agregado exitosamente.")
                    except sqlite3.IntegrityError:
                        st.error(f"❌ El ID '{id_proveedor}' ya está registrado.")
                    finally:
                        conn.close()
                else:
                    st.warning("⚠️ ID y Nombre son obligatorios.")
    
    with tab2:
        st.markdown("#### Lista Actual de Proveedores")
        conn = get_db_connection()
        proveedores = pd.read_sql_query("SELECT * FROM proveedores", conn)
        conn.close()
        st.dataframe(proveedores, use_container_width=True)

# MÓDULO 3: ENTRADA DE LECHE CRUDA
elif app_mode == "🥛 Entrada de Leche Cruda":
    st.subheader("🥛 Entrada Diaria de Leche Cruda")
    
    tab1, tab2 = st.tabs(["➕ Registrar Entrada Diaria", "📋 Historial de Entradas"])
    
    with tab1:
        st.markdown("#### Datos de la Entrada")
        conn = get_db_connection()
        proveedores = pd.read_sql_query("SELECT id_proveedor, nombre FROM proveedores", conn)
        conn.close()
        
        if proveedores.empty:
            st.warning("⚠️ Debes registrar al menos un proveedor primero.")
        else:
            with st.form("form_entrada_leche", clear_on_submit=True):
                col1, col2 = st.columns(2)
                fecha_entrada = col1.date_input("Fecha", date.today())
                id_proveedor_sel = col2.selectbox("Proveedor", proveedores['id_proveedor'] + " - " + proveedores['nombre'])
                id_proveedor_final = id_proveedor_sel.split(' - ')[0]
                
                litros = col1.number_input("Litros Entregados", min_value=0.1)
                precio_litro = col2.number_input("Precio por Litro (COP)", min_value=100.0)
                
                total = litros * precio_litro
                col1.metric(label="Total a Pagar (COP)", value=f"${total:,.0f}")
                
                submitted = st.form_submit_button("Registrar Entrada")
                
                if submitted:
                    conn = get_db_connection()
                    conn.execute("INSERT INTO entrada_leche (fecha, id_proveedor, litros, precio_litro, total) VALUES (?, ?, ?, ?, ?)", (str(fecha_entrada), id_proveedor_final, litros, precio_litro, total))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Entrada de {litros} litros de '{id_proveedor_sel}' registrada exitosamente.")
    
    with tab2:
        st.markdown("#### Historial de Entradas Diarias")
        conn = get_db_connection()
        entradas = pd.read_sql_query("""
            SELECT el.id_entrada, el.fecha, p.nombre AS proveedor, el.litros, el.precio_litro, el.total
            FROM entrada_leche el
            JOIN proveedores p ON el.id_proveedor = p.id_proveedor
            ORDER BY el.fecha DESC
        """, conn)
        conn.close()
        st.dataframe(entradas, use_container_width=True)

# MÓDULO 4: INVENTARIO DE PRODUCTOS TERMINADOS (KARDEX BASE)
elif app_mode == "📦 Inventario de Productos Terminados":
    st.subheader("📦 Kardex de Productos Terminados")
    
    tab1, tab2 = st.tabs(["➕ Definir Nuevo Producto", "📋 Inventario Actual (Kardex)"])
    
    with tab1:
        st.markdown("#### Definir Producto")
        with st.form("form_producto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            id_producto = col1.text_input("ID Producto (Ej. QF-001)")
            nombre_producto = col2.text_input("Nombre (Ej. Queso Fresco 500g)")
            categoria = col1.text_input("Categoría (Quesos, Sueros, etc.)")
            precio_venta = col2.number_input("Precio de Venta Sugerido (COP)", min_value=1000.0)
            submitted = st.form_submit_button("Guardar Producto")
            
            if submitted:
                if id_producto and nombre_producto:
                    conn = get_db_connection()
                    try:
                        conn.execute("INSERT INTO inventario_productos (id_producto, nombre_producto, categoria, precio_venta) VALUES (?, ?, ?, ?)", (id_producto, nombre_producto, categoria, precio_venta))
                        conn.commit()
                        st.success(f"✅ Producto '{nombre_producto}' definido exitosamente.")
                    except sqlite3.IntegrityError:
                        st.error(f"❌ El ID '{id_producto}' ya está registrado.")
                    finally:
                        conn.close()
                else:
                    st.warning("⚠️ ID y Nombre son obligatorios.")
    
    with tab2:
        st.markdown("#### Kardex de Productos Terminados (Kg)")
        conn = get_db_connection()
        inventario = pd.read_sql_query("SELECT * FROM inventario_productos", conn)
        conn.close()
        st.dataframe(inventario, use_container_width=True)

# MÓDULO 5: PRODUCCIÓN: TRANSFORMACIÓN GENERAL (LECHE A PRODUCTO)
elif app_mode == "🔄 Producción: Transformación":
    st.subheader("🔄 Producción Diaria: Litros a Queso/Suero")
    
    tab1, tab2 = st.tabs(["➕ Registrar Nueva Transformación", "📋 Historial de Producción"])
    
    with tab1:
        st.markdown("#### Datos de la Producción")
        conn = get_db_connection()
        productos = pd.read_sql_query("SELECT id_producto, nombre_producto FROM inventario_productos WHERE categoria != 'Tajado'", conn) # No mostrar tajados aquí
        conn.close()
        
        if productos.empty:
            st.warning("⚠️ Debes definir al menos un producto terminado (kg) primero.")
        else:
            with st.form("form_transformacion", clear_on_submit=True):
                col1, col2 = st.columns(2)
                fecha_prod = col1.date_input("Fecha", date.today())
                litros_usados = col1.number_input("Litros de Leche Cruda Usados", min_value=1.0)
                
                id_producto_sel = col2.selectbox("Producto Obtenido", productos['id_producto'] + " - " + productos['nombre_producto'])
                id_producto_final = id_producto_sel.split(' - ')[0]
                
                kg_producidos = col2.number_input("Cantidad Producida (Kg)", min_value=0.1)
                merma_kg = col1.number_input("Merma de Proceso (Kg)", min_value=0.0)
                observaciones = st.text_area("Observaciones")
                
                submitted = st.form_submit_button("Registrar Transformación")
                
                if submitted:
                    conn = get_db_connection()
                    # 1. Guardar registro de transformación
                    conn.execute("INSERT INTO transformacion_diaria (fecha, litros_leche_cruda_usados, producto_terminado_id, cantidad_kg_producidos, merma_kg, observaciones) VALUES (?, ?, ?, ?, ?, ?)", (str(fecha_prod), litros_usados, id_producto_final, kg_producidos, merma_kg, observaciones))
                    # 2. Actualizar el Kardex del producto terminado
                    conn.execute("UPDATE inventario_productos SET cantidad_kg = cantidad_kg + ? WHERE id_producto = ?", (kg_producidos, id_producto_final))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Transformación registrada. Se sumaron {kg_producidos} Kg al Kardex de '{id_producto_sel}'.")
    
    with tab2:
        st.markdown("#### Historial de Transformaciones Diarias")
        conn = get_db_connection()
        transformaciones = pd.read_sql_query("""
            SELECT td.id_transformacion, td.fecha, td.litros_leche_cruda_usados AS litros_usados, ip.nombre_producto AS producto_obtenido, td.cantidad_kg_producidos AS kg_producidos, td.merma_kg
            FROM transformacion_diaria td
            JOIN inventario_productos ip ON td.producto_terminado_id = ip.id_producto
            ORDER BY td.fecha DESC
        """, conn)
        conn.close()
        st.dataframe(transformaciones, use_container_width=True)

# MÓDULO 6: PRODUCCIÓN: TAJADO (SLICING - BLOQUE A TAJADO) CON MERMA POR SENSOR
elif app_mode == "🍽️ Producción: Tajado (Slicing)":
    st.subheader("🍽️ Producción: Transformación por Slicing (Tajado)")
    
    tab1, tab2 = st.tabs(["➕ Nueva Transformación por Slicing", "📋 Historial de Slicing"])
    
    with tab1:
        st.markdown("#### Datos del Slicing / Tajado")
        conn = get_db_connection()
        productos_bloque = pd.read_sql_query("SELECT id_producto, nombre_producto, cantidad_kg FROM inventario_productos WHERE nombre_producto LIKE '%Bloque%'", conn)
        productos_tajado = pd.read_sql_query("SELECT id_producto, nombre_producto FROM inventario_productos WHERE nombre_producto LIKE '%Tajado%' OR nombre_producto LIKE '%Porcionado%'", conn)
        conn.close()
        
        if productos_bloque.empty or productos_tajado.empty:
            st.warning("⚠️ Debes tener definidos productos 'Bloque' (Salida) y 'Tajado'/'Porcionado' (Entrada) en el inventario.")
        else:
            with st.form("form_slicing", clear_on_submit=True):
                col1, col2 = st.columns(2)
                fecha_slicing = col1.date_input("Fecha", date.today())
                
                id_bloque_sel = col1.selectbox("Bloque de Origen (Salida Kardex)", productos_bloque['id_producto'] + " - " + productos_bloque['nombre_producto'])
                id_bloque_final = id_bloque_sel.split(' - ')[0]
                cantidad_bloque_kg = col1.number_input("Cantidad de Bloque Usada (Kg)", min_value=2.5, help="Ej: 1 Bloque de 2.5kg")
                
                id_tajado_sel = col2.selectbox("Producto Tajado (Entrada Kardex)", productos_tajado['id_producto'] + " - " + productos_tajado['nombre_producto'])
                id_tajado_final = id_tajado_sel.split(' - ')[0]
                
                # Definición de formatos de tajado para cálculo automático
                formatos_tajado = {"250g": 0.250, "500g": 0.500, "125g": 0.125, "200g": 0.200, "1kg": 1.0, "Personalizado": 1.0}
                formato_sel = col2.selectbox("Formato de Tajado", list(formatos_tajado.keys()))
                peso_formato = formatos_tajado[formato_sel]
                
                unidades_producidas = col2.number_input(f"Unidades Producidas ({formato_sel})", min_value=1)
                
                # CÁLCULO DE LA MERMA
                # 1. Merma Fija por Sensor (200g por cada bloque usado)
                merma_sensor_kg = (cantidad_bloque_kg / 2.5) * 0.2
                
                # 2. Cantidad Entrada (Kg)
                cantidad_tajado_kg_total = unidades_producidas * peso_formato
                
                # 3. Merma Total y Adicional (Porcionado diferente)
                merma_total_kg = cantidad_bloque_kg - cantidad_tajado_kg_total
                merma_adicional_kg = merma_total_kg - merma_sensor_kg
                
                col1.metric(label="Total Kg Tajado (Entrada Kardex)", value=f"{cantidad_tajado_kg_total:.2f} Kg")
                col2.metric(label="Merma Sensor/Reproceso Fija (Kg)", value=f"{merma_sensor_kg:.2f} Kg", help="0.2kg por bloque")
                st.metric(label="Total Merma de Slicing (Kg)", value=f"{merma_total_kg:.2f} Kg")
                
                observaciones = st.text_area("Observaciones")
                submitted = st.form_submit_button("Registrar Transformación por Slicing")
                
                if submitted:
                    conn = get_db_connection()
                    # 1. Verificar inventario suficiente del bloque
                    cantidad_disponible = conn.execute("SELECT cantidad_kg FROM inventario_productos WHERE id_producto = ?", (id_bloque_final,)).fetchone()[0]
                    
                    if cantidad_disponible < cantidad_bloque_kg:
                        st.error(f"❌ Inventario insuficiente de '{id_bloque_sel}'. Disponible: {cantidad_disponible} Kg.")
                    else:
                        # 2. Guardar registro de Slicing
                        conn.execute("INSERT INTO transformacion_slicing (fecha, producto_origen_id, cantidad_origen_kg, producto_destino_id, cantidad_destino_kg, merma_sensor_kg, merma_adicional_kg, total_merma_kg, observaciones) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(fecha_slicing), id_bloque_final, cantidad_bloque_kg, id_tajado_final, cantidad_tajado_kg_total, merma_sensor_kg, merma_adicional_kg, merma_total_kg, observaciones))
                        # 3. DESCONTAR del Kardex del Bloque
                        conn.execute("UPDATE inventario_productos SET cantidad_kg = cantidad_kg - ? WHERE id_producto = ?", (cantidad_bloque_kg, id_bloque_final))
                        # 4. SUMAR al Kardex del Tajado
                        conn.execute("UPDATE inventario_productos SET cantidad_kg = cantidad_kg + ? WHERE id_producto = ?", (cantidad_tajado_kg_total, id_tajado_final))
                        
                        conn.commit()
                        st.success(f"✅ Transformación por Slicing exitosa. Se descontaron {cantidad_bloque_kg} Kg de '{id_bloque_sel}' y se sumaron {cantidad_tajado_kg_total} Kg a '{id_tajado_sel}'. Merma: {merma_total_kg} Kg.")
                    conn.close()
    
    with tab2:
        st.markdown("#### Historial de Slicing / Tajado")
        conn = get_db_connection()
        historico_slicing = pd.read_sql_query("""
            SELECT ts.id_slicing, ts.fecha, ipo.nombre_producto AS bloque_origen, ts.cantidad_origen_kg AS kg_origen, ipd.nombre_producto AS tajado_destino, ts.cantidad_destino_kg AS kg_destino, ts.merma_sensor_kg AS merma_sensor, ts.total_merma_kg AS merma_total
            FROM transformacion_slicing ts
            JOIN inventario_productos ipo ON ts.producto_origen_id = ipo.id_producto
            JOIN inventario_productos ipd ON ts.producto_destino_id = ipd.id_producto
            ORDER BY ts.fecha DESC
        """, conn)
        conn.close()
        st.dataframe(historico_slicing, use_container_width=True)

# MÓDULO 7: GESTIÓN DE CLIENTES
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

# MÓDULO 8: REGISTRO DE VENTAS Y DESPACHOS
elif app_mode == "💰 Registro de Ventas":
    st.subheader("💰 Registro de Ventas y Despachos")
    
    tab1, tab2 = st.tabs(["➕ Nueva Venta / Despacho", "📋 Historial de Ventas"])
    
    with tab1:
        st.markdown("#### Datos de la Venta")
        conn = get_db_connection()
        clientes = pd.read_sql_query("SELECT id_cliente, nombre_completo FROM clientes", conn)
        productos = pd.read_sql_query("SELECT id_producto, nombre_producto, cantidad_kg, precio_venta FROM inventario_productos WHERE cantidad_kg > 0", conn)
        conn.close()
        
        if clientes.empty or productos.empty:
            st.warning("⚠️ Debes tener definidos Clientes y Productos en el Kardex (con inventario) primero.")
        else:
            with st.form("form_venta", clear_on_submit=True):
                col1, col2 = st.columns(2)
                fecha_venta = col1.date_input("Fecha", date.today())
                
                id_cliente_sel = col1.selectbox("Cliente", clientes['id_cliente'] + " - " + clientes['nombre_completo'])
                id_cliente_final = id_cliente_sel.split(' - ')[0]
                
                id_producto_sel = col2.selectbox("Producto", productos['id_producto'] + " - " + productos['nombre_producto'])
                id_producto_final = id_producto_sel.split(' - ')[0]
                
                inventario_disponible = productos[productos['id_producto'] == id_producto_final]['cantidad_kg'].values[0]
                precio_unitario_sugerido = productos[productos['id_producto'] == id_producto_final]['precio_venta'].values[0]
                
                col2.metric(label="Inventario Disponible (Kg)", value=f"{inventario_disponible:.2f} Kg")
                
                cantidad_venta = col1.number_input("Cantidad a Vender (Kg)", min_value=0.1, max_value=inventario_disponible)
                precio_unitario = col2.number_input("Precio Unitario Final (COP)", min_value=1000.0, value=precio_unitario_sugerido)
                
                total_venta = cantidad_venta * precio_unitario
                st.metric(label="Total Venta (COP)", value=f"${total_venta:,.0f}")
                
                submitted = st.form_submit_button("Registrar Venta")
                
                if submitted:
                    conn = get_db_connection()
                    # 1. Guardar registro de venta
                    conn.execute("INSERT INTO ventas (fecha, id_cliente, id_producto, cantidad, precio_unitario, total_venta) VALUES (?, ?, ?, ?, ?, ?)", (str(fecha_venta), id_cliente_final, id_producto_final, cantidad_venta, precio_unitario, total_venta))
                    # 2. DESCONTAR del Kardex del Producto
                    conn.execute("UPDATE inventario_productos SET cantidad_kg = cantidad_kg - ? WHERE id_producto = ?", (cantidad_venta, id_producto_final))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Venta registrada. Se descontaron {cantidad_venta} Kg de '{id_producto_sel}'.")
    
    with tab2:
        st.markdown("#### Historial de Ventas")
        conn = get_db_connection()
        historico_ventas = pd.read_sql_query("""
            SELECT v.id_venta, v.fecha, c.nombre_completo AS cliente, ip.nombre_producto AS producto, v.cantidad AS kg, v.precio_unitario, v.total_venta AS total
            FROM ventas v
            JOIN clientes c ON v.id_cliente = c.id_cliente
            JOIN inventario_productos ip ON v.id_producto = ip.id_producto
            ORDER BY v.fecha DESC
        """, conn)
        conn.close()
        st.dataframe(historico_ventas, use_container_width=True)

# MÓDULO 9: REPORTES Y GRÁFICOS (POR INTEGRAR MÁS)
elif app_mode == "📈 Reportes y Gráficos":
    st.subheader("📈 Reportes y Visualización de Datos")
    st.markdown("#### *Sección en desarrollo... Próximamente reportes de rentabilidad y consumo.*")

# MÓDULO 10: CONFIGURACIÓN Y RESPALDO
elif app_mode == "⚙️ Configuración":
    st.subheader("⚙️ Configuración Avanzada y Seguridad")
    st.markdown("#### *Sección en desarrollo... Próximamente edición de contraseñas.*")
    st.warning("⚠️ La función de respaldo en Excel está desactivada temporalmente por compatibilidad.")
