# scripts/vector_db_manager.py
import os
import shutil
import torch
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from . import document_utils 
from . import config # Para acceder a CACHE_DIR_HF
import traceback
import logging

logger = logging.getLogger(__name__)

def get_embedding_function(model_name_or_path):
    device = 'cpu' 
    cache_folder_path = config.CACHE_DIR_HF # Usar la ruta de caché de config.py

    logger.info(f"Intentando inicializar modelo de embeddings desde: '{model_name_or_path}' en dispositivo '{device}'.")
    logger.info(f"Usando directorio de caché para embeddings: '{cache_folder_path}'")
    
    try:
        # Asegurar que el directorio de caché exista (config.py ya lo hace, pero por si acaso)
        if cache_folder_path and not os.path.exists(cache_folder_path):
            try:
                os.makedirs(cache_folder_path, exist_ok=True)
                logger.info(f"Directorio de caché de embeddings creado: {cache_folder_path}")
            except Exception as e_mkdir:
                logger.error(f"No se pudo crear el directorio de caché {cache_folder_path}: {e_mkdir}")
                # No es un error fatal para el intento de carga, SentenceTransformer lo manejará.

        embedding_function = SentenceTransformerEmbeddings(
            model_name=model_name_or_path,
            model_kwargs={'device': device},
            cache_folder=cache_folder_path # Pasar el directorio de caché
        )
        try:
            model_display_name = os.path.basename(str(model_name_or_path))
        except:
            model_display_name = str(model_name_or_path)
        logger.info(f"Modelo de embeddings '{model_display_name}' inicializado exitosamente en '{device}'.")
        return embedding_function
    except Exception as e:
        logger.error(f"ERROR CRÍTICO al inicializar SentenceTransformerEmbeddings:")
        logger.error(f"Modelo intentado: '{model_name_or_path}' en dispositivo '{device}'")
        logger.error(f"Directorio de caché intentado: {cache_folder_path}")
        logger.error(f"Tipo de error: {type(e)}, Mensaje: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

def crear_o_cargar_chroma_db(chroma_db_path, docs_base_conocimiento_path, embedding_function, 
                               chunk_size, chunk_overlap, recrear_db_flag):
    if not embedding_function:
        logger.error("Función de embeddings no proporcionada a crear_o_cargar_chroma_db.")
        return None

    chroma_db_file_check = os.path.join(chroma_db_path, "chroma.sqlite3")

    if recrear_db_flag and os.path.exists(chroma_db_path):
        logger.info(f"Borrando base de datos ChromaDB existente en: {chroma_db_path} porque RECREAR_DB es True.")
        try:
            shutil.rmtree(chroma_db_path)
            os.makedirs(chroma_db_path, exist_ok=True) 
            logger.info(f"Carpeta {chroma_db_path} limpiada y recreada.")
        except Exception as e_shutil:
            logger.error(f"Error al intentar borrar la carpeta de ChromaDB: {e_shutil}")
            logger.debug(traceback.format_exc())
            return None 

    vector_db = None
    if not os.path.exists(chroma_db_file_check) or recrear_db_flag:
        logger.info(f"Intentando crear nueva base de datos vectorial en: {chroma_db_path}")
        # Usar el nombre de función correcto de tu document_utils.py
        fragmentos_base_conocimiento = document_utils.cargar_y_procesar_pdfs_de_carpeta(
            docs_base_conocimiento_path,
            chunk_size,
            chunk_overlap
        )

        if fragmentos_base_conocimiento:
            logger.info(f"Creando colección en ChromaDB con {len(fragmentos_base_conocimiento)} fragmentos...")
            try:
                logger.debug("Antes de llamar a Chroma.from_documents()...")
                vector_db = Chroma.from_documents(
                    documents=fragmentos_base_conocimiento,
                    embedding=embedding_function,
                    persist_directory=chroma_db_path
                )
                logger.info("¡ÉXITO! Base de datos vectorial creada y fragmentos añadidos.")
            except Exception as e_chroma_create:
                logger.error(f"ERROR FATALMENTE CRÍTICO durante Chroma.from_documents:")
                logger.error(f"Tipo de error: {type(e_chroma_create)}, Mensaje: {str(e_chroma_create)}")
                logger.debug(traceback.format_exc())
                return None
        else:
            logger.error("No se cargaron fragmentos de la base de conocimiento. La base de datos vectorial no se creará.")
            return None
    else:
        logger.info(f"Cargando base de datos vectorial existente desde: {chroma_db_path}")
        try:
            vector_db = Chroma(
                persist_directory=chroma_db_path,
                embedding_function=embedding_function
            )
            if vector_db and hasattr(vector_db, '_collection') and vector_db._collection and vector_db._collection.count() > 0:
                 logger.info(f"Base de datos vectorial cargada. Contiene {vector_db._collection.count()} fragmentos.")
            elif vector_db:
                 logger.warning("Base de datos vectorial cargada, pero la colección está vacía o su contenido no pudo ser verificado.")
            else:
                logger.error(f"No se pudo cargar la base de datos desde {chroma_db_path}.")
                return None
        except Exception as e_chroma_load:
            logger.error(f"Error crítico al cargar la base de datos Chroma existente: {e_chroma_load}")
            logger.debug(traceback.format_exc())
            return None
            
    return vector_db

if __name__ == '__main__':
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger.info("Módulo vector_db_manager.py cargado.")