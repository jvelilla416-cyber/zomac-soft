import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Control de Planta")

def get_db_connection():
    conn = sqlite3.connect('suiza_planta_v11.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Proveedores completo
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, cedula TEXT, 
                  fedegan INTEGER, valor_litro REAL, ciclo TEXT)''')
    # 2. Recibo de leche
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio REAL, silo TEXT)')
    # 3. Silos/Tanques (Capacidad 10.000L)
    c.execute('CREATE TABLE IF NOT EXISTS silos (nombre TEXT PRIMARY KEY, saldo REAL)')
    # 4. Kardex (Inventario)
    c.execute('CREATE TABLE IF NOT EXISTS kardex (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    
    # Inicializar 4 Silos de 10.000L
    for s in ["Silo 1", "Silo 2", "Silo 3", "Silo 4"]:
        c.execute('INSERT OR IGNORE INTO silos VALUES (?, 0)', (s,))
    conn.commit()
    conn.close()

init_db()

# --- INTERFAZ ---
st.sidebar.image("logo_suiza.png", width=150)
menu = st.sidebar.selectbox("Módulo Planta:", [
    "🆕 Nuevo Proveedor", 
    "🥛 Ingreso de Leche", 
    "📊 Silos de Producción", 
    "🏭 Producción (Transformar)", 
    "🍽️ Tajado y Merma",
    "📦 Kardex Actual"
])

# --- 1. NUEVO PROVEEDOR ---
if menu == "🆕 Nuevo Proveedor":
    st.header("🆕 Registro de Proveedores")
    with st.form("f_p", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cod = c1.text_input("Código")
        nom = c2.text_input("Nombre del Proveedor")
        finca = c3.text_input("Nombre de la Finca")
        ced = c1.text_input("Cédula/NIT")
        val = c2.number_input("Valor Litro ($)", value=1850.0)
        ciclo = c3.selectbox("Ciclo de Pago", ["Semanal", "Quincenal"])
        fede = st.checkbox("Aplica Fedegán ($10/L)")
        if st.form_submit_button("✅ Guardar Proveedor"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?,?,?)', (cod, nom, finca, ced, 1 if fede else 0, val, ciclo))
            conn.commit()
            st.success(f"Proveedor {nom} registrado.")

# --- 2. INGRESO DE LECHE ---
elif menu == "🥛 Ingreso de Leche":
    st.header("🥛 Ingreso Diario a Silos")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    with st.form("f_r", clear_on_submit=True):
        p_sel = st.selectbox("Proveedor", provs['codigo'] + " - " + provs['nombre'] if not provs.empty else [])
        lts = st.number_input("Cantidad de Litros", min_value=0.0)
        silo = st.selectbox("Silo de Destino", ["Silo 1", "Silo 2", "Silo 3", "Silo 4"])
        
        # Lógica de cambio de precio
        p_base = 1850.0
        if p_sel:
            c_p = p_sel.split(" - ")[0]
            p_base = provs[provs['codigo']==c_p]['valor_litro'].values[0]
        p_final = st.number_input("Precio Final Litro (Cambio opcional)", value=float(p_base))
        
        if st.form_submit_button("🚀 Registrar Ingreso"):
            cod_p = p_sel.split(" - ")[0]
            conn.execute('UPDATE silos SET saldo = saldo + ? WHERE nombre = ?', (lts, silo))
            conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, precio, silo) VALUES (?,?,?,?,?)', (str(date.today()), cod_p, lts, p_final, silo))
            conn.commit()
            st.success(f"Ingresados {lts}L al {silo}")

# --- 3. SILOS DE PRODUCCIÓN ---
elif menu == "📊 Silos de Producción":
    st.header("📊 Nivel de Silos (Capacidad 10.000L)")
    conn = get_db_connection()
    df_s = pd.read_sql_query("SELECT * FROM silos", conn)
    cols = st.columns(4)
    for i, row in df_s.iterrows():
        cols[i].metric(row['nombre'], f"{row['saldo']} L")
        cols[i].progress(min(row['saldo']/10000, 1.0))

# --- 4. PRODUCCIÓN (TRANSFORMAR) ---
elif menu == "🏭 Producción (Transformar)":
    st.header("🏭 Transformación de Leche")
    conn = get_db_connection()
    silos_act = pd.read_sql_query("SELECT * FROM silos WHERE saldo > 0", conn)
    variedades = [
        "Queso Costeño Pasteurizado", "Queso Mozzarella", "Queso Pera", 
        "Queso Sábana", "Queso Costeño Industrializado", "Queso Cheddar",
        "Suero Costeño", "Yogurt (Vaso)", "Yogurt (Bolsa)", "Arequipe", "Quesadillo"
    ]
    
    with st.form("f_prod"):
        c1, c2 = st.columns(2)
        s_uso = c1.selectbox("Silo de Origen", silos_act['nombre'] if not silos_act.empty else ["Vacíos"])
        lts_u = c2.number_input("Litros a utilizar", min_value=0.0)
        prod = c1.selectbox("Producto a Elaborar", variedades)
        pres = c2.selectbox("Presentación", ["Bloque 2.5Kg", "Bloque 5Kg", "Unidad 1Kg", "Litro", "Vaso"])
        cant = st.number_input("Cantidad Resultante (Kg/Unidades)", min_value=0.0)
        
        if st.form_submit_button("⚙️ Procesar"):
            conn.execute('UPDATE silos SET saldo = saldo - ? WHERE nombre = ?', (lts_u, s_uso))
            # Sumar al Kardex
            c = conn.cursor()
            c.execute('SELECT stock FROM kardex WHERE producto=? AND presentacion=?', (prod, pres))
            res = c.fetchone()
            if res:
                conn.execute('UPDATE kardex SET stock = stock + ? WHERE producto=? AND presentacion=?', (cant, prod, pres))
            else:
                conn.execute('INSERT INTO kardex VALUES (?,?,?)', (prod, pres, cant))
            conn.commit()
            st.success("Producción cargada al Kardex.")

# --- 5. TAJADO Y MERMA ---
elif menu == "🍽️ Tajado y Merma":
    st.header("🍽️ Proceso de Tajado (Mozzarella, Sábana, etc.)")
    conn = get_db_connection()
    # Solo mostramos bloques en el tajado
    bloques = pd.read_sql_query("SELECT * FROM kardex WHERE presentacion LIKE '%Bloque%'", conn)
    
    with st.form("f_t"):
        b_sel = st.selectbox("Seleccione Bloque del Inventario", bloques['producto'] + " (" + bloques['presentacion'] + ")" if not bloques.empty else [])
        cant_b = st.number_input("¿Cuántos BLOQUES va a tajar?", min_value=0)
        pres_t = st.selectbox("Presentación de Salida", ["125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g"])
        
        if st.form_submit_button("⚖️ Ejecutar Tajado"):
            p_nombre = b_sel.split(" (")[0]
            p_pres = b_sel.split("(")[1].replace(")", "")
            # Lógica: Bloque de 2.5kg (2500g) - 200g merma = 2300g útiles
            # Si el bloque es de 5kg, serían 400g merma. 
            merma_por_bloque = 0.200 # 200 gramos
            peso_bloque = 2.5 if "2.5Kg" in p_pres else 5.0
            total_kg_usados = cant_b * peso_bloque
            total_merma = cant_b * merma_por_bloque
            total_neto = total_kg_usados - total_merma
            
            # 1. Restar bloques del kardex
            conn.execute('UPDATE kardex SET stock = stock - ? WHERE producto=? AND presentacion=?', (total_kg_usados, p_nombre, p_pres))
            # 2. Sumar tajado al kardex
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,?)', 
                         (p_nombre + " Tajado", pres_t, total_neto))
            conn.commit()
            st.warning(f"Merma total: {total_merma:.2f} Kg. Neto cargado: {total_neto:.2f} Kg.")

elif menu == "📦 Kardex Actual":
    st.header("📦 Inventario Real en Bodega")
    conn = get_db_connection()
    st.dataframe(pd.read_sql_query("SELECT * FROM kardex WHERE stock > 0", conn), use_container_width=True)
