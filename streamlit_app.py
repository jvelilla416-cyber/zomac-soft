import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Lácteos de María - Sistema Protegido", page_icon="🛡️")

def get_db_connection():
    # Usamos el nombre de la base de datos maestra
    conn = sqlite3.connect('lacteos_maria_v6.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- FUNCIÓN DE COPIA DE SEGURIDAD (EXPORTAR A EXCEL) ---
def generar_respaldo():
    conn = get_db_connection()
    output = io.BytesIO()
    # Creamos un archivo Excel con varias pestañas (Proveedores, Leche, Kardex)
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.read_sql_query("SELECT * FROM proveedores", conn).to_excel(writer, sheet_name='Proveedores', index=False)
        pd.read_sql_query("SELECT * FROM entrada_leche", conn).to_excel(writer, sheet_name='Entrada_Leche', index=False)
        pd.read_sql_query("SELECT * FROM inventario", conn).to_excel(writer, sheet_name='Kardex_Inventario', index=False)
        pd.read_sql_query("SELECT * FROM produccion", conn).to_excel(writer, sheet_name='Produccion', index=False)
        pd.read_sql_query("SELECT * FROM despachos", conn).to_excel(writer, sheet_name='Despachos', index=False)
    
    return output.getvalue()

# --- NAVEGACIÓN Y BOTÓN DE SEGURIDAD ---
st.sidebar.title("🥛 LÁCTEOS DE MARÍA")

# --- BOTÓN DE RESPALDO (SIEMPRE VISIBLE PARA EL DUEÑO) ---
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Seguridad de Datos")
datos_excel = generar_respaldo()
st.sidebar.download_button(
    label="📥 Descargar Copia de Seguridad (Excel)",
    data=datos_excel,
    file_name=f"Respaldo_Lacteos_Maria_{date.today()}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="Haz clic aquí para bajar toda la información a tu PC en formato Excel."
)
st.sidebar.markdown("---")

# ... (El resto de los módulos que ya tenemos: Gestión, Recibo, Transformación, etc.)
