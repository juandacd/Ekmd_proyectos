# -*- coding: utf-8 -*-
import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ==========================
# Config general
# ==========================
st.set_page_config(page_title="Dashboard Ejecutivo - Ekonomodo", layout="wide")

st.title("📊 Dashboard Ejecutivo de Ventas — Ekonomodo")
st.caption("Fuente: Siigo – Ventas mensuales por producto")

# ==========================
# Parámetros de carga
# ==========================
st.sidebar.header("⚙️ Parámetros")
uploaded_file = st.sidebar.file_uploader("Sube el archivo de ventas (Excel)", type=["xlsx", "xls"])

# Opcional: archivo de costos unitarios
st.sidebar.markdown("---")
st.sidebar.subheader("💸 (Opcional) Costos para margen")
st.sidebar.caption("Un archivo con columnas: PRODUCTO o REFERENCIA, y COSTO_UNITARIO.")
costs_file = st.sidebar.file_uploader("Sube archivo de costos (xlsx/csv)", type=["xlsx","xls","csv"])

# ==========================
# Funciones auxiliares
# ==========================
MONTH_MAP = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12
}
MONTH_ORDER = ["ENE","FEB","MAR","ABR","MAY","JUN","JUL","AGO","SEP","OCT","NOV","DIC"]

@st.cache_data(show_spinner=False)
def load_sales_df(file_like_or_path):
    try:
        # Lee todo el archivo primero para analizar la estructura
        df_raw = pd.read_excel(file_like_or_path)
        
        # Buscar la fila que contiene los encabezados principales
        header_row = None
        for i, row in df_raw.iterrows():
            # Convertir toda la fila a string y limpiar
            row_values = [str(cell).strip().upper() for cell in row if pd.notna(cell)]
            row_str = ' '.join(row_values)
            
            # Verificar si contiene las palabras clave (más flexible)
            has_linea = any('LINEA' in val for val in row_values)
            has_grupo = any('GRUPO' in val for val in row_values) 
            has_producto = any('PRODUCTO' in val for val in row_values)
            
            if has_linea and has_grupo and has_producto:
                header_row = i
                break
        
        # Si no encuentra los encabezados, asumir que están en la primera fila
        if header_row is None:
            st.warning("No se encontró fila de encabezados específica, usando la primera fila")
            header_row = 0
            
            # Verificar que realmente tenga las columnas esperadas
            first_row_cols = [str(col).strip().upper() for col in df_raw.iloc[0] if pd.notna(col)]
            has_required_cols = (
                any('LINEA' in col for col in first_row_cols) and 
                any('GRUPO' in col for col in first_row_cols) and 
                any('PRODUCTO' in col for col in first_row_cols)
            )
            
            if not has_required_cols:
                # Intentar con los nombres de columnas originales
                original_cols = [str(col).strip().upper() for col in df_raw.columns]
                has_required_cols = (
                    any('LINEA' in col for col in original_cols) and 
                    any('GRUPO' in col for col in original_cols) and 
                    any('PRODUCTO' in col for col in original_cols)
                )
                
                if has_required_cols:
                    # Los encabezados están en las columnas originales
                    df = df_raw.copy()
                    header_row = None  # No saltar filas
                else:
                    st.error("No se encontraron las columnas requeridas: LINEA, GRUPO, PRODUCTO")
                    return pd.DataFrame(), pd.DataFrame(), []
        
        # Leer desde la fila de encabezados si es necesario
        if header_row is not None:
            df = pd.read_excel(file_like_or_path, skiprows=header_row)
        
        # Limpiar y normalizar nombres de columnas
        df.columns = [str(col).strip().upper() for col in df.columns]
        df.columns = [re.sub(r'\s+', ' ', col) for col in df.columns]
        
        # Renombrar columnas que pueden venir con nombres raros
        column_mapping = {}
        for i, col in enumerate(df.columns):
            col_clean = str(col).upper().strip()
            if 'LINEA' in col_clean and not any('DESCRIPCION' in col_clean for x in [col_clean]):
                if 'LINEA' not in column_mapping.values():  # Solo mapear el primero
                    column_mapping[col] = 'LINEA'
            elif 'GRUPO' in col_clean and not any('DESCRIPCION' in col_clean for x in [col_clean]):
                if 'GRUPO' not in column_mapping.values():  # Solo mapear el primero
                    column_mapping[col] = 'GRUPO'  
            elif 'PRODUCTO' in col_clean:
                column_mapping[col] = 'PRODUCTO'
            elif 'REFERENCIA' in col_clean:
                column_mapping[col] = 'REFERENCIA'
            elif 'DESCRIPCION' in col_clean and 'LINEA' in col_clean:
                column_mapping[col] = 'DESCRIPCION_LINEA'
            elif 'DESCRIPCION' in col_clean and 'GRUPO' in col_clean:
                column_mapping[col] = 'DESCRIPCION_GRUPO'
            elif 'DESCRIPCION' in col_clean and col_clean == 'DESCRIPCION':
                column_mapping[col] = 'DESCRIPCION'
        
        df = df.rename(columns=column_mapping)
        
        st.info(f"Columnas después del mapeo: {list(df.columns)}")
        
        # Filtrar filas que NO son totales y tienen datos válidos
        if 'LINEA' in df.columns:
            # Eliminar filas de totales por línea/grupo
            total_mask = df['LINEA'].astype(str).str.contains(r'^TOTAL', case=False, na=False)
            if 'GRUPO' in df.columns:
                total_mask = total_mask | df['GRUPO'].astype(str).str.contains(r'^TOTAL', case=False, na=False)
            df = df[~total_mask]
            
            # Mantener solo filas con LINEA válida (código numérico o texto válido)
            valid_linea = (
                df['LINEA'].notna() & 
                (df['LINEA'].astype(str).str.strip() != '') &
                (~df['LINEA'].astype(str).str.contains(r'^TOTAL', case=False, na=False))
            )
            df = df[valid_linea]
        
        # Filtrar filas con PRODUCTO válido
        if 'PRODUCTO' in df.columns:
            valid_producto = (
                df['PRODUCTO'].notna() & 
                (df['PRODUCTO'].astype(str).str.strip() != '') &
                (~df['PRODUCTO'].astype(str).str.contains(r'^TOTAL', case=False, na=False))
            )
            df = df[valid_producto]
        
        # Mantener columnas básicas
        base_cols = []
        for col in ['LINEA', 'GRUPO', 'PRODUCTO', 'REFERENCIA', 'DESCRIPCION', 'DESCRIPCION_LINEA', 'DESCRIPCION_GRUPO']:
            if col in df.columns:
                base_cols.append(col)
        
        # Buscar columnas de meses y totales - FIXED REGEX
        month_pattern = re.compile(r'^(ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)[\.\s]*(CANTIDAD|VALOR)$', re.IGNORECASE)
        month_cols = [c for c in df.columns if month_pattern.match(str(c))]
        
        # Buscar columnas de totales - FIXED REGEX
        total_pattern = re.compile(r'^TOT[\.\s]*(CANTIDAD|VALOR)$', re.IGNORECASE)
        total_cols = [c for c in df.columns if total_pattern.match(str(c))]
        
        st.info(f"Columnas detectadas - Base: {len(base_cols)} {base_cols}, Meses: {len(month_cols)}, Totales: {len(total_cols)}")
        
        # Convertir columnas numéricas
        numeric_cols = month_cols + total_cols
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Crear DataFrame largo (mensual)
        long_rows = []
        if month_cols:
            for col in month_cols:
                match = month_pattern.match(str(col))
                if match:
                    mes_abbr = match.group(1).upper()
                    metric = match.group(2).upper()
                    
                    temp_df = df[base_cols + [col]].copy()
                    temp_df = temp_df.rename(columns={col: 'valor'})
                    temp_df['MES_ABBR'] = mes_abbr
                    temp_df['METRICA'] = metric
                    long_rows.append(temp_df)
        
        if long_rows:
            long_df = pd.concat(long_rows, ignore_index=True)
            # Pivotear para tener CANTIDAD y VALOR como columnas
            long_df = long_df.pivot_table(
                index=base_cols + ['MES_ABBR'],
                columns='METRICA',
                values='valor',
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            
            # Asegurar que existan las columnas
            for col in ['CANTIDAD', 'VALOR']:
                if col not in long_df.columns:
                    long_df[col] = 0.0
            
            # Añadir número de mes
            long_df['MES_NUM'] = long_df['MES_ABBR'].map(MONTH_MAP).fillna(0).astype(int)
            long_df = long_df[long_df['MES_NUM'] > 0]  # Filtrar meses válidos
            long_df = long_df.sort_values(['MES_NUM'] + [col for col in base_cols if col in long_df.columns])
        else:
            long_df = pd.DataFrame(columns=base_cols + ['MES_ABBR', 'CANTIDAD', 'VALOR', 'MES_NUM'])
        
        # DataFrame ancho (totales)
        wide_cols = base_cols + [col for col in total_cols if col in df.columns]
        wide_df = df[wide_cols].copy() if wide_cols else pd.DataFrame()
        
        # Calcular ticket promedio si hay datos de totales
        if not wide_df.empty:
            cantidad_col = next((col for col in wide_df.columns if 'CANTIDAD' in col.upper()), None)
            valor_col = next((col for col in wide_df.columns if 'VALOR' in col.upper()), None)
            
            if cantidad_col and valor_col:
                # Normalizar nombres de columnas de totales
                wide_df = wide_df.rename(columns={cantidad_col: 'TOT. CANTIDAD', valor_col: 'TOT. VALOR'})
                wide_df['TICKET_PROM'] = np.where(
                    wide_df['TOT. CANTIDAD'] > 0,
                    wide_df['TOT. VALOR'] / wide_df['TOT. CANTIDAD'],
                    0
                )
        
        return long_df, wide_df, base_cols
        
    except Exception as e:
        st.error(f"Error al procesar el archivo: {str(e)}")
        st.exception(e)  # Mostrar traceback completo para debug
        return pd.DataFrame(), pd.DataFrame(), []

@st.cache_data(show_spinner=False)
def load_costs_df(file_like):
    if file_like is None:
        return None
    try:
        if getattr(file_like, "name", "").lower().endswith(".csv"):
            dfc = pd.read_csv(file_like)
        else:
            dfc = pd.read_excel(file_like)
        # Normalizar nombres de columnas
        dfc.columns = [str(col).strip().upper() for col in dfc.columns]
        dfc.columns = [re.sub(r'\s+', ' ', col) for col in dfc.columns]
        # Esperado: PRODUCTO o REFERENCIA y COSTO_UNITARIO
        rename_map = {}
        if "COSTO UNITARIO" in dfc.columns:
            rename_map["COSTO UNITARIO"] = "COSTO_UNITARIO"
        dfc = dfc.rename(columns=rename_map)
        return dfc
    except Exception as e:
        st.warning(f"No se pudo leer archivo de costos: {e}")
        return None

def join_costs(wide_tot, costs_df):
    if costs_df is None or wide_tot is None or wide_tot.empty:
        return wide_tot
    w = wide_tot.copy()
    c = costs_df.copy()
    # Normalizar nombres
    w.columns = [col.upper() for col in w.columns]
    # Merge por PRODUCTO si existe, si no por REFERENCIA
    how_merge = None
    if "PRODUCTO" in w.columns and "PRODUCTO" in c.columns:
        w = w.merge(c[["PRODUCTO","COSTO_UNITARIO"]], on="PRODUCTO", how="left")
        how_merge = "PRODUCTO"
    elif "REFERENCIA" in w.columns and "REFERENCIA" in c.columns:
        w = w.merge(c[["REFERENCIA","COSTO_UNITARIO"]], on="REFERENCIA", how="left")
        how_merge = "REFERENCIA"
    else:
        st.warning("No fue posible cruzar costos: se requieren columnas comunes PRODUCTO o REFERENCIA.")
        return wide_tot

    w["COSTO_UNITARIO"] = pd.to_numeric(w.get("COSTO_UNITARIO"), errors="coerce")
    if "TOT. CANTIDAD" in w.columns:
        w["COSTO_TOTAL_EST"] = w["COSTO_UNITARIO"] * w["TOT. CANTIDAD"]
    if "TOT. VALOR" in w.columns:
        w["UTILIDAD_EST"] = w["TOT. VALOR"] - w.get("COSTO_TOTAL_EST", 0)
        w["MARGEN_%"] = np.where(w["TOT. VALOR"]>0, 100 * w["UTILIDAD_EST"]/w["TOT. VALOR"], np.nan)
    st.caption(f"Costos enlazados por **{how_merge}**.")
    return w

def pareto_curve(df_val, value_col="TOT. VALOR", label_col="DESCRIPCION", top_n=30):
    if df_val.empty or value_col not in df_val.columns or label_col not in df_val.columns:
        return pd.DataFrame(), 0
    d = df_val[[label_col, value_col]].copy().sort_values(value_col, ascending=False).reset_index(drop=True)
    d["ACUM"] = d[value_col].cumsum()
    total = d[value_col].sum()
    d["ACUM_%"] = np.where(total>0, 100*d["ACUM"]/total, 0)
    return d.head(top_n), total

def create_reference_analysis(data_df, long_df, group_col="REFERENCIA"):
    """
    Función específica para análisis de referencias
    """
    if group_col not in data_df.columns or data_df.empty:
        return None, None, None, None
    
    # Agregar por referencia
    ref_agg = data_df.groupby(group_col, as_index=False).agg({
        'TOT. VALOR': 'sum',
        'TOT. CANTIDAD': 'sum',
        'PRODUCTO': 'nunique',  # Cantidad de productos diferentes por referencia
    }).rename(columns={'PRODUCTO': 'NUM_PRODUCTOS'})
    
    # Calcular ticket promedio por referencia
    ref_agg['TICKET_PROM_REF'] = np.where(
        ref_agg['TOT. CANTIDAD'] > 0,
        ref_agg['TOT. VALOR'] / ref_agg['TOT. CANTIDAD'],
        0
    )
    
    # Top y Bottom referencias
    top_refs_valor = ref_agg.sort_values('TOT. VALOR', ascending=False)
    top_refs_cantidad = ref_agg.sort_values('TOT. CANTIDAD', ascending=False)
    bottom_refs = ref_agg[ref_agg['TOT. CANTIDAD'] > 0].sort_values('TOT. CANTIDAD', ascending=True)
    
    # Análisis temporal si hay datos mensuales
    temporal_analysis = None
    if not long_df.empty and group_col in long_df.columns:
        temporal_analysis = (long_df.groupby([group_col, 'MES_ABBR'], as_index=False)
                           .agg({'VALOR': 'sum', 'CANTIDAD': 'sum'}))
        temporal_analysis['MES_NUM'] = temporal_analysis['MES_ABBR'].map(MONTH_MAP).fillna(0).astype(int)
        temporal_analysis = temporal_analysis[temporal_analysis['MES_NUM'] > 0].sort_values(['MES_NUM', 'VALOR'], ascending=[True, False])
    
    return ref_agg, top_refs_valor, top_refs_cantidad, bottom_refs, temporal_analysis

# ==========================
# Carga de datos
# ==========================
# Solo usar el archivo cargado
file_to_read = uploaded_file

# Inicializar variables por defecto
long_df = pd.DataFrame()
wide_tot = pd.DataFrame()
base_cols = ["PRODUCTO", "REFERENCIA", "DESCRIPCION"]

if file_to_read is not None:
    try:
        long_df, wide_tot, base_cols = load_sales_df(file_to_read)
        if wide_tot.empty:
            st.warning("No se pudieron cargar los datos del archivo. Verifica que el archivo tiene el formato correcto.")
    except Exception as e:
        st.error(f"No pude leer el Excel. Revisa el archivo. Detalle: {e}")
        st.info("Cargando con datos vacíos para mostrar la estructura del dashboard...")
else:
    st.info("Por favor, carga un archivo Excel para comenzar el análisis.")
    st.info("El archivo debe contener columnas: LINEA, GRUPO, PRODUCTO, REFERENCIA, DESCRIPCION y columnas mensuales (ENE.CANTIDAD, ENE.VALOR, etc.)")

# Cruce de costos (opcional) - ahora con verificación
costs_df = load_costs_df(costs_file)
if not wide_tot.empty:
    wide_tot_cost = join_costs(wide_tot, costs_df) if costs_df is not None else wide_tot
else:
    wide_tot_cost = wide_tot  # DataFrame vacío

# ==========================
# Filtros
# ==========================
st.sidebar.header("🧭 Filtros")
# Filtros jerárquicos si existen
if "LINEA" in base_cols and not wide_tot_cost.empty:
    linea_sel = st.sidebar.multiselect("Línea", sorted(wide_tot_cost["LINEA"].dropna().unique().tolist()))
else:
    linea_sel = []
if "GRUPO" in base_cols and not wide_tot_cost.empty:
    # filtrar por línea primero si aplica
    _tmp = wide_tot_cost
    if linea_sel:
        _tmp = _tmp[_tmp["LINEA"].isin(linea_sel)]
    grupo_sel = st.sidebar.multiselect("Grupo", sorted(_tmp["GRUPO"].dropna().unique().tolist()))
else:
    grupo_sel = []

# Nuevo filtro por referencia
if "REFERENCIA" in base_cols and not wide_tot_cost.empty:
    _tmp_ref = wide_tot_cost
    if linea_sel:
        _tmp_ref = _tmp_ref[_tmp_ref["LINEA"].isin(linea_sel)]
    if grupo_sel:
        _tmp_ref = _tmp_ref[_tmp_ref["GRUPO"].isin(grupo_sel)]
    ref_sel = st.sidebar.multiselect("Referencia", sorted(_tmp_ref["REFERENCIA"].dropna().unique().tolist()))
else:
    ref_sel = []

# Filtros aplicados a ambos dataframes
def apply_filters(df_in):
    if df_in.empty:
        return df_in
    df2 = df_in.copy()
    if linea_sel and "LINEA" in df2.columns:
        df2 = df2[df2["LINEA"].isin(linea_sel)]
    if grupo_sel and "GRUPO" in df2.columns:
        df2 = df2[df2["GRUPO"].isin(grupo_sel)]
    if ref_sel and "REFERENCIA" in df2.columns:
        df2 = df2[df2["REFERENCIA"].isin(ref_sel)]
    return df2

wide_f = apply_filters(wide_tot_cost)
long_f = apply_filters(long_df)

# Filtro de meses para series
if not long_f.empty and "MES_NUM" in long_f.columns:
    if long_f["MES_NUM"].notna().any():
        min_m, max_m = int(long_f["MES_NUM"].min()), int(long_f["MES_NUM"].max())
        mes_range = st.sidebar.slider("Rango de meses", min_value=1, max_value=12,
                                      value=(min_m, max_m), step=1)
        long_f = long_f[(long_f["MES_NUM"]>=mes_range[0]) & (long_f["MES_NUM"]<=mes_range[1])]
    else:
        mes_range = (1, 12)
else:
    mes_range = (1, 12)

# ==========================
# KPIs
# ==========================
col1, col2, col3, col4, col5 = st.columns(5)

# Cálculos con verificación de datos vacíos
ventas_tot = wide_f["TOT. VALOR"].sum() if "TOT. VALOR" in wide_f.columns and not wide_f.empty else (long_f["VALOR"].sum() if not long_f.empty else 0)
unid_tot = wide_f["TOT. CANTIDAD"].sum() if "TOT. CANTIDAD" in wide_f.columns and not wide_f.empty else (long_f["CANTIDAD"].sum() if not long_f.empty else 0)
prod_act = wide_f["PRODUCTO"].nunique() if "PRODUCTO" in wide_f.columns and not wide_f.empty else (long_f["PRODUCTO"].nunique() if not long_f.empty else 0)
ref_act = wide_f["REFERENCIA"].nunique() if "REFERENCIA" in wide_f.columns and not wide_f.empty else (long_f["REFERENCIA"].nunique() if not long_f.empty else 0)
ticket_prom = ventas_tot / unid_tot if unid_tot > 0 else 0

col1.metric("💰 Ventas Totales", f"${ventas_tot:,.0f}")
col2.metric("📦 Unidades", f"{unid_tot:,.0f}")
col3.metric("🧾 Ticket Promedio", f"${ticket_prom:,.0f}")
col4.metric("🔢 Productos Activos", f"{prod_act:,}")
col5.metric("📋 Referencias Activas", f"{ref_act:,}")

# Segunda fila de KPIs
col6, col7, col8 = st.columns(3)

# HHI para productos
hhi_prod = None
if "TOT. VALOR" in wide_f.columns and ventas_tot > 0 and not wide_f.empty:
    shares = (wide_f["TOT. VALOR"] / ventas_tot) ** 2
    hhi_prod = 10000 * shares.sum()

# HHI para referencias
hhi_ref = None
if "REFERENCIA" in wide_f.columns and "TOT. VALOR" in wide_f.columns and not wide_f.empty:
    ref_ventas = wide_f.groupby("REFERENCIA")["TOT. VALOR"].sum()
    if ventas_tot > 0:
        ref_shares = (ref_ventas / ventas_tot) ** 2
        hhi_ref = 10000 * ref_shares.sum()

col6.metric("📚 Concentración Prod. (HHI)", f"{hhi_prod:,.0f}" if hhi_prod is not None else "NA")
col7.metric("📊 Concentración Ref. (HHI)", f"{hhi_ref:,.0f}" if hhi_ref is not None else "NA")

if "MARGEN_%" in wide_f.columns and not wide_f.empty:
    util_total = wide_f.get("UTILIDAD_EST", pd.Series(dtype=float)).sum()
    margen_prom = np.nanmean(wide_f["MARGEN_%"])
    col8.metric("💵 Utilidad Estimada", f"${util_total:,.0f}")

st.markdown("---")

# ==========================
# Tendencia mensual
# ==========================
st.subheader("📈 Tendencia mensual")
if long_f.empty:
    st.info("No se detectaron columnas mensuales en el archivo o no hay datos para mostrar.")
else:
    # Serie valor
    serie_valor = long_f.groupby("MES_NUM", as_index=False)["VALOR"].sum()
    serie_valor["MES"] = serie_valor["MES_NUM"].map({v:k for k,v in MONTH_MAP.items()})
    fig_val = px.line(serie_valor, x="MES", y="VALOR", markers=True, title="Ventas por Mes ($)")
    st.plotly_chart(fig_val, use_container_width=True)

    # Serie cantidad
    serie_qty = long_f.groupby("MES_NUM", as_index=False)["CANTIDAD"].sum()
    serie_qty["MES"] = serie_qty["MES_NUM"].map({v:k for k,v in MONTH_MAP.items()})
    fig_qty = px.line(serie_qty, x="MES", y="CANTIDAD", markers=True, title="Unidades por Mes")
    st.plotly_chart(fig_qty, use_container_width=True)

# ==========================
# Rankings Top/Bottom
# ==========================
st.subheader("🏆 Rankings de productos")
top_n = st.slider("Top N", 5, 30, 10, step=5)

# Base para ranking: usar totales
rank_base = wide_f.copy()
if ("TOT. VALOR" not in rank_base.columns or rank_base.empty) and not long_f.empty:  # fallback desde long
    agg = long_f.groupby(["PRODUCTO","REFERENCIA","DESCRIPCION"], as_index=False)[["VALOR","CANTIDAD"]].sum()
    agg = agg.rename(columns={"VALOR":"TOT. VALOR","CANTIDAD":"TOT. CANTIDAD"})
    rank_base = agg

if not rank_base.empty and "TOT. VALOR" in rank_base.columns:
    top_valor = rank_base.sort_values("TOT. VALOR", ascending=False).head(top_n)
    top_cant = rank_base.sort_values("TOT. CANTIDAD", ascending=False).head(top_n)
    bottom_cant = rank_base[rank_base["TOT. CANTIDAD"]>0].sort_values("TOT. CANTIDAD", ascending=True).head(top_n)

    c1, c2 = st.columns(2)
    c1.plotly_chart(px.bar(top_valor, x="DESCRIPCION", y="TOT. VALOR", title=f"Top {top_n} por valor ($)", text_auto=True),
                    use_container_width=True)
    c2.plotly_chart(px.bar(top_cant, x="DESCRIPCION", y="TOT. CANTIDAD", title=f"Top {top_n} por unidades", text_auto=True),
                    use_container_width=True)

    st.plotly_chart(px.bar(bottom_cant, x="DESCRIPCION", y="TOT. CANTIDAD",
                           title=f"Bottom {top_n} por unidades (excluye 0)", text_auto=True),
                    use_container_width=True)
else:
    st.info("No hay datos suficientes para mostrar los rankings de productos.")

# ==========================
# NUEVA SECCIÓN: ANÁLISIS COMPLETO DE REFERENCIAS
# ==========================
st.markdown("---")
st.header("🏷️ ANÁLISIS DETALLADO DE REFERENCIAS")

if "REFERENCIA" in wide_f.columns and not wide_f.empty:
    # Crear análisis de referencias
    ref_analysis = create_reference_analysis(wide_f, long_f, "REFERENCIA")
    ref_agg, top_refs_valor, top_refs_cantidad, bottom_refs, temporal_refs = ref_analysis
    
    if ref_agg is not None and not ref_agg.empty:
        # KPIs específicos de referencias
        st.subheader("📊 KPIs de Referencias")
        col1_ref, col2_ref, col3_ref, col4_ref = st.columns(4)
        
        total_refs = len(ref_agg)
        avg_valor_por_ref = ref_agg["TOT. VALOR"].mean()
        avg_cantidad_por_ref = ref_agg["TOT. CANTIDAD"].mean()
        refs_con_multiples_prod = len(ref_agg[ref_agg["NUM_PRODUCTOS"] > 1])
        
        col1_ref.metric("🏷️ Total Referencias", f"{total_refs:,}")
        col2_ref.metric("💰 Venta Promedio/Ref", f"${avg_valor_por_ref:,.0f}")
        col3_ref.metric("📦 Unidades Prom/Ref", f"{avg_cantidad_por_ref:,.0f}")
        col4_ref.metric("🔗 Refs Multi-Producto", f"{refs_con_multiples_prod:,}")
        
        # Rankings de referencias
        st.subheader("🏆 Top y Bottom Referencias")
        
        # Crear tabs para diferentes análisis
        tab1, tab2, tab3 = st.tabs(["💰 Por Valor", "📦 Por Cantidad", "📊 Análisis Comparativo"])
        
        with tab1:
            st.write("**Top Referencias por Valor de Ventas**")
            col_a, col_b = st.columns(2)
            
            with col_a:
                top_refs_display = top_refs_valor.head(top_n)
                fig_top_valor_ref = px.bar(
                    top_refs_display, 
                    x="REFERENCIA", 
                    y="TOT. VALOR",
                    title=f"Top {top_n} Referencias por Valor ($)",
                    text_auto=True,
                    hover_data=["NUM_PRODUCTOS", "TICKET_PROM_REF"]
                )
                fig_top_valor_ref.update_layout(xaxis_tickangle=45)
                st.plotly_chart(fig_top_valor_ref, use_container_width=True)
                
                # Tabla detallada
                st.write("**Detalle de Top Referencias por Valor**")
                top_refs_table = top_refs_display[["REFERENCIA", "TOT. VALOR", "TOT. CANTIDAD", "NUM_PRODUCTOS", "TICKET_PROM_REF"]].copy()
                top_refs_table["TOT. VALOR"] = top_refs_table["TOT. VALOR"].apply(lambda x: f"${x:,.0f}")
                top_refs_table["TOT. CANTIDAD"] = top_refs_table["TOT. CANTIDAD"].apply(lambda x: f"{x:,.0f}")
                top_refs_table["TICKET_PROM_REF"] = top_refs_table["TICKET_PROM_REF"].apply(lambda x: f"${x:,.0f}")
                top_refs_table.columns = ["Referencia", "Valor Total", "Cantidad", "# Productos", "Ticket Prom"]
                st.dataframe(top_refs_table, use_container_width=True)
            
            with col_b:
                # Bottom referencias (con ventas > 0)
                bottom_refs_display = bottom_refs.head(top_n)
                fig_bottom_valor_ref = px.bar(
                    bottom_refs_display,
                    x="REFERENCIA",
                    y="TOT. VALOR", 
                    title=f"Bottom {top_n} Referencias por Valor ($)",
                    text_auto=True,
                    color_discrete_sequence=["#ff6b6b"]
                )
                fig_bottom_valor_ref.update_layout(xaxis_tickangle=45)
                st.plotly_chart(fig_bottom_valor_ref, use_container_width=True)
                
                # Tabla detallada bottom
                st.write("**Detalle de Bottom Referencias por Valor**")
                bottom_refs_table = bottom_refs_display[["REFERENCIA", "TOT. VALOR", "TOT. CANTIDAD", "NUM_PRODUCTOS", "TICKET_PROM_REF"]].copy()
                bottom_refs_table["TOT. VALOR"] = bottom_refs_table["TOT. VALOR"].apply(lambda x: f"${x:,.0f}")
                bottom_refs_table["TOT. CANTIDAD"] = bottom_refs_table["TOT. CANTIDAD"].apply(lambda x: f"{x:,.0f}")
                bottom_refs_table["TICKET_PROM_REF"] = bottom_refs_table["TICKET_PROM_REF"].apply(lambda x: f"${x:,.0f}")
                bottom_refs_table.columns = ["Referencia", "Valor Total", "Cantidad", "# Productos", "Ticket Prom"]
                st.dataframe(bottom_refs_table, use_container_width=True)
        
        with tab2:
            st.write("**Top Referencias por Cantidad Vendida**")
            col_c, col_d = st.columns(2)
            
            with col_c:
                top_cant_refs_display = top_refs_cantidad.head(top_n)
                fig_top_cant_ref = px.bar(
                    top_cant_refs_display,
                    x="REFERENCIA",
                    y="TOT. CANTIDAD",
                    title=f"Top {top_n} Referencias por Cantidad",
                    text_auto=True,
                    color_discrete_sequence=["#4ecdc4"],
                    hover_data=["TOT. VALOR", "TICKET_PROM_REF"]
                )
                fig_top_cant_ref.update_layout(xaxis_tickangle=45)
                st.plotly_chart(fig_top_cant_ref, use_container_width=True)
            
            with col_d:
                # Scatter: Valor vs Cantidad por referencia
                fig_scatter_ref = px.scatter(
                    ref_agg,
                    x="TOT. CANTIDAD",
                    y="TOT. VALOR",
                    hover_data=["REFERENCIA", "NUM_PRODUCTOS", "TICKET_PROM_REF"],
                    title="Referencias: Valor vs Cantidad",
                    labels={"TOT. CANTIDAD": "Cantidad Total", "TOT. VALOR": "Valor Total ($)"}
                )
                st.plotly_chart(fig_scatter_ref, use_container_width=True)
        
        with tab3:
            # Análisis de concentración por referencias
            st.write("**Análisis de Concentración por Referencias**")
            
            # Curva de Pareto para referencias
            ref_pareto, total_ref = pareto_curve(ref_agg, value_col="TOT. VALOR", label_col="REFERENCIA", top_n=30)
            
            if not ref_pareto.empty:
                fig_pareto_ref = go.Figure()
                fig_pareto_ref.add_bar(
                    x=ref_pareto["REFERENCIA"], 
                    y=ref_pareto["TOT. VALOR"], 
                    name="Ventas por Ref",
                    yaxis="y"
                )
                fig_pareto_ref.add_trace(go.Scatter(
                    x=ref_pareto["REFERENCIA"], 
                    y=ref_pareto["ACUM_%"],
                    name="% Acumulado", 
                    yaxis="y2", 
                    mode="lines+markers",
                    line=dict(color="red")
                ))
                fig_pareto_ref.update_layout(
                    title="Curva de Pareto - Referencias",
                    yaxis=dict(title="Ventas ($)"),
                    yaxis2=dict(title="% Acumulado", overlaying="y", side="right", range=[0,100]),
                    xaxis=dict(tickangle=45)
                )
                st.plotly_chart(fig_pareto_ref, use_container_width=True)
                
                # Análisis 80/20
                col_80_1, col_80_2, col_80_3 = st.columns(3)
                
                refs_80 = len(ref_pareto[ref_pareto["ACUM_%"] <= 80])
                refs_90 = len(ref_pareto[ref_pareto["ACUM_%"] <= 90])
                refs_95 = len(ref_pareto[ref_pareto["ACUM_%"] <= 95])
                
                col_80_1.metric("🎯 Referencias para 80%", f"{refs_80}/{total_refs} ({100*refs_80/total_refs:.1f}%)")
                col_80_2.metric("🎯 Referencias para 90%", f"{refs_90}/{total_refs} ({100*refs_90/total_refs:.1f}%)")
                col_80_3.metric("🎯 Referencias para 95%", f"{refs_95}/{total_refs} ({100*refs_95/total_refs:.1f}%)")
        
        # # Análisis temporal de referencias (si hay datos mensuales)
        # if temporal_refs is not None and not temporal_refs.empty:
        #     st.subheader("📅 Evolución Temporal de Referencias")
            
        #     # Top 10 referencias para análisis temporal
        #     top_10_refs = ref_agg.head(10)["REFERENCIA"].tolist()
        #     temporal_top = temporal_refs[temporal_refs["REFERENCIA"].isin(top_10_refs)]
            
        #     if not temporal_top.empty:
        #         # Gráfico de líneas por referencia
        #         fig_temporal_refs = px.line(
        #             temporal_top,
        #             x="MES_ABBR",
        #             y="VALOR",
        #             color="REFERENCIA",
        #             title="Evolución Mensual - Top 10 Referencias por Valor",
        #             markers=True
        #         )
        #         fig_temporal_refs.update_layout(xaxis=dict(categoryorder='array', categoryarray=MONTH_ORDER))
        #         st.plotly_chart(fig_temporal_refs, use_container_width=True)
                
        #         # Heatmap de referencias vs meses
        #         pivot_refs = temporal_refs.pivot_table(
        #             index="REFERENCIA", 
        #             columns="MES_ABBR", 
        #             values="VALOR", 
        #             aggfunc="sum", 
        #             fill_value=0
        #         )
                
        #         # Tomar solo las top 20 referencias para el heatmap
        #         top_20_for_heat = ref_agg.head(20)["REFERENCIA"].tolist()
        #         pivot_refs_filtered = pivot_refs[pivot_refs.index.isin(top_20_for_heat)]
                
        #         if not pivot_refs_filtered.empty:
        #             fig_heat_refs = px.imshow(
        #                 pivot_refs_filtered,
        #                 title="Heatmap: Referencias vs Meses (Top 20 Referencias)",
        #                 labels=dict(x="Mes", y="Referencia", color="Ventas ($)"),
        #                 aspect="auto",
        #                 color_continuous_scale="Viridis"
        #             )
        #             st.plotly_chart(fig_heat_refs, use_container_width=True)
        
        # Referencias sin movimiento o con bajo desempeño
        st.subheader("⚠️ Referencias de Atención Especial")
        
        col_atencion1, col_atencion2 = st.columns(2)
        
        with col_atencion1:
            # Referencias con una sola venta o muy pocas
            refs_bajo_vol = ref_agg[ref_agg["TOT. CANTIDAD"] <= 1]
            st.write(f"**Referencias con ≤1 unidad vendida: {len(refs_bajo_vol)}**")
            if not refs_bajo_vol.empty:
                refs_bajo_vol_display = refs_bajo_vol[["REFERENCIA", "TOT. VALOR", "TOT. CANTIDAD", "NUM_PRODUCTOS"]].copy()
                refs_bajo_vol_display["TOT. VALOR"] = refs_bajo_vol_display["TOT. VALOR"].apply(lambda x: f"${x:,.0f}")
                refs_bajo_vol_display.columns = ["Referencia", "Valor", "Cantidad", "# Productos"]
                st.dataframe(refs_bajo_vol_display, use_container_width=True)
        
        with col_atencion2:
            # Referencias con ticket promedio muy bajo
            if ref_agg["TICKET_PROM_REF"].sum() > 0:
                percentil_25 = ref_agg["TICKET_PROM_REF"].quantile(0.25)
                refs_ticket_bajo = ref_agg[ref_agg["TICKET_PROM_REF"] <= percentil_25]
                st.write(f"**Referencias con ticket bajo (≤P25: ${percentil_25:,.0f}): {len(refs_ticket_bajo)}**")
                if not refs_ticket_bajo.empty:
                    refs_ticket_display = refs_ticket_bajo[["REFERENCIA", "TICKET_PROM_REF", "TOT. CANTIDAD", "NUM_PRODUCTOS"]].head(10).copy()
                    refs_ticket_display["TICKET_PROM_REF"] = refs_ticket_display["TICKET_PROM_REF"].apply(lambda x: f"${x:,.0f}")
                    refs_ticket_display.columns = ["Referencia", "Ticket Prom", "Cantidad", "# Productos"]
                    st.dataframe(refs_ticket_display, use_container_width=True)
        
        # Análisis de referencias por línea/grupo si existen
        if "LINEA" in wide_f.columns or "GRUPO" in wide_f.columns:
            st.subheader("🏗️ Referencias por Línea/Grupo")
            
            if "LINEA" in wide_f.columns:
                refs_por_linea = wide_f.groupby(["LINEA", "REFERENCIA"], as_index=False)["TOT. VALOR"].sum()
                refs_count_linea = refs_por_linea.groupby("LINEA")["REFERENCIA"].nunique().reset_index()
                refs_count_linea.columns = ["LINEA", "NUM_REFERENCIAS"]
                
                fig_refs_linea = px.bar(
                    refs_count_linea.sort_values("NUM_REFERENCIAS", ascending=False),
                    x="LINEA",
                    y="NUM_REFERENCIAS",
                    title="Número de Referencias por Línea",
                    text_auto=True
                )
                st.plotly_chart(fig_refs_linea, use_container_width=True)
            
            if "GRUPO" in wide_f.columns:
                refs_por_grupo = wide_f.groupby(["GRUPO", "REFERENCIA"], as_index=False)["TOT. VALOR"].sum()
                refs_count_grupo = refs_por_grupo.groupby("GRUPO")["REFERENCIA"].nunique().reset_index()
                refs_count_grupo.columns = ["GRUPO", "NUM_REFERENCIAS"]
                
                fig_refs_grupo = px.bar(
                    refs_count_grupo.sort_values("NUM_REFERENCIAS", ascending=False),
                    x="GRUPO",
                    y="NUM_REFERENCIAS", 
                    title="Número de Referencias por Grupo",
                    text_auto=True
                )
                fig_refs_grupo.update_layout(xaxis_tickangle=45)
                st.plotly_chart(fig_refs_grupo, use_container_width=True)

else:
    st.info("No se encontró la columna 'REFERENCIA' en los datos o no hay datos para mostrar el análisis de referencias.")

# ==========================
# Curva de Pareto & concentración (PRODUCTOS)
# ==========================
# st.markdown("---")
# st.subheader("📌 Concentración de ventas por Productos (Pareto)")
# if not rank_base.empty and "TOT. VALOR" in rank_base.columns:
#     pareto_df, total_val = pareto_curve(rank_base.rename(columns={"TOT. VALOR":"TOT. VALOR", "DESCRIPCION":"DESCRIPCION"}),
#                                         value_col="TOT. VALOR", label_col="DESCRIPCION", top_n=50)
#     if not pareto_df.empty:
#         fig_pareto = go.Figure()
#         fig_pareto.add_bar(x=pareto_df["DESCRIPCION"], y=pareto_df["TOT. VALOR"], name="Ventas")
#         fig_pareto.add_trace(go.Scatter(x=pareto_df["DESCRIPCION"], y=pareto_df["ACUM_%"],
#                                         name="Acumulado %", yaxis="y2", mode="lines+markers"))
#         fig_pareto.update_layout(
#             title="Curva de Pareto de productos",
#             yaxis=dict(title="Ventas ($)"),
#             yaxis2=dict(title="Acumulado %", overlaying="y", side="right", range=[0,100]),
#             xaxis=dict(tickangle=45)
#         )
#         st.plotly_chart(fig_pareto, use_container_width=True)

#         top_share_k = st.number_input("Calcular participación del Top-K", min_value=1, max_value=100, value=10)
#         top_share = rank_base.sort_values("TOT. VALOR", ascending=False).head(int(top_share_k))["TOT. VALOR"].sum()
#         st.metric(f"Participación Top-{int(top_share_k)}", f"{(100*top_share/max(1,ventas_tot)):.1f}%")
# else:
#     st.info("No hay datos suficientes para mostrar la curva de Pareto.")

# ==========================
# Análisis por Línea / Grupo (si existen)
# ==========================
if ("LINEA" in base_cols or "GRUPO" in base_cols) and not wide_f.empty:
    st.subheader("🏗️ Análisis por Línea / Grupo")
    if "LINEA" in base_cols and "LINEA" in wide_f.columns:
        g_linea = wide_f.groupby("LINEA", as_index=False)[["TOT. VALOR","TOT. CANTIDAD"]].sum()
        st.plotly_chart(px.bar(g_linea.sort_values("TOT. VALOR", ascending=False),
                               x="LINEA", y="TOT. VALOR", title="Ventas por Línea ($)", text_auto=True),
                        use_container_width=True)
    if "GRUPO" in base_cols and "GRUPO" in wide_f.columns:
        g_grupo = wide_f.groupby("GRUPO", as_index=False)[["TOT. VALOR","TOT. CANTIDAD"]].sum()
        st.plotly_chart(px.bar(g_grupo.sort_values("TOT. VALOR", ascending=False),
                               x="GRUPO", y="TOT. VALOR", title="Ventas por Grupo ($)", text_auto=True),
                        use_container_width=True)

# ==========================
# Estacionalidad / Heatmap
# ==========================
# st.subheader("📆 Estacionalidad")
# if not long_f.empty:
#     # Heatmap por mes vs TOP productos por valor
#     topK = 20
#     top_prod = (long_f.groupby(["PRODUCTO","DESCRIPCION"])["VALOR"].sum()
#                 .sort_values(ascending=False).head(topK).reset_index()["PRODUCTO"])
#     heat = (long_f[long_f["PRODUCTO"].isin(top_prod)]
#             .groupby(["DESCRIPCION","MES_ABBR"], as_index=False)["VALOR"].sum())
#     if not heat.empty:
#         heat["MES_ABBR"] = pd.Categorical(heat["MES_ABBR"], categories=MONTH_ORDER, ordered=True)
#         fig_heat = px.density_heatmap(heat, x="MES_ABBR", y="DESCRIPCION", z="VALOR",
#                                       title=f"Heatmap de ventas por mes — Top {topK} productos",
#                                       nbinsx=12, histfunc="sum", text_auto=True)
#         st.plotly_chart(fig_heat, use_container_width=True)

#         # Barras por mes (Top grupos si existen)
#         if "GRUPO" in long_f.columns:
#             g_month_group = (long_f.groupby(["MES_ABBR","GRUPO"], as_index=False)["VALOR"].sum())
#             if not g_month_group.empty:
#                 g_month_group["MES_ABBR"] = pd.Categorical(g_month_group["MES_ABBR"], categories=MONTH_ORDER, ordered=True)
#                 fig_grp = px.bar(g_month_group, x="MES_ABBR", y="VALOR", color="GRUPO",
#                                  title="Ventas por mes y grupo ($)", barmode="stack")
#                 st.plotly_chart(fig_grp, use_container_width=True)

# ==========================
# Precio promedio y dispersión
# ==========================
# st.subheader("💲 Precio promedio y dispersión")
# if {"TOT. VALOR","TOT. CANTIDAD"}.issubset(set(wide_f.columns)) and not wide_f.empty:
#     df_price = wide_f.copy()
#     df_price["TICKET_PROM"] = np.where(df_price["TOT. CANTIDAD"]>0,
#                                        df_price["TOT. VALOR"]/df_price["TOT. CANTIDAD"], 0.0)
#     fig_scatter = px.scatter(df_price, x="TOT. CANTIDAD", y="TICKET_PROM",
#                              hover_data=["DESCRIPCION","REFERENCIA"],
#                              title="Dispersión: Unidades vs Ticket promedio")
#     st.plotly_chart(fig_scatter, use_container_width=True)

# ==========================
# Productos silenciosos / baja rotación
# ==========================
st.subheader("🧯 Productos silenciosos y de baja rotación")
if not long_df.empty:
    # Sin ventas en periodo filtrado
    vendidos = long_f.groupby("PRODUCTO")["CANTIDAD"].sum()
    sin_ventas = vendidos[vendidos==0].index
    base = long_df.drop_duplicates(subset=["PRODUCTO","DESCRIPCION","REFERENCIA"])[["PRODUCTO","DESCRIPCION","REFERENCIA"]]
    tabla_silenciosos = base[base["PRODUCTO"].isin(sin_ventas)]
    st.write(f"Productos sin ventas en meses {mes_range[0]}–{mes_range[1]}: {len(tabla_silenciosos)}")
    if not tabla_silenciosos.empty:
        st.dataframe(tabla_silenciosos.reset_index(drop=True), use_container_width=True)

    # Baja rotación (percentil 10 por unidades)
    agg_units = long_f.groupby(["PRODUCTO","DESCRIPCION","REFERENCIA"], as_index=False)["CANTIDAD"].sum()
    if not agg_units.empty and len(agg_units) > 5:
        p10 = agg_units["CANTIDAD"].quantile(0.1)
        baja_rotacion = agg_units[agg_units["CANTIDAD"] <= p10]
        st.write(f"Productos con baja rotación (≤P10: {p10:.1f} unidades): {len(baja_rotacion)}")
        if not baja_rotacion.empty:
            st.dataframe(baja_rotacion.head(20), use_container_width=True)

# ==========================
# Referencias silenciosas / baja rotación
# ==========================
if "REFERENCIA" in long_df.columns:
    st.subheader("🏷️ Referencias silenciosas y de baja rotación")
    
    # Sin ventas en periodo filtrado
    refs_vendidas = long_f.groupby("REFERENCIA")["CANTIDAD"].sum()
    refs_sin_ventas = refs_vendidas[refs_vendidas==0].index
    base_refs = long_df.drop_duplicates(subset=["REFERENCIA","DESCRIPCION","PRODUCTO"])[["REFERENCIA","DESCRIPCION","PRODUCTO"]]
    tabla_refs_silenciosas = base_refs[base_refs["REFERENCIA"].isin(refs_sin_ventas)]
    st.write(f"Referencias sin ventas en meses {mes_range[0]}–{mes_range[1]}: {len(tabla_refs_silenciosas)}")
    if not tabla_refs_silenciosas.empty:
        st.dataframe(tabla_refs_silenciosas.reset_index(drop=True), use_container_width=True)

    # Baja rotación para referencias
    agg_refs_units = long_f.groupby(["REFERENCIA","DESCRIPCION","PRODUCTO"], as_index=False)["CANTIDAD"].sum()
    if not agg_refs_units.empty and len(agg_refs_units) > 5:
        p10_refs = agg_refs_units["CANTIDAD"].quantile(0.1)
        baja_rotacion_refs = agg_refs_units[agg_refs_units["CANTIDAD"] <= p10_refs]
        st.write(f"Referencias con baja rotación (≤P10: {p10_refs:.1f} unidades): {len(baja_rotacion_refs)}")
        if not baja_rotacion_refs.empty:
            st.dataframe(baja_rotacion_refs.head(20), use_container_width=True)