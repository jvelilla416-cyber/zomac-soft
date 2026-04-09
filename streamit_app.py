import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos Suiza - Control y Pagos")

def get_db_connection():
    # Usamos V8 para asegurar que las nuevas columnas de pago existan
    conn = sqlite3.connect('suiza_v8_pagos.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Proveedores (Añadimos Forma de Pago)
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores 
                 (codigo TEXT PRIMARY KEY, nombre TEXT, finca TEXT, ruta TEXT, 
                  precio_base REAL, ciclo TEXT, forma_pago TEXT, fedegan INTEGER, retencion INTEGER)''')
    # 2. Recibo de Leche (Con precio corregible)
    c.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, tanque TEXT, precio_aplicado REAL)')
    # 3. Tanques
    c.execute('CREATE TABLE IF NOT EXISTS tanques (nombre TEXT PRIMARY KEY, saldo REAL)')
    for t in ["Tanque 1", "Tanque 2", "Tanque 3"]:
        c.execute('INSERT OR IGNORE INTO tanques VALUES (?, 0)', (t,))
    conn.commit()
    conn.close()

init_db()

# --- SIDEBAR ---
st.sidebar.image("logo_suiza.png", width=150)
menu = st.sidebar.selectbox("Menú Principal:", ["📊 Tanques", "👥 Proveedores", "🥛 Recibo de Leche", "💰 Liquidación de Pagos", "🏭 Producción", "📦 Kardex"])

# --- 1. PROVEEDORES (CORREGIDO CON FORMA DE PAGO) ---
if menu == "👥 Proveedores":
    st.header("👥 Registro de Proveedores")
    with st.form("f_p", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cod = c1.text_input("Código")
        nom = c2.text_input("Nombre Dueño")
        finca = c3.text_input("Nombre Finca")
        ruta = c1.text_input("Ruta")
        pre = c2.number_input("Precio Base Sugerido", value=1850.0)
        ciclo = c3.selectbox("Ciclo de Pago", ["Semanal", "Quincenal"])
        pago = st.selectbox("Forma de Pago", ["Efectivo", "Transferencia Bancaria", "Cheque"])
        
        fede = st.checkbox("Descuento Fedegán ($10/L)")
        rete = st.checkbox("Aplica Retención (1.5%)")
        
        if st.form_submit_button("✅ Guardar/Actualizar"):
            conn = get_db_connection()
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?,?,?,?,?,?)', 
                         (cod, nom, finca, ruta, pre, ciclo, pago, 1 if fede else 0, 1 if rete else 0))
            conn.commit()
            st.success("Proveedor actualizado.")

# --- 2. RECIBO DE LECHE (PRECIO EDITABLE) ---
elif menu == "🥛 Recibo de Leche":
    st.header("🥛 Ingreso de Leche Diario")
    conn = get_db_connection()
    provs = pd.read_sql_query("SELECT * FROM proveedores", conn)
    
    with st.form("f_r", clear_on_submit=True):
        p_sel = st.selectbox("Seleccione Proveedor", provs['codigo'] + " - " + provs['finca'] if not provs.empty else [])
        lts = st.number_input("Litros recibidos", min_value=0.0)
        tanq = st.selectbox("Tanque Destino", ["Tanque 1", "Tanque 2", "Tanque 3"])
        
        # Buscar el precio base para sugerirlo
        precio_sug = 1850.0
        if p_sel:
            c_p = p_sel.split(" - ")[0]
            precio_sug = provs[provs['codigo']==c_p]['precio_base'].values[0]
            
        p_final = st.number_input("Precio a pagar por litro (Corregible)", value=float(precio_sug))
        
        if st.form_submit_button("🚀 Registrar Entrada"):
            cod_p = p_sel.split(" - ")[0]
            conn.execute('UPDATE tanques SET saldo = saldo + ? WHERE nombre = ?', (lts, tanq))
            conn.execute('INSERT INTO recibo_leche (fecha, cod_prov, litros, tanque, precio_aplicado) VALUES (?,?,?,?,?)', 
                         (str(date.today()), cod_p, lts, tanq, p_final))
            conn.commit()
            st.success(f"Registrados {lts}L a ${p_final}")

# --- 3. LIQUIDACIÓN DE PAGOS (LO NUEVO) ---
elif menu == "💰 Liquidación de Pagos":
    st.header("💰 Liquidación de Proveedores")
    tipo_liq = st.radio("Filtro de Ciclo:", ["Semanal", "Quincenal"], horizontal=True)
    
    conn = get_db_connection()
    # Consulta que suma litros y calcula valores
    query = f'''
        SELECT p.codigo, p.nombre, p.finca, p.forma_pago,
               SUM(r.litros) as total_litros, 
               AVG(r.precio_aplicado) as precio_promedio,
               SUM(r.litros * r.precio_aplicado) as valor_bruto,
               p.fedegan, p.retencion
        FROM recibo_leche r 
        JOIN proveedores p ON r.cod_prov = p.codigo
        WHERE p.ciclo = '{tipo_liq}'
        GROUP BY p.codigo
    '''
    df_liq = pd.read_sql_query(query, conn)
    
    if not df_liq.empty:
        # Cálculos de descuentos
        df_liq['Desc_Fedegan'] = df_liq.apply(lambda x: x['total_litros'] * 10 if x['fedegan'] == 1 else 0, axis=1)
        df_liq['Valor_Neto'] = df_liq['valor_bruto'] - df_liq['Desc_Fedegan']
        
        # Aplicar retención si pasa el tope (aprox 3.6M)
        df_liq['Retencion_1.5'] = df_liq.apply(lambda x: x['Valor_Neto'] * 0.015 if (x['retencion'] == 1 and x['Valor_Neto'] > 3666000) else 0, axis=1)
        df_liq['TOTAL_A_PAGAR'] = df_liq['Valor_Neto'] - df_liq['Retencion_1.5']
        
        # Mostrar tabla limpia para el usuario
        st.subheader(f"Relación de Pagos - Ciclo {tipo_liq}")
        tabla_final = df_liq[['codigo', 'nombre', 'finca', 'total_litros', 'precio_promedio', 'TOTAL_A_PAGAR', 'forma_pago']]
        st.dataframe(tabla_final.style.format({"precio_promedio": "${:,.2f}", "TOTAL_A_PAGAR": "${:,.0f}"}), use_container_width=True)
        
        if st.button("📥 Descargar Liquidación (CSV)"):
            tabla_final.to_csv(f"liquidacion_{tipo_liq}_{date.today()}.csv", index=False)
            st.success("Archivo listo para Excel.")
    else:
        st.info(f"No hay leche registrada para el ciclo {tipo_liq} todavía.")

# (Resto de módulos de Tanques y Kardex se mantienen iguales)
