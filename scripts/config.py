# scripts/config.py
import os
import certifi
import logging 

logger = logging.getLogger(__name__)

try:
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
except Exception as e_certifi:
    logger.warning(f"No se pudo establecer SSL_CERT_FILE/REQUESTS_CA_BUNDLE usando certifi: {e_certifi}")

import google.generativeai as genai
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), os.pardir, '.env')
load_dotenv(dotenv_path)

if 'SSL_CERT_FILE' in os.environ:
    logger.info(f"Usando bundle de certificados de certifi en: {os.environ['SSL_CERT_FILE']}")

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_DIR = os.path.join(PROJECT_ROOT, "datos")

# Nombres de variables consistentes con el main.py que usaremos
DIRECTORIO_BASE_CONOCIMIENTO = os.path.join(DATA_DIR, "BaseConocimiento")
DIRECTORIO_PROYECTO_ANALIZAR = os.path.join(DATA_DIR, "ProyectoAnalizar")
CHROMA_DB_PATH = os.path.join(DATA_DIR, "ChromaDB_V1")
DIRECTORIO_RESULTADOS = os.path.join(DATA_DIR, "Resultados")
MODELOS_LOCALES_PATH = os.path.join(PROJECT_ROOT, "modelos_locales")
CACHE_DIR_HF = os.path.join(PROJECT_ROOT, ".cache", "huggingface_cache")

DEFAULT_EMBEDDING_MODEL_HF_REPO_ID = 'sentence-transformers/all-MiniLM-L6-v2'
EMBEDDING_MODEL_NAME_OR_PATH = DEFAULT_EMBEDDING_MODEL_HF_REPO_ID

env_model_path_str = os.environ.get('EMBEDDING_MODEL_PATH', '').strip()
if env_model_path_str:
    if not os.path.isabs(env_model_path_str):
        candidate_path_abs = os.path.join(PROJECT_ROOT, env_model_path_str)
    else:
        candidate_path_abs = env_model_path_str
    normalized_local_path = os.path.normpath(candidate_path_abs).replace("\\", "/")
    if os.path.isdir(normalized_local_path):
        EMBEDDING_MODEL_NAME_OR_PATH = normalized_local_path
        logger.info(f"Usando modelo de embeddings local (desde .env): {EMBEDDING_MODEL_NAME_OR_PATH}")
    else:
        logger.warning(f"Ruta local EMBEDDING_MODEL_PATH='{env_model_path_str}' (resuelta a '{normalized_local_path}') no es un directorio válido.")
        logger.warning(f"Revirtiendo al modelo por defecto de Hugging Face: '{DEFAULT_EMBEDDING_MODEL_HF_REPO_ID}'")
        EMBEDDING_MODEL_NAME_OR_PATH = DEFAULT_EMBEDDING_MODEL_HF_REPO_ID
else:
    logger.info(f"EMBEDDING_MODEL_PATH no definido en .env o vacío. Usando por defecto: {EMBEDDING_MODEL_NAME_OR_PATH}")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
GEMINI_MODEL_NAME = 'gemini-1.5-flash-latest' # Usado por main.py
K_RETRIEVED_DOCS = 3
MAX_CHARS_PROYECTO = 32000
RECREAR_DB = True
DASHBOARD_HTML_SUFFIX = "_dashboard.html"

# En scripts/config.py
INFO_TESIS = {
    "titulo_tesis_h1": "TESIS FIN DE MAESTRÍA",
    "titulo_tesis_h2": "Innovación en entornos empresariales",
    "titulo_tesis_h3": "Sistemas RAG para la Optimización de la Gestión de Proyectos y Análisis Estratégico.",
    "app_subtitle": "ANALIZADOR DE RIESGOS CON IA.", # Este es el que pusiste en app.py
    "alumno": "Adriel J. Cuesta",
    "institucion_line1": "ITBA - Instituto Tecnológico Buenos Aires",
    "institucion_line2": "Maestría en Management & Analytics",
    "github_repo_url": "https://github.com/Adrielcuesta/tesismma"
    # Añade cualquier otra clave que eventualmente quieras usar de forma centralizada.
}

_api_configured_flag = False
_dirs_initialized_flag = False

def configure_google_api():
    global _api_configured_flag
    if _api_configured_flag: return True
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY no encontrada en .env. El LLM no funcionará.")
        return False
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("API Key de Gemini configurada exitosamente (desde config.py).")
        _api_configured_flag = True
        return True
    except Exception as e:
        logger.error(f"Error al configurar la API Key de Gemini (desde config.py): {e}")
        return False

def inicializar_directorios_datos():
    global _dirs_initialized_flag
    if _dirs_initialized_flag: return True
    directorios_a_crear = [
        DIRECTORIO_BASE_CONOCIMIENTO, DIRECTORIO_PROYECTO_ANALIZAR,
        CHROMA_DB_PATH, DIRECTORIO_RESULTADOS, MODELOS_LOCALES_PATH, CACHE_DIR_HF
    ]
    try:
        for dir_path in directorios_a_crear:
            os.makedirs(dir_path, exist_ok=True)
        logger.info("Directorios de datos inicializados/verificados (desde config.py).")
        _dirs_initialized_flag = True
        return True
    except OSError as e:
        logger.error(f"Error al crear directorios (desde config.py): {e}")
        return False

if __name__ == '__main__':
    # Configurar un logger básico si se ejecuta config.py directamente para pruebas
    if not logging.getLogger().handlers: # Chequea el root logger
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', datefmt='%H:%M:%S')

    logger.info("--- [INICIO] Ejecutando config.py directamente para verificación ---")
    inicializar_directorios_datos()
    configure_google_api()
    logger.info(f"GEMINI_API_KEY disponible: {'Sí' if GEMINI_API_KEY else 'No'}")
    logger.info(f"PROJECT_ROOT: {PROJECT_ROOT}")
    logger.info(f"EMBEDDING_MODEL_NAME_OR_PATH: '{EMBEDDING_MODEL_NAME_OR_PATH}'")
    logger.info(f"DIRECTORIO_PROYECTO_ANALIZAR: {DIRECTORIO_PROYECTO_ANALIZAR}") # Nombre corregido
    logger.info(f"DIRECTORIO_BASE_CONOCIMIENTO: {DIRECTORIO_BASE_CONOCIMIENTO}") # Nombre corregido
    logger.info(f"DIRECTORIO_RESULTADOS: {DIRECTORIO_RESULTADOS}") # Nombre corregido
    logger.info(f"RECREAR_DB: {RECREAR_DB}")
    logger.info(f"INFO_TESIS: {INFO_TESIS}")
    logger.info("--- [FIN] Verificación de config.py ---")