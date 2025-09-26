import streamlit as st
import pandas as pd
import gdown
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# ==============================
# CONFIGURACIÓN DEL DASHBOARD
# ==============================
st.set_page_config(
    page_title="Dashboard Ekonomodo", 
    layout="wide",
    page_icon="📊"
)

# Logo en la esquina superior
top_col1, top_col2 = st.columns([0.7,0.3])
with top_col2:
    st.image("https://ekonomodo.com/cdn/shop/files/Logo-Ekonomodo-color.svg?v=1736956350&width=450", width=5000)

st.title("📊 Dashboard Control Ekonomodo")
st.markdown("---")

# ==============================
# FUNCIÓN PARA CARGAR DATOS DESDE WEB PUBLICADA
# ==============================
@st.cache_data(ttl=300)  # Cache por 5 minutos
def cargar_datos_web():
    """Carga datos desde Google Sheets publicado en web"""
    
    # CONFIGURACIÓN - Reemplaza con tus URLs
    # Opción 1: URL directa de descarga (más rápida)
    SHEETS_URL = "TU_URL_PUBLICAR_WEB_AQUI"  # ⚠️ Reemplaza con tu URL
    
    # Opción 2: URLs específicas por hoja (si tienes problemas con la URL principal)
    URL_ARCHIVO = "URL_HOJA_ARCHIVO"  # ⚠️ Opcional
    URL_ESTATUS = "URL_HOJA_ESTATUS"  # ⚠️ Opcional
    
    try:
        with st.spinner('Cargando datos desde Google Sheets...'):
            
            # Método 1: Cargar archivo completo y leer hojas
            if SHEETS_URL != "TU_URL_PUBLICAR_WEB_AQUI":
                response = requests.get(SHEETS_URL)
                response.raise_for_status()
                
                # Leer Excel desde bytes
                excel_data = io.BytesIO(response.content)
                df_archivo = pd.read_excel(excel_data, sheet_name="ARCHIVO")
                df_estatus = pd.read_excel(excel_data, sheet_name="ESTATUS")
                
                st.success("✅ Datos cargados desde Google Sheets (Web publicada)")
                return df_archivo, df_estatus
            
            # Método 2: URLs separadas por hoja (como CSV)
            elif URL_ARCHIVO != "URL_HOJA_ARCHIVO" and URL_ESTATUS != "URL_HOJA_ESTATUS":
                df_archivo = pd.read_csv(URL_ARCHIVO)
                df_estatus = pd.read_csv(URL_ESTATUS)
                
                st.success("✅ Datos cargados desde hojas CSV separadas")
                return df_archivo, df_estatus
            
            else:
                # Mostrar instrucciones si no hay URL configurada
                return None, None
                
    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión: {str(e)}")
        return None, None
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        return None, None

# ==============================
# FUNCIÓN PARA LIMPIAR DATOS
# ==============================
def limpiar_datos(df_archivo, df_estatus):
    # Limpiar fechas en ARCHIVO
    df_archivo["FECHA DE VENCIMIENTO"] = pd.to_datetime(df_archivo["FECHA DE VENCIMIENTO"], errors="coerce")
    if "FECHA ESTIMADA DE ENTREGA DE PRODUCCION" in df_archivo.columns:
        df_archivo["FECHA ESTIMADA DE ENTREGA DE PRODUCCION"] = pd.to_datetime(
            df_archivo["FECHA ESTIMADA DE ENTREGA DE PRODUCCION"], errors="coerce"
        )
    
    # Limpiar fechas en ESTATUS
    if "marca temporal" in df_estatus.columns:
        df_estatus["marca temporal"] = pd.to_datetime(df_estatus["marca temporal"], errors="coerce")
    
    # Limpiar valores nulos y normalizar texto
    df_archivo = df_archivo.fillna("")
    df_estatus = df_estatus.fillna("")
    
    return df_archivo, df_estatus

# ==============================
# CARGAR Y LIMPIAR DATOS
# ==============================
df_archivo, df_estatus = cargar_datos()

if df_archivo is not None and df_estatus is not None:
    df_archivo, df_estatus = limpiar_datos(df_archivo, df_estatus)
    
    # ==============================
    # SIDEBAR - FILTROS
    # ==============================
    st.sidebar.header("🔍 Filtros")
    
    # Botón para refrescar datos
    if st.sidebar.button("🔄 Refrescar Datos"):
        st.cache_data.clear()
        st.rerun()
    
    # Filtros principales
    cuentas_disponibles = df_archivo["CUENTA"].unique()
    cuenta = st.sidebar.multiselect("Filtrar por Cuenta:", cuentas_disponibles)
    
    estatus_disponibles = df_archivo["ESTATUS"].unique()
    estatus = st.sidebar.multiselect("Filtrar por Estatus:", estatus_disponibles)
    
    if "ESTATUS LOGISTICA" in df_archivo.columns:
        estatus_log_disponibles = df_archivo["ESTATUS LOGISTICA"].unique()
        estatus_log = st.sidebar.multiselect("Filtrar por Estatus Logística:", estatus_log_disponibles)
    else:
        estatus_log = []
    
    # Filtro por rango de fechas
    st.sidebar.subheader("📅 Filtros de Fecha")
    fecha_inicio = st.sidebar.date_input("Fecha inicio", value=datetime.now() - timedelta(days=30))
    fecha_fin = st.sidebar.date_input("Fecha fin", value=datetime.now())
    
    # Aplicar filtros
    df_filtrado = df_archivo.copy()
    
    if cuenta:
        df_filtrado = df_filtrado[df_filtrado["CUENTA"].isin(cuenta)]
    if estatus:
        df_filtrado = df_filtrado[df_filtrado["ESTATUS"].isin(estatus)]
    if estatus_log and "ESTATUS LOGISTICA" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["ESTATUS LOGISTICA"].isin(estatus_log)]
    
    # Filtrar por fechas
    if "FECHA DE VENCIMIENTO" in df_filtrado.columns:
        df_filtrado = df_filtrado[
            (df_filtrado["FECHA DE VENCIMIENTO"].dt.date >= fecha_inicio) &
            (df_filtrado["FECHA DE VENCIMIENTO"].dt.date <= fecha_fin)
        ]
    
    # ==============================
    # MÉTRICAS PRINCIPALES
    # ==============================
    st.header("📊 Resumen Ejecutivo")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_ordenes = len(df_filtrado)
    produccion = (df_filtrado["ESTATUS"] == "PRODUCCION").sum()
    entrega = (df_filtrado["ESTATUS"] == "ENTREGA").sum()
    cancelados = (df_filtrado["ESTATUS"] == "CANCELADO").sum()
    
    if "ESTATUS LOGISTICA" in df_filtrado.columns:
        recibidos = (df_filtrado["ESTATUS LOGISTICA"] == "RECIBIDO").sum()
    else:
        recibidos = 0
    
    col1.metric("📦 Total Órdenes", total_ordenes)
    col2.metric("🏭 Producción", produccion)
    col3.metric("🚚 Entrega", entrega)
    col4.metric("❌ Cancelados", cancelados)
    col5.metric("✅ Recibidos", recibidos)
    
    # ==============================
    # ANÁLISIS DE ESTATUS
    # ==============================
    st.header("📈 Análisis de Estatus")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Distribución de Estatus General")
        estatus_counts = df_filtrado["ESTATUS"].value_counts()
        
        fig_estatus = px.pie(
            values=estatus_counts.values,
            names=estatus_counts.index,
            title="Distribución de Estatus",
            hole=0.4
        )
        fig_estatus.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_estatus, use_container_width=True)
    
    with col2:
        if "ESTATUS LOGISTICA" in df_filtrado.columns:
            st.subheader("Distribución de Estatus Logística")
            log_counts = df_filtrado["ESTATUS LOGISTICA"].value_counts()
            
            fig_log = px.bar(
                x=log_counts.index,
                y=log_counts.values,
                title="Estatus Logística",
                labels={'x': 'Estatus', 'y': 'Cantidad'}
            )
            st.plotly_chart(fig_log, use_container_width=True)
    
    # ==============================
    # ANÁLISIS DE CUMPLIMIENTO
    # ==============================
    st.header("⏱️ Análisis de Cumplimiento de Entregas")
    
    # Merge de las dos hojas por ORDEN
    if "ORDEN" in df_archivo.columns and "ORDEN" in df_estatus.columns:
        df_merged = pd.merge(df_filtrado, df_estatus, on="ORDEN", how="left", suffixes=("", "_estatus"))
        
        # Filtrar solo las órdenes con marca temporal (entregadas)
        df_entregadas = df_merged.dropna(subset=["marca temporal"])
        
        if not df_entregadas.empty:
            # Calcular cumplimiento
            df_entregadas["DIAS_DIFERENCIA"] = (
                df_entregadas["marca temporal"] - df_entregadas["FECHA DE VENCIMIENTO"]
            ).dt.days
            
            df_entregadas["CUMPLIMIENTO"] = df_entregadas["DIAS_DIFERENCIA"] <= 0
            df_entregadas["CATEGORIA_ENTREGA"] = df_entregadas["DIAS_DIFERENCIA"].apply(
                lambda x: "A tiempo" if x <= 0 else f"Retraso ({x} días)" if x <= 7 else f"Retraso crítico ({x} días)"
            )
            
            col1, col2, col3 = st.columns(3)
            
            entregadas_total = len(df_entregadas)
            a_tiempo = df_entregadas["CUMPLIMIENTO"].sum()
            retrasadas = entregadas_total - a_tiempo
            
            col1.metric("📦 Órdenes Entregadas", entregadas_total)
            col2.metric("✅ A Tiempo", a_tiempo, f"{(a_tiempo/entregadas_total*100):.1f}%" if entregadas_total > 0 else "0%")
            col3.metric("⏰ Retrasadas", retrasadas, f"{(retrasadas/entregadas_total*100):.1f}%" if entregadas_total > 0 else "0%")
            
            # Gráfico de cumplimiento
            col1, col2 = st.columns(2)
            
            with col1:
                cumplimiento_counts = df_entregadas["CUMPLIMIENTO"].value_counts()
                fig_cumpl = px.pie(
                    values=cumplimiento_counts.values,
                    names=["A tiempo" if x else "Retrasadas" for x in cumplimiento_counts.index],
                    title="Cumplimiento de Entregas",
                    color_discrete_map={"A tiempo": "#00CC96", "Retrasadas": "#EF553B"}
                )
                st.plotly_chart(fig_cumpl, use_container_width=True)
            
            with col2:
                # Histograma de días de diferencia
                fig_hist = px.histogram(
                    df_entregadas,
                    x="DIAS_DIFERENCIA",
                    nbins=20,
                    title="Distribución de Días de Retraso/Adelanto",
                    labels={'DIAS_DIFERENCIA': 'Días (negativo = adelanto)', 'count': 'Cantidad'}
                )
                fig_hist.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Fecha límite")
                st.plotly_chart(fig_hist, use_container_width=True)
            
            # Análisis por cuenta
            st.subheader("📊 Cumplimiento por Cuenta")
            cumplimiento_cuenta = df_entregadas.groupby("CUENTA").agg({
                "CUMPLIMIENTO": ["count", "sum"],
                "DIAS_DIFERENCIA": "mean"
            }).round(2)
            
            cumplimiento_cuenta.columns = ["Total", "A Tiempo", "Promedio Días Diferencia"]
            cumplimiento_cuenta["% Cumplimiento"] = (
                cumplimiento_cuenta["A Tiempo"] / cumplimiento_cuenta["Total"] * 100
            ).round(1)
            
            st.dataframe(cumplimiento_cuenta, use_container_width=True)
    
    # ==============================
    # ANÁLISIS TEMPORAL
    # ==============================
    st.header("📅 Análisis Temporal")
    
    if "FECHA DE VENCIMIENTO" in df_filtrado.columns:
        df_temp = df_filtrado.copy()
        df_temp["MES_VENCIMIENTO"] = df_temp["FECHA DE VENCIMIENTO"].dt.to_period("M").astype(str)
        
        # Órdenes por mes
        ordenes_mes = df_temp.groupby(["MES_VENCIMIENTO", "ESTATUS"]).size().reset_index(name="CANTIDAD")
        
        fig_temporal = px.bar(
            ordenes_mes,
            x="MES_VENCIMIENTO",
            y="CANTIDAD",
            color="ESTATUS",
            title="Órdenes por Mes y Estatus",
            labels={'MES_VENCIMIENTO': 'Mes', 'CANTIDAD': 'Cantidad de Órdenes'}
        )
        st.plotly_chart(fig_temporal, use_container_width=True)
    
    # ==============================
    # TABLA DETALLADA
    # ==============================
    st.header("📋 Detalle de Órdenes")
    
    # Selectores para personalizar la vista
    col1, col2 = st.columns(2)
    with col1:
        mostrar_todas = st.checkbox("Mostrar todas las columnas", value=False)
    with col2:
        num_filas = st.selectbox("Número de filas a mostrar", [10, 25, 50, 100, "Todas"], index=1)
    
    if mostrar_todas:
        df_mostrar = df_filtrado
    else:
        columnas_principales = ["ORDEN", "CUENTA", "FECHA DE VENCIMIENTO", "ESTATUS", "ESTATUS LOGISTICA", "EKM"]
        columnas_existentes = [col for col in columnas_principales if col in df_filtrado.columns]
        df_mostrar = df_filtrado[columnas_existentes]
    
    if num_filas == "Todas":
        st.dataframe(df_mostrar, use_container_width=True)
    else:
        st.dataframe(df_mostrar.head(num_filas), use_container_width=True)
    
    # ==============================
    # DESCARGA DE DATOS
    # ==============================
    st.header("💾 Exportar Datos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv = df_filtrado.to_csv(index=False)
        st.download_button(
            label="📥 Descargar datos filtrados (CSV)",
            data=csv,
            file_name=f"ekonomodo_filtrado_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    with col2:
        if "ORDEN" in df_archivo.columns and "ORDEN" in df_estatus.columns:
            df_completo = pd.merge(df_filtrado, df_estatus, on="ORDEN", how="left", suffixes=("", "_estatus"))
            csv_completo = df_completo.to_csv(index=False)
            st.download_button(
                label="📥 Descargar datos completos (CSV)",
                data=csv_completo,
                file_name=f"ekonomodo_completo_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
    
    # ==============================
    # FOOTER
    # ==============================
    st.markdown("---")
    st.markdown(f"**Última actualización:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("**Dashboard Ekonomodo** - Desarrollado con Streamlit")

else:
    st.error("No se pudieron cargar los datos. Verifica la configuración del archivo.")
    st.info("""
    **Pasos para configurar:**
    1. Sube tu archivo Excel a Google Drive
    2. Haz clic derecho → Obtener enlace
    3. Copia el FILE_ID del enlace (la parte entre /d/ y /view)
    4. Reemplaza 'TU_FILE_ID' en el código con tu ID real
    5. Asegúrate de que el archivo tenga las hojas 'ARCHIVO' y 'ESTATUS'
    """)