import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Planta Central")

def get_db_connection():
    conn = sqlite3.connect('suiza_planta_v13.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Proveedores
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, cedula TEXT, 
                  fedegan_bool INTEGER, valor_litro REAL, ciclo TEXT)''')
    # 2. Recibo de Leche
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_pactado REAL, silo TEXT)')
    # 3. Silos (10.000L)
    c.execute('CREATE TABLE IF NOT EXISTS silos (nombre TEXT PRIMARY KEY, saldo REAL)')
    # 4. Kardex
    c.execute('CREATE TABLE IF NOT EXISTS kardex (producto TEXT, presentacion TEXT, stock REAL, PRIMARY KEY (producto, presentacion))')
    # 5. Registro de Tajado
    c.execute('CREATE TABLE IF NOT EXISTS log_tajado (id INTEGER PRIMARY KEY, fecha TEXT, producto TEXT, bloques INTEGER, merma REAL, neto REAL)')
    
    for s in ["Silo 1", "Silo 2", "Silo 3", "Silo 4"]:
        c.execute('INSERT OR IGNORE INTO silos VALUES (?, 0)', (s,))
    conn.commit()
    conn.close()

init_db()

# --- SIDEBAR ---
st.sidebar.title("🥛 LÁCTEOS SUIZA")
menu = st.sidebar.selectbox("Módulo Planta:", [
    "🆕 Nuevo Proveedor", 
    "🥛 Ingreso de Leche", 
    "📊 Silos de Producción",
    "💰 Liquidación y Volantes",
    "🏭 Producción", 
    "🍽️ Tajado y Merma",
    "📦 Kardex"
])

# --- 1. NUEVO PROVEEDOR ---
if menu == "🆕 Nuevo Proveedor":
    st.header("🆕 Registro de Proveedores")
    with st.form("f_p", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cod = c1.text_input("Código")
        nom = c2.text_input("Nombre Completo")
        finca = c3.text_input("Nombre Finca")
        ced = c1.text_input("Cédula / NIT")
        val = c2.number_input("Valor Litro Base ($)", value=1850.0)
        ciclo = c3.selectbox("Ciclo de Pago", ["Semanal", "Quincenal"])
        fede = st.checkbox("Aplica Fedegán (0.75%)")
        if st.form_submit_button("✅ Guardar Proveedor"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?,?,?)', (cod, nom, finca, ced, 1 if fede else 0, val, ciclo))
            conn.commit()
            st.success(f"Proveedor {nom} registrado correctamente.")

# --- 2. INGRESO DE LECHE ---
elif menu == "🥛 Ingreso de Leche":
    st.header("🥛 Ingreso de Leche")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    with st.form("f_r", clear_on_submit=True):
        p_sel = st.selectbox("Proveedor", provs['codigo'] + " - " + provs['nombre'] if not provs.empty else [])
        lts = st.number_input("Cantidad de Litros", min_value=0.0)
        silo = st.selectbox("Silo Destino", ["Silo 1", "Silo 2", "Silo 3", "Silo 4"])
        
        p_sug = 1850.0
        if p_sel:
            c_p = p_sel.split(" - ")[0]
            p_sug = provs[provs['codigo']==c_p]['valor_litro'].values[0]
        p_final = st.number_input("Precio Litro hoy", value=float(p_sug))
        
        if st.form_submit_button("🚀 Registrar Ingreso"):
            cod_p = p_sel.split(" - ")[0]
            conn.execute('UPDATE silos SET saldo = saldo + ? WHERE nombre = ?', (lts, silo))
            conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, precio_pactado, silo) VALUES (?,?,?,?,?)', (str(date.today()), cod_p, lts, p_final, silo))
            conn.commit()
            st.success("Leche ingresada al silo.")

# --- 3. LIQUIDACIÓN Y VOLANTES ---
elif menu == "💰 Liquidación y Volantes":
    st.header("💰 Liquidación y Relación de Pagos")
    ciclo_sel = st.radio("Ciclo:", ["Semanal", "Quincenal"], horizontal=True)
    conn = get_db_connection()
    query = f'''SELECT p.*, SUM(r.litros) as total_lts, AVG(r.precio_pactado) as precio_avg 
               FROM recibo_leche r JOIN proveedores p ON r.cod_prov = p.codigo 
               WHERE p.ciclo = '{ciclo_sel}' GROUP BY p.codigo'''
    df = pd.read_sql_query(query, conn)
    
    if not df.empty:
        df['Subtotal'] = df['total_lts'] * df['precio_avg']
        # FEDEGAN AL 0.75%
        df['Fedegan'] = df.apply(lambda x: x['Subtotal'] * 0.0075 if x['fedegan_bool'] == 1 else 0, axis=1)
        df['Neto a Pagar'] = df['Subtotal'] - df['Fedegan']
        
        st.dataframe(df[['codigo', 'nombre', 'finca', 'total_lts', 'precio_avg', 'Fedegan', 'Neto a Pagar']], use_container_width=True)
        
        st.subheader("🖨️ Imprimir Volante Individual")
        p_volante = st.selectbox("Seleccione para volante:", df['nombre'])
        if st.button("Generar Volante de Pago"):
            row = df[df['nombre'] == p_volante].iloc[0]
            st.info(f"RECIBO DE PAGO - LÁCTEOS SUIZA\n\nProveedor: {row['nombre']}\nFinca: {row['finca']}\nLitros: {row['total_lts']}\nSubtotal: ${row['Subtotal']:,.0f}\nFedegan (0.75%): ${row['Fedegan']:,.0f}\nTOTAL: ${row['Neto a Pagar']:,.0f}")
            st.caption("Use 'Ctrl+P' para imprimir este resumen.")
    else:
        st.info("No hay registros en este ciclo.")

# --- 4. PRODUCCIÓN ---
elif menu == "🏭 Producción":
    st.header("🏭 Transformación de Silos")
    conn = get_db_connection()
    silos = pd.read_sql_query("SELECT * FROM silos WHERE saldo > 0", conn)
    variedades = ["Queso Costeño Pasteurizado", "Queso Mozzarella", "Queso Pera", "Queso Sábana", "Queso Costeño Industrializado", "Queso Cheddar", "Suero Costeño", "Yogurt (Vaso)", "Yogurt (Bolsa)", "Arequipe", "Quesadillo"]
    
    with st.form("f_prod"):
        s_uso = st.selectbox("Origen (Silo)", silos['nombre'] if not silos.empty else ["Vacíos"])
        lts_u = st.number_input("Litros a procesar", min_value=0.0)
        prod = st.selectbox("Transformar a:", variedades)
        pres = st.selectbox("Presentación", ["Bloque 2.5Kg", "Bloque 5Kg", "Litro", "Vaso", "Bolsa"])
        cant = st.number_input("Cantidad Resultante (Kg/Und)", min_value=0.0)
        
        if st.form_submit_button("⚙️ Procesar Producción"):
            conn.execute('UPDATE silos SET saldo = saldo - ? WHERE nombre = ?', (lts_u, s_uso))
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (prod, pres, prod, pres, cant))
            conn.commit()
            st.success("Producción guardada en Kardex.")

# --- 5. TAJADO Y MERMA ---
elif menu == "🍽️ Tajado y Merma":
    st.header("🍽️ Tajado de Bloques")
    with st.form("f_t"):
        queso = st.selectbox("Variedad:", ["Mozzarella", "Sábana", "Pera", "Doble Crema", "Cheddar"])
        bloques = st.number_input("Número de bloques de 2.5kg", min_value=0)
        pres_sal = st.selectbox("Porción:", ["125g", "200g", "250g", "400g", "500g", "1000g", "1250g", "2500g"])
        
        if st.form_submit_button("⚖️ Ejecutar y Registrar"):
            merma = bloques * 0.200
            neto = (bloques * 2.5) - merma
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO kardex (producto, presentacion, stock) VALUES (?,?,(SELECT COALESCE(stock,0) FROM kardex WHERE producto=? AND presentacion=?)+?)', (queso + " Tajado", pres_sal, queso + " Tajado", pres_sal, neto))
            conn.execute('INSERT INTO log_tajado (fecha, producto, bloques, merma, neto) VALUES (?,?,?,?,?)', (str(date.today()), queso, bloques, merma, neto))
            conn.commit()
            st.warning(f"REGISTRO: Bloques: {bloques} | Merma: {merma}kg | Neto: {neto}kg")

elif menu == "📦 Kardex":
    st.header("📦 Kardex / Inventario")
    conn = get_db_connection()
    st.dataframe(pd.read_sql_query("SELECT * FROM kardex WHERE stock > 0", conn), use_container_width=True)

elif menu == "📊 Silos de Producción":
    st.header("📊 Nivel de Silos (10.000L)")
    conn = get_db_connection()
    df_s = pd.read_sql_query("SELECT * FROM silos", conn)
    cols = st.columns(4)
    for i, row in df_s.iterrows():
        cols[i].metric(row['nombre'], f"{row['saldo']} L")
        cols[i].progress(min(row['saldo']/10000, 1.0))
