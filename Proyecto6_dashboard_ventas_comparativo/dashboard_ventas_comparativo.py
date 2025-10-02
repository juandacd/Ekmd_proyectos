import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import numpy as np

# Logo en la esquina superior
top_col1, top_col2 = st.columns([0.7,0.3])
with top_col2:
    st.image("https://ekonomodo.com/cdn/shop/files/Logo-Ekonomodo-color.svg?v=1736956350&width=450", width=5000)

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Comparativo Ventas", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados
st.markdown("""
<style>
.metric-container {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 0.5rem 0;
}
.stAlert > div {
    padding-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard Comparativo de Ventas 2024 vs 2025")
st.markdown("---")

# ==============================
# FUNCIONES AUXILIARES
# ==============================

def clean_column_names(df):
    """Limpia los nombres de las columnas eliminando espacios extra"""
    df.columns = df.columns.str.strip()
    return df

def load_file(file):
    """Carga archivos CSV o Excel con manejo de errores"""
    if file is None:
        return None
    try:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file, encoding='utf-8')
        else:
            df = pd.read_excel(file)
        return clean_column_names(df)
    except Exception as e:
        st.error(f"Error cargando {file.name}: {str(e)}")
        return None

def validate_columns(df, required_cols, file_name):
    """Valida que las columnas requeridas existan en el DataFrame"""
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"❌ {file_name}: Faltan columnas: {missing_cols}")
        st.info(f"Columnas disponibles: {list(df.columns)}")
        return False
    return True

def preparar_datos(df_ventas, df_aux, df_comercios, df_vendedores, year):
    """Prepara y cruza los datos de ventas"""
    try:
        # Validar columnas requeridas
        if not validate_columns(df_aux, ["NRO. CRUCE", "COMPROBA", "C MP. CR", "FECHA", "CANT.ENTREGA", "REFERENCIA", "VEND"], f"Auxiliar {year}"):
            return None
        if not validate_columns(df_ventas, ["NRO", "FECHA", "GRAVADAS IVA"], f"Libro de ventas {year}"):
            return None
        # Hacer auxiliar opcional
        for col in ["NRO. CRUCE", "COMPROBA", "REFERENCIA", "VEND"]:
            if col not in df_aux.columns:
                df_aux[col] = None
        if not validate_columns(df_comercios, ["Z", "Nombre"], "Comercios"):
            return None

        # Validar vendedores (opcional)
        if not validate_columns(df_vendedores, ["VENDEDOR", "NOMBRE"], "Vendedores"):
            st.warning("Archivo de vendedores no válido, se usarán códigos numéricos")
            df_vendedores = None
        
        # Buscar columna C MP. CR en auxiliar ANTES del merge
        cmp_col_aux = None
        for col in df_aux.columns:
            if "C MP" in col.upper() and "CR" in col.upper():
                cmp_col_aux = col
                break

        # Usar Libro de ventas como base principal
        df = pd.merge(df_ventas, df_aux, left_on="NRO", right_on="NRO. CRUCE", how="left", suffixes=('', '_aux'))

        # Si encontramos C MP. CR, verificar que esté en el resultado
        if cmp_col_aux and cmp_col_aux in df.columns:
            st.info(f"✓ Columna '{cmp_col_aux}' encontrada y disponible para clasificar Falabella")
        else:
            st.warning(f"⚠️ Columna C MP. CR no encontrada en el merge. Columnas disponibles: {[c for c in df.columns if 'MP' in c.upper() or 'CR' in c.upper()]}")

        # Eliminar duplicados por NRO, priorizando registros con datos completos
        df = df.sort_values('COMPROBA', na_position='last')
        df = df.drop_duplicates(subset=['NRO'], keep='first')

        # Resetear índice después de eliminar duplicados
        df = df.reset_index(drop=True)

        if df.empty:
            st.warning(f"⚠️ No se encontraron coincidencias entre auxiliar y ventas para {year}")
            return None

        # Usar fecha del libro de ventas directamente
        df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")
        
        df = df.dropna(subset=["FECHA"])
        
        # Crear columnas de tiempo
        df["mes"] = df["FECHA"].dt.strftime("%m")  # Solo el número del mes (01, 02, 03...)
        df["mes_nombre"] = df["FECHA"].dt.strftime("%Y-%m")  # Para referencia
        df["año"] = year
        df["mes_num"] = df["FECHA"].dt.month
        df["trimestre"] = df["FECHA"].dt.quarter
        
        # Limpiar códigos de comercios
        df["COMPROBA"] = df["COMPROBA"].astype(str).str.strip()
        df_comercios["Z"] = df_comercios["Z"].astype(str).str.strip()
        
        # Cruzar con comercios (mantener el cruce original)
        df = pd.merge(df, df_comercios, left_on="COMPROBA", right_on="Z", how="left")

        # Diferenciar Falabella de Falabella Verde basado en C MP. CR
        # Buscar la columna C MP. CR que puede tener espacios
        cmp_col = None
        for col in df.columns:
            if "C MP" in col.upper() and "CR" in col.upper():
                cmp_col = col
                break

        if cmp_col:
            # Identificar registros de Falabella (Z-082 o nombre Falabella)
            mask_falabella = (df["COMPROBA"] == "Z-082") | (df["Nombre"].str.contains("Falabella", case=False, na=False))
            
            if mask_falabella.sum() > 0:
                # Extraer el primer carácter de C MP. CR y convertir a mayúscula
                df.loc[mask_falabella, "prefijo_temp"] = df.loc[mask_falabella, cmp_col].astype(str).str.strip().str[0].str.upper()
                
                # Asignar nombres según el prefijo
                df.loc[mask_falabella & (df["prefijo_temp"] == "F"), "Nombre"] = "Falabella"
                df.loc[mask_falabella & (df["prefijo_temp"] == "S"), "Nombre"] = "Falabella Verde"
                
                # Limpiar columna temporal
                df = df.drop(columns=["prefijo_temp"], errors="ignore")
                
                st.info(f"📊 Procesados {mask_falabella.sum():,} registros de Falabella (F={len(df[(df['Nombre']=='Falabella') & mask_falabella])}, S={len(df[(df['Nombre']=='Falabella Verde') & mask_falabella])})")

        # Buscar la columna NOMBRE del Libro que puede tener espacios
        nombre_col = None
        for col in df.columns:
            if col.strip().upper() == "NOMBRE" and col != "Nombre":  # Evitar confusión con Nombre del comercio
                nombre_col = col
                break

        if nombre_col:
            # Solo mapear registros que NO tienen comercio asignado (principalmente devoluciones)
            def asignar_comercio_por_nombre(nombre_str, cmp_cr=None):
                if pd.isna(nombre_str):
                    return "PARTICULAR"
                
                nombre_upper = str(nombre_str).upper()
                
                if "SODIMAC COLOMBIA" in nombre_upper:
                    return "Homecenter"
                elif "ALMACENES EXITO" in nombre_upper:
                    return "Éxito-Emplea" 
                elif "TUGO" in nombre_upper:
                    return "Tugo"
                elif "ALMACENES MAXIMO" in nombre_upper:
                    return "Maximo"
                elif "APER COLOMBIA" in nombre_upper:
                    return "Aper Colombia"
                elif "FALABELLA" in nombre_upper:
                    # Diferenciar Falabella por C MP. CR si está disponible
                    if pd.notna(cmp_cr):
                        prefijo = str(cmp_cr)[0].upper()
                        if prefijo == "S":
                            return "Falabella Verde"
                        else:
                            return "Falabella"
                    else:
                        return "Falabella"  # Por defecto si no hay C MP. CR
                else:
                    # Buscar coincidencia con nombres de comercios del catálogo Z
                    for _, row in df_comercios.iterrows():
                        if str(row["Nombre"]).upper() in nombre_upper:
                            return row["Nombre"]
                    return "PARTICULAR"

            # Aplicar solo a registros sin comercio asignado
            # Aplicar solo a registros sin comercio asignado
            mask_sin_comercio = pd.isna(df["Nombre"])
            if mask_sin_comercio.sum() > 0:
                # Buscar columna C MP. CR
                cmp_col = None
                for col in df.columns:
                    if col.strip().upper() == "C MP. CR":
                        cmp_col = col
                        break
                
                if cmp_col:
                    df.loc[mask_sin_comercio, "Nombre"] = df.loc[mask_sin_comercio].apply(
                        lambda row: asignar_comercio_por_nombre(row[nombre_col], row[cmp_col]), axis=1
                    )
                else:
                    df.loc[mask_sin_comercio, "Nombre"] = df.loc[mask_sin_comercio, nombre_col].apply(
                        lambda x: asignar_comercio_por_nombre(x, None)
                    )

            # AGREGAR ESTA NORMALIZACIÓN DESPUÉS:
            # Normalizar nombres de comercios para evitar duplicados
            df["Nombre"] = df["Nombre"].astype(str)
            df.loc[df["Nombre"].str.upper() == "PARTICULAR", "Nombre"] = "Particular"
            # Capitalizar correctamente otros nombres comunes
            df.loc[df["Nombre"].str.upper() == "HOMECENTER", "Nombre"] = "Homecenter"
            df.loc[df["Nombre"].str.upper() == "ÉXITO-EMPLEA", "Nombre"] = "Éxito-Emplea"
            df.loc[df["Nombre"].str.upper() == "TUGO", "Nombre"] = "Tugo"
            df.loc[df["Nombre"].str.upper() == "MAXIMO", "Nombre"] = "Maximo"
            df.loc[df["Nombre"].str.upper() == "APER COLOMBIA", "Nombre"] = "Aper Colombia"                
        else:
            st.warning("No se encontró columna NOMBRE en el Libro de ventas para mapear devoluciones")

        # Cruzar con vendedores
        if df_vendedores is not None:
            df_vendedores["VENDEDOR"] = df_vendedores["VENDEDOR"].astype(str).str.strip()
            df["VEND"] = df["VEND"].astype(str).str.strip()
            df = pd.merge(df, df_vendedores, left_on="VEND", right_on="VENDEDOR", how="left", suffixes=('', '_vendedor'))
            df["Nombre_Vendedor"] = df["NOMBRE_vendedor"].fillna(f"Vendedor {df['VEND']}")
        else:
            df["Nombre_Vendedor"] = "Vendedor " + df["VEND"].astype(str)
        
        # Limpiar datos
        df["GRAVADAS IVA"] = pd.to_numeric(df["GRAVADAS IVA"], errors="coerce")
        df["CANT.ENTREGA"] = pd.to_numeric(df["CANT.ENTREGA"], errors="coerce")
        df = df.dropna(subset=["GRAVADAS IVA"])  # Eliminar registros sin valor
        
        # Identificar productos EKM
        df["es_producto_ekm"] = df["REFERENCIA"].astype(str).str.startswith("EKM")
        
        return df
    
    except Exception as e:
        st.error(f"Error procesando datos {year}: {str(e)}")
        return None

# ==============================
# SIDEBAR - SUBIDA DE ARCHIVOS
# ==============================

st.sidebar.header("📁 Cargar Archivos")
st.sidebar.markdown("Sube las 5 bases de datos requeridas:")

ventas_2024 = st.sidebar.file_uploader("📊 Libro de ventas 2024", type=["xlsx", "csv"])
aux_2024 = st.sidebar.file_uploader("📋 Auxiliar por número 2024", type=["xlsx", "csv"])
ventas_2025 = st.sidebar.file_uploader("📊 Libro de ventas 2025", type=["xlsx", "csv"])
aux_2025 = st.sidebar.file_uploader("📋 Auxiliar por número 2025", type=["xlsx", "csv"])
comercios_file = st.sidebar.file_uploader("🏪 Catálogo de Comercios (Z)", type=["xlsx", "csv"])
vendedores_file = st.sidebar.file_uploader("👤 Catálogo de Vendedores", type=["xlsx", "csv"])
ventas_vend_2024 = st.sidebar.file_uploader("📊 Ventas por vendedor 2024", type=["xlsx", "csv"])
dev_vend_2024 = st.sidebar.file_uploader("↩️ Devoluciones por vendedor 2024", type=["xlsx", "csv"])
ventas_vend_2025 = st.sidebar.file_uploader("📊 Ventas por vendedor 2025", type=["xlsx", "csv"])
dev_vend_2025 = st.sidebar.file_uploader("↩️ Devoluciones por vendedor 2025", type=["xlsx", "csv"])

# ==============================
# PROCESAMIENTO PRINCIPAL
# ==============================

if all([ventas_2024, aux_2024, ventas_2025, aux_2025, comercios_file, vendedores_file, 
        ventas_vend_2024, dev_vend_2024, ventas_vend_2025, dev_vend_2025]):

    with st.spinner("Cargando y procesando archivos..."):
        # Cargar archivos
        df_v24 = load_file(ventas_2024)
        df_a24 = load_file(aux_2024)
        df_v25 = load_file(ventas_2025)
        df_a25 = load_file(aux_2025)
        df_com = load_file(comercios_file)
        df_vendedores = load_file(vendedores_file)
        df_ventas_vend_24 = load_file(ventas_vend_2024)
        df_dev_vend_24 = load_file(dev_vend_2024)
        df_ventas_vend_25 = load_file(ventas_vend_2025)
        df_dev_vend_25 = load_file(dev_vend_2025)
        
        # Verificar que todos los archivos se cargaron correctamente
        if any(df is None for df in [df_v24, df_a24, df_v25, df_a25, df_com, 
                                    df_ventas_vend_24, df_dev_vend_24, 
                                    df_ventas_vend_25, df_dev_vend_25]):
            st.stop()
        
        # Preparar datos
        df2024 = preparar_datos(df_v24, df_a24, df_com, df_vendedores, 2024)
        df2025 = preparar_datos(df_v25, df_a25, df_com, df_vendedores, 2025)
        
        if df2024 is None or df2025 is None:
            st.stop()
        
        # Verificar y alinear columnas antes de concatenar
        cols_2024 = set(df2024.columns)
        cols_2025 = set(df2025.columns)
        common_cols = list(cols_2024.intersection(cols_2025))

        # Usar solo las columnas comunes
        df2024_clean = df2024[common_cols].copy().reset_index(drop=True)
        df2025_clean = df2025[common_cols].copy().reset_index(drop=True)

        # Concatenar
        df_all = pd.concat([df2024_clean, df2025_clean], ignore_index=True)

        # st.info(f"Columnas usadas para análisis: {len(common_cols)} columnas comunes")
        
        # Mostrar estadísticas básicas
        st.success(f"✅ Datos procesados exitosamente!")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Registros 2024", f"{len(df2024):,}")
        with col2:
            st.metric("Registros 2025", f"{len(df2025):,}")
        with col3:
            st.metric("Comercios únicos", df_all["Nombre"].nunique())
        with col4:
            st.metric("Productos EKM", df_all[df_all["es_producto_ekm"]]["REFERENCIA"].nunique())

    # ==============================
    # FILTROS
    # ==============================
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros")
    
    # Filtro de comercios
    comercios_disponibles = ["Todos"] + sorted([x for x in df_all["Nombre"].dropna().unique() if str(x) != 'nan'])
    comercio_sel = st.sidebar.selectbox("🏪 Comercio:", comercios_disponibles)
    
    # Filtro de meses
    meses_disponibles = ["Todos"] + sorted(df_all["mes"].unique().tolist())
    mes_sel = st.sidebar.multiselect("📅 Meses:", meses_disponibles, default=["Todos"])
    
    # Filtro de productos EKM
    solo_ekm = st.sidebar.checkbox("🏷️ Solo productos EKM", value=False)
    
    # Aplicar filtros
    df_filtrado = df_all.copy()
    
    if comercio_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Nombre"] == comercio_sel]
    
    if "Todos" not in mes_sel and mes_sel:
        df_filtrado = df_filtrado[df_filtrado["mes"].isin(mes_sel)]
    
    if solo_ekm:
        df_filtrado = df_filtrado[df_filtrado["es_producto_ekm"]]
    
    if df_filtrado.empty:
        st.warning("⚠️ No hay datos para los filtros seleccionados")
        st.stop()

    # ==============================
    # ANÁLISIS Y MÉTRICAS
    # ==============================
    
    st.header("📈 Análisis Comparativo")
    
    # Verificar qué columna usar para contar órdenes únicas
    numero_col = None
    if "NUMERO" in df_filtrado.columns:
        numero_col = "NUMERO"
    elif "NRO. CRUCE" in df_filtrado.columns:
        numero_col = "NRO. CRUCE"
    else:
        st.error("No se encontró columna para contar órdenes (NUMERO o NRO. CRUCE)")
        st.stop()

    resumen_mensual = df_filtrado.groupby(["año", "mes"]).agg({
        "GRAVADAS IVA": "sum",
        "NRO": "nunique",
        "CANT.ENTREGA": "sum",
        "REFERENCIA": "nunique"
    }).round(2).reset_index()

    resumen_mensual.columns = ["año", "mes", "monto_total", "ordenes", "cantidad_total", "productos_unicos"]
    
    resumen_mensual.columns = ["año", "mes", "monto_total", "ordenes", "cantidad_total", "productos_unicos"]
    
    # Pivot para comparación
    pivot_monto = resumen_mensual.pivot(index="mes", columns="año", values="monto_total").fillna(0)
    pivot_ordenes = resumen_mensual.pivot(index="mes", columns="año", values="ordenes").fillna(0)
    pivot_cantidad = resumen_mensual.pivot(index="mes", columns="año", values="cantidad_total").fillna(0)
    
    # Calcular diferencias y porcentajes
    if 2024 in pivot_monto.columns and 2025 in pivot_monto.columns:
        pivot_monto["Diferencia"] = pivot_monto[2025] - pivot_monto[2024]
        pivot_monto["% Cambio"] = ((pivot_monto[2025] - pivot_monto[2024]) / pivot_monto[2024] * 100).round(2)
        pivot_monto["% Cambio"] = pivot_monto["% Cambio"].replace([np.inf, -np.inf], np.nan)
        
        pivot_ordenes["Diferencia"] = pivot_ordenes[2025] - pivot_ordenes[2024]
        pivot_ordenes["% Cambio"] = ((pivot_ordenes[2025] - pivot_ordenes[2024]) / pivot_ordenes[2024] * 100).round(2)
        pivot_ordenes["% Cambio"] = pivot_ordenes["% Cambio"].replace([np.inf, -np.inf], np.nan)
    
    # ==============================
    # MÉTRICAS PRINCIPALES
    # ==============================
    
    total_2024 = df_filtrado[df_filtrado["año"] == 2024]["GRAVADAS IVA"].sum()
    total_2025 = df_filtrado[df_filtrado["año"] == 2025]["GRAVADAS IVA"].sum()
    # Buscar la columna correcta para contar órdenes
    numero_col = None
    for col in df_filtrado.columns:
        if col.startswith("NUMERO"):
            numero_col = col
            break
    if numero_col is None:
        numero_col = "NRO. CRUCE"

    ordenes_2024 = df_filtrado[df_filtrado["año"] == 2024][numero_col].nunique()
    ordenes_2025 = df_filtrado[df_filtrado["año"] == 2025][numero_col].nunique()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Ventas 2025", 
            f"${total_2025:,.0f}",
            delta=f"${total_2025 - total_2024:,.0f}" if total_2024 > 0 else None
        )
    
    with col2:
        st.metric(
            "💰 Ventas 2024", 
            f"${total_2024:,.0f}"
        )
    
    with col3:
        st.metric(
            "📦 Órdenes 2025", 
            f"{ordenes_2025:,}",
            delta=f"{ordenes_2025 - ordenes_2024:,}" if ordenes_2024 > 0 else None
        )
    
    with col4:
        st.metric(
            "📦 Órdenes 2024", 
            f"{ordenes_2024:,}"
        )

        # Métricas detalladas incluyendo descuentos
        ventas_positivas_2024 = df_filtrado[(df_filtrado["año"] == 2024) & (df_filtrado["GRAVADAS IVA"] > 0)]["GRAVADAS IVA"].sum()
        ventas_positivas_2025 = df_filtrado[(df_filtrado["año"] == 2025) & (df_filtrado["GRAVADAS IVA"] > 0)]["GRAVADAS IVA"].sum()
        descuentos_2024 = abs(df_filtrado[(df_filtrado["año"] == 2024) & (df_filtrado["GRAVADAS IVA"] < 0)]["GRAVADAS IVA"].sum())
        descuentos_2025 = abs(df_filtrado[(df_filtrado["año"] == 2025) & (df_filtrado["GRAVADAS IVA"] < 0)]["GRAVADAS IVA"].sum())
   
    st.subheader("💰 Desglose Detallado de Ventas")

    # Primera fila - Ventas brutas
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "✅ Ventas Brutas 2025", 
            f"${ventas_positivas_2025:,.0f}",
            delta=f"${ventas_positivas_2025 - ventas_positivas_2024:,.0f}" if ventas_positivas_2024 > 0 else None
        )
    with col2:
        st.metric("✅ Ventas Brutas 2024", f"${ventas_positivas_2024:,.0f}")

    # Segunda fila - Descuentos
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "❌ Devoluciones 2025", 
            f"${descuentos_2025:,.0f}",
            delta=f"${descuentos_2025 - descuentos_2024:,.0f}" if descuentos_2024 > 0 else None
        )
    with col2:
        st.metric("❌ Devoluciones 2024", f"${descuentos_2024:,.0f}")
    
    # ==============================
    # TABLAS COMPARATIVAS
    # ==============================
    
    st.subheader("📋 Comparativo Mensual - Montos")

    # Verificar qué columnas existen para el formato
    format_dict = {}
    if 2024 in pivot_monto.columns:
        format_dict[2024] = "${:,.0f}"
    if 2025 in pivot_monto.columns:
        format_dict[2025] = "${:,.0f}"
    if "Diferencia" in pivot_monto.columns:
        format_dict["Diferencia"] = "${:,.0f}"
    if "% Cambio" in pivot_monto.columns:
        format_dict["% Cambio"] = "{:.1f}%"

    # Aplicar formato solo si hay columnas de % Cambio
    if "% Cambio" in pivot_monto.columns:
        st.dataframe(
            pivot_monto.style.format(format_dict).background_gradient(subset=["% Cambio"], cmap="RdYlGn"),
            use_container_width=True
        )
    else:
        st.dataframe(
            pivot_monto.style.format(format_dict),
            use_container_width=True
        )
    
    st.subheader("📋 Comparativo Mensual - Órdenes")

    # Verificar qué columnas existen para el formato
    format_dict_ordenes = {}
    if 2024 in pivot_ordenes.columns:
        format_dict_ordenes[2024] = "{:,.0f}"
    if 2025 in pivot_ordenes.columns:
        format_dict_ordenes[2025] = "{:,.0f}"
    if "Diferencia" in pivot_ordenes.columns:
        format_dict_ordenes["Diferencia"] = "{:,.0f}"
    if "% Cambio" in pivot_ordenes.columns:
        format_dict_ordenes["% Cambio"] = "{:.1f}%"

    # Aplicar formato solo si hay columnas de % Cambio
    if "% Cambio" in pivot_ordenes.columns:
        st.dataframe(
            pivot_ordenes.style.format(format_dict_ordenes).background_gradient(subset=["% Cambio"], cmap="RdYlGn"),
            use_container_width=True
        )
    else:
        st.dataframe(
            pivot_ordenes.style.format(format_dict_ordenes),
            use_container_width=True
        )
    
    # ==============================
    # ANÁLISIS DETALLADO DE DEVOLUCIONES
    # ==============================

    st.subheader("🔍 Análisis Detallado de Devoluciones")

    # Crear tabs para diferentes vistas
    tab1, tab2, tab3 = st.tabs(["📊 Resumen", "📋 Detalle por Mes", "🏪 Detalle por Comercio"])

    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Devoluciones 2025**")
            devoluciones_count_2025 = len(df_filtrado[(df_filtrado["año"] == 2025) & (df_filtrado["GRAVADAS IVA"] < 0)])
            st.metric("Cantidad de devoluciones", f"{devoluciones_count_2025:,}")
            if total_2025 != 0:
                porcentaje_dev_2025 = (descuentos_2025 / abs(total_2025 + descuentos_2025)) * 100
                st.metric("% sobre ventas brutas", f"{porcentaje_dev_2025:.2f}%")
        
        with col2:
            st.markdown("**Devoluciones 2024**")
            devoluciones_count_2024 = len(df_filtrado[(df_filtrado["año"] == 2024) & (df_filtrado["GRAVADAS IVA"] < 0)])
            st.metric("Cantidad de devoluciones", f"{devoluciones_count_2024:,}")
            if total_2024 != 0:
                porcentaje_dev_2024 = (descuentos_2024 / abs(total_2024 + descuentos_2024)) * 100
                st.metric("% sobre ventas brutas", f"{porcentaje_dev_2024:.2f}%")

    with tab2:
        # Devoluciones por mes
        devoluciones_mes = df_filtrado[df_filtrado["GRAVADAS IVA"] < 0].groupby(["año", "mes"]).agg({
            "GRAVADAS IVA": ["sum", "count"],
            "NRO": "nunique"
        }).round(2).reset_index()
        
        devoluciones_mes.columns = ["año", "mes", "monto_devolucion", "cantidad_registros", "facturas_unicas"]
        devoluciones_mes["monto_devolucion"] = abs(devoluciones_mes["monto_devolucion"])
        
        if not devoluciones_mes.empty:
            pivot_dev = devoluciones_mes.pivot(index="mes", columns="año", values="monto_devolucion").fillna(0)
            st.dataframe(
                pivot_dev.style.format("${:,.0f}"),
                use_container_width=True
            )
        else:
            st.info("No hay devoluciones en el período/filtro seleccionado")

    with tab3:
        # Devoluciones por comercio (solo si no hay filtro de comercio)
        if comercio_sel == "Todos":
            dev_comercio = df_filtrado[df_filtrado["GRAVADAS IVA"] < 0].groupby(["Nombre", "año"]).agg({
                "GRAVADAS IVA": ["sum", "count"]
            }).round(2).reset_index()
            
            dev_comercio.columns = ["Comercio", "año", "monto_devolucion", "cantidad"]
            dev_comercio["monto_devolucion"] = abs(dev_comercio["monto_devolucion"])
            
            if not dev_comercio.empty:
                pivot_dev_comercio = dev_comercio.pivot(index="Comercio", columns="año", values="monto_devolucion").fillna(0)
                st.dataframe(
                    pivot_dev_comercio.style.format("${:,.0f}"),
                    use_container_width=True
                )
            else:
                st.info("No hay devoluciones por comercio en el período seleccionado")
        else:
            # Mostrar devoluciones del comercio seleccionado por mes
            dev_comercio_detalle = df_filtrado[df_filtrado["GRAVADAS IVA"] < 0]
            if not dev_comercio_detalle.empty:
                st.dataframe(
                    dev_comercio_detalle[["mes_nombre", "NRO", "GRAVADAS IVA", "REFERENCIA"]].sort_values("mes_nombre"),
                    use_container_width=True
                )
            else:
                st.info(f"No hay devoluciones registradas para {comercio_sel}")     

    # ==============================
    # GRÁFICOS
    # ==============================
    
    st.subheader("📊 Visualizaciones")
    
    # Configurar estilo de matplotlib
    plt.style.use('default')
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if 2024 in pivot_monto.columns and 2025 in pivot_monto.columns:
            x_pos = range(len(pivot_monto.index))
            width = 0.35
            
            bars1 = ax.bar([x - width/2 for x in x_pos], pivot_monto[2024], width, label='2024', alpha=0.8, color='#1f77b4')
            bars2 = ax.bar([x + width/2 for x in x_pos], pivot_monto[2025], width, label='2025', alpha=0.8, color='#ff7f0e')
            
            ax.set_xlabel('Mes')
            ax.set_ylabel('Monto Total ($)')
            ax.set_title('Comparativo de Ventas por Mes')
            ax.set_xticks(x_pos)
            ax.set_xticklabels(pivot_monto.index, rotation=45)
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
            
            # Agregar valores en las barras
            for bar in bars1:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height, f'${height:,.0f}',
                       ha='center', va='bottom', fontsize=8, rotation=90)
            
            for bar in bars2:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height, f'${height:,.0f}',
                       ha='center', va='bottom', fontsize=8, rotation=90)
        
        plt.tight_layout()
        st.pyplot(fig)
    
    with col2:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if 2024 in pivot_ordenes.columns and 2025 in pivot_ordenes.columns:
            x_pos = range(len(pivot_ordenes.index))
            width = 0.35
            
            bars1 = ax.bar([x - width/2 for x in x_pos], pivot_ordenes[2024], width, label='2024', alpha=0.8, color='#2ca02c')
            bars2 = ax.bar([x + width/2 for x in x_pos], pivot_ordenes[2025], width, label='2025', alpha=0.8, color='#d62728')
            
            ax.set_xlabel('Mes')
            ax.set_ylabel('Número de Órdenes')
            ax.set_title('Comparativo de Órdenes por Mes')
            ax.set_xticks(x_pos)
            ax.set_xticklabels(pivot_ordenes.index, rotation=45)
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
            
            # Agregar valores en las barras
            for bar in bars1:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}',
                       ha='center', va='bottom', fontsize=8)
            
            for bar in bars2:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}',
                       ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        st.pyplot(fig)
    
    # Gráfico de tendencias
    col1, col2 = st.columns(2)
    
    with col1:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if 2024 in pivot_monto.columns and 2025 in pivot_monto.columns:
            ax.plot(range(len(pivot_monto.index)), pivot_monto[2024], marker='o', linewidth=2, markersize=8, label='2024', color='#1f77b4')
            ax.plot(range(len(pivot_monto.index)), pivot_monto[2025], marker='s', linewidth=2, markersize=8, label='2025', color='#ff7f0e')
            
            ax.set_xlabel('Mes')
            ax.set_ylabel('Monto Total ($)')
            ax.set_title('Tendencia de Ventas')
            ax.set_xticks(range(len(pivot_monto.index)))
            ax.set_xticklabels(pivot_monto.index, rotation=45)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Formato del eje Y
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        plt.tight_layout()
        st.pyplot(fig)
    
    with col2:
        # Gráfico de % de cambio
        if "% Cambio" in pivot_monto.columns:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            colors = ['green' if x > 0 else 'red' for x in pivot_monto["% Cambio"].fillna(0)]
            bars = ax.bar(range(len(pivot_monto.index)), pivot_monto["% Cambio"].fillna(0), color=colors, alpha=0.7)
            
            ax.set_xlabel('Mes')
            ax.set_ylabel('% de Cambio')
            ax.set_title('Variación Porcentual 2025 vs 2024')
            ax.set_xticks(range(len(pivot_monto.index)))
            ax.set_xticklabels(pivot_monto.index, rotation=45)
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax.grid(axis='y', alpha=0.3)
            
            # Agregar valores en las barras
            for i, bar in enumerate(bars):
                height = bar.get_height()
                if not np.isnan(height):
                    ax.text(bar.get_x() + bar.get_width()/2., height + (1 if height >= 0 else -3),
                           f'{height:.1f}%', ha='center', va='bottom' if height >= 0 else 'top', fontsize=9)
            
            plt.tight_layout()
            st.pyplot(fig)
    
    # ==============================
    # ANÁLISIS POR COMERCIOS
    # ==============================
    
    if comercio_sel == "Todos":
        st.subheader("🏪 Análisis por Comercios")
        
        comercios_resumen = df_filtrado.groupby(["Nombre", "año"]).agg({
            "GRAVADAS IVA": "sum",
            "NUMERO": "nunique"
        }).reset_index()
        
        comercios_pivot = comercios_resumen.pivot(index="Nombre", columns="año", values="GRAVADAS IVA").fillna(0)
        
        if 2024 in comercios_pivot.columns and 2025 in comercios_pivot.columns:
            comercios_pivot["Diferencia"] = comercios_pivot[2025] - comercios_pivot[2024]
            comercios_pivot["% Cambio"] = ((comercios_pivot[2025] - comercios_pivot[2024]) / comercios_pivot[2024] * 100).round(2)
            comercios_pivot["% Cambio"] = comercios_pivot["% Cambio"].replace([np.inf, -np.inf], np.nan)
            
            st.dataframe(
                comercios_pivot.style.format({
                    2024: "${:,.0f}",
                    2025: "${:,.0f}",
                    "Diferencia": "${:,.0f}",
                    "% Cambio": "{:.1f}%"
                }).background_gradient(subset=["% Cambio"], cmap="RdYlGn"),
                use_container_width=True
            )

    # ==============================
    # ANÁLISIS POR VENDEDORES
    # ==============================

    st.subheader("👤 Análisis por Vendedores")

    # Preparar datos de vendedores 2024
    ventas_vend_24_prep = df_ventas_vend_24.copy()
    ventas_vend_24_prep["año"] = 2024
    ventas_vend_24_prep["tipo"] = "venta"
    ventas_vend_24_prep = ventas_vend_24_prep.rename(columns={"CODI": "COD_VENDEDOR", "VALOR VENTA": "VALOR"})

    dev_vend_24_prep = df_dev_vend_24.copy()
    dev_vend_24_prep["año"] = 2024
    dev_vend_24_prep["tipo"] = "devolucion"
    dev_vend_24_prep = dev_vend_24_prep.rename(columns={"COD.VEND": "COD_VENDEDOR"})

    # Preparar datos de vendedores 2025
    ventas_vend_25_prep = df_ventas_vend_25.copy()
    ventas_vend_25_prep["año"] = 2025
    ventas_vend_25_prep["tipo"] = "venta"
    ventas_vend_25_prep = ventas_vend_25_prep.rename(columns={"CODI": "COD_VENDEDOR", "VALOR VENTA": "VALOR"})

    dev_vend_25_prep = df_dev_vend_25.copy()
    dev_vend_25_prep["año"] = 2025
    dev_vend_25_prep["tipo"] = "devolucion"
    dev_vend_25_prep = dev_vend_25_prep.rename(columns={"COD.VEND": "COD_VENDEDOR"})

    # Consolidar datos
    df_vendedores_all = pd.concat([
        ventas_vend_24_prep[["COD_VENDEDOR", "año", "VALOR", "tipo"]],
        dev_vend_24_prep[["COD_VENDEDOR", "año", "VALOR", "tipo"]],
        ventas_vend_25_prep[["COD_VENDEDOR", "año", "VALOR", "tipo"]],
        dev_vend_25_prep[["COD_VENDEDOR", "año", "VALOR", "tipo"]]
    ], ignore_index=True)

    # Cruzar con nombres de vendedores
    df_vendedores_all["COD_VENDEDOR"] = df_vendedores_all["COD_VENDEDOR"].astype(str).str.strip()
    if df_vendedores is not None:
        df_vendedores["VENDEDOR"] = df_vendedores["VENDEDOR"].astype(str).str.strip()
        df_vendedores_all = pd.merge(
            df_vendedores_all, 
            df_vendedores[["VENDEDOR", "NOMBRE"]], 
            left_on="COD_VENDEDOR", 
            right_on="VENDEDOR", 
            how="left"
        )
        df_vendedores_all["Nombre_Vendedor"] = df_vendedores_all["NOMBRE"].fillna("Vendedor " + df_vendedores_all["COD_VENDEDOR"])
    else:
        df_vendedores_all["Nombre_Vendedor"] = "Vendedor " + df_vendedores_all["COD_VENDEDOR"]

    # Calcular resumen por vendedor
    resumen_vendedores = df_vendedores_all.groupby(["Nombre_Vendedor", "año", "tipo"]).agg({
        "VALOR": "sum"
    }).reset_index()

    # Pivot para separar ventas y devoluciones
    resumen_pivot = resumen_vendedores.pivot_table(
        index=["Nombre_Vendedor", "año"],
        columns="tipo",
        values="VALOR",
        fill_value=0
    ).reset_index()

    # Calcular ventas netas
    resumen_pivot["ventas_netas"] = resumen_pivot.get("venta", 0) - resumen_pivot.get("devolucion", 0)

    # Top vendedores por año
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Top 10 Vendedores 2025 (Ventas Netas)**")
        top_2025 = resumen_pivot[resumen_pivot["año"] == 2025].sort_values("ventas_netas", ascending=False).head(10)
        if not top_2025.empty:
            display_2025 = top_2025[["Nombre_Vendedor", "venta", "devolucion", "ventas_netas"]].copy()
            display_2025.columns = ["Vendedor", "Ventas Brutas", "Devoluciones", "Ventas Netas"]
            st.dataframe(
                display_2025.style.format({
                    "Ventas Brutas": "${:,.0f}",
                    "Devoluciones": "${:,.0f}",
                    "Ventas Netas": "${:,.0f}"
                }),
                use_container_width=True
            )
        else:
            st.info("No hay datos de vendedores para 2025")

    with col2:
        st.markdown("**Top 10 Vendedores 2024 (Ventas Netas)**")
        top_2024 = resumen_pivot[resumen_pivot["año"] == 2024].sort_values("ventas_netas", ascending=False).head(10)
        if not top_2024.empty:
            display_2024 = top_2024[["Nombre_Vendedor", "venta", "devolucion", "ventas_netas"]].copy()
            display_2024.columns = ["Vendedor", "Ventas Brutas", "Devoluciones", "Ventas Netas"]
            st.dataframe(
                display_2024.style.format({
                    "Ventas Brutas": "${:,.0f}",
                    "Devoluciones": "${:,.0f}",
                    "Ventas Netas": "${:,.0f}"
                }),
                use_container_width=True
            )
        else:
            st.info("No hay datos de vendedores para 2024")

    # Comparativo año contra año
    st.markdown("**Comparativo 2024 vs 2025 (Vendedores presentes ambos años)**")

    # Crear pivots por año
    pivot_2024 = resumen_pivot[resumen_pivot["año"] == 2024].set_index("Nombre_Vendedor")[["ventas_netas"]]
    pivot_2024.columns = [2024]

    pivot_2025 = resumen_pivot[resumen_pivot["año"] == 2025].set_index("Nombre_Vendedor")[["ventas_netas"]]
    pivot_2025.columns = [2025]

    # Combinar
    comparativo_vendedores = pd.merge(pivot_2024, pivot_2025, left_index=True, right_index=True, how="inner")

    if not comparativo_vendedores.empty:
        comparativo_vendedores["Diferencia"] = comparativo_vendedores[2025] - comparativo_vendedores[2024]
        comparativo_vendedores["% Cambio"] = ((comparativo_vendedores[2025] - comparativo_vendedores[2024]) / comparativo_vendedores[2024] * 100).round(2)
        comparativo_vendedores["% Cambio"] = comparativo_vendedores["% Cambio"].replace([np.inf, -np.inf], np.nan)
        
        st.dataframe(
            comparativo_vendedores.sort_values("% Cambio", ascending=False).head(20).style.format({
                2024: "${:,.0f}",
                2025: "${:,.0f}",
                "Diferencia": "${:,.0f}",
                "% Cambio": "{:.1f}%"
            }).background_gradient(subset=["% Cambio"], cmap="RdYlGn"),
            use_container_width=True
        )
    else:
        st.info("No hay vendedores con datos en ambos años para comparar")
    
    # ==============================
    # DATOS DETALLADOS
    # ==============================
    
    with st.expander("📋 Ver datos detallados"):
        st.subheader("Datos filtrados")
        st.dataframe(
            df_filtrado[["año", "mes", "Nombre", "REFERENCIA", "GRAVADAS IVA", "NUMERO", "CANT.ENTREGA", "VEND"]].head(1000),
            use_container_width=True
        )
        
        st.download_button(
            label="📥 Descargar datos filtrados (CSV)",
            data=df_filtrado.to_csv(index=False).encode('utf-8'),
            file_name=f'ventas_filtradas_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
            mime='text/csv'
        )

else:
    st.info("👆 **Sube los 5 archivos requeridos para generar el análisis comparativo:**")
    st.markdown("""
    1. **Ventas por facturas emitidas 2024** (Excel/CSV)
    2. **Auxiliar por número 2024** (Excel/CSV) 
    3. **Ventas por facturas emitidas 2025** (Excel/CSV)
    4. **Auxiliar por número 2025** (Excel/CSV)
    5. **Catálogo de Comercios (Z)** (Excel/CSV)
    6. **Catálogo de Vendedores** (Excel/CSV)
    7. **Ventas por vendedor 2024** (Excel/CSV)
    8. **Devoluciones por vendedor 2024** (Excel/CSV)
    9. **Ventas por vendedor 2025** (Excel/CSV)
    10. **Devoluciones por vendedor 2025** (Excel/CSV)
    """)
    
    st.markdown("---")
    st.markdown("### ℹ️ Información sobre las columnas requeridas:")  
    
    with st.expander("📋 Auxiliar por número"):
        st.markdown("""
        - **NRO. CRUCE**: Número de factura (para cruce con ventas)
        - **COMPROBA**: Código del comercio (Z-001, Z-002, etc.)
        - **FECHA**: Fecha de la transacción
        - **CANT.ENTREGA**: Cantidad entregada del producto
        - **REFERENCIA**: Código único del producto (EKMxxx)
        - **VEN**: Número del vendedor
        """)
    
    with st.expander("🏪 Catálogo de Comercios (Z)"):
        st.markdown("""
        - **Z**: Código del comercio (para cruce con COMPROBA)
        - **Nombre**: Nombre del comercio (Sodimac, Falabella, etc.)
        """)

    with st.expander("📊 Libro de ventas"):
        st.markdown("""
        - **NRO**: Número de factura (para cruce con auxiliar)
        - **FECHA**: Fecha de la transacción
        - **GRAVADAS IVA**: Valor de la venta (positivo=venta, negativo=descuento)
        """)

with st.expander("👤 Catálogo de Vendedores"):
    st.markdown("""
    - **VENDEDOR**: Código del vendedor (para cruce con VEND)
    - **NOMBRE**: Nombre del vendedor
    """)