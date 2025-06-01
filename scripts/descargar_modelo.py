# scripts/descargar_modelo.py
import os
import certifi
from sentence_transformers import SentenceTransformer
import logging
import traceback

logger = logging.getLogger(__name__)

try:
    original_ssl_cert_file = os.environ.get('SSL_CERT_FILE')
    original_requests_ca_bundle = os.environ.get('REQUESTS_CA_BUNDLE')
    certifi_path = certifi.where()
    os.environ['SSL_CERT_FILE'] = certifi_path
    os.environ['REQUESTS_CA_BUNDLE'] = certifi_path
    logger.info(f"Intentando usar bundle de certifi en: {certifi_path}")
except Exception as e_certifi_setup:
    logger.warning(f"No se pudo establecer SSL con certifi: {e_certifi_setup}")

try:
    from .config import PROJECT_ROOT, MODELOS_LOCALES_PATH, CACHE_DIR_HF, DEFAULT_EMBEDDING_MODEL_HF_REPO_ID # Añadido DEFAULT_EMBEDDING_MODEL_HF_REPO_ID
except ImportError:
    logger.error("No se pudo importar 'config' usando import relativo. Definiendo rutas fallback.")
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    MODELOS_LOCALES_PATH = os.path.join(PROJECT_ROOT, "modelos_locales")
    CACHE_DIR_HF = os.path.join(PROJECT_ROOT, ".cache", "huggingface_cache")
    DEFAULT_EMBEDDING_MODEL_HF_REPO_ID = "sentence-transformers/all-MiniLM-L6-v2" # Fallback


MODEL_ID_TO_DOWNLOAD = DEFAULT_EMBEDDING_MODEL_HF_REPO_ID # Usar la variable de config
MODEL_SAVE_SUBFOLDER = MODEL_ID_TO_DOWNLOAD.split('/')[-1] # Derivar subfolder del ID
FULL_SAVE_PATH = os.path.join(MODELOS_LOCALES_PATH, MODEL_SAVE_SUBFOLDER)

def descargar_modelo():
    if not os.path.exists(MODELOS_LOCALES_PATH): # Asegurar que MODELOS_LOCALES_PATH exista
        try:
            os.makedirs(MODELOS_LOCALES_PATH)
            logger.info(f"Directorio base de modelos locales creado: {MODELOS_LOCALES_PATH}")
        except OSError as e:
            logger.error(f"No se pudo crear el directorio base de modelos locales {MODELOS_LOCALES_PATH}: {e}")
            return

    if not os.path.exists(FULL_SAVE_PATH):
        try:
            os.makedirs(FULL_SAVE_PATH)
            logger.info(f"Directorio de guardado específico del modelo creado: {FULL_SAVE_PATH}")
        except OSError as e:
            logger.error(f"No se pudo crear el directorio de guardado específico {FULL_SAVE_PATH}: {e}")
            return
    else:
        logger.info(f"Directorio de guardado específico ya existe: {FULL_SAVE_PATH}")

    logger.info(f"Descargando y guardando el modelo '{MODEL_ID_TO_DOWNLOAD}' en '{FULL_SAVE_PATH}'...")
    logger.info(f"Usando directorio de caché de Hugging Face: {CACHE_DIR_HF}")
    try:
        # Asegurar que el directorio de caché exista antes de usarlo
        if CACHE_DIR_HF and not os.path.exists(CACHE_DIR_HF):
            os.makedirs(CACHE_DIR_HF, exist_ok=True)
            logger.info(f"Directorio de caché de Hugging Face creado: {CACHE_DIR_HF}")

        model = SentenceTransformer(MODEL_ID_TO_DOWNLOAD, cache_folder=CACHE_DIR_HF)
        model.save(FULL_SAVE_PATH)
        logger.info(f"Modelo '{MODEL_ID_TO_DOWNLOAD}' guardado exitosamente en {FULL_SAVE_PATH}")
        logger.info("Archivos guardados:")
        for item in os.listdir(FULL_SAVE_PATH):
            logger.info(f" - {item}")
    except Exception as e:
        logger.error(f"ERROR al descargar o guardar el modelo '{MODEL_ID_TO_DOWNLOAD}':")
        logger.error(f"Tipo: {type(e)}, Mensaje: {str(e)}")
        logger.debug(traceback.format_exc())
        logger.error("Asegúrate de tener conexión a internet.")
        logger.error("Si es un problema de SSL (CERTIFICATE_VERIFY_FAILED):")
        logger.error("  1. Verifica tu conexión y configuración de red/proxy.")
        logger.error(f"  2. Considera descargar los archivos manualmente desde huggingface.co/{MODEL_ID_TO_DOWNLOAD}/tree/main y colocarlos en '{FULL_SAVE_PATH}'")
    finally:
        if 'original_ssl_cert_file' in locals() and original_ssl_cert_file is not None:
            os.environ['SSL_CERT_FILE'] = original_ssl_cert_file
        elif 'SSL_CERT_FILE' in os.environ and 'original_ssl_cert_file' in locals():
            del os.environ['SSL_CERT_FILE']
        if 'original_requests_ca_bundle' in locals() and original_requests_ca_bundle is not None:
            os.environ['REQUESTS_CA_BUNDLE'] = original_requests_ca_bundle
        elif 'REQUESTS_CA_BUNDLE' in os.environ and 'original_requests_ca_bundle' in locals():
            del os.environ['REQUESTS_CA_BUNDLE']

if __name__ == '__main__':
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    descargar_modelo()