# streamlit_dashboard_pedidos_ceo.py
# Dashboard CEO Premium para análisis completo de pedidos por comercios
# Requisitos: pip install streamlit pandas plotly openpyxl seaborn

import streamlit as st
import re
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(layout="wide", page_title="Dashboard CEO - Análisis de Pedidos", page_icon="📊")

# Logo en la esquina superior
top_col1, top_col2 = st.columns([0.9,0.1])
with top_col2:
    st.image("https://ekonomodo.com/cdn/shop/files/Logo-Ekonomodo-color.svg?v=1736956350&width=450", width=5000)

# ----------------------- Custom CSS for CEO styling -----------------------
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .alert-high { background-color: #ffebee; border-left: 4px solid #f44336; padding: 10px; }
    .alert-medium { background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 10px; }
    .alert-low { background-color: #e8f5e8; border-left: 4px solid #4caf50; padding: 10px; }
    .section-header {
        background: linear-gradient(90deg, #434343 0%, #000000 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 20px 0 10px 0;
        text-align: center;
        font-weight: bold;
        font-size: 1.2em;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------- Helper Functions -----------------------
@st.cache_data
def load_excel(file):
    return pd.read_excel(file, engine='openpyxl',header=6)

@st.cache_data
def preprocess_orders(df):
    df = df.copy()
    # Normalizar nombres de columnas
    df.columns = [c.strip() for c in df.columns]

    # Fechas - Mejor manejo de errores
    for col in ['FECHA', 'FECHA ENT.', 'FECHA PAC']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Valores numéricos
    numeric_cols = ['VAL.PEDIDO', 'VAL.ENTREGAD', 'CANT.PEDIDA', 'CANT.ENTREGA', 'CANT PEND', 'CANT.PENDIENTE LOTE']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Limpieza de códigos
    if 'COMPROBA' in df.columns:
        df['COMPROBA'] = df['COMPROBA'].astype(str).str.strip()

    # Columnas auxiliares - Solo si hay fechas válidas
    if 'FECHA' in df.columns:
        # Crear FECHA_DATE solo donde FECHA no es nulo
        df['FECHA_DATE'] = df['FECHA'].dt.date
        
        # Solo calcular columnas temporales donde hay fechas válidas
        mask_fechas_validas = df['FECHA'].notna()
        
        df['MES'] = None
        df['SEMANA'] = None
        df['DIA_SEMANA'] = None
        
        if mask_fechas_validas.any():
            df.loc[mask_fechas_validas, 'MES'] = df.loc[mask_fechas_validas, 'FECHA'].dt.to_period('M')
            df.loc[mask_fechas_validas, 'SEMANA'] = df.loc[mask_fechas_validas, 'FECHA'].dt.isocalendar().week
            df.loc[mask_fechas_validas, 'DIA_SEMANA'] = df.loc[mask_fechas_validas, 'FECHA'].dt.day_name()
    
    # Calcular eficiencia de entrega
    if 'VAL.PEDIDO' in df.columns and 'VAL.ENTREGAD' in df.columns:
        df['EFICIENCIA_ENTREGA'] = np.where(df['VAL.PEDIDO'] > 0, 
                                           df['VAL.ENTREGAD'] / df['VAL.PEDIDO'], 0)
    
    # Estado del pedido
    if 'CANT PEND' in df.columns:
        df['ESTADO_PEDIDO'] = np.where(df['CANT PEND'] == 0, 'Completado', 
                              np.where(df['CANT PEND'] > 0, 'Pendiente', 'Error'))

    return df

@st.cache_data
def merge_comercios(df_orders, df_shops, code_col_orders='COMPROBA'):
    df = df_orders.copy()
    df_shops = df_shops.copy()
    
    # Limpiar columnas
    df_shops.columns = [c.strip() for c in df_shops.columns]
    code_col_shops = df_shops.columns[0]
    name_col = df_shops.columns[1] if len(df_shops.columns) > 1 else df_shops.columns[0]

    df_shops[code_col_shops] = df_shops[code_col_shops].astype(str).str.strip()
    df_shops[name_col] = df_shops[name_col].astype(str).str.strip()

    merged = df.merge(df_shops, left_on=code_col_orders, right_on=code_col_shops, how='left')
    merged = merged.rename(columns={name_col: 'NOMBRE_COMERCIO'})
    merged['NOMBRE_COMERCIO'] = merged['NOMBRE_COMERCIO'].fillna(merged[code_col_orders])
    
    return merged

@st.cache_data
def merge_vendedores(df_orders, df_vendors, code_col_orders='VEND'):
    df = df_orders.copy()
    df_vendors = df_vendors.copy()
    
    # Limpiar nombres de columnas - convertir todo a string primero
    df_vendors.columns = [str(c).strip() if hasattr(c, 'strip') else str(c) for c in df_vendors.columns]
    
    # Eliminar filas completamente vacías
    df_vendors = df_vendors.dropna(how='all').reset_index(drop=True)
    
    # Buscar las columnas por posición ya que los nombres pueden estar mal
    # Asumir: primera columna = VENDEDOR, tercera columna = NOMBRE
    if len(df_vendors.columns) >= 2:
        code_col_vendors = df_vendors.columns[0]  # Primera columna
        name_col = df_vendors.columns[1]          # Segunda columna
    else:
        st.error(f"El archivo de vendedores debe tener al menos 2 columnas. Encontradas: {len(df_vendors.columns)}")
        return df
    
    # Crear copia para trabajo con las columnas identificadas
    vendors_clean = df_vendors[[code_col_vendors, name_col]].copy()
    
    # Función para normalizar códigos
    def clean_code(code):
        try:
            if pd.isna(code):
                return ''
            code_str = str(code).strip()
            # Asegurarse de quitar ceros solo si es estrictamente necesario
            return code_str.lstrip('0') or '0'
        except:
            return str(code) if code is not None else ''

    
    # Función para limpiar nombres  
    def clean_name(name):
        try:
            if pd.isna(name):
                return ''
            return str(name).strip()
        except:
            return str(name) if name is not None else ''
    
    # Aplicar limpieza
    vendors_clean['VENDEDOR_CLEAN'] = vendors_clean[code_col_vendors].apply(clean_code)
    vendors_clean['NOMBRE_CLEAN'] = vendors_clean[name_col].apply(clean_name)
    
    # Limpiar códigos en df principal
    df['VEND_CLEAN'] = df[code_col_orders].apply(clean_code)

    # 👉 DEBUG: Comparar códigos después de limpiar
    st.write("Códigos en pedidos (df_orders) después de limpiar:")
    st.write(df['VEND_CLEAN'].unique())

    st.write("Códigos en archivo de vendedores después de limpiar:")
    st.write(vendors_clean['VENDEDOR_CLEAN'].unique())
    
    # Eliminar duplicados en vendedores
    vendors_clean = vendors_clean.drop_duplicates(subset=['VENDEDOR_CLEAN'], keep='first')
    
    # Hacer merge
    merged = df.merge(
        vendors_clean[['VENDEDOR_CLEAN', 'NOMBRE_CLEAN']],
        left_on='VEND_CLEAN',
        right_on='VENDEDOR_CLEAN',
        how='left'
    )
    
    # Limpiar resultado
    merged['NOMBRE_VENDEDOR'] = merged['NOMBRE_CLEAN'].fillna(merged[code_col_orders].astype(str))
    merged = merged.drop(['VENDEDOR_CLEAN', 'VEND_CLEAN', 'NOMBRE_CLEAN'], axis=1, errors='ignore')
    
    return merged

def calculate_growth_rate(df, date_col='FECHA_DATE', value_col='VAL.PEDIDO', periods=30):
    """Calcular tasa de crecimiento comparando últimos N días vs N días anteriores"""
    if df.empty:
        return 0
    
    # Filtrar solo registros con fechas válidas
    df_with_dates = df.dropna(subset=[date_col])
    if df_with_dates.empty:
        return 0
    
    df_sorted = df_with_dates.sort_values(date_col)
    today = df_sorted[date_col].max()
    
    # Últimos N días
    recent_start = today - timedelta(days=periods)
    recent_data = df_sorted[df_sorted[date_col] >= recent_start]
    recent_total = recent_data[value_col].sum()
    
    # N días anteriores
    previous_end = recent_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=periods)
    previous_data = df_sorted[(df_sorted[date_col] >= previous_start) & 
                             (df_sorted[date_col] <= previous_end)]
    previous_total = previous_data[value_col].sum()
    
    if previous_total == 0:
        return 100 if recent_total > 0 else 0
    
    return ((recent_total - previous_total) / previous_total) * 100

# ----------------------- Sidebar: Configuración y Filtros -----------------------
st.sidebar.markdown("<div class='section-header'>🚀 CONFIGURACIÓN</div>", unsafe_allow_html=True)

orders_file = st.sidebar.file_uploader('📊 Archivo de Pedidos (Excel)', type=['xlsx','xls'])
shops_file = st.sidebar.file_uploader('🏪 Mapeo de Comercios (Excel/CSV)', type=['xlsx','xls','csv'])
vendors_file = st.sidebar.file_uploader('👤 Mapeo de Vendedores (Excel/CSV)', type=['xlsx','xls','csv'])

if orders_file is None:
    st.markdown("""
    <div style='text-align: center; padding: 50px;'>
        <h1>📊 Dashboard CEO - Análisis de Pedidos</h1>
        <h3>Sube el archivo de pedidos para comenzar el análisis</h3>
        <p>Este dashboard te proporcionará insights completos sobre:</p>
        <ul style='text-align: left; max-width: 500px; margin: 0 auto;'>
            <li>🎯 KPIs ejecutivos y métricas clave</li>
            <li>📈 Rankings de comercios y análisis de rendimiento</li>
            <li>⏰ Análisis temporal y tendencias</li>
            <li>👥 Performance por vendedores y ciudades</li>
            <li>🚨 Alertas y comercios en riesgo</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Cargar datos
try:
    df_orders_raw = load_excel(orders_file)
except Exception as e:
    st.error(f'❌ Error cargando pedidos: {e}')
    st.stop()

df_shops = None
if shops_file is not None:
    try:
        if str(shops_file.name).lower().endswith('.csv'):
            df_shops = pd.read_csv(shops_file)
        else:
            df_shops = load_excel(shops_file)
    except Exception as e:
        st.warning(f'⚠️ No se pudo cargar comercios: {e}')

df_vendors = None
if vendors_file is not None:
    try:
        if str(vendors_file.name).lower().endswith('.csv'):
            df_vendors = pd.read_csv(vendors_file)
        else:
            df_vendors = load_excel(vendors_file)
    except Exception as e:
        st.warning(f'⚠️ No se pudo cargar vendedores: {e}')

# Preprocesar datos
df_orders = preprocess_orders(df_orders_raw)

# Merge con comercios
if df_shops is not None:
    df = merge_comercios(df_orders, df_shops)
else:
    df = df_orders.copy()
    if 'COMPROBA' in df.columns:
        df['NOMBRE_COMERCIO'] = df['COMPROBA']

# Merge con vendedores
if df_vendors is not None:
    df = merge_vendedores(df, df_vendors)
else:
    if 'VEND' in df.columns:
        df['NOMBRE_VENDEDOR'] = df['VEND']

st.sidebar.markdown("<div class='section-header'>🎯 FILTROS GLOBALES</div>", unsafe_allow_html=True)

# Filtros mejorados - Manejo seguro de fechas
if 'FECHA_DATE' in df.columns and not df['FECHA_DATE'].isna().all():
    # Filtrar valores no nulos antes de calcular min/max
    fechas_validas = df['FECHA_DATE'].dropna()
    if not fechas_validas.empty:
        min_date = fechas_validas.min()
        max_date = fechas_validas.max()
    else:
        min_date = datetime.today().date()
        max_date = datetime.today().date()
else:
    min_date = datetime.today().date()
    max_date = datetime.today().date()
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input('📅 Desde', value=min_date)
with col2:
    end_date = st.date_input('📅 Hasta', value=max_date)

# Filtros adicionales
cities = df['COS'].dropna().unique().tolist() if 'COS' in df.columns else []
city_sel = st.sidebar.multiselect('🏙️ Ciudades', options=cities)

comercios = df['NOMBRE_COMERCIO'].dropna().unique().tolist()
comercio_sel = st.sidebar.multiselect('🏪 Comercios específicos', options=comercios)

vendedores = df['NOMBRE_VENDEDOR'].dropna().unique().tolist() if 'NOMBRE_VENDEDOR' in df.columns else []
vend_sel = st.sidebar.multiselect('👤 Vendedores', options=vendedores)

# Filtro por rango de ventas
if 'VAL.PEDIDO' in df.columns:
    min_val, max_val = float(df['VAL.PEDIDO'].min()), float(df['VAL.PEDIDO'].max())
    val_range = st.sidebar.slider('💰 Rango de valor pedido', min_val, max_val, (min_val, max_val))
    
# Aplicar filtros - Mejorado para manejar fechas nulas
mask = pd.Series(True, index=df.index)

if start_date and end_date and 'FECHA_DATE' in df.columns:
    # Solo aplicar filtro de fechas a registros que tienen fecha válida
    mask_fechas = df['FECHA_DATE'].notna()
    mask_rango = (df['FECHA_DATE'] >= start_date) & (df['FECHA_DATE'] <= end_date)
    mask &= (~mask_fechas) | (mask_fechas & mask_rango)

if city_sel and 'COS' in df.columns:
    if 'SCOS' in df.columns:
        mask &= df['COS'].isin(city_sel) | df['SCOS'].isin(city_sel)
    else:
        mask &= df['COS'].isin(city_sel)

if comercio_sel:
    mask &= df['NOMBRE_COMERCIO'].isin(comercio_sel)

if vend_sel and 'NOMBRE_VENDEDOR' in df.columns:
    mask &= df['NOMBRE_VENDEDOR'].isin(vend_sel)

if 'VAL.PEDIDO' in df.columns:
    mask &= (df['VAL.PEDIDO'] >= val_range[0]) & (df['VAL.PEDIDO'] <= val_range[1])

# Aplicar filtros
mask = pd.Series(True, index=df.index)
if start_date and end_date:
    mask &= (df['FECHA_DATE'] >= start_date) & (df['FECHA_DATE'] <= end_date)
if city_sel:
    mask &= df['COS'].isin(city_sel) | df['SCOS'].isin(city_sel)
if comercio_sel:
    mask &= df['NOMBRE_COMERCIO'].isin(comercio_sel)
if vend_sel:
    mask &= df['VEND'].isin(vend_sel)
if 'VAL.PEDIDO' in df.columns:
    mask &= (df['VAL.PEDIDO'] >= val_range[0]) & (df['VAL.PEDIDO'] <= val_range[1])

df_filtered = df[mask].copy()

# ----------------------- EXECUTIVE DASHBOARD -----------------------
st.markdown("<h1 style='text-align: center; color: #2E4057;'>📊 DASHBOARD CEO - ANÁLISIS DE PEDIDOS</h1>", unsafe_allow_html=True)

# ----------------------- KPIs Ejecutivos Avanzados -----------------------
st.markdown("<div class='section-header'>📈 KPIS EJECUTIVOS</div>", unsafe_allow_html=True)

kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

# Calcular KPIs
total_pedidos = df_filtered['VAL.PEDIDO'].sum() if 'VAL.PEDIDO' in df_filtered.columns else 0
total_entregado = df_filtered['VAL.ENTREGAD'].sum() if 'VAL.ENTREGAD' in df_filtered.columns else 0
valor_pendiente = total_pedidos - total_entregado
comercios_activos = df_filtered['NOMBRE_COMERCIO'].nunique() if len(df_filtered) > 0 else 0
eficiencia_promedio = df_filtered['EFICIENCIA_ENTREGA'].mean() * 100 if 'EFICIENCIA_ENTREGA' in df_filtered.columns else 0

# Calcular tasas de crecimiento
growth_rate = calculate_growth_rate(df_filtered)

with kpi_col1:
    delta_color = "normal" if growth_rate >= 0 else "inverse"
    st.metric("💰 Total Pedidos", f"${total_pedidos:,.0f}", 
              f"{growth_rate:+.1f}% vs mes anterior", delta_color=delta_color)

with kpi_col2:
    efficiency_delta = f"{eficiencia_promedio:.1f}%"
    st.metric("🚚 Total Entregado", f"${total_entregado:,.0f}", efficiency_delta)

with kpi_col3:
    pending_pct = (valor_pendiente/total_pedidos)*100 if total_pedidos > 0 else 0
    st.metric("⏳ Valor Pendiente", f"${valor_pendiente:,.0f}", f"{pending_pct:.1f}% del total")

with kpi_col4:
    avg_per_commerce = total_pedidos/comercios_activos if comercios_activos > 0 else 0
    st.metric("🏪 Comercios Activos", f"{comercios_activos:,}", f"Prom: ${avg_per_commerce:,.0f}")

with kpi_col5:
    st.metric("📊 Eficiencia Entrega", f"{eficiencia_promedio:.1f}%", 
              "🎯 Meta: 95%" if eficiencia_promedio < 95 else "✅ Excelente")

# ----------------------- Análisis de Comercios - Sección Principal -----------------------
st.markdown("<div class='section-header'>🏪 ANÁLISIS DE COMERCIOS</div>", unsafe_allow_html=True)

if len(df_filtered) == 0:
    st.warning("⚠️ No hay datos disponibles con los filtros actuales.")
    st.info("💡 Ajusta los filtros de fecha, ciudad, comercio o vendedor para ver los datos.")
    st.stop()  # Detiene la ejecución del resto del dashboard

# Preparar datos agregados por comercio
agg_comercios = df_filtered.groupby('NOMBRE_COMERCIO').agg({
    'VAL.PEDIDO': 'sum',
    'VAL.ENTREGAD': 'sum',
    'CANT.PEDIDA': 'sum',
    'CANT.ENTREGA': 'sum',
    'CANT PEND': 'sum',
    'FECHA_DATE': ['min', 'max', 'count'],
    'EFICIENCIA_ENTREGA': 'mean',
    'NUMERO': 'nunique'
}).round(2)

# Agrega validación después de crear agg_comercios:
if len(agg_comercios) == 0:
    st.error("❌ No se encontraron comercios con los filtros aplicados.")
    st.info("💡 Sugerencias:")
    st.info("- Amplía el rango de fechas")
    st.info("- Quita filtros de ciudad o vendedor")
    st.info("- Verifica que los datos del archivo coincidan con los filtros")
    st.stop()

# Aplanar nombres de columnas
agg_comercios.columns = ['VAL_PEDIDO', 'VAL_ENTREGADO', 'CANT_PEDIDA', 'CANT_ENTREGADA', 
                        'CANT_PENDIENTE', 'FECHA_MIN', 'FECHA_MAX', 'DIAS_ACTIVO', 
                        'EFICIENCIA', 'PEDIDOS_UNICOS']
agg_comercios.reset_index(inplace=True)

# Calcular métricas adicionales
agg_comercios['VALOR_PENDIENTE'] = agg_comercios['VAL_PEDIDO'] - agg_comercios['VAL_ENTREGADO']
agg_comercios['TICKET_PROMEDIO'] = agg_comercios['VAL_PEDIDO'] / agg_comercios['PEDIDOS_UNICOS'].replace(0, 1)
agg_comercios['FRECUENCIA_COMPRA'] = agg_comercios['DIAS_ACTIVO'] / agg_comercios['PEDIDOS_UNICOS'].replace(0, 1)

# Nuevas métricas para cantidades
agg_comercios['PROP_PENDIENTE'] = np.where(
    agg_comercios['VAL_PEDIDO'] > 0,
    agg_comercios['VALOR_PENDIENTE'] / agg_comercios['VAL_PEDIDO'],
    0
)

# Nueva clasificación por cantidades
agg_comercios['CLASIFICACION'] = pd.cut(
    agg_comercios['PROP_PENDIENTE'],
    bins=[-0.01, 0.33, 0.66, 1],
    labels=['🟢 Alto', '🟡 Medio', '🔴 Bajo']
)

# NUEVAS MÉTRICAS PARA CANTIDADES
agg_comercios['PROP_CANT_PENDIENTE'] = np.where(
    agg_comercios['CANT_PEDIDA'] > 0,
    agg_comercios['CANT_PENDIENTE'] / agg_comercios['CANT_PEDIDA'],
    0
)

agg_comercios['EFICIENCIA_CANTIDAD'] = np.where(
    agg_comercios['CANT_PEDIDA'] > 0,
    agg_comercios['CANT_ENTREGADA'] / agg_comercios['CANT_PEDIDA'],
    0
)

# Nueva clasificación por cantidades
agg_comercios['CLASIFICACION_CANTIDAD'] = pd.cut(
    agg_comercios['PROP_CANT_PENDIENTE'],
    bins=[-0.01, 0.20, 0.50, 1],
    labels=['🟢 Excelente', '🟡 Regular', '🔴 Crítico']
)

# Análisis visual principal
main_col1, main_col2 = st.columns([2, 1])

with main_col1:
    # Gráfico principal: Top comercios
    top_n = st.slider('🎯 Top N comercios a mostrar', 10, 50, 20)
    top_comercios = agg_comercios.nlargest(top_n, 'VAL_PEDIDO')
    
    fig_main = px.bar(top_comercios, 
                      x='VAL_PEDIDO', 
                      y='NOMBRE_COMERCIO', 
                      orientation='h',
                      color='EFICIENCIA',
                      color_continuous_scale='RdYlGn',
                      title=f'🏆 Top {top_n} Comercios por Ventas',
                      labels={'VAL_PEDIDO': 'Valor Total Pedidos', 
                             'EFICIENCIA': 'Eficiencia %'})
    fig_main.update_layout(height=600, showlegend=True)
    st.plotly_chart(fig_main, use_container_width=True)

with main_col2:
    # Distribución por clasificación - CORREGIDO
    class_dist = agg_comercios['CLASIFICACION'].value_counts()
    fig_pie = px.pie(values=class_dist.values, 
                     names=class_dist.index,
                     title='📊 Distribución por Rendimiento',
                     color_discrete_map={
                         '🟢 Alto': 'green',
                         '🟡 Medio': 'gold', 
                         '🔴 Bajo': 'red'
                     })
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # Métricas de distribución
    st.markdown("**📈 Estadísticas Clave:**")
    if len(top_comercios) > 0:
        st.write(f"🥇 Comercio Top: {top_comercios.iloc[0]['NOMBRE_COMERCIO']}")
        st.write(f"💰 Ventas Top: ${top_comercios.iloc[0]['VAL_PEDIDO']:,.0f}")
        st.write(f"🎯 Ticket Prom. Top: ${top_comercios.iloc[0]['TICKET_PROMEDIO']:,.0f}")
        st.write(f"📊 Concentración Top 10: {(top_comercios.head(10)['VAL_PEDIDO'].sum()/agg_comercios['VAL_PEDIDO'].sum())*100:.1f}%")

# ==========================
# ANÁLISIS MEJORADO DE CANTIDADES PENDIENTES
# ==========================
st.markdown("<div class='section-header'>📦 ANÁLISIS DE CANTIDADES PENDIENTES</div>", unsafe_allow_html=True)

# KPIs de cantidades
kpi_cant_col1, kpi_cant_col2, kpi_cant_col3, kpi_cant_col4 = st.columns(4)

# Calcular KPIs de cantidades
total_cant_pedida = agg_comercios['CANT_PEDIDA'].sum()
total_cant_pendiente = agg_comercios['CANT_PENDIENTE'].sum()
total_cant_entregada = agg_comercios['CANT_ENTREGADA'].sum()
eficiencia_cantidad_global = (total_cant_entregada / total_cant_pedida * 100) if total_cant_pedida > 0 else 0

# Comercio con más pendientes
if len(agg_comercios) > 0:
    max_pend_idx = agg_comercios['CANT_PENDIENTE'].idxmax()
    comercio_max_pend = agg_comercios.loc[max_pend_idx, 'NOMBRE_COMERCIO']
    cant_max_pend = agg_comercios.loc[max_pend_idx, 'CANT_PENDIENTE']
    
    # Comercios críticos (más del 50% pendiente)
    comercios_criticos = len(agg_comercios[agg_comercios['PROP_CANT_PENDIENTE'] > 0.5])
else:
    comercio_max_pend = "N/A"
    cant_max_pend = 0
    comercios_criticos = 0

with kpi_cant_col1:
    st.metric("📦 Total Unidades Pedidas", f"{total_cant_pedida:,.0f}")

with kpi_cant_col2:
    prop_pend_global = (total_cant_pendiente / total_cant_pedida * 100) if total_cant_pedida > 0 else 0
    st.metric("⏳ Total Unidades Pendientes", f"{total_cant_pendiente:,.0f}", 
              f"{prop_pend_global:.1f}% del total")

with kpi_cant_col3:
    st.metric("🚚 Eficiencia de Cantidad", f"{eficiencia_cantidad_global:.1f}%")

with kpi_cant_col4:
    st.metric("🚨 Comercios Críticos", f"{comercios_criticos}", 
              f">50% pendiente")

# Comercio con más pendientes
if cant_max_pend > 0:
    st.info(f"🎯 **Comercio con más pendientes:** {comercio_max_pend} ({cant_max_pend:,.0f} unidades)")

# Análisis Pareto mejorado - CON VALIDACIÓN PARA EVITAR DIVISIÓN POR CERO
st.markdown("### 📊 Análisis Pareto - Regla 80/20")
pareto_col1, pareto_col2 = st.columns([3, 1])

with pareto_col1:
    # VALIDACIÓN CRÍTICA: Verificar que hay datos antes de proceder
    if len(agg_comercios) > 0:
        agg_comercios_sorted = agg_comercios.sort_values('VAL_PEDIDO', ascending=False)
        agg_comercios_sorted['ACUM_PERC'] = agg_comercios_sorted['VAL_PEDIDO'].cumsum() / agg_comercios_sorted['VAL_PEDIDO'].sum()
        
        # Encontrar el punto 80%
        comercios_80 = len(agg_comercios_sorted[agg_comercios_sorted['ACUM_PERC'] <= 0.8])
        
        fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig_pareto.add_trace(
            go.Bar(x=list(range(len(agg_comercios_sorted))), 
                   y=agg_comercios_sorted['VAL_PEDIDO'],
                   name="Ventas por Comercio",
                   marker_color='lightblue'),
            secondary_y=False)
        
        fig_pareto.add_trace(
            go.Scatter(x=list(range(len(agg_comercios_sorted))), 
                      y=agg_comercios_sorted['ACUM_PERC']*100,
                      mode='lines+markers',
                      name="% Acumulado",
                      line=dict(color='red', width=2)),
            secondary_y=True)
        
        # Línea del 80%
        fig_pareto.add_hline(y=80, line_dash="dash", line_color="orange", 
                            annotation_text="80%", secondary_y=True)
        fig_pareto.add_vline(x=comercios_80, line_dash="dash", line_color="orange",
                            annotation_text=f"{comercios_80} comercios")
        
        fig_pareto.update_layout(title="🎯 Análisis Pareto: Concentración de Ventas")
        fig_pareto.update_yaxes(title_text="Valor Ventas", secondary_y=False)
        fig_pareto.update_yaxes(title_text="% Acumulado", secondary_y=True)
        
        st.plotly_chart(fig_pareto, use_container_width=True)
    else:
        # Mostrar mensaje cuando no hay datos
        st.warning("⚠️ No hay datos disponibles para el análisis Pareto con los filtros actuales.")
        st.info("💡 Intenta ajustar los filtros para obtener más datos.")

with pareto_col2:
    st.markdown("**🎯 Insights Pareto:**")
    
    # VALIDACIÓN CRÍTICA: Solo mostrar insights si hay datos
    if len(agg_comercios) > 0:
        st.info(f"📊 {comercios_80} comercios ({comercios_80/len(agg_comercios)*100:.1f}%) generan el 80% de las ventas")
        
        pareto_20_pct = len(agg_comercios) * 0.2
        if comercios_80 <= pareto_20_pct:
            st.success("✅ Se cumple la regla 80/20")
        else:
            st.warning("⚠️ Ventas más distribuidas que la regla típica")
    else:
        st.warning("📊 Sin datos suficientes para análisis Pareto")
        st.info("Ajusta los filtros para ver más comercios")

# ----------------------- Estado Diario por Comercio -----------------------
st.markdown("<div class='section-header'>📅 ANÁLISIS TEMPORAL POR COMERCIO</div>", unsafe_allow_html=True)

# Selector de comercio mejorado
comercio_selected = st.selectbox('🏪 Selecciona un comercio para análisis detallado:', 
                                options=agg_comercios.sort_values('VAL_PEDIDO', ascending=False)['NOMBRE_COMERCIO'].tolist(),
                                index=0)

if comercio_selected:
    comercio_data = df_filtered[df_filtered['NOMBRE_COMERCIO'] == comercio_selected]
    
    if not comercio_data.empty:
        temporal_col1, temporal_col2 = st.columns([2, 1])
        
        with temporal_col1:
            # Serie temporal principal
            ts_daily = comercio_data.groupby('FECHA_DATE').agg({
                'VAL.PEDIDO': 'sum',
                'VAL.ENTREGAD': 'sum',
                'CANT PEND': 'sum'
            }).reset_index()
            
            fig_temporal = go.Figure()
            
            fig_temporal.add_trace(go.Scatter(
                x=ts_daily['FECHA_DATE'],
                y=ts_daily['VAL.PEDIDO'],
                mode='lines+markers',
                name='💰 Valor Pedido',
                line=dict(color='blue', width=2)))
            
            fig_temporal.add_trace(go.Scatter(
                x=ts_daily['FECHA_DATE'],
                y=ts_daily['VAL.ENTREGAD'],
                mode='lines+markers',
                name='🚚 Valor Entregado',
                line=dict(color='green', width=2)))
            
            fig_temporal.update_layout(
                title=f'📈 Evolución Temporal: {comercio_selected}',
                xaxis_title='Fecha',
                yaxis_title='Valor ($)',
                hovermode='x unified')
            
            st.plotly_chart(fig_temporal, use_container_width=True)
        
        with temporal_col2:
            # Estadísticas del comercio seleccionado
            comercio_stats = agg_comercios[agg_comercios['NOMBRE_COMERCIO'] == comercio_selected].iloc[0]
            
            st.markdown(f"**📊 Estadísticas - {comercio_selected}:**")
            st.metric("💰 Total Ventas", f"${comercio_stats['VAL_PEDIDO']:,.0f}")
            st.metric("🚚 Total Entregado", f"${comercio_stats['VAL_ENTREGADO']:,.0f}")
            st.metric("📋 Pedidos Únicos", f"{int(comercio_stats['PEDIDOS_UNICOS'])}")
            st.metric("🎯 Ticket Promedio", f"${comercio_stats['TICKET_PROMEDIO']:,.0f}")
            st.metric("⚡ Eficiencia", f"{comercio_stats['EFICIENCIA']*100:.1f}%")
            
            # Ranking del comercio
            ranking = agg_comercios.sort_values('VAL_PEDIDO', ascending=False).reset_index(drop=True)
            posicion = ranking[ranking['NOMBRE_COMERCIO'] == comercio_selected].index[0] + 1
            st.info(f"🏆 Ranking: #{posicion} de {len(agg_comercios)} comercios")
        
        # Análisis por día de la semana
        if 'DIA_SEMANA' in comercio_data.columns:
            st.markdown("### 📅 Análisis por Día de la Semana")
            
            dow_analysis = comercio_data.groupby('DIA_SEMANA')['VAL.PEDIDO'].sum().reset_index()
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            dow_analysis['DIA_SEMANA'] = pd.Categorical(dow_analysis['DIA_SEMANA'], categories=days_order, ordered=True)
            dow_analysis = dow_analysis.sort_values('DIA_SEMANA')
            
            fig_dow = px.bar(dow_analysis, x='DIA_SEMANA', y='VAL.PEDIDO',
                           title=f'💼 Ventas por Día de la Semana - {comercio_selected}')
            st.plotly_chart(fig_dow, use_container_width=True)

# ----------------------- Análisis por Vendedores y Plataformas -----------------------
st.markdown("<div class='section-header'>👥 ANÁLISIS POR VENDEDORES Y PLATAFORMAS</div>", unsafe_allow_html=True)

if 'VEND' in df_filtered.columns:
    # Análisis de vendedores
    vendedor_col1, vendedor_col2 = st.columns([2, 1])
    
    with vendedor_col1:
        # Performance por vendedor
        vend_performance = df_filtered.groupby('NOMBRE_VENDEDOR').agg({
            'VAL.PEDIDO': 'sum',
            'VAL.ENTREGAD': 'sum',
            'NOMBRE_COMERCIO': 'nunique',
            'NUMERO': 'nunique',
            'EFICIENCIA_ENTREGA': 'mean'
        }).round(2)
        
        vend_performance.columns = ['VENTAS_TOTAL', 'ENTREGADO_TOTAL', 'COMERCIOS_ATENDIDOS', 
                                   'PEDIDOS_UNICOS', 'EFICIENCIA_PROM']
        vend_performance = vend_performance.sort_values('VENTAS_TOTAL', ascending=False)
        vend_performance.reset_index(inplace=True)
        
        fig_vendors = px.bar(vend_performance.head(15), 
                           x='VENTAS_TOTAL', 
                           y='NOMBRE_VENDEDOR',
                           orientation='h',
                           color='EFICIENCIA_PROM',
                           color_continuous_scale='RdYlGn',
                           title='🏆 Top 15 Vendedores por Ventas')
        st.plotly_chart(fig_vendors, use_container_width=True)
    
    with vendedor_col2:
        st.markdown("**🎯 Top 5 Vendedores:**")
        for idx, row in vend_performance.head(5).iterrows():
            st.write(f"**{idx+1}. {row['NOMBRE_VENDEDOR']}**")
            st.write(f"💰 Ventas: ${row['VENTAS_TOTAL']:,.0f}")
            st.write(f"🏪 Comercios: {int(row['COMERCIOS_ATENDIDOS'])}")
            st.write(f"⚡ Eficiencia: {row['EFICIENCIA_PROM']*100:.1f}%")
            st.write("---")
        
# ----------------------- Alertas y Monitoreo Ejecutivo -----------------------
st.markdown("<div class='section-header'>🚨 ALERTAS Y MONITOREO EJECUTIVO</div>", unsafe_allow_html=True)

# Identificar comercios en riesgo y oportunidades
alertas_col1, alertas_col2, alertas_col3 = st.columns(3)

with alertas_col1:
    st.markdown("### 🔴 COMERCIOS EN RIESGO")
    
    # Comercios con baja eficiencia de entrega
    comercios_riesgo = agg_comercios[
        (agg_comercios['EFICIENCIA'] < 0.7) & 
        (agg_comercios['VAL_PEDIDO'] > agg_comercios['VAL_PEDIDO'].median())
    ].sort_values('EFICIENCIA')
    
    for _, comercio in comercios_riesgo.head(5).iterrows():
        st.markdown(f"""
        <div class='alert-high'>
            <strong>🚨 {comercio['NOMBRE_COMERCIO']}</strong><br>
            Eficiencia: {comercio['EFICIENCIA']*100:.1f}%<br>
            Pendiente: ${comercio['VALOR_PENDIENTE']:,.0f}
        </div>
        """, unsafe_allow_html=True)

with alertas_col2:
    st.markdown("### 🟡 ATENCIÓN REQUERIDA")
    
    # Comercios con alta pendencia pero buenas ventas
    comercios_atencion = agg_comercios[
        (agg_comercios['VALOR_PENDIENTE'] > agg_comercios['VALOR_PENDIENTE'].quantile(0.75)) &
        (agg_comercios['VAL_PEDIDO'] > agg_comercios['VAL_PEDIDO'].quantile(0.5))
    ].sort_values('VALOR_PENDIENTE', ascending=False)
    
    for _, comercio in comercios_atencion.head(5).iterrows():
        st.markdown(f"""
        <div class='alert-medium'>
            <strong>⚠️ {comercio['NOMBRE_COMERCIO']}</strong><br>
            Pendiente: ${comercio['VALOR_PENDIENTE']:,.0f}<br>
            Ventas: ${comercio['VAL_PEDIDO']:,.0f}
        </div>
        """, unsafe_allow_html=True)

with alertas_col3:
    st.markdown("### 🟢 OPORTUNIDADES")
    
    # Comercios con alta eficiencia y potencial de crecimiento
    comercios_oportunidad = agg_comercios[
        (agg_comercios['EFICIENCIA'] > 0.9) & 
        (agg_comercios['FRECUENCIA_COMPRA'] < agg_comercios['FRECUENCIA_COMPRA'].median())
    ].sort_values('TICKET_PROMEDIO', ascending=False)
    
    for _, comercio in comercios_oportunidad.head(5).iterrows():
        st.markdown(f"""
        <div class='alert-low'>
            <strong>🌟 {comercio['NOMBRE_COMERCIO']}</strong><br>
            Eficiencia: {comercio['EFICIENCIA']*100:.1f}%<br>
            Ticket: ${comercio['TICKET_PROMEDIO']:,.0f}
        </div>
        """, unsafe_allow_html=True)

# ----------------------- Análisis Geográfico -----------------------
st.markdown("<div class='section-header'>🗺️ ANÁLISIS GEOGRÁFICO</div>", unsafe_allow_html=True)

if 'COS' in df_filtered.columns:
    geo_col1, geo_col2 = st.columns([2, 1])
    
    with geo_col1:
        # Análisis por ciudades
        city_analysis = df_filtered.groupby('COS').agg({
            'VAL.PEDIDO': 'sum',
            'VAL.ENTREGAD': 'sum',
            'NOMBRE_COMERCIO': 'nunique',
            'VEND': 'nunique',
            'EFICIENCIA_ENTREGA': 'mean'
        }).round(2)
        
        city_analysis.columns = ['VENTAS_TOTAL', 'ENTREGADO_TOTAL', 'COMERCIOS', 'VENDEDORES', 'EFICIENCIA']
        city_analysis.reset_index(inplace=True)
        city_analysis = city_analysis.sort_values('VENTAS_TOTAL', ascending=False)
        
        fig_cities = px.treemap(city_analysis,
                               path=['COS'],
                               values='VENTAS_TOTAL',
                               color='EFICIENCIA',
                               color_continuous_scale='RdYlGn',
                               title='🏙️ Ventas por Ciudad (Tamaño) y Eficiencia (Color)')
        st.plotly_chart(fig_cities, use_container_width=True)
    
    with geo_col2:
        st.markdown("**🏆 Ranking de Ciudades:**")
        st.dataframe(
            city_analysis.head(10)[['COS', 'VENTAS_TOTAL', 'COMERCIOS', 'EFICIENCIA']]
            .style.format({'VENTAS_TOTAL': '${:,.0f}', 'EFICIENCIA': '{:.1%}'})
        )

# ----------------------- Análisis de Tendencias y Forecasting -----------------------
st.markdown("<div class='section-header'>📈 ANÁLISIS DE TENDENCIAS</div>", unsafe_allow_html=True)

if 'FECHA_DATE' in df_filtered.columns:
    trend_col1, trend_col2 = st.columns([3, 1])
    
    with trend_col1:
        # Tendencia semanal
        df_filtered['SEMANA_YEAR'] = df_filtered['FECHA'].dt.strftime('%Y-W%U')
        weekly_trend = df_filtered.groupby('SEMANA_YEAR').agg({
            'VAL.PEDIDO': 'sum',
            'VAL.ENTREGAD': 'sum',
            'NOMBRE_COMERCIO': 'nunique'
        }).reset_index()
        
        # Calcular media móvil
        weekly_trend['MA_PEDIDOS'] = weekly_trend['VAL.PEDIDO'].rolling(window=4).mean()
        weekly_trend['MA_ENTREGADOS'] = weekly_trend['VAL.ENTREGAD'].rolling(window=4).mean()
        
        fig_trend = go.Figure()
        
        fig_trend.add_trace(go.Scatter(
            x=weekly_trend['SEMANA_YEAR'],
            y=weekly_trend['VAL.PEDIDO'],
            mode='lines+markers',
            name='📊 Ventas Semanales',
            line=dict(color='blue', width=1),
            opacity=0.6))
        
        fig_trend.add_trace(go.Scatter(
            x=weekly_trend['SEMANA_YEAR'],
            y=weekly_trend['MA_PEDIDOS'],
            mode='lines',
            name='📈 Tendencia (MA 4 sem)',
            line=dict(color='red', width=3)))
        
        fig_trend.update_layout(
            title='📊 Tendencia de Ventas Semanales',
            xaxis_title='Semana',
            yaxis_title='Valor ($)',
            xaxis=dict(tickangle=45))
        
        st.plotly_chart(fig_trend, use_container_width=True)
    
    with trend_col2:
        # Estadísticas de tendencia
        if len(weekly_trend) > 1:
            last_4_weeks = weekly_trend.tail(4)['VAL.PEDIDO'].mean()
            prev_4_weeks = weekly_trend.tail(8).head(4)['VAL.PEDIDO'].mean()
            trend_change = ((last_4_weeks - prev_4_weeks) / prev_4_weeks * 100) if prev_4_weeks > 0 else 0
            
            st.markdown("**📊 Indicadores de Tendencia:**")
            st.metric("📈 Cambio Mensual", f"{trend_change:+.1f}%")
            st.metric("💰 Prom. Últimas 4 sem", f"${last_4_weeks:,.0f}")
            st.metric("📅 Prom. 4 sem anteriores", f"${prev_4_weeks:,.0f}")
            
            # Proyección simple
            if trend_change > 0:
                st.success("✅ Tendencia positiva")
                projection = last_4_weeks * (1 + trend_change/100)
                st.info(f"🔮 Proyección próxima semana: ${projection:,.0f}")
            else:
                st.warning("⚠️ Tendencia negativa")

# ----------------------- Cuadro de Mando Ejecutivo -----------------------
st.markdown("<div class='section-header'>📋 CUADRO DE MANDO EJECUTIVO</div>", unsafe_allow_html=True)

# Resumen ejecutivo en columnas
exec_col1, exec_col2, exec_col3, exec_col4 = st.columns(4)

with exec_col1:
    st.markdown("**🎯 OBJETIVOS DE NEGOCIO**")
    
    # Calcular cumplimiento de objetivos (asumir metas)
    meta_ventas_mensual = total_pedidos * 1.1  # Meta 10% superior     # Falta ver ese dato real
    cumplimiento = (total_pedidos / meta_ventas_mensual) * 100
    
    #st.metric("🎯 Cumplimiento Meta", f"{cumplimiento:.1f}%")
    st.metric("🎯 Cumplimiento Meta", f"Falta estimar")

with exec_col2:
    st.markdown("**⚡ EFICIENCIA OPERATIVA**")
    
    comercios_eficientes = len(agg_comercios[agg_comercios['EFICIENCIA'] > 0.9])
    pct_eficientes = (comercios_eficientes / len(agg_comercios)) * 100
    
    st.metric("✅ Comercios Eficientes", f"{comercios_eficientes}", f"{pct_eficientes:.1f}% del total")
    
    tiempo_prom_entrega = "Pendiente por asignar"  # Asumir métrica
    st.metric("🚚 Tiempo Prom. Entrega", tiempo_prom_entrega)

with exec_col3:
    st.markdown("**💰 RENTABILIDAD**")
    
    margen_estimado = 0.25  # Asumir 25% margen     # Suposición, hay que sacar el valor real
    utilidad_estimada = total_entregado * margen_estimado
    
    #st.metric("💵 Utilidad Estimada", f"${utilidad_estimada:,.0f}")
    #st.metric("📊 Margen Estimado", f"{margen_estimado:.1%}")
    st.metric("💵 Utilidad Estimada", f"Falta estimar")         # Asignar un margen estimado
    st.metric("📊 Margen Estimado", f"Falta estimar")

with exec_col4:
    st.markdown("**🚀 CRECIMIENTO**")
    
    comercios_nuevos = len(agg_comercios[agg_comercios['DIAS_ACTIVO'] <= 30])  # Últimos 30 días
    
    st.metric("🆕 Comercios Nuevos", f"{comercios_nuevos}")
    st.metric("📈 Tasa Crecimiento", f"{growth_rate:+.1f}%")

# ----------------------- Tabla Resumen Ejecutiva -----------------------
st.markdown("### 📊 TABLA RESUMEN EJECUTIVA - TOP 20 COMERCIOS")

# Preparar tabla ejecutiva
tabla_ejecutiva = agg_comercios.head(20)[['NOMBRE_COMERCIO', 'VAL_PEDIDO', 'VAL_ENTREGADO', 
                                         'VALOR_PENDIENTE', 'EFICIENCIA', 'TICKET_PROMEDIO', 
                                         'PEDIDOS_UNICOS', 'CLASIFICACION']].copy()

# Formatear para presentación ejecutiva
st.dataframe(
    tabla_ejecutiva.style.format({
        'VAL_PEDIDO': '${:,.0f}',
        'VAL_ENTREGADO': '${:,.0f}',
        'VALOR_PENDIENTE': '${:,.0f}',
        'EFICIENCIA': '{:.1%}',
        'TICKET_PROMEDIO': '${:,.0f}',
        'PEDIDOS_UNICOS': '{:.0f}'
    }).background_gradient(subset=['VAL_PEDIDO'], cmap='RdYlGn'),
    use_container_width=True
)

# ----------------------- Exportaciones y Reportes -----------------------
st.markdown("<div class='section-header'>📤 EXPORTACIONES Y REPORTES</div>", unsafe_allow_html=True)

export_col1, export_col2, export_col3 = st.columns(3)

with export_col1:
    if st.button('📊 Exportar Resumen Ejecutivo'):
        # Preparar datos para export
        export_data = agg_comercios[['NOMBRE_COMERCIO', 'VAL_PEDIDO', 'VAL_ENTREGADO', 
                                   'EFICIENCIA', 'TICKET_PROMEDIO', 'CLASIFICACION']]
        csv_data = export_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 Descargar CSV Ejecutivo",
            data=csv_data,
            file_name=f"resumen_ejecutivo_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv'
        )

with export_col2:
    if st.button('👥 Exportar Análisis Vendedores'):
        if 'VEND' in df_filtered.columns:
            csv_vendedores = vend_performance.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="💾 Descargar Vendedores CSV",
                data=csv_vendedores,
                file_name=f"analisis_vendedores_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv'
            )

with export_col3:
    if st.button('🚨 Exportar Alertas'):
        alertas_data = pd.concat([
            comercios_riesgo[['NOMBRE_COMERCIO', 'EFICIENCIA', 'VALOR_PENDIENTE']].assign(TIPO='RIESGO'),
            comercios_atencion[['NOMBRE_COMERCIO', 'EFICIENCIA', 'VALOR_PENDIENTE']].assign(TIPO='ATENCION'),
            comercios_oportunidad[['NOMBRE_COMERCIO', 'EFICIENCIA', 'VALOR_PENDIENTE']].assign(TIPO='OPORTUNIDAD')
        ])
        csv_alertas = alertas_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 Descargar Alertas CSV",
            data=csv_alertas,
            file_name=f"alertas_comercios_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv'
        )

# ==========================
# RESUMEN EJECUTIVO MEJORADO (REEMPLAZAR EL EXISTENTE)
# ==========================
st.markdown("### 📋 Resumen Ejecutivo de Comercios")

# Seleccionar columnas relevantes para el resumen
columnas_resumen = [
    'NOMBRE_COMERCIO', 'VAL_PEDIDO', 'VALOR_PENDIENTE', 'VAL_ENTREGADO',
    'CANT_PEDIDA', 'CANT_PENDIENTE', 'CANT_ENTREGADA', 'EFICIENCIA', 
    'EFICIENCIA_CANTIDAD', 'CLASIFICACION', 'CLASIFICACION_CANTIDAD'
]

tabla_resumen = agg_comercios[columnas_resumen].copy()

# Aplicar formato mejorado
styled_summary = tabla_resumen.style.format({
    'VAL_PEDIDO': "${:,.0f}",
    'VALOR_PENDIENTE': "${:,.0f}",
    'VAL_ENTREGADO': "${:,.0f}",
    'CANT_PEDIDA': "{:,.0f}",
    'CANT_PENDIENTE': "{:,.0f}",
    'CANT_ENTREGADA': "{:,.0f}",
    'EFICIENCIA': "{:.1%}",
    'EFICIENCIA_CANTIDAD': "{:.1%}"
}).background_gradient(
    subset=['VAL_PEDIDO'], cmap='YlGn'
).background_gradient(
    subset=['VALOR_PENDIENTE', 'CANT_PENDIENTE'], cmap='Reds'
).background_gradient(
    subset=['EFICIENCIA', 'EFICIENCIA_CANTIDAD'], cmap='RdYlGn'
)

st.dataframe(styled_summary, use_container_width=True)

# ==========================
# TABLA DE COMERCIOS CRÍTICOS
# ==========================
st.markdown("### 🚨 Comercios que Requieren Atención Inmediata")

comercios_criticos_detalle = agg_comercios[
    agg_comercios['PROP_CANT_PENDIENTE'] > 0.3  # Más del 30% pendiente
].sort_values('CANT_PENDIENTE', ascending=False)

if len(comercios_criticos_detalle) > 0:
    tabla_criticos = comercios_criticos_detalle[[
        'NOMBRE_COMERCIO', 'CANT_PENDIENTE', 'CANT_PEDIDA', 
        'PROP_CANT_PENDIENTE', 'VALOR_PENDIENTE', 'CLASIFICACION_CANTIDAD'
    ]].copy()
    
    st.dataframe(
        tabla_criticos.style.format({
            'CANT_PENDIENTE': "{:,.0f}",
            'CANT_PEDIDA': "{:,.0f}",
            'PROP_CANT_PENDIENTE': "{:.1%}",
            'VALOR_PENDIENTE': "${:,.0f}"
        }).background_gradient(subset=['PROP_CANT_PENDIENTE'], cmap='Reds'),
        use_container_width=True
    )
    
    # Estadísticas de comercios críticos
    st.error(f"⚠️ **{len(comercios_criticos_detalle)} comercios** requieren atención inmediata con más del 30% de cantidades pendientes")
    
    total_unidades_criticas = comercios_criticos_detalle['CANT_PENDIENTE'].sum()
    valor_critico = comercios_criticos_detalle['VALOR_PENDIENTE'].sum()
    
    critico_col1, critico_col2 = st.columns(2)
    with critico_col1:
        st.metric("📦 Unidades en Riesgo", f"{total_unidades_criticas:,.0f}")
    with critico_col2:
        st.metric("💰 Valor en Riesgo", f"${valor_critico:,.0f}")
        
else:
    st.success("✅ No hay comercios críticos en este momento")


st.success("✅ Dashboard cargado exitosamente. Todos los análisis están actualizados con los datos filtrados.")