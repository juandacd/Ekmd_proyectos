import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import numpy as np

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Comparativo Ventas", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Logo en la esquina superior
top_col1, top_col2 = st.columns([0.7,0.3])
with top_col2:
    st.image("https://ekonomodo.com/cdn/shop/files/Logo-Ekonomodo-color.svg?v=1736956350&width=450", width=5000)

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

def preparar_datos(df_ventas, df_aux, df_comercios, year):
    """Prepara y cruza los datos de ventas"""
    try:
        # Validar columnas requeridas
        if not validate_columns(df_aux, ["NRO. CRUCE", "COMPROBA", "FECHA", "CANT.ENTREGA", "REFERENCIA", "VEND"], f"Auxiliar {year}"):
            return None
        if not validate_columns(df_ventas, ["NRO", "FECHA", "GRAVADAS IVA"], f"Libro de ventas {year}"):
            return None
        if not validate_columns(df_comercios, ["Z", "Nombre"], "Comercios"):
            return None
        
        # Cruzar auxiliar con ventas
        df = pd.merge(df_aux, df_ventas, left_on="NRO. CRUCE", right_on="NRO", how="inner", suffixes=('_aux', '_ventas'))
        
        if df.empty:
            st.warning(f"⚠️ No se encontraron coincidencias entre auxiliar y ventas para {year}")
            return None
        
        # Procesar fechas - buscar la columna que contenga "FECHA" sin otros caracteres
        fecha_col = None
        for col in df.columns:
            col_limpio = col.strip()
            if col_limpio == "FECHA":
                fecha_col = col
                break

        if fecha_col is None:
            # Si no encuentra exactamente "FECHA", buscar la que más se parezca
            for col in df.columns:
                if "FECHA" in col and "PAC" not in col and "ENT" not in col:
                    fecha_col = col
                    break

        if fecha_col is None:
            st.error(f"No se encontró la columna 'FECHA' en auxiliar {year}. Columnas disponibles: {list(df.columns)}")
            return None

        # Usar la fecha del libro de ventas en lugar de auxiliar
        df["FECHA"] = pd.to_datetime(df["FECHA_ventas"], errors="coerce")
        df = df.dropna(subset=["FECHA"])  # Eliminar registros sin fecha válida
        
        # Crear columnas de tiempo
        df["mes"] = df["FECHA"].dt.strftime("%m")  # Solo el número del mes (01, 02, 03...)
        df["mes_nombre"] = df["FECHA"].dt.strftime("%Y-%m")  # Para referencia
        df["año"] = year
        df["mes_num"] = df["FECHA"].dt.month
        df["trimestre"] = df["FECHA"].dt.quarter
        
        # Limpiar códigos de comercios
        df["COMPROBA"] = df["COMPROBA"].astype(str).str.strip()
        df_comercios["Z"] = df_comercios["Z"].astype(str).str.strip()
        
        # Cruzar con comercios
        df = pd.merge(df, df_comercios, left_on="COMPROBA", right_on="Z", how="left")
        
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

# ==============================
# PROCESAMIENTO PRINCIPAL
# ==============================

if all([ventas_2024, aux_2024, ventas_2025, aux_2025, comercios_file]):
    
    with st.spinner("Cargando y procesando archivos..."):
        # Cargar archivos
        df_v24 = load_file(ventas_2024)
        df_a24 = load_file(aux_2024)
        df_v25 = load_file(ventas_2025)
        df_a25 = load_file(aux_2025)
        df_com = load_file(comercios_file)
        
        # Verificar que todos los archivos se cargaron correctamente
        if any(df is None for df in [df_v24, df_a24, df_v25, df_a25, df_com]):
            st.stop()
        
        # Preparar datos
        df2024 = preparar_datos(df_v24, df_a24, df_com, 2024)
        df2025 = preparar_datos(df_v25, df_a25, df_com, 2025)
        
        if df2024 is None or df2025 is None:
            st.stop()
        
        # Unir datos
        df_all = pd.concat([df2024, df2025], ignore_index=True)
        
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
        numero_col: "nunique",
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

    # Métricas de devoluciones
    total_sin_dev_2024 = df_filtrado[(df_filtrado["año"] == 2024) & (df_filtrado["GRAVADAS IVA"] > 0)]["GRAVADAS IVA"].sum()
    total_sin_dev_2025 = df_filtrado[(df_filtrado["año"] == 2025) & (df_filtrado["GRAVADAS IVA"] > 0)]["GRAVADAS IVA"].sum()
    devoluciones_2024 = df_filtrado[(df_filtrado["año"] == 2024) & (df_filtrado["GRAVADAS IVA"] < 0)]["GRAVADAS IVA"].sum()
    devoluciones_2025 = df_filtrado[(df_filtrado["año"] == 2025) & (df_filtrado["GRAVADAS IVA"] < 0)]["GRAVADAS IVA"].sum()

    st.subheader("📊 Desglose de Ventas y Devoluciones")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("💚 Ventas sin devoluciones 2025", f"${total_sin_dev_2025:,.0f}")
    with col2:
        st.metric("💚 Ventas sin devoluciones 2024", f"${total_sin_dev_2024:,.0f}")
    with col3:
        st.metric("🔴 Devoluciones 2025", f"${abs(devoluciones_2025):,.0f}")
    with col4:
        st.metric("🔴 Devoluciones 2024", f"${abs(devoluciones_2024):,.0f}")
    
    # ==============================
    # TABLAS COMPARATIVAS
    # ==============================
    
    st.subheader("📋 Comparativo Mensual - Montos")
    st.dataframe(
        pivot_monto.style.format({
            2024: "${:,.0f}",
            2025: "${:,.0f}",
            "Diferencia": "${:,.0f}",
            "% Cambio": "{:.1f}%"
        }).background_gradient(subset=["% Cambio"], cmap="RdYlGn"),
        use_container_width=True
    )
    
    st.subheader("📋 Comparativo Mensual - Órdenes")
    st.dataframe(
        pivot_ordenes.style.format({
            2024: "{:,.0f}",
            2025: "{:,.0f}",
            "Diferencia": "{:,.0f}",
            "% Cambio": "{:.1f}%"
        }).background_gradient(subset=["% Cambio"], cmap="RdYlGn"),
        use_container_width=True
    )
    
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
    """)
    
    st.markdown("---")
    st.markdown("### ℹ️ Información sobre las columnas requeridas:")
    
    with st.expander("📊 Ventas por facturas emitidas"):
        st.markdown("""
        - **NUMERO**: Número de factura (para cruce con auxiliar)
        - **GRAVADAS IVA**: Valor real de las ventas
        """)
    
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