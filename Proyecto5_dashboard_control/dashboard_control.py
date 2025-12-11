import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

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
        df_estatus['FECHA_ENTREGA'] = pd.to_datetime(df_estatus['FECHA_ENTREGA'], errors='coerce')
        
        return df_estatus
    except Exception as e:
        st.error(f"Error al cargar estatus: {str(e)}")
        return None

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
                
                # Calcular días de producción (solo para órdenes con fecha de entrega)
                df_ultimo_mes['DIAS_PRODUCCION'] = None
                mask = df_ultimo_mes['FECHA_ENTREGA'].notna() & df_ultimo_mes['FECHA DE VENTA'].notna()
                df_ultimo_mes.loc[mask, 'DIAS_PRODUCCION'] = (
                    df_ultimo_mes.loc[mask, 'FECHA_ENTREGA'] - 
                    df_ultimo_mes.loc[mask, 'FECHA DE VENTA']
                ).dt.days
            
            # ==== ALERTAS PRINCIPALES ====
            st.header("🚨 Alertas Importantes")
            
            col1, col2, col3 = st.columns(3)
            
            # Alerta: Próximos a vencer en 2 días
            fecha_limite = fecha_actual + timedelta(days=2)
            # Alerta: Próximos a vencer en 2 días
            fecha_limite = fecha_actual + timedelta(days=2)
            proximos_vencer = df_ultimo_mes[
                (df_ultimo_mes['FECHA DE VENCIMIENTO'] <= fecha_limite) & 
                (df_ultimo_mes['FECHA DE VENCIMIENTO'] >= fecha_actual) &
                (df_ultimo_mes['ESTATUS'] == 'PRODUCCION')
            ]
            
            with col1:
                if len(proximos_vencer) > 0:
                    st.error(f"⚠️ {len(proximos_vencer)} órdenes vencen en 2 días")
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
                        st.dataframe(
                            vencidas[['ORDEN', 'CUENTA', 'DESCRIPCION PLATAFORMA', 
                                    'FECHA DE VENCIMIENTO', 'ESTATUS', 'DIAS_PRODUCCION']],
                            hide_index=True
                        )
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
            
            # ==== VISUALIZACIONES ====
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
                            'ESTATUS LOGISTICA', 'LOGISTICA', 'DIAS_PRODUCCION']],  # Añadido 'LOGISTICA'
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
