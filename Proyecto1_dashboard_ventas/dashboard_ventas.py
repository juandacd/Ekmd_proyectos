import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
from urllib.parse import quote

# Logo en la esquina superior
top_col1, top_col2 = st.columns([0.7,0.3])
with top_col2:
    st.image("https://ekonomodo.com/cdn/shop/files/Logo-Ekonomodo-color.svg?v=1736956350&width=450", width=5000)

# Configuración de página
st.set_page_config(
    page_title="Análisis de Ventas Ekonomodo 2025",
    page_icon="📊",
    layout="wide"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: left;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 3px solid #1f77b4;
        padding-bottom: 0.5rem;
    }
    .subsection-header {
        font-size: 1.4rem;
        font-weight: bold;
        color: #34495e;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Funciones de limpieza y procesamiento
@st.cache_data
def limpiar_columnas(df):
    """Limpia y normaliza los nombres de las columnas"""
    df.columns = df.columns.str.strip().str.upper()
    return df

def limpiar_valores_nd(df):
    """Reemplaza valores #N/D por NaN en columnas específicas, manteniendo las filas"""
    columnas_texto = ['CIUDAD', 'REFERENCIA', 'DESCRIPCION', 'CLIENTE', 'VENDEDOR', 'PLATAFORMA']
    
    for col in columnas_texto:
        if col in df.columns:
            # Reemplazar #N/D, #N/A, y variantes por NaN
            df[col] = df[col].replace(['#N/D', '#N/A', '#¡N/A', '#DIV/0!', '#REF!', '#VALUE!'], pd.NA)
            df[col] = df[col].replace('nan', pd.NA)
            # También limpiar si viene como string
            df[col] = df[col].apply(lambda x: pd.NA if str(x).strip() in ['#N/D', '#N/A', '#¡N/A', 'nan', 'NaN', ''] else x)
    
    return df

def procesar_ciudad_departamento(df):
    """Extrae ciudad y departamento del formato 'CIUDAD-DEPARTAMENTO' y unifica Bogotá"""
    if 'CIUDAD' in df.columns:
        # Crear columna de ciudad limpia
        df['CIUDAD_LIMPIA'] = df['CIUDAD'].apply(lambda x: extraer_ciudad(x) if pd.notna(x) else pd.NA)
        df['DEPARTAMENTO'] = df['CIUDAD'].apply(lambda x: extraer_departamento(x) if pd.notna(x) else pd.NA)
    
    return df

def extraer_ciudad(texto):
    """Extrae el nombre de la ciudad del formato CIUDAD-DEPARTAMENTO"""
    if pd.isna(texto):
        return pd.NA
    
    texto = str(texto).strip().upper()
    
    # Caso especial: Unificar todas las variantes de Bogotá
    if 'BOGOTA' in texto or 'BOGOTÁ' in texto:
        return 'BOGOTÁ'
    
    # Si tiene guion, tomar la parte antes del guion
    if '-' in texto:
        ciudad = texto.split('-')[0].strip()
        return ciudad
    
    # Si no tiene guion, devolver tal cual
    return texto

def extraer_departamento(texto):
    """Extrae el departamento del formato CIUDAD-DEPARTAMENTO"""
    if pd.isna(texto):
        return pd.NA
    
    texto = str(texto).strip().upper()
    
    # Caso especial Bogotá
    if 'BOGOTA' in texto or 'BOGOTÁ' in texto:
        return 'BOGOTÁ D.C.'
    
    # Si tiene guion, tomar la parte después del guion
    if '-' in texto:
        departamento = texto.split('-')[1].strip()
        return departamento
    
    # Si no tiene guion, devolver vacío
    return pd.NA

# Coordenadas de las principales ciudades de Colombia
COORDENADAS_CIUDADES = {
    # Ciudades principales
    'BOGOTÁ': {'lat': 4.7110, 'lon': -74.0721},
    'MEDELLÍN': {'lat': 6.2476, 'lon': -75.5658},
    'MEDELLIN': {'lat': 6.2476, 'lon': -75.5658},
    'CALI': {'lat': 3.4516, 'lon': -76.5320},
    'BARRANQUILLA': {'lat': 10.9685, 'lon': -74.7813},
    'CARTAGENA': {'lat': 10.3910, 'lon': -75.4794},
    'CÚCUTA': {'lat': 7.8939, 'lon': -72.5078},
    'CUCUTA': {'lat': 7.8939, 'lon': -72.5078},
    'BUCARAMANGA': {'lat': 7.1193, 'lon': -73.1227},
    'PEREIRA': {'lat': 4.8133, 'lon': -75.6961},
    'SANTA MARTA': {'lat': 11.2408, 'lon': -74.2120},
    'IBAGUÉ': {'lat': 4.4389, 'lon': -75.2322},
    'IBAGUE': {'lat': 4.4389, 'lon': -75.2322},
    'MANIZALES': {'lat': 5.0689, 'lon': -75.5174},
    'VILLAVICENCIO': {'lat': 4.1420, 'lon': -73.6266},
    'PASTO': {'lat': 1.2136, 'lon': -77.2811},
    'NEIVA': {'lat': 2.9273, 'lon': -75.2819},
    'ARMENIA': {'lat': 4.5339, 'lon': -75.6811},
    'POPAYÁN': {'lat': 2.4448, 'lon': -76.6147},
    'POPAYAN': {'lat': 2.4448, 'lon': -76.6147},
    'MONTERÍA': {'lat': 8.7479, 'lon': -75.8814},
    'MONTERIA': {'lat': 8.7479, 'lon': -75.8814},
    'VALLEDUPAR': {'lat': 10.4631, 'lon': -73.2532},
    'SINCELEJO': {'lat': 9.3047, 'lon': -75.3978},
    'TUNJA': {'lat': 5.5353, 'lon': -73.3678},
    'RIOHACHA': {'lat': 11.5444, 'lon': -72.9072},
    'QUIBDÓ': {'lat': 5.6947, 'lon': -76.6611},
    'QUIBDO': {'lat': 5.6947, 'lon': -76.6611},
    'FLORENCIA': {'lat': 1.6144, 'lon': -75.6062},
    'LETICIA': {'lat': -4.2153, 'lon': -69.9406},
    'ARAUCA': {'lat': 7.0903, 'lon': -70.7619},
    'YOPAL': {'lat': 5.3378, 'lon': -72.3959},
    'INÍRIDA': {'lat': 3.8653, 'lon': -67.9239},
    'INIRIDA': {'lat': 3.8653, 'lon': -67.9239},
    'SAN JOSÉ DEL GUAVIARE': {'lat': 2.5697, 'lon': -72.6458},
    'MITÚ': {'lat': 1.2581, 'lon': -70.1736},
    'MITU': {'lat': 1.2581, 'lon': -70.1736},
    'PUERTO CARREÑO': {'lat': 6.1847, 'lon': -67.4860},
    
    # Antioquia
    'ENVIGADO': {'lat': 6.1719, 'lon': -75.5831},
    'ITAGÜÍ': {'lat': 6.1845, 'lon': -75.6139},
    'ITAGUI': {'lat': 6.1845, 'lon': -75.6139},
    'BELLO': {'lat': 6.3370, 'lon': -75.5547},
    'RIONEGRO': {'lat': 6.1554, 'lon': -75.3736},
    'SABANETA': {'lat': 6.1514, 'lon': -75.6169},
    'LA ESTRELLA': {'lat': 6.1583, 'lon': -75.6417},
    'CALDAS': {'lat': 6.0911, 'lon': -75.6364},
    'COPACABANA': {'lat': 6.3469, 'lon': -75.5078},
    'GIRARDOTA': {'lat': 6.3783, 'lon': -75.4472},
    'BARBOSA': {'lat': 6.4386, 'lon': -75.3319},
    'APARTADÓ': {'lat': 7.8833, 'lon': -76.6333},
    'APARTADO': {'lat': 7.8833, 'lon': -76.6333},
    'TURBO': {'lat': 8.0928, 'lon': -76.7272},
    'CAUCASIA': {'lat': 7.9869, 'lon': -75.1944},
    'CHIGORODÓ': {'lat': 7.6667, 'lon': -76.6833},
    'CHIGORODO': {'lat': 7.6667, 'lon': -76.6833},
    'CAREPA': {'lat': 7.7583, 'lon': -76.6528},
    'EL CARMEN DE VIBORAL': {'lat': 6.0833, 'lon': -75.3333},
    'MARINILLA': {'lat': 6.1728, 'lon': -75.3356},
    'GUARNE': {'lat': 6.2756, 'lon': -75.4447},
    'LA CEJA': {'lat': 6.0278, 'lon': -75.4278},
    'RETIRO': {'lat': 6.0625, 'lon': -75.5042},
    'CARMEN DE VIBORAL': {'lat': 6.0833, 'lon': -75.3333},
    'PUERTO BERRIO': {'lat': 6.4903, 'lon': -74.4056},
    'PUERTO BERRÍO': {'lat': 6.4903, 'lon': -74.4056},
    'SEGOVIA': {'lat': 7.0800, 'lon': -74.7064},
    'REMEDIOS': {'lat': 7.0294, 'lon': -74.6897},
    'YARUMAL': {'lat': 6.9664, 'lon': -75.4197},
    'ANDES': {'lat': 5.6556, 'lon': -75.8794},
    'SANTA ROSA DE OSOS': {'lat': 6.6472, 'lon': -75.4597},
    'JERICÓ': {'lat': 5.7925, 'lon': -75.7836},
    'JERICO': {'lat': 5.7925, 'lon': -75.7836},
    'FREDONIA': {'lat': 5.9261, 'lon': -75.6719},
    'TÁMESIS': {'lat': 5.6675, 'lon': -75.7172},
    'TAMESIS': {'lat': 5.6675, 'lon': -75.7172},
    'SANTA FÉ DE ANTIOQUIA': {'lat': 6.5569, 'lon': -75.8275},
    'SANTA FE DE ANTIOQUIA': {'lat': 6.5569, 'lon': -75.8275},
    'URRAO': {'lat': 6.3197, 'lon': -76.1372},
    'DABEIBA': {'lat': 7.0042, 'lon': -76.2961},
    'SANTO DOMINGO': {'lat': 6.4644, 'lon': -75.1708},
    'AMALFI': {'lat': 6.9053, 'lon': -75.0711},
    'ANORÍ': {'lat': 7.0589, 'lon': -75.1544},
    'ANORI': {'lat': 7.0589, 'lon': -75.1544},
    'SONSÓN': {'lat': 5.7111, 'lon': -75.3125},
    'SONSON': {'lat': 5.7111, 'lon': -75.3125},
    'ABEJORRAL': {'lat': 5.8000, 'lon': -75.4333},
    'ARGELIA': {'lat': 5.7969, 'lon': -75.8481},
    'NARIÑO': {'lat': 5.6122, 'lon': -75.1817},
    'GRANADA': {'lat': 6.1689, 'lon': -75.1847},
    'COCORNÁ': {'lat': 6.0567, 'lon': -75.1864},
    'COCORNA': {'lat': 6.0567, 'lon': -75.1864},
    'SAN CARLOS': {'lat': 6.1800, 'lon': -74.9992},
    'SAN RAFAEL': {'lat': 6.2861, 'lon': -75.0244},
    'JARDÍN': {'lat': 5.5994, 'lon': -75.8219},
    'JARDIN': {'lat': 5.5994, 'lon': -75.8219},
    'CIUDAD BOLÍVAR': {'lat': 5.8569, 'lon': -76.0200},
    'CIUDAD BOLIVAR': {'lat': 5.8569, 'lon': -76.0200},
    'VENECIA': {'lat': 5.9611, 'lon': -75.7503},
    'TITIRIBÍ': {'lat': 6.0608, 'lon': -75.7906},
    'TITIRIBI': {'lat': 6.0608, 'lon': -75.7906},
    'AMAGÁ': {'lat': 6.0364, 'lon': -75.7072},
    'AMAGA': {'lat': 6.0364, 'lon': -75.7072},
    'ANGELÓPOLIS': {'lat': 6.1053, 'lon': -75.7111},
    'ANGELOPOLIS': {'lat': 6.1053, 'lon': -75.7111},
    'HISPANIA': {'lat': 5.8069, 'lon': -75.9264},
    'VALPARAÍSO': {'lat': 5.4936, 'lon': -75.5789},
    'VALPARAISO': {'lat': 5.4936, 'lon': -75.5789},
    'CARAMANTA': {'lat': 5.5419, 'lon': -75.6411},
    'SAN VICENTE': {'lat': 6.2928, 'lon': -75.3281},
    'CONCEPCIÓN': {'lat': 6.3750, 'lon': -75.3208},
    'CONCEPCION': {'lat': 6.3750, 'lon': -75.3208},
    'ALEJANDRÍA': {'lat': 6.3703, 'lon': -75.1342},
    'ALEJANDRIA': {'lat': 6.3703, 'lon': -75.1342},
    'SAN ROQUE': {'lat': 6.4981, 'lon': -75.0125},
    'MACEO': {'lat': 6.5486, 'lon': -74.7853},
    'PUERTO TRIUNFO': {'lat': 5.8736, 'lon': -74.6392},
    'YONDÓ': {'lat': 7.0125, 'lon': -73.9011},
    'YONDO': {'lat': 7.0125, 'lon': -73.9011},
    
    # Valle del Cauca
    'PALMIRA': {'lat': 3.5394, 'lon': -76.3036},
    'BUENAVENTURA': {'lat': 3.8801, 'lon': -77.0318},
    'TULUÁ': {'lat': 4.0848, 'lon': -76.1950},
    'TULUA': {'lat': 4.0848, 'lon': -76.1950},
    'CARTAGO': {'lat': 4.7467, 'lon': -75.9117},
    'BUGA': {'lat': 3.9011, 'lon': -76.2978},
    'GUADALAJARA DE BUGA': {'lat': 3.9011, 'lon': -76.2978},
    'JAMUNDÍ': {'lat': 3.2644, 'lon': -76.5403},
    'JAMUNDI': {'lat': 3.2644, 'lon': -76.5403},
    'YUMBO': {'lat': 3.5833, 'lon': -76.5000},
    'CANDELARIA': {'lat': 3.4114, 'lon': -76.3497},
    'FLORIDA': {'lat': 3.3228, 'lon': -76.2350},
    'PRADERA': {'lat': 3.4239, 'lon': -76.2431},
    'SEVILLA': {'lat': 4.2708, 'lon': -75.9378},
    'CAICEDONIA': {'lat': 4.3311, 'lon': -75.8236},
    'ROLDANILLO': {'lat': 4.4119, 'lon': -76.1542},
    'ZARZAL': {'lat': 4.3928, 'lon': -76.0711},
    'LA UNIÓN': {'lat': 4.5342, 'lon': -76.1044},
    'LA UNION': {'lat': 4.5342, 'lon': -76.1044},
    'BUGALAGRANDE': {'lat': 4.2092, 'lon': -76.1542},
    'ANDALUCÍA': {'lat': 4.1333, 'lon': -76.2167},
    'ANDALUCIA': {'lat': 4.1333, 'lon': -76.2167},
    'EL CERRITO': {'lat': 3.6833, 'lon': -76.3167},
    'GINEBRA': {'lat': 3.7253, 'lon': -76.2681},
    'GUACARÍ': {'lat': 3.7586, 'lon': -76.3308},
    'GUACARI': {'lat': 3.7586, 'lon': -76.3308},
    'VIJES': {'lat': 3.6989, 'lon': -76.4403},
    'YOTOCO': {'lat': 3.8650, 'lon': -76.3858},
    'RESTREPO': {'lat': 3.8239, 'lon': -76.5311},
    'DAGUA': {'lat': 3.6561, 'lon': -76.6844},
    'LA CUMBRE': {'lat': 3.6336, 'lon': -76.5711},
    'CALIMA': {'lat': 3.9189, 'lon': -76.4803},
    
    # Atlántico
    'SOLEDAD': {'lat': 10.9185, 'lon': -74.7693},
    'MALAMBO': {'lat': 10.8597, 'lon': -74.7736},
    'SABANALARGA': {'lat': 10.6336, 'lon': -74.9211},
    'BARANOA': {'lat': 10.7947, 'lon': -74.9161},
    'GALAPA': {'lat': 10.8997, 'lon': -74.8828},
    'PUERTO COLOMBIA': {'lat': 11.0097, 'lon': -74.8539},
    'PALMAR DE VARELA': {'lat': 10.7400, 'lon': -74.7542},
    'SANTO TOMÁS': {'lat': 10.7536, 'lon': -74.7542},
    'SANTO TOMAS': {'lat': 10.7536, 'lon': -74.7542},
    'SABANAGRANDE': {'lat': 10.7883, 'lon': -74.7581},
    'POLONUEVO': {'lat': 10.7753, 'lon': -74.8536},
    'PONEDERA': {'lat': 10.6433, 'lon': -74.7536},
    'USIACURÍ': {'lat': 10.7406, 'lon': -75.0072},
    'USIACURI': {'lat': 10.7406, 'lon': -75.0072},
    'JUAN DE ACOSTA': {'lat': 10.8336, 'lon': -75.0389},
    'TUBARÁ': {'lat': 10.8847, 'lon': -75.0414},
    'TUBARA': {'lat': 10.8847, 'lon': -75.0414},
    'CAMPO DE LA CRUZ': {'lat': 10.3764, 'lon': -74.8861},
    'MANATÍ': {'lat': 10.4497, 'lon': -74.9564},
    'MANATI': {'lat': 10.4497, 'lon': -74.9564},
    'CANDELARIA': {'lat': 10.4600, 'lon': -74.8717},
    'SUAN': {'lat': 10.5136, 'lon': -74.8833},
    'REPELÓN': {'lat': 10.4939, 'lon': -75.1267},
    'REPELON': {'lat': 10.4939, 'lon': -75.1267},
    'LURUACO': {'lat': 10.6092, 'lon': -75.1550},
    'SANTA LUCÍA': {'lat': 10.3150, 'lon': -74.9622},
    'SANTA LUCIA': {'lat': 10.3150, 'lon': -74.9622},
    
    # Cundinamarca
    'SOACHA': {'lat': 4.5794, 'lon': -74.2169},
    'GIRARDOT': {'lat': 4.3017, 'lon': -74.8022},
    'ZIPAQUIRÁ': {'lat': 5.0269, 'lon': -74.0039},
    'ZIPAQUIRA': {'lat': 5.0269, 'lon': -74.0039},
    'FACATATIVÁ': {'lat': 4.8131, 'lon': -74.3547},
    'FACATATIVA': {'lat': 4.8131, 'lon': -74.3547},
    'CHÍA': {'lat': 4.8606, 'lon': -74.0589},
    'CHIA': {'lat': 4.8606, 'lon': -74.0589},
    'FUSAGASUGÁ': {'lat': 4.3367, 'lon': -74.3636},
    'FUSAGASUGA': {'lat': 4.3367, 'lon': -74.3636},
    'MADRID': {'lat': 4.7314, 'lon': -74.2658},
    'MOSQUERA': {'lat': 4.7058, 'lon': -74.2303},
    'FUNZA': {'lat': 4.7164, 'lon': -74.2125},
    'CAJICÁ': {'lat': 4.9186, 'lon': -74.0281},
    'CAJICA': {'lat': 4.9186, 'lon': -74.0281},
    'LA CALERA': {'lat': 4.7236, 'lon': -73.9689},
    'COTA': {'lat': 4.8097, 'lon': -74.1031},
    'SOPÓ': {'lat': 4.9086, 'lon': -73.9425},
    'SOPO': {'lat': 4.9086, 'lon': -73.9425},
    'TOCANCIPÁ': {'lat': 4.9669, 'lon': -73.9147},
    'TOCANCIPA': {'lat': 4.9669, 'lon': -73.9147},
    'GACHANCIPÁ': {'lat': 4.9928, 'lon': -73.8717},
    'GACHANCIPA': {'lat': 4.9928, 'lon': -73.8717},
    'TENJO': {'lat': 4.8717, 'lon': -74.1467},
    'TABIO': {'lat': 4.9194, 'lon': -74.0942},
    'EL ROSAL': {'lat': 4.8453, 'lon': -74.2636},
    'SUBACHOQUE': {'lat': 4.9289, 'lon': -74.1764},
    'BOJACÁ': {'lat': 4.7322, 'lon': -74.3422},
    'BOJACA': {'lat': 4.7322, 'lon': -74.3422},
    'ARBELÁEZ': {'lat': 4.2722, 'lon': -74.4181},
    'ARBELAEZ': {'lat': 4.2722, 'lon': -74.4181},
    'SILVANIA': {'lat': 4.4019, 'lon': -74.3872},
    'GRANADA': {'lat': 4.5208, 'lon': -74.3606},
    'SAN ANTONIO DEL TEQUENDAMA': {'lat': 4.6106, 'lon': -74.3500},
    'LA MESA': {'lat': 4.6336, 'lon': -74.4644},
    'ANAPOIMA': {'lat': 4.5478, 'lon': -74.5333},
    'APULO': {'lat': 4.5211, 'lon': -74.5939},
    'TOCAIMA': {'lat': 4.4581, 'lon': -74.6350},
    'AGUA DE DIOS': {'lat': 4.3772, 'lon': -74.6711},
    'RICAURTE': {'lat': 4.2983, 'lon': -74.7669},
    'GUATAQUÍ': {'lat': 4.1944, 'lon': -74.7819},
    'GUATAQUI': {'lat': 4.1944, 'lon': -74.7819},
    'NILO': {'lat': 4.3128, 'lon': -74.6072},
    'GUADUAS': {'lat': 5.0692, 'lon': -74.5981},
    'VILLETA': {'lat': 5.0119, 'lon': -74.4731},
    'NIMAIMA': {'lat': 5.1394, 'lon': -74.3828},
    'NOCAIMA': {'lat': 5.0878, 'lon': -74.3581},
    'UBATÉ': {'lat': 5.3117, 'lon': -73.8156},
    'UBATE': {'lat': 5.3117, 'lon': -73.8156},
    'CHIQUINQUIRÁ': {'lat': 5.6181, 'lon': -73.8200},
    'CHIQUINQUIRA': {'lat': 5.6181, 'lon': -73.8200},
    'SIMIJACA': {'lat': 5.5228, 'lon': -73.8578},
    'SUSA': {'lat': 5.4250, 'lon': -73.8272},
    'CARMEN DE CARUPA': {'lat': 5.3497, 'lon': -73.9042},
    'TAUSA': {'lat': 5.1989, 'lon': -73.9158},
    'COGUA': {'lat': 5.0608, 'lon': -73.9772},
    'NEMOCÓN': {'lat': 5.0539, 'lon': -73.8925},
    'NEMOCON': {'lat': 5.0539, 'lon': -73.8925},
    'SUESCA': {'lat': 5.1031, 'lon': -73.7992},
    'SESQUILÉ': {'lat': 5.0533, 'lon': -73.7903},
    'SESQUILE': {'lat': 5.0533, 'lon': -73.7903},
    'CHOCONTÁ': {'lat': 5.1458, 'lon': -73.6875},
    'CHOCONTA': {'lat': 5.1458, 'lon': -73.6875},
    'VILLAPINZÓN': {'lat': 5.2131, 'lon': -73.5969},
    'VILLAPINZON': {'lat': 5.2131, 'lon': -73.5969},
    'GUATAVITA': {'lat': 4.9294, 'lon': -73.8372},
    'GUASCA': {'lat': 4.8664, 'lon': -73.8753},
    'SOPÓ': {'lat': 4.9086, 'lon': -73.9425},
    'GUARNE': {'lat': 6.2756, 'lon': -75.4447},
    
    # Bolívar
    'MAGANGUÉ': {'lat': 9.2414, 'lon': -74.7544},
    'MAGANGUE': {'lat': 9.2414, 'lon': -74.7544},
    'CARMEN DE BOLIVAR': {'lat': 9.7181, 'lon': -75.1208},
    'TURBACO': {'lat': 10.3364, 'lon': -75.4267},
    'ARJONA': {'lat': 10.2592, 'lon': -75.3464},
    'EL CARMEN DE BOLÍVAR': {'lat': 9.7181, 'lon': -75.1208},
    'EL CARMEN DE BOLIVAR': {'lat': 9.7181, 'lon': -75.1208},
    'SANTA ROSA': {'lat': 9.2578, 'lon': -75.0758},
    'MOMPÓS': {'lat': 9.2406, 'lon': -74.4294},
    'MOMPOS': {'lat': 9.2406, 'lon': -74.4294},
    'SAN JACINTO': {'lat': 9.8331, 'lon': -75.1178},
    'SAN JUAN NEPOMUCENO': {'lat': 9.9542, 'lon': -75.0861},
    'MARÍA LA BAJA': {'lat': 9.9831, 'lon': -75.3042},
    'MARIA LA BAJA': {'lat': 9.9831, 'lon': -75.3042},
    
    # Santander
    'FLORIDABLANCA': {'lat': 7.0642, 'lon': -73.0931},
    'GIRÓN': {'lat': 7.0667, 'lon': -73.1697},
    'GIRON': {'lat': 7.0667, 'lon': -73.1697},
    'PIEDECUESTA': {'lat': 6.9850, 'lon': -73.0508},
    'BARRANCABERMEJA': {'lat': 7.0653, 'lon': -73.8547},
    'SAN GIL': {'lat': 6.5578, 'lon': -73.1336},
    'SOCORRO': {'lat': 6.4633, 'lon': -73.2625},
    'MÁLAGA': {'lat': 6.6553, 'lon': -72.7364},
    'MALAGA': {'lat': 6.6553, 'lon': -72.7364},
    'VÉLEZ': {'lat': 6.0092, 'lon': -73.6736},
    'VELEZ': {'lat': 6.0092, 'lon': -73.6736},
    'BARBOSA': {'lat': 5.9311, 'lon': -73.6200},
    'ZAPATOCA': {'lat': 6.8197, 'lon': -73.2742},
    'CHARALÁ': {'lat': 6.2939, 'lon': -73.1261},
    'CHARALA': {'lat': 6.2939, 'lon': -73.1261},
    'CALIFORNIA': {'lat': 7.1261, 'lon': -73.0850},
    'LEBRIJA': {'lat': 7.1358, 'lon': -73.2142},
    'RIONEGRO': {'lat': 7.2586, 'lon': -73.1572},
    'EL PLAYÓN': {'lat': 7.4917, 'lon': -73.2208},
    'EL PLAYON': {'lat': 7.4917, 'lon': -73.2208},
    
    # Risaralda
    'DOSQUEBRADAS': {'lat': 4.8397, 'lon': -75.6728},
    'SANTA ROSA DE CABAL': {'lat': 4.8681, 'lon': -75.6203},
    'LA VIRGINIA': {'lat': 4.9028, 'lon': -75.8828},
    'MARSELLA': {'lat': 4.9336, 'lon': -75.7392},
    'BELÉN DE UMBRÍA': {'lat': 5.1992, 'lon': -75.8753},
    'BELEN DE UMBRIA': {'lat': 5.1992, 'lon': -75.8753},
    'QUINCHÍA': {'lat': 5.3389, 'lon': -75.7289},
    'QUINCHIA': {'lat': 5.3389, 'lon': -75.7289},
    'APÍA': {'lat': 5.0972, 'lon': -75.9547},
    'APIA': {'lat': 5.0972, 'lon': -75.9547},
    'SANTUARIO': {'lat': 5.0586, 'lon': -75.9650},
    'PUEBLO RICO': {'lat': 5.2203, 'lon': -76.0142},
    'MISTRATÓ': {'lat': 5.1797, 'lon': -75.8886},
    'MISTRATO': {'lat': 5.1797, 'lon': -75.8886},
    'GUÁTICA': {'lat': 5.3089, 'lon': -75.7972},
    
    # Quindío
    'CALARCÁ': {'lat': 4.5294, 'lon': -75.6456},
    'CALARCA': {'lat': 4.5294, 'lon': -75.6456},
    'MONTENEGRO': {'lat': 4.5644, 'lon': -75.7508},
    'LA TEBAIDA': {'lat': 4.4472, 'lon': -75.7836},
    'CIRCASIA': {'lat': 4.6181, 'lon': -75.6372},
    'QUIMBAYA': {'lat': 4.6211, 'lon': -75.7694},
    'FILANDIA': {'lat': 4.6747, 'lon': -75.6564},
    'SALENTO': {'lat': 4.6381, 'lon': -75.5706},
    'GÉNOVA': {'lat': 4.2642, 'lon': -75.7747},
    'GENOVA': {'lat': 4.2642, 'lon': -75.7747},
    'CÓRDOBA': {'lat': 4.4000, 'lon': -75.6667},
    'CORDOBA': {'lat': 4.4000, 'lon': -75.6667},
    'PIJAO': {'lat': 4.3278, 'lon': -75.7083},
    'BUENAVISTA': {'lat': 4.3383, 'lon': -75.7597},

    # Caldas
    'CHINCHINÁ': {'lat': 4.9828, 'lon': -75.6036},
    'CHINCHINA': {'lat': 4.9828, 'lon': -75.6036},
    'VILLAMARÍA': {'lat': 5.0406, 'lon': -75.5136},
    'VILLAMARIA': {'lat': 5.0406, 'lon': -75.5136},
    'PALESTINA': {'lat': 5.0497, 'lon': -75.6508},
    'NEIRA': {'lat': 5.1650, 'lon': -75.5208},
    'LA DORADA': {'lat': 5.4514, 'lon': -74.6647},
    'RIOSUCIO': {'lat': 5.4222, 'lon': -75.7019},
    'SUPÍA': {'lat': 5.4550, 'lon': -75.6508},
    'SUPIA': {'lat': 5.4550, 'lon': -75.6508},
    'MARMATO': {'lat': 5.4764, 'lon': -75.6378},
    'ANSERMA': {'lat': 5.2378, 'lon': -75.7789},
    'VITERBO': {'lat': 5.0669, 'lon': -75.8742},
    'LA MERCED': {'lat': 5.3319, 'lon': -75.8769},
    'FILADELFIA': {'lat': 5.3039, 'lon': -75.5742},
    'ARANZAZU': {'lat': 5.2642, 'lon': -75.4769},
    'SALAMINA': {'lat': 5.4069, 'lon': -75.4886},
    'PÁCORA': {'lat': 5.5264, 'lon': -75.4606},
    'PACORA': {'lat': 5.5264, 'lon': -75.4606},
    'AGUADAS': {'lat': 5.6094, 'lon': -75.4608},
    'PENSILVANIA': {'lat': 5.3869, 'lon': -75.1628},
    'MARULANDA': {'lat': 5.2833, 'lon': -75.2333},
    'MANZANARES': {'lat': 5.2522, 'lon': -75.1578},
    'MARQUETALIA': {'lat': 5.2978, 'lon': -75.0411},
    'VICTORIA': {'lat': 5.3208, 'lon': -74.9206},
    'SAMANÁ': {'lat': 5.4072, 'lon': -75.0072},
    'SAMANA': {'lat': 5.4072, 'lon': -75.0072},

    # Tolima
    'ESPINAL': {'lat': 4.1489, 'lon': -74.8836},
    'MELGAR': {'lat': 4.2039, 'lon': -74.6389},
    'HONDA': {'lat': 5.2086, 'lon': -74.7358},
    'LÍBANO': {'lat': 4.9222, 'lon': -75.0639},
    'LIBANO': {'lat': 4.9222, 'lon': -75.0639},
    'CHAPARRAL': {'lat': 3.7244, 'lon': -75.4814},
    'MARIQUITA': {'lat': 5.1989, 'lon': -74.8911},
    'PURIFICACIÓN': {'lat': 3.8583, 'lon': -74.9308},
    'PURIFICACION': {'lat': 3.8583, 'lon': -74.9308},
    'FLANDES': {'lat': 4.2869, 'lon': -74.8164},
    'GUAMO': {'lat': 4.0306, 'lon': -74.9678},
    'SALDAÑA': {'lat': 3.9303, 'lon': -75.0178},
    'SALDANA': {'lat': 3.9303, 'lon': -75.0178},
    'ARMERO': {'lat': 5.0308, 'lon': -74.9039},
    'GUAYABAL': {'lat': 5.0167, 'lon': -74.9833},
    'LÉRIDA': {'lat': 4.8667, 'lon': -74.9333},
    'LERIDA': {'lat': 4.8667, 'lon': -74.9333},
    'AMBALEMA': {'lat': 4.7881, 'lon': -74.7644},
    'FRESNO': {'lat': 5.1567, 'lon': -75.0403},
    'FALAN': {'lat': 5.1181, 'lon': -75.0167},
    'PALOCABILDO': {'lat': 5.0833, 'lon': -75.0333},
    'CASABIANCA': {'lat': 5.0811, 'lon': -75.1006},
    'HERVEO': {'lat': 5.0886, 'lon': -75.1764},
    'VILLAHERMOSA': {'lat': 5.0742, 'lon': -75.1956},
    'SANTA ISABEL': {'lat': 4.8167, 'lon': -75.1167},
    'MURILLO': {'lat': 4.9133, 'lon': -75.1550},
    'ANZOÁTEGUI': {'lat': 4.5700, 'lon': -75.2989},
    'ANZOATEGUI': {'lat': 4.5700, 'lon': -75.2989},
    'ROVIRA': {'lat': 4.2406, 'lon': -75.2403},
    'VALLE DE SAN JUAN': {'lat': 4.2228, 'lon': -75.1528},
    'CARMEN DE APICALÁ': {'lat': 4.1483, 'lon': -74.7328},
    'CARMEN DE APICALA': {'lat': 4.1483, 'lon': -74.7328},
    'CUNDAY': {'lat': 4.0628, 'lon': -74.6836},
    'VILLARRICA': {'lat': 3.4728, 'lon': -76.0169},
    'ICONONZO': {'lat': 4.1789, 'lon': -74.5339},
    'PRADO': {'lat': 3.7464, 'lon': -74.9228},
    'DOLORES': {'lat': 3.1539, 'lon': -75.3403},
    'ALPUJARRA': {'lat': 3.4028, 'lon': -75.1378},
    'SUÁREZ': {'lat': 3.1672, 'lon': -75.3011},
    'SUAREZ': {'lat': 3.1672, 'lon': -75.3011},
    'NATAGAIMA': {'lat': 3.6817, 'lon': -75.0828},
    'COYAIMA': {'lat': 3.8028, 'lon': -75.1906},
    'ORTEGA': {'lat': 3.9594, 'lon': -75.2614},
    'SAN ANTONIO': {'lat': 3.5425, 'lon': -75.4464},
    'SAN LUIS': {'lat': 2.0167, 'lon': -76.0833},
    'PLANADAS': {'lat': 3.1964, 'lon': -75.6519},
    'RIOBLANCO': {'lat': 3.5175, 'lon': -75.7447},
    'ATACO': {'lat': 3.5939, 'lon': -75.3878},
    'RONCESVALLES': {'lat': 4.0111, 'lon': -75.6589},

    # Norte de Santander
    'OCAÑA': {'lat': 8.2378, 'lon': -73.3544},
    'PAMPLONA': {'lat': 7.3756, 'lon': -72.6486},
    'VILLA DEL ROSARIO': {'lat': 7.8353, 'lon': -72.4758},
    'LOS PATIOS': {'lat': 7.8372, 'lon': -72.5050},
    'SAN JOSÉ DE CÚCUTA': {'lat': 7.8939, 'lon': -72.5078},
    'SAN JOSE DE CUCUTA': {'lat': 7.8939, 'lon': -72.5078},
    'EL ZULIA': {'lat': 7.9272, 'lon': -72.6064},
    'SARDINATA': {'lat': 8.0764, 'lon': -72.7589},
    'TIBÚ': {'lat': 8.6400, 'lon': -72.7319},
    'TIBU': {'lat': 8.6400, 'lon': -72.7319},
    'CHINÁCOTA': {'lat': 7.5983, 'lon': -72.6089},
    'CHINACOTA': {'lat': 7.5983, 'lon': -72.6089},
    'BOCHALEMA': {'lat': 7.5878, 'lon': -72.6547},
    'DURANIA': {'lat': 7.7258, 'lon': -72.6758},
    'HERRÁN': {'lat': 7.5139, 'lon': -72.5247},
    'HERRAN': {'lat': 7.5139, 'lon': -72.5247},
    'RAGONVALIA': {'lat': 7.6075, 'lon': -72.4503},
    'TOLEDO': {'lat': 7.3019, 'lon': -72.4686},
    'LABATECA': {'lat': 7.3183, 'lon': -72.5325},
    'SILOS': {'lat': 7.3044, 'lon': -72.7142},
    'MUTISCUA': {'lat': 7.4139, 'lon': -72.7333},
    'CHITAGÁ': {'lat': 7.1225, 'lon': -72.6636},
    'CHITAGA': {'lat': 7.1225, 'lon': -72.6636},
    'CÁCHIRA': {'lat': 7.7453, 'lon': -73.0522},
    'CACHIRA': {'lat': 7.7453, 'lon': -73.0522},
    'ÁBREGO': {'lat': 8.1117, 'lon': -73.2267},
    'ABREGO': {'lat': 8.1117, 'lon': -73.2267},
    'LA PLAYA': {'lat': 8.2881, 'lon': -73.3519},
    'HACARÍ': {'lat': 8.3214, 'lon': -73.1361},
    'HACARI': {'lat': 8.3214, 'lon': -73.1361},
    'SAN CALIXTO': {'lat': 8.4011, 'lon': -73.2447},
    'TEORAMA': {'lat': 8.4625, 'lon': -73.2322},
    'EL TARRA': {'lat': 8.5600, 'lon': -73.0956},
    'CONVENCIÓN': {'lat': 8.4764, 'lon': -73.2611},
    'CONVENCION': {'lat': 8.4764, 'lon': -73.2611},
    'EL CARMEN': {'lat': 8.4700, 'lon': -73.4511},

    # Cesar
    'AGUACHICA': {'lat': 8.3106, 'lon': -73.6117},
    'BOSCONIA': {'lat': 9.9803, 'lon': -73.8944},
    'CODAZZI': {'lat': 10.0353, 'lon': -73.2406},
    'AGUSTÍN CODAZZI': {'lat': 10.0353, 'lon': -73.2406},
    'AGUSTIN CODAZZI': {'lat': 10.0353, 'lon': -73.2406},
    'CHIMICHAGUA': {'lat': 9.2606, 'lon': -73.8108},
    'CHIRIGUANÁ': {'lat': 9.3639, 'lon': -73.6064},
    'CHIRIGUANA': {'lat': 9.3639, 'lon': -73.6064},
    'CURUMANÍ': {'lat': 9.2017, 'lon': -73.5372},
    'CURUMANI': {'lat': 9.2017, 'lon': -73.5372},
    'EL COPEY': {'lat': 10.1472, 'lon': -73.9622},
    'GAMARRA': {'lat': 8.3342, 'lon': -73.7508},
    'GONZÁLEZ': {'lat': 8.3900, 'lon': -73.2783},
    'GONZALEZ': {'lat': 8.3900, 'lon': -73.2783},
    'LA GLORIA': {'lat': 8.5631, 'lon': -73.7683},
    'LA JAGUA DE IBIRICO': {'lat': 9.5633, 'lon': -73.3358},
    'MANAURE': {'lat': 10.3839, 'lon': -73.0256},
    'PAILITAS': {'lat': 8.9569, 'lon': -73.6253},
    'PELAYA': {'lat': 8.6881, 'lon': -73.6706},
    'PUEBLO BELLO': {'lat': 10.4153, 'lon': -73.5842},
    'RÍO DE ORO': {'lat': 8.2906, 'lon': -73.3889},
    'RIO DE ORO': {'lat': 8.2906, 'lon': -73.3889},
    'LA PAZ': {'lat': 10.3808, 'lon': -73.1886},
    'SAN ALBERTO': {'lat': 7.7650, 'lon': -73.3944},
    'SAN DIEGO': {'lat': 10.3347, 'lon': -73.1544},
    'SAN MARTÍN': {'lat': 7.9994, 'lon': -73.5169},
    'SAN MARTIN': {'lat': 7.9994, 'lon': -73.5169},
    'TAMALAMEQUE': {'lat': 8.8611, 'lon': -73.8119},
    'ASTREA': {'lat': 9.4983, 'lon': -73.9669},

    # Córdoba
    'CERETÉ': {'lat': 8.8850, 'lon': -75.7919},
    'CERETE': {'lat': 8.8850, 'lon': -75.7919},
    'LORICA': {'lat': 9.2400, 'lon': -75.8161},
    'SAHAGÚN': {'lat': 8.9456, 'lon': -75.4425},
    'SAHAGUN': {'lat': 8.9456, 'lon': -75.4425},
    'PLANET RICA': {'lat': 8.4097, 'lon': -75.5850},
    'MONTELÍBANO': {'lat': 7.9767, 'lon': -75.4244},
    'MONTELIBANO': {'lat': 7.9767, 'lon': -75.4244},
    'TIERRALTA': {'lat': 8.1719, 'lon': -76.0608},
    'CIÉNAGA DE ORO': {'lat': 8.8778, 'lon': -75.6208},
    'CIENAGA DE ORO': {'lat': 8.8778, 'lon': -75.6208},
    'SAN PELAYO': {'lat': 8.9572, 'lon': -75.8350},
    'COTORRA': {'lat': 9.0350, 'lon': -75.7975},
    'SAN BERNARDO DEL VIENTO': {'lat': 9.3517, 'lon': -75.9711},
    'MOÑITOS': {'lat': 9.2500, 'lon': -76.1311},
    'MONITOS': {'lat': 9.2500, 'lon': -76.1311},
    'SAN ANTERO': {'lat': 9.3742, 'lon': -75.7569},
    'PURÍSIMA': {'lat': 9.2192, 'lon': -75.7178},
    'PURISIMA': {'lat': 9.2192, 'lon': -75.7178},
    'MOMIL': {'lat': 9.2392, 'lon': -75.6714},
    'CHIMA': {'lat': 9.1561, 'lon': -75.6367},
    'CHINÚ': {'lat': 9.1103, 'lon': -75.3989},
    'CHINU': {'lat': 9.1103, 'lon': -75.3989},
    'TUCHÍN': {'lat': 9.1403, 'lon': -75.5692},
    'TUCHIN': {'lat': 9.1403, 'lon': -75.5692},
    'SAN ANDRÉS SOTAVENTO': {'lat': 9.1544, 'lon': -75.4947},
    'SAN ANDRES SOTAVENTO': {'lat': 9.1544, 'lon': -75.4947},
    'AYAPEL': {'lat': 8.3111, 'lon': -75.1417},
    'BUENAVISTA': {'lat': 8.3081, 'lon': -75.4431},
    'PUEBLO NUEVO': {'lat': 8.3794, 'lon': -75.3039},
    'LA APARTADA': {'lat': 8.0011, 'lon': -75.3522},
    'LOS CÓRDOBAS': {'lat': 8.7700, 'lon': -76.3178},
    'LOS CORDOBAS': {'lat': 8.7700, 'lon': -76.3178},
    'PUERTO ESCONDIDO': {'lat': 9.0300, 'lon': -76.2569},
    'SAN JOSÉ DE URÉ': {'lat': 7.7936, 'lon': -75.6428},
    'SAN JOSE DE URE': {'lat': 7.7936, 'lon': -75.6428},
    'VALENCIA': {'lat': 8.2339, 'lon': -76.1344},
    'CANALETE': {'lat': 8.7747, 'lon': -76.2575},

    # Sucre
    'SINCELEJO': {'lat': 9.3047, 'lon': -75.3978},
    'COROZAL': {'lat': 9.3200, 'lon': -75.2961},
    'SAMPUÉS': {'lat': 9.1819, 'lon': -75.3783},
    'SAMPUES': {'lat': 9.1819, 'lon': -75.3783},
    'SINCÉ': {'lat': 9.2497, 'lon': -75.1461},
    'SINCE': {'lat': 9.2497, 'lon': -75.1461},
    'SAN ONOFRE': {'lat': 9.7347, 'lon': -75.5256},
    'TOLÚ': {'lat': 9.5264, 'lon': -75.5847},
    'TOLU': {'lat': 9.5264, 'lon': -75.5847},
    'SANTIAGO DE TOLÚ': {'lat': 9.5264, 'lon': -75.5847},
    'COVEÑAS': {'lat': 9.4064, 'lon': -75.6806},
    'COVENAS': {'lat': 9.4064, 'lon': -75.6806},
    'TOLUVIEJO': {'lat': 9.4611, 'lon': -75.4172},
    'SAN BENITO ABAD': {'lat': 8.9356, 'lon': -75.0286},
    'MAJAGUAL': {'lat': 8.5397, 'lon': -74.6322},
    'SUCRE': {'lat': 8.8111, 'lon': -74.7211},
    'GUARANDA': {'lat': 8.4611, 'lon': -74.5733},
    'SAN MARCOS': {'lat': 8.6703, 'lon': -75.1472},
    'LA UNIÓN': {'lat': 9.3578, 'lon': -75.2550},
    'PALMITO': {'lat': 9.3756, 'lon': -75.1683},
    'MORROA': {'lat': 9.3322, 'lon': -75.3022},
    'OVEJAS': {'lat': 9.5322, 'lon': -75.2436},
    'CHALÁN': {'lat': 9.5178, 'lon': -75.3589},
    'CHALAN': {'lat': 9.5178, 'lon': -75.3589},
    'COLOSO': {'lat': 9.4944, 'lon': -75.3608},
    'SAN LUIS DE SINCÉ': {'lat': 9.2497, 'lon': -75.1461},
    'SAN LUIS DE SINCE': {'lat': 9.2497, 'lon': -75.1461},
    'GALERAS': {'lat': 9.3272, 'lon': -75.1703},
    'BUENAVISTA': {'lat': 9.3244, 'lon': -75.4378},
    'LOS PALMITOS': {'lat': 9.3756, 'lon': -75.1683},
    'SAN PEDRO': {'lat': 9.4094, 'lon': -75.2414},
    'SAN JUAN DE BETULIA': {'lat': 9.1881, 'lon': -75.2589},
    'CAIMITO': {'lat': 9.2486, 'lon': -75.1311},

    # Magdalena
    'CIÉNAGA': {'lat': 11.0086, 'lon': -74.2456},
    'CIENAGA': {'lat': 11.0086, 'lon': -74.2456},
    'FUNDACIÓN': {'lat': 10.5203, 'lon': -74.1853},
    'FUNDACION': {'lat': 10.5203, 'lon': -74.1853},
    'PLATO': {'lat': 9.7892, 'lon': -74.7878},
    'EL BANCO': {'lat': 9.0022, 'lon': -73.9758},
    'SANTA ANA': {'lat': 9.3181, 'lon': -74.5444},
    'ZONA BANANERA': {'lat': 10.7389, 'lon': -74.1508},
    'ARACATACA': {'lat': 10.5906, 'lon': -74.1842},
    'EL DIFÍCIL': {'lat': 10.5386, 'lon': -74.5211},
    'EL DIFICIL': {'lat': 10.5386, 'lon': -74.5211},
    'PIVIJAY': {'lat': 10.4628, 'lon': -74.6139},
    'SABANAS DE SAN ANGEL': {'lat': 10.2689, 'lon': -73.9747},
    'SITIONUEVO': {'lat': 10.7722, 'lon': -74.7250},
    'REMOLINO': {'lat': 10.7078, 'lon': -74.5936},
    'PUEBLO VIEJO': {'lat': 10.9964, 'lon': -74.2803},
    'SALAMINA': {'lat': 10.4875, 'lon': -74.7972},
    'CERRO SAN ANTONIO': {'lat': 10.3064, 'lon': -74.8539},
    'SAN ZENÓN': {'lat': 9.2528, 'lon': -74.5039},
    'SAN ZENON': {'lat': 9.2528, 'lon': -74.5039},
    'SANTA BÁRBARA DE PINTO': {'lat': 9.4353, 'lon': -74.6978},
    'SANTA BARBARA DE PINTO': {'lat': 9.4353, 'lon': -74.6978},
    'GUAMAL': {'lat': 9.1403, 'lon': -74.2278},
    'NUEVA GRANADA': {'lat': 9.8003, 'lon': -74.3931},
    'SAN SEBASTIÁN DE BUENAVISTA': {'lat': 9.9239, 'lon': -74.3961},
    'SAN SEBASTIAN DE BUENAVISTA': {'lat': 9.9239, 'lon': -74.3961},
    'ALGARROBO': {'lat': 10.1908, 'lon': -74.0728},
    'ARIGUANÍ': {'lat': 10.2536, 'lon': -74.0228},
    'ARIGUANI': {'lat': 10.2536, 'lon': -74.0228},
    'PIJIÑO DEL CARMEN': {'lat': 9.4000, 'lon': -74.4378},
    'PIJINO DEL CARMEN': {'lat': 9.4000, 'lon': -74.4378},
    'CONCORDIA': {'lat': 9.5289, 'lon': -74.8244},
    'TENERIFE': {'lat': 9.9803, 'lon': -74.8586},

    # La Guajira
    'MAICAO': {'lat': 11.3808, 'lon': -72.2403},
    'URIBIA': {'lat': 11.7092, 'lon': -72.2686},
    'MANAURE': {'lat': 11.7750, 'lon': -72.4453},
    'FONSECA': {'lat': 10.8908, 'lon': -72.8472},
    'SAN JUAN DEL CESAR': {'lat': 10.7711, 'lon': -73.0031},
    'VILLANUEVA': {'lat': 10.6072, 'lon': -72.9728},
    'DISTRACCIÓN': {'lat': 10.9150, 'lon': -72.9611},
    'DISTRACCION': {'lat': 10.9150, 'lon': -72.9611},
    'BARRANCAS': {'lat': 10.9642, 'lon': -72.7872},
    'HATONUEVO': {'lat': 11.0906, 'lon': -72.7706},
    'ALBANIA': {'lat': 11.0069, 'lon': -72.6136},
    'DIBULLA': {'lat': 11.2722, 'lon': -73.3086},
    'EL MOLINO': {'lat': 10.6531, 'lon': -72.9228},
    'URUMITA': {'lat': 10.5547, 'lon': -73.0156},
    'LA JAGUA DEL PILAR': {'lat': 10.3711, 'lon': -73.3264},

    # Huila
    'GARZÓN': {'lat': 2.1978, 'lon': -75.6278},
    'GARZON': {'lat': 2.1978, 'lon': -75.6278},
    'PITALITO': {'lat': 1.8539, 'lon': -76.0511},
    'LA PLATA': {'lat': 2.3878, 'lon': -75.8897},
    'CAMPOALEGRE': {'lat': 3.0089, 'lon': -75.3308},
    'HOBO': {'lat': 2.5636, 'lon': -75.4367},
    'GIGANTE': {'lat': 2.3778, 'lon': -75.5411},
    'ALGECIRAS': {'lat': 2.5372, 'lon': -75.3461},
    'AIPE': {'lat': 3.2186, 'lon': -75.2378},
    'YAGUARÁ': {'lat': 2.6625, 'lon': -75.5144},
    'YAGUARA': {'lat': 2.6625, 'lon': -75.5144},
    'PALERMO': {'lat': 2.8886, 'lon': -75.4422},
    'RIVERA': {'lat': 2.7742, 'lon': -75.2533},
    'BARAYA': {'lat': 3.4092, 'lon': -75.0636},
    'TELLO': {'lat': 3.0961, 'lon': -75.1744},
    'TERUEL': {'lat': 3.1122, 'lon': -75.6403},
    'PAICOL': {'lat': 2.4478, 'lon': -75.7569},
    'TESALIA': {'lat': 2.4889, 'lon': -75.7994},
    'ÍQUIRA': {'lat': 2.6422, 'lon': -75.6728},
    'IQUIRA': {'lat': 2.6422, 'lon': -75.6728},
    'NÁTAGA': {'lat': 2.9650, 'lon': -75.6644},
    'NATAGA': {'lat': 2.9650, 'lon': -75.6644},
    'ACEVEDO': {'lat': 1.7997, 'lon': -75.8850},
    'ELÍAS': {'lat': 2.0672, 'lon': -75.9736},
    'ELIAS': {'lat': 2.0672, 'lon': -75.9736},
    'ISNOS': {'lat': 1.9178, 'lon': -76.2322},
    'SALADOBLANCO': {'lat': 1.6236, 'lon': -76.1694},
    'OPORAPA': {'lat': 1.6711, 'lon': -76.0381},
    'SAN AGUSTÍN': {'lat': 1.8806, 'lon': -76.2703},
    'SAN AGUSTIN': {'lat': 1.8806, 'lon': -76.2703},
    'SUAZA': {'lat': 1.9708, 'lon': -75.8008},
    'ALTAMIRA': {'lat': 2.0350, 'lon': -76.0978},
    'GUADALUPE': {'lat': 2.2422, 'lon': -75.7694},
    'TIMANÁ': {'lat': 1.9714, 'lon': -75.9481},
    'TIMANA': {'lat': 1.9714, 'lon': -75.9481},
    'TARQUI': {'lat': 1.8689, 'lon': -75.8328},
    'AGRADO': {'lat': 2.3283, 'lon': -75.8464},
    'SANTA MARÍA': {'lat': 3.0856, 'lon': -75.5736},
    'SANTA MARIA': {'lat': 3.0856, 'lon': -75.5736},
    'COLOMBIA': {'lat': 3.3978, 'lon': -74.9944},
    # Cauca
    'SANTANDER DE QUILICHAO': {'lat': 3.0089, 'lon': -76.4842},
    'PUERTO TEJADA': {'lat': 3.2314, 'lon': -76.4161},
    'VILLA RICA': {'lat': 3.2022, 'lon': -76.5028},
    'CALOTO': {'lat': 3.0200, 'lon': -76.3311},
    'MIRANDA': {'lat': 3.2536, 'lon': -76.2306},
    'CORINTO': {'lat': 3.1739, 'lon': -76.2636},
    'PATÍA': {'lat': 2.0714, 'lon': -77.0644},
    'PATIA': {'lat': 2.0714, 'lon': -77.0644},
    'PIENDAMÓ': {'lat': 2.6394, 'lon': -76.9886},
    'PIENDAMO': {'lat': 2.6394, 'lon': -76.9886},
    'SILVIA': {'lat': 2.6150, 'lon': -76.3806},
    'TOTORÓ': {'lat': 2.5058, 'lon': -76.3550},
    'TOTORO': {'lat': 2.5058, 'lon': -76.3550},
    'CAJIBÍO': {'lat': 2.6211, 'lon': -76.5689},
    'CAJIBIO': {'lat': 2.6211, 'lon': -76.5689},
    'ROSAS': {'lat': 2.4772, 'lon': -77.1422},
    'BOLÍVAR': {'lat': 1.8831, 'lon': -77.1836},
    'BOLIVAR': {'lat': 1.8831, 'lon': -77.1836},
    'MERCADERES': {'lat': 2.0086, 'lon': -77.1711},
    'BALBOA': {'lat': 1.9811, 'lon': -77.2814},
    'SUCRE': {'lat': 2.0433, 'lon': -76.9228},
    'EL TAMBO': {'lat': 2.4500, 'lon': -76.8167},
    'TIMBÍO': {'lat': 2.3522, 'lon': -76.6828},
    'TIMBIO': {'lat': 2.3522, 'lon': -76.6828},
    'MORALES': {'lat': 2.7928, 'lon': -76.6289},
    'JAMBALÓ': {'lat': 2.7550, 'lon': -76.1917},
    'JAMBALO': {'lat': 2.7550, 'lon': -76.1917},
    'TORIBÍO': {'lat': 2.8161, 'lon': -76.0733},
    'TORIBIO': {'lat': 2.8161, 'lon': -76.0733},
    'CALDONO': {'lat': 2.8089, 'lon': -76.4772},
    'INZÁ': {'lat': 2.5467, 'lon': -76.0706},
    'INZA': {'lat': 2.5467, 'lon': -76.0706},
    'PÁEZ': {'lat': 2.6042, 'lon': -76.0056},
    'PAEZ': {'lat': 2.6042, 'lon': -76.0056},
    'BELALCÁZAR': {'lat': 2.9886, 'lon': -76.7972},
    'BELALCAZAR': {'lat': 2.9886, 'lon': -76.7972},
    'BUENOS AIRES': {'lat': 3.0372, 'lon': -76.5939},
    'SUÁREZ': {'lat': 2.6619, 'lon': -76.9064},
    'SUAREZ': {'lat': 2.6619, 'lon': -76.9064},
    'LÓPEZ': {'lat': 2.2236, 'lon': -77.0342},
    'LOPEZ': {'lat': 2.2236, 'lon': -77.0342},
    'TIMBIQUÍ': {'lat': 2.7742, 'lon': -77.6619},
    'TIMBIQUI': {'lat': 2.7742, 'lon': -77.6619},
    'GUAPI': {'lat': 2.5714, 'lon': -77.8911},

    # Nariño
    'IPIALES': {'lat': 0.8272, 'lon': -77.6422},
    'TUMACO': {'lat': 1.8014, 'lon': -78.7989},
    'TÚQUERRES': {'lat': 1.0878, 'lon': -77.6242},
    'TUQUERRES': {'lat': 1.0878, 'lon': -77.6242},
    'SAMANIEGO': {'lat': 1.3328, 'lon': -77.5906},
    'LA UNIÓN': {'lat': 1.6042, 'lon': -77.1300},
    'LA UNION': {'lat': 1.6042, 'lon': -77.1300},
    'SAN PABLO': {'lat': 1.0933, 'lon': -77.0672},
    'SANDONÁ': {'lat': 1.2831, 'lon': -77.4711},
    'SANDONA': {'lat': 1.2831, 'lon': -77.4711},
    'LA CRUZ': {'lat': 1.6072, 'lon': -77.0328},
    'SAN BERNARDO': {'lat': 1.5211, 'lon': -77.0433},
    'BELÉN': {'lat': 1.6328, 'lon': -77.1311},
    'BELEN': {'lat': 1.6328, 'lon': -77.1311},
    'CONSACÁ': {'lat': 1.2122, 'lon': -77.4608},
    'CONSACA': {'lat': 1.2122, 'lon': -77.4608},
    'EL TABLÓN DE GÓMEZ': {'lat': 1.4422, 'lon': -77.0872},
    'EL TABLON DE GOMEZ': {'lat': 1.4422, 'lon': -77.0872},
    'TANGUA': {'lat': 1.0997, 'lon': -77.5331},
    'FUNES': {'lat': 1.0583, 'lon': -77.3644},
    'GUAITARILLA': {'lat': 1.1439, 'lon': -77.5569},
    'CUMBAL': {'lat': 0.9111, 'lon': -77.7956},
    'ALDANA': {'lat': 0.9164, 'lon': -77.6769},
    'CARLOSAMA': {'lat': 0.8656, 'lon': -77.6869},
    'CONTADERO': {'lat': 0.7408, 'lon': -77.4328},
    'CUASPUD': {'lat': 0.8106, 'lon': -77.6600},
    'CÓRDOBA': {'lat': 1.6917, 'lon': -77.4000},
    'CORDOBA': {'lat': 1.6917, 'lon': -77.4000},
    'POTOSÍ': {'lat': 0.8117, 'lon': -77.5556},
    'POTOSI': {'lat': 0.8117, 'lon': -77.5556},
    'GUACHUCAL': {'lat': 0.9722, 'lon': -77.7089},
    'PUPIALES': {'lat': 0.8633, 'lon': -77.6317},
    'GUALMATÁN': {'lat': 0.9200, 'lon': -77.5581},
    'GUALMATAN': {'lat': 0.9200, 'lon': -77.5581},
    'ILES': {'lat': 0.9456, 'lon': -77.4747},
    'SAPUYES': {'lat': 1.0150, 'lon': -77.6803},
    'MALLAMA': {'lat': 0.9194, 'lon': -77.8839},
    'RICAURTE': {'lat': 1.2133, 'lon': -77.9589},
    'BARBACOAS': {'lat': 1.6642, 'lon': -78.1408},
    'MAGÜÍ': {'lat': 1.7306, 'lon': -78.5489},
    'MAGUI': {'lat': 1.7306, 'lon': -78.5489},
    'SANTA BÁRBARA': {'lat': 1.9506, 'lon': -78.0758},
    'SANTA BARBARA': {'lat': 1.9506, 'lon': -78.0758},
    'FRANCISCO PIZARRO': {'lat': 1.9358, 'lon': -78.6911},
    'ROBERTO PAYÁN': {'lat': 1.8536, 'lon': -78.2911},
    'ROBERTO PAYAN': {'lat': 1.8536, 'lon': -78.2911},
    'EL CHARCO': {'lat': 2.4792, 'lon': -78.1092},
    'LA TOLA': {'lat': 2.4228, 'lon': -78.4206},
    'MOSQUERA': {'lat': 2.5328, 'lon': -78.4550},
    'OLAYA HERRERA': {'lat': 2.4461, 'lon': -78.4383},
    'SANTA CRUZ': {'lat': 2.3056, 'lon': -78.1631},
    'LEIVA': {'lat': 1.8728, 'lon': -77.2922},
    'POLICARPA': {'lat': 1.5497, 'lon': -77.4564},
    'CUMBITARA': {'lat': 1.7244, 'lon': -77.5658},
    'LOS ANDES': {'lat': 1.6508, 'lon': -77.6731},
    'EL PEÑOL': {'lat': 1.4847, 'lon': -77.4428},
    'EL PENOL': {'lat': 1.4847, 'lon': -77.4428},
    'EL ROSARIO': {'lat': 1.7936, 'lon': -77.3856},
    'COLÓN': {'lat': 1.1606, 'lon': -77.2569},
    'COLON': {'lat': 1.1606, 'lon': -77.2569},
    'SAN LORENZO': {'lat': 1.3606, 'lon': -77.2369},
    'ARBOLEDA': {'lat': 1.4592, 'lon': -77.1611},
    'SAN JOSÉ DE ALBÁN': {'lat': 1.2269, 'lon': -77.2031},
    'SAN JOSE DE ALBAN': {'lat': 1.2269, 'lon': -77.2031},
    'ANCUYÁ': {'lat': 1.2778, 'lon': -77.5042},
    'ANCUYA': {'lat': 1.2778, 'lon': -77.5042},
    'LINARES': {'lat': 1.3742, 'lon': -77.5181},
    'PROVIDENCIA': {'lat': 0.8200, 'lon': -77.5847},
    'LA FLORIDA': {'lat': 1.3336, 'lon': -77.4206},
    'NARIÑO': {'lat': 1.2856, 'lon': -77.2814},
    'YACUANQUER': {'lat': 1.1253, 'lon': -77.4050},
    'IMUÉS': {'lat': 0.8769, 'lon': -77.5181},
    'IMUES': {'lat': 0.8769, 'lon': -77.5181},
    'OSPINA': {'lat': 0.9294, 'lon': -77.5967},
    'PUERRES': {'lat': 0.8022, 'lon': -77.2931},

    # Putumayo
    'MOCOA': {'lat': 1.1514, 'lon': -76.6464},
    'PUERTO ASÍS': {'lat': 0.5097, 'lon': -76.4997},
    'PUERTO ASIS': {'lat': 0.5097, 'lon': -76.4997},
    'VALLE DEL GUAMUEZ': {'lat': 0.4789, 'lon': -76.8978},
    'SAN MIGUEL': {'lat': 0.3619, 'lon': -76.9008},
    'ORITO': {'lat': 0.6658, 'lon': -76.8592},
    'PUERTO GUZMÁN': {'lat': 1.0722, 'lon': -76.4956},
    'PUERTO GUZMAN': {'lat': 1.0722, 'lon': -76.4956},
    'PUERTO CAICEDO': {'lat': 0.6614, 'lon': -76.3961},
    'PUERTO LEGUÍZAMO': {'lat': -0.1933, 'lon': -74.7811},
    'PUERTO LEGUIZAMO': {'lat': -0.1933, 'lon': -74.7811},
    'VILLAGARZÓN': {'lat': 1.0306, 'lon': -76.6189},
    'VILLAGARZON': {'lat': 1.0306, 'lon': -76.6189},
    'SIBUNDOY': {'lat': 1.1508, 'lon': -76.9336},
    'SAN FRANCISCO': {'lat': 1.1789, 'lon': -76.8872},
    'SANTIAGO': {'lat': 1.1356, 'lon': -76.8772},
    'COLÓN': {'lat': 1.1867, 'lon': -76.9800},

    # Caquetá
    'SAN VICENTE DEL CAGUÁN': {'lat': 2.1119, 'lon': -74.7650},
    'SAN VICENTE DEL CAGUAN': {'lat': 2.1119, 'lon': -74.7650},
    'PUERTO RICO': {'lat': 1.9211, 'lon': -75.1533},
    'EL PAUJÍL': {'lat': 1.5847, 'lon': -75.2742},
    'EL PAUJIL': {'lat': 1.5847, 'lon': -75.2742},
    'EL DONCELLO': {'lat': 1.6897, 'lon': -75.2886},
    'LA MONTAÑITA': {'lat': 1.4803, 'lon': -75.4047},
    'LA MONTANITA': {'lat': 1.4803, 'lon': -75.4047},
    'MILÁN': {'lat': 1.2681, 'lon': -75.3647},
    'MILAN': {'lat': 1.2681, 'lon': -75.3647},
    'VALPARAÍSO': {'lat': 0.7542, 'lon': -75.4367},
    'MORELIA': {'lat': 1.4903, 'lon': -75.6833},
    'BELÉN DE LOS ANDAQUÍES': {'lat': 1.4153, 'lon': -75.8642},
    'BELEN DE LOS ANDAQUIES': {'lat': 1.4153, 'lon': -75.8642},
    'SAN JOSÉ DEL FRAGUA': {'lat': 1.3136, 'lon': -76.0258},
    'SAN JOSE DEL FRAGUA': {'lat': 1.3136, 'lon': -76.0258},
    'ALBANIA': {'lat': 1.0350, 'lon': -76.1189},
    'CURILLO': {'lat': 1.2275, 'lon': -76.0953},
    'CARTAGENA DEL CHAIRÁ': {'lat': 1.3389, 'lon': -74.8603},
    'CARTAGENA DEL CHAIRA': {'lat': 1.3389, 'lon': -74.8603},
    'SOLANO': {'lat': 0.7069, 'lon': -75.2628},
    'SOLITA': {'lat': 1.1000, 'lon': -75.6333},

    # Meta
    'ACACÍAS': {'lat': 3.9881, 'lon': -73.7594},
    'ACACIAS': {'lat': 3.9881, 'lon': -73.7594},
    'GRANADA': {'lat': 3.5381, 'lon': -73.7081},
    'SAN MARTÍN': {'lat': 3.6953, 'lon': -73.6981},
    'SAN MARTIN': {'lat': 3.6953, 'lon': -73.6981},
    'PUERTO LÓPEZ': {'lat': 4.0856, 'lon': -72.9572},
    'PUERTO LOPEZ': {'lat': 4.0856, 'lon': -72.9572},
    'PUERTO GAITÁN': {'lat': 4.3164, 'lon': -72.0844},
    'PUERTO GAITAN': {'lat': 4.3164, 'lon': -72.0844},
    'CUMARAL': {'lat': 4.2711, 'lon': -73.4869},
    'PUERTO LLERAS': {'lat': 3.2728, 'lon': -73.3872},
    'RESTREPO': {'lat': 4.2611, 'lon': -73.5733},
    'GUAMAL': {'lat': 3.8839, 'lon': -73.7636},
    'CASTILLA LA NUEVA': {'lat': 3.8125, 'lon': -73.6764},
    'SAN CARLOS DE GUAROA': {'lat': 3.6814, 'lon': -73.2431},
    'PUERTO RICO': {'lat': 2.9464, 'lon': -73.0064},
    'LEJANÍAS': {'lat': 3.5336, 'lon': -74.0122},
    'LEJANIAS': {'lat': 3.5336, 'lon': -74.0122},
    'EL CALVARIO': {'lat': 4.3917, 'lon': -73.7600},
    'SAN JUANITO': {'lat': 4.4553, 'lon': -73.6814},
    'CABUYARO': {'lat': 4.2889, 'lon': -72.7781},
    'BARRANCA DE UPÍA': {'lat': 4.5183, 'lon': -72.9606},
    'BARRANCA DE UPIA': {'lat': 4.5183, 'lon': -72.9606},
    'FUENTE DE ORO': {'lat': 3.4597, 'lon': -73.6089},
    'SAN JUAN DE ARAMA': {'lat': 3.3739, 'lon': -73.8728},
    'MESETAS': {'lat': 3.3878, 'lon': -73.9828},
    'LA MACARENA': {'lat': 2.1833, 'lon': -73.7833},
    'URIBE': {'lat': 3.2675, 'lon': -74.2456},
    'VISTAHERMOSA': {'lat': 3.1300, 'lon': -73.7111},
    'MAPIRIPÁN': {'lat': 2.8833, 'lon': -72.1333},
    'MAPIRIPAN': {'lat': 2.8833, 'lon': -72.1333},
    'EL CASTILLO': {'lat': 3.6042, 'lon': -73.7797},

    # Casanare
    'PAZ DE ARIPORO': {'lat': 5.8778, 'lon': -71.8878},
    'AGUAZUL': {'lat': 5.1728, 'lon': -72.5508},
    'VILLANUEVA': {'lat': 4.5858, 'lon': -72.9403},
    'TAURAMENA': {'lat': 5.0131, 'lon': -72.7444},
    'MONTERREY': {'lat': 4.8797, 'lon': -72.8900},
    'TRINIDAD': {'lat': 5.4342, 'lon': -71.6636},
    'SAN LUIS DE PALENQUE': {'lat': 5.4331, 'lon': -71.0844},
    'MANÍ': {'lat': 4.8144, 'lon': -72.2831},
    'MANI': {'lat': 4.8144, 'lon': -72.2831},
    'SABANALARGA': {'lat': 4.7628, 'lon': -72.9214},
    'PORE': {'lat': 5.7631, 'lon': -71.9519},
    'NUNCHÍA': {'lat': 5.7125, 'lon': -72.1503},
    'NUNCHIA': {'lat': 5.7125, 'lon': -72.1503},
    'TÁMARA': {'lat': 5.9728, 'lon': -71.7456},
    'TAMARA': {'lat': 5.9728, 'lon': -71.7456},
    'HATO COROZAL': {'lat': 6.1639, 'lon': -71.7536},
    'LA SALINA': {'lat': 5.3844, 'lon': -71.9711},
    'CHÁMEZA': {'lat': 5.2214, 'lon': -72.8314},
    'CHAMEZA': {'lat': 5.2214, 'lon': -72.8314},
    'RECETOR': {'lat': 5.3592, 'lon': -72.9228},
    'OROCUÉ': {'lat': 4.7911, 'lon': -71.3422},
    'OROCUE': {'lat': 4.7911, 'lon': -71.3422},

    # Boyacá
    'DUITAMA': {'lat': 5.8267, 'lon': -73.0339},
    'SOGAMOSO': {'lat': 5.7147, 'lon': -72.9342},
    'CHIQUINQUIRÁ': {'lat': 5.6181, 'lon': -73.8200},
    'PUERTO BOYACÁ': {'lat': 5.9761, 'lon': -74.5847},
    'PUERTO BOYACA': {'lat': 5.9761, 'lon': -74.5847},
    'PAIPA': {'lat': 5.7781, 'lon': -73.1139},
    'VILLA DE LEYVA': {'lat': 5.6389, 'lon': -73.5261},
    'MONIQUIRÁ': {'lat': 5.8778, 'lon': -73.5739},
    'MONIQUIRA': {'lat': 5.8778, 'lon': -73.5739},
    'SAMACÁ': {'lat': 5.4911, 'lon': -73.4894},
    'SAMACA': {'lat': 5.4911, 'lon': -73.4894},
    'VENTAQUEMADA': {'lat': 5.3617, 'lon': -73.5347},
    'TIBASOSA': {'lat': 5.7467, 'lon': -72.9953},
    'NOBSA': {'lat': 5.7722, 'lon': -72.9461},
    'GARAGOA': {'lat': 5.0794, 'lon': -73.3636},
    'GUATEQUE': {'lat': 5.0186, 'lon': -73.4406},
    'RAMIRIQUÍ': {'lat': 5.3939, 'lon': -73.3297},
    'RAMIRIQUI': {'lat': 5.3939, 'lon': -73.3297},
    'RÁQUIRA': {'lat': 5.5381, 'lon': -73.6336},
    'RAQUIRA': {'lat': 5.5381, 'lon': -73.6336},
    'SANTA ROSA DE VITERBO': {'lat': 5.8814, 'lon': -72.9875},
    'CORRALES': {'lat': 6.0150, 'lon': -72.8947},
    'BETÉITIVA': {'lat': 5.9400, 'lon': -72.8033},
    'BETEITIVA': {'lat': 5.9400, 'lon': -72.8033},
    'PAZ DE RÍO': {'lat': 5.9769, 'lon': -72.7608},
    'PAZ DE RIO': {'lat': 5.9769, 'lon': -72.7608},
    'TASCO': {'lat': 5.9486, 'lon': -72.7756},
    'SOCOTÁ': {'lat': 6.0572, 'lon': -72.6428},
    'SOCOTA': {'lat': 6.0572, 'lon': -72.6428},
    'SOCHA': {'lat': 5.9994, 'lon': -72.6894},
    'FIRAVITOBA': {'lat': 5.6761, 'lon': -72.9903},
    'IZA': {'lat': 5.6247, 'lon': -72.9725},
    'TÓPAGA': {'lat': 5.7681, 'lon': -72.8739},
    'TOPAGA': {'lat': 5.7681, 'lon': -72.8739},
    'MONGUÍ': {'lat': 5.7289, 'lon': -72.8392},
    'MONGUI': {'lat': 5.7289, 'lon': -72.8392},
    'MONGUA': {'lat': 5.7306, 'lon': -72.8108},
    'GÁMEZA': {'lat': 5.8036, 'lon': -72.7742},
    'GAMEZA': {'lat': 5.8036, 'lon': -72.7742},
    'AQUITANIA': {'lat': 5.5217, 'lon': -72.8989},
    'TOTA': {'lat': 5.5606, 'lon': -72.9792},
    'CUíTIVA': {'lat': 5.6169, 'lon': -72.9542},
    'CUITIVA': {'lat': 5.6169, 'lon': -72.9542},
    'BELÉN': {'lat': 5.9728, 'lon': -72.8525},
    'CERINZA': {'lat': 5.9581, 'lon': -72.9172},
    'TUTAZÁ': {'lat': 6.0636, 'lon': -72.8503},
    'TUTAZA': {'lat': 6.0636, 'lon': -72.8503},
    'FLORESTA': {'lat': 6.0261, 'lon': -72.9178},
    'BUSBANZÁ': {'lat': 6.0372, 'lon': -72.9017},
    'BUSBANZA': {'lat': 6.0372, 'lon': -72.9017},
    'SUSACÓN': {'lat': 6.2361, 'lon': -72.6772},
    'SUSACON': {'lat': 6.2361, 'lon': -72.6772},
    'SOATÁ': {'lat': 6.3456, 'lon': -72.6803},
    'SOATA': {'lat': 6.3456, 'lon': -72.6803},
    'BOAVITA': {'lat': 6.3000, 'lon': -72.5733},
    'LA UVITA': {'lat': 6.2667, 'lon': -72.5594},
    'COVARACHÍA': {'lat': 6.3911, 'lon': -72.6569},
    'COVARACHIA': {'lat': 6.3911, 'lon': -72.6569},
    'TIPACOQUE': {'lat': 6.4300, 'lon': -72.7317},
    'SAN MATEO': {'lat': 6.3828, 'lon': -72.7403},
    'SATIVANORTE': {'lat': 6.1481, 'lon': -72.7758},
    'SATIVASUR': {'lat': 6.1211, 'lon': -72.7192},
    'GUACAMAYAS': {'lat': 6.4683, 'lon': -72.5342},
    'GÜICÁN': {'lat': 6.4083, 'lon': -72.4114},
    'GUICAN': {'lat': 6.4083, 'lon': -72.4114},
    'EL COCUY': {'lat': 6.4114, 'lon': -72.4464},
    'CHITA': {'lat': 6.1786, 'lon': -72.4889},
    'EL ESPINO': {'lat': 6.2236, 'lon': -72.5439},
    'CUBARÁ': {'lat': 7.0228, 'lon': -72.0736},
    'CUBARA': {'lat': 7.0228, 'lon': -72.0736},
    'PISBA': {'lat': 5.7722, 'lon': -72.4289},
    'LABRANZAGRANDE': {'lat': 5.5594, 'lon': -72.5758},
    'PÁJAROS': {'lat': 5.3186, 'lon': -72.6606},
    'PAJAROS': {'lat': 5.3186, 'lon': -72.6606},
    'MIRAFLORES': {'lat': 5.1869, 'lon': -73.1439},
    'ZETAQUIRA': {'lat': 5.3458, 'lon': -73.0842},
    'BERBEO': {'lat': 5.1856, 'lon': -73.0606},
    'CAMPOHERMOSO': {'lat': 5.0372, 'lon': -73.0806},
    'SAN EDUARDO': {'lat': 4.6958, 'lon': -73.1017},
    'SANTA MARÍA': {'lat': 4.8597, 'lon': -73.2611},
    'QUÍPAMA': {'lat': 5.5253, 'lon': -74.1744},
    'QUIPAMA': {'lat': 5.5253, 'lon': -74.1744},
    'MUZO': {'lat': 5.5339, 'lon': -74.1042},
    'MARIPÍ': {'lat': 5.5514, 'lon': -74.0400},
    'MARIPI': {'lat': 5.5514, 'lon': -74.0400},
    'COPER': {'lat': 5.4311, 'lon': -74.2292},
    'PAUNA': {'lat': 5.6500, 'lon': -74.1006},
    'BRICEÑO': {'lat': 5.7228, 'lon': -73.9006},
    'BRICENO': {'lat': 5.7228, 'lon': -73.9006},
    'TUNUNGUA': {'lat': 5.7806, 'lon': -73.9278},
    'BUENAVISTA': {'lat': 5.5431, 'lon': -73.9703},
    'SAN PABLO DE BORBUR': {'lat': 5.7214, 'lon': -74.0528},
    'OTANCHE': {'lat': 5.6739, 'lon': -74.1861},
    'TUNUNGUÁ': {'lat': 5.7806, 'lon': -73.9278},
    'TOGÜÍ': {'lat': 5.9392, 'lon': -73.5136},
    'TOGUI': {'lat': 5.9392, 'lon': -73.5136},
    'SABOYÁ': {'lat': 5.7361, 'lon': -73.7828},
    'SABOYA': {'lat': 5.7361, 'lon': -73.7828},
    'SANTANA': {'lat': 6.0806, 'lon': -73.7589},
    'SAN MIGUEL DE SEMA': {'lat': 5.5372, 'lon': -73.9961},
    'CALDAS': {'lat': 5.5828, 'lon': -73.8872},
    'VILLA DE SAN DIEGO DE UBATE': {'lat': 5.3117, 'lon': -73.8156},
    'VILLA DE SAN DIEGO DE UBAT': {'lat': 5.3117, 'lon': -73.8156},

    # Arauca
    'ARAUQUITA': {'lat': 7.0247, 'lon': -71.4297},
    'FORTUL': {'lat': 6.6650, 'lon': -71.8389},
    'TAME': {'lat': 6.4581, 'lon': -71.7403},
    'SARAVENA': {'lat': 6.9547, 'lon': -71.8831},
    'PUERTO RONDÓN': {'lat': 5.2611, 'lon': -71.7856},
    'PUERTO RONDON': {'lat': 5.2611, 'lon': -71.7856},
    'CRAVO NORTE': {'lat': 6.3169, 'lon': -70.2078},

    # Vichada
    'CUMARIBO': {'lat': 4.4547, 'lon': -69.8078},
    'LA PRIMAVERA': {'lat': 5.4617, 'lon': -70.3492},
    'SANTA ROSALÍA': {'lat': 3.5086, 'lon': -70.5194},
    'SANTA ROSALIA': {'lat': 3.5086, 'lon': -70.5194},

    # Guainía
    'BARRANCO MINAS': {'lat': 1.5639, 'lon': -69.8761},
    'CACAHUAL': {'lat': 3.1239, 'lon': -67.7406},
    'LA GUADALUPE': {'lat': 2.5833, 'lon': -69.9167},
    'MORICHAL': {'lat': 3.0167, 'lon': -68.2833},
    'PANA PANA': {'lat': 2.4333, 'lon': -68.8500},
    'PUERTO COLOMBIA': {'lat': 2.9833, 'lon': -68.3000},
    'SAN FELIPE': {'lat': 3.3667, 'lon': -67.3333},

    # Guaviare
    'CALAMAR': {'lat': 1.9511, 'lon': -72.6619},
    'EL RETORNO': {'lat': 2.3261, 'lon': -72.6283},
    'MIRAFLORES': {'lat': 1.3333, 'lon': -71.9667},

    # Vaupés
    'CARURÚ': {'lat': 1.1167, 'lon': -71.0667},
    'CARURU': {'lat': 1.1167, 'lon': -71.0667},
    'PACOA': {'lat': 0.5333, 'lon': -70.2500},
    'TARAIRA': {'lat': 0.6167, 'lon': -69.8167},
    'PAPUNAHUA': {'lat': 1.0500, 'lon': -70.3833},
    'YAVARATÉ': {'lat': 0.6000, 'lon': -69.1667},
    'YAVARATE': {'lat': 0.6000, 'lon': -69.1667},

    # Amazonas
    'LETICIA': {'lat': -4.2153, 'lon': -69.9406},
    'PUERTO NARIÑO': {'lat': -3.7714, 'lon': -70.3858},
    'PUERTO NARINO': {'lat': -3.7714, 'lon': -70.3858},
    'PUERTO ALEGRÍA': {'lat': -4.0667, 'lon': -69.9500},
    'PUERTO ALEGRIA': {'lat': -4.0667, 'lon': -69.9500},
    'LA CHORRERA': {'lat': -0.7333, 'lon': -73.0167},
    'LA PEDRERA': {'lat': -1.3167, 'lon': -69.5833},
    'MIRITI PARANÁ': {'lat': -1.1833, 'lon': -72.4167},
    'MIRITI PARANA': {'lat': -1.1833, 'lon': -72.4167},
    'PUERTO ARICA': {'lat': -0.9833, 'lon': -71.7000},
    'PUERTO SANTANDER': {'lat': -0.2500, 'lon': -72.4167},
    'TARAPACÁ': {'lat': -2.8833, 'lon': -69.7333},
    'TARAPACA': {'lat': -2.8833, 'lon': -69.7333},
    'EL ENCANTO': {'lat': -1.7333, 'lon': -73.1833},
}

@st.cache_data
def cargar_datos_google_sheets(url, hoja_nombre, fila_inicio=0, tiene_encabezados=True):
    """Carga datos desde Google Sheets"""
    try:
        sheet_id = url.split('/d/')[1].split('/')[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={quote(hoja_nombre)}"
        
        if tiene_encabezados:
            # Cargar saltando filas hasta los encabezados
            df = pd.read_csv(csv_url, skiprows=fila_inicio)
        else:
            df = pd.read_csv(csv_url, header=None, skiprows=fila_inicio)
        
        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return None
    
def procesar_datos_ventas(url):
    """Procesa y limpia los datos de ventas y devoluciones"""
    
    # Cargar datos 2025 (encabezados en fila 7, índice 6)
    df_2025_completo = cargar_datos_google_sheets(url, "SIIGO 2025", fila_inicio=0, tiene_encabezados=True)
    
    if df_2025_completo is None:
        return None, None, None, None
    
    # Separar ventas (columnas A-P, 0-15) y devoluciones (columnas R-AB, 17-27)
    ventas_2025 = df_2025_completo.iloc[:, 0:16].copy()
    devoluciones_2025 = df_2025_completo.iloc[:, 17:28].copy()
    
    # Limpiar columnas
    ventas_2025 = limpiar_columnas(ventas_2025)
    devoluciones_2025 = limpiar_columnas(devoluciones_2025)
    
    # Limpiar valores #N/D sin eliminar filas
    ventas_2025 = limpiar_valores_nd(ventas_2025)
    devoluciones_2025 = limpiar_valores_nd(devoluciones_2025)
    
    # Limpiar filas vacías DESPUÉS de limpiar columnas
    ventas_2025 = ventas_2025.dropna(how='all')
    ventas_2025 = ventas_2025[ventas_2025.iloc[:, 0].notna()].reset_index(drop=True)
    
    devoluciones_2025 = devoluciones_2025.dropna(how='all')
    devoluciones_2025 = devoluciones_2025[devoluciones_2025.iloc[:, 0].notna()].reset_index(drop=True)
    
    # Cargar datos 2024 (encabezados en fila 1, índice 0)
    df_2024_completo = cargar_datos_google_sheets(url, "SIIGO 2024", fila_inicio=0, tiene_encabezados=True)
    
    if df_2024_completo is not None:
        ventas_2024 = df_2024_completo.iloc[:, 0:16].copy()
        devoluciones_2024 = df_2024_completo.iloc[:, 17:28].copy()
        
        ventas_2024 = limpiar_columnas(ventas_2024)
        devoluciones_2024 = limpiar_columnas(devoluciones_2024)
        
        # Limpiar valores #N/D sin eliminar filas
        ventas_2024 = limpiar_valores_nd(ventas_2024)
        devoluciones_2024 = limpiar_valores_nd(devoluciones_2024)
        
        ventas_2024 = ventas_2024.dropna(how='all')
        ventas_2024 = ventas_2024[ventas_2024.iloc[:, 0].notna()].reset_index(drop=True)
        
        devoluciones_2024 = devoluciones_2024.dropna(how='all')
        devoluciones_2024 = devoluciones_2024[devoluciones_2024.iloc[:, 0].notna()].reset_index(drop=True)
    else:
        ventas_2024, devoluciones_2024 = None, None
    
    return ventas_2025, devoluciones_2025, ventas_2024, devoluciones_2024

def unificar_vendedor(nombre):
    """Unifica nombres de vendedores quitando apellidos y normalizando"""
    if pd.isna(nombre):
        return nombre
    
    nombre = str(nombre).strip().upper()
    
    # Diccionario de unificaciones específicas
    unificaciones = {
        '0004 KATERINE GARCES': '0004 KATERINE',
        '0004 KATERINE GARCÉS': '0004 KATERINE',
        # Puedes agregar más unificaciones aquí si encuentras otros casos
    }
    
    # Aplicar unificaciones específicas
    if nombre in unificaciones:
        return unificaciones[nombre]
    
    return nombre

def preparar_datos_analisis(ventas, devoluciones):
    """Prepara los datos para análisis con las columnas correctas"""
    
    # Convertir FECHA a datetime
    if 'FECHA' in ventas.columns:
        ventas['FECHA'] = pd.to_datetime(ventas['FECHA'], errors='coerce')
        ventas['MES_NUM'] = ventas['FECHA'].dt.month
        ventas['AÑO'] = ventas['FECHA'].dt.year
    
    # Limpiar y convertir VALOR NETO a numérico
    if 'VALOR NETO' in ventas.columns:
        # Eliminar espacios, puntos de miles y convertir comas decimales a puntos
        ventas['VALOR NETO'] = ventas['VALOR NETO'].astype(str).str.strip()
        ventas['VALOR NETO'] = ventas['VALOR NETO'].str.replace('.', '', regex=False)  # Quitar puntos de miles
        ventas['VALOR NETO'] = ventas['VALOR NETO'].str.replace(',', '.', regex=False)  # Cambiar comas por puntos
        ventas['VALOR NETO'] = ventas['VALOR NETO'].str.replace('$', '', regex=False)  # Quitar símbolo $
        ventas['VALOR NETO'] = ventas['VALOR NETO'].str.replace(' ', '', regex=False)  # Quitar espacios
        ventas['VALOR NETO'] = pd.to_numeric(ventas['VALOR NETO'], errors='coerce')
    
    # Limpiar y convertir CANT.PEDIDA a numérico
    if 'CANT.PEDIDA' in ventas.columns:
        ventas['CANT.PEDIDA'] = ventas['CANT.PEDIDA'].astype(str).str.strip()
        ventas['CANT.PEDIDA'] = ventas['CANT.PEDIDA'].str.replace('.', '', regex=False)
        ventas['CANT.PEDIDA'] = ventas['CANT.PEDIDA'].str.replace(',', '.', regex=False)
        ventas['CANT.PEDIDA'] = pd.to_numeric(ventas['CANT.PEDIDA'], errors='coerce')
    
    # Limpiar otras columnas numéricas
    columnas_numericas = ['VALOR VENTA', 'IVA', 'TOTAL']
    for col in columnas_numericas:
        if col in ventas.columns:
            ventas[col] = ventas[col].astype(str).str.strip()
            ventas[col] = ventas[col].str.replace('.', '', regex=False)
            ventas[col] = ventas[col].str.replace(',', '.', regex=False)
            ventas[col] = ventas[col].str.replace('$', '', regex=False)
            ventas[col] = ventas[col].str.replace(' ', '', regex=False)
            ventas[col] = pd.to_numeric(ventas[col], errors='coerce')
    
    # Clasificar tipo de cliente (Persona Natural vs Empresa)
    if 'CLIENTE' in ventas.columns:
        # Heurística: si el nombre tiene palabras como S.A.S, LTDA, S.A, etc., es empresa
        ventas['TIPO_CLIENTE'] = ventas['CLIENTE'].apply(
            lambda x: 'Empresa' if pd.notna(x) and any(term in str(x).upper() for term in 
            ['S.A.S', 'SAS', 'S.A', 'LTDA', 'S EN C', 'E.U', 'EU', 'SOCIEDAD', 'EMPRESA', 'CIA', 'CORP']) 
            else 'Persona Natural'
        )

    # Unificar vendedores (quitar apellidos y normalizar)
    if 'VENDEDOR' in ventas.columns:
        ventas['VENDEDOR'] = ventas['VENDEDOR'].apply(lambda x: unificar_vendedor(x) if pd.notna(x) else x)
    
    # Procesar devoluciones si existen
    if devoluciones is not None and len(devoluciones) > 0:
        if 'VALOR' in devoluciones.columns:
            devoluciones['VALOR'] = devoluciones['VALOR'].astype(str).str.strip()
            devoluciones['VALOR'] = devoluciones['VALOR'].str.replace('.', '', regex=False)
            devoluciones['VALOR'] = devoluciones['VALOR'].str.replace(',', '.', regex=False)
            devoluciones['VALOR'] = devoluciones['VALOR'].str.replace('$', '', regex=False)
            devoluciones['VALOR'] = devoluciones['VALOR'].str.replace(' ', '', regex=False)
            devoluciones['VALOR'] = pd.to_numeric(devoluciones['VALOR'], errors='coerce')
        
        if 'CANTIDAD' in devoluciones.columns:
            devoluciones['CANTIDAD'] = devoluciones['CANTIDAD'].astype(str).str.strip()
            devoluciones['CANTIDAD'] = devoluciones['CANTIDAD'].str.replace('.', '', regex=False)
            devoluciones['CANTIDAD'] = devoluciones['CANTIDAD'].str.replace(',', '.', regex=False)
            devoluciones['CANTIDAD'] = pd.to_numeric(devoluciones['CANTIDAD'], errors='coerce')
            
    # Procesar ciudad y departamento
    ventas = procesar_ciudad_departamento(ventas)
    
    return ventas, devoluciones
        
def calcular_ventas_netas(ventas, devoluciones):
    """Calcula ventas netas restando devoluciones"""
    ventas_totales = ventas['VALOR NETO'].sum() if 'VALOR NETO' in ventas.columns else 0
    devoluciones_totales = 0
    
    if devoluciones is not None and len(devoluciones) > 0 and 'VALOR' in devoluciones.columns:
        devoluciones_totales = abs(devoluciones['VALOR'].sum())  # Usar valor absoluto
    
    # Asegurar que las ventas netas no sean negativas (puede pasar si hay más devoluciones que ventas en el filtro)
    ventas_netas = ventas_totales - devoluciones_totales
    
    return ventas_totales, devoluciones_totales, ventas_netas

# Header principal
st.markdown('<div class="main-header">Análisis de Ventas Ekonomodo 2025</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align: left; margin-bottom: 2rem;">Reunión Comercial - 14 de Enero 2026</div>', unsafe_allow_html=True)

# Cargar datos
with st.spinner('Cargando datos desde Google Sheets...'):
    url = "https://docs.google.com/spreadsheets/d/1xh15BZGWNPvyoypQWtrUOgeKXY6Ihm8bNnq4JpmL0GI/edit?usp=sharing"
    ventas_2025, devoluciones_2025, ventas_2024, devoluciones_2024 = procesar_datos_ventas(url)

if ventas_2025 is not None:
    st.success('✅ Datos cargados exitosamente')
    
    # Preparar datos
    ventas_2025, devoluciones_2025 = preparar_datos_analisis(ventas_2025, devoluciones_2025)
    if ventas_2024 is not None:
        ventas_2024, devoluciones_2024 = preparar_datos_analisis(ventas_2024, devoluciones_2024)
    
    # Sidebar para filtros
    st.sidebar.header("🎛️ Filtros y Configuración")
    
    # Botón de actualización en sidebar
    if st.sidebar.button("🔄 Actualizar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Filtros de vista
    vista_analisis = st.sidebar.radio(
        "Vista de Análisis:",
        ["📊 General (Ekonomodo)", "🏢 Por Plataforma/Comercio", "👤 Por Vendedor/Comercial"]
    )
    
    # Filtro específico según la vista
    filtro_aplicado = None
    if vista_analisis == "🏢 Por Plataforma/Comercio" and 'PLATAFORMA' in ventas_2025.columns:
        plataformas = ['TODAS'] + sorted(ventas_2025['PLATAFORMA'].dropna().unique().tolist())
        filtro_aplicado = st.sidebar.selectbox("Seleccionar Plataforma:", plataformas)
    elif vista_analisis == "👤 Por Vendedor/Comercial" and 'VENDEDOR' in ventas_2025.columns:
        vendedores = ['TODOS'] + sorted(ventas_2025['VENDEDOR'].dropna().unique().tolist())
        filtro_aplicado = st.sidebar.selectbox("Seleccionar Vendedor:", vendedores)
    
    # Aplicar filtros
    ventas_filtradas = ventas_2025.copy()
    devoluciones_filtradas = devoluciones_2025.copy() if devoluciones_2025 is not None else None
    
    if vista_analisis == "🏢 Por Plataforma/Comercio" and filtro_aplicado and filtro_aplicado != 'TODAS':
        ventas_filtradas = ventas_2025[ventas_2025['PLATAFORMA'] == filtro_aplicado]
        if devoluciones_filtradas is not None and 'PLATAFORMA' in devoluciones_filtradas.columns:
            devoluciones_filtradas = devoluciones_2025[devoluciones_2025['PLATAFORMA'] == filtro_aplicado]
    elif vista_analisis == "👤 Por Vendedor/Comercial" and filtro_aplicado and filtro_aplicado != 'TODOS':
        ventas_filtradas = ventas_2025[ventas_2025['VENDEDOR'] == filtro_aplicado]
        if devoluciones_filtradas is not None and 'VENDEDOR' in devoluciones_filtradas.columns:
            devoluciones_filtradas = devoluciones_2025[devoluciones_2025['VENDEDOR'] == filtro_aplicado]
    
    # Tabs principales
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Resumen Ejecutivo", 
        "📊 Análisis Completo 2025",
        "🔄 Comparativa 2024 vs 2025",
        "🎯 Proyección 2026"
    ])
    
    with tab1:
        st.markdown('<div class="section-header">Resumen Ejecutivo 2025</div>', unsafe_allow_html=True)
        
        if filtro_aplicado and filtro_aplicado not in ['TODAS', 'TODOS']:
            st.info(f"📌 Vista filtrada: {filtro_aplicado}")
        
        # Calcular métricas
        ventas_brutas, total_devoluciones, ventas_netas = calcular_ventas_netas(ventas_filtradas, devoluciones_filtradas)
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            facturas_unicas = ventas_filtradas['NUMERO'].nunique() if 'NUMERO' in ventas_filtradas.columns else 0
            st.metric("🛒 Facturas Únicas", f"{facturas_unicas:,}")
        
        with col2:
            st.metric("💰 Ventas Netas", f"${ventas_netas:,.0f}")
        
        with col3:
            unidades_totales = ventas_filtradas['CANT.PEDIDA'].sum() if 'CANT.PEDIDA' in ventas_filtradas.columns else 0
            st.metric("📦 Unidades Vendidas", f"{unidades_totales:,.0f}")
        
        with col4:
            if facturas_unicas > 0:
                ticket_promedio = ventas_netas / facturas_unicas
                st.metric("💳 Ticket Promedio", f"${ticket_promedio:,.0f}")
        
        # Segunda fila de métricas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            clientes_unicos = ventas_filtradas['CLIENTE'].nunique() if 'CLIENTE' in ventas_filtradas.columns else 0
            st.metric("👥 Clientes Únicos", f"{clientes_unicos:,}")
        
        with col2:
            productos_unicos = ventas_filtradas['REFERENCIA'].nunique() if 'REFERENCIA' in ventas_filtradas.columns else 0
            st.metric("🏷️ Productos Diferentes", f"{productos_unicos:,}")
        
        with col3:
            ciudades_unicas = ventas_filtradas['CIUDAD'].nunique() if 'CIUDAD' in ventas_filtradas.columns else 0
            st.metric("🌎 Ciudades Atendidas", f"{ciudades_unicas:,}")
        
        with col4:
            if devoluciones_filtradas is not None and len(devoluciones_filtradas) > 0:
                tasa_devolucion = (total_devoluciones / ventas_brutas * 100) if ventas_brutas > 0 else 0
                st.metric("📉 Tasa Devolución", f"{tasa_devolucion:.2f}%")
        
        st.markdown("---")
        
        # Gráficos resumen
        col1, col2 = st.columns(2)
        
        with col1:
            if 'MES_NUM' in ventas_filtradas.columns:
                meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
                ventas_mes = ventas_filtradas.groupby('MES_NUM')['VALOR NETO'].sum().reset_index()
                ventas_mes['MES'] = ventas_mes['MES_NUM'].map(lambda x: meses_nombres[int(x)-1] if 1 <= x <= 12 else str(x))
                
                fig_mes = px.line(ventas_mes, x='MES', y='VALOR NETO', 
                                 title='Evolución Ventas Mensuales 2025',
                                 markers=True)
                fig_mes.update_traces(line_color='#1f77b4', line_width=3)
                st.plotly_chart(fig_mes, use_container_width=True)
        
        with col2:
            if 'TIPO_CLIENTE' in ventas_filtradas.columns:
                ventas_tipo = ventas_filtradas.groupby('TIPO_CLIENTE')['VALOR NETO'].sum().reset_index()
                fig_tipo = px.pie(ventas_tipo, values='VALOR NETO', names='TIPO_CLIENTE',
                                 title='Ventas: Personas vs Empresas',
                                 color_discrete_map={'Empresa': '#2ecc71', 'Persona Natural': '#3498db'})
                st.plotly_chart(fig_tipo, use_container_width=True)
    
    with tab2:
        st.markdown('<div class="section-header">Análisis Completo 2025</div>', unsafe_allow_html=True)
        
        if filtro_aplicado and filtro_aplicado not in ['TODAS', 'TODOS']:
            st.info(f"📌 Análisis para: {filtro_aplicado}")
        
        # 1. Ventas mes a mes
        st.markdown('<div class="subsection-header">1. 📅 Ventas Mes a Mes</div>', unsafe_allow_html=True)
        
        if 'MES_NUM' in ventas_filtradas.columns:
            meses_nombres = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                           'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            
            ventas_mensuales = ventas_filtradas.groupby('MES_NUM').agg({
                'NUMERO': 'nunique',
                'CANT.PEDIDA': 'sum',
                'VALOR NETO': 'sum',
                'CLIENTE': 'nunique'
            }).reset_index()
            ventas_mensuales.columns = ['MES_NUM', 'FACTURAS', 'UNIDADES', 'MONTO_BRUTO', 'CLIENTES']

            # Calcular devoluciones por mes si existen
            if devoluciones_filtradas is not None and len(devoluciones_filtradas) > 0:
                if 'MES' in devoluciones_filtradas.columns and 'VALOR' in devoluciones_filtradas.columns:
                    # Convertir MES a numérico si es necesario
                    devoluciones_filtradas['MES_NUM'] = pd.to_numeric(devoluciones_filtradas['MES'], errors='coerce')
                    
                    devol_mensuales = devoluciones_filtradas.groupby('MES_NUM').agg({
                        'VALOR': 'sum',
                        'CANTIDAD': 'sum'
                    }).reset_index()
                    devol_mensuales.columns = ['MES_NUM', 'DEVOL_MONTO', 'DEVOL_CANTIDAD']
                    
                    # Unir con ventas mensuales
                    ventas_mensuales = ventas_mensuales.merge(devol_mensuales, on='MES_NUM', how='left')
                    ventas_mensuales['DEVOL_MONTO'] = ventas_mensuales['DEVOL_MONTO'].fillna(0)
                    ventas_mensuales['DEVOL_CANTIDAD'] = ventas_mensuales['DEVOL_CANTIDAD'].fillna(0)
                else:
                    ventas_mensuales['DEVOL_MONTO'] = 0
                    ventas_mensuales['DEVOL_CANTIDAD'] = 0
            else:
                ventas_mensuales['DEVOL_MONTO'] = 0
                ventas_mensuales['DEVOL_CANTIDAD'] = 0

            # Calcular neto (ventas - devoluciones)
            ventas_mensuales['MONTO'] = ventas_mensuales['MONTO_BRUTO'] - ventas_mensuales['DEVOL_MONTO']
            ventas_mensuales['UNIDADES'] = ventas_mensuales['UNIDADES'] - ventas_mensuales['DEVOL_CANTIDAD']
            ventas_mensuales['MES'] = ventas_mensuales['MES_NUM'].map(
                lambda x: meses_nombres[int(x)-1] if 1 <= x <= 12 else str(x)
            )
            ventas_mensuales['TICKET_PROM'] = ventas_mensuales['MONTO'] / ventas_mensuales['FACTURAS']
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_monto = px.bar(ventas_mensuales, x='MES', y='MONTO',
                    title='Monto Total de Ventas por Mes',
                    color='MONTO', color_continuous_scale='Blues', text='MONTO')
                fig_monto.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
                st.plotly_chart(fig_monto, use_container_width=True)
            
            with col2:
                fig_unidades = px.bar(ventas_mensuales, x='MES', y='UNIDADES',
                    title='Cantidad de Unidades Vendidas por Mes',
                    color='UNIDADES', color_continuous_scale='Greens', text='UNIDADES')
                fig_unidades.update_traces(texttemplate='%{text:,}', textposition='outside')
                st.plotly_chart(fig_unidades, use_container_width=True)
            
            st.dataframe(
                ventas_mensuales[['MES', 'FACTURAS', 'UNIDADES', 'MONTO', 'TICKET_PROM', 'CLIENTES']].style.format({
                    'FACTURAS': '{:,.0f}',
                    'UNIDADES': '{:,.0f}',
                    'MONTO': '${:,.0f}',
                    'TICKET_PROM': '${:,.0f}',
                    'CLIENTES': '{:,.0f}'
                }),
                use_container_width=True
            )
        
        st.markdown("---")
        
        # 2. Pareto de productos
        st.markdown('<div class="subsection-header">2. 📊 Análisis Pareto de Productos</div>', unsafe_allow_html=True)
        
        if 'REFERENCIA' in ventas_filtradas.columns and 'DESCRIPCION' in ventas_filtradas.columns:
            # Filtrar solo productos con referencia y descripción válidas
            ventas_con_producto = ventas_filtradas[
                (ventas_filtradas['REFERENCIA'].notna()) & 
                (ventas_filtradas['DESCRIPCION'].notna())
            ].copy()
            
            productos_analisis = ventas_con_producto.groupby(['REFERENCIA', 'DESCRIPCION']).agg({
                'CANT.PEDIDA': 'sum',
                'VALOR NETO': 'sum',
                'NUMERO': 'nunique'
            }).reset_index()
            productos_analisis.columns = ['REFERENCIA', 'DESCRIPCION', 'UNIDADES', 'VALOR_TOTAL', 'VECES_VENDIDO']
            productos_analisis = productos_analisis.sort_values('VALOR_TOTAL', ascending=False)
            productos_analisis['PORCENTAJE'] = (productos_analisis['VALOR_TOTAL'] / productos_analisis['VALOR_TOTAL'].sum() * 100)
            productos_analisis['ACUMULADO'] = productos_analisis['PORCENTAJE'].cumsum()
            productos_analisis['PRODUCTO'] = productos_analisis['REFERENCIA'] + ' - ' + productos_analisis['DESCRIPCION'].str[:30]
            
            # Clasificación ABC
            productos_analisis['CLASIFICACION'] = 'C'
            productos_analisis.loc[productos_analisis['ACUMULADO'] <= 80, 'CLASIFICACION'] = 'A'
            productos_analisis.loc[(productos_analisis['ACUMULADO'] > 80) & (productos_analisis['ACUMULADO'] <= 95), 'CLASIFICACION'] = 'B'
            
            # Pareto Top 20
            top_20 = productos_analisis.head(20)
            
            fig_pareto = go.Figure()
            fig_pareto.add_trace(go.Bar(
                x=top_20['PRODUCTO'], y=top_20['VALOR_TOTAL'],
                name='Valor Ventas', yaxis='y', marker_color='steelblue'))
            fig_pareto.add_trace(go.Scatter(
                x=top_20['PRODUCTO'], y=top_20['ACUMULADO'],
                name='% Acumulado', yaxis='y2', marker_color='red', line=dict(width=3)))
            
            fig_pareto.update_layout(
                title='Análisis Pareto - Top 20 Productos por Valor',
                xaxis=dict(title='Producto', tickangle=-45),
                yaxis=dict(title='Valor Total', side='left'),
                yaxis2=dict(title='% Acumulado', side='right', overlaying='y', range=[0, 100]),
                height=500)
            
            st.plotly_chart(fig_pareto, use_container_width=True)
            
            # Clasificación ABC
            col1, col2, col3 = st.columns(3)
            clasificacion_count = productos_analisis['CLASIFICACION'].value_counts()
            
            with col1:
                st.metric("📈 Productos Clase A (80%)", clasificacion_count.get('A', 0))
            with col2:
                st.metric("📊 Productos Clase B (15%)", clasificacion_count.get('B', 0))
            with col3:
                st.metric("📉 Productos Clase C (5%)", clasificacion_count.get('C', 0))
            
            st.info("""
            **Clasificación ABC:**
            - **Clase A**: Productos que generan el 80% de las ventas (alta rotación - prioridad máxima)
            - **Clase B**: Productos que generan el 15% de las ventas (rotación media - mantener stock)
            - **Clase C**: Productos que generan el 5% de las ventas (baja rotación - evaluar descontinuar)
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**🏆 Top 10 Productos Más Vendidos (Mayor Rotación)**")
                st.dataframe(
                    productos_analisis.head(10)[['REFERENCIA', 'DESCRIPCION', 'UNIDADES', 'VALOR_TOTAL', 'CLASIFICACION']].style.format({
                        'UNIDADES': '{:,.0f}',
                        'VALOR_TOTAL': '${:,.0f}'
                    }),
                    use_container_width=True
                )
            
            with col2:
                st.write("**⚠️ Top 10 Productos Menos Vendidos (Menor Rotación)**")
                st.dataframe(
                    productos_analisis.tail(10)[['REFERENCIA', 'DESCRIPCION', 'UNIDADES', 'VALOR_TOTAL', 'CLASIFICACION']].style.format({
                        'UNIDADES': '{:,.0f}',
                        'VALOR_TOTAL': '${:,.0f}'
                    }),
                    use_container_width=True
                )
        
        st.markdown("---")
        
    # 3. Análisis de Portafolio
    st.markdown('<div class="subsection-header">3. 🎯 Análisis de Portafolio</div>', unsafe_allow_html=True)

    if 'REFERENCIA' in ventas_filtradas.columns and 'DESCRIPCION' in ventas_filtradas.columns:
        # Si productos_analisis no existe, crearlo aquí también
        if 'productos_analisis' not in locals():
            productos_analisis = ventas_filtradas.groupby(['REFERENCIA', 'DESCRIPCION']).agg({
                'CANT.PEDIDA': 'sum',
                'VALOR NETO': 'sum',
                'NUMERO': 'nunique'
            }).reset_index()
            productos_analisis.columns = ['REFERENCIA', 'DESCRIPCION', 'UNIDADES', 'VALOR_TOTAL', 'VECES_VENDIDO']
            productos_analisis = productos_analisis.sort_values('VALOR_TOTAL', ascending=False)
            productos_analisis['PORCENTAJE'] = (productos_analisis['VALOR_TOTAL'] / productos_analisis['VALOR_TOTAL'].sum() * 100)
            productos_analisis['ACUMULADO'] = productos_analisis['PORCENTAJE'].cumsum()
            productos_analisis['CLASIFICACION'] = 'C'
            productos_analisis.loc[productos_analisis['ACUMULADO'] <= 80, 'CLASIFICACION'] = 'A'
            productos_analisis.loc[(productos_analisis['ACUMULADO'] > 80) & (productos_analisis['ACUMULADO'] <= 95), 'CLASIFICACION'] = 'B'
        
        total_productos = productos_analisis['REFERENCIA'].nunique()
        productos_vendidos = len(productos_analisis[productos_analisis['VECES_VENDIDO'] > 0])
        productos_baja_rotacion = len(productos_analisis[productos_analisis['VECES_VENDIDO'] <= 2])
        productos_sin_venta = total_productos - productos_vendidos
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📦 Total Productos en Portafolio", f"{total_productos:,}")
        with col2:
            st.metric("✅ Productos que se Venden", f"{productos_vendidos:,}")
        with col3:
            st.metric("⚠️ Baja Rotación (≤2 ventas)", f"{productos_baja_rotacion:,}")
        with col4:
            st.metric("❌ Sin Ventas", f"{productos_sin_venta:,}")
        
        # Gráfico de clasificación ABC
        clasificacion_valores = productos_analisis.groupby('CLASIFICACION')['VALOR_TOTAL'].sum().reset_index()
        fig_abc = px.pie(clasificacion_valores, values='VALOR_TOTAL', names='CLASIFICACION',
                        title='Distribución de Valor por Clasificación ABC',
                        color='CLASIFICACION',
                        color_discrete_map={'A': '#2ecc71', 'B': '#f39c12', 'C': '#e74c3c'})
        st.plotly_chart(fig_abc, use_container_width=True)
        
        st.markdown("---")

        st.markdown("---")
        
        # 3.5 Tabla Completa de Productos
        st.markdown('<div class="subsection-header">📋 Tabla Completa de Productos (Referencia y Descripción)</div>', unsafe_allow_html=True)
        
        if 'REFERENCIA' in ventas_filtradas.columns and 'DESCRIPCION' in ventas_filtradas.columns:
            # Filtrar solo productos con referencia y descripción válidas
            ventas_con_producto = ventas_filtradas[
                (ventas_filtradas['REFERENCIA'].notna()) & 
                (ventas_filtradas['DESCRIPCION'].notna())
            ].copy()
            
            # Crear tabla completa
            tabla_productos = ventas_con_producto.groupby(['REFERENCIA', 'DESCRIPCION']).agg({
                'CANT.PEDIDA': 'sum',
                'VALOR NETO': 'sum',
                'NUMERO': 'nunique'
            }).reset_index()
            tabla_productos.columns = ['REFERENCIA', 'DESCRIPCION', 'CANTIDAD_TOTAL', 'MONTO_TOTAL', 'FACTURAS']
            tabla_productos = tabla_productos.sort_values('MONTO_TOTAL', ascending=False)
            
            # Agregar columnas calculadas
            tabla_productos['PRECIO_PROMEDIO'] = tabla_productos['MONTO_TOTAL'] / tabla_productos['CANTIDAD_TOTAL']
            tabla_productos['PARTICIPACION_%'] = (tabla_productos['MONTO_TOTAL'] / tabla_productos['MONTO_TOTAL'].sum() * 100)
            
            # Reordenar columnas
            tabla_productos = tabla_productos[['REFERENCIA', 'DESCRIPCION', 'CANTIDAD_TOTAL', 'MONTO_TOTAL', 'PRECIO_PROMEDIO', 'FACTURAS', 'PARTICIPACION_%']]
            
            # Mostrar resumen
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📦 Total Referencias", f"{len(tabla_productos):,}")
            with col2:
                st.metric("💰 Monto Total", f"${tabla_productos['MONTO_TOTAL'].sum():,.0f}")
            with col3:
                st.metric("📊 Cantidad Total", f"{tabla_productos['CANTIDAD_TOTAL'].sum():,.0f}")
            
            # Filtros para la tabla
            col1, col2 = st.columns(2)
            with col1:
                buscar_producto = st.text_input("🔍 Buscar por Referencia o Descripción:", "")
            with col2:
                ordenar_por = st.selectbox("Ordenar por:", 
                    ["Monto Total (Mayor a Menor)", "Monto Total (Menor a Mayor)", 
                     "Cantidad (Mayor a Menor)", "Cantidad (Menor a Mayor)",
                     "Referencia (A-Z)", "Referencia (Z-A)"])
            
            # Aplicar filtro de búsqueda
            if buscar_producto:
                tabla_filtrada = tabla_productos[
                    tabla_productos['REFERENCIA'].str.contains(buscar_producto, case=False, na=False) |
                    tabla_productos['DESCRIPCION'].str.contains(buscar_producto, case=False, na=False)
                ]
            else:
                tabla_filtrada = tabla_productos.copy()
            
            # Aplicar ordenamiento
            if ordenar_por == "Monto Total (Mayor a Menor)":
                tabla_filtrada = tabla_filtrada.sort_values('MONTO_TOTAL', ascending=False)
            elif ordenar_por == "Monto Total (Menor a Mayor)":
                tabla_filtrada = tabla_filtrada.sort_values('MONTO_TOTAL', ascending=True)
            elif ordenar_por == "Cantidad (Mayor a Menor)":
                tabla_filtrada = tabla_filtrada.sort_values('CANTIDAD_TOTAL', ascending=False)
            elif ordenar_por == "Cantidad (Menor a Mayor)":
                tabla_filtrada = tabla_filtrada.sort_values('CANTIDAD_TOTAL', ascending=True)
            elif ordenar_por == "Referencia (A-Z)":
                tabla_filtrada = tabla_filtrada.sort_values('REFERENCIA', ascending=True)
            elif ordenar_por == "Referencia (Z-A)":
                tabla_filtrada = tabla_filtrada.sort_values('REFERENCIA', ascending=False)
            
            # Mostrar tabla con formato
            st.dataframe(
                tabla_filtrada.style.format({
                    'CANTIDAD_TOTAL': '{:,.0f}',
                    'MONTO_TOTAL': '${:,.0f}',
                    'PRECIO_PROMEDIO': '${:,.0f}',
                    'FACTURAS': '{:,.0f}',
                    'PARTICIPACION_%': '{:.2f}%'
                }),
                use_container_width=True,
                height=600
            )
            
            # Botón de descarga
            csv = tabla_filtrada.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Descargar Tabla Completa en CSV",
                data=csv,
                file_name=f"productos_completo_{filtro_aplicado if filtro_aplicado else 'general'}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            st.info(f"📊 Mostrando {len(tabla_filtrada):,} de {len(tabla_productos):,} productos")
        
        # 4. Ticket Promedio
        st.markdown('<div class="subsection-header">4. 💳 Ticket Promedio</div>', unsafe_allow_html=True)
        
        if 'MES_NUM' in ventas_filtradas.columns:
            ticket_mensual = ventas_filtradas.groupby('MES_NUM').apply(
                lambda x: x['VALOR NETO'].sum() / x['NUMERO'].nunique() if x['NUMERO'].nunique() > 0 else 0
            ).reset_index()
            ticket_mensual.columns = ['MES_NUM', 'TICKET_PROMEDIO']
            ticket_mensual['MES'] = ticket_mensual['MES_NUM'].map(
                lambda x: meses_nombres[int(x)-1] if 1 <= x <= 12 else str(x)
            )
            
            fig_ticket = px.line(ticket_mensual, x='MES', y='TICKET_PROMEDIO',
                title='Evolución del Ticket Promedio Mensual', markers=True)
            fig_ticket.update_traces(line_color='#e74c3c', line_width=3)
            st.plotly_chart(fig_ticket, use_container_width=True)
            
            ticket_anual = ventas_filtradas['VALOR NETO'].sum() / facturas_unicas if facturas_unicas > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🎯 Ticket Promedio Anual", f"${ticket_anual:,.0f}")
            with col2:
                ticket_max = ticket_mensual['TICKET_PROMEDIO'].max()
                mes_max = ticket_mensual.loc[ticket_mensual['TICKET_PROMEDIO'].idxmax(), 'MES']
                st.metric(f"📈 Ticket Máximo ({mes_max})", f"${ticket_max:,.0f}")
            with col3:
                ticket_min = ticket_mensual['TICKET_PROMEDIO'].min()
                mes_min = ticket_mensual.loc[ticket_mensual['TICKET_PROMEDIO'].idxmin(), 'MES']
                st.metric(f"📉 Ticket Mínimo ({mes_min})", f"${ticket_min:,.0f}")
        
        st.markdown("---")
        
        # 6. Ventas por Ciudad
        st.markdown('<div class="subsection-header">6. 🌎 Segmentación: Ventas por Ciudad</div>', unsafe_allow_html=True)
        
        if 'CIUDAD_LIMPIA' in ventas_filtradas.columns:
            # Filtrar solo filas con ciudad válida
            ventas_con_ciudad = ventas_filtradas[ventas_filtradas['CIUDAD_LIMPIA'].notna()].copy()
            
            # Agrupar por ciudad limpia
            ventas_ciudad = ventas_con_ciudad.groupby('CIUDAD_LIMPIA').agg({
                'VALOR NETO': 'sum',
                'NUMERO': 'nunique',
                'CANT.PEDIDA': 'sum',
                'CLIENTE': 'nunique'
            }).reset_index()
            ventas_ciudad.columns = ['CIUDAD', 'VALOR_TOTAL', 'FACTURAS', 'UNIDADES', 'CLIENTES']
            ventas_ciudad = ventas_ciudad.sort_values('VALOR_TOTAL', ascending=False)
            ventas_ciudad['PARTICIPACION'] = (ventas_ciudad['VALOR_TOTAL'] / ventas_ciudad['VALOR_TOTAL'].sum() * 100)
            
            # Agregar coordenadas
            ventas_ciudad['LAT'] = ventas_ciudad['CIUDAD'].map(lambda x: COORDENADAS_CIUDADES.get(x, {}).get('lat', None))
            ventas_ciudad['LON'] = ventas_ciudad['CIUDAD'].map(lambda x: COORDENADAS_CIUDADES.get(x, {}).get('lon', None))
            
            # Filtrar solo ciudades con coordenadas
            ventas_ciudad_mapa = ventas_ciudad[ventas_ciudad['LAT'].notna()].copy()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📍 Mapa de Ventas por Ciudad en Colombia**")
                
                if len(ventas_ciudad_mapa) > 0:
                    # Crear mapa scatter con tamaño proporcional a ventas
                    fig_mapa = px.scatter_geo(
                        ventas_ciudad_mapa,
                        lat='LAT',
                        lon='LON',
                        size='VALOR_TOTAL',
                        hover_name='CIUDAD',
                        hover_data={
                            'VALOR_TOTAL': ':$,.0f',
                            'FACTURAS': ':,',
                            'UNIDADES': ':,',
                            'PARTICIPACION': ':.2f%',
                            'LAT': False,
                            'LON': False
                        },
                        color='VALOR_TOTAL',
                        color_continuous_scale='RdYlGn',
                        size_max=50,
                        title='Distribución Geográfica de Ventas en Colombia'
                    )
                    
                    # Configurar el mapa centrado en Colombia
                    fig_mapa.update_geos(
                        scope='south america',
                        center=dict(lat=4.5, lon=-74),
                        projection_scale=4.5,
                        showland=True,
                        landcolor='rgb(243, 243, 243)',
                        coastlinecolor='rgb(204, 204, 204)',
                        showlakes=True,
                        lakecolor='rgb(255, 255, 255)',
                        showcountries=True,
                        countrycolor='rgb(204, 204, 204)'
                    )
                    
                    fig_mapa.update_layout(height=600)
                    st.plotly_chart(fig_mapa, use_container_width=True)
                    
                    # Mostrar ciudades sin coordenadas si las hay
                    ciudades_sin_coords = ventas_ciudad[ventas_ciudad['LAT'].isna()]
                    if len(ciudades_sin_coords) > 0:
                        st.warning(f"⚠️ {len(ciudades_sin_coords)} ciudades no tienen coordenadas y no aparecen en el mapa: {', '.join(ciudades_sin_coords['CIUDAD'].head(5).tolist())}")
                else:
                    st.warning("No hay datos con coordenadas para mostrar en el mapa")
            
            with col2:
                # Top 10 ciudades por ventas
                fig_ciudad_bar = px.bar(
                    ventas_ciudad.head(10), 
                    x='CIUDAD', 
                    y='VALOR_TOTAL',
                    title='Top 10 Ciudades por Valor de Ventas',
                    color='VALOR_TOTAL', 
                    color_continuous_scale='Blues',
                    text='VALOR_TOTAL'
                )
                fig_ciudad_bar.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
                fig_ciudad_bar.update_xaxes(tickangle=-45)
                st.plotly_chart(fig_ciudad_bar, use_container_width=True)
            
            # Pie chart de participación
            st.write("**📊 Distribución Porcentual - Top 15 Ciudades**")
            fig_ciudad_pie = px.pie(
                ventas_ciudad.head(15), 
                values='VALOR_TOTAL', 
                names='CIUDAD',
                title='Participación de Ventas por Ciudad (Top 15)'
            )
            st.plotly_chart(fig_ciudad_pie, use_container_width=True)
            
            # Tabla detallada
            st.write("**📋 Detalle de Ventas por Ciudad**")
            st.dataframe(
                ventas_ciudad[['CIUDAD', 'VALOR_TOTAL', 'FACTURAS', 'UNIDADES', 'CLIENTES', 'PARTICIPACION']].style.format({
                    'VALOR_TOTAL': '${:,.0f}',
                    'FACTURAS': '{:,.0f}',
                    'UNIDADES': '{:,.0f}',
                    'CLIENTES': '{:,.0f}',
                    'PARTICIPACION': '{:.2f}%'
                }),
                use_container_width=True,
                height=400
            )
        else:
            st.warning("No se encontró información de ciudades en los datos")
        
        st.markdown("---")
        
        # 7. Análisis por Plataforma (vista general)
        if vista_analisis == "📊 General (Ekonomodo)" and 'PLATAFORMA' in ventas_filtradas.columns:
            st.markdown('<div class="subsection-header">7. 🏢 Segmentación: Análisis por Plataforma/Comercio</div>', unsafe_allow_html=True)
            
            ventas_con_plataforma = ventas_filtradas[ventas_filtradas['PLATAFORMA'].notna()].copy()
            
            ventas_plataforma = ventas_con_plataforma.groupby('PLATAFORMA').agg({
                'VALOR NETO': 'sum',
                'NUMERO': 'nunique',
                'CANT.PEDIDA': 'sum',
                'CLIENTE': 'nunique'
            }).reset_index()
            ventas_plataforma.columns = ['PLATAFORMA', 'VALOR_TOTAL', 'FACTURAS', 'UNIDADES', 'CLIENTES']
            ventas_plataforma = ventas_plataforma.sort_values('VALOR_TOTAL', ascending=False)
            ventas_plataforma['PARTICIPACION'] = (ventas_plataforma['VALOR_TOTAL'] / ventas_plataforma['VALOR_TOTAL'].sum() * 100)
            ventas_plataforma['TICKET_PROM'] = ventas_plataforma['VALOR_TOTAL'] / ventas_plataforma['FACTURAS']
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_plat_bar = px.bar(ventas_plataforma, x='PLATAFORMA', y='VALOR_TOTAL',
                    title='Ventas por Plataforma/Comercio',
                    color='VALOR_TOTAL', color_continuous_scale='Blues', text='VALOR_TOTAL')
                fig_plat_bar.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
                fig_plat_bar.update_xaxes(tickangle=-45)
                st.plotly_chart(fig_plat_bar, use_container_width=True)
            
            with col2:
                fig_plat_pie = px.pie(ventas_plataforma, values='PARTICIPACION', names='PLATAFORMA',
                    title='Participación por Plataforma (%)')
                st.plotly_chart(fig_plat_pie, use_container_width=True)
            
            st.dataframe(
                ventas_plataforma.style.format({
                    'VALOR_TOTAL': '${:,.0f}',
                    'FACTURAS': '{:,.0f}',
                    'UNIDADES': '{:,.0f}',
                    'CLIENTES': '{:,.0f}',
                    'PARTICIPACION': '{:.2f}%',
                    'TICKET_PROM': '${:,.0f}'
                }),
                use_container_width=True
            )
        
        st.markdown("---")
        
        # 8. Análisis por Vendedor/Comercial (vista general)
        if vista_analisis == "📊 General (Ekonomodo)" and 'VENDEDOR' in ventas_filtradas.columns:
            st.markdown('<div class="subsection-header">8. 👤 Segmentación: Análisis por Vendedor/Comercial</div>', unsafe_allow_html=True)
            
            ventas_con_vendedor = ventas_filtradas[ventas_filtradas['VENDEDOR'].notna()].copy()
            
            ventas_vendedor = ventas_con_vendedor.groupby('VENDEDOR').agg({
                'VALOR NETO': 'sum',
                'NUMERO': 'nunique',
                'CANT.PEDIDA': 'sum',
                'CLIENTE': 'nunique'
            }).reset_index()
            ventas_vendedor.columns = ['VENDEDOR', 'VALOR_TOTAL', 'FACTURAS', 'UNIDADES', 'CLIENTES']
            ventas_vendedor = ventas_vendedor.sort_values('VALOR_TOTAL', ascending=False)
            ventas_vendedor['PARTICIPACION'] = (ventas_vendedor['VALOR_TOTAL'] / ventas_vendedor['VALOR_TOTAL'].sum() * 100)
            ventas_vendedor['TICKET_PROM'] = ventas_vendedor['VALOR_TOTAL'] / ventas_vendedor['FACTURAS']
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_vend_bar = px.bar(ventas_vendedor, x='VENDEDOR', y='VALOR_TOTAL',
                    title='Ventas por Vendedor/Comercial',
                    color='VALOR_TOTAL', color_continuous_scale='Greens', text='VALOR_TOTAL')
                fig_vend_bar.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
                fig_vend_bar.update_xaxes(tickangle=-45)
                st.plotly_chart(fig_vend_bar, use_container_width=True)
            
            with col2:
                fig_ticket_vend = px.bar(ventas_vendedor, x='VENDEDOR', y='TICKET_PROM',
                    title='Ticket Promedio por Vendedor',
                    color='TICKET_PROM', color_continuous_scale='Oranges', text='TICKET_PROM')
                fig_ticket_vend.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
                fig_ticket_vend.update_xaxes(tickangle=-45)
                st.plotly_chart(fig_ticket_vend, use_container_width=True)
            
            st.dataframe(
                ventas_vendedor.style.format({
                    'VALOR_TOTAL': '${:,.0f}',
                    'FACTURAS': '{:,.0f}',
                    'UNIDADES': '{:,.0f}',
                    'CLIENTES': '{:,.0f}',
                    'PARTICIPACION': '{:.2f}%',
                    'TICKET_PROM': '${:,.0f}'
                }),
                use_container_width=True
            )
        
        st.markdown("---")
        
        # 9. Tipo de Cliente (Persona Natural vs Empresa)
        st.markdown('<div class="subsection-header">9. 👥 Análisis por Tipo de Cliente</div>', unsafe_allow_html=True)
        
        if 'TIPO_CLIENTE' in ventas_filtradas.columns:
            ventas_tipo_cliente = ventas_filtradas.groupby('TIPO_CLIENTE').agg({
                'VALOR NETO': 'sum',
                'NUMERO': 'nunique',
                'CANT.PEDIDA': 'sum',
                'CLIENTE': 'nunique'
            }).reset_index()
            ventas_tipo_cliente.columns = ['TIPO_CLIENTE', 'VALOR_TOTAL', 'FACTURAS', 'UNIDADES', 'CLIENTES']
            ventas_tipo_cliente['PARTICIPACION'] = (ventas_tipo_cliente['VALOR_TOTAL'] / ventas_tipo_cliente['VALOR_TOTAL'].sum() * 100)
            ventas_tipo_cliente['TICKET_PROM'] = ventas_tipo_cliente['VALOR_TOTAL'] / ventas_tipo_cliente['FACTURAS']
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_tipo_bar = px.bar(ventas_tipo_cliente, x='TIPO_CLIENTE', y='VALOR_TOTAL',
                    title='Ventas por Tipo de Cliente',
                    color='TIPO_CLIENTE',
                    color_discrete_map={'Empresa': '#2ecc71', 'Persona Natural': '#3498db'},
                    text='VALOR_TOTAL')
                fig_tipo_bar.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
                st.plotly_chart(fig_tipo_bar, use_container_width=True)
            
            with col2:
                fig_tipo_pie = px.pie(ventas_tipo_cliente, values='PARTICIPACION', names='TIPO_CLIENTE',
                    title='Distribución de Ventas por Tipo',
                    color='TIPO_CLIENTE',
                    color_discrete_map={'Empresa': '#2ecc71', 'Persona Natural': '#3498db'})
                st.plotly_chart(fig_tipo_pie, use_container_width=True)
            
            st.dataframe(
                ventas_tipo_cliente.style.format({
                    'VALOR_TOTAL': '${:,.0f}',
                    'FACTURAS': '{:,.0f}',
                    'UNIDADES': '{:,.0f}',
                    'CLIENTES': '{:,.0f}',
                    'PARTICIPACION': '{:.2f}%',
                    'TICKET_PROM': '${:,.0f}'
                }),
                use_container_width=True
            )
            
            # Análisis específico de empresas
            st.write("**🏢 Top 10 Empresas (Canal Empresarial)**")
            empresas = ventas_filtradas[
                (ventas_filtradas['TIPO_CLIENTE'] == 'Empresa') & 
                (ventas_filtradas['CLIENTE'].notna())
            ].copy()
            
            if len(empresas) > 0:
                top_empresas = empresas.groupby('CLIENTE').agg({
                    'VALOR NETO': 'sum',
                    'NUMERO': 'nunique',
                    'CANT.PEDIDA': 'sum'
                }).reset_index().sort_values('VALOR NETO', ascending=False).head(10)
                top_empresas.columns = ['EMPRESA', 'VALOR_TOTAL', 'FACTURAS', 'UNIDADES']
                
                st.dataframe(
                    top_empresas.style.format({
                        'VALOR_TOTAL': '${:,.0f}',
                        'FACTURAS': '{:,.0f}',
                        'UNIDADES': '{:,.0f}'
                    }),
                    use_container_width=True
                )
            else:
                st.info("No se encontraron ventas a empresas en este período")
        
        st.markdown("---")
        
        # 10. Análisis de Devoluciones
        if devoluciones_filtradas is not None and len(devoluciones_filtradas) > 0:
            st.markdown('<div class="subsection-header">10. ↩️ Gestión de Plataformas: Análisis de Devoluciones</div>', unsafe_allow_html=True)
            
            total_devol_valor = devoluciones_filtradas['VALOR'].sum() if 'VALOR' in devoluciones_filtradas.columns else 0
            total_devol_cant = devoluciones_filtradas['CANTIDAD'].sum() if 'CANTIDAD' in devoluciones_filtradas.columns else len(devoluciones_filtradas)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💸 Valor Total Devoluciones", f"${total_devol_valor:,.0f}")
            with col2:
                st.metric("📦 Cantidad Devoluciones", f"{total_devol_cant:,.0f}")
            with col3:
                tasa = (total_devol_valor / ventas_brutas * 100) if ventas_brutas > 0 else 0
                st.metric("📊 Tasa de Devolución", f"{tasa:.2f}%")
            with col4:
                num_devoluciones = len(devoluciones_filtradas)
                st.metric("📋 Casos de Devolución", f"{num_devoluciones:,}")
            
            # Devoluciones por producto
            if 'PRODUCTO' in devoluciones_filtradas.columns:
                devol_producto = devoluciones_filtradas.groupby('PRODUCTO').agg({
                    'VALOR': 'sum',
                    'CANTIDAD': 'sum'
                }).reset_index().sort_values('VALOR', ascending=False)
                
                fig_devol = px.bar(devol_producto.head(10), x='PRODUCTO', y='VALOR',
                    title='Top 10 Productos con Más Devoluciones',
                    color='VALOR', color_continuous_scale='Reds')
                fig_devol.update_xaxes(tickangle=-45)
                st.plotly_chart(fig_devol, use_container_width=True)
                
                st.dataframe(
                    devol_producto.head(15).style.format({
                        'VALOR': '${:,.0f}',
                        'CANTIDAD': '{:,.0f}'
                    }),
                    use_container_width=True
                )
            
            # Devoluciones por plataforma
            if 'PLATAFORMA' in devoluciones_filtradas.columns:
                st.write("**🏢 Devoluciones por Plataforma**")
                devol_plat = devoluciones_filtradas.groupby('PLATAFORMA')['VALOR'].sum().reset_index()
                devol_plat = devol_plat.sort_values('VALOR', ascending=False)
                
                fig_devol_plat = px.bar(devol_plat, x='PLATAFORMA', y='VALOR',
                    title='Valor de Devoluciones por Plataforma',
                    color='VALOR', color_continuous_scale='Reds')
                st.plotly_chart(fig_devol_plat, use_container_width=True)
    
    with tab3:
        st.markdown('<div class="section-header">Comparativa 2024 vs 2025</div>', unsafe_allow_html=True)
        
        if ventas_2024 is not None:
            # Calcular totales
            ventas_2024_total, devol_2024_total, netas_2024 = calcular_ventas_netas(ventas_2024, devoluciones_2024)
            ventas_2025_total, devol_2025_total, netas_2025 = calcular_ventas_netas(ventas_2025, devoluciones_2025)
            
            # Métricas comparativas principales
            st.subheader("📊 Indicadores Generales")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                facturas_2024 = ventas_2024['NUMERO'].nunique() if 'NUMERO' in ventas_2024.columns else 0
                facturas_2025 = ventas_2025['NUMERO'].nunique() if 'NUMERO' in ventas_2025.columns else 0
                crecimiento_fact = ((facturas_2025 - facturas_2024) / facturas_2024 * 100) if facturas_2024 > 0 else 0
                st.metric("🛒 Facturas 2024", f"{facturas_2024:,}")
                st.metric("🛒 Facturas 2025", f"{facturas_2025:,}", delta=f"{crecimiento_fact:.2f}%")
            
            with col2:
                crecimiento_ventas = ((netas_2025 - netas_2024) / netas_2024 * 100) if netas_2024 > 0 else 0
                st.metric("💰 Ventas 2024", f"${netas_2024:,.0f}")
                st.metric("💰 Ventas 2025", f"${netas_2025:,.0f}", delta=f"{crecimiento_ventas:.2f}%")
            
            with col3:
                unidades_2024 = ventas_2024['CANT.PEDIDA'].sum() if 'CANT.PEDIDA' in ventas_2024.columns else 0
                unidades_2025 = ventas_2025['CANT.PEDIDA'].sum() if 'CANT.PEDIDA' in ventas_2025.columns else 0
                crecimiento_unid = ((unidades_2025 - unidades_2024) / unidades_2024 * 100) if unidades_2024 > 0 else 0
                st.metric("📦 Unidades 2024", f"{unidades_2024:,.0f}")
                st.metric("📦 Unidades 2025", f"{unidades_2025:,.0f}", delta=f"{crecimiento_unid:.2f}%")
            
            with col4:
                ticket_2024 = netas_2024 / facturas_2024 if facturas_2024 > 0 else 0
                ticket_2025 = netas_2025 / facturas_2025 if facturas_2025 > 0 else 0
                crecimiento_ticket = ((ticket_2025 - ticket_2024) / ticket_2024 * 100) if ticket_2024 > 0 else 0
                st.metric("💳 Ticket 2024", f"${ticket_2024:,.0f}")
                st.metric("💳 Ticket 2025", f"${ticket_2025:,.0f}", delta=f"{crecimiento_ticket:.2f}%")
            
            st.markdown("---")
            
            # Comparación mensual
            st.subheader("📅 Comparación Mensual de Ventas")
            
            if 'MES_NUM' in ventas_2024.columns and 'MES_NUM' in ventas_2025.columns:
                meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
                
                # Por valor
                ventas_mes_2024 = ventas_2024.groupby('MES_NUM')['VALOR NETO'].sum().reset_index()
                ventas_mes_2024.columns = ['MES_NUM', 'VENTAS_2024']
                
                ventas_mes_2025 = ventas_2025.groupby('MES_NUM')['VALOR NETO'].sum().reset_index()
                ventas_mes_2025.columns = ['MES_NUM', 'VENTAS_2025']
                
                comparacion = pd.merge(ventas_mes_2024, ventas_mes_2025, on='MES_NUM', how='outer').fillna(0)
                comparacion['MES'] = comparacion['MES_NUM'].map(
                    lambda x: meses_nombres[int(x)-1] if 1 <= x <= 12 else str(x)
                )
                comparacion['CRECIMIENTO'] = ((comparacion['VENTAS_2025'] - comparacion['VENTAS_2024']) / comparacion['VENTAS_2024'] * 100).replace([np.inf, -np.inf], 0)
                comparacion['DIFERENCIA'] = comparacion['VENTAS_2025'] - comparacion['VENTAS_2024']
                
                fig_comp = go.Figure()
                fig_comp.add_trace(go.Bar(
                    name='2024', x=comparacion['MES'], y=comparacion['VENTAS_2024'],
                    marker_color='lightblue'))
                fig_comp.add_trace(go.Bar(
                    name='2025', x=comparacion['MES'], y=comparacion['VENTAS_2025'],
                    marker_color='darkblue'))
                fig_comp.update_layout(
                    title='Comparación Mensual de Ventas 2024 vs 2025',
                    barmode='group', xaxis_title='Mes', yaxis_title='Valor Ventas')
                st.plotly_chart(fig_comp, use_container_width=True)
                
                # Tabla de comparación
                st.dataframe(
                    comparacion[['MES', 'VENTAS_2024', 'VENTAS_2025', 'DIFERENCIA', 'CRECIMIENTO']].style.format({
                        'VENTAS_2024': '${:,.0f}',
                        'VENTAS_2025': '${:,.0f}',
                        'DIFERENCIA': '${:,.0f}',
                        'CRECIMIENTO': '{:.2f}%'
                    }),
                    use_container_width=True
                )
                
                # Por unidades
                st.write("**📦 Comparación de Unidades Vendidas**")
                unid_mes_2024 = ventas_2024.groupby('MES_NUM')['CANT.PEDIDA'].sum().reset_index()
                unid_mes_2024.columns = ['MES_NUM', 'UNIDADES_2024']
                
                unid_mes_2025 = ventas_2025.groupby('MES_NUM')['CANT.PEDIDA'].sum().reset_index()
                unid_mes_2025.columns = ['MES_NUM', 'UNIDADES_2025']
                
                comp_unid = pd.merge(unid_mes_2024, unid_mes_2025, on='MES_NUM', how='outer').fillna(0)
                comp_unid['MES'] = comp_unid['MES_NUM'].map(
                    lambda x: meses_nombres[int(x)-1] if 1 <= x <= 12 else str(x)
                )
                
                fig_unid = go.Figure()
                fig_unid.add_trace(go.Bar(
                    name='2024', x=comp_unid['MES'], y=comp_unid['UNIDADES_2024'],
                    marker_color='lightgreen'))
                fig_unid.add_trace(go.Bar(
                    name='2025', x=comp_unid['MES'], y=comp_unid['UNIDADES_2025'],
                    marker_color='darkgreen'))
                fig_unid.update_layout(
                    title='Comparación de Unidades Vendidas 2024 vs 2025',
                    barmode='group')
                st.plotly_chart(fig_unid, use_container_width=True)
            
            st.markdown("---")
            
            # Comparación por plataforma
            if 'PLATAFORMA' in ventas_2024.columns and 'PLATAFORMA' in ventas_2025.columns:
                st.subheader("🏢 Comparación por Plataforma")
                
                plat_2024 = ventas_2024.groupby('PLATAFORMA')['VALOR NETO'].sum().reset_index()
                plat_2024.columns = ['PLATAFORMA', 'VENTAS_2024']
                
                plat_2025 = ventas_2025.groupby('PLATAFORMA')['VALOR NETO'].sum().reset_index()
                plat_2025.columns = ['PLATAFORMA', 'VENTAS_2025']
                
                comp_plat = pd.merge(plat_2024, plat_2025, on='PLATAFORMA', how='outer').fillna(0)
                comp_plat['CRECIMIENTO'] = ((comp_plat['VENTAS_2025'] - comp_plat['VENTAS_2024']) / comp_plat['VENTAS_2024'] * 100).replace([np.inf, -np.inf], 0)
                comp_plat = comp_plat.sort_values('VENTAS_2025', ascending=False)
                
                fig_plat_comp = go.Figure()
                fig_plat_comp.add_trace(go.Bar(
                    name='2024', x=comp_plat['PLATAFORMA'], y=comp_plat['VENTAS_2024'],
                    marker_color='lightcoral'))
                fig_plat_comp.add_trace(go.Bar(
                    name='2025', x=comp_plat['PLATAFORMA'], y=comp_plat['VENTAS_2025'],
                    marker_color='darkgreen'))
                fig_plat_comp.update_layout(
                    title='Comparación por Plataforma 2024 vs 2025',
                    barmode='group', xaxis_title='Plataforma', yaxis_title='Valor Ventas')
                fig_plat_comp.update_xaxes(tickangle=-45)
                st.plotly_chart(fig_plat_comp, use_container_width=True)
                
                st.dataframe(
                    comp_plat.style.format({
                        'VENTAS_2024': '${:,.0f}',
                        'VENTAS_2025': '${:,.0f}',
                        'CRECIMIENTO': '{:.2f}%'
                    }),
                    use_container_width=True
                )
            
            st.markdown("---")
            
            # Comparación por vendedor
            if 'VENDEDOR' in ventas_2024.columns and 'VENDEDOR' in ventas_2025.columns:
                st.subheader("👤 Comparación por Vendedor/Comercial")
                
                vend_2024 = ventas_2024.groupby('VENDEDOR')['VALOR NETO'].sum().reset_index()
                vend_2024.columns = ['VENDEDOR', 'VENTAS_2024']
                
                vend_2025 = ventas_2025.groupby('VENDEDOR')['VALOR NETO'].sum().reset_index()
                vend_2025.columns = ['VENDEDOR', 'VENTAS_2025']
                
                comp_vend = pd.merge(vend_2024, vend_2025, on='VENDEDOR', how='outer').fillna(0)
                comp_vend['CRECIMIENTO'] = ((comp_vend['VENTAS_2025'] - comp_vend['VENTAS_2024']) / comp_vend['VENTAS_2024'] * 100).replace([np.inf, -np.inf], 0)
                comp_vend = comp_vend.sort_values('VENTAS_2025', ascending=False)
                
                fig_vend_comp = go.Figure()
                fig_vend_comp.add_trace(go.Bar(
                    name='2024', x=comp_vend['VENDEDOR'], y=comp_vend['VENTAS_2024'],
                    marker_color='lightsalmon'))
                fig_vend_comp.add_trace(go.Bar(
                    name='2025', x=comp_vend['VENDEDOR'], y=comp_vend['VENTAS_2025'],
                    marker_color='seagreen'))
                fig_vend_comp.update_layout(
                    title='Comparación por Vendedor 2024 vs 2025',
                    barmode='group')
                fig_vend_comp.update_xaxes(tickangle=-45)
                st.plotly_chart(fig_vend_comp, use_container_width=True)
                
                st.dataframe(
                    comp_vend.style.format({
                        'VENTAS_2024': '${:,.0f}',
                        'VENTAS_2025': '${:,.0f}',
                        'CRECIMIENTO': '{:.2f}%'
                    }),
                    use_container_width=True
                )
        else:
            st.warning("⚠️ No se encontraron datos de 2024 para comparación")
    
    with tab4:
        st.markdown('<div class="section-header">Proyección y Presupuesto 2026</div>', unsafe_allow_html=True)
        
        st.info("📋 **Guía para completar**: Esta sección debe ser desarrollada por cada comercial basándose en los análisis anteriores")
        
        # Calcular tendencia
        if ventas_2024 is not None:
            st.subheader("📈 Análisis de Tendencia Histórica")
            
            ventas_2024_total, _, netas_2024 = calcular_ventas_netas(ventas_2024, devoluciones_2024)
            ventas_2025_total, _, netas_2025 = calcular_ventas_netas(ventas_2025, devoluciones_2025)
            
            crecimiento_anual = ((netas_2025 - netas_2024) / netas_2024 * 100) if netas_2024 > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Ventas Netas 2024", f"${netas_2024:,.0f}")
            with col2:
                st.metric("💰 Ventas Netas 2025", f"${netas_2025:,.0f}")
            with col3:
                st.metric("📊 Crecimiento 2024→2025", f"{crecimiento_anual:.2f}%")