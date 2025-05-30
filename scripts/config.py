# scripts/config.py
import os
import certifi 

# --- INICIO DE LA MODIFICACIÓN PARA SSL/CERTIFI ---
try:
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where() 
    # El print se movió más abajo para que aparezca después de la carga de .env
except Exception as e_certifi:
    print(f"ADVERTENCIA (config.py): No se pudo establecer SSL_CERT_FILE usando certifi: {e_certifi}")
# --- FIN DE LA MODIFICACIÓN PARA SSL/CERTIFI ----

import google.generativeai as genai
from dotenv import load_dotenv
import shutil 
from datetime import datetime 

dotenv_path = os.path.join(os.path.dirname(__file__), os.pardir, '.env')
load_dotenv(dotenv_path)

# Ahora que .env está cargado, podemos imprimir la info de certifi
if 'SSL_CERT_FILE' in os.environ:
    print(f"INFO (config.py): Usando bundle de certificados de certifi en: {os.environ['SSL_CERT_FILE']}")

# --- API Key ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- Rutas Base ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_DIR = os.path.join(PROJECT_ROOT, "datos")

# --- Rutas Específicas de Datos ---
DOCS_BASE_CONOCIMIENTO_PATH = os.path.join(DATA_DIR, "BaseConocimiento")
PROYECTO_A_ANALIZAR_PATH = os.path.join(DATA_DIR, "ProyectoAnalizar")
CHROMA_DB_PATH = os.path.join(DATA_DIR, "ChromaDB_V1")
OUTPUT_PATH = os.path.join(DATA_DIR, "Resultados")
MODELOS_LOCALES_PATH = os.path.join(PROJECT_ROOT, "modelos_locales")

# --- Modelo de Embeddings ---
DEFAULT_EMBEDDING_MODEL_HF_REPO_ID = 'sentence-transformers/all-MiniLM-L6-v2'
EMBEDDING_MODEL_NAME_OR_PATH = DEFAULT_EMBEDDING_MODEL_HF_REPO_ID # Default

env_model_path_str = os.environ.get('EMBEDDING_MODEL_PATH', '').strip()

if env_model_path_str:
    # Comprobar si es una ruta absoluta o relativa que existe
    # Si es relativa, asumimos que es relativa a PROJECT_ROOT
    if not os.path.isabs(env_model_path_str):
        candidate_path_abs = os.path.join(PROJECT_ROOT, env_model_path_str)
    else:
        candidate_path_abs = env_model_path_str
    
    normalized_local_path = os.path.normpath(candidate_path_abs).replace("\\", "/")
    
    if os.path.isdir(normalized_local_path):
        EMBEDDING_MODEL_NAME_OR_PATH = normalized_local_path
        print(f"INFO (config.py): Usando modelo de embeddings local (desde .env): {EMBEDDING_MODEL_NAME_OR_PATH}")
    else:
        print(f"ADVERTENCIA (config.py): Ruta local EMBEDDING_MODEL_PATH='{env_model_path_str}' (resuelta a '{normalized_local_path}') no es un directorio válido.")
        print(f"Revirtiendo al modelo por defecto de Hugging Face: '{DEFAULT_EMBEDDING_MODEL_HF_REPO_ID}'")
        EMBEDDING_MODEL_NAME_OR_PATH = DEFAULT_EMBEDDING_MODEL_HF_REPO_ID
else:
    print(f"INFO (config.py): EMBEDDING_MODEL_PATH no definido en .env o vacío. Usando por defecto: {EMBEDDING_MODEL_NAME_OR_PATH}")

# --- Parámetros de Procesamiento ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
LLM_MODEL_NAME = 'gemini-1.5-flash-latest'
K_RETRIEVED_DOCS = 3
MAX_CHARS_PROYECTO = 32000

#----- CREACION DE VECTOR DE BASE DE DATOS----
DASHBOARD_HTML_SUFFIX = "_dashboard.html"
# En caso de iniciar por primera vez o volver a cargar la base de conocimiento
# RECREAR_DB = True  
RECREAR_DB = False # Default para el repositorio. 

#----------------------------------------------

_api_configured_flag = False
_dirs_initialized_flag = False

def configure_google_api():
    global _api_configured_flag
    if _api_configured_flag: return True
    if not GEMINI_API_KEY:
        print("ADVERTENCIA (config.py): GEMINI_API_KEY no encontrada en .env. El LLM no funcionará.")
        return False
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("--- API Key de Gemini configurada exitosamente (desde config.py) ---")
        _api_configured_flag = True
        return True
    except Exception as e:
        print(f"Error al configurar la API Key de Gemini (desde config.py): {e}")
        return False

def inicializar_directorios_datos():
    global _dirs_initialized_flag
    if _dirs_initialized_flag: return True
    try:
        os.makedirs(DOCS_BASE_CONOCIMIENTO_PATH, exist_ok=True)
        os.makedirs(PROYECTO_A_ANALIZAR_PATH, exist_ok=True)
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        os.makedirs(OUTPUT_PATH, exist_ok=True)
        os.makedirs(MODELOS_LOCALES_PATH, exist_ok=True) 
        print("--- Directorios de datos inicializados/verificados (desde config.py) ---")
        _dirs_initialized_flag = True
        return True
    except OSError as e:
        print(f"Error al crear directorios (desde config.py): {e}")
        return False

if __name__ == '__main__':
    print("--- [INICIO] Ejecutando config.py directamente para verificación ---")
    inicializar_directorios_datos() # Llamar primero para que PROJECT_ROOT, etc., estén disponibles para los prints
    configure_google_api()
    print(f"\nValor final de EMBEDDING_MODEL_NAME_OR_PATH que se usará: '{EMBEDDING_MODEL_NAME_OR_PATH}'")
    if os.path.isdir(EMBEDDING_MODEL_NAME_OR_PATH):
         print(f"  -> La ruta del modelo local es un directorio válido.")
    elif EMBEDDING_MODEL_NAME_OR_PATH == DEFAULT_EMBEDDING_MODEL_HF_REPO_ID:
         print(f"  -> Se usará el modelo de Hugging Face Hub.")
    else:
         print(f"  -> ADVERTENCIA: La ruta/nombre del modelo '{EMBEDDING_MODEL_NAME_OR_PATH}' podría no ser válida.")
    print("--- [FIN] Verificación de config.py ---")
