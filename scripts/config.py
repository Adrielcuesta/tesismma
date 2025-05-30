# scripts/config.py
import os
import shutil
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# Cargar variables de entorno desde .env que debe estar en la raíz del proyecto
dotenv_path = os.path.join(os.path.dirname(__file__), os.pardir, '.env')
load_dotenv(dotenv_path)

# --- API Key ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- Rutas Base ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_DIR = os.path.join(PROJECT_ROOT, "datos")

# --- Rutas Específicas de Datos ---
DOCS_BASE_CONOCIMIENTO_PATH = os.path.join(DATA_DIR, "BaseConocimiento")
PROYECTO_A_ANALIZAR_PATH = os.path.join(DATA_DIR, "ProyectoAnalizar") # Carpeta donde se buscará el PDF
CHROMA_DB_PATH = os.path.join(DATA_DIR, "ChromaDB_V1")
OUTPUT_PATH = os.path.join(DATA_DIR, "Resultados") # Carpeta base para todas las salidas

# --- Parámetros de Procesamiento ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
LLM_MODEL_NAME = 'gemini-1.5-flash-latest'
K_RETRIEVED_DOCS = 3
# NOMBRE_PDF_PROYECTO_ANALIZAR ya no es necesario aquí, se detectará automáticamente
MAX_CHARS_PROYECTO = 32000

# --- Nombres de Archivos de Salida ---
DASHBOARD_HTML_SUFFIX = "_dashboard.html" # Se añadirá al nombre base del PDF analizado

# --- Control de Base de Datos ---
RECREAR_DB = True

def configure_google_api():
    """Configura la API de Google Generative AI."""
    if not GEMINI_API_KEY:
        print("ADVERTENCIA: GEMINI_API_KEY no encontrada. El LLM no funcionará.")
        return False
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("--- API Key de Gemini configurada exitosamente ---")
        return True
    except Exception as e:
        print(f"Error al configurar la API Key de Gemini: {e}")
        return False

def inicializar_directorios_datos():
    """Crea los directorios de datos necesarios si no existen."""
    try:
        os.makedirs(DOCS_BASE_CONOCIMIENTO_PATH, exist_ok=True)
        os.makedirs(PROYECTO_A_ANALIZAR_PATH, exist_ok=True)
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        os.makedirs(OUTPUT_PATH, exist_ok=True)
        print("--- Directorios de datos inicializados/verificados ---")
        print(f"Directorio Raíz del Proyecto: {PROJECT_ROOT}")
        print(f"Directorio de Datos: {DATA_DIR}")
        print(f"  BaseConocimiento: {DOCS_BASE_CONOCIMIENTO_PATH}")
        print(f"  ProyectoAnalizar: {PROYECTO_A_ANALIZAR_PATH}")
        print(f"  ChromaDB: {CHROMA_DB_PATH}")
        print(f"  Resultados (base): {OUTPUT_PATH}")
        return True
    except OSError as e:
        print(f"Error al crear directorios: {e}")
        return False

if __name__ == '__main__':
    print("--- Verificando configuración ---")
    api_configured = configure_google_api()
    dirs_initialized = inicializar_directorios_datos()
    if api_configured and dirs_initialized:
        print("Configuración verificada. Rutas y API (si provista) parecen correctas.")
    else:
        print("Problemas en la verificación de la configuración.")
