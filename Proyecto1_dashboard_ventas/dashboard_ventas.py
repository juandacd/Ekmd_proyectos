# -*- coding: utf-8 -*-
import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==========================
# Config general
# ==========================
st.set_page_config(page_title="Dashboard Ejecutivo - Ekonomodo", layout="wide")

st.title("📊 Dashboard Ejecutivo de Ventas — Ekonomodo")
st.caption("Fuente: Auxiliar por número - Análisis transaccional completo")

# ==========================
# Parámetros de carga
# ==========================
st.sidebar.header("⚙️ Cargar Datos")

# Archivos principales de ventas
st.sidebar.subheader("📁 Archivos de Ventas")
file_2024 = st.sidebar.file_uploader("Ventas 2024 (Excel)", type=["xlsx", "xls"], key="2024")
file_2025 = st.sidebar.file_uploader("Ventas 2025 (Excel)", type=["xlsx", "xls"], key="2025")

# Archivos de catálogos
st.sidebar.markdown("---")
st.sidebar.subheader("📋 Catálogos (Opcional)")
st.sidebar.caption("Para filtrar por nombre en lugar de código")
comercios_file = st.sidebar.file_uploader("Catálogo Comercios (Excel/CSV)", type=["xlsx", "xls", "csv"], key="comercios")
st.sidebar.caption("Debe tener: Z (código) y Nombre")

vendedores_file = st.sidebar.file_uploader("Catálogo Vendedores (Excel/CSV)", type=["xlsx", "xls", "csv"], key="vendedores")
st.sidebar.caption("Debe tener: VENDEDOR (código) y NOMBRE")

# ==========================
# Funciones auxiliares
# ==========================
MONTH_ORDER = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
MONTH_MAP = {
    1: "ENE", 2: "FEB", 3: "MAR", 4: "ABR", 5: "MAY", 6: "JUN",
    7: "JUL", 8: "AGO", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DIC"
}

@st.cache_data(show_spinner=False)
def load_transactional_data(file_obj, year_label):
    """Carga datos transaccionales de ventas"""
    if file_obj is None:
        return pd.DataFrame()
    
    try:
        # Leer con header=None primero para inspeccionar
        df_raw = pd.read_excel(file_obj, header=None)
        
        # Buscar la fila de encabezados (que contenga palabras clave)
        header_row = None
        for i in range(min(10, len(df_raw))):  # Buscar en las primeras 10 filas
            row_values = [str(cell).strip().upper() for cell in df_raw.iloc[i] if pd.notna(cell)]
            row_str = ' '.join(row_values)
            
            # Buscar palabras clave
            if any(keyword in row_str for keyword in ['REFERENCIA', 'FECHA', 'COMPROBA', 'VALOR', 'CANTIDAD']):
                header_row = i
                break
        
        # Leer desde la fila de encabezados detectada
        if header_row is not None:
            df = pd.read_excel(file_obj, skiprows=header_row)
        else:
            df = pd.read_excel(file_obj)
        
        # Manejar columnas duplicadas agregando sufijos
        cols = pd.Series(df.columns)
        for dup in cols[cols.duplicated()].unique():
            dup_indices = [i for i, x in enumerate(cols) if x == dup]
            for i, idx in enumerate(dup_indices[1:], start=1):
                cols.iloc[idx] = f"{dup}_{i}"
        df.columns = cols
        
        # Normalizar nombres de columnas
        df.columns = [str(col).strip().upper() for col in df.columns]
        
        # Mapeo de columnas esperadas
        column_mapping = {}
        for col in df.columns:
            col_clean = col.upper().strip()
            if 'REFERENCIA' in col_clean:
                column_mapping[col] = 'REFERENCIA'
            elif 'DESCRIPCION' in col_clean or 'DESCRIP' in col_clean:
                column_mapping[col] = 'DESCRIPCION'
            elif 'COMPROBA' in col_clean:
                column_mapping[col] = 'COMPROBA'
            elif 'FECHA' in col_clean:
                column_mapping[col] = 'FECHA'
            elif 'VEND' in col_clean and 'VENDEDOR' not in col_clean:
                column_mapping[col] = 'VEND'
            elif 'VAL.ENTREGA' in col_clean or 'VAL ENTREGA' in col_clean or 'VALOR' in col_clean:
                if 'VALOR' not in column_mapping.values():
                    column_mapping[col] = 'VALOR'
            elif 'CANT.ENTREGA' in col_clean or 'CANT ENTREGA' in col_clean or 'CANTIDAD' in col_clean:
                if 'CANTIDAD' not in column_mapping.values():
                    column_mapping[col] = 'CANTIDAD'
        
        df = df.rename(columns=column_mapping)
        
        # Verificar columnas requeridas
        required_cols = ['REFERENCIA', 'FECHA', 'VALOR', 'CANTIDAD']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Faltan columnas requeridas en {year_label}: {missing_cols}")
            st.info(f"Columnas disponibles: {list(df.columns)}")
            return pd.DataFrame()
        
        # Convertir tipos de datos
        df['FECHA'] = pd.to_datetime(df['FECHA'], errors='coerce')
        df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce').fillna(0)
        df['CANTIDAD'] = pd.to_numeric(df['CANTIDAD'], errors='coerce').fillna(0)
        
        # Filtrar filas válidas
        df = df[df['FECHA'].notna() & (df['REFERENCIA'].notna())]
        
        # Extraer mes y año
        df['AÑO'] = df['FECHA'].dt.year
        df['MES_NUM'] = df['FECHA'].dt.month
        df['MES_ABBR'] = df['MES_NUM'].map(MONTH_MAP)
        df['AÑO_MES'] = df['FECHA'].dt.to_period('M').astype(str)
        
        # Agregar etiqueta de año
        df['PERIODO'] = year_label
        
        # Limpiar campos opcionales
        for col in ['COMPROBA', 'VEND', 'DESCRIPCION']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            else:
                df[col] = 'N/D'
        
        st.success(f"✅ Cargados {len(df):,} registros de {year_label}")
        return df
        
    except Exception as e:
        st.error(f"Error al cargar {year_label}: {str(e)}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_catalog(file_obj, key_col, value_col):
    """Carga catálogos de comercios o vendedores"""
    if file_obj is None:
        return None
    
    try:
        if getattr(file_obj, "name", "").lower().endswith(".csv"):
            df = pd.read_csv(file_obj)
        else:
            df = pd.read_excel(file_obj)
        
        # Normalizar columnas
        df.columns = [str(col).strip().upper() for col in df.columns]
        
        # Buscar columnas requeridas (flexible)
        key_found = None
        value_found = None
        
        for col in df.columns:
            if key_col.upper() in col.upper() and key_found is None:
                key_found = col
            if value_col.upper() in col.upper() and value_found is None:
                value_found = col
        
        if key_found and value_found:
            result = df[[key_found, value_found]].copy()
            result.columns = [key_col.upper(), value_col.upper()]
            result[key_col.upper()] = result[key_col.upper()].astype(str).str.strip()
            st.success(f"✅ Catálogo cargado: {len(result)} registros")
            return result
        else:
            st.warning(f"No se encontraron columnas {key_col} y {value_col} en el catálogo")
            return None
            
    except Exception as e:
        st.warning(f"Error al cargar catálogo: {e}")
        return None

def merge_catalogs(df, comercios_df, vendedores_df):
    """Une los catálogos con los datos de ventas"""
    result = df.copy()
    
    if comercios_df is not None and 'COMPROBA' in result.columns:
        # Normalizar COMPROBA antes del merge
        result['COMPROBA'] = result['COMPROBA'].astype(str).str.strip()
        comercios_df['Z'] = comercios_df['Z'].astype(str).str.strip()
        
        result = result.merge(
            comercios_df.rename(columns={'Z': 'COMPROBA', 'NOMBRE': 'COMERCIO_NOMBRE'}),
            on='COMPROBA',
            how='left'
        )
        result['COMERCIO_NOMBRE'] = result['COMERCIO_NOMBRE'].fillna(result['COMPROBA'])
    else:
        result['COMERCIO_NOMBRE'] = result.get('COMPROBA', 'N/D')
    
    if vendedores_df is not None and 'VEND' in result.columns:
        # Normalizar VEND antes del merge
        result['VEND'] = result['VEND'].astype(str).str.strip()
        vendedores_df['VENDEDOR'] = vendedores_df['VENDEDOR'].astype(str).str.strip()
        
        result = result.merge(
            vendedores_df.rename(columns={'VENDEDOR': 'VEND', 'NOMBRE': 'VENDEDOR_NOMBRE'}),
            on='VEND',
            how='left'
        )
        result['VENDEDOR_NOMBRE'] = result['VENDEDOR_NOMBRE'].fillna(result['VEND'])
    else:
        result['VENDEDOR_NOMBRE'] = result.get('VEND', 'N/D')
    
    return result

def pareto_analysis(df_grouped, value_col='VALOR', label_col='REFERENCIA', top_n=50):
    """Análisis de Pareto 80/20"""
    if df_grouped.empty or value_col not in df_grouped.columns:
        return pd.DataFrame(), 0, 0, 0
    
    df_sorted = df_grouped.sort_values(value_col, ascending=False).reset_index(drop=True)
    total = df_sorted[value_col].sum()
    
    if total == 0:
        return df_sorted.head(top_n), 0, 0, 0
    
    df_sorted['ACUM'] = df_sorted[value_col].cumsum()
    df_sorted['ACUM_%'] = 100 * df_sorted['ACUM'] / total
    
    # Calcular cuántos elementos representan el 80%
    items_80 = len(df_sorted[df_sorted['ACUM_%'] <= 80])
    items_90 = len(df_sorted[df_sorted['ACUM_%'] <= 90])
    items_95 = len(df_sorted[df_sorted['ACUM_%'] <= 95])
    
    return df_sorted.head(top_n), items_80, items_90, items_95

# ==========================
# Carga de datos
# ==========================
df_2024 = load_transactional_data(file_2024, "2024")
df_2025 = load_transactional_data(file_2025, "2025")

# Cargar catálogos
comercios_cat = load_catalog(comercios_file, 'Z', 'NOMBRE')
vendedores_cat = load_catalog(vendedores_file, 'VENDEDOR', 'NOMBRE')

# Combinar ambos años
if not df_2024.empty and not df_2025.empty:
    df_all = pd.concat([df_2024, df_2025], ignore_index=True)
    st.success(f"✅ Total combinado: {len(df_all):,} registros")
elif not df_2024.empty:
    df_all = df_2024.copy()
    st.info("Solo datos de 2024 disponibles")
elif not df_2025.empty:
    df_all = df_2025.copy()
    st.info("Solo datos de 2025 disponibles")
else:
    df_all = pd.DataFrame()
    st.warning("⚠️ Por favor, carga al menos un archivo de ventas para comenzar")

# Unir con catálogos
if not df_all.empty:
    df_all = merge_catalogs(df_all, comercios_cat, vendedores_cat)

# ==========================
# Filtros
# ==========================
st.sidebar.markdown("---")
st.sidebar.header("🧭 Filtros")

# Inicializar filtros
año_sel = []
comercio_sel = []
vendedor_sel = []
mes_sel = []

if not df_all.empty:
    # Filtro por año
    años_disponibles = sorted(df_all['AÑO'].unique().tolist())
    año_sel = st.sidebar.multiselect("📅 Año", años_disponibles, default=años_disponibles)
    
    # Filtrar datos según año
    df_filtered = df_all[df_all['AÑO'].isin(año_sel)] if año_sel else df_all.copy()
    
    # Filtro por comercio
    if 'COMERCIO_NOMBRE' in df_filtered.columns:
        comercios_disponibles = sorted(df_filtered['COMERCIO_NOMBRE'].unique().tolist())
        comercio_sel = st.sidebar.multiselect("🏪 Comercio", comercios_disponibles)
        if comercio_sel:
            df_filtered = df_filtered[df_filtered['COMERCIO_NOMBRE'].isin(comercio_sel)]
    
    # Filtro por vendedor
    if 'VENDEDOR_NOMBRE' in df_filtered.columns:
        vendedores_disponibles = sorted(df_filtered['VENDEDOR_NOMBRE'].unique().tolist())
        vendedor_sel = st.sidebar.multiselect("👤 Vendedor", vendedores_disponibles)
        if vendedor_sel:
            df_filtered = df_filtered[df_filtered['VENDEDOR_NOMBRE'].isin(vendedor_sel)]
    
    # Filtro por mes
    meses_disponibles = sorted(df_filtered['MES_NUM'].unique().tolist())
    mes_sel = st.sidebar.multiselect("📆 Mes", meses_disponibles, 
                                     format_func=lambda x: MONTH_MAP.get(x, str(x)))
    if mes_sel:
        df_filtered = df_filtered[df_filtered['MES_NUM'].isin(mes_sel)]
else:
    df_filtered = pd.DataFrame()

# ==========================
# KPIs Principales
# ==========================
st.markdown("---")
st.header("📊 Indicadores Principales")

if not df_filtered.empty:
    col1, col2, col3, col4, col5 = st.columns(5)
    
    ventas_total = df_filtered['VALOR'].sum()
    unidades_total = df_filtered['CANTIDAD'].sum()
    ticket_promedio = ventas_total / unidades_total if unidades_total > 0 else 0
    referencias_activas = df_filtered['REFERENCIA'].nunique()
    transacciones = len(df_filtered)
    
    col1.metric("💰 Ventas Totales", f"${ventas_total:,.0f}")
    col2.metric("📦 Unidades", f"{unidades_total:,.0f}")
    col3.metric("🧾 Ticket Promedio", f"${ticket_promedio:,.0f}")
    col4.metric("🏷️ Referencias Activas", f"{referencias_activas:,}")
    col5.metric("📝 Transacciones", f"{transacciones:,}")
    
    # Segunda fila de KPIs
    col6, col7, col8, col9 = st.columns(4)
    
    # Calcular métricas adicionales
    if 'COMERCIO_NOMBRE' in df_filtered.columns:
        comercios_activos = df_filtered['COMERCIO_NOMBRE'].nunique()
        col6.metric("🏪 Comercios", f"{comercios_activos:,}")
    
    if 'VENDEDOR_NOMBRE' in df_filtered.columns:
        vendedores_activos = df_filtered['VENDEDOR_NOMBRE'].nunique()
        col7.metric("👤 Vendedores", f"{vendedores_activos:,}")
    
    # Venta promedio por transacción
    venta_prom_trans = ventas_total / transacciones if transacciones > 0 else 0
    col8.metric("💵 Venta Prom/Trans", f"${venta_prom_trans:,.0f}")
    
    # Unidades promedio por transacción
    unid_prom_trans = unidades_total / transacciones if transacciones > 0 else 0
    col9.metric("📊 Unid Prom/Trans", f"{unid_prom_trans:.1f}")
else:
    st.info("Carga archivos y aplica filtros para ver los indicadores")

# ==========================
# Comparación Interanual
# ==========================
if not df_filtered.empty and len(año_sel) > 1:
    st.markdown("---")
    st.header("📅 Comparación Interanual")
    
    # Agrupar por año y mes
    comparacion_anual = df_filtered.groupby(['AÑO', 'MES_NUM', 'MES_ABBR'], as_index=False).agg({
        'VALOR': 'sum',
        'CANTIDAD': 'sum'
    })
    comparacion_anual = comparacion_anual.sort_values(['AÑO', 'MES_NUM'])
    
    col_comp1, col_comp2 = st.columns(2)
    
    with col_comp1:
        fig_comp_valor = px.line(
            comparacion_anual,
            x='MES_ABBR',
            y='VALOR',
            color='AÑO',
            title='Comparación de Ventas por Mes ($)',
            markers=True,
            category_orders={'MES_ABBR': MONTH_ORDER}
        )
        st.plotly_chart(fig_comp_valor, use_container_width=True)
    
    with col_comp2:
        fig_comp_cant = px.line(
            comparacion_anual,
            x='MES_ABBR',
            y='CANTIDAD',
            color='AÑO',
            title='Comparación de Unidades por Mes',
            markers=True,
            category_orders={'MES_ABBR': MONTH_ORDER}
        )
        st.plotly_chart(fig_comp_cant, use_container_width=True)
    
    # Calcular variación año a año
    if len(año_sel) == 2:
        años_ordenados = sorted(año_sel)
        año_base = años_ordenados[0]
        año_comp = años_ordenados[1]
        
        ventas_año_base = df_filtered[df_filtered['AÑO'] == año_base]['VALOR'].sum()
        ventas_año_comp = df_filtered[df_filtered['AÑO'] == año_comp]['VALOR'].sum()
        
        if ventas_año_base > 0:
            variacion_pct = ((ventas_año_comp - ventas_año_base) / ventas_año_base) * 100
            st.metric(
                f"📈 Variación {año_comp} vs {año_base}",
                f"${ventas_año_comp - ventas_año_base:,.0f}",
                f"{variacion_pct:+.1f}%"
            )

# ==========================
# Análisis de Referencias - Top y Bottom
# ==========================
if not df_filtered.empty:
    st.markdown("---")
    st.header("🏷️ Análisis de Referencias")
    
    # Agrupar por referencia
    ref_analysis = df_filtered.groupby(['REFERENCIA', 'DESCRIPCION'], as_index=False).agg({
        'VALOR': 'sum',
        'CANTIDAD': 'sum',
        'FECHA': 'count'  # Número de transacciones
    }).rename(columns={'FECHA': 'NUM_TRANSACCIONES'})
    
    ref_analysis['TICKET_PROMEDIO'] = ref_analysis['VALOR'] / ref_analysis['CANTIDAD']
    ref_analysis['VALOR_PROM_TRANS'] = ref_analysis['VALOR'] / ref_analysis['NUM_TRANSACCIONES']
    
    # Ordenar por valor
    ref_analysis_sorted = ref_analysis.sort_values('VALOR', ascending=False).reset_index(drop=True)
    
    # Control de top N
    top_n = st.slider("📊 Top/Bottom N referencias", 5, 50, 20, step=5)
    
    # Tabs para diferentes análisis
    tab1, tab2, tab3 = st.tabs(["💰 Por Valor", "📦 Por Cantidad", "🔄 Por Rotación"])
    
    with tab1:
        col_top1, col_bot1 = st.columns(2)
        
        with col_top1:
            st.subheader(f"🏆 Top {top_n} Referencias por Valor")
            top_refs_valor = ref_analysis_sorted.head(top_n)
            
            fig_top_valor = px.bar(
                top_refs_valor,
                x='REFERENCIA',
                y='VALOR',
                title=f'Top {top_n} Referencias - Ventas ($)',
                text='VALOR',
                hover_data=['DESCRIPCION', 'CANTIDAD', 'TICKET_PROMEDIO']
            )
            fig_top_valor.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            fig_top_valor.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig_top_valor, use_container_width=True)
            
            # Tabla detallada
            top_refs_table = top_refs_valor[['REFERENCIA', 'DESCRIPCION', 'VALOR', 'CANTIDAD', 'TICKET_PROMEDIO']].copy()
            top_refs_table['VALOR'] = top_refs_table['VALOR'].apply(lambda x: f"${x:,.0f}")
            top_refs_table['CANTIDAD'] = top_refs_table['CANTIDAD'].apply(lambda x: f"{x:,.0f}")
            top_refs_table['TICKET_PROMEDIO'] = top_refs_table['TICKET_PROMEDIO'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(top_refs_table, use_container_width=True)
        
        with col_bot1:
            st.subheader(f"⚠️ Bottom {top_n} Referencias por Valor")
            bottom_refs_valor = ref_analysis_sorted.tail(top_n)
            
            fig_bottom_valor = px.bar(
                bottom_refs_valor,
                x='REFERENCIA',
                y='VALOR',
                title=f'Bottom {top_n} Referencias - Ventas ($)',
                text='VALOR',
                color_discrete_sequence=['#ff6b6b'],
                hover_data=['DESCRIPCION', 'CANTIDAD']
            )
            fig_bottom_valor.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            fig_bottom_valor.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig_bottom_valor, use_container_width=True)
            
            # Tabla detallada
            bottom_refs_table = bottom_refs_valor[['REFERENCIA', 'DESCRIPCION', 'VALOR', 'CANTIDAD']].copy()
            bottom_refs_table['VALOR'] = bottom_refs_table['VALOR'].apply(lambda x: f"${x:,.0f}")
            bottom_refs_table['CANTIDAD'] = bottom_refs_table['CANTIDAD'].apply(lambda x: f"{x:,.0f}")
            st.dataframe(bottom_refs_table, use_container_width=True)
    
    with tab2:
        col_top2, col_bot2 = st.columns(2)
        
        with col_top2:
            st.subheader(f"🏆 Top {top_n} Referencias por Cantidad")
            top_refs_cant = ref_analysis.sort_values('CANTIDAD', ascending=False).head(top_n)
            
            fig_top_cant = px.bar(
                top_refs_cant,
                x='REFERENCIA',
                y='CANTIDAD',
                title=f'Top {top_n} Referencias - Unidades',
                text='CANTIDAD',
                color_discrete_sequence=['#4ecdc4'],
                hover_data=['DESCRIPCION', 'VALOR']
            )
            fig_top_cant.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_top_cant.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig_top_cant, use_container_width=True)
        
        with col_bot2:
            st.subheader(f"⚠️ Bottom {top_n} Referencias por Cantidad")
            bottom_refs_cant = ref_analysis.sort_values('CANTIDAD', ascending=True).head(top_n)
            
            fig_bottom_cant = px.bar(
                bottom_refs_cant,
                x='REFERENCIA',
                y='CANTIDAD',
                title=f'Bottom {top_n} Referencias - Unidades',
                text='CANTIDAD',
                color_discrete_sequence=['#ff6b6b'],
                hover_data=['DESCRIPCION', 'VALOR']
            )
            fig_bottom_cant.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_bottom_cant.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig_bottom_cant, use_container_width=True)
    
    with tab3:
        st.subheader("🔄 Análisis de Rotación (Número de Transacciones)")
        
        col_rot1, col_rot2 = st.columns(2)
        
        with col_rot1:
            st.write(f"**Top {top_n} Referencias - Mayor Rotación**")
            top_refs_rot = ref_analysis.sort_values('NUM_TRANSACCIONES', ascending=False).head(top_n)
            
            fig_top_rot = px.bar(
                top_refs_rot,
                x='REFERENCIA',
                y='NUM_TRANSACCIONES',
                title='Referencias con Mayor Rotación',
                text='NUM_TRANSACCIONES',
                color_discrete_sequence=['#95e1d3'],
                hover_data=['DESCRIPCION', 'VALOR', 'CANTIDAD']
            )
            fig_top_rot.update_traces(texttemplate='%{text}', textposition='outside')
            fig_top_rot.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig_top_rot, use_container_width=True)
        
        with col_rot2:
            st.write(f"**Bottom {top_n} Referencias - Menor Rotación**")
            bottom_refs_rot = ref_analysis.sort_values('NUM_TRANSACCIONES', ascending=True).head(top_n)
            
            fig_bottom_rot = px.bar(
                bottom_refs_rot,
                x='REFERENCIA',
                y='NUM_TRANSACCIONES',
                title='Referencias con Menor Rotación',
                text='NUM_TRANSACCIONES',
                color_discrete_sequence=['#f38181'],
                hover_data=['DESCRIPCION', 'VALOR', 'CANTIDAD']
            )
            fig_bottom_rot.update_traces(texttemplate='%{text}', textposition='outside')
            fig_bottom_rot.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig_bottom_rot, use_container_width=True)

# ==========================
# Curva de Pareto 80/20
# ==========================
if not df_filtered.empty:
    st.markdown("---")
    st.header("📈 Análisis de Pareto 80/20")
    
    # Preparar datos para Pareto
    pareto_df, items_80, items_90, items_95 = pareto_analysis(
        ref_analysis_sorted,
        value_col='VALOR',
        label_col='REFERENCIA',
        top_n=100
    )
    
    if not pareto_df.empty:
        # Gráfico de Pareto
        fig_pareto = go.Figure()
        
        # Barras de valor
        fig_pareto.add_trace(go.Bar(
            x=pareto_df['REFERENCIA'],
            y=pareto_df['VALOR'],
            name='Ventas ($)',
            yaxis='y',
            marker_color='steelblue'
        ))
        
        # Línea de acumulado
        fig_pareto.add_trace(go.Scatter(
            x=pareto_df['REFERENCIA'],
            y=pareto_df['ACUM_%'],
            name='% Acumulado',
            yaxis='y2',
            mode='lines+markers',
            line=dict(color='red', width=2),
            marker=dict(size=6)
        ))
        
        # Línea del 80%
        fig_pareto.add_hline(
            y=80, 
            line_dash="dash", 
            line_color="green",
            yref='y2',
            annotation_text="80%"
        )
        
        fig_pareto.update_layout(
            title='Curva de Pareto - Referencias por Valor',
            yaxis=dict(title='Ventas ($)'),
            yaxis2=dict(
                title='% Acumulado',
                overlaying='y',
                side='right',
                range=[0, 100]
            ),
            xaxis=dict(tickangle=45, title='Referencia'),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_pareto, use_container_width=True)
        
        # Métricas de concentración
        total_refs = len(ref_analysis)
        
        col_pareto1, col_pareto2, col_pareto3, col_pareto4 = st.columns(4)
        
        col_pareto1.metric(
            "🎯 Referencias para 80% ventas",
            f"{items_80} de {total_refs}",
            f"{100*items_80/total_refs:.1f}%"
        )
        col_pareto2.metric(
            "🎯 Referencias para 90% ventas",
            f"{items_90} de {total_refs}",
            f"{100*items_90/total_refs:.1f}%"
        )
        col_pareto3.metric(
            "🎯 Referencias para 95% ventas",
            f"{items_95} de {total_refs}",
            f"{100*items_95/total_refs:.1f}%"
        )
        
        # Índice de Herfindahl-Hirschman (HHI)
        ventas_total_hhi = ref_analysis['VALOR'].sum()
        if ventas_total_hhi > 0:
            shares = (ref_analysis['VALOR'] / ventas_total_hhi) ** 2
            hhi = 10000 * shares.sum()
            col_pareto4.metric("📊 Concentración (HHI)", f"{hhi:,.0f}")
        
        # Interpretación del análisis de Pareto
        st.info(f"""
        **Interpretación del Análisis de Pareto:**
        - El **{100*items_80/total_refs:.1f}%** de las referencias ({items_80} productos) generan el **80%** de las ventas
        - Esto indica una concentración {'ALTA' if items_80/total_refs < 0.2 else 'MEDIA' if items_80/total_refs < 0.4 else 'BAJA'} de ventas en pocos productos
        - Recomendación: Enfocarse en optimizar inventario y promoción de estos {items_80} productos clave
        """)

# ==========================
# Análisis Temporal
# ==========================
if not df_filtered.empty:
    st.markdown("---")
    st.header("📅 Análisis Temporal")
    
    # Serie temporal mensual
    temporal_mensual = df_filtered.groupby(['AÑO_MES', 'MES_ABBR', 'AÑO'], as_index=False).agg({
        'VALOR': 'sum',
        'CANTIDAD': 'sum'
    })
    temporal_mensual = temporal_mensual.sort_values('AÑO_MES')
    
    col_temp1, col_temp2 = st.columns(2)
    
    with col_temp1:
        fig_temp_valor = px.line(
            temporal_mensual,
            x='AÑO_MES',
            y='VALOR',
            title='Evolución de Ventas por Mes ($)',
            markers=True
        )
        fig_temp_valor.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_temp_valor, use_container_width=True)
    
    with col_temp2:
        fig_temp_cant = px.line(
            temporal_mensual,
            x='AÑO_MES',
            y='CANTIDAD',
            title='Evolución de Unidades por Mes',
            markers=True,
            color_discrete_sequence=['#4ecdc4']
        )
        fig_temp_cant.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_temp_cant, use_container_width=True)

# ==========================
# Análisis por Comercio
# ==========================
if not df_filtered.empty and 'COMERCIO_NOMBRE' in df_filtered.columns:
    st.markdown("---")
    st.header("🏪 Análisis por Comercio")
    
    comercio_analysis = df_filtered.groupby('COMERCIO_NOMBRE', as_index=False).agg({
        'VALOR': 'sum',
        'CANTIDAD': 'sum',
        'REFERENCIA': 'nunique',
        'FECHA': 'count'
    }).rename(columns={
        'REFERENCIA': 'REFERENCIAS_UNICAS',
        'FECHA': 'TRANSACCIONES'
    })
    comercio_analysis = comercio_analysis.sort_values('VALOR', ascending=False)
    
    col_com1, col_com2 = st.columns(2)
    
    with col_com1:
        fig_comercio_valor = px.bar(
            comercio_analysis.head(15),
            x='COMERCIO_NOMBRE',
            y='VALOR',
            title='Top 15 Comercios por Ventas ($)',
            text='VALOR'
        )
        fig_comercio_valor.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig_comercio_valor.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_comercio_valor, use_container_width=True)
    
    with col_com2:
        fig_comercio_cant = px.bar(
            comercio_analysis.head(15),
            x='COMERCIO_NOMBRE',
            y='CANTIDAD',
            title='Top 15 Comercios por Unidades',
            text='CANTIDAD',
            color_discrete_sequence=['#95e1d3']
        )
        fig_comercio_cant.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_comercio_cant.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_comercio_cant, use_container_width=True)
    
    # Tabla detallada de comercios
    st.subheader("📊 Detalle por Comercio")
    comercio_table = comercio_analysis.copy()
    comercio_table['TICKET_PROM'] = comercio_table['VALOR'] / comercio_table['CANTIDAD']
    comercio_table['VALOR_PROM_TRANS'] = comercio_table['VALOR'] / comercio_table['TRANSACCIONES']
    
    comercio_display = comercio_table[['COMERCIO_NOMBRE', 'VALOR', 'CANTIDAD', 'REFERENCIAS_UNICAS', 
                                       'TRANSACCIONES', 'TICKET_PROM', 'VALOR_PROM_TRANS']].copy()
    comercio_display['VALOR'] = comercio_display['VALOR'].apply(lambda x: f"${x:,.0f}")
    comercio_display['CANTIDAD'] = comercio_display['CANTIDAD'].apply(lambda x: f"{x:,.0f}")
    comercio_display['TICKET_PROM'] = comercio_display['TICKET_PROM'].apply(lambda x: f"${x:,.0f}")
    comercio_display['VALOR_PROM_TRANS'] = comercio_display['VALOR_PROM_TRANS'].apply(lambda x: f"${x:,.0f}")
    comercio_display.columns = ['Comercio', 'Ventas', 'Unidades', 'Referencias', 'Transacciones', 'Ticket Prom', 'Valor Prom/Trans']
    
    st.dataframe(comercio_display, use_container_width=True, height=400)

# ==========================
# Análisis por Vendedor
# ==========================
if not df_filtered.empty and 'VENDEDOR_NOMBRE' in df_filtered.columns:
    st.markdown("---")
    st.header("👤 Análisis por Vendedor")
    
    vendedor_analysis = df_filtered.groupby('VENDEDOR_NOMBRE', as_index=False).agg({
        'VALOR': 'sum',
        'CANTIDAD': 'sum',
        'REFERENCIA': 'nunique',
        'FECHA': 'count'
    }).rename(columns={
        'REFERENCIA': 'REFERENCIAS_UNICAS',
        'FECHA': 'TRANSACCIONES'
    })
    vendedor_analysis = vendedor_analysis.sort_values('VALOR', ascending=False)
    
    col_vend1, col_vend2 = st.columns(2)
    
    with col_vend1:
        fig_vendedor_valor = px.bar(
            vendedor_analysis.head(15),
            x='VENDEDOR_NOMBRE',
            y='VALOR',
            title='Top 15 Vendedores por Ventas ($)',
            text='VALOR',
            color_discrete_sequence=['#f38181']
        )
        fig_vendedor_valor.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig_vendedor_valor.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_vendedor_valor, use_container_width=True)
    
    with col_vend2:
        fig_vendedor_cant = px.bar(
            vendedor_analysis.head(15),
            x='VENDEDOR_NOMBRE',
            y='CANTIDAD',
            title='Top 15 Vendedores por Unidades',
            text='CANTIDAD',
            color_discrete_sequence=['#aa96da']
        )
        fig_vendedor_cant.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_vendedor_cant.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_vendedor_cant, use_container_width=True)
    
    # Tabla detallada de vendedores
    st.subheader("📊 Detalle por Vendedor")
    vendedor_table = vendedor_analysis.copy()
    vendedor_table['TICKET_PROM'] = vendedor_table['VALOR'] / vendedor_table['CANTIDAD']
    vendedor_table['VALOR_PROM_TRANS'] = vendedor_table['VALOR'] / vendedor_table['TRANSACCIONES']
    
    vendedor_display = vendedor_table[['VENDEDOR_NOMBRE', 'VALOR', 'CANTIDAD', 'REFERENCIAS_UNICAS', 
                                        'TRANSACCIONES', 'TICKET_PROM', 'VALOR_PROM_TRANS']].copy()
    vendedor_display['VALOR'] = vendedor_display['VALOR'].apply(lambda x: f"${x:,.0f}")
    vendedor_display['CANTIDAD'] = vendedor_display['CANTIDAD'].apply(lambda x: f"{x:,.0f}")
    vendedor_display['TICKET_PROM'] = vendedor_display['TICKET_PROM'].apply(lambda x: f"${x:,.0f}")
    vendedor_display['VALOR_PROM_TRANS'] = vendedor_display['VALOR_PROM_TRANS'].apply(lambda x: f"${x:,.0f}")
    vendedor_display.columns = ['Vendedor', 'Ventas', 'Unidades', 'Referencias', 'Transacciones', 'Ticket Prom', 'Valor Prom/Trans']
    
    st.dataframe(vendedor_display, use_container_width=True, height=400)

# ==========================
# Referencias sin Movimiento
# ==========================
if not df_filtered.empty:
    st.markdown("---")
    st.header("⚠️ Alertas y Referencias de Atención")
    
    col_alert1, col_alert2 = st.columns(2)
    
    with col_alert1:
        st.subheader("🔴 Referencias con Baja Rotación")
        
        # Referencias con menos de 3 transacciones
        refs_baja_rotacion = ref_analysis[ref_analysis['NUM_TRANSACCIONES'] <= 3].sort_values('NUM_TRANSACCIONES')
        
        st.metric("Referencias con ≤3 transacciones", len(refs_baja_rotacion))
        
        if not refs_baja_rotacion.empty:
            refs_baja_display = refs_baja_rotacion.head(20)[['REFERENCIA', 'DESCRIPCION', 'NUM_TRANSACCIONES', 'CANTIDAD', 'VALOR']].copy()
            refs_baja_display['VALOR'] = refs_baja_display['VALOR'].apply(lambda x: f"${x:,.0f}")
            refs_baja_display['CANTIDAD'] = refs_baja_display['CANTIDAD'].apply(lambda x: f"{x:,.0f}")
            refs_baja_display.columns = ['Referencia', 'Descripción', 'Trans', 'Unidades', 'Valor']
            st.dataframe(refs_baja_display, use_container_width=True, height=300)
    
    with col_alert2:
        st.subheader("💰 Referencias con Bajo Valor")
        
        # Referencias con ventas menores al percentil 25
        if len(ref_analysis) > 0:
            percentil_25 = ref_analysis['VALOR'].quantile(0.25)
            refs_bajo_valor = ref_analysis[ref_analysis['VALOR'] <= percentil_25].sort_values('VALOR')
            
            st.metric(f"Referencias ≤ P25 (${percentil_25:,.0f})", len(refs_bajo_valor))
            
            if not refs_bajo_valor.empty:
                refs_bajo_display = refs_bajo_valor.head(20)[['REFERENCIA', 'DESCRIPCION', 'VALOR', 'CANTIDAD', 'NUM_TRANSACCIONES']].copy()
                refs_bajo_display['VALOR'] = refs_bajo_display['VALOR'].apply(lambda x: f"${x:,.0f}")
                refs_bajo_display['CANTIDAD'] = refs_bajo_display['CANTIDAD'].apply(lambda x: f"{x:,.0f}")
                refs_bajo_display.columns = ['Referencia', 'Descripción', 'Valor', 'Unidades', 'Trans']
                st.dataframe(refs_bajo_display, use_container_width=True, height=300)

# ==========================
# Exportar Datos
# ==========================
if not df_filtered.empty:
    st.markdown("---")
    st.header("📥 Exportar Datos")
    
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    
    with col_exp1:
        # Exportar análisis de referencias
        csv_refs = ref_analysis.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 Descargar Análisis de Referencias (CSV)",
            data=csv_refs,
            file_name=f"analisis_referencias_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col_exp2:
        if 'comercio_analysis' in locals():
            csv_comercios = comercio_analysis.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="🏪 Descargar Análisis de Comercios (CSV)",
                data=csv_comercios,
                file_name=f"analisis_comercios_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col_exp3:
        if 'vendedor_analysis' in locals():
            csv_vendedores = vendedor_analysis.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="👤 Descargar Análisis de Vendedores (CSV)",
                data=csv_vendedores,
                file_name=f"analisis_vendedores_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

# ==========================
# Footer
# ==========================
st.markdown("---")
st.caption("Dashboard Ejecutivo de Ventas - Ekonomodo | Desarrollado con Streamlit")
st.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")