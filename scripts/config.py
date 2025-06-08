# scripts/config.py
import os
import certifi
import logging

logger = logging.getLogger(__name__)

# --- Configuración de Certificados SSL ---
try:
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
except Exception as e_certifi:
    logger.warning(f"No se pudo establecer SSL_CERT_FILE/REQUESTS_CA_BUNDLE usando certifi: {e_certifi}")

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), os.pardir, '.env')
load_dotenv(dotenv_path)

if 'SSL_CERT_FILE' in os.environ:
    logger.info(f"Usando bundle de certificados de certifi en: {os.environ['SSL_CERT_FILE']}")

# --- Rutas del Proyecto ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_DIR = os.path.join(PROJECT_ROOT, "datos")
DIRECTORIO_BASE_CONOCIMIENTO = os.path.join(DATA_DIR, "BaseConocimiento")
DIRECTORIO_PROYECTO_ANALIZAR = os.path.join(DATA_DIR, "ProyectoAnalizar")
CHROMA_DB_PATH = os.path.join(DATA_DIR, "ChromaDB_V1")
DIRECTORIO_RESULTADOS = os.path.join(DATA_DIR, "Resultados")
MODELOS_LOCALES_PATH = os.path.join(PROJECT_ROOT, "modelos_locales")
CACHE_DIR_HF = os.path.join(PROJECT_ROOT, ".cache", "huggingface_cache")

# --- Lógica de selección del modelo de Embeddings ---
DEFAULT_EMBEDDING_MODEL_HF_REPO_ID = 'sentence-transformers/all-MiniLM-L6-v2'
MODEL_SAVE_SUBFOLDER = DEFAULT_EMBEDDING_MODEL_HF_REPO_ID.split('/')[-1]
LOCAL_EMBEDDING_MODEL_PATH = os.path.join(MODELOS_LOCALES_PATH, MODEL_SAVE_SUBFOLDER)

if os.path.exists(LOCAL_EMBEDDING_MODEL_PATH):
    EMBEDDING_MODEL_NAME_OR_PATH = LOCAL_EMBEDDING_MODEL_PATH
else:
    EMBEDDING_MODEL_NAME_OR_PATH = os.environ.get('EMBEDDING_MODEL_PATH', DEFAULT_EMBEDDING_MODEL_HF_REPO_ID).strip()

# --- Configuración de RAG y Embeddings ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
MAX_CHARS_PROYECTO = 12000
# --- ¡IMPORTANTE! Forzamos la recreación para que se aplique el filtro de páginas ---
RECREAR_DB = True 
MAX_PAGES_TO_CHECK_FOR_INDEX = 5

# --- Configuración para el Re-ranker ---
USE_RERANKER = True
K_RETRIEVED_DOCS_BEFORE_RERANK = 50
RERANKER_TOP_N = 4

# --- Configuración de LLMs ---
LLM_MODELS = {
    "gemini-1.5-flash": {
        "provider": "google",
        "display_name": "Google Gemini 1.5 Flash (Recomendado)",
        "api_key_env": "GEMINI_API_KEY"
    },
    "gemini-1.5-pro": {
        "provider": "google",
        "display_name": "Google Gemini 1.5 Pro",
        "api_key_env": "GEMINI_API_KEY"
    },
    "gpt-4o": {
        "provider": "openai",
        "display_name": "OpenAI GPT-4o",
        "api_key_env": "OPENAI_API_KEY"
    },
    "deepseek-chat": {
        "provider": "openai_compatible",
        "display_name": "DeepSeek Chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1"
    },
    "qwen-plus": {
        "provider": "openai_compatible",
        "display_name": "Qwen Plus (Alibaba)",
        "api_key_env": "QWEN_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
    }
}

# --- Información de la Tesis ---
INFO_TESIS = {
    "titulo_tesis_h1": "TESIS FIN DE MAESTRÍA",
    "titulo_tesis_h2": "Innovación en entornos empresariales",
    "titulo_tesis_h3": "Sistemas RAG para la Optimización de la Gestión de Proyectos y Análisis Estratégico.",
    "app_subtitle_h4": "ANALIZADOR DE RIESGOS CON IA.",
    "alumno": "Adriel J. Cuesta",
    "institucion_line1": "ITBA - Instituto Tecnológico Buenos Aires",
    "institucion_line2": "Maestría en Management & Analytics",
    "github_repo_url": "https://github.com/Adrielcuesta/tesismma"
}

# --- Funciones de Inicialización ---
_api_configured_flag_google = False

def configure_google_api():
    global _api_configured_flag_google
    if _api_configured_flag_google: return True
    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    if not gemini_api_key:
        logger.warning("GEMINI_API_KEY no encontrada en .env. El modelo de Gemini no funcionará.")
        return False
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_api_key)
        logger.info("API Key de Gemini configurada exitosamente.")
        _api_configured_flag_google = True
        return True
    except Exception as e:
        logger.error(f"Error al configurar la API Key de Gemini: {e}")
        return False

def inicializar_directorios_datos():
    directorios_a_crear = [
        DIRECTORIO_BASE_CONOCIMIENTO, DIRECTORIO_PROYECTO_ANALIZAR,
        CHROMA_DB_PATH, DIRECTORIO_RESULTADOS, MODELOS_LOCALES_PATH, CACHE_DIR_HF
    ]
    try:
        for dir_path in directorios_a_crear:
            os.makedirs(dir_path, exist_ok=True)
        return True
    except OSError as e:
        logger.error(f"Error al crear directorios: {e}")
        return False
