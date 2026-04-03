import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout="wide", page_title="Lácteos Zomac - Panel de Control")

# --- ESTILOS CSS PERSONALIZADOS (Panel Azul) ---
st.markdown("""
    <style>
    .reportview-container {
        background: #e6f3ff; /* Azul muy claro */
    }
    .sidebar .sidebar-content {
        background: #004080; /* Azul oscuro */
        color: white;
    }
    h1 {
        color: #004080; /* Azul oscuro */
        border-bottom: 2px solid #004080;
        padding-bottom: 10px;
    }
    .stButton>button {
        color: white;
        background-color: #0059b3;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ENCABEZADO PRINCIPAL (Panel Azul Zomac) ---
st.markdown("<div style='background-color:#004080;padding:20px;border-radius:10px'>"
            "<h1 style='color:white;text-align:center;border:none;'>🥛 LÁCTEOS DE MARÍA ZOMAC 🧀</h1>"
            "<p style='color:white;text-align:center;'>Sistema de Gestión de Inventario y Ventas</p>"
            "</div>", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE DATOS (Simulados para el inicio) ---
# En el futuro, esto se leerá de una base de datos o Google Sheets.
if 'productos' not in st.session_state:
    st.session_state.productos = pd.DataFrame(columns=['ID', 'Nombre', 'Categoría', 'Precio Venta', 'Stock'])
if 'ventas' not in st.session_state:
    st.session_state.ventas = pd.DataFrame(columns=['ID Venta', 'Fecha', 'Producto', 'Cantidad', 'Total'])

# --- MENÚ DE NAVEGACIÓN LATERAL ---
st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", ["📊 Panel Principal (Resumen)", "📦 Inventario de Productos", "💰 Registro de Ventas", "📈 Reportes y Gráficos"])

# ==========================================
# 📊 PANEL PRINCIPAL (RESUMEN)
# ==========================================
if opcion == "📊 Panel Principal (Resumen)":
    st.header("📊 Resumen del Negocio")
    
    # Métricas clave en columnas
    col1, col2, col3 = st.columns(3)
    
    total_productos = len(st.session_state.productos)
    total_ventas_hoy = len(st.session_state.ventas) # Faltaría filtrar por fecha real
    ingresos_totales = st.session_state.ventas['Total'].sum()

    col1.metric("Productos Registrados", total_productos)
    col2.metric("Ventas de Hoy", total_ventas_hoy)
    col3.metric("Ingresos Totales (COP)", f"${ingresos_totales:,.2f}")

    st.markdown("---")
    st.subheader("⚠️ Alertas de Inventario Bajo")
    # Mostrar productos con stock bajo (ej. < 5)
    productos_bajos = st.session_state.productos[st.session_state.productos['Stock'] < 5]
    if not productos_bajos.empty:
        st.warning("Los siguientes productos tienen stock bajo:")
        st.dataframe(productos_bajos[['Nombre', 'Stock']])
    else:
        st.success("El stock de todos los productos está OK.")

# ==========================================
# 📦 INVENTARIO DE PRODUCTOS
# ==========================================
elif opcion == "📦 Inventario de Productos":
    st.header("📦 Gestión de Inventario")

    # Formulario para agregar producto
    with st.expander("➕ Agregar Nuevo Producto"):
        col1, col2 = st.columns(2)
        with col1:
            nuevo_id = st.text_input("ID del Producto (Ej. Q001)")
            nuevo_nombre = st.text_input("Nombre del Producto (Ej. Queso Costeño)")
        with col2:
            nueva_categoria = st.selectbox("Categoría", ["Leche Larga Vida", "Quesos Frescos", "Mantequillas", "Sueros", "Otros"])
            nuevo_precio = st.number_input("Precio de Venta (COP)", min_value=0, step=100)
            nuevo_stock = st.number_input("Stock Inicial", min_value=0, step=1)

        if st.button("Guardar Producto"):
            if nuevo_id and nuevo_nombre and nuevo_precio > 0:
                # Verificar si el ID ya existe
                if nuevo_id in st.session_state.productos['ID'].values:
                    st.error(f"El ID '{nuevo_id}' ya existe. Usa uno diferente.")
                else:
                    nuevo_prod = pd.DataFrame([[nuevo_id, nuevo_nombre, nueva_categoria, nuevo_precio, nuevo_stock]], 
                                            columns=['ID', 'Nombre', 'Categoría', 'Precio Venta', 'Stock'])
                    st.session_state.productos = pd.concat([st.session_state.productos, nuevo_prod], ignore_index=True)
                    st.success(f"Producto '{nuevo_nombre}' agregado correctamente.")
            else:
                st.warning("Por favor, rellena los campos obligatorios (ID, Nombre y Precio).")

    st.markdown("---")
    st.subheader("📋 Lista Actual de Productos")
    st.dataframe(st.session_state.productos, use_container_width=True)

# ==========================================
# 💰 REGISTRO DE VENTAS
# ==========================================
elif opcion == "💰 Registro de Ventas":
    st.header("💰 Registrar Nueva Venta")

    if st.session_state.productos.empty:
        st.warning("Primero debes agregar productos al inventario para poder vender.")
    else:
        # Formulario de venta
        with st.form("form_venta"):
            col1, col2, col3 = st.columns(3)
            with col1:
                # Selector de producto de la lista existente
                lista_productos = st.session_state.productos['Nombre'].tolist()
                producto_seleccionado = st.selectbox("Seleccionar Producto", lista_productos)
            with col2:
                cantidad_venta = st.number_input("Cantidad", min_value=1, step=1)
            with col3:
                # Obtener precio y stock actual
                info_prod = st.session_state.productos[st.session_state.productos['Nombre'] == producto_seleccionado].iloc[0]
                precio_unitario = info_prod['Precio Venta']
                stock_actual = info_prod['Stock']
                st.write(f"**Precio:** ${precio_unitario:,.2f}")
                st.write(f"**Stock Disponible:** {stock_actual}")

            submit_venta = st.form_submit_button("Confirmar Venta")

            if submit_venta:
                if cantidad_venta > stock_actual:
                    st.error(f"No hay suficiente stock. Solo quedan {stock_actual} unidades.")
                else:
                    # Calcular total y guardar venta
                    total_venta = cantidad_venta * precio_unitario
                    nueva_venta = pd.DataFrame([[f"V{len(st.session_state.ventas)+1:03d}", pd.Timestamp.now(), producto_seleccionado, cantidad_venta, total_venta]],
                                                columns=['ID Venta', 'Fecha', 'Producto', 'Cantidad', 'Total'])
                    st.session_state.ventas = pd.concat([st.session_state.ventas, nueva_venta], ignore_index=True)
                    
                    # Actualizar stock
                    st.session_state.productos.loc[st.session_state.productos['Nombre'] == producto_seleccionado, 'Stock'] -= cantidad_venta
                    
                    st.success(f"Venta de {cantidad_venta} {producto_seleccionado}(s) registrada. Total: ${total_venta:,.2f}")

    st.markdown("---")
    st.subheader("📋 Historial de Ventas")
    st.dataframe(st.session_state.ventas, use_container_width=True)

# ==========================================
# 📈 REPORTES Y GRÁFICOS
# ==========================================
elif opcion == "📈 Reportes y Gráficos":
    st.header("📈 Reportes de Rendimiento")

    if st.session_state.ventas.empty:
        st.info("No hay ventas registradas para generar reportes.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💰 Ingresos por Producto")
            ventas_por_prod = st.session_state.ventas.groupby('Producto')['Total'].sum().sort_values(ascending=False)
            st.bar_chart(ventas_por_prod)
            st.write(ventas_por_prod)

        with col2:
            st.subheader("📦 Unidades Vendidas por Producto")
            unidades_por_prod = st.session_state.ventas.groupby('Producto')['Cantidad'].sum().sort_values(ascending=False)
            # Ejemplo usando Matplotlib para un gráfico de pastel
            fig, ax = plt.subplots()
            ax.pie(unidades_por_prod, labels=unidades_por_prod.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')  # Asegura que el pastel sea circular
            st.pyplot(fig)
            st.write(unidades_por_prod)

# --- PIE DE PÁGINA ---
st.markdown("---")
st.caption("© 2023 Lácteos de María Zomac. Sistema desarrollado con Streamlit.")
