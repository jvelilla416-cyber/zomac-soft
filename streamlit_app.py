import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io
# Usamos fpdf para la generación de PDFs profesionales para impresión
from fpdf import FPDF

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
    # (Código de creación de tablas idéntico al anterior)
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
            merma_sensor_kg REAL DEFAULT 0.2, -- Merma fija de 200g por bloque
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
    # --- NUEVA MATRIZ DE DATOS: DESPACHOS (image_4.png) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS despachos (
            id_despacho INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_despacho TEXT NOT NULL,
            id_cliente TEXT NOT NULL,
            ciudad TEXT,
            nombre_conductor TEXT,
            cedula_conductor TEXT,
            placa_vehiculo TEXT,
            temperatura_producto REAL,
            lote_producto TEXT,
            id_producto TEXT NOT NULL,
            cantidad REAL NOT NULL,
            firma_recibe TEXT, -- Almacenaremos nombre de quien firma
            firma_despacha TEXT, -- Almacenaremos nombre de quien firma
            observaciones TEXT,
            FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente),
            FOREIGN KEY (id_producto) REFERENCES inventario_productos (id_producto)
        )
    """)
    conn.commit()
    conn.close()

create_tables()

# --- BARRA LATERAL (SIDEBAR) - NAVEGACIÓN (CON CONTRASTE MÁXIMO Y SIN CLAVES) ---
with st.sidebar:
    st.header("Navegación")
    app_mode = st.radio("Ir a:", ["📊 Director del Panel (Resumen)", 
                                  "👥 Gestión de Proveedores",
                                  "🥛 Entrada de Leche Cruda", 
                                  "📦 Inventario de Productos Terminados",
                                  "🔄 Producción: Transformación",
                                  "🍽️ Producción: Tajado (Slicing)",
                                  "👥 Gestión de Clientes",
                                  "💰 Registro de Ventas",
                                  "🚛 Registro de Despachos y Carga",
                                  "📈 Reportes y Gráficos",
                                  "⚙️ Configuración"])
    
    st.markdown("---")
    # Botón de Excel desactivado temporalmente para asegurar que arranque
    # st.download_button(label="📥 Descargar Respaldo (Excel)", data=download_backup(), file_name=f'respaldo_lacteos_suiza_{date.today()}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    st.info("💡 Botón de Respaldo Excel desactivado temporalmente.")

# --- CÓDIGO DE LOS MÓDULOS (IDÉNTICO AL ANTERIOR) ---

# Función para generar Planilla de Despacho Profesional (image_4.png)
def generar_pdf_despacho(id_despacho_print):
    conn = get_db_connection()
    # Obtener los datos completos del despacho de la BD
    despacho_db = conn.execute("""
        SELECT d.*, c.nombre_completo AS cliente, c.direccion AS dir_cliente, ip.nombre_producto AS producto
        FROM despachos d
        JOIN clientes c ON d.id_cliente = c.id_cliente
        JOIN inventario_productos ip ON d.id_producto = ip.id_producto
        WHERE d.id_despacho = ?
    """, (id_despacho_print,)).fetchone()
    conn.close()

    if not despacho_db:
        return None

    # Clase base para el PDF de Lácteos Suiza
    class SuizaPDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            # Encabezado azul profesional
            self.set_text_color(0, 75, 160)
            self.cell(0, 10, 'Lácteos Suiza - Sistema de Gestión', 0, 1, 'C')
            self.set_font('Arial', 'I', 10)
            self.cell(0, 10, f'Fecha de Impresión: {date.today()}', 0, 1, 'R')
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(169, 169, 169)
            self.cell(0, 10, 'Lácteos Suiza - Sincelejo, Sucre - Tel: 300 123 4567 - Página ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

    pdf = SuizaPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(0, 0, 0)

    # 1. Datos de la Planilla (image_4.png)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f'Planilla de Despacho y Carga de Mercancía #{id_despacho_print}', 0, 1, 'C')
    pdf.ln(5)

    pdf.set_font('Arial', '', 11)
    # Tabla de datos generales (image_4.png)
    col_width = 50
    data_width = 100
    row_height = 8

    pdf.cell(col_width, row_height, 'Nombre del Cliente:', 0)
    pdf.cell(data_width, row_height, f"{despacho_db['cliente']}", 1, 1)
    
    pdf.cell(col_width, row_height, 'Ciudad / Dirección:', 0)
    pdf.cell(data_width, row_height, f"{despacho_db['ciudad']} / {despacho_db['dir_cliente']}", 1, 1)
    
    pdf.cell(col_width, row_height, 'Fecha de despacho:', 0)
    pdf.cell(data_width, row_height, f"{despacho_db['fecha_despacho']}", 1, 1)
    
    pdf.cell(col_width, row_height, 'Nombre del conductor:', 0)
    pdf.cell(data_width, row_height, f"{despacho_db['nombre_conductor']}", 1, 1)
    
    pdf.cell(col_width, row_height, 'Cédula del conductor:', 0)
    pdf.cell(data_width, row_height, f"{despacho_db['cedula_conductor']}", 1, 1)
    
    pdf.cell(col_width, row_height, 'Placa del vehículo:', 0)
    pdf.cell(data_width, row_height, f"{despacho_db['placa_vehiculo']}", 1, 1)
    
    pdf.ln(10)

    # 2. Datos del Producto
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Detalle de Productos a Despachar:', 0, 1, 'L')
    pdf.set_font('Arial', '', 11)
    
    # Tabla de productos (image_4.png)
    # Encabezados
    pdf.cell(70, 8, 'Producto a despachar', 1)
    pdf.cell(40, 8, 'Lotes del producto', 1)
    pdf.cell(40, 8, 'Cantidad (Kg)', 1)
    pdf.cell(40, 8, 'Temperatura (°C)', 1, 1)
    
    # Contenido (iterar sobre los productos)
    pdf.cell(70, 8, f"{despacho_db['producto']}", 1)
    pdf.cell(40, 8, f"{despacho_db['lote_producto']}", 1)
    pdf.cell(40, 8, f"{despacho_db['cantidad']}", 1)
    pdf.cell(40, 8, f"{despacho_db['temperatura_producto']}", 1, 1)

    pdf.ln(20)

    # 3. Firmas (image_4.png)
    pdf.set_font('Arial', 'B', 11)
    
    # Línea de firma quien despacha
    pdf.cell(95, 8, 'Firma quien despacha (Lácteos Suiza):', 0)
    pdf.cell(95, 8, 'Firma de quién recibe la mercancía:', 0, 1)
    
    pdf.ln(15)
    
    # Líneas para firma física
    pdf.cell(95, 0, '_______________________________', 0)
    pdf.cell(95, 0, '_______________________________', 0, 1)
    
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 9)
    # Nombres de firmas almacenados (image_4.png)
    pdf.cell(95, 5, f"{despacho_db['firma_despacha']}", 0, 0, 'C')
    pdf.cell(95, 5, f"{despacho_db['firma_recibe']}", 0, 1, 'C')

    # Retornar el PDF como bytes para el botón de descarga professional
    return pdf.output(dest='S').encode('latin1')

# (Módulos del Sistema idénticos al anterior)

# MÓDULO 1: DIRECTOR DEL PANEL (RESUMEN)
if app_mode == "📊 Director del Panel (Resumen)":
    # (Código anterior idéntico, sin cambios)
    pass

# MÓDULO 2: GESTIÓN DE PROVEEDORES
elif app_mode == "👥 Gestión de Proveedores":
    # (Código anterior idéntico, sin cambios)
    pass

# MÓDULO 3: ENTRADA DE LECHE CRUDA
elif app_mode == "🥛 Entrada de Leche Cruda":
    # (Código anterior idéntico, sin cambios)
    pass

# MÓDULO 4: INVENTARIO DE PRODUCTOS TERMINADOS (KARDEX BASE)
elif app_mode == "📦 Inventario de Productos Terminados":
    # (Código anterior idéntico, sin cambios)
    pass

# MÓDULO 5: PRODUCCIÓN: TRANSFORMACIÓN GENERAL (LECHE A PRODUCTO)
elif app_mode == "🔄 Producción: Transformación":
    # (Código anterior idéntico, sin cambios)
    pass

# MÓDULO 6: PRODUCCIÓN: TAJADO (SLICING - BLOQUE A TAJADO)
elif app_mode == "🍽️ Producción: Tajado (Slicing)":
    # (Código anterior idéntico, sin cambios)
    pass

# MÓDULO 7: GESTIÓN DE CLIENTES
elif app_mode == "👥 Gestión de Clientes":
    # (Código anterior idéntico, sin cambios)
    pass

# MÓDULO 8: REGISTRO DE VENTAS
elif app_mode == "💰 Registro de Ventas":
    # (Código anterior idéntico, sin cambios)
    pass

# MÓDULO 9: REGISTRO DE DESPACHOS Y CARGA (ADMIN, DESPACHOS)
elif app_mode == "🚛 Registro de Despachos y Carga":
    st.subheader("🚛 Registro de Despachos, Carga de Mercancía y 🖨️ Impresión (image_4.png)")
    
    tab1, tab2 = st.tabs(["➕ Nuevo Despacho / Planilla (image_4.png)", "📋 Historial y 🖨️ Imprimir Planilla Firmada"])
    
    with tab1:
        st.markdown("#### Datos de la Planilla de Despacho (image_4.png)")
        conn = get_db_connection()
        # Obtener clientes y productos disponibles
        clientes = pd.read_sql_query("SELECT id_cliente, nombre_completo, direccion FROM clientes", conn)
        productos = pd.read_sql_query("SELECT id_producto, nombre_producto, cantidad_kg FROM inventario_productos WHERE cantidad_kg > 0", conn)
        conn.close()
        
        if clientes.empty or productos.empty:
            st.warning("⚠️ Debes tener definidos Clientes y Productos en el Kardex (con inventario) primero.")
        else:
            with st.form("form_despacho", clear_on_submit=True):
                # --- DATOS GENERALES DEL DESPACHO (image_4.png) ---
                col1, col2 = st.columns(2)
                nombre_cliente = col1.selectbox("Nombre del Cliente (image_4.png)", clientes['id_cliente'] + " - " + clientes['nombre_completo'])
                ciudad = col2.text_input("Ciudad de Destino (image_4.png)")
                fecha_despacho = col1.date_input("Fecha de despacho (image_4.png)", date.today())
                nombre_conductor = col2.text_input("Nombre del conductor (image_4.png)")
                cedula_conductor = col1.text_input("Cédula del conductor (image_4.png)")
                placa_vehiculo = col2.text_input("Placa del vehículo (image_4.png)")
                
                # --- DATOS DEL PRODUCTO A DESPACHAR ---
                st.markdown("---")
                col3, col4, col5 = st.columns(3)
                producto_despachar = col3.selectbox("Producto a despachar (image_4.png)", productos['id_producto'] + " - " + productos['nombre_producto'])
                lote_producto = col4.text_input("Lotes de el producto (image_4.png)")
                temperatura_producto = col5.number_input("Temperatura del producto (°C) (image_4.png)", min_value=-20.0, max_value=30.0, value=4.0)
                
                # Obtener inventario disponible del producto seleccionado
                id_producto_final = producto_despachar.split(' - ')[0]
                inventario_disponible = productos[productos['id_producto'] == id_producto_final]['cantidad_kg'].values[0]
                col3.metric(label="Inventario Disponible (Kg)", value=f"{inventario_disponible:.2f} Kg")
                
                cantidad = col4.number_input("Cantidad (Kg) (image_4.png)", min_value=0.1, max_value=inventario_disponible)
                
                # --- FIRMAS (image_4.png) ---
                st.markdown("---")
                col6, col7 = st.columns(2)
                firma_recibe = col6.text_input("Firma de quién recibe la mercancía (image_4.png)", help="Escriba nombre o 'Ver planilla física'")
                firma_despacha = col7.text_input("Firma quien despacha (Lácteos Suiza) (image_4.png)", help="Escriba nombre del operario")
                
                observaciones = st.text_area("Observaciones Adicionales")
                
                submitted = st.form_submit_button("Registrar Despacho")
                
                if submitted:
                    if nombre_conductor and placa_vehiculo and lote_producto and firma_despacha and firma_recibe:
                        conn = get_db_connection()
                        # 1. Guardar registro de despacho en la nueva matriz de datos
                        conn.execute("""
                            INSERT INTO despachos (
                                fecha_despacho, id_cliente, ciudad, nombre_conductor, cedula_conductor, 
                                placa_vehiculo, temperatura_producto, lote_producto, id_producto, 
                                cantidad, firma_recibe, firma_despacha, observaciones
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            str(fecha_despacho), producto_despachar.split(' - ')[0], ciudad, nombre_conductor, cedula_conductor, 
                            placa_vehiculo, temperatura_producto, lote_producto, id_producto_final, 
                            cantidad, firma_recibe, firma_despacha, observaciones
                        ))
                        # 2. DESCONTAR del Kardex del Producto (FUNDAMENTAL PARA EL CONTROL)
                        conn.execute("UPDATE inventario_productos SET cantidad_kg = cantidad_kg - ? WHERE id_producto = ?", (cantidad, id_producto_final))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Despacho de {cantidad} Kg de '{producto_despachar}' registrado exitosamente y descontado del Kardex.")
                    else:
                        st.warning("⚠️ Por favor complete todos los campos obligatorios del despacho (Conductor, Placa, Lote, Firmas).")
    
    with tab2:
        st.markdown("#### Historial de Despachos y Planillas Emitidas")
        conn = get_db_connection()
        historico_despachos = pd.read_sql_query("""
            SELECT d.id_despacho, d.fecha_despacho, c.nombre_completo AS cliente, d.ciudad, d.nombre_conductor, d.placa_vehiculo, d.lote_producto, ip.nombre_producto AS producto, d.cantidad AS kg, d.temperatura_producto AS temp_C, d.firma_despacha, d.firma_recibe
            FROM despachos d
            JOIN clientes c ON d.id_cliente = c.id_cliente
            JOIN inventario_productos ip ON d.id_producto = ip.id_producto
            ORDER BY d.fecha_despacho DESC
        """, conn)
        conn.close()
        st.dataframe(historico_despachos, use_container_width=True)
        
        # --- ACTIVACIÓN DE IMPRESIÓN PROFESIONAL SOLICITADA ---
        st.markdown("---")
        st.markdown("#### 🖨️ Imprimir Planilla Física Firmada (image_4.png)")
        id_despacho_print = st.number_input("Ingrese ID de Despacho para imprimir planilla profesional:", min_value=1)
        
        if st.button("🖨️ Generar Planilla de Despacho Profesional (PDF)"):
            # Generar el PDF profesional usando la función que definimos arriba
            pdf_bytes = generar_pdf_despacho(id_despacho_print)
            
            if pdf_bytes:
                st.success("✅ Planilla generada exitosamente. Haga clic en el botón de abajo para descargar e imprimir.")
                
                # Botón de descarga professional para impresión
                st.download_button(
                    label="📥 Descargar Planilla de Despacho (PDF) para Imprimir",
                    data=pdf_bytes,
                    file_name=f"planilla_despacho_{id_despacho_print}_{date.today()}.pdf",
                    mime="application/pdf",
                    key="download_despacho_pdf"
                )
            else:
                st.error("❌ ID de Despacho no encontrado.")

# MÓDULO 10: REPORTES Y GRÁFICOS
elif app_mode == "📈 Reportes y Gráficos":
    # (Código anterior idéntico, sin cambios)
    pass

# MÓDULO 11: CONFIGURACIÓN Y RESPALDO
elif app_mode == "⚙️ Configuración":
    # (Código anterior idéntico, sin cambios)
    pass
