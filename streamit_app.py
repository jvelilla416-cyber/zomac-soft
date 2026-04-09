import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Planta Central")

def get_db_connection():
    conn = sqlite3.connect('suiza_planta_v12.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Proveedores
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, cedula TEXT, 
                  fedegan INTEGER, valor_litro REAL, ciclo TEXT)''')
    # 2. Recibo de Leche
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_pactado REAL, silo TEXT)')
    # 3. Silos (10.000L)
    c.execute('CREATE TABLE IF NOT EXISTS silos (nombre TEXT PRIMARY KEY, saldo REAL)')
    # 4. Kardex
    c.execute('CREATE TABLE IF NOT EXISTS kardex (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    
    for s in ["Silo 1", "Silo 2", "Silo 3", "Silo 4"]:
        c.execute('INSERT OR IGNORE INTO silos VALUES (?, 0)', (s,))
    conn.commit()
    conn.close()

init_db()

# --- SIDEBAR ---
st.sidebar.image("logo_suiza.png", width=150)
menu = st.sidebar.selectbox("Módulo Planta:", [
    "🆕 Nuevo Proveedor", 
    "🥛 Ingreso de Leche", 
    "📊 Silos de Producción",
    "💰 Liquidación de Pagos",
    "🏭 Producción (Transformar)", 
    "🍽️ Tajado y Merma",
    "📦 Kardex"
])

# --- 1. NUEVO PROVEEDOR ---
if menu == "🆕 Nuevo Proveedor":
    st.header("🆕 Registro de Proveedores")
    with st.form("f_p", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cod = c1.text_input("Código")
        nom = c2.text_input("Nombre")
        finca = c3.text_input("Finca")
        ced = c1.text_input("Cédula/NIT")
        val = c2.number_input("Valor Litro ($)", value=1850.0)
        ciclo = c3.selectbox("Ciclo", ["Semanal", "Quincenal"])
        fede = st.checkbox("Aplica Fedegán ($10/L)")
        if st.form_submit_button("✅ Guardar"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?,?,?)', (cod, nom, finca, ced, 1 if fede else 0, val, ciclo))
            conn.commit()
            st.success("Guardado.")

# --- 2. INGRESO DE LECHE ---
elif menu == "🥛 Ingreso de Leche":
    st.header("🥛 Recibo de Leche")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    with st.form("f_r", clear_on_submit=True):
        p_sel = st.selectbox("Proveedor", provs['codigo'] + " - " + provs['nombre'] if not provs.empty else [])
        lts = st.number_input("Litros", min_value=0.0)
        silo = st.selectbox("Silo Destino", ["Silo 1", "Silo 2", "Silo 3", "Silo 4"])
        
        p_base = 1850.0
        if p_sel:
            c_p = p_sel.split(" - ")[0]
            p_base = provs[provs['codigo']==c_p]['valor_litro'].values[0]
        p_final = st.number_input("Precio Litro (Corregible)", value=float(p_base))
        
        if st.form_submit_button("🚀 Registrar"):
            cod_p = p_sel.split(" - ")[0]
            conn.execute('UPDATE silos SET saldo = saldo + ? WHERE nombre = ?', (lts, silo))
            conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, precio_pactado, silo) VALUES (?,?,?,?,?)', (str(date.today()), cod_p, lts, p_final, silo))
            conn.commit()
            st.success("Ingreso registrado.")

# --- 3. LIQUIDACIÓN (LO QUE PEDISTE) ---
elif menu == "💰 Liquidación de Pagos":
    st.header("💰 Liquidación de Proveedores")
    ciclo_sel = st.radio("Ciclo a Liquidar:", ["Semanal", "Quincenal"], horizontal=True)
    
    conn = get_db_connection()
    query = f'''SELECT p.codigo, p.nombre, p.finca, p.fedegan, SUM(r.litros) as total_lts, AVG(r.precio_pactado) as precio_avg
               FROM recibo_leche r JOIN proveedores p ON r.cod_prov = p.codigo
               WHERE p.ciclo = '{ciclo_sel}' GROUP BY p.codigo'''
    df = pd.read_sql_query(query, conn)
    
    if not df.empty:
        df['Bruto'] = df['total_lts'] * df['precio_avg']
        df['Descuento Fedegan'] = df.apply(lambda x: x['total_lts'] * 10 if x['fedegan'] == 1 else 0, axis=1)
        df['Total a Pagar'] = df['Bruto'] - df['Descuento Fedegan']
        
        st.dataframe(df[['codigo', 'nombre', 'finca', 'total_lts', 'precio_avg', 'Descuento Fedegan', 'Total a Pagar']], use_container_width=True)
        
        if st.button("📥 Generar Relación para Impresión (CSV)"):
            df.to_csv(f"liquidacion_{ciclo_sel}_{date.today()}.csv", index=False)
            st.success("Archivo generado. Puede abrirlo en Excel para imprimir.")
    else:
        st.info("No hay datos para liquidar en este ciclo.")

# --- 4. PRODUCCIÓN ---
elif menu == "🏭 Producción (Transformar)":
    st.header("🏭 Transformación")
    conn = get_db_connection()
    silos = pd.read_sql_query("SELECT * FROM silos WHERE saldo > 0", conn)
    variedades = ["Queso Costeño Pasteurizado", "Queso Mozzarella", "Queso Pera", "Queso Sábana", "Queso Costeño Industrial", "Queso Cheddar", "Suero Costeño", "Yogurt (Bolsa)", "Arequipe", "Quesadillo"]
    
    with st.form("f_prod"):
        c1, c2 = st.columns(2)
        s_uso = c1.selectbox("Silo", silos['nombre'] if not silos.empty else ["Vacíos"])
        lts_u = c2.number_input("Litros a usar", min_value=0.0)
        prod = c1.selectbox("Producto", variedades)
        pres = c2.selectbox("Presentación", ["Bloque 2.5Kg", "Bloque 5Kg", "Litro", "Vaso"])
        cant = st.number_input("Cantidad Resultante", min_value=0.0)
        if st.form_submit_button("⚙️ Procesar"):
            conn.execute('UPDATE silos SET saldo = saldo - ? WHERE nombre = ?', (lts_u, s_uso))
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (prod, pres, prod, pres, cant))
            conn.commit()
            st.success("Kardex actualizado.")

# --- 5. TAJADO Y MERMA ---
elif menu == "🍽️ Tajado y Merma":
    st.header("🍽️ Proceso de Tajado")
    with st.form("f_t"):
        prod_t = st.selectbox("Queso a tajar", ["Mozzarella", "Sábana", "Pera", "Doble Crema", "Cheddar"])
        cant_bloques = st.number_input("Cantidad de bloques (de 2.5kg)", min_value=0)
        pres_salida = st.selectbox("Presentación", ["125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g"])
        
        if st.form_submit_button("⚖️ Ejecutar"):
            merma = cant_bloques * 0.200 # 200g por bloque
            neto = (cant_bloques * 2.5) - merma
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (prod_t + " Tajado", pres_salida, prod_t + " Tajado", pres_salida, neto))
            conn.commit()
            st.warning(f"Merma: {merma} kg. Neto: {neto} kg.")

elif menu == "📦 Kardex":
    st.header("📦 Inventario")
    conn = get_db_connection()
    st.dataframe(pd.read_sql_query("SELECT * FROM kardex", conn), use_container_width=True)

elif menu == "📊 Silos de Producción":
    st.header("📊 Nivel de Silos (10.000L)")
    conn = get_db_connection()
    df_s = pd.read_sql_query("SELECT * FROM silos", conn)
    cols = st.columns(4)
    for i, row in df_s.iterrows():
        cols[i].metric(row['nombre'], f"{row['saldo']} L")
        cols[i].progress(min(row['saldo']/10000, 1.0))
