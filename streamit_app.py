import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from fpdf import FPDF

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Planta y Rutas")

def get_db_connection():
    # Nueva versión de DB para aplicar los cambios de rutas y retenciones
    conn = sqlite3.connect('suiza_v6_final.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Proveedores con Finca, Ruta y Configuración de Descuentos
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, ruta TEXT, 
                  precio_base REAL, ciclo TEXT, aplica_fedegan INTEGER, aplica_retencion INTEGER)''')
    
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, tanque TEXT, precio_pactado REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS inventario (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    c.execute('CREATE TABLE IF NOT EXISTS tanques (nombre TEXT PRIMARY KEY, capacidad REAL, saldo REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS cuarto_frio (id INTEGER PRIMARY KEY, fecha TEXT, cantidad REAL, motivo TEXT)')
    
    for t in ["Tanque 1", "Tanque 2", "Tanque 3"]:
        c.execute('INSERT OR IGNORE INTO tanques VALUES (?, 2000, 0)')
    conn.commit()
    conn.close()

init_db()

# --- SIDEBAR ---
st.sidebar.image("logo_suiza.png", width=150)
st.sidebar.title("🥛 PLANTA SUIZA")
menu = st.sidebar.selectbox("Módulo:", ["📊 Estado de Tanques", "👥 Proveedores y Rutas", "🥛 Recibo Leche", "📈 Reporte Diario", "🏭 Producción", "🍽️ Tajado y Merma", "📦 Kardex"])

# --- 1. PROVEEDORES Y RUTAS ---
if menu == "👥 Proveedores y Rutas":
    st.header("👥 Gestión de Proveedores por Rutas")
    with st.form("f_prov", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cod = c1.text_input("Código Proveedor")
        nom = c2.text_input("Nombre Dueño")
        finca = c3.text_input("Nombre de la Finca")
        ruta = c1.text_input("Nombre de la Ruta (Ej: Molonga)")
        pre = c2.number_input("Precio Base Litro ($)", value=1850)
        ciclo = c3.selectbox("Ciclo de Pago", ["Semanal", "Quincenal"])
        
        st.write("**Configuración de Descuentos:**")
        fede = st.checkbox("Descontar Fedegán ($10/Litro)")
        rete = st.checkbox("Habilitar Retención (1.5% tras tope $3,666,000)")
        
        if st.form_submit_button("✅ Guardar Proveedor"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?,?,?,?)', 
                         (cod, nom, finca, ruta, pre, ciclo, 1 if fede else 0, 1 if rete else 0))
            conn.commit()
            st.success(f"Proveedor {nom} de la Finca {finca} guardado en Ruta {ruta}.")

# --- 2. RECIBO LECHE ---
elif menu == "🥛 Recibo Leche":
    st.header("🥛 Ingreso de Leche")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    tanques = pd.read_sql_query("SELECT nombre FROM tanques", conn)
    
    with st.form("f_recibo", clear_on_submit=True):
        col1, col2 = st.columns(2)
        p_sel = col1.selectbox("Proveedor / Finca", provs['codigo'] + " - " + provs['finca'] if not provs.empty else [])
        t_sel = col2.selectbox("Tanque Destino", tanques['nombre'])
        lts = col1.number_input("Litros Ingresados", min_value=0.0)
        p_hoy = col2.number_input("Precio Pactado hoy", value=1850)
        
        if st.form_submit_button("🚀 Registrar Ingreso"):
            cod_p = p_sel.split(" - ")[0]
            conn.execute('UPDATE tanques SET saldo = saldo + ? WHERE nombre = ?', (lts, t_sel))
            conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, tanque, precio_pactado) VALUES (?,?,?,?,?)', 
                         (str(date.today()), cod_p, lts, t_sel, p_hoy))
            conn.commit()
            st.success("Ingreso registrado.")

# --- 3. REPORTE DIARIO (LO QUE ME PEDISTE) ---
elif menu == "📈 Reporte Diario":
    st.header(f"📈 Reporte de Leche - {date.today()}")
    conn = get_db_connection()
    query = '''SELECT r.fecha, p.ruta, p.finca, p.nombre as proveedor, r.litros, r.precio_pactado, (r.litros * r.precio_pactado) as subtotal
               FROM recibo_leche r JOIN proveedores p ON r.cod_prov = p.codigo
               WHERE r.fecha = ?'''
    df_hoy = pd.read_sql_query(query, conn, params=(str(date.today()),))
    
    if not df_hoy.empty:
        st.dataframe(df_hoy, use_container_width=True)
        total_lts = df_hoy['litros'].sum()
        total_pesos = df_hoy['subtotal'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("TOTAL LITROS DÍA", f"{total_lts} L")
        c2.metric("TOTAL VALOR DÍA", f"${total_pesos:,.0f}")
    else:
        st.info("No hay registros hoy.")

# --- 4. TAJADO Y MERMA ---
elif menu == "🍽️ Tajado y Merma":
    st.header("🍽️ Proceso de Tajado (Control de Mermas)")
    with st.form("f_taja", clear_on_submit=True):
        kg_in = st.number_input("Kilos de Queso Bloque a tajar (Kardex)", min_value=0.0)
        prod = st.selectbox("Variedad a sacar", ["Queso Tajado", "Queso Desmenuzado"])
        pres = st.selectbox("Presentación final", ["125g", "250g", "500g", "1000g", "2500g"])
        
        # Merma de 200g por cada bloque de 2.5kg
        n_bloques = kg_in / 2.5 if kg_in > 0 else 0
        merma_kg = n_bloques * 0.200
        neto = kg_in - merma_kg
        
        if st.form_submit_button("⚙️ Procesar Tajado"):
            conn = get_db_connection()
            # 1. Merma a Cuarto Frío
            conn.execute('INSERT INTO cuarto_frio (fecha, cantidad, motivo) VALUES (?,?,"Merma Tajado")', (str(date.today()), merma_kg))
            # 2. Neto a Kardex (Debes tener lógica para restar el bloque antes)
            conn.execute('INSERT OR REPLACE INTO inventario (producto, presentacion, stock) VALUES (?,?,?)', (prod, pres, neto))
            conn.commit()
            st.warning(f"Merma: {merma_kg:.2f} Kg enviada a Cuarto Frío.")
            st.success(f"Cargados {neto:.2f} Kg de {prod} al Kardex.")

# (Los demás módulos de Tanques, Producción y Kardex siguen igual que los anteriores)
