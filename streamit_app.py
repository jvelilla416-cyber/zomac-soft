import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from fpdf import FPDF

st.set_page_config(layout="wide", page_title="Zomac - Planta y Producción")

def get_db_connection():
    conn = sqlite3.connect('zomac_planta.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- INICIALIZACIÓN ---
conn = get_db_connection()
conn.execute('CREATE TABLE IF NOT EXISTS proveedores (codigo TEXT PRIMARY KEY, nombre TEXT, precio_base REAL, fedegan INTEGER)')
conn.execute('CREATE TABLE IF NOT EXISTS recibo_leche (id INTEGER PRIMARY KEY, fecha TEXT, cod_prov TEXT, litros REAL, precio_dia REAL)')
conn.execute('CREATE TABLE IF NOT EXISTS kardex (producto TEXT PRIMARY KEY, presentacion TEXT, stock REAL)')
conn.execute('CREATE TABLE IF NOT EXISTS cuarto_frio (id INTEGER PRIMARY KEY, fecha TEXT, cantidad REAL, motivo TEXT)')
conn.commit()

st.sidebar.image("logo_suiza.png", width=150) # El logo de la vaquita
menu = st.sidebar.selectbox("Módulo Planta:", ["👥 Proveedores", "🥛 Recibo Leche", "💸 Liquidación", "🏭 Producción", "🍽️ Tajado"])

if menu == "👥 Proveedores":
    st.header("👥 Maestros de Proveedores")
    with st.form("f_p", clear_on_submit=True):
        c1, c2 = st.columns(2); cod = c1.text_input("Código"); nom = c2.text_input("Nombre")
        pre = c1.number_input("Precio Base", value=1850); fed = c2.checkbox("Descuento Fedegán")
        if st.form_submit_button("Guardar"):
            conn.execute('INSERT OR REPLACE INTO proveedores VALUES (?,?,?,?)', (cod, nom, pre, 1 if fed else 0))
            conn.commit(); st.success("Guardado y formulario limpio.")

elif menu == "🍽️ Tajado":
    st.header("🍽️ Tajado y Merma (200g/Bloque)")
    with st.form("f_t"):
        kg_in = st.number_input("Kilos de Bloque a tajar", min_value=0.0)
        formato = st.selectbox("Salida", ["125g", "250g", "500g", "1000g"])
        merma = (kg_in / 2.5) * 0.200 if kg_in > 0 else 0
        if st.form_submit_button("Procesar"):
            conn.execute('INSERT INTO cuarto_frio (fecha, cantidad, motivo) VALUES (?,?,"Merma Tajado")', (str(date.today()), merma))
            conn.commit(); st.warning(f"Merma de {merma:.2f}kg a Cuarto Frío.")