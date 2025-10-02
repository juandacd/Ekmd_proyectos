# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ==========================
# CONFIGURACIÓN GENERAL
# ==========================
st.set_page_config(
    page_title="Dashboard de Despachos", 
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("📦 Dashboard Avanzado de Despachos Diarios")
st.markdown("---")

# Logo en la esquina superior
top_col1, top_col2 = st.columns([0.7,0.3])
with top_col2:
    st.image("https://ekonomodo.com/cdn/shop/files/Logo-Ekonomodo-color.svg?v=1736956350&width=450", width=5000)

# ==========================
# FUNCIONES AUXILIARES
# ==========================
@st.cache_data
def load_and_process_data(uploaded_file):
    """Carga y procesa el archivo Excel"""
    try:
        df = pd.read_excel(uploaded_file)
       
        # Limpiar y normalizar columnas (eliminar espacios excesivos)
        df.columns = df.columns.astype(str).str.strip().str.upper()
        # Reemplazar múltiples espacios por uno solo
        df.columns = [' '.join(col.split()) for col in df.columns]
        
        # Mapeo de nombres de columnas comunes
        column_mapping = {
            'FECHA': 'FECHA_FACTURA',
            'FECHA FACTURA': 'FECHA_FACTURA',
        }
        df.rename(columns=column_mapping, inplace=True)
        
        # Procesar fechas - formato día/mes/año
        date_columns = ["FECHA_FACTURA", "FECHA DESPACHO"]
        for col in date_columns:
            if col in df.columns:
                # Intentar múltiples formatos con prioridad en día/mes/año
                try:
                    # Primero intentar con dayfirst=True (día/mes/año)
                    df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True, format="%d/%m/%Y")
                    
                    # Si hay muchos NaN, intentar otros formatos comunes
                    if df[col].isna().sum() > len(df) * 0.5:  # Si más del 50% son NaN
                        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                    
                    if df[col].isna().all():
                        st.warning(f"No se pudieron procesar las fechas en la columna {col}")
                    else:
                        fechas_procesadas = df[col].notna().sum()
                        st.info(f"✅ Procesadas {fechas_procesadas} fechas en columna {col}")
                        
                except Exception as e:
                    st.warning(f"Error procesando fechas en {col}: {str(e)}")
                    # Fallback: intentar sin formato específico
                    df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

        # Limpiar espacios en ALISTAMIENTO
        if "ALISTAMIENTO" in df.columns:
            df["ALISTAMIENTO"] = df["ALISTAMIENTO"].astype(str).str.strip()

        # Mapear códigos de ciudad
        if "COS" in df.columns:
            def mapear_ciudad(cos):
                cos = pd.to_numeric(cos, errors='coerce')
                if pd.isna(cos):
                    return "Sin ciudad"
                elif cos == 1:
                    return "Bogotá"
                elif cos == 2:
                    return "Medellín"
                elif cos == 999:
                    return "RTA"
                else:
                    return f"Ciudad {int(cos)}"
            
            df["CIUDAD"] = df["COS"].apply(mapear_ciudad)
        
        # Calcular tiempo de despacho
        if "FECHA_FACTURA" in df.columns and "FECHA DESPACHO" in df.columns:
            df["TIEMPO_DESPACHO_DIAS"] = (df["FECHA DESPACHO"] - df["FECHA_FACTURA"]).dt.days
            df["TIEMPO_DESPACHO_HORAS"] = (df["FECHA DESPACHO"] - df["FECHA_FACTURA"]).dt.total_seconds() / 3600

        # Limpiar espacios en ALISTAMIENTO
        if "ALISTAMIENTO" in df.columns:
            df["ALISTAMIENTO"] = df["ALISTAMIENTO"].astype(str).str.strip()
        
        # Limpiar costos - ser más agresivo con la limpieza
        if "COSTO FLETE" in df.columns:
            # Convertir a string primero para limpiar
            df["COSTO FLETE"] = df["COSTO FLETE"].astype(str)
            # Remover caracteres no numéricos excepto puntos y comas
            df["COSTO FLETE"] = df["COSTO FLETE"].str.replace(r'[^\d.,]', '', regex=True)
            # Reemplazar comas por puntos para decimales
            df["COSTO FLETE"] = df["COSTO FLETE"].str.replace(',', '.')
            # Convertir a numérico
            df["COSTO FLETE"] = pd.to_numeric(df["COSTO FLETE"], errors="coerce").fillna(0)
            
        # Lista de plataformas conocidas
        plataformas_conocidas = [
            "PAGINA WEB", "FALABELLA", "SODIMAC", "ADDI", "AGAVAL",
            "APER", "CRICKET", "MERCADO LIBRE", "PUNTOS COLOMBIA", "TUGO"
        ]

        # Asegurar que la columna PLATAFORMA existe
        if "PLATAFORMA" in df.columns:
            # Limpiar espacios y poner en mayúsculas para comparar mejor
            df["PLATAFORMA_CLEAN"] = df["PLATAFORMA"].astype(str).str.strip().str.upper()

            def clasificar_canal(plataforma):
                if pd.isna(plataforma) or plataforma.strip() == "":
                    return np.nan  # No se ha despachado
                elif any(p in plataforma for p in plataformas_conocidas):
                    return plataforma  # Es una plataforma conocida
                else:
                    return "PARTICULAR"  # No coincide, asumimos que es nombre de persona

            # Aplicar función
            df["CANAL_VENTA"] = df["PLATAFORMA_CLEAN"].apply(clasificar_canal)

            # (Opcional) Eliminar columna temporal
            df.drop(columns=["PLATAFORMA_CLEAN"], inplace=True)
        
        # Crear variables temporales
        if "FECHA DESPACHO" in df.columns:
            mask_fecha_valida = df["FECHA DESPACHO"].notna()
            df.loc[mask_fecha_valida, "AÑO"] = df.loc[mask_fecha_valida, "FECHA DESPACHO"].dt.year
            df.loc[mask_fecha_valida, "MES"] = df.loc[mask_fecha_valida, "FECHA DESPACHO"].dt.month
            df.loc[mask_fecha_valida, "DIA_SEMANA"] = df.loc[mask_fecha_valida, "FECHA DESPACHO"].dt.day_name()
            df.loc[mask_fecha_valida, "SEMANA"] = df.loc[mask_fecha_valida, "FECHA DESPACHO"].dt.isocalendar().week
        
        # Categorizar estatus - ser más flexible
        if "ESTATUS" in df.columns:
            df["ESTATUS_CLEAN"] = df["ESTATUS"].fillna("SIN ESTATUS").astype(str).str.upper().str.strip()
            df["IS_ENTREGADO"] = df["ESTATUS_CLEAN"].isin(["ENTREGADO", "ENTREGADA", "DELIVERED", "COMPLETADO", "DESPACHADO", "DEPACHADO"])
            
            # Verificar que existe la columna NRO. CRUCE antes de usarla
            if "NRO. CRUCE" in df.columns:
                # Convertir a numérico primero para detectar tanto 0 como 0.0
                df["NRO_CRUCE_NUMERIC"] = pd.to_numeric(df["NRO. CRUCE"], errors='coerce')
                
                # Un producto NO está facturado si:
                # - El valor numérico es 0 (incluye 0.0, 0, etc.)
                # - Es NaN (valores faltantes o no numéricos)
                df["IS_NO_FACTURADO"] = (df["NRO_CRUCE_NUMERIC"] == 0) | (df["NRO_CRUCE_NUMERIC"].isna())
                df["IS_FACTURADO"] = ~df["IS_NO_FACTURADO"]
                
                # Limpiar columna temporal
                df.drop("NRO_CRUCE_NUMERIC", axis=1, inplace=True)
                
                # Un producto está facturado pero no despachado si está facturado pero no está entregado
                df["IS_FACTURADO_NO_DESPACHADO"] = (df["IS_FACTURADO"]) & (~df["IS_ENTREGADO"])
            else:
                df["IS_FACTURADO_NO_DESPACHADO"] = False
                df["IS_NO_FACTURADO"] = False
                df["IS_FACTURADO"] = False
        
        return df
    except Exception as e:
        st.error(f"Error al procesar el archivo: {str(e)}")
        import traceback
        st.error(f"Detalles del error: {traceback.format_exc()}")
        return None

@st.cache_data
def load_vendedores_data(uploaded_file):
    """Carga el archivo de vendedores para hacer el cruce"""
    if uploaded_file is not None:
        try:
            df_vendedores = pd.read_excel(uploaded_file)
            # Limpiar columnas
            df_vendedores.columns = df_vendedores.columns.astype(str).str.strip().str.upper()
            df_vendedores.columns = [' '.join(col.split()) for col in df_vendedores.columns]
            
            st.write(f"**Vendedores cargados:** {len(df_vendedores)} registros")
            st.write("**Columnas en archivo de vendedores:**")
            st.write(list(df_vendedores.columns))
            
            return df_vendedores
        except Exception as e:
            st.error(f"Error al cargar archivo de vendedores: {str(e)}")
            return None
    return None

def merge_vendedores(df, df_vendedores):
    """Hace el cruce entre despachos y vendedores"""
    try:
        if df_vendedores is not None and "VEND" in df.columns:
            # Limpiar nombres de columnas del catálogo de vendedores
            df_vendedores.columns = df_vendedores.columns.str.strip().str.replace('"', '').str.upper()

            # Mostrar información de depuración
            st.write("**Columnas en archivo de vendedores:**")
            st.write(df_vendedores.columns.tolist())
            st.write(f"**Códigos de vendedor únicos en despachos:** {df['VEND'].nunique()}")
            st.write(f"**Códigos de vendedor únicos en catálogo:** {df_vendedores['VENDEDOR'].nunique() if 'VENDEDOR' in df_vendedores.columns else 'Columna VENDEDOR no encontrada'}")

            if "VENDEDOR" in df_vendedores.columns and "NOMBRE" in df_vendedores.columns:
                # Asegurar formatos consistentes
                df["VEND"] = df["VEND"].astype(str).str.strip().str.upper()
                df_vendedores["VENDEDOR"] = df_vendedores["VENDEDOR"].astype(str).str.strip().str.upper()

                # Hacer el merge
                df_original_len = len(df)
                df = df.merge(
                    df_vendedores[["VENDEDOR", "NOMBRE"]],
                    left_on="VEND",
                    right_on="VENDEDOR",
                    how="left"
                )

                df.rename(columns={"NOMBRE_y": "NOMBRE"}, inplace=True)

                # Verificar si el merge alteró la cantidad de registros
                if len(df) != df_original_len:
                    st.warning(f"⚠️ El merge cambió el número de registros: de {df_original_len} a {len(df)}")

                # Crear columna combinada con nombre del vendedor
                df["VENDEDOR_NOMBRE"] = df.apply(lambda row:
                    f"{row['VEND']} - {row['NOMBRE']}" if pd.notna(row.get("NOMBRE")) and str(row.get("NOMBRE")).strip() != ""
                    else f"{row['VEND']} - Sin nombre", axis=1)

                # Mostrar estadísticas del cruce
                if "NOMBRE" in df.columns:
                    vendedores_con_nombre = df["NOMBRE"].notna().sum()
                    st.success(f"✅ Cruce completado: {vendedores_con_nombre} registros con nombre de vendedor")
                else:
                    st.warning(f"⚠️ 'NOMBRE' no se encuentra en df después del merge. Columnas actuales: {df.columns.tolist()}")

            else:
                st.error("❌ El archivo de vendedores debe tener columnas 'VENDEDOR' y 'NOMBRE'")

    except Exception as e:
        st.warning(f"⚠️ Error al vincular vendedores: {str(e)}")
        import traceback
        st.error(f"📄 Detalles del error:\n\n{traceback.format_exc()}")

    return df


def format_currency(value):
    """Formatea un valor como moneda"""
    if pd.isna(value) or value == 0:
        return "$0"
    return f"${value:,.0f}"

def show_detailed_selection(df, filter_column, filter_value, title):
    """Muestra detalles de una selección específica"""
    st.subheader(f"📋 {title}")
    
    # Filtrar datos según la selección
    df_filtered = df[df[filter_column] == filter_value]
    
    # Mostrar métricas rápidas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Registros", len(df_filtered))
    with col2:
        if "IS_ENTREGADO" in df_filtered.columns:
            entregados = df_filtered["IS_ENTREGADO"].sum()
            st.metric("Entregados", entregados)
    with col3:
        if "COSTO FLETE" in df_filtered.columns:
            costo_total = df_filtered["COSTO FLETE"].sum()
            st.metric("Costo Total", format_currency(costo_total))
    with col4:
        if "IS_FACTURADO_NO_DESPACHADO" in df_filtered.columns:
            alertas = df_filtered["IS_FACTURADO_NO_DESPACHADO"].sum()
            st.metric("🚨 Alertas", alertas, delta_color="inverse")
    
    # Mostrar tabla detallada
    st.dataframe(df_filtered, use_container_width=True, height=400)
    
    # Opción de descarga
    csv = df_filtered.to_csv(index=False)
    st.download_button(
        label="📥 Descargar datos filtrados",
        data=csv,
        file_name=f"detalle_{filter_value}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

def create_kpi_metrics(df):
    """Calcula métricas KPI"""
    try:
        total_despachos = len(df)
        total_costo = df["COSTO FLETE"].sum() if "COSTO FLETE" in df.columns else 0
        entregados = df["IS_ENTREGADO"].sum() if "IS_ENTREGADO" in df.columns else 0
        no_entregados = total_despachos - entregados
        facturado_no_desp = df["IS_FACTURADO_NO_DESPACHADO"].sum() if "IS_FACTURADO_NO_DESPACHADO" in df.columns else 0
        no_facturados = df["IS_NO_FACTURADO"].sum() if "IS_NO_FACTURADO" in df.columns else 0
        facturados = df["IS_FACTURADO"].sum() if "IS_FACTURADO" in df.columns else 0
        
        tasa_entrega = (entregados / total_despachos * 100) if total_despachos > 0 else 0
        tiempo_promedio = df["TIEMPO_DESPACHO_DIAS"].mean() if "TIEMPO_DESPACHO_DIAS" in df.columns else 0
        costo_promedio = df["COSTO FLETE"].mean() if "COSTO FLETE" in df.columns else 0
        
        return {
            "total_despachos": total_despachos,
            "total_costo": total_costo,
            "entregados": entregados,
            "no_entregados": no_entregados,
            "facturado_no_desp": facturado_no_desp,
            "no_facturados": no_facturados,
            "facturados": facturados,
            "tasa_entrega": tasa_entrega,
            "tiempo_promedio": tiempo_promedio,
            "costo_promedio": costo_promedio
        }
    except Exception as e:
        st.error(f"Error calculando KPIs: {str(e)}")
        return {
            "total_despachos": 0,
            "total_costo": 0,
            "entregados": 0,
            "no_entregados": 0,
            "facturado_no_desp": 0,
            "tasa_entrega": 0,
            "tiempo_promedio": 0,
            "costo_promedio": 0
        }

# ==========================
# CARGAR ARCHIVO
# ==========================
def main():
    st.sidebar.header("🔧 Configuración")

    # Cargar archivo principal de despachos
    uploaded_file = st.sidebar.file_uploader("Sube el archivo Excel de despachos", type=["xlsx", "xls"])

    # Cargar archivo de vendedores (opcional)
    st.sidebar.subheader("📊 Datos de Vendedores (Opcional)")
    vendedores_file = st.sidebar.file_uploader(
        "Sube el archivo Excel de vendedores", 
        type=["xlsx", "xls"],
        key="vendedores_file",
        help="Archivo con columnas: VENDEDOR y NOMBRE"
    )

    if uploaded_file:
        # Cargar datos
        with st.spinner("Cargando y procesando datos..."):
            df = load_and_process_data(uploaded_file)
            
            if df is None:
                st.error("No se pudo cargar el archivo. Verifica el formato.")
                return
            
            # Cargar y hacer cruce con vendedores si está disponible
            df_vendedores = load_vendedores_data(vendedores_file) if vendedores_file else None
            if df_vendedores is not None:
                df = merge_vendedores(df, df_vendedores)
        
        st.success(f"✅ Datos cargados exitosamente: {len(df)} registros")
   
        # ==========================
        # FILTROS AVANZADOS
        # ==========================
        df_filtered = apply_filters(df)
        
        if df_filtered is not None and len(df_filtered) > 0:
            
            # ==========================
            # KPI DASHBOARD
            # ==========================
            show_kpi_dashboard(df_filtered)
            
            # ==========================
            # ALERTAS CRÍTICAS
            # ==========================
            show_critical_alerts(df_filtered)
            
            # ==========================
            # ANÁLISIS TEMPORAL
            # ==========================
            show_temporal_analysis(df_filtered)
            
            # ==========================
            # ANÁLISIS DE COSTOS
            # ==========================
            show_cost_analysis(df_filtered)
            
            # ==========================
            # ANÁLISIS POR LOGÍSTICO
            # ==========================
            show_logistics_analysis(df_filtered)
            
            # ==========================
            # ANÁLISIS POR CANAL DE VENTA
            # ==========================
            show_channel_analysis(df_filtered)

            # ==========================
            # ANÁLISIS POR CIUDAD
            # ==========================
            if "CIUDAD" in df_filtered.columns:
                show_city_analysis(df_filtered)

            # ==========================
            # ANÁLISIS TEMPORAL DE COSTOS
            # ==========================
            periodo_seleccionado = st.session_state.get('periodo_analisis', 'Todos los datos')
            show_temporal_cost_analysis(df_filtered, periodo_seleccionado)
            
            # ==========================
            # ANÁLISIS POR VENDEDOR
            # ==========================
            if "VENDEDOR_NOMBRE" in df_filtered.columns:
                show_seller_analysis(df_filtered)
            
            # ==========================
            # ANÁLISIS DE TIEMPOS
            # ==========================
            show_time_analysis(df_filtered)
            
            # ==========================
            # DATOS DETALLADOS
            # ==========================
            show_detailed_data(df_filtered)
        else:
            st.warning("No hay datos que mostrar con los filtros seleccionados.")
    else:
        show_help_info()



def apply_filters(df):
    """Aplica todos los filtros seleccionados"""
    st.sidebar.subheader("🔍 Filtros")
    
    try:
        # MOVER ESTO AL PRINCIPIO:
        # Filtro de período temporal
        st.sidebar.subheader("📅 Análisis Temporal")
        periodo_analisis = st.sidebar.selectbox(
            "Seleccionar período de análisis",
            ["Todos los datos", "Año actual", "Mes actual", "Semana actual", "Día actual"],
            index=0
        )
        st.session_state['periodo_analisis'] = periodo_analisis

        # Aplicar filtro temporal
        if "FECHA DESPACHO" in df.columns and periodo_analisis != "Todos los datos":
            hoy = datetime.now()
            
            if periodo_analisis == "Año actual":
                inicio_periodo = datetime(hoy.year, 1, 1)
                df = df[df["FECHA DESPACHO"] >= inicio_periodo]
            elif periodo_analisis == "Mes actual":
                inicio_periodo = datetime(hoy.year, hoy.month, 1)
                df = df[df["FECHA DESPACHO"] >= inicio_periodo]
            elif periodo_analisis == "Semana actual":
                dias_desde_lunes = hoy.weekday()
                inicio_semana = hoy - timedelta(days=dias_desde_lunes)
                inicio_periodo = datetime(inicio_semana.year, inicio_semana.month, inicio_semana.day)
                df = df[df["FECHA DESPACHO"] >= inicio_periodo]
            elif periodo_analisis == "Día actual":
                inicio_periodo = datetime(hoy.year, hoy.month, hoy.day)
                df = df[df["FECHA DESPACHO"] >= inicio_periodo]

        # Filtros de fecha (rango manual)
        if "FECHA DESPACHO" in df.columns:
            # Filtrar solo fechas válidas para el rango
            df_fechas_validas = df[df["FECHA DESPACHO"].notna()]
            
            if len(df_fechas_validas) > 0:
                fecha_min = df_fechas_validas["FECHA DESPACHO"].min()
                fecha_max = df_fechas_validas["FECHA DESPACHO"].max()
                
                if pd.notna(fecha_min) and pd.notna(fecha_max):
                    fecha_inicio, fecha_fin = st.sidebar.date_input(
                        "Rango de fechas",
                        value=(fecha_min.date(), fecha_max.date()),
                        min_value=fecha_min.date(),
                        max_value=fecha_max.date()
                    )
                    df = df[(df["FECHA DESPACHO"].dt.date >= fecha_inicio) & 
                           (df["FECHA DESPACHO"].dt.date <= fecha_fin)]
                    
        # Filtro por canal de venta
        if "CANAL_VENTA" in df.columns:
            canales = sorted([str(x) for x in df["CANAL_VENTA"].dropna().unique() if str(x) != "nan"])
            if canales:
                canal_selec = st.sidebar.multiselect("Canal de Venta", canales, default=[])
                if canal_selec:
                    df = df[df["CANAL_VENTA"].isin(canal_selec)]
        
        # Filtro por logístico
        if "ALISTAMIENTO" in df.columns:
            alistadores = sorted([str(x) for x in df["ALISTAMIENTO"].dropna().unique() if str(x) != "nan"])
            if alistadores:
                alistador_selec = st.sidebar.multiselect("Logístico", alistadores, default=[])
                if alistador_selec:
                    df = df[df["ALISTAMIENTO"].isin(alistador_selec)]
        
        # Filtro por estatus
        if "ESTATUS_CLEAN" in df.columns:
            estatus_options = sorted([str(x) for x in df["ESTATUS_CLEAN"].unique() if str(x) != "nan"])
            if estatus_options:
                estatus_selec = st.sidebar.multiselect("Estatus", estatus_options, default=[])
                if estatus_selec:
                    df = df[df["ESTATUS_CLEAN"].isin(estatus_selec)]
        
        # Filtro por vendedor
        if "VENDEDOR_NOMBRE" in df.columns:
            vendedores = sorted([str(x) for x in df["VENDEDOR_NOMBRE"].dropna().unique() if str(x) != "nan"])
            if vendedores:
                # Limitar a máximo 10 por defecto para evitar sobrecarga
                default_vendedores = vendedores[:10] if len(vendedores) > 10 else vendedores
                vendedor_selec = st.sidebar.multiselect("Vendedor", vendedores, default=[])
                if vendedor_selec:
                    df = df[df["VENDEDOR_NOMBRE"].isin(vendedor_selec)]

        # Filtro por ciudad
        if "CIUDAD" in df.columns:
            ciudades = sorted([str(x) for x in df["CIUDAD"].dropna().unique() if str(x) != "nan"])
            if ciudades:
                ciudad_selec = st.sidebar.multiselect("Ciudad", ciudades, default=[])
                if ciudad_selec:
                    df = df[df["CIUDAD"].isin(ciudad_selec)]
        
        return df
    except Exception as e:
        st.error(f"Error aplicando filtros: {str(e)}")
        return df

def show_kpi_dashboard(df):
    """Muestra el dashboard de KPIs"""
    st.subheader("📊 Resumen Ejecutivo")
    kpis = create_kpi_metrics(df)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📦 Total Despachos", f"{kpis['total_despachos']:,}")
        st.metric("⏱️ Tiempo Promedio", f"{kpis['tiempo_promedio']:.1f} días")
    with col2:
        st.metric("✅ Entregados", f"{kpis['entregados']:,}")
        st.metric("📈 Tasa Entrega", f"{kpis['tasa_entrega']:.1f}%")
    with col3:
        st.metric("❌ No Entregados", f"{kpis['no_entregados']:,}")
        st.metric("🚨 Fact. No Desp.", f"{kpis['facturado_no_desp']:,}")
    with col4:
        st.metric("📋 Facturados", f"{kpis['facturados']:,}")
        st.metric("📄 No Facturados", f"{kpis['no_facturados']:,}")
    with col5:
        st.metric("💰 Costo Total Fletes", format_currency(kpis['total_costo']))
        st.metric("💵 Costo Promedio Fletes", format_currency(kpis['costo_promedio']))
    
    st.markdown("---")

def show_critical_alerts(df):
    """Muestra alertas críticas"""
    if "IS_FACTURADO_NO_DESPACHADO" in df.columns:
        facturado_no_desp = df["IS_FACTURADO_NO_DESPACHADO"].sum()
        
        if facturado_no_desp > 0:
            st.error(f"🚨 **ALERTA CRÍTICA**: {facturado_no_desp} productos facturados sin despachar")
            
            with st.expander("Ver detalles de productos facturados sin despachar"):
                alertas_df = df[df["IS_FACTURADO_NO_DESPACHADO"] == True]
                if not alertas_df.empty:
                    # Mostrar tabla con información relevante
                    cols_mostrar = ["NRO. CRUCE", "FECHA_FACTURA", "CANAL_VENTA", "ALISTAMIENTO", "VENDEDOR_NOMBRE", "ESTATUS_CLEAN", "COSTO FLETE"]
                    cols_disponibles = [col for col in cols_mostrar if col in alertas_df.columns]
                    
                    # Formatear costos en la tabla
                    df_display = alertas_df[cols_disponibles].copy()
                    if "COSTO FLETE" in df_display.columns:
                        df_display["COSTO FLETE"] = df_display["COSTO FLETE"].apply(format_currency)
                    
                    st.dataframe(df_display, use_container_width=True)
                    
                    # Opción de descarga
                    csv = alertas_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Descargar alertas en CSV",
                        data=csv,
                        file_name=f"alertas_despachos_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )

def show_temporal_analysis(df):
    """Muestra análisis temporal"""
    st.subheader("📅 Análisis Temporal")
    
    if "FECHA DESPACHO" in df.columns and not df["FECHA DESPACHO"].isna().all():
        col1, col2 = st.columns(2)
        
        with col1:
            # Despachos por mes
            try:
                df_fechas_validas = df[df["FECHA DESPACHO"].notna()]
                despachos_mes = df_fechas_validas.groupby(df_fechas_validas["FECHA DESPACHO"].dt.to_period("M")).size().reset_index()
                despachos_mes["FECHA DESPACHO"] = despachos_mes["FECHA DESPACHO"].astype(str)
                despachos_mes.columns = ["Mes", "Cantidad"]
                
                fig_temporal = px.line(
                    despachos_mes,
                    x="Mes",
                    y="Cantidad",
                    title="Evolución Mensual de Despachos",
                    markers=True
                )
                fig_temporal.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_temporal, use_container_width=True)
            except Exception as e:
                st.warning(f"Error generando gráfico temporal: {str(e)}")
        
        with col2:
            # Despachos por día de la semana
            if "DIA_SEMANA" in df.columns:
                try:
                    dias_orden = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    df_dias_validos = df[df["DIA_SEMANA"].notna()]
                    despachos_dia = df_dias_validos.groupby("DIA_SEMANA").size().reindex(dias_orden).fillna(0)
                    
                    fig_dias = px.bar(
                        x=despachos_dia.index,
                        y=despachos_dia.values,
                        title="Despachos por Día de la Semana"
                    )
                    fig_dias.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_dias, use_container_width=True)
                except Exception as e:
                    st.warning(f"Error generando gráfico por día: {str(e)}")

def show_cost_analysis(df):
    """Muestra análisis de costos"""
    if "COSTO FLETE" not in df.columns:
        return
        
    st.subheader("💰 Análisis de Costos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Evolución de costos
        if "FECHA DESPACHO" in df.columns:
            try:
                df_fechas_validas = df[df["FECHA DESPACHO"].notna()]
                costos_mes = df_fechas_validas.groupby(df_fechas_validas["FECHA DESPACHO"].dt.to_period("M"))["COSTO FLETE"].sum().reset_index()
                costos_mes["FECHA DESPACHO"] = costos_mes["FECHA DESPACHO"].astype(str)
                
                fig_costos = px.line(
                    costos_mes,
                    x="FECHA DESPACHO",
                    y="COSTO FLETE",
                    title="Evolución Mensual de Costos de Flete"
                )
                fig_costos.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_costos, use_container_width=True)
            except Exception as e:
                st.warning(f"Error generando gráfico de costos: {str(e)}")
    
    with col2:
        # Distribución de costos
        try:
            df_costos_positivos = df[df["COSTO FLETE"] > 0]
            if not df_costos_positivos.empty:
                fig_dist_costos = px.histogram(
                    df_costos_positivos,
                    x="COSTO FLETE",
                    nbins=20,
                    title="Distribución de Costos de Flete"
                )
                st.plotly_chart(fig_dist_costos, use_container_width=True)
            else:
                st.info("No hay datos de costos positivos para mostrar")
        except Exception as e:
            st.warning(f"Error generando distribución de costos: {str(e)}")

def show_logistics_analysis(df):
    """Muestra análisis por logístico con interactividad"""
    if "ALISTAMIENTO" not in df.columns:
        return
        
    st.subheader("👷‍♂️ Performance por Logístico")
    
    try:
        # Resumen por alistamiento
        resumen_data = []
        for alistamiento in df["ALISTAMIENTO"].dropna().unique():
            subset = df[df["ALISTAMIENTO"] == alistamiento]
            
            data = {
                "ALISTAMIENTO": alistamiento,
                "Total_Despachos": len(subset),
                "Entregados": subset.get("IS_ENTREGADO", pd.Series()).sum(),
                "Costo_Total": subset.get("COSTO FLETE", pd.Series()).sum(),
                "Costo_Promedio": subset.get("COSTO FLETE", pd.Series()).mean(),
                "Tiempo_Prom_Dias": subset.get("TIEMPO_DESPACHO_DIAS", pd.Series()).mean()
            }
            data["Tasa_Entrega_%"] = (data["Entregados"] / data["Total_Despachos"] * 100) if data["Total_Despachos"] > 0 else 0
            resumen_data.append(data)
        
        resumen_alistamiento = pd.DataFrame(resumen_data).fillna(0).round(2)
        
        # Selector interactivo de logístico
        col1, col2 = st.columns([1, 3])
        with col1:
            logisticos_list = ["Ver todos"] + sorted(resumen_alistamiento["ALISTAMIENTO"].tolist())
            logistico_seleccionado = st.selectbox(
                "🔍 Ver detalles de:",
                logisticos_list,
                key="logistico_detail_selector"
            )
        
        # Formatear costos en la tabla
        resumen_display = resumen_alistamiento.copy()
        resumen_display["Costo_Total"] = resumen_display["Costo_Total"].apply(format_currency)
        resumen_display["Costo_Promedio"] = resumen_display["Costo_Promedio"].apply(format_currency)
        
        # Mostrar tabla
        st.dataframe(resumen_display, use_container_width=True)
        
        # Gráficos de performance
        if not resumen_alistamiento.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig_logistico = px.bar(
                    resumen_alistamiento,
                    x="ALISTAMIENTO",
                    y="Total_Despachos",
                    title="Despachos por Logístico (Click para ver detalles)"
                )
                fig_logistico.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_logistico, use_container_width=True)
            
            with col2:
                fig_tasa = px.bar(
                    resumen_alistamiento,
                    x="ALISTAMIENTO",
                    y="Tasa_Entrega_%",
                    title="Tasa de Entrega por Logístico"
                )
                fig_tasa.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_tasa, use_container_width=True)
        
        # Mostrar detalles si se seleccionó un logístico específico
        if logistico_seleccionado != "Ver todos":
            st.markdown("---")
            show_detailed_selection(df, "ALISTAMIENTO", logistico_seleccionado, 
                                   f"Detalles de {logistico_seleccionado}")
    
    except Exception as e:
        st.warning(f"Error en análisis de logísticos: {str(e)}")

def show_channel_analysis(df):
    """Muestra análisis por canal de venta con interactividad"""
    if "CANAL_VENTA" not in df.columns:
        return
        
    st.subheader("🛒 Análisis por Canal de Venta")
    
    try:
        # Resumen por canal
        resumen_data = []
        for canal in df["CANAL_VENTA"].dropna().unique():
            subset = df[df["CANAL_VENTA"] == canal]
            
            data = {
                "CANAL_VENTA": canal,
                "Total_Despachos": len(subset),
                "Entregados": subset.get("IS_ENTREGADO", pd.Series()).sum(),
                "Costo_Total": subset.get("COSTO FLETE", pd.Series()).sum(),
                "Costo_Promedio": subset.get("COSTO FLETE", pd.Series()).mean()
            }
            data["Tasa_Entrega_%"] = (data["Entregados"] / data["Total_Despachos"] * 100) if data["Total_Despachos"] > 0 else 0
            resumen_data.append(data)
        
        resumen_canal = pd.DataFrame(resumen_data).fillna(0).round(2)
        
        # Selector interactivo de canal
        col1, col2 = st.columns([1, 3])
        with col1:
            canales_list = ["Ver todos"] + sorted(resumen_canal["CANAL_VENTA"].tolist())
            canal_seleccionado = st.selectbox(
                "🔍 Ver detalles de:",
                canales_list,
                key="canal_detail_selector"
            )
        
        # Formatear costos en la tabla
        resumen_display = resumen_canal.copy()
        resumen_display["Costo_Total"] = resumen_display["Costo_Total"].apply(format_currency)
        resumen_display["Costo_Promedio"] = resumen_display["Costo_Promedio"].apply(format_currency)
        
        st.dataframe(resumen_display, use_container_width=True)
        
        if not resumen_canal.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig_canal = px.pie(
                    resumen_canal,
                    values="Total_Despachos",
                    names="CANAL_VENTA",
                    title="Distribución de Despachos por Canal (Click para detalles)"
                )
                st.plotly_chart(fig_canal, use_container_width=True)
            
            with col2:
                fig_canal_costo = px.bar(
                    resumen_canal,
                    x="CANAL_VENTA",
                    y="Costo_Total",
                    title="Costo Total por Canal"
                )
                fig_canal_costo.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_canal_costo, use_container_width=True)
        
        # Mostrar detalles si se seleccionó un canal específico
        if canal_seleccionado != "Ver todos":
            st.markdown("---")
            show_detailed_selection(df, "CANAL_VENTA", canal_seleccionado, 
                                   f"Detalles de {canal_seleccionado}")
    
    except Exception as e:
        st.warning(f"Error en análisis de canales: {str(e)}")

def show_city_analysis(df):
    """Muestra análisis por ciudad con interactividad"""
    if "CIUDAD" not in df.columns:
        return
        
    st.subheader("🏙️ Análisis por Ciudad")
    
    try:
        # Resumen por ciudad
        resumen_data = []
        for ciudad in df["CIUDAD"].dropna().unique():
            subset = df[df["CIUDAD"] == ciudad]
            
            data = {
                "CIUDAD": ciudad,
                "Total_Despachos": len(subset),
                "Entregados": subset.get("IS_ENTREGADO", pd.Series()).sum(),
                "Costo_Total": subset.get("COSTO FLETE", pd.Series()).sum(),
                "Costo_Promedio": subset.get("COSTO FLETE", pd.Series()).mean(),
                "Tiempo_Prom_Dias": subset.get("TIEMPO_DESPACHO_DIAS", pd.Series()).mean()
            }
            data["Tasa_Entrega_%"] = (data["Entregados"] / data["Total_Despachos"] * 100) if data["Total_Despachos"] > 0 else 0
            resumen_data.append(data)
        
        resumen_ciudad = pd.DataFrame(resumen_data).fillna(0).round(2)
        
        # Selector interactivo de ciudad
        col1, col2 = st.columns([1, 3])
        with col1:
            ciudades_list = ["Ver todos"] + sorted(resumen_ciudad["CIUDAD"].tolist())
            ciudad_seleccionada = st.selectbox(
                "🔍 Ver detalles de:",
                ciudades_list,
                key="ciudad_detail_selector"
            )
        
        # Formatear costos en la tabla
        resumen_display = resumen_ciudad.copy()
        resumen_display["Costo_Total"] = resumen_display["Costo_Total"].apply(format_currency)
        resumen_display["Costo_Promedio"] = resumen_display["Costo_Promedio"].apply(format_currency)
        
        st.dataframe(resumen_display, use_container_width=True)
        
        if not resumen_ciudad.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig_ciudad = px.pie(
                    resumen_ciudad,
                    values="Total_Despachos",
                    names="CIUDAD",
                    title="Distribución de Despachos por Ciudad (Click para detalles)"
                )
                st.plotly_chart(fig_ciudad, use_container_width=True)
            
            with col2:
                fig_ciudad_costo = px.bar(
                    resumen_ciudad,
                    x="CIUDAD",
                    y="Costo_Total",
                    title="Costo Total por Ciudad"
                )
                fig_ciudad_costo.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_ciudad_costo, use_container_width=True)
        
        # Mostrar detalles si se seleccionó una ciudad específica
        if ciudad_seleccionada != "Ver todos":
            st.markdown("---")
            show_detailed_selection(df, "CIUDAD", ciudad_seleccionada, 
                                   f"Detalles de {ciudad_seleccionada}")
    
    except Exception as e:
        st.warning(f"Error en análisis de ciudades: {str(e)}")

def show_temporal_cost_analysis(df, periodo_seleccionado):
    """Muestra análisis de costos por período temporal"""
    
    if "COSTO FLETE" not in df.columns or "FECHA DESPACHO" not in df.columns:
        st.error("DEBUG: Saliendo por falta de columnas")
        return
        
    st.subheader(f"💰 Análisis de Gastos en Fletes - {periodo_seleccionado}")
    
    try:
        df_validos = df[(df["FECHA DESPACHO"].notna()) & (df["COSTO FLETE"].fillna(0) > 0)]
        
        if df_validos.empty:
            st.warning("No hay datos de costos válidos para el período seleccionado")
            return
        
        # Métricas del período
        costo_total_periodo = df_validos["COSTO FLETE"].sum()
        costo_promedio_periodo = df_validos["COSTO FLETE"].mean()
        despachos_periodo = len(df_validos)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Gasto Total en Fletes", format_currency(costo_total_periodo))
        with col2:
            st.metric("📊 Costo Promedio por Envío", format_currency(costo_promedio_periodo))
        with col3:
            st.metric("📦 Total Despachos con Costo", f"{despachos_periodo:,}")
        
        # Análisis detallado por sub-períodos
        col1, col2 = st.columns(2)
        
        with col1:
            if periodo_seleccionado in ["Año actual", "Todos los datos"]:
                # Gastos por mes
                gastos_mes = df_validos.groupby(df_validos["FECHA DESPACHO"].dt.to_period("M"))["COSTO FLETE"].sum().reset_index()
                gastos_mes["FECHA DESPACHO"] = gastos_mes["FECHA DESPACHO"].astype(str)
                
                fig_gastos_mes = px.bar(
                    gastos_mes,
                    x="FECHA DESPACHO",
                    y="COSTO FLETE",
                    title="Gastos en Fletes por Mes"
                )
                fig_gastos_mes.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_gastos_mes, use_container_width=True)
            
            elif periodo_seleccionado == "Mes actual":
                # Gastos por día del mes actual solamente
                gastos_dia = df_validos.groupby(df_validos["FECHA DESPACHO"].dt.date)["COSTO FLETE"].sum().reset_index()
                gastos_dia["DIA"] = gastos_dia["FECHA DESPACHO"].dt.day
                gastos_dia = gastos_dia.sort_values("FECHA DESPACHO")
                
                fig_gastos_dia = px.bar(
                    gastos_dia,
                    x="DIA",
                    y="COSTO FLETE",
                    title=f"Gastos en Fletes por Día - {datetime.now().strftime('%B %Y')}",
                    labels={"DIA": "Día del Mes", "COSTO FLETE": "Costo Flete"}
                )
                st.plotly_chart(fig_gastos_dia, use_container_width=True)
        
        with col2:
            # Gastos por canal en el período
            if "CANAL_VENTA" in df_validos.columns:
                gastos_canal = df_validos.groupby("CANAL_VENTA")["COSTO FLETE"].sum().reset_index()
                gastos_canal = gastos_canal.sort_values("COSTO FLETE", ascending=False)
                
                fig_gastos_canal = px.pie(
                    gastos_canal,
                    values="COSTO FLETE",
                    names="CANAL_VENTA",
                    title="Distribución de Gastos por Canal"
                )
                st.plotly_chart(fig_gastos_canal, use_container_width=True)
        
        # Tabla detallada de gastos por categoría
        st.subheader("📊 Desglose Detallado de Gastos")
        
        categorias_gastos = []
        
        # Por logístico
        if "ALISTAMIENTO" in df_validos.columns:
            for alistamiento in df_validos["ALISTAMIENTO"].dropna().unique():
                subset = df_validos[df_validos["ALISTAMIENTO"] == alistamiento]
                categorias_gastos.append({
                    "Categoría": "Logístico",
                    "Nombre": alistamiento,
                    "Gasto_Total": subset["COSTO FLETE"].sum(),
                    "Promedio_Envío": subset["COSTO FLETE"].mean(),
                    "Cantidad_Envíos": len(subset)
                })
        
        # Por canal
        if "CANAL_VENTA" in df_validos.columns:
            for canal in df_validos["CANAL_VENTA"].dropna().unique():
                subset = df_validos[df_validos["CANAL_VENTA"] == canal]
                categorias_gastos.append({
                    "Categoría": "Canal",
                    "Nombre": canal,
                    "Gasto_Total": subset["COSTO FLETE"].sum(),
                    "Promedio_Envío": subset["COSTO FLETE"].mean(),
                    "Cantidad_Envíos": len(subset)
                })
        
        # Por ciudad
        if "CIUDAD" in df_validos.columns:
            for ciudad in df_validos["CIUDAD"].dropna().unique():
                subset = df_validos[df_validos["CIUDAD"] == ciudad]
                categorias_gastos.append({
                    "Categoría": "Ciudad",
                    "Nombre": ciudad,
                    "Gasto_Total": subset["COSTO FLETE"].sum(),
                    "Promedio_Envío": subset["COSTO FLETE"].mean(),
                    "Cantidad_Envíos": len(subset)
                })
        
        if categorias_gastos:
            df_categorias = pd.DataFrame(categorias_gastos).round(2)
            df_categorias = df_categorias.sort_values("Gasto_Total", ascending=False)
            
            # Formatear costos
            df_categorias_display = df_categorias.copy()
            df_categorias_display["Gasto_Total"] = df_categorias_display["Gasto_Total"].apply(format_currency)
            df_categorias_display["Promedio_Envío"] = df_categorias_display["Promedio_Envío"].apply(format_currency)
            
            st.dataframe(df_categorias_display, use_container_width=True)
            
            # Descarga del reporte
            csv = df_categorias.to_csv(index=False)
            st.download_button(
                label=f"📥 Descargar reporte de gastos - {periodo_seleccionado}",
                data=csv,
                file_name=f"reporte_gastos_fletes_{periodo_seleccionado.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    except Exception as e:
        st.warning(f"Error en análisis temporal de costos: {str(e)}")

def show_seller_analysis(df):
    """Muestra análisis por vendedor con interactividad"""
    st.subheader("🤝 Análisis por Vendedor")
    
    try:
        # Resumen por vendedor
        resumen_data = []
        for vendedor in df["VENDEDOR_NOMBRE"].dropna().unique():
            subset = df[df["VENDEDOR_NOMBRE"] == vendedor]
            
            data = {
                "VENDEDOR_NOMBRE": vendedor,
                "Total_Despachos": len(subset),
                "Entregados": subset.get("IS_ENTREGADO", pd.Series()).sum(),
                "Costo_Total": subset.get("COSTO FLETE", pd.Series()).sum(),
                "Costo_Promedio": subset.get("COSTO FLETE", pd.Series()).mean(),
                "Tiempo_Prom_Dias": subset.get("TIEMPO_DESPACHO_DIAS", pd.Series()).mean()
            }
            data["Tasa_Entrega_%"] = (data["Entregados"] / data["Total_Despachos"] * 100) if data["Total_Despachos"] > 0 else 0
            resumen_data.append(data)
        
        resumen_vendedor = pd.DataFrame(resumen_data).fillna(0).round(2)
        resumen_vendedor = resumen_vendedor.sort_values("Total_Despachos", ascending=False)
        
        # Selector interactivo de vendedor
        col1, col2 = st.columns([1, 3])
        with col1:
            vendedores_list = ["Ver todos"] + sorted(resumen_vendedor["VENDEDOR_NOMBRE"].tolist())
            vendedor_seleccionado = st.selectbox(
                "🔍 Ver detalles de:",
                vendedores_list,
                key="vendedor_detail_selector"
            )
        
        # Formatear costos en la tabla
        resumen_display = resumen_vendedor.copy()
        resumen_display["Costo_Total"] = resumen_display["Costo_Total"].apply(format_currency)
        resumen_display["Costo_Promedio"] = resumen_display["Costo_Promedio"].apply(format_currency)
        
        st.dataframe(resumen_display, use_container_width=True, height=300)
        
        if not resumen_vendedor.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                top_vendedores = resumen_vendedor.head(10)
                fig_top_vendedores = px.bar(
                    top_vendedores,
                    x="Total_Despachos",
                    y="VENDEDOR_NOMBRE",
                    orientation="h",
                    title="Top 10 Vendedores (Click para detalles)"
                )
                fig_top_vendedores.update_layout(height=500)
                st.plotly_chart(fig_top_vendedores, use_container_width=True)
            
            with col2:
                vendedores_relevantes = resumen_vendedor[resumen_vendedor["Total_Despachos"] >= 5].head(10)
                if not vendedores_relevantes.empty:
                    fig_tasa_vendedores = px.bar(
                        vendedores_relevantes,
                        x="Tasa_Entrega_%",
                        y="VENDEDOR_NOMBRE",
                        orientation="h",
                        title="Tasa de Entrega por Vendedor (≥5 despachos)"
                    )
                    fig_tasa_vendedores.update_layout(height=500)
                    st.plotly_chart(fig_tasa_vendedores, use_container_width=True)
        
        # Mostrar detalles si se seleccionó un vendedor específico
        if vendedor_seleccionado != "Ver todos":
            st.markdown("---")
            show_detailed_selection(df, "VENDEDOR_NOMBRE", vendedor_seleccionado, 
                                   f"Detalles de {vendedor_seleccionado}")
    
    except Exception as e:
        st.warning(f"Error en análisis de vendedores: {str(e)}")
        
def show_time_analysis(df):
    """Muestra análisis de tiempos"""
    if "TIEMPO_DESPACHO_DIAS" not in df.columns:
        return
        
    st.subheader("⏱️ Análisis de Tiempos de Despacho")
    
    try:
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribución de tiempos (filtrar valores razonables)
            df_tiempo_valido = df[(df["TIEMPO_DESPACHO_DIAS"] >= 0) & (df["TIEMPO_DESPACHO_DIAS"] <= 30)]
            if not df_tiempo_valido.empty:
                fig_tiempo_dist = px.histogram(
                    df_tiempo_valido,
                    x="TIEMPO_DESPACHO_DIAS",
                    nbins=30,
                    title="Distribución de Tiempos de Despacho (0-30 días)"
                )
                st.plotly_chart(fig_tiempo_dist, use_container_width=True)
            else:
                st.info("No hay datos válidos de tiempo de despacho")
        
        with col2:
            # Box plot por canal
            if "CANAL_VENTA" in df.columns and not df_tiempo_valido.empty:
                fig_tiempo_canal = px.box(
                    df_tiempo_valido,
                    x="CANAL_VENTA",
                    y="TIEMPO_DESPACHO_DIAS",
                    title="Tiempos de Despacho por Canal"
                )
                fig_tiempo_canal.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_tiempo_canal, use_container_width=True)
    
    except Exception as e:
        st.warning(f"Error en análisis de tiempos: {str(e)}")

def show_detailed_data(df):
    """Muestra datos detallados"""
    with st.expander("🔍 Ver Datos Detallados"):
        # Crear una copia para mostrar con formatos
        df_display = df.copy()
        
        # Formatear columnas de costo si existen
        cost_columns = ["COSTO FLETE"]
        for col in cost_columns:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(format_currency)
        
        st.dataframe(df_display, use_container_width=True)
        
        # Opción de descarga
        try:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Descargar datos filtrados",
                data=csv,
                file_name=f"despachos_detallados_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.warning(f"Error preparando descarga: {str(e)}")

def show_help_info():
    """Muestra información de ayuda"""
    st.info("👆 **Sube un archivo Excel para comenzar el análisis**")
    
    # Información de ayuda
    st.markdown("""
    ### 📋 Formato del archivo Excel esperado:
    
    **Columnas principales:**
    - `FECHA`: Fecha de facturación
    - `FECHA DESPACHO`: Fecha de despacho
    - `NRO. CRUCE`: Número de referencia
    - `ESTATUS`: Estado del despacho (ENTREGADO, etc.)
    - `COSTO FLETE`: Costo del transporte
    - `ALISTAMIENTO`: Nombre del logístico
    - `PLATAFORMA`: Canal de venta
    - `TERCERO`: Cliente directo (cuando no es plataforma)
    - `VEND`: Código del vendedor
    
    **Archivo de vendedores (opcional):**
    - `VENDEDOR`: Código del vendedor
    - `NOMBRE`: Nombre del vendedor
    
    ### 🚀 Funcionalidades del Dashboard:
    - ✅ Métricas KPI en tiempo real con formato de moneda
    - 🚨 Alertas automáticas para productos facturados sin despachar
    - 📊 Análisis temporal y de tendencias
    - 💰 Análisis detallado de costos con formato de moneda
    - 👷‍♂️ Performance individual por logístico
    - 🛒 Análisis por canal de venta
    - 🤝 Análisis completo por vendedor (con cruce mejorado de datos)
    - ⏱️ Análisis de tiempos de despacho
    - 🧹 Limpieza automática y robusta de datos
    - 📥 Descarga de reportes en CSV
    - 🔍 Debug mejorado para identificar problemas de carga
    
    ### 📝 Notas importantes:
    - El archivo debe estar en formato Excel (.xlsx o .xls)
    - Las fechas deben estar en formato de fecha válido
    - Los costos deben ser valores numéricos (se limpian automáticamente)
    - Las columnas pueden tener espacios adicionales (se limpian automáticamente)
    - El sistema ahora muestra información de debug para ayudar a identificar problemas
    
    ### 🔧 Correcciones implementadas:
    - ✅ Corregido error de `update_xaxis` → `update_layout(xaxis_tickangle=-45)`
    - ✅ Mejorado el conteo de registros con información de debug
    - ✅ Mejorado el cruce de datos de vendedores con validaciones
    - ✅ Añadido formato de moneda en todas las visualizaciones
    - ✅ Mejor manejo de datos faltantes y errores
    - ✅ Limpieza más robusta de datos de costos
    """)

# ==========================
# EJECUTAR APLICACIÓN
# ==========================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Error general en la aplicación: {str(e)}")
        import traceback
        st.error(f"Detalles del error: {traceback.format_exc()}")
        st.info("Por favor, recarga la página e intenta nuevamente.")