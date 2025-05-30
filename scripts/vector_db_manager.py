# scripts/vector_db_manager.py
import os
import shutil
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
# No es necesario importar config si los parámetros se pasan a las funciones
# Importar document_utils para usar su función de carga
import document_utils

def get_embedding_function(model_name):
    """Inicializa y retorna la función de embeddings."""
    print(f"Inicializando modelo de embeddings: {model_name}...")
    try:
        embedding_function = SentenceTransformerEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'} # Usar CPU por defecto para mayor compatibilidad local
        )
        print(f"Modelo de embeddings '{model_name}' inicializado en CPU.")
        return embedding_function
    except Exception as e:
        print(f"Error crítico al inicializar el modelo de embeddings '{model_name}': {e}")
        return None

def crear_o_cargar_chroma_db(chroma_db_path, docs_base_conocimiento_path, embedding_function, 
                               chunk_size, chunk_overlap, recrear_db_flag):
    """
    Crea una nueva base de datos ChromaDB o carga una existente.
    Retorna la instancia de la base de datos vectorial o None si hay error.
    """
    if not embedding_function:
        print("Error: Función de embeddings no proporcionada a crear_o_cargar_chroma_db.")
        return None

    chroma_db_file_check = os.path.join(chroma_db_path, "chroma.sqlite3") # Archivo principal de Chroma

    if recrear_db_flag and os.path.exists(chroma_db_path):
        print(f"Borrando base de datos ChromaDB existente en: {chroma_db_path} porque RECREAR_DB es True.")
        try:
            shutil.rmtree(chroma_db_path)
            # Es importante recrear la carpeta raíz para ChromaDB después de borrarla
            os.makedirs(chroma_db_path, exist_ok=True) 
            print(f"Carpeta {chroma_db_path} limpiada y recreada.")
        except Exception as e_shutil:
            print(f"Error al intentar borrar la carpeta de ChromaDB: {e_shutil}")
            # Considerar si se debe detener la ejecución aquí
            return None 

    vector_db = None
    if not os.path.exists(chroma_db_file_check) or recrear_db_flag:
        print(f"Intentando crear nueva base de datos vectorial en: {chroma_db_path}")
        print("Cargando documentos de la base de conocimiento...")
        
        fragmentos_base_conocimiento = document_utils.cargar_y_procesar_pdfs_de_carpeta(
            docs_base_conocimiento_path,
            chunk_size,
            chunk_overlap
        )

        if fragmentos_base_conocimiento:
            print(f"Creando colección en ChromaDB con {len(fragmentos_base_conocimiento)} fragmentos...")
            try:
                vector_db = Chroma.from_documents(
                    documents=fragmentos_base_conocimiento,
                    embedding=embedding_function,
                    persist_directory=chroma_db_path
                )
                # ChromaDB >0.4.0 persiste automáticamente, .persist() puede ser obsoleto o no necesario.
                # vector_db.persist() 
                print("Base de datos vectorial creada y fragmentos añadidos exitosamente.")
            except Exception as e_chroma_create:
                print(f"Error crítico al crear la base de datos Chroma: {e_chroma_create}")
                return None
        else:
            print("No se cargaron fragmentos de la base de conocimiento. La base de datos vectorial no se creará.")
            # Si no hay documentos, no se puede crear una DB útil.
            return None
    else:
        print(f"Cargando base de datos vectorial existente desde: {chroma_db_path}")
        try:
            vector_db = Chroma(
                persist_directory=chroma_db_path,
                embedding_function=embedding_function
            )
            # Verificar si la colección cargada tiene elementos
            if vector_db and hasattr(vector_db, '_collection') and vector_db._collection and vector_db._collection.count() > 0:
                 print(f"Base de datos vectorial cargada. Contiene {vector_db._collection.count()} fragmentos.")
            elif vector_db: # Se cargó pero está vacía o no se pudo verificar
                 print("Advertencia: Base de datos vectorial cargada, pero la colección está vacía o su contenido no pudo ser verificado.")
                 print("Asegúrate de que haya PDFs en BaseConocimiento y considera recrear la DB si es la primera vez o hay cambios.")
            else: # No se pudo cargar
                print(f"Error: No se pudo cargar la base de datos desde {chroma_db_path}.")
                return None
        except Exception as e_chroma_load:
            print(f"Error crítico al cargar la base de datos Chroma existente: {e_chroma_load}")
            print(f"Si el problema persiste, considera borrar la carpeta '{chroma_db_path}' y re-ejecutar con RECREAR_DB=True.")
            return None
            
    return vector_db

if __name__ == '__main__':
    # Pequeña prueba (requiere config.py y document_utils.py)
    # from config import (CHROMA_DB_PATH, DOCS_BASE_CONOCIMIENTO_PATH, EMBEDDING_MODEL_NAME, 
    #                     CHUNK_SIZE, CHUNK_OVERLAP, RECREAR_DB, inicializar_directorios_datos)
    # inicializar_directorios_datos()
    # print("Probando gestión de base de datos vectorial...")
    # test_embedding_func = get_embedding_function(EMBEDDING_MODEL_NAME)
    # if test_embedding_func:
    #     test_db = crear_o_cargar_chroma_db(
    #         CHROMA_DB_PATH, 
    #         DOCS_BASE_CONOCIMIENTO_PATH, 
    #         test_embedding_func,
    #         CHUNK_SIZE,
    #         CHUNK_OVERLAP,
    #         RECREAR_DB # Usar el flag de config para la prueba
    #     )
    #     if test_db:
    #         print("Prueba de gestión de DB exitosa.")
    #     else:
    #         print("Prueba de gestión de DB fallida.")
    print("Módulo vector_db_manager.py cargado. Contiene funciones para gestionar ChromaDB.")
