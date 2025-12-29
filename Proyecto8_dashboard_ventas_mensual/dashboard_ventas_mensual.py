import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Logo en la esquina superior
top_col1, top_col2 = st.columns([0.7,0.3])
with top_col2:
    st.image("https://ekonomodo.com/cdn/shop/files/Logo-Ekonomodo-color.svg?v=1736956350&width=450", width=5000)

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Ventas",
    page_icon="📊",
    layout="wide"
)

# Título principal
st.title("Dashboard de Análisis de Ventas")
st.markdown("---")

# Sidebar para cargar datos y configuración
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # URL fija de Google Sheets
    google_sheet_url = "https://docs.google.com/spreadsheets/d/16BlZobNzpy0zat8NyQFbMH02EWDRxqB2IG1yT_8eNPs/edit?usp=sharing"
    
    st.markdown("---")
    
    # Selector de meses
    st.subheader("📅 Seleccionar Meses")
    meses_disponibles = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 
                         'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']
    
    meses_seleccionados = st.multiselect(
        "Elige uno o más meses:",
        meses_disponibles,
        default=['NOVIEMBRE']
    )
    
    st.markdown("---")
    
    # Meta de ventas
    meta_ventas = st.number_input(
        "🎯 Meta de Ventas del Mes ($)",
        min_value=0.0,
        value=750000000.0,
        step=10000000.0,
        format="%.2f"
    )

# Función para normalizar datos
def normalizar_datos(df):
    """Limpia y normaliza el DataFrame"""
    # Limpiar nombres de columnas
    df.columns = df.columns.str.strip().str.upper()
    
    # Identificar la tercera columna DESCRIPCION
    descripcion_cols = [col for col in df.columns if 'DESCRIPCION' in col]
    if len(descripcion_cols) >= 3:
        # Renombrar la tercera columna DESCRIPCION
        df = df.rename(columns={descripcion_cols[2]: 'DESCRIPCION_PRODUCTO'})
        # Eliminar las otras columnas DESCRIPCION si existen
        cols_to_drop = [descripcion_cols[0], descripcion_cols[1]]
        df = df.drop(columns=cols_to_drop, errors='ignore')
    elif len(descripcion_cols) > 0:
        df = df.rename(columns={descripcion_cols[-1]: 'DESCRIPCION_PRODUCTO'})
    
    # Limpiar espacios en todas las columnas de texto
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()
    
    # Asegurar que CANTIDAD y VALOR sean numéricos
    if 'CANTIDAD' in df.columns:
        df['CANTIDAD'] = pd.to_numeric(df['CANTIDAD'], errors='coerce').fillna(0)
    if 'VALOR' in df.columns:
        df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce').fillna(0)
    
    # EXCLUIR FLETE ENVIO de los cálculos
    if 'DESCRIPCION_PRODUCTO' in df.columns:
        df = df[df['DESCRIPCION_PRODUCTO'].str.upper() != 'FLETE ENVIO']
    
    return df

def cargar_google_sheets(url, meses):
    """Carga datos desde Google Sheets para uno o múltiples meses"""
    try:
        if '/edit' in url:
            url = url.split('/edit')[0]
        sheet_id = url.split('/d/')[1].split('/')[0]
        
        dfs = []
        for mes in meses:
            try:
                # Intentar cargar cada mes
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={mes}"
                df_mes = pd.read_csv(csv_url, thousands='.', decimal=',')
                df_mes['MES'] = mes  # Agregar columna de mes
                dfs.append(df_mes)
                st.sidebar.success(f"✅ {mes} cargado")
            except Exception as e:
                st.sidebar.warning(f"⚠️ {mes} no encontrado o sin datos")
        
        if not dfs:
            st.error("No se pudo cargar ningún mes")
            return None
        
        # Combinar todos los DataFrames
        df_combined = pd.concat(dfs, ignore_index=True)
        return normalizar_datos(df_combined)
        
    except Exception as e:
        st.error(f"Error al cargar datos de Google Sheets: {str(e)}")
        return None

# Cargar datos
df = None

if google_sheet_url and meses_seleccionados:
    with st.spinner(f"Cargando datos de {len(meses_seleccionados)} mes(es)..."):
        df = cargar_google_sheets(google_sheet_url, meses_seleccionados)
elif google_sheet_url and not meses_seleccionados:
    st.warning("⚠️ Por favor selecciona al menos un mes")
    df = None
if not google_sheet_url:
    st.error("No se pudo conectar con Google Sheets")

# Mostrar dashboard si hay datos
if df is not None and not df.empty:
    
    # KPIs principales
    col1, col2, col3, col4 = st.columns(4)
    
    total_ventas = df['VALOR'].sum()
    total_unidades = df['CANTIDAD'].sum()
    num_vendedores = df['NOMBRE'].nunique()
    num_productos = df['REFERENCIA'].nunique()
    
    with col1:
        st.metric(
            "💰 Ventas Totales",
            f"${total_ventas:,.2f}",
            f"{((total_ventas/meta_ventas)*100):.1f}% de la meta"
        )
    
    with col2:
        faltante = meta_ventas - total_ventas
        st.metric(
            "🎯 Faltante para Meta",
            f"${faltante:,.2f}",
            f"{((faltante/meta_ventas)*100):.1f}%"
        )
    
    with col3:
        st.metric("📦 Unidades Vendidas", f"{total_unidades:,.0f}")
    
    with col4:
        st.metric("👥 Vendedores Activos", num_vendedores)
    
    st.markdown("---")
    
    # Gráfico de progreso de meta
    st.subheader("Progreso hacia la Meta")
    progreso = (total_ventas / meta_ventas) * 100
    
    fig_meta = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = progreso,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "% de Meta Alcanzada"},
        delta = {'reference': 100},
        gauge = {
            'axis': {'range': [None, 120]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 80], 'color': "gray"},
                {'range': [80, 100], 'color': "lightgreen"},
                {'range': [100, 120], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 100
            }
        }
    ))
    
    fig_meta.update_layout(height=300)
    st.plotly_chart(fig_meta, use_container_width=True)
    
    st.markdown("---")
    
    # Dos columnas para gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top 10 Vendedores")
        ventas_vendedor = df.groupby('NOMBRE')['VALOR'].sum().sort_values(ascending=False).head(10)
        fig_vendedores = px.bar(
            x=ventas_vendedor.values,
            y=ventas_vendedor.index,
            orientation='h',
            labels={'x': 'Ventas ($)', 'y': 'Vendedor'},
            color=ventas_vendedor.values,
            color_continuous_scale='Blues'
        )
        fig_vendedores.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_vendedores, use_container_width=True)
    
    with col2:
        st.subheader("🌆 Ventas por Ciudad")
        ventas_ciudad = df.groupby('CIUDAD')['VALOR'].sum().sort_values(ascending=False)
        fig_ciudad = px.pie(
            values=ventas_ciudad.values,
            names=ventas_ciudad.index,
            hole=0.4
        )
        fig_ciudad.update_layout(height=400)
        st.plotly_chart(fig_ciudad, use_container_width=True)
    
    st.markdown("---")
    
    # Productos más vendidos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 Top 10 Productos (Por Valor)")
        ventas_producto = df.groupby('DESCRIPCION_PRODUCTO' if 'DESCRIPCION_PRODUCTO' in df.columns else 'REFERENCIA')['VALOR'].sum().sort_values(ascending=False).head(10)
        fig_productos = px.bar(
            x=ventas_producto.values,
            y=ventas_producto.index,
            orientation='h',
            labels={'x': 'Ventas ($)', 'y': 'Producto'},
            color=ventas_producto.values,
            color_continuous_scale='Greens'
        )
        fig_productos.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_productos, use_container_width=True)
    
    with col2:
        st.subheader("📊 Top 10 Productos (Por Cantidad)")
        cantidad_producto = df.groupby('DESCRIPCION_PRODUCTO' if 'DESCRIPCION_PRODUCTO' in df.columns else 'REFERENCIA')['CANTIDAD'].sum().sort_values(ascending=False).head(10)
        fig_cantidad = px.bar(
            x=cantidad_producto.values,
            y=cantidad_producto.index,
            orientation='h',
            labels={'x': 'Unidades', 'y': 'Producto'},
            color=cantidad_producto.values,
            color_continuous_scale='Oranges'
        )
        fig_cantidad.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_cantidad, use_container_width=True)
    
    st.markdown("---")
    
    # Tabla detallada de vendedores
    st.subheader("Detalle por Vendedor")
    detalle_vendedor = df.groupby('NOMBRE').agg({
        'VALOR': 'sum',
        'CANTIDAD': 'sum',
        'REFERENCIA': 'count',
        'CIUDAD': 'first'
    }).round(2)
    detalle_vendedor.columns = ['Ventas ($)', 'Unidades', 'Num. Transacciones', 'Ciudad']
    detalle_vendedor = detalle_vendedor.sort_values('Ventas ($)', ascending=False)
    detalle_vendedor['% de Meta Individual'] = (detalle_vendedor['Ventas ($)'] / meta_ventas * 100).round(2)
    
    # Formatear la tabla para mostrar
    detalle_vendedor_formatted = detalle_vendedor.copy()
    detalle_vendedor_formatted['Ventas ($)'] = detalle_vendedor_formatted['Ventas ($)'].apply(lambda x: f"${x:,.2f}")
    detalle_vendedor_formatted['% de Meta Individual'] = detalle_vendedor_formatted['% de Meta Individual'].apply(lambda x: f"{x:.2f}%")
    
    st.dataframe(detalle_vendedor_formatted, use_container_width=True)
    
    # Opción de descargar datos procesados
    st.markdown("---")
    st.subheader("💾 Exportar Datos")
    
    csv = detalle_vendedor.to_csv().encode('utf-8')
    st.download_button(
        label="📥 Descargar Resumen por Vendedor (CSV)",
        data=csv,
        file_name=f"resumen_ventas_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

else:
    # Mensaje de bienvenida
    st.info("👋 Bienvenido! Por favor carga tus datos desde Google Sheets o un archivo local en el panel lateral.")
    
    st.markdown("""
    ### 📌 Instrucciones:
    
    **Opción 1: Google Sheets**
    1. Sube tu archivo Excel a Google Drive
    2. Abre el archivo con Google Sheets
    3. Asegúrate que la hoja se llame **NOVIEMBRE**
    4. Ve a Archivo → Compartir → Compartir con otros
    5. Cambia el acceso a "Cualquier persona con el enlace"
    6. Copia el enlace y pégalo en el panel lateral
    
    **Opción 2: Archivo Local**
    1. Haz clic en "Browse files" en el panel lateral
    2. Selecciona tu archivo Excel
    
    ### 📊 Columnas requeridas:
    - CIUDAD
    - NOMBRE (vendedor)
    - REFERENCIA (código del producto)
    - DESCRIPCION (descripción del producto - tercera columna con este nombre)
    - CANTIDAD
    - VALOR
    """)