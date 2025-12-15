import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday
from pandas.tseries.offsets import CustomBusinessDay

# Logo en la esquina superior
top_col1, top_col2 = st.columns([0.7,0.3])
with top_col2:
    st.image("https://ekonomodo.com/cdn/shop/files/Logo-Ekonomodo-color.svg?v=1736956350&width=450", width=5000)

# Configuración de la página
st.set_page_config(
    page_title="Control Ekonomodo",
    page_icon="📦",
    layout="wide"
)

@st.cache_data(ttl=300)  # Cache por 5 minutos
def cargar_datos(sheet_url):
    """Carga los datos desde Google Sheets"""
    try:
        # Convertir URL a formato CSV export
        sheet_id = sheet_url.split('/d/')[1].split('/')[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=1456329364"
        
        df = pd.read_csv(csv_url, header=1)
        
        # Normalizar nombres de columnas
        df = df.rename(columns={
            'COMERCIAL ORDEN': 'ORDEN',
            'PRODUCCION ESTATUS': 'ESTATUS'
        })

        # Convertir ORDEN a string
        df['ORDEN'] = df['ORDEN'].astype(str)
        
        # Convertir fechas
        df['FECHA DE VENTA'] = pd.to_datetime(df['FECHA DE VENTA'], format='%d/%m/%Y', errors='coerce')
        df['FECHA DE VENCIMIENTO'] = pd.to_datetime(df['FECHA DE VENCIMIENTO'], format='%d/%m/%Y', errors='coerce')

        # Limpiar y normalizar datos
        df['ORDEN'] = df['ORDEN'].astype(str).str.strip().str.upper()
        df['ESTATUS'] = df['ESTATUS'].astype(str).str.strip().str.upper()
        df['ESTATUS LOGISTICA'] = df['ESTATUS LOGISTICA'].astype(str).str.strip().str.upper()
        df['CUENTA'] = df['CUENTA'].astype(str).str.strip()
        df['EKM'] = df['EKM'].astype(str).str.strip()

        # DIAGNÓSTICO - Temporal para ver qué hay en los datos
        st.sidebar.write("🔍 Diagnóstico de datos:")
        st.sidebar.write(f"Total filas cargadas: {len(df)}")
        st.sidebar.write(f"Conteo por ESTATUS:")
        st.sidebar.write(df['ESTATUS'].value_counts())

        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return None
    
@st.cache_data(ttl=300)
def cargar_estatus(sheet_url):
    """Carga los datos de la hoja Estatus"""
    try:
        sheet_id = sheet_url.split('/d/')[1].split('/')[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Estatus"
        
        df_estatus = pd.read_csv(csv_url)
        
        # Renombrar columnas para que sea más fácil trabajar
        df_estatus = df_estatus.rename(columns={
            'Marca temporal': 'FECHA_ENTREGA',
            'N° Orden': 'ORDEN'
        })

        # Convertir ORDEN a entero primero (elimina .0) y luego a string
        df_estatus['ORDEN'] = df_estatus['ORDEN'].fillna(0).astype(float).astype(int).astype(str)
        
        # Convertir fecha de entrega a datetime (pandas lo detectará automáticamente)
        df_estatus['FECHA_ENTREGA'] = pd.to_datetime(df_estatus['FECHA_ENTREGA'], format='mixed', dayfirst=True, errors='coerce')
        
        return df_estatus
    except Exception as e:
        st.error(f"Error al cargar estatus: {str(e)}")
        return None
    
def dias_habiles_colombia(fecha_inicio, dias_habiles_objetivo):
    """
    Calcula la fecha después de X días hábiles en Colombia (excluyendo fines de semana y festivos)
    """
    cal = ColombiaHolidayCalendar()
    fecha_actual = pd.Timestamp(fecha_inicio)
    dias_contados = 0
    
    while dias_contados < dias_habiles_objetivo:
        fecha_actual += timedelta(days=1)
        # Si es día hábil (no fin de semana ni festivo)
        if fecha_actual.weekday() < 5 and fecha_actual not in cal.holidays():
            dias_contados += 1
    
    return fecha_actual

class ColombiaHolidayCalendar(AbstractHolidayCalendar):
    """Calendario de festivos de Colombia"""
    rules = [
        # Festivos fijos
        Holiday('Año Nuevo', month=1, day=1),
        Holiday('Día del Trabajo', month=5, day=1),
        Holiday('Día de la Independencia', month=7, day=20),
        Holiday('Batalla de Boyacá', month=8, day=7),
        Holiday('Inmaculada Concepción', month=12, day=8),
        Holiday('Navidad', month=12, day=25),
        
        # Festivos 2024
        Holiday('Reyes Magos 2024', month=1, day=8, year=2024),
        Holiday('San José 2024', month=3, day=25, year=2024),
        Holiday('Jueves Santo 2024', month=3, day=28, year=2024),
        Holiday('Viernes Santo 2024', month=3, day=29, year=2024),
        Holiday('Ascensión 2024', month=5, day=13, year=2024),
        Holiday('Corpus Christi 2024', month=6, day=3, year=2024),
        Holiday('Sagrado Corazón 2024', month=6, day=10, year=2024),
        Holiday('San Pedro y San Pablo 2024', month=7, day=1, year=2024),
        Holiday('Asunción 2024', month=8, day=19, year=2024),
        Holiday('Día de la Raza 2024', month=10, day=14, year=2024),
        Holiday('Todos los Santos 2024', month=11, day=4, year=2024),
        Holiday('Independencia de Cartagena 2024', month=11, day=11, year=2024),
        
        # Festivos 2025
        Holiday('Reyes Magos 2025', month=1, day=6, year=2025),
        Holiday('San José 2025', month=3, day=24, year=2025),
        Holiday('Jueves Santo 2025', month=4, day=17, year=2025),
        Holiday('Viernes Santo 2025', month=4, day=18, year=2025),
        Holiday('Ascensión 2025', month=6, day=2, year=2025),
        Holiday('Corpus Christi 2025', month=6, day=23, year=2025),
        Holiday('Sagrado Corazón 2025', month=6, day=30, year=2025),
        Holiday('San Pedro y San Pablo 2025', month=6, day=30, year=2025),
        Holiday('Asunción 2025', month=8, day=18, year=2025),
        Holiday('Día de la Raza 2025', month=10, day=13, year=2025),
        Holiday('Todos los Santos 2025', month=11, day=3, year=2025),
        Holiday('Independencia de Cartagena 2025', month=11, day=17, year=2025),
    ]

def calcular_dias_habiles(fecha_inicio, fecha_fin):
    """
    Calcula días hábiles entre dos fechas excluyendo fines de semana y festivos colombianos
    """
    if pd.isna(fecha_inicio) or pd.isna(fecha_fin):
        return None
    
    # Crear calendario colombiano
    cal = ColombiaHolidayCalendar()
    
    # Crear rango de días hábiles
    dias_habiles = pd.bdate_range(
        start=fecha_inicio,
        end=fecha_fin,
        freq=CustomBusinessDay(calendar=cal)
    )
    
    return len(dias_habiles)

# Título principal
st.title("Control de Producción y Logística - Ekonomodo")

st.sidebar.header("⚙️ Configuración")
# URL fija del Google Sheet de Control
sheet_url = "https://docs.google.com/spreadsheets/d/1xx9zB70fxzl0YyXkh5o0tIs_eCxpHYQaS8oesyTuUEs/edit#gid=1456329364"

if sheet_url:
    try:
        df = cargar_datos(sheet_url)
        df_estatus = cargar_estatus(sheet_url)
        
        if df is not None and not df.empty:
            # Filtrar por último mes
            fecha_actual = datetime.now()
            fecha_mes_atras = fecha_actual - timedelta(days=30)
            df_ultimo_mes = df[df['FECHA DE VENTA'] >= fecha_mes_atras]

            # Cruzar con datos de entrega y calcular días de producción
            if df_estatus is not None:
                
                # Tomar solo la última entrega por orden (por si hay múltiples registros)
                df_estatus_ultimo = df_estatus.groupby('ORDEN').agg({
                    'FECHA_ENTREGA': 'max'
                }).reset_index()
                
                # Cruzar datos
                df_ultimo_mes = df_ultimo_mes.merge(
                    df_estatus_ultimo, 
                    on='ORDEN', 
                    how='left'
                )
                
            # Calcular días de producción en días hábiles (solo para órdenes con fecha de entrega)
            df_ultimo_mes['DIAS_PRODUCCION'] = None
            mask = df_ultimo_mes['FECHA_ENTREGA'].notna() & df_ultimo_mes['FECHA DE VENTA'].notna()

            # Calcular días hábiles para cada orden
            for idx in df_ultimo_mes[mask].index:
                dias = calcular_dias_habiles(
                    df_ultimo_mes.loc[idx, 'FECHA DE VENTA'],
                    df_ultimo_mes.loc[idx, 'FECHA_ENTREGA']
                )
                df_ultimo_mes.loc[idx, 'DIAS_PRODUCCION'] = dias
            
            # ==== ALERTAS PRINCIPALES ====
            st.header("🚨 Alertas Importantes")
            
            col1, col2, col3 = st.columns(3)
            
            # Alerta: Próximos a vencer en 2 días hábiles
            fecha_limite = dias_habiles_colombia(fecha_actual, 2)
            proximos_vencer = df_ultimo_mes[
                (df_ultimo_mes['FECHA DE VENCIMIENTO'] <= fecha_limite) & 
                (df_ultimo_mes['FECHA DE VENCIMIENTO'] >= fecha_actual) &
                (df_ultimo_mes['ESTATUS'] == 'PRODUCCION')
            ]
            
            with col1:
                if len(proximos_vencer) > 0:
                    st.error(f"⚠️ {len(proximos_vencer)} órdenes vencen en 2 días hábiles")
                    with st.expander("Ver detalles"):
                        st.dataframe(
                            proximos_vencer[['ORDEN', 'CUENTA', 'DESCRIPCION PLATAFORMA', 
                                           'FECHA DE VENCIMIENTO', 'ESTATUS']],
                            hide_index=True
                        )
                else:
                    st.success("✅ No hay órdenes próximas a vencer")
            
            # Alerta: Devoluciones
            devoluciones = df_ultimo_mes[df_ultimo_mes['ESTATUS LOGISTICA'] == 'DEVOLUCION']
            
            with col2:
                if len(devoluciones) > 0:
                    st.error(f"🔄 {len(devoluciones)} devoluciones pendientes")
                    with st.expander("Ver detalles"):
                        st.dataframe(
                            devoluciones[['ORDEN', 'CUENTA', 'DESCRIPCION PLATAFORMA', 'EKM']],
                            hide_index=True
                        )
                else:
                    st.success("✅ No hay devoluciones")

            # Alerta: Pendientes de despacho en logística
            pendientes_despacho = df_ultimo_mes[
                (df_ultimo_mes['ESTATUS'] == 'LOGISTICA') & 
                (~df_ultimo_mes['LOGISTICA'].isin(['ENTREGADO', 'DESPACHADO']))
            ]

            with col3:  # o col4 si añades una columna más
                if len(pendientes_despacho) > 0:
                    st.warning(f"📦 {len(pendientes_despacho)} órdenes pendientes de despachar")
                    with st.expander("Ver detalles"):
                        st.dataframe(
                            pendientes_despacho[['ORDEN', 'CUENTA', 'DESCRIPCION PLATAFORMA', 
                                                'CANTIDAD', 'LOGISTICA']],
                            hide_index=True
                        )
                else:
                    st.success("✅ Todo despachado")

            # Alerta: Órdenes vencidas
            vencidas = df_ultimo_mes[
                (df_ultimo_mes['FECHA DE VENCIMIENTO'] < fecha_actual) &
                (df_ultimo_mes['ESTATUS'] == 'PRODUCCION')
            ]

            # Nueva fila de alertas
            col4, col5, col6 = st.columns(3)

            # Alerta: Entregados pero no recibidos en logística
            entregados_no_recibidos = df_ultimo_mes[
                (df_ultimo_mes['ESTATUS'] == 'ENTREGADO') & 
                (df_ultimo_mes['ESTATUS LOGISTICA'].isna() | (df_ultimo_mes['ESTATUS LOGISTICA'] == '') | (df_ultimo_mes['ESTATUS LOGISTICA'] == 'NAN'))
            ]

            with col4:
                if len(entregados_no_recibidos) > 0:
                    st.warning(f"⚠️ {len(entregados_no_recibidos)} entregados sin recibir en logística")
                    with st.expander("Ver detalles"):
                        st.dataframe(
                            entregados_no_recibidos[['ORDEN', 'CUENTA', 'DESCRIPCION PLATAFORMA', 'CANTIDAD', 'EKM']],
                            hide_index=True
                        )
                else:
                    st.success("✅ Todos los entregados recibidos")

            with col5:
                if len(vencidas) > 0:
                    st.error(f"🔴 {len(vencidas)} órdenes VENCIDAS")
                    with st.expander("Ver detalles"):
                        # Calcular días de tardanza en días hábiles para las vencidas
                        vencidas_display = vencidas.copy()
                        vencidas_display['DIAS_TARDANZA'] = vencidas_display.apply(
                            lambda row: calcular_dias_habiles(row['FECHA DE VENTA'], fecha_actual),
                            axis=1
                        )
                        
                        # Crear función para colorear las celdas
                        def colorear_tardanza(val):
                            if pd.isna(val):
                                return ''
                            if val <= 7:
                                return 'background-color: #90EE90'  # Verde claro
                            elif val <= 14:
                                return 'background-color: #FFD700'  # Amarillo
                            elif val <= 21:
                                return 'background-color: #FFA500'  # Naranja
                            else:
                                return 'background-color: #FF6B6B'  # Rojo claro
                        
                        # Mostrar dataframe con estilo
                        styled_df = vencidas_display[['ORDEN', 'CUENTA', 'DESCRIPCION PLATAFORMA', 
                                'FECHA DE VENCIMIENTO', 'ESTATUS', 'DIAS_TARDANZA']].style.map(
                                    colorear_tardanza, subset=['DIAS_TARDANZA']
                                )
                        
                        st.dataframe(styled_df, hide_index=True, use_container_width=True)
                else:
                    st.success("✅ No hay órdenes vencidas")
            
            st.divider()
            
            # ==== MÉTRICAS GENERALES ====
            st.header("📊 Resumen del Último Mes")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Total Órdenes", len(df_ultimo_mes))
            
            with col2:
                en_produccion_count = len(df_ultimo_mes[df_ultimo_mes['ESTATUS'] == 'PRODUCCION'])
                st.metric("En Producción", en_produccion_count)
            
            with col3:
                en_logistica_count = len(df_ultimo_mes[df_ultimo_mes['ESTATUS'] == 'LOGISTICA'])
                st.metric("En Logística", en_logistica_count)

            with col4:  # ajusta el número según tu layout
                despachados_count = len(df_ultimo_mes[
                    df_ultimo_mes['LOGISTICA'].isin(['ENTREGADO', 'DESPACHADO'])
                ])
                st.metric("Despachados", despachados_count)
            
            with col5:
                total_productos = df_ultimo_mes['CANTIDAD'].sum()
                st.metric("Total Productos", int(total_productos))

            with col6:
                ordenes_entregadas = df_ultimo_mes[df_ultimo_mes['DIAS_PRODUCCION'].notna()]
                if len(ordenes_entregadas) > 0:
                    mediana = ordenes_entregadas['DIAS_PRODUCCION'].median()
                    p75 = ordenes_entregadas['DIAS_PRODUCCION'].quantile(0.75)
                    st.metric("Mediana Días", f"{mediana:.1f} días", 
                            help=f"50% de órdenes ≤ {mediana:.1f} días | 75% ≤ {p75:.1f} días")
                else:
                    st.metric("Mediana Días", "N/A")
            
            st.divider()

        # ==== ESTADÍSTICA Y ANALÍTICA ====
        st.header("📈 Estadística y Analítica")

        # Filtrar datos de los últimos 30 días para análisis diario
        df_analisis = df_ultimo_mes.copy()

        # Preparar datos para análisis temporal
        tab_stat1, tab_stat2, tab_stat3, tab_stat4 = st.tabs([
            "📊 Flujo Diario",
            "🔥 Productos Populares", 
            "⚡ Velocidad de Producción",
            "📉 Tendencias"
        ])

        with tab_stat1:
            st.subheader("Flujo de Órdenes Diario")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Órdenes que pasaron por PRODUCCION (incluyendo las ya ENTREGADAS)
                st.markdown("**Entradas a Producción por día**")
                entradas_prod = df_analisis[df_analisis['ESTATUS'].isin(['PRODUCCION', 'ENTREGADO'])]
                entradas_prod_dia = entradas_prod.groupby(entradas_prod['FECHA DE VENTA'].dt.date).size().reset_index()
                entradas_prod_dia.columns = ['Fecha', 'Cantidad']
                
                if len(entradas_prod_dia) > 0:
                    fig = px.line(entradas_prod_dia, x='Fecha', y='Cantidad', 
                                title='Órdenes entrando a Producción',
                                markers=True)
                    st.plotly_chart(fig, use_container_width=True)
                    st.metric("Promedio diario", f"{entradas_prod_dia['Cantidad'].mean():.1f} órdenes")
                else:
                    st.info("No hay datos suficientes")
            
            with col2:
                # Órdenes entrando a LOGISTICA por día
                st.markdown("**Entradas a Logística por día**")
                entradas_log = df_analisis[df_analisis['ESTATUS'].isin(['LOGISTICA', 'ENTREGADO'])]
                entradas_log_dia = entradas_log.groupby(entradas_log['FECHA DE VENTA'].dt.date).size().reset_index()
                entradas_log_dia.columns = ['Fecha', 'Cantidad']
                
                if len(entradas_log_dia) > 0:
                    fig = px.line(entradas_log_dia, x='Fecha', y='Cantidad',
                                title='Órdenes entrando a Logística',
                                markers=True, color_discrete_sequence=['orange'])
                    st.plotly_chart(fig, use_container_width=True)
                    st.metric("Promedio diario", f"{entradas_log_dia['Cantidad'].mean():.1f} órdenes")
                else:
                    st.info("No hay datos suficientes")
            
            st.divider()
            
            # Tasa de entrada vs salida en Producción
            st.markdown("**⚖️ Tasa de Entrada vs Salida en Producción**")
            col1, col2, col3 = st.columns(3)
            
            # Órdenes entregadas por día
            entregadas = df_analisis[df_analisis['FECHA_ENTREGA'].notna()]
            if len(entregadas) > 0:
                entregadas_dia = entregadas.groupby(entregadas['FECHA_ENTREGA'].dt.date).size()
                promedio_salida = entregadas_dia.mean()
            else:
                promedio_salida = 0
            
            promedio_entrada = entradas_prod_dia['Cantidad'].mean() if len(entradas_prod_dia) > 0 else 0
            diferencia = promedio_entrada - promedio_salida
            
            with col1:
                st.metric("Entrada diaria promedio", f"{promedio_entrada:.1f} órdenes")
            
            with col2:
                st.metric("Salida diaria promedio", f"{promedio_salida:.1f} órdenes")
            
            with col3:
                st.metric("Diferencia", f"{diferencia:+.1f} órdenes", 
                        delta_color="inverse" if diferencia > 0 else "normal")
            
            if len(entregadas) > 0:
                # Gráfico comparativo
                comparacion = pd.DataFrame({
                    'Fecha': list(entradas_prod_dia['Fecha']) + list(entregadas_dia.index),
                    'Cantidad': list(entradas_prod_dia['Cantidad']) + list(entregadas_dia.values),
                    'Tipo': ['Entrada']*len(entradas_prod_dia) + ['Salida']*len(entregadas_dia)
                })
                
                fig = px.line(comparacion, x='Fecha', y='Cantidad', color='Tipo',
                            title='Comparación Entrada vs Salida en Producción',
                            markers=True)
                st.plotly_chart(fig, use_container_width=True)

        # Tabla detallada de flujo diario
            st.divider()
            st.markdown("**📊 Tabla de Flujo Diario**")
            
            # Crear tabla combinada
            if len(entradas_prod_dia) > 0 or len(entregadas) > 0:
                tabla_flujo = entradas_prod_dia.copy()
                tabla_flujo = tabla_flujo.rename(columns={'Cantidad': 'Entradas'})
                
                if len(entregadas) > 0:
                    salidas_df = entregadas_dia.reset_index()
                    salidas_df.columns = ['Fecha', 'Salidas']
                    tabla_flujo = tabla_flujo.merge(salidas_df, on='Fecha', how='outer')
                else:
                    tabla_flujo['Salidas'] = 0
                
                tabla_flujo = tabla_flujo.fillna(0)
                tabla_flujo['Diferencia'] = tabla_flujo['Entradas'] - tabla_flujo['Salidas']
                tabla_flujo = tabla_flujo.sort_values('Fecha', ascending=False)
                
                # Convertir a enteros
                tabla_flujo['Entradas'] = tabla_flujo['Entradas'].astype(int)
                tabla_flujo['Salidas'] = tabla_flujo['Salidas'].astype(int)
                tabla_flujo['Diferencia'] = tabla_flujo['Diferencia'].astype(int)
                
                st.dataframe(tabla_flujo, hide_index=True, use_container_width=True)           

        with tab_stat2:
            st.subheader("Productos Más Populares")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🏭 Top 10 en Producción**")
                prod_data = df_analisis[df_analisis['ESTATUS'].isin(['PRODUCCION', 'ENTREGADO'])].groupby('EKM').agg({
                    'ORDEN': 'count',
                    'DESCRIPCION PLATAFORMA': 'first'
                }).reset_index()
                prod_data.columns = ['EKM', 'Cantidad', 'Descripción']
                prod_data = prod_data.sort_values('Cantidad', ascending=False).head(10)
                
                if len(prod_data) > 0:
                    # Crear etiqueta combinada
                    prod_data['Label'] = prod_data['EKM'] + ' - ' + prod_data['Descripción'].str[:30]
                    
                    fig = px.bar(prod_data, x='Cantidad', y='Label', 
                                orientation='h',
                                labels={'Cantidad': 'Cantidad de Órdenes', 'Label': ''},
                                title='Productos más frecuentes en Producción',
                                color='Cantidad',
                                color_continuous_scale='Reds',
                                hover_data={'EKM': True, 'Descripción': True})
                    fig.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Tabla detallada
                    st.dataframe(prod_data[['EKM', 'Descripción', 'Cantidad']], hide_index=True, use_container_width=True)
                else:
                    st.info("No hay órdenes en producción")
            
            with col2:
                st.markdown("**📦 Top 10 en Logística**")
                log_data = df_analisis[df_analisis['ESTATUS'] == 'LOGISTICA'].groupby('EKM').agg({
                    'ORDEN': 'count',
                    'DESCRIPCION PLATAFORMA': 'first'
                }).reset_index()
                log_data.columns = ['EKM', 'Cantidad', 'Descripción']
                log_data = log_data.sort_values('Cantidad', ascending=False).head(10)
                
                if len(log_data) > 0:
                    # Crear etiqueta combinada
                    log_data['Label'] = log_data['EKM'] + ' - ' + log_data['Descripción'].str[:30]
                    
                    fig = px.bar(log_data, x='Cantidad', y='Label',
                                orientation='h',
                                labels={'Cantidad': 'Cantidad de Órdenes', 'Label': ''},
                                title='Productos más frecuentes en Logística',
                                color='Cantidad',
                                color_continuous_scale='Blues',
                                hover_data={'EKM': True, 'Descripción': True})
                    fig.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Tabla detallada
                    st.dataframe(log_data[['EKM', 'Descripción', 'Cantidad']], hide_index=True, use_container_width=True)
                else:
                    st.info("No hay órdenes en logística")

        with tab_stat3:
            st.subheader("Velocidad de Producción por Producto")
            
            # Calcular mediana de días de producción por EKM (PRODUCCION + ENTREGADO)
            ordenes_con_tiempo = df_analisis[
                (df_analisis['ESTATUS'].isin(['PRODUCCION', 'ENTREGADO'])) &
                (df_analisis['DIAS_PRODUCCION'].notna())
            ].copy()
            
            if len(ordenes_con_tiempo) > 0:
                velocidad_por_ekm = ordenes_con_tiempo.groupby('EKM').agg({
                    'DIAS_PRODUCCION': [('mediana', 'median'), ('promedio', 'mean'), ('cantidad', 'count')],
                    'DESCRIPCION PLATAFORMA': 'first'
                }).reset_index()

                # Aplanar columnas
                velocidad_por_ekm.columns = ['EKM', 'mediana', 'promedio', 'cantidad', 'Descripción']

                # AGREGAR ESTA LÍNEA:
                velocidad_por_ekm['mediana'] = pd.to_numeric(velocidad_por_ekm['mediana'], errors='coerce')
                velocidad_por_ekm['promedio'] = pd.to_numeric(velocidad_por_ekm['promedio'], errors='coerce')

                # Filtrar productos con al menos 3 órdenes completadas
                velocidad_por_ekm = velocidad_por_ekm[velocidad_por_ekm['cantidad'] >= 3]
                    
                # Filtrar productos con al menos 3 órdenes completadas
                velocidad_por_ekm = velocidad_por_ekm[velocidad_por_ekm['cantidad'] >= 3]
                
                if len(velocidad_por_ekm) > 0:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**⚡ Top 10 Más Rápidos**")
                        mas_rapidos = velocidad_por_ekm.sort_values('mediana').head(10)
                        mas_rapidos['Label'] = mas_rapidos['EKM'] + ' - ' + mas_rapidos['Descripción'].str[:25]
                        
                        fig = px.bar(mas_rapidos, x='mediana', y='Label',
                                    orientation='h',
                                    labels={'mediana': 'Días (mediana)', 'Label': ''},
                                    title='Productos con menor tiempo de producción',
                                    color='mediana',
                                    color_continuous_scale='Greens_r',
                                    hover_data={'cantidad': True, 'promedio': ':.1f'})
                        fig.update_layout(yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.markdown("**🐌 Top 10 Más Lentos**")
                        mas_lentos = velocidad_por_ekm.sort_values('mediana', ascending=False).head(10)
                        mas_lentos['Label'] = mas_lentos['EKM'] + ' - ' + mas_lentos['Descripción'].str[:25]
                        
                        fig = px.bar(mas_lentos, x='mediana', y='Label',
                                    orientation='h',
                                    labels={'mediana': 'Días (mediana)', 'Label': ''},
                                    title='Productos con mayor tiempo de producción',
                                    color='mediana',
                                    color_continuous_scale='Reds',
                                    hover_data={'cantidad': True, 'promedio': ':.1f'})
                        fig.update_layout(yaxis={'categoryorder':'total descending'})
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Tabla detallada
                    st.divider()
                    st.markdown("**📊 Tabla Completa de Tiempos de Producción**")
                    velocidad_display = velocidad_por_ekm.sort_values('mediana')
                    velocidad_display['mediana'] = velocidad_display['mediana'].round(1)
                    velocidad_display['promedio'] = velocidad_display['promedio'].round(1)
                    st.dataframe(velocidad_display, hide_index=True, use_container_width=True)
                else:
                    st.info("No hay suficientes datos. Se necesitan al menos 3 órdenes completadas por producto.")
            else:
                st.info("No hay órdenes con tiempo de producción calculado aún.")

        with tab_stat4:
            st.subheader("Tendencias Generales")
            
            # Distribución de días de producción
            if len(ordenes_con_tiempo) > 0:
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.histogram(ordenes_con_tiempo, x='DIAS_PRODUCCION',
                                    title='Distribución de Días de Producción',
                                    labels={'DIAS_PRODUCCION': 'Días de Producción'},
                                    nbins=30,
                                    color_discrete_sequence=['#636EFA'])
                    fig.add_vline(x=ordenes_con_tiempo['DIAS_PRODUCCION'].median(), 
                                line_dash="dash", line_color="red",
                                annotation_text=f"Mediana: {ordenes_con_tiempo['DIAS_PRODUCCION'].median():.1f} días")
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.box(ordenes_con_tiempo, y='DIAS_PRODUCCION',
                                title='Distribución de Tiempos (Box Plot)',
                                labels={'DIAS_PRODUCCION': 'Días de Producción'})
                    st.plotly_chart(fig, use_container_width=True)
                
                # Métricas de resumen
                st.divider()
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Mínimo", f"{ordenes_con_tiempo['DIAS_PRODUCCION'].min():.0f} días")
                with col2:
                    st.metric("Percentil 25", f"{ordenes_con_tiempo['DIAS_PRODUCCION'].quantile(0.25):.1f} días")
                with col3:
                    st.metric("Percentil 75", f"{ordenes_con_tiempo['DIAS_PRODUCCION'].quantile(0.75):.1f} días")
                with col4:
                    st.metric("Máximo", f"{ordenes_con_tiempo['DIAS_PRODUCCION'].max():.0f} días")
            
        # ==== VISUALIZACIONES ====
        st.header("📊 Visualizaciones Generales")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Estado de Órdenes")
            estatus_counts = df_ultimo_mes['ESTATUS'].value_counts()
            fig = px.pie(
                values=estatus_counts.values,
                names=estatus_counts.index,
                title="Distribución por Estatus",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Órdenes por Cuenta")
            cuenta_counts = df_ultimo_mes['CUENTA'].value_counts().head(10)
            fig = px.bar(
                x=cuenta_counts.index,
                y=cuenta_counts.values,
                title="Top 10 Cuentas",
                labels={'x': 'Cuenta', 'y': 'Cantidad de Órdenes'},
                color=cuenta_counts.values,
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # ==== TABLAS DETALLADAS ====
        st.header("📋 Detalle de Órdenes")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏭 En Producción", 
            "📦 En Logística", 
            "✅ Recibidos",
            "🚚 Despachados",
            "🔍 Buscar Orden"
        ])
        
        with tab1:
            produccion = df_ultimo_mes[df_ultimo_mes['ESTATUS'] == 'PRODUCCION']
            st.dataframe(
                produccion[['ORDEN', 'CUENTA', 'FECHA DE VENCIMIENTO', 
                          'DESCRIPCION PLATAFORMA', 'CANTIDAD', 'EKM', 'DIAS_PRODUCCION']],
                hide_index=True,
                use_container_width=True
            )
        
        with tab2:
            logistica = df_ultimo_mes[
                (df_ultimo_mes['ESTATUS'] == 'LOGISTICA') &
                (~df_ultimo_mes['LOGISTICA'].isin(['ENTREGADO', 'DESPACHADO']))
            ]
            st.dataframe(
                logistica[['ORDEN', 'CUENTA', 'FECHA DE VENCIMIENTO', 
                        'DESCRIPCION PLATAFORMA', 'CANTIDAD', 'EKM', 
                        'ESTATUS LOGISTICA', 'LOGISTICA', 'DIAS_PRODUCCION']],
                hide_index=True,
                use_container_width=True
            )
        
        with tab3:
            recibidos = df_ultimo_mes[df_ultimo_mes['ESTATUS LOGISTICA'] == 'RECIBIDO']
            st.dataframe(
                recibidos[['ORDEN', 'CUENTA', 'FECHA DE VENCIMIENTO', 
                         'DESCRIPCION PLATAFORMA', 'CANTIDAD', 'EKM', 'DIAS_PRODUCCION']],
                hide_index=True,
                use_container_width=True
            )

        with tab4:
            despachados = df_ultimo_mes[df_ultimo_mes['LOGISTICA'].isin(['ENTREGADO', 'DESPACHADO'])]
            st.dataframe(
                despachados[['ORDEN', 'CUENTA', 'FECHA DE VENCIMIENTO', 
                        'DESCRIPCION PLATAFORMA', 'CANTIDAD', 'EKM', 
                        'LOGISTICA', 'DIAS_PRODUCCION']],
                hide_index=True,
                use_container_width=True
            )
        
        with tab5:
            buscar = st.text_input("Buscar por número de orden o código EKM")
            if buscar:
                resultado = df_ultimo_mes[
                    (df_ultimo_mes['ORDEN'].astype(str).str.contains(buscar, case=False, na=False)) |
                    (df_ultimo_mes['EKM'].astype(str).str.contains(buscar, case=False, na=False))
                ]
                if len(resultado) > 0:
                    st.dataframe(
                        resultado[['ORDEN', 'CUENTA', 'FECHA DE VENTA', 'FECHA DE VENCIMIENTO',
                                 'DESCRIPCION PLATAFORMA', 'CANTIDAD', 'EKM', 'ESTATUS', 
                                 'ESTATUS LOGISTICA', 'DIAS_PRODUCCION']],
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.warning("No se encontraron resultados")
        
        # Botón de actualización
        st.sidebar.divider()
        if st.sidebar.button("🔄 Actualizar datos"):
            st.cache_data.clear()
            st.rerun()
        
        # Información de última actualización
        st.sidebar.info(f"📅 Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.info("👆 Asegúrate de configurar correctamente las credenciales de Google Cloud")