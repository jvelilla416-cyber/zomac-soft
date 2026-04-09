# --- 3. LIQUIDACIÓN Y VOLANTES PDF / EXCEL ---
elif menu == "💰 Liquidación y Volantes":
    st.header("💰 Liquidación y Reportes de Pago")
    ciclo_sel = st.radio("Seleccione Ciclo:", ["Semanal", "Quincenal"], horizontal=True)
    conn = get_db_connection()
    
    # Consulta Maestra
    query = f'''SELECT p.*, SUM(r.litros) as total_lts FROM recibo_leche r 
               JOIN proveedores p ON r.cod_prov = p.codigo WHERE p.ciclo = '{ciclo_sel}' GROUP BY p.codigo'''
    df_resumen = pd.read_sql_query(query, conn)
    
    if not df_resumen.empty:
        # Cálculos de dinero
        df_resumen['Subtotal'] = df_resumen['total_lts'] * df_resumen['valor_litro']
        df_resumen['Fedegan'] = df_resumen.apply(lambda x: x['Subtotal'] * 0.0075 if x['fedegan_bool'] == 1 else 0, axis=1)
        df_resumen['Neto'] = df_resumen['Subtotal'] - df_resumen['Fedegan']
        
        st.subheader(f"📋 Relación Grupal - {ciclo_sel}")
        st.dataframe(df_resumen[['codigo', 'nombre', 'finca', 'total_lts', 'Neto']], use_container_width=True)
        
        # --- BOTÓN PARA DESCARGAR REPORTE GENERAL ---
        csv = df_resumen.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 DESCARGAR RELACIÓN GENERAL (EXCEL/CSV)",
            data=csv,
            file_name=f'Relacion_Ganaderos_{ciclo_sel}_{date.today()}.csv',
            mime='text/csv',
        )
        
        st.divider()
        
        # --- VOLANTE INDIVIDUAL ---
        st.subheader("🖨️ Imprimir Volante por Ganadero")
        p_escogido = st.selectbox("Escoger Ganadero:", df_resumen['nombre'])
        
        if st.button("📄 Generar Datos de Volante"):
            p_data = df_resumen[df_resumen['nombre'] == p_escogido].iloc[0].to_dict()
            hist = pd.read_sql_query(f"SELECT fecha, litros, precio FROM recibo_leche WHERE cod_prov = '{p_data['codigo']}'", conn)
            
            # Mostrar en pantalla para imprimir con Ctrl+P si el PDF falla
            st.info(f"PREPARADO: {p_escogido} - {p_data['finca']}")
            pdf_bytes = generar_volante_pdf(p_data, hist)
            
            st.download_button(
                label=f"💾 DESCARGAR PDF DE {p_escogido}",
                data=pdf_bytes,
                file_name=f"Volante_{p_escogido}.pdf",
                mime="application/pdf"
            )
    else:
        st.info("No hay entregas registradas para este ciclo.")
