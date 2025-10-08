# -*- coding: utf-8 -*-
import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Logo en la esquina superior
top_col1, top_col2 = st.columns([0.7,0.3])
with top_col2:
    st.image("https://ekonomodo.com/cdn/shop/files/Logo-Ekonomodo-color.svg?v=1736956350&width=450", width=5000)

# ==========================
# Config general
# ==========================
st.set_page_config(page_title="Dashboard Ejecutivo - Ekonomodo", layout="wide")

st.title("📊 Dashboard Ejecutivo de Ventas — Ekonomodo")
st.caption("Fuente: Auxiliar por número - Análisis transaccional completo")

# ==========================
# Parámetros de carga
# ==========================<

# Archivos de catálogos
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Cargar Datos")

# Archivos principales de ventas
st.sidebar.subheader("📁 Archivos de Ventas")
st.sidebar.caption("Libro de ventas (base principal)")
libro_2024 = st.sidebar.file_uploader("Libro Ventas 2024", type=["xlsx", "xls"], key="libro_2024")
libro_2025 = st.sidebar.file_uploader("Libro Ventas 2025", type=["xlsx", "xls"], key="libro_2025")

st.sidebar.caption("Auxiliar por número (datos complementarios)")
aux_2024 = st.sidebar.file_uploader("Auxiliar 2024", type=["xlsx", "xls"], key="aux_2024")
aux_2025 = st.sidebar.file_uploader("Auxiliar 2025", type=["xlsx", "xls"], key="aux_2025")

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
def load_libro_ventas(file_obj, year_label):
    """Carga Libro de ventas - BASE PRINCIPAL"""
    if file_obj is None:
        return pd.DataFrame()
    
    try:
        # Leer directamente con encabezados en la primera fila
        df = pd.read_excel(file_obj, header=0)
        
        # Normalizar nombres de columnas
        df.columns = [str(col).strip().upper().replace('.', '').replace(' ', '_') for col in df.columns]
        
        # Mapear nombres de columnas a los esperados
        column_mapping = {}
        for col in df.columns:
            if 'GRAVADAS' in col and 'IVA' in col:
                column_mapping[col] = 'VALOR_REAL'
            elif col == 'NRO':
                column_mapping[col] = 'NRO'
            elif 'FECHA' in col:
                column_mapping[col] = 'FECHA'
        
        df = df.rename(columns=column_mapping)
        
        # Verificar columnas requeridas
        if 'NRO' not in df.columns or 'VALOR_REAL' not in df.columns:
            st.error(f"Libro {year_label}: Faltan columnas NRO o GRAVADAS_IVA")
            st.info(f"Columnas encontradas: {list(df.columns)}")
            return pd.DataFrame()
        
        # Normalizar NRO
        df['NRO'] = df['NRO'].astype(str).str.replace('.0', '', regex=False).str.strip()
        
        # Normalizar VALOR_REAL
        df['VALOR_REAL'] = pd.to_numeric(df['VALOR_REAL'], errors='coerce').fillna(0)
        
        # Filtrar registros válidos
        df = df[df['VALOR_REAL'] > 0]
        df = df[df['NRO'].str.len() > 0]
        df = df[df['NRO'] != '0']
        
        df['PERIODO'] = year_label
        
        return df
        
    except Exception as e:
        st.error(f"Error en Libro {year_label}: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_auxiliar(file_obj, year_label):
    """Carga Auxiliar - DATOS COMPLEMENTARIOS"""
    if file_obj is None:
        return pd.DataFrame()
    
    try:
        # Leer directamente con encabezados en la primera fila
        df = pd.read_excel(file_obj, header=0)
        
        # Normalizar nombres de columnas
        df.columns = [str(col).strip().upper().replace('.', '').replace(' ', '_') for col in df.columns]
        
        # Verificar que existan las columnas necesarias
        if 'NRO_CRUCE' not in df.columns or 'REFERENCIA' not in df.columns:
            st.error(f"Auxiliar {year_label}: Faltan columnas NRO_CRUCE o REFERENCIA")
            st.info(f"Columnas encontradas: {list(df.columns)}")
            return pd.DataFrame()
        
        # Normalizar NRO_CRUCE de forma simple
        df['NRO_CRUCE'] = df['NRO_CRUCE'].astype(str).str.replace('.0', '', regex=False).str.strip()
        
        # Normalizar REFERENCIA
        df['REFERENCIA'] = df['REFERENCIA'].fillna('').astype(str).str.strip().str.upper()
        
        # Filtrar EKMFLETE
        df = df[~df['REFERENCIA'].str.contains('EKMFLETE|EKMSS', na=False, case=False)]
        
        # Normalizar campos opcionales
        for col in ['COMPROBA', 'VEND', 'DESCRIPCION']:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str).str.strip()
        
        if 'CANTIDAD' in df.columns:
            df['CANTIDAD'] = pd.to_numeric(df['CANTIDAD'], errors='coerce').fillna(0.0)
        else:
            df['CANTIDAD'] = 0.0
        
        # Limpiar registros vacíos
        df = df[df['REFERENCIA'].str.len() > 0]
        df = df[df['NRO_CRUCE'].str.len() > 0]
        df = df[df['NRO_CRUCE'] != '0']
        
        return df
        
    except Exception as e:
        st.error(f"Error en Auxiliar {year_label}: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
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
            # st.success(f"✅ Catálogo cargado: {len(result)} registros")
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
    
    # **GUARDAR NOMBRE DEL AUXILIAR ANTES DEL MERGE (SI EXISTE)**
    nombre_guardado = False
    if 'NOMBRE' in result.columns:
        # Verificar que sea una Serie, no un DataFrame
        if isinstance(result['NOMBRE'], pd.Series):
            result['NOMBRE_AUX_ORIGINAL'] = result['NOMBRE'].astype(str).str.strip().str.upper()
            nombre_guardado = True
        else:
            # Si es DataFrame, tomar la primera columna
            result['NOMBRE_AUX_ORIGINAL'] = result['NOMBRE'].iloc[:, 0].astype(str).str.strip().str.upper()
            nombre_guardado = True
    
    if comercios_df is not None and 'COMPROBA' in result.columns:
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
    
    # **REGLA ESPECIAL Z-082 USANDO NOMBRE GUARDADO**
    if nombre_guardado and 'COMPROBA' in result.columns and 'NOMBRE_AUX_ORIGINAL' in result.columns:
        mask_z082 = result['COMPROBA'] == 'Z-082'
        
        mask_falabella = mask_z082 & result['NOMBRE_AUX_ORIGINAL'].str.contains('FALABELLA', na=False, case=False)
        result.loc[mask_falabella, 'COMERCIO_NOMBRE'] = 'FALABELLA CT VERDE'
        
        mask_seller = mask_z082 & ~result['NOMBRE_AUX_ORIGINAL'].str.contains('FALABELLA', na=False, case=False)
        result.loc[mask_seller, 'COMERCIO_NOMBRE'] = 'FALABELLA SELLER'
        
        # Mostrar contador
        count_ct_verde = mask_falabella.sum()
        count_seller = mask_seller.sum()
        if count_ct_verde > 0 or count_seller > 0:
            st.info(f"✅ Z-082 clasificado: {count_ct_verde:,} CT VERDE | {count_seller:,} SELLER")
        
        # Limpiar columna temporal
        result = result.drop(columns=['NOMBRE_AUX_ORIGINAL'], errors='ignore')
    
    if vendedores_df is not None and 'VEND' in result.columns:
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
# Cargar Libro de ventas
libro_df_2024 = load_libro_ventas(libro_2024, "2024")
libro_df_2025 = load_libro_ventas(libro_2025, "2025")

# Cargar Auxiliar
aux_df_2024 = load_auxiliar(aux_2024, "2024")
aux_df_2025 = load_auxiliar(aux_2025, "2025")

# Cargar catálogos
comercios_cat = load_catalog(comercios_file, 'Z', 'NOMBRE')
vendedores_cat = load_catalog(vendedores_file, 'VENDEDOR', 'NOMBRE')

# Combinar años del Libro
if not libro_df_2024.empty and not libro_df_2025.empty:
    libro_all = pd.concat([libro_df_2024, libro_df_2025], ignore_index=True)
elif not libro_df_2024.empty:
    libro_all = libro_df_2024.copy()
    st.info("Solo datos de Libro 2024 disponibles")
elif not libro_df_2025.empty:
    libro_all = libro_df_2025.copy()
    st.info("Solo datos de Libro 2025 disponibles")
else:
    libro_all = pd.DataFrame()

# Combinar años del Auxiliar
if not aux_df_2024.empty and not aux_df_2025.empty:
    aux_all = pd.concat([aux_df_2024, aux_df_2025], ignore_index=True)
    # st.success(f"✅ Total combinado Auxiliar: {len(aux_all):,} registros")
elif not aux_df_2024.empty:
    aux_all = aux_df_2024.copy()
    st.info("Solo datos de Auxiliar 2024 disponibles")
elif not aux_df_2025.empty:
    aux_all = aux_df_2025.copy()
    st.info("Solo datos de Auxiliar 2025 disponibles")
else:
    aux_all = pd.DataFrame()

# ==========================
# DIAGNÓSTICO DE CRUCE
# ==========================
if not libro_all.empty and not aux_all.empty:

    aux_all = aux_all.drop_duplicates(subset=['NRO_CRUCE'], keep='first')
    
    # col_diag1, col_diag2 = st.columns(2)
    
    # with col_diag1:
    #     st.subheader("📘 Libro de Ventas")
    #     st.write(f"**Total registros:** {len(libro_all):,}")
    #     st.write(f"**Columnas:** {', '.join(libro_all.columns.tolist())}")
    #     st.write("**Muestra de NRO (primeros 10):**")
    #     nro_sample = libro_all['NRO'].head(10).tolist()
    #     for i, nro in enumerate(nro_sample, 1):
    #         st.write(f"{i}. `{nro}` (tipo: {type(nro).__name__}, longitud: {len(str(nro))})")
    
    # with col_diag2:
    #     st.subheader("📗 Auxiliar")
    #     st.write(f"**Total registros:** {len(aux_all):,}")
    #     st.write(f"**Columnas:** {', '.join(aux_all.columns.tolist())}")
    #     st.write("**Muestra de NRO_CRUCE (primeros 10):**")
    #     nro_cruce_sample = aux_all['NRO_CRUCE'].head(10).tolist()
    #     for i, nro in enumerate(nro_cruce_sample, 1):
    #         st.write(f"{i}. `{nro}` (tipo: {type(nro).__name__}, longitud: {len(str(nro))})")

df_all = pd.DataFrame()

# CRUCE: Libro (NRO) con Auxiliar (NRO_CRUCE)
if not libro_all.empty and not aux_all.empty:
    df_all = libro_all.merge(
        aux_all,
        left_on='NRO',
        right_on='NRO_CRUCE',
        how='inner',
        suffixes=('_LIBRO', '_AUX')  # Sufijos para columnas duplicadas
    )
    
    # Renombrar columnas para consistencia
    rename_dict = {}
    
    # Manejar FECHA
    if 'FECHA_LIBRO' in df_all.columns:
        rename_dict['FECHA_LIBRO'] = 'FECHA'
    elif 'FECHA_AUX' in df_all.columns:
        rename_dict['FECHA_AUX'] = 'FECHA'
    
    # Valor real
    if 'VALOR_REAL' in df_all.columns:
        rename_dict['VALOR_REAL'] = 'VALOR'
    
    # Cantidad
    if 'CANTENTREGA' in df_all.columns:
        rename_dict['CANTENTREGA'] = 'CANTIDAD'
    
    # NOMBRE del auxiliar (el importante)
    if 'NOMBRE_AUX' in df_all.columns:
        rename_dict['NOMBRE_AUX'] = 'NOMBRE'
    
    df_all = df_all.rename(columns=rename_dict)
    
    # Seleccionar columnas necesarias
    columnas_base = ['NRO', 'FECHA', 'VALOR', 'PERIODO', 'REFERENCIA', 
                     'DESCRIPCION', 'COMPROBA', 'VEND', 'CANTIDAD', 
                     'NRO_CRUCE', 'NOMBRE']
    
    columnas_finales = [col for col in columnas_base if col in df_all.columns]
    df_all = df_all[columnas_finales].copy()
    
    # Extraer año del PERIODO
    if 'PERIODO' in df_all.columns:
        df_all['AÑO'] = pd.to_numeric(df_all['PERIODO'], errors='coerce').fillna(0).astype(int)
    
    # Si existe FECHA, extraer mes
    if 'FECHA' in df_all.columns:
        df_all['FECHA'] = pd.to_datetime(df_all['FECHA'], errors='coerce')
        df_all['MES_NUM'] = df_all['FECHA'].dt.month.fillna(1).astype(int)
        df_all['MES_ABBR'] = df_all['MES_NUM'].map(MONTH_MAP)
        df_all['AÑO_MES'] = df_all['FECHA'].dt.to_period('M').astype(str)
    else:
        df_all['MES_NUM'] = 1
        df_all['MES_ABBR'] = 'ENE'
        df_all['AÑO_MES'] = df_all['AÑO'].astype(str) + '-01'
    
    st.success(f"✅ Cruce exitoso: {len(df_all):,} registros con datos completos")
    st.write(f"**Columnas finales:** {list(df_all.columns)}")

# Unir con catálogos
if not df_all.empty:
    df_all = merge_catalogs(df_all, comercios_cat, vendedores_cat)
    
    # **LIMPIAR COLUMNAS DUPLICADAS**
    df_all = df_all.loc[:, ~df_all.columns.duplicated(keep='first')]
    
    # Verificar columnas finales
    st.write(f"**Columnas después de limpieza:** {list(df_all.columns)}")

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
    
    # Verificar y manejar Series vs valor escalar
    try:
        if isinstance(df_filtered['VALOR'], pd.DataFrame):
            ventas_total = df_filtered['VALOR'].iloc[:, 0].sum()
        else:
            ventas_total = df_filtered['VALOR'].sum()
        
        if isinstance(df_filtered['CANTIDAD'], pd.DataFrame):
            unidades_total = df_filtered['CANTIDAD'].iloc[:, 0].sum()
        else:
            unidades_total = df_filtered['CANTIDAD'].sum()
        
        ticket_promedio = ventas_total / unidades_total if unidades_total > 0 else 0
        referencias_activas = df_filtered['REFERENCIA'].nunique() if isinstance(df_filtered['REFERENCIA'], pd.Series) else df_filtered['REFERENCIA'].iloc[:, 0].nunique()
        transacciones = len(df_filtered)
        
        col1.metric("💰 Ventas Totales", f"${ventas_total:,.0f}")
        col2.metric("📦 Unidades", f"{unidades_total:,.0f}")
        col3.metric("🧾 Ticket Promedio", f"${ticket_promedio:,.0f}")
        col4.metric("🏷️ Referencias Activas", f"{referencias_activas:,}")
        col5.metric("📝 Transacciones", f"{transacciones:,}")
    except Exception as e:
        st.error(f"Error calculando KPIs: {e}")
        st.write("Columnas disponibles:", df_filtered.columns.tolist())
    
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
        
        # col_pareto1, col_pareto2, col_pareto3, col_pareto4 = st.columns(4)
        col_pareto1, col_pareto2, col_pareto3 = st.columns(3)

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
        
        # # Índice de Herfindahl-Hirschman (HHI)
        # ventas_total_hhi = ref_analysis['VALOR'].sum()
        # if ventas_total_hhi > 0:
        #     shares = (ref_analysis['VALOR'] / ventas_total_hhi) ** 2
        #     hhi = 10000 * shares.sum()
        #     # col_pareto4.metric("📊 Concentración (HHI)", f"{hhi:,.0f}")
        
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