import streamlit as st

# --- CONFIGURACIÓN VISUAL (Lácteos Zomac) ---
st.set_page_config(page_title="Lácteos María Zomac", layout="wide")

st.markdown("""
    <style>
    .header-zomac { background-color: #003366; padding: 20px; border-radius: 10px; text-align: center; color: white; }
    .logo-red { color: #FF0000; font-weight: bold; }
    </style>
    <div class='header-zomac'>
        <h1>LÁCTEOS DE <span class='logo-red'>MARÍA ZOMAC</span></h1>
        <p>Sistema de Gestión Centralizado</p>
    </div>
    """, unsafe_allow_status=True)

# --- MENÚ PRINCIPAL ---
st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", ["Dashboard", "Recibo de Leche", "Inventario Quesos"])

if opcion == "Dashboard":
    st.subheader("📊 Panel de Control General")
    st.info("Aquí verás los gráficos de producción de toda la empresa.")
    st.metric(label="Litros Recibidos Hoy", value="0 L", delta="0%")

elif opcion == "Recibo de Leche":
    st.subheader("🥛 Registro de Entrada de Leche (Planta)")
    with st.form("form_leche"):
        prov = st.text_input("Nombre del Proveedor")
        litros = st.number_input("Cantidad de Litros", min_value=0.0)
        boton = st.form_submit_button("Guardar Registro")
        if boton:
            st.success(f"✅ Registrado: {litros} L de {prov}")
            st.balloons()

elif opcion == "Inventario Quesos":
    st.subheader("🧀 Control de Cavas (Kardex)")
    st.write("Módulo de inventario activo.")
