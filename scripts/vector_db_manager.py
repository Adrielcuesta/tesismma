# scripts/vector_db_manager.py
import os
import shutil
import torch
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from . import document_utils # CAMBIO A IMPORT RELATIVO
import traceback
import logging # Añadido

logger = logging.getLogger(__name__) # Añadido

def get_embedding_function(model_name_or_path):
    device = 'cpu' 
    logger.info(f"Intentando inicializar modelo de embeddings desde: '{model_name_or_path}' en dispositivo '{device}'...") # CAMBIO a logger
    try:
        embedding_function = SentenceTransformerEmbeddings(
            model_name=model_name_or_path,
            model_kwargs={'device': device} 
        )
        try:
            model_display_name = os.path.basename(str(model_name_or_path))
        except:
            model_display_name = str(model_name_or_path)
        logger.info(f"Modelo de embeddings '{model_display_name}' inicializado exitosamente en '{device}'.") # CAMBIO a logger
        return embedding_function
    except Exception as e:
        logger.error(f"ERROR CRÍTICO al inicializar SentenceTransformerEmbeddings:") # CAMBIO a logger
        logger.error(f"Modelo intentado: '{model_name_or_path}' en dispositivo '{device}'") # CAMBIO a logger
        logger.error(f"Tipo de error: {type(e)}, Mensaje: {str(e)}") # CAMBIO a logger
        logger.debug(traceback.format_exc()) # CAMBIO a logger.debug para el traceback completo
        return None

def crear_o_cargar_chroma_db(chroma_db_path, docs_base_conocimiento_path, embedding_function, 
                               chunk_size, chunk_overlap, recrear_db_flag):
    if not embedding_function:
        logger.error("Función de embeddings no proporcionada a crear_o_cargar_chroma_db.") # CAMBIO a logger
        return None

    chroma_db_file_check = os.path.join(chroma_db_path, "chroma.sqlite3")

    if recrear_db_flag and os.path.exists(chroma_db_path):
        logger.info(f"Borrando base de datos ChromaDB existente en: {chroma_db_path} porque RECREAR_DB es True.") # CAMBIO a logger
        try:
            shutil.rmtree(chroma_db_path)
            os.makedirs(chroma_db_path, exist_ok=True) 
            logger.info(f"Carpeta {chroma_db_path} limpiada y recreada.") # CAMBIO a logger
        except Exception as e_shutil:
            logger.error(f"Error al intentar borrar la carpeta de ChromaDB: {e_shutil}") # CAMBIO a logger
            logger.debug(traceback.format_exc())
            return None 

    vector_db = None
    if not os.path.exists(chroma_db_file_check) or recrear_db_flag:
        logger.info(f"Intentando crear nueva base de datos vectorial en: {chroma_db_path}") # CAMBIO a logger
        # Aquí se llama a la función de document_utils para cargar y procesar PDFs.
        # El nombre original en tu document_utils.py es cargar_y_procesar_pdfs_de_carpeta.
        # La versión de document_utils que te di arriba la renombró a cargar_y_dividir_documentos_kb.
        # Usaremos el nombre de tu document_utils original para minimizar cambios allí.
        fragmentos_base_conocimiento = document_utils.cargar_y_procesar_pdfs_de_carpeta(
            docs_base_conocimiento_path,
            chunk_size,
            chunk_overlap
        )

        if fragmentos_base_conocimiento:
            logger.info(f"Creando colección en ChromaDB con {len(fragmentos_base_conocimiento)} fragmentos...") # CAMBIO a logger
            try:
                logger.debug("DEBUG (vector_db_manager.py): Antes de llamar a Chroma.from_documents()...") # CAMBIO a logger
                vector_db = Chroma.from_documents(
                    documents=fragmentos_base_conocimiento,
                    embedding=embedding_function,
                    persist_directory=chroma_db_path
                )
                logger.info("¡ÉXITO (vector_db_manager.py)! Base de datos vectorial creada y fragmentos añadidos.") # CAMBIO a logger
            except Exception as e_chroma_create:
                logger.error(f"ERROR FATALMENTE CRÍTICO (vector_db_manager.py) durante Chroma.from_documents:") # CAMBIO a logger
                logger.error(f"Tipo de error: {type(e_chroma_create)}, Mensaje: {str(e_chroma_create)}") # CAMBIO a logger
                logger.debug(traceback.format_exc())
                return None
        else:
            logger.error("No se cargaron fragmentos de la base de conocimiento. La base de datos vectorial no se creará.") # CAMBIO a logger
            return None
    else:
        logger.info(f"Cargando base de datos vectorial existente desde: {chroma_db_path}") # CAMBIO a logger
        try:
            vector_db = Chroma(
                persist_directory=chroma_db_path,
                embedding_function=embedding_function
            )
            if vector_db and hasattr(vector_db, '_collection') and vector_db._collection and vector_db._collection.count() > 0:
                 logger.info(f"Base de datos vectorial cargada. Contiene {vector_db._collection.count()} fragmentos.") # CAMBIO a logger
            elif vector_db:
                 logger.warning("Advertencia (vector_db_manager.py): Base de datos vectorial cargada, pero la colección está vacía o su contenido no pudo ser verificado.") # CAMBIO a logger
            else: # Esto no debería pasar si Chroma() no lanza excepción
                logger.error(f"Error (vector_db_manager.py): No se pudo cargar la base de datos desde {chroma_db_path}.") # CAMBIO a logger
                return None
        except Exception as e_chroma_load:
            logger.error(f"Error crítico (vector_db_manager.py) al cargar la base de datos Chroma existente: {e_chroma_load}") # CAMBIO a logger
            logger.debug(traceback.format_exc())
            return None
            
    return vector_db

if __name__ == '__main__':
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger.info("Módulo vector_db_manager.py cargado.")