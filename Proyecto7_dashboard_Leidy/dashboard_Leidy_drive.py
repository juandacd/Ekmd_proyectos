import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import BytesIO

# Logo en la esquina superior
top_col1, top_col2 = st.columns([0.7,0.3])
with top_col2:
    st.image("https://ekonomodo.com/cdn/shop/files/Logo-Ekonomodo-color.svg?v=1736956350&width=450", width=5000)

st.set_page_config(page_title="Dashboard Pedidos Ekonomodo", layout="wide")
st.title("Dashboard de Pedidos - Ekonomodo CEO")

# ======================
# Funciones auxiliares
# ======================
def add_week_indicators(df):
    """Agregar indicadores de semana del año a las columnas de fecha"""
    date_columns = ["FECHA DE ORDEN", "FECHA DE DESPACHO INTERNO", "FECHA VENC"]
    
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            df[f"{col}_SEMANA"] = df[col].dt.isocalendar().week
            df[f"{col}_AÑO"] = df[col].dt.year
            df[f"{col}_SEMANA_AÑO"] = df[f"{col}_AÑO"].astype(str) + "-S" + df[f"{col}_SEMANA"].astype(str).str.zfill(2)
    
    return df

def format_metric_card(title, value, delta=None, delta_color="normal"):
    """Crear tarjeta de métrica personalizada"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.metric(title, value, delta=delta, delta_color=delta_color)

# ======================
# Cargar datos
# ======================
st.sidebar.header("🔧 Configuración")

# Función para cargar desde Google Sheets
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_google_sheet(url):
    # Convertir URL de Google Sheets a formato de exportación
    file_id = url.split('/d/')[1].split('/')[0]
    export_url = f'https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx'
    
    response = requests.get(export_url)
    return pd.read_excel(BytesIO(response.content), sheet_name="BASE")

# URL de tu Google Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1L_gT_jKH_7KKqdqj_tVm5IeWHVO2fYOr5UvKUp6uZmo/edit?usp=sharing"

# Botón para forzar actualización
if st.sidebar.button("🔄 Actualizar Datos"):
    st.cache_data.clear()
    st.rerun()

if SHEET_URL:
    try:
        df_original = load_google_sheet(SHEET_URL)  # Guardar copia original
        df = df_original.copy()  # Trabajar con copia
        
        # Normalizamos nombres de columnas (eliminar espacios y convertir a mayúsculas)
        df.columns = df.columns.astype(str).str.strip().str.upper()
        
        # Agregar indicadores de semana
        df = add_week_indicators(df)

        # Limpiar columna # FACTURA ANTES de filtrar
        if "# FACTURA" in df.columns:
            df["# FACTURA"] = df["# FACTURA"].astype(str).str.strip().str.upper()
            df["# FACTURA"] = df["# FACTURA"].replace(["", "#N/A", "#N/D", "NAN", "NONE"], pd.NA)
            df["# FACTURA"] = pd.to_numeric(df["# FACTURA"], errors='coerce')
        
        # Guardar dataframe completo (con cancelados) para alertas
        df_completo = df.copy()
        
        # Excluir pedidos cancelados SOLO del df de trabajo
        if "DESPACHADO" in df.columns:
            df = df[~df["DESPACHADO"].astype(str).str.strip().str.upper().str.contains("CANCELADO", na=False)]

        # Excluir pedidos cancelados de todos los análisis
        if "DESPACHADO" in df.columns:
            df = df[~df["DESPACHADO"].astype(str).str.strip().str.upper().str.contains("CANCELADO", na=False)]
        
        # AGREGAR AQUÍ: Limpiar y convertir columna # FACTURA
        if "# FACTURA" in df.columns:
            # Convertir todo a string primero
            df["# FACTURA_ORIGINAL"] = df["# FACTURA"].copy()  # Guardar original
            df["# FACTURA"] = df["# FACTURA"].astype(str).str.strip().str.upper()
            
            # Reemplazar valores vacíos y #N/A por NaN
            df["# FACTURA"] = df["# FACTURA"].replace(["", "#N/A", "#N/D", "NAN", "NONE"], pd.NA)
            
            # Convertir a numérico (los que se puedan)
            df["# FACTURA"] = pd.to_numeric(df["# FACTURA"], errors='coerce')

        # Cargar catálogo de productos desde la misma hoja de Google Sheets
        catalog_df = None
        try:
            # Función para cargar la hoja de catálogo
            @st.cache_data(ttl=300)
            def load_catalog_sheet(url):
                file_id = url.split('/d/')[1].split('/')[0]
                export_url = f'https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx'
                response = requests.get(export_url)
                return pd.read_excel(BytesIO(response.content), sheet_name="LISTA DE PRECIOS")
            
            catalog_df = load_catalog_sheet(SHEET_URL)
            catalog_df.columns = catalog_df.columns.astype(str).str.strip().str.upper()
            st.sidebar.success("✅ Catálogo cargado correctamente desde Google Sheets")
        except Exception as e:
            st.sidebar.warning(f"No se pudo cargar el catálogo: {str(e)}")
        
        # ======================
        # Filtros en sidebar
        # ======================
        st.sidebar.subheader("📅 Filtros")
        
        # Filtro por plataforma
        if "PLATAFORMA" in df.columns:
            plataformas = ["Todas"] + sorted(df["PLATAFORMA"].dropna().unique().tolist())
            selected_plataforma = st.sidebar.selectbox("Filtrar por Plataforma:", plataformas)
            if selected_plataforma != "Todas":
                df = df[df["PLATAFORMA"] == selected_plataforma]
        
        # Filtro por comercial
        if "COMERCIAL" in df.columns:
            comerciales = ["Todos"] + sorted(df["COMERCIAL"].dropna().unique().tolist())
            selected_comercial = st.sidebar.selectbox("Filtrar por Comercial:", comerciales)
            if selected_comercial != "Todos":
                df = df[df["COMERCIAL"] == selected_comercial]
        
        # Filtro por bodega
        if "BODEGA" in df.columns:
            bodegas = ["Todas"] + sorted(df["BODEGA"].dropna().unique().tolist())
            selected_bodega = st.sidebar.selectbox("Filtrar por Bodega:", bodegas)
            if selected_bodega != "Todas":
                df = df[df["BODEGA"] == selected_bodega]
        
        # Filtro por semana del año
        if "FECHA DE ORDEN_SEMANA_AÑO" in df.columns:
            semanas_disponibles = ["Todas"] + sorted(df["FECHA DE ORDEN_SEMANA_AÑO"].dropna().unique().tolist(), reverse=True)
            selected_semana = st.sidebar.selectbox("Filtrar por Semana de Orden:", semanas_disponibles)
            if selected_semana != "Todas":
                df = df[df["FECHA DE ORDEN_SEMANA_AÑO"] == selected_semana]
        
        # Filtro por rango de fechas
        if "FECHA DE ORDEN" in df.columns:
            min_date = df["FECHA DE ORDEN"].min()
            max_date = df["FECHA DE ORDEN"].max()
            if pd.notna(min_date) and pd.notna(max_date):
                date_range = st.sidebar.date_input(
                    "Rango de fechas de orden:",
                    value=(min_date.date(), max_date.date()),
                    min_value=min_date.date(),
                    max_value=max_date.date()
                )
                if len(date_range) == 2:
                    start_date, end_date = date_range
                    df = df[(df["FECHA DE ORDEN"].dt.date >= start_date) & 
                           (df["FECHA DE ORDEN"].dt.date <= end_date)]
        
        # ======================
        # KPIs principales
        # ======================
        st.subheader("KPIs Principales")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # 1. Pedidos no facturados
        no_facturados = df[
            (df["# FACTURA"].isna()) | 
            (df["# FACTURA"] == 0) | 
            (df["# FACTURA"].astype(str).str.upper().isin(["#N/D", "0"]))
        ]
        
        # 2. Pedidos no despachados
        if "GUIA" in df.columns:
            no_despachados = df[
                (df["# FACTURA"].notna()) &
                (df["# FACTURA"] != 0) &
                (~df["# FACTURA"].astype(str).str.upper().isin(["#N/D", "0"])) &
                ((df["GUIA"].isna()) | 
                (df["GUIA"] == 0) | 
                (df["GUIA"].astype(str).str.upper().isin(["", "CANCELADO", "0"])))
            ]
        else:
            no_despachados = pd.DataFrame()
            st.warning("No se encontró la columna 'GUIA' en el archivo.")
        
        # 3. Alerta de vencimiento (solo pedidos no despachados)
        hoy = datetime.today()
        if "FECHA VENC" in df.columns:
            # Filtrar solo pedidos que NO han sido despachados Y que vencen en los próximos 3 días
            alerta_vencimiento = df[
                (df["FECHA VENC"].notna()) & 
                (df["FECHA VENC"] >= hoy) &  # Que no hayan vencido ya
                (df["FECHA VENC"] <= hoy + timedelta(days=3)) &  # Que venzan en 3 días o menos
                (  # Y que NO estén despachados (misma lógica de no_despachados)
                    (df["# FACTURA"].isna()) | 
                    (df["# FACTURA"] == 0) | 
                    (df["# FACTURA"].astype(str).str.upper().isin(["#N/D", "0"])) |
                    ((df["GUIA"].isna()) | 
                    (df["GUIA"] == 0) | 
                    (df["GUIA"].astype(str).str.upper().isin(["", "CANCELADO", "0"])))
                )
            ]
        else:
            alerta_vencimiento = pd.DataFrame()
        
        # 4. Tiempo de entrega promedio
        if "FECHA DE ORDEN" in df.columns and "FECHA DE DESPACHO INTERNO" in df.columns:
            df["TIEMPO_ENTREGA"] = (df["FECHA DE DESPACHO INTERNO"] - df["FECHA DE ORDEN"]).dt.days
            tiempo_entrega_prom = df["TIEMPO_ENTREGA"].mean(skipna=True)
        else:
            tiempo_entrega_prom = None
        
        with col1:
            st.metric("🚫 No Facturados", len(no_facturados))
        with col2:
            st.metric("📦 No Despachados", len(no_despachados))
        with col3:
            st.metric("⚠️ Por Vencer (≤3 días)", len(alerta_vencimiento))
        with col4:
            if tiempo_entrega_prom is not None:
                st.metric("⏱️ Tiempo Promedio (días)", f"{tiempo_entrega_prom:.1f}")
            else:
                st.metric("⏱️ Tiempo Promedio", "N/A")
        
        # ======================
        # Análisis detallado
        # ======================
        
        # Crear pestañas para mejor organización
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
            "📋 No Facturados", 
            "📦 No Despachados", 
            "🏪 Por Comercio", 
            "⚠️ Alertas", 
            "📊 Análisis", 
            "📈 Gráficos",
            "💰 Fletes",
            "💵 Ventas",
            "🏆 Top Productos"
        ])
        
        with tab1:
            st.subheader("1. Pedidos No Facturados")
            st.write(f"Total: **{len(no_facturados)}** pedidos")
            
            if len(no_facturados) > 0:
                # Resumen por plataforma
                if "PLATAFORMA" in no_facturados.columns:
                    resumen_no_fact = no_facturados["PLATAFORMA"].value_counts().reset_index()
                    resumen_no_fact.columns = ["PLATAFORMA", "Cantidad de Pedidos"]
                    st.write("**Por Plataforma:**")
                    st.dataframe(resumen_no_fact)
                
                st.write("**Detalle:**")
                columns_to_show = ["ORDEN", "PLATAFORMA", "COMERCIAL", "FECHA DE ORDEN", 
                                 "FECHA DE ORDEN_SEMANA_AÑO", "SKU CLIENTE", "BODEGA"]
                available_cols = [col for col in columns_to_show if col in no_facturados.columns]
                st.dataframe(no_facturados[available_cols], use_container_width=True)
        
        with tab2:
            st.subheader("2. Pedidos No Despachados (Facturados)")
            st.write(f"Total: **{len(no_despachados)}** pedidos")
            
            if len(no_despachados) > 0:
                # Resumen por plataforma
                if "PLATAFORMA" in no_despachados.columns:
                    resumen_no_desp = no_despachados["PLATAFORMA"].value_counts().reset_index()
                    resumen_no_desp.columns = ["PLATAFORMA", "Cantidad de Pedidos"]
                    st.write("**Por Plataforma:**")
                    st.dataframe(resumen_no_desp)
                
                st.write("**Detalle:**")
                columns_to_show = ["ORDEN", "PLATAFORMA", "COMERCIAL", "# FACTURA", 
                                 "FECHA DE ORDEN", "FECHA DE ORDEN_SEMANA_AÑO", "BODEGA", "GUIA"]
                available_cols = [col for col in columns_to_show if col in no_despachados.columns]
                st.dataframe(no_despachados[available_cols], use_container_width=True)
        
        with tab3:
            st.subheader("3. Pendientes por Despachar por Comercio")
            
            # Análisis por plataforma
            if "PLATAFORMA" in no_despachados.columns:
                pendientes_por_comercio = no_despachados.groupby("PLATAFORMA").size().reset_index(name="Pendientes")
                pendientes_por_comercio = pendientes_por_comercio.sort_values("Pendientes", ascending=False)
                st.dataframe(pendientes_por_comercio, use_container_width=True)
            
            # Análisis por comercial
            if "COMERCIAL" in no_despachados.columns:
                st.write("**Por Comercial:**")
                pendientes_por_vendedor = no_despachados.groupby("COMERCIAL").size().reset_index(name="Pendientes")
                pendientes_por_vendedor = pendientes_por_vendedor.sort_values("Pendientes", ascending=False)
                st.dataframe(pendientes_por_vendedor, use_container_width=True)
        
        with tab4:
            st.subheader("4. Alertas de Vencimiento (≤ 3 días)")
            st.write(f"Total: **{len(alerta_vencimiento)}** pedidos")
            
            if len(alerta_vencimiento) > 0:
                # Agregar días restantes
                alerta_vencimiento = alerta_vencimiento.copy()
                alerta_vencimiento["DIAS_RESTANTES"] = (alerta_vencimiento["FECHA VENC"] - pd.Timestamp.now()).dt.days
                
                columns_to_show = ["ORDEN", "PLATAFORMA", "COMERCIAL", "FECHA VENC", 
                                 "DIAS_RESTANTES", "# FACTURA", "GUIA", "DESPACHADO"]
                available_cols = [col for col in columns_to_show if col in alerta_vencimiento.columns]
                st.dataframe(alerta_vencimiento[available_cols].sort_values("DIAS_RESTANTES"), 
                           use_container_width=True)
                
            st.markdown("---")
            st.subheader("🚨 Pedidos Cancelados pero Facturados")
            st.write("⚠️ Estos pedidos fueron cancelados pero tienen factura. Requieren revisión.")
            
            # Detectar pedidos cancelados con factura (usando df_completo)
            pedidos_cancelados_facturados = df_completo[
                (df_completo["DESPACHADO"].astype(str).str.strip().str.upper() == "CANCELADO") &
                (df_completo["# FACTURA"].notna()) &
                (df_completo["# FACTURA"] > 0)
            ]
            
            st.write(f"Total: **{len(pedidos_cancelados_facturados)}** pedidos")
            
            if len(pedidos_cancelados_facturados) > 0:
                # Mostrar tabla con los casos problemáticos
                columns_to_show = ["ORDEN", "PLATAFORMA", "COMERCIAL", "# FACTURA", 
                                 "DESPACHADO", "FECHA DE ORDEN", "GUIA", "BODEGA"]
                available_cols = [col for col in columns_to_show if col in pedidos_cancelados_facturados.columns]
                
                # Crear copia para formatear
                df_display = pedidos_cancelados_facturados[available_cols].copy()
                
                # Formatear columnas numéricas sin decimales
                if "ORDEN" in df_display.columns:
                    df_display["ORDEN"] = df_display["ORDEN"].apply(lambda x: f"{int(x)}" if pd.notna(x) else x)
                if "# FACTURA" in df_display.columns:
                    df_display["# FACTURA"] = df_display["# FACTURA"].apply(lambda x: f"{int(x)}" if pd.notna(x) else x)
                
                st.dataframe(
                    df_display.style.apply(
                        lambda x: ['background-color: #ffcccc'] * len(x), axis=1
                    ),
                    use_container_width=True
                )
                
                # Resumen por plataforma
                if "PLATAFORMA" in pedidos_cancelados_facturados.columns:
                    st.write("**Casos por Plataforma:**")
                    casos_por_plataforma = pedidos_cancelados_facturados["PLATAFORMA"].value_counts().reset_index()
                    casos_por_plataforma.columns = ["PLATAFORMA", "Cantidad de Casos"]
                    st.dataframe(casos_por_plataforma, use_container_width=True)
            else:
                st.success("✅ No hay pedidos cancelados con factura")
        
        with tab5:
            st.subheader("5. Análisis de Tiempos de Entrega")
            
            if tiempo_entrega_prom is not None:
                entrega_stats = df["TIEMPO_ENTREGA"].describe()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Estadísticas:**")
                    st.write(f"- Promedio: {entrega_stats['mean']:.1f} días")
                    st.write(f"- Mediana: {entrega_stats['50%']:.1f} días")
                    st.write(f"- Mínimo: {entrega_stats['min']:.0f} días")
                    st.write(f"- Máximo: {entrega_stats['max']:.0f} días")
                
                with col2:
                    if "PLATAFORMA" in df.columns:
                        tiempo_por_plataforma = df.groupby("PLATAFORMA")["TIEMPO_ENTREGA"].mean().sort_values(ascending=False)
                        st.write("**Tiempo promedio por Plataforma:**")
                        st.dataframe(tiempo_por_plataforma.round(1))
                
                # Mostrar pedidos con tiempos calculados
                columns_to_show = ["ORDEN", "PLATAFORMA", "FECHA DE ORDEN", "FECHA DE DESPACHO INTERNO", 
                                 "TIEMPO_ENTREGA", "FECHA DE ORDEN_SEMANA_AÑO"]
                available_cols = [col for col in columns_to_show if col in df.columns]
                df_tiempo = df[df["TIEMPO_ENTREGA"].notna()][available_cols]
                st.dataframe(df_tiempo.sort_values("TIEMPO_ENTREGA", ascending=False), use_container_width=True)
            else:
                st.warning("No se pueden calcular tiempos de entrega. Verificar columnas de fecha.")
        
        with tab6:
            st.subheader("📈 Visualizaciones")
            
            # Gráfico de pedidos por semana
            if "FECHA DE ORDEN_SEMANA_AÑO" in df.columns:
                pedidos_por_semana = df["FECHA DE ORDEN_SEMANA_AÑO"].value_counts().sort_index()
                
                fig1 = px.bar(
                    x=pedidos_por_semana.index, 
                    y=pedidos_por_semana.values,
                    title="Pedidos por Semana del Año",
                    labels={"x": "Semana", "y": "Número de Pedidos"}
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            # Gráfico de estado de pedidos
            estados = []
            if len(no_facturados) > 0:
                estados.append(("No Facturados", len(no_facturados)))
            if len(no_despachados) > 0:
                estados.append(("Facturados No Despachados", len(no_despachados)))
            
            despachados = len(df) - len(no_facturados) - len(no_despachados)
            if despachados > 0:
                estados.append(("Despachados", despachados))
            
            if estados:
                fig2 = px.pie(
                    values=[x[1] for x in estados],
                    names=[x[0] for x in estados],
                    title="Estado de Pedidos"
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Gráfico por plataforma
            if "PLATAFORMA" in df.columns:
                pedidos_por_plataforma = df["PLATAFORMA"].value_counts()
                fig3 = px.bar(
                    x=pedidos_por_plataforma.values,
                    y=pedidos_por_plataforma.index,
                    orientation='h',
                    title="Pedidos por Plataforma",
                    labels={"x": "Número de Pedidos", "y": "Plataforma"}
                )
                st.plotly_chart(fig3, use_container_width=True)
        
        with tab7:
            st.subheader("🚚 Análisis de Costos de Fletes (EKMFLETES)")
            
            if "COSTO TOTAL ANTES DE IVA" in df.columns and "SKU EKM" in df.columns:
                # Filtrar solo los fletes (SKU que contengan EKMFLETE)
                df_fletes = df[df["SKU EKM"].astype(str).str.upper().str.contains("EKMFLETE", na=False)].copy()
                
                if len(df_fletes) > 0:
                    # Convertir a numérico
                    df_fletes["COSTO_NUMERICO"] = pd.to_numeric(df_fletes["COSTO TOTAL ANTES DE IVA"], errors='coerce')
                    
                    # KPIs de flete
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_flete = df_fletes["COSTO_NUMERICO"].sum()
                        st.metric("💵 Gasto Total en Fletes", f"${total_flete:,.2f}")
                    with col2:
                        promedio_flete = df_fletes["COSTO_NUMERICO"].mean()
                        st.metric("📊 Costo Promedio por Flete", f"${promedio_flete:,.2f}")
                    with col3:
                        total_fletes = len(df_fletes)
                        st.metric("🚚 Cantidad de Fletes", total_fletes)
                    
                    # Agregar columnas de mes y año
                    if "FECHA DE ORDEN" in df_fletes.columns:
                        df_fletes["MES_AÑO"] = df_fletes["FECHA DE ORDEN"].dt.to_period('M').astype(str)
                        
                        # Análisis por mes
                        st.write("**Gastos en Fletes por Mes:**")
                        fletes_por_mes = df_fletes.groupby("MES_AÑO")["COSTO_NUMERICO"].agg(['sum', 'count', 'mean']).round(2)
                        fletes_por_mes.columns = ['Gasto Total en Fletes', 'Cantidad de Fletes', 'Costo Promedio']
                        # Formatear columnas de dinero
                        fletes_por_mes['Gasto Total en Fletes'] = fletes_por_mes['Gasto Total en Fletes'].apply(lambda x: f"${x:,.2f}")
                        fletes_por_mes['Costo Promedio'] = fletes_por_mes['Costo Promedio'].apply(lambda x: f"${x:,.2f}")
                        st.dataframe(fletes_por_mes, use_container_width=True)
                    
                    # Análisis por plataforma
                    if "PLATAFORMA" in df_fletes.columns:
                        st.write("**Gastos en Fletes por Plataforma:**")
                        fletes_por_plataforma = df_fletes.groupby("PLATAFORMA")["COSTO_NUMERICO"].agg(['sum', 'count', 'mean']).round(2)
                        fletes_por_plataforma.columns = ['Gasto Total en Fletes', 'Cantidad de Fletes', 'Costo Promedio']
                        fletes_por_plataforma = fletes_por_plataforma.sort_values('Gasto Total en Fletes', ascending=False)
                        # Formatear columnas de dinero
                        fletes_por_plataforma['Gasto Total en Fletes'] = fletes_por_plataforma['Gasto Total en Fletes'].apply(lambda x: f"${x:,.2f}")
                        fletes_por_plataforma['Costo Promedio'] = fletes_por_plataforma['Costo Promedio'].apply(lambda x: f"${x:,.2f}")
                        st.dataframe(fletes_por_plataforma, use_container_width=True)
                    
                    # Análisis por bodega
                    if "BODEGA" in df_fletes.columns:
                        st.write("**Gastos en Fletes por Bodega:**")
                        fletes_por_bodega = df_fletes.groupby("BODEGA")["COSTO_NUMERICO"].agg(['sum', 'count', 'mean']).round(2)
                        fletes_por_bodega.columns = ['Gasto Total en Fletes', 'Cantidad de Fletes', 'Costo Promedio']
                        fletes_por_bodega = fletes_por_bodega.sort_values('Gasto Total en Fletes', ascending=False)
                        # Formatear columnas de dinero
                        fletes_por_bodega['Gasto Total en Fletes'] = fletes_por_bodega['Gasto Total en Fletes'].apply(lambda x: f"${x:,.2f}")
                        fletes_por_bodega['Costo Promedio'] = fletes_por_bodega['Costo Promedio'].apply(lambda x: f"${x:,.2f}")
                        st.dataframe(fletes_por_bodega, use_container_width=True)

                    # Análisis por bodega
                    if "BODEGA" in df_fletes.columns:
                        st.write("**Gastos en Fletes por Bodega:**")
                        fletes_por_bodega = df_fletes.groupby("BODEGA")["COSTO_NUMERICO"].agg(['sum', 'count', 'mean']).round(2)
                        fletes_por_bodega.columns = ['Gasto Total en Fletes', 'Cantidad de Fletes', 'Costo Promedio']
                        fletes_por_bodega = fletes_por_bodega.sort_values('Gasto Total en Fletes', ascending=False)
                        # Formatear columnas de dinero
                        fletes_por_bodega['Gasto Total en Fletes'] = fletes_por_bodega['Gasto Total en Fletes'].apply(lambda x: f"${x:,.2f}")
                        fletes_por_bodega['Costo Promedio'] = fletes_por_bodega['Costo Promedio'].apply(lambda x: f"${x:,.2f}")
                        st.dataframe(fletes_por_bodega, use_container_width=True)
                    
                    # Análisis por comercial
                    if "COMERCIAL" in df_fletes.columns:
                        st.write("**Gastos en Fletes por Comercial:**")
                        fletes_por_comercial = df_fletes.groupby("COMERCIAL")["COSTO_NUMERICO"].agg(['sum', 'count', 'mean']).round(2)
                        fletes_por_comercial.columns = ['Gasto Total en Fletes', 'Cantidad de Fletes', 'Costo Promedio']
                        fletes_por_comercial = fletes_por_comercial.sort_values('Gasto Total en Fletes', ascending=False)
                        # Formatear columnas de dinero
                        fletes_por_comercial['Gasto Total en Fletes'] = fletes_por_comercial['Gasto Total en Fletes'].apply(lambda x: f"${x:,.2f}")
                        fletes_por_comercial['Costo Promedio'] = fletes_por_comercial['Costo Promedio'].apply(lambda x: f"${x:,.2f}")
                        st.dataframe(fletes_por_comercial, use_container_width=True)
                        
                else:
                    st.warning("No se encontraron pedidos con SKU que contengan 'EKMFLETE'")
                
            else:
                st.warning("No se encontraron las columnas necesarias: 'COSTO TOTAL ANTES DE IVA' o 'SKU EKM'")

        with tab8:
            st.subheader("💵 Análisis de Ventas")
            
            if "COSTO TOTAL ANTES DE IVA" in df.columns and "SKU EKM" in df.columns and "# FACTURA" in df.columns:
                # Excluir fletes Y filtrar solo pedidos facturados
                df_ventas = df[
                    (~df["SKU EKM"].astype(str).str.upper().str.contains("EKMFLETE", na=False)) &
                    (df["# FACTURA"].notna()) &
                    (df["# FACTURA"] > 0)
                ].copy()
                
                if len(df_ventas) > 0:
                    # Convertir a numérico
                    df_ventas["VENTA_NUMERICO"] = pd.to_numeric(df_ventas["COSTO TOTAL ANTES DE IVA"], errors='coerce')
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        total_ventas = df_ventas["VENTA_NUMERICO"].sum()
                        st.metric("💰 Ventas Totales", f"${total_ventas:,.2f}")
                    with col2:
                        promedio_venta = df_ventas["VENTA_NUMERICO"].mean()
                        st.metric("📊 Venta Promedio", f"${promedio_venta:,.2f}")
                    with col3:
                        total_pedidos_venta = len(df_ventas)
                        st.metric("📦 Total Pedidos", total_pedidos_venta)
                    with col4:
                        ticket_promedio = total_ventas / total_pedidos_venta if total_pedidos_venta > 0 else 0
                        st.metric("🎫 Ticket Promedio", f"${ticket_promedio:,.2f}")
                    
                    st.markdown("---")
                    
                    # Análisis por mes
                    if "FECHA DE ORDEN" in df_ventas.columns:
                        df_ventas["MES_AÑO"] = df_ventas["FECHA DE ORDEN"].dt.to_period('M').astype(str)
                        
                        st.write("### 📅 Ventas por Mes")
                        ventas_por_mes = df_ventas.groupby("MES_AÑO")["VENTA_NUMERICO"].agg(['sum', 'count', 'mean']).round(2)
                        ventas_por_mes.columns = ['Ventas Totales', 'Cantidad Pedidos', 'Venta Promedio']
                        ventas_por_mes = ventas_por_mes.sort_index(ascending=False)
                        
                        # Formatear columnas de dinero
                        ventas_por_mes_display = ventas_por_mes.copy()
                        ventas_por_mes_display['Ventas Totales'] = ventas_por_mes_display['Ventas Totales'].apply(lambda x: f"${x:,.2f}")
                        ventas_por_mes_display['Venta Promedio'] = ventas_por_mes_display['Venta Promedio'].apply(lambda x: f"${x:,.2f}")
                        st.dataframe(ventas_por_mes_display, use_container_width=True)
                        
                        # Gráfico de ventas por mes
                        fig_ventas_mes = px.bar(
                            x=ventas_por_mes.index,
                            y=ventas_por_mes['Ventas Totales'],
                            title="Evolución de Ventas Mensuales",
                            labels={"x": "Mes", "y": "Ventas ($)"}
                        )
                        st.plotly_chart(fig_ventas_mes, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Análisis por plataforma
                    if "PLATAFORMA" in df_ventas.columns:
                        st.write("### 🏪 Ventas por Plataforma")
                        ventas_por_plataforma = df_ventas.groupby("PLATAFORMA")["VENTA_NUMERICO"].agg(['sum', 'count', 'mean']).round(2)
                        ventas_por_plataforma.columns = ['Ventas Totales', 'Cantidad Pedidos', 'Venta Promedio']
                        ventas_por_plataforma = ventas_por_plataforma.sort_values('Ventas Totales', ascending=False)
                        
                        # Formatear columnas de dinero
                        ventas_por_plataforma_display = ventas_por_plataforma.copy()
                        ventas_por_plataforma_display['Ventas Totales'] = ventas_por_plataforma_display['Ventas Totales'].apply(lambda x: f"${x:,.2f}")
                        ventas_por_plataforma_display['Venta Promedio'] = ventas_por_plataforma_display['Venta Promedio'].apply(lambda x: f"${x:,.2f}")
                        st.dataframe(ventas_por_plataforma_display, use_container_width=True)
                        
                        # Gráfico de ventas por plataforma
                        fig_ventas_plataforma = px.pie(
                            values=ventas_por_plataforma['Ventas Totales'],
                            names=ventas_por_plataforma.index,
                            title="Distribución de Ventas por Plataforma"
                        )
                        st.plotly_chart(fig_ventas_plataforma, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Análisis por comercial
                    if "COMERCIAL" in df_ventas.columns:
                        st.write("### 👤 Ventas por Comercial")
                        ventas_por_comercial = df_ventas.groupby("COMERCIAL")["VENTA_NUMERICO"].agg(['sum', 'count', 'mean']).round(2)
                        ventas_por_comercial.columns = ['Ventas Totales', 'Cantidad Pedidos', 'Venta Promedio']
                        ventas_por_comercial = ventas_por_comercial.sort_values('Ventas Totales', ascending=False)
                        
                        # Formatear columnas de dinero
                        ventas_por_comercial_display = ventas_por_comercial.copy()
                        ventas_por_comercial_display['Ventas Totales'] = ventas_por_comercial_display['Ventas Totales'].apply(lambda x: f"${x:,.2f}")
                        ventas_por_comercial_display['Venta Promedio'] = ventas_por_comercial_display['Venta Promedio'].apply(lambda x: f"${x:,.2f}")
                        st.dataframe(ventas_por_comercial_display, use_container_width=True)
                        
                        # Gráfico de ventas por comercial
                        fig_ventas_comercial = px.bar(
                            x=ventas_por_comercial['Ventas Totales'],
                            y=ventas_por_comercial.index,
                            orientation='h',
                            title="Ranking de Ventas por Comercial",
                            labels={"x": "Ventas ($)", "y": "Comercial"}
                        )
                        st.plotly_chart(fig_ventas_comercial, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Análisis por bodega
                    if "BODEGA" in df_ventas.columns:
                        st.write("### 🏭 Ventas por Bodega")
                        ventas_por_bodega = df_ventas.groupby("BODEGA")["VENTA_NUMERICO"].agg(['sum', 'count', 'mean']).round(2)
                        ventas_por_bodega.columns = ['Ventas Totales', 'Cantidad Pedidos', 'Venta Promedio']
                        ventas_por_bodega = ventas_por_bodega.sort_values('Ventas Totales', ascending=False)
                        
                        # Formatear columnas de dinero
                        ventas_por_bodega_display = ventas_por_bodega.copy()
                        ventas_por_bodega_display['Ventas Totales'] = ventas_por_bodega_display['Ventas Totales'].apply(lambda x: f"${x:,.2f}")
                        ventas_por_bodega_display['Venta Promedio'] = ventas_por_bodega_display['Venta Promedio'].apply(lambda x: f"${x:,.2f}")
                        st.dataframe(ventas_por_bodega_display, use_container_width=True)
                    
                else:
                    st.warning("No se encontraron datos de ventas (todos los pedidos son fletes)")
                
            else:
                st.warning("No se encontraron las columnas necesarias: 'COSTO TOTAL ANTES DE IVA' o 'SKU EKM'")

        with tab9:
                    st.subheader("🏆 Productos Más Vendidos")
                    
                    if "SKU EKM" in df.columns:
                        # Excluir fletes del análisis de top productos
                        df_productos = df[~df["SKU EKM"].astype(str).str.upper().str.contains("EKMFLETE", na=False)].copy()
                        
                        # Contar productos más vendidos
                        top_productos = df_productos["SKU EKM"].value_counts().head(20).reset_index()
                        top_productos.columns = ['SKU EKM', 'Cantidad Vendida']
                        
                        # Si hay catálogo, hacer el cruce
                        if catalog_df is not None and "EKM" in catalog_df.columns and "NOMBRE" in catalog_df.columns:
                            # Normalizar espacios en ambas columnas antes del cruce
                            top_productos["SKU_EKM_CLEAN"] = top_productos["SKU EKM"].astype(str).str.strip().str.upper()
                            catalog_df["EKM_CLEAN"] = catalog_df["EKM"].astype(str).str.strip().str.upper()
                            
                            top_productos = top_productos.merge(
                                catalog_df[["EKM_CLEAN", "NOMBRE"]], 
                                left_on="SKU_EKM_CLEAN", 
                                right_on="EKM_CLEAN", 
                                how="left"
                            )
                            # Limpiar columnas auxiliares
                            top_productos = top_productos.drop(columns=["SKU_EKM_CLEAN", "EKM_CLEAN"])
                            # Reorganizar columnas
                            top_productos = top_productos[["SKU EKM", "NOMBRE", "Cantidad Vendida"]]
                            top_productos["NOMBRE"] = top_productos["NOMBRE"].fillna("Sin nombre")
                        else:
                            st.info("💡 Sube el catálogo de productos para ver los nombres de los productos")
                        
                        st.dataframe(top_productos, use_container_width=True)
                        
                        # Gráfico de top productos
                        fig_productos = px.bar(
                            top_productos.head(10), 
                            x="Cantidad Vendida", 
                            y="SKU EKM",
                            orientation='h',
                            title="Top 10 Productos Más Vendidos"
                        )
                        st.plotly_chart(fig_productos, use_container_width=True)
                        
                    else:
                        st.warning("No se encontró la columna 'SKU EKM'")

        # ======================
        # Resumen ejecutivo
        # ======================
        st.subheader("📋 Resumen Ejecutivo")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Estado Actual:**")
            total_pedidos = len(df)
            st.write(f"- Total de pedidos: **{total_pedidos}**")
            st.write(f"- No facturados: **{len(no_facturados)}** ({len(no_facturados)/total_pedidos*100:.1f}%)")
            st.write(f"- Facturados no despachados: **{len(no_despachados)}** ({len(no_despachados)/total_pedidos*100:.1f}%)")
            st.write(f"- Por vencer: **{len(alerta_vencimiento)}** ({len(alerta_vencimiento)/total_pedidos*100:.1f}%)")
        
        with col2:
            st.write("**Recomendaciones:**")
            if len(no_facturados) > len(df) * 0.1:
                st.write("🔴 Alto número de pedidos sin facturar")
            if len(no_despachados) > len(df) * 0.1:
                st.write("🟠 Revisar proceso de despacho")
            if len(alerta_vencimiento) > 0:
                st.write("⚠️ Atender pedidos próximos a vencer")
            if tiempo_entrega_prom and tiempo_entrega_prom > 7:
                st.write("🕐 Optimizar tiempos de entrega")
    
    except Exception as e:
        st.error(f"Error al procesar el archivo: {str(e)}")
        st.write("Por favor verifica que el archivo tenga el formato correcto.")

else:
    st.info("👆 Por favor sube un archivo Excel para comenzar el análisis.")
    
    # Mostrar información sobre las columnas esperadas
    st.subheader("📝 Columnas esperadas en el archivo Excel:")
    expected_columns = {
        "PLATAFORMA": "Indica qué comercio es",
        "COMERCIAL": "Nombre del vendedor",
        "FECHA DE DESPACHO INTERNO": "Fecha de despacho interno",
        "FECHA DE ORDEN": "Fecha de la orden",
        "FECHA VENC": "Fecha de vencimiento del pedido",
        "ORDEN": "Código único de la orden",
        "SKU CLIENTE": "Código interno del producto (estructura: EKMXXXX)",
        "DESPACHADO": "Estado: DESPACHADO o CANCELADO",
        "BODEGA": "Bodega: Medellín, Bogotá o RTA",
        "GUIA": "Número de guía o CANCELADO",
        "# FACTURA": "Número de factura (0 o #N/D si no facturado)"
    }
    
    for col, desc in expected_columns.items():
        st.write(f"- **{col}**: {desc}")