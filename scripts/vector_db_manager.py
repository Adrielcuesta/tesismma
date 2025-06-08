# scripts/vector_db_manager.py
import os
import shutil
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from . import document_utils 
from . import config
import logging

logger = logging.getLogger(__name__)

def get_embedding_function(model_name_or_path):
    device = 'cpu' 
    cache_folder_path = config.CACHE_DIR_HF
    logger.info(f"Intentando inicializar modelo de embeddings desde: '{model_name_or_path}' en dispositivo '{device}'.")
    try:
        embedding_function = SentenceTransformerEmbeddings(
            model_name=model_name_or_path,
            model_kwargs={'device': device},
            cache_folder=cache_folder_path
        )
        logger.info(f"Modelo de embeddings '{os.path.basename(str(model_name_or_path))}' inicializado exitosamente.")
        return embedding_function
    except Exception as e:
        logger.error(f"ERROR CRÍTICO al inicializar SentenceTransformerEmbeddings: {e}", exc_info=True)
        return None

def crear_o_cargar_chroma_db(chroma_db_path, docs_base_conocimiento_path, embedding_function, 
                               chunk_size, chunk_overlap, recrear_db_flag):
    if not embedding_function:
        logger.error("Función de embeddings no proporcionada.")
        return None

    db_exists = os.path.exists(os.path.join(chroma_db_path, 'chroma.sqlite3'))
    if recrear_db_flag or not db_exists:
        if recrear_db_flag and db_exists:
            logger.info(f"Borrando DB existente en: {chroma_db_path} porque se solicitó su recreación.")
            try:
                shutil.rmtree(chroma_db_path)
            except Exception as e:
                logger.error(f"Error al borrar la carpeta de ChromaDB: {e}")
                return None
        
        logger.info(f"Creando nueva base de datos vectorial en: {chroma_db_path}")
        fragmentos = document_utils.cargar_y_procesar_pdfs_de_carpeta(
            docs_base_conocimiento_path, chunk_size, chunk_overlap
        )
        if not fragmentos:
            logger.error("No se generaron fragmentos. La DB no se creará.")
            return None
        
        try:
            vector_db = Chroma.from_documents(documents=fragmentos, embedding=embedding_function, persist_directory=chroma_db_path)
            logger.info(f"✅ ¡ÉXITO! Base de datos vectorial creada con {len(fragmentos)} fragmentos.")
            return vector_db
        except Exception as e:
            logger.error(f"ERROR FATAL durante la creación de la base de datos: {e}", exc_info=True)
            return None
    else:
        logger.info(f"Cargando base de datos vectorial existente desde: {chroma_db_path}")
        try:
            vector_db = Chroma(persist_directory=chroma_db_path, embedding_function=embedding_function)
            count = vector_db._collection.count()
            if count == 0:
                logger.error("Error: La DB existente está vacía. Bórrela manualmente o active la opción para recrearla.")
                return None
            logger.info(f"✅ Base de datos vectorial cargada. Contiene {count} fragmentos.")
            return vector_db
        except Exception as e:
            logger.error(f"Error crítico al cargar la DB Chroma: {e}", exc_info=True)
            return None
