import pandas as pd
from difflib import SequenceMatcher
import numpy as np
import re

def normalizar_texto(texto):
    """Normaliza texto para mejor comparación"""
    import re
    if pd.isna(texto):
        return ""
    
    texto = str(texto).lower()  # Todo a minúsculas
    
    # Remover acentos/tildes
    texto = texto.replace('á', 'a').replace('é', 'e').replace('í', 'i')
    texto = texto.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    
    # Remover símbolos y puntuación, dejando solo letras, números y espacios
    texto = re.sub(r'[^\w\s]', ' ', texto)
    
    # Remover espacios múltiples
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    return texto

def similitud_texto(a, b):
    """Calcula similitud entre dos textos normalizados"""
    a_norm = normalizar_texto(a)
    b_norm = normalizar_texto(b)
    return SequenceMatcher(None, a_norm, b_norm).ratio()

def obtener_mejor_similitud(titulo, df_referencia):
    """Obtiene la mejor similitud encontrada (para diagnóstico)"""
    if pd.isna(titulo) or titulo == '':
        return 0
    
    mejor_similitud = 0
    for idx, row in df_referencia.iterrows():
        descripcion = str(row['DESCRIPCION'])
        similitud = similitud_texto(titulo, descripcion)
        if similitud > mejor_similitud:
            mejor_similitud = similitud
    
    return mejor_similitud

def encontrar_mejor_sku(titulo, df_referencia, umbral=0.8):
    """
    Encuentra el SKU más similar basado en el título
    
    Args:
        titulo: Título a buscar
        df_referencia: DataFrame con columnas SKU y DESCRIPCION
        umbral: Similitud mínima requerida (0-1)
    
    Returns:
        SKU encontrado o None
    """
    if pd.isna(titulo) or titulo == '':
        return None
    
    mejor_similitud = 0
    mejor_sku = None
    
    for idx, row in df_referencia.iterrows():
        descripcion = str(row['DESCRIPCION'])
        similitud = similitud_texto(titulo, descripcion)
        
        if similitud > mejor_similitud:
            mejor_similitud = similitud
            mejor_sku = row['SKU']
    
    # Solo retornar si supera el umbral de similitud
    if mejor_similitud >= umbral:
        return mejor_sku
    return None

# Leer el archivo Excel
archivo = r'C:\Users\SARA\Desktop\JUAN DAVID\Ekmd_proyectos\Proyecto8_dashboard_ventas_mensual\PLANTILLA MELI (2).xlsm'  # Cambia esto por tu nombre de archivo
df_principal = pd.read_excel(archivo, sheet_name='ALL PRODUCTS')
df_referencia = pd.read_excel(archivo, sheet_name='SODIMAC')

# Asegurarse de que las columnas existen
# Ajusta los nombres según tu archivo
#df_referencia.columns = ['SKU', 'Título']  # Ajusta según tu estructura

# Renombrar las columnas de referencia para que el script funcione
df_referencia = df_referencia.rename(columns={
    'REFERENCIA': 'SKU',
    'DESCRIPCION': 'DESCRIPCION'
})

# Crear una copia de respaldo
df_principal['SKU_ORIGINAL'] = df_principal['SKU']

# Procesar cada fila donde el SKU está vacío
print("Procesando SKUs faltantes...")
skus_asignados = 0
no_asignados = []

# ETAPA 1: Asignación con umbral alto (0.6) - Mayor confianza
print("\n=== ETAPA 1: Asignación con umbral alto (80%) ===")
for idx, row in df_principal.iterrows():
    if pd.isna(row['SKU']) or row['SKU'] == '':
        titulo = row['Título']
        sku_encontrado = encontrar_mejor_sku(titulo, df_referencia, umbral=0.8)
        
        if sku_encontrado:
            df_principal.at[idx, 'SKU'] = sku_encontrado
            skus_asignados += 1
            print(f"✓ Fila {idx+2}: '{titulo[:50]}...' -> SKU: {sku_encontrado}")

print(f"\n✓ SKUs asignados en Etapa 1: {skus_asignados}")

# ETAPA 2: Asignación con umbral bajo (0.4) - Para los restantes
print("\n=== ETAPA 2: Asignación con umbral bajo (40%) para restantes ===")
skus_asignados_etapa2 = 0

for idx, row in df_principal.iterrows():
    if pd.isna(row['SKU']) or row['SKU'] == '':  # Solo los que siguen vacíos
        titulo = row['Título']
        sku_encontrado = encontrar_mejor_sku(titulo, df_referencia, umbral=0.4)
        
        if sku_encontrado:
            df_principal.at[idx, 'SKU'] = sku_encontrado
            skus_asignados_etapa2 += 1
            similitud = obtener_mejor_similitud(titulo, df_referencia)
            print(f"⚠ Fila {idx+2}: Similitud {similitud:.1%} -> SKU: {sku_encontrado}")
            print(f"   Título: {titulo[:70]}")
        else:
            no_asignados.append({
                'fila': idx+2,
                'titulo': titulo,
                'mejor_similitud': obtener_mejor_similitud(titulo, df_referencia)
            })

print(f"\n✓ SKUs asignados en Etapa 2: {skus_asignados_etapa2}")
print(f"✓ Total de SKUs asignados: {skus_asignados + skus_asignados_etapa2}")
print(f"✓ SKUs que quedaron vacíos: {len(no_asignados)}")

# Guardar el resultado
archivo_salida = 'archivo_con_skus_completos.xlsx'
df_principal.to_excel(archivo_salida, index=False)
print(f"\n✓ Archivo guardado como: {archivo_salida}")

# Mostrar muestra de cambios
print("\n--- Muestra de cambios realizados ---")
cambios = df_principal[df_principal['SKU_ORIGINAL'].isna() & df_principal['SKU'].notna()][['SKU', 'Título']].head(10)
print(cambios.to_string())