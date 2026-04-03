import streamlit as st

# --- CONFIGURACIÓN VISUAL (Lácteos Zomac) ---
st.set_page_config(page_title="Zomac-Soft", layout="wide")

st.markdown("""
    <style>
    .header-zomac { background-color: #003366; padding: 20px; border-radius: 10px; text-align: center; color: white; }
    .logo-red { color: #FF0000; font-weight: bold; }
    </style>
    <div class='header-zomac'>
        <h1>LÁCTEOS DE <span class='logo-red'>MARÍA ZOMAC</span></h1>
        <p>Panel de Gestión Empresarial</p>
    </div>
    """, unsafe_allow_status=True)

# --- MENÚ PRINCIPAL ---
st.sidebar.title("MENÚ")
opcion = st.sidebar.radio("Navegación", ["Inicio", "Recibo de Leche", "Inventario Quesos", "Despachos"])

if opcion == "Inicio":
    st.subheader("📊 Resumen Gerencial")
    st.info("Seleccione un módulo a la izquierda para ver más detalles.")
    # Métricas de ejemplo (puedes personalizarlas)
    col1, col2 = st.columns(2)
    col1.metric("Litros Hoy", "150 L", "10%")
    col2.metric("Quesos fabricados", "25", "5%")

elif opcion == "Recibo de Leche":
    st.subheader("🥛 Registro de Entrada (Planta)")
    with st.form("form_leche"):
        prov = st.text_input("Nombre del Proveedor")
        litros = st.number_input("Cantidad de Litros", min_value=0.0)
        boton = st.form_submit_button("Guardar Registro")
        if boton:
            st.success(f"✅ Registrado: {litros}L de {prov}")
            st.balloons()

elif opcion == "Inventario Quesos":
    st.subheader("🧀 Control de Cavas (Kardex)")
    st.selectbox("Producto", ["Queso Costeño", "Mozzarella", "Cuajada"])
    st.number_input("Unidades en existencia", min_value=0)
    st.button("Actualizar Stock")

elif opcion == "Despachos":
    st.subheader("🚛 Salida de Producto Terminado")
    st.text_input("Cliente")
    st.date_input("Fecha")
    st.button("Generar Remisión")
