# scripts/vector_db_manager.py
import os
import shutil
import torch # Para la lógica de dispositivo, aunque aquí se use CPU
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
import document_utils
import traceback # Importar para imprimir el traceback completo

def get_embedding_function(model_name_or_path):
    """Inicializa y retorna la función de embeddings, usando CPU."""
    device = 'cpu' 
    print(f"INFO (vector_db_manager.py): Intentando inicializar modelo de embeddings desde: '{model_name_or_path}' en dispositivo '{device}'...")
    try:
        embedding_function = SentenceTransformerEmbeddings(
            model_name=model_name_or_path,
            model_kwargs={'device': device} 
        )
        try:
            model_display_name = os.path.basename(str(model_name_or_path))
        except: # En caso de que model_name_or_path no sea una cadena que os.path.basename pueda procesar
            model_display_name = str(model_name_or_path)

        print(f"Modelo de embeddings '{model_display_name}' inicializado exitosamente en '{device}'.")
        return embedding_function
    except Exception as e:
        print(f"--------------------------------------------------------------------")
        print(f"ERROR CRÍTICO (vector_db_manager.py) al inicializar SentenceTransformerEmbeddings:")
        print(f"Modelo intentado: '{model_name_or_path}' en dispositivo '{device}'")
        print(f"Tipo de error: {type(e)}")
        print(f"Mensaje de error: {str(e)}")
        print(f"--------------------------------------------------------------------")
        traceback.print_exc() # Imprime el traceback completo del error
        print(f"--------------------------------------------------------------------")
        return None

def crear_o_cargar_chroma_db(chroma_db_path, docs_base_conocimiento_path, embedding_function, 
                               chunk_size, chunk_overlap, recrear_db_flag):
    if not embedding_function:
        print("Error (vector_db_manager.py): Función de embeddings no proporcionada a crear_o_cargar_chroma_db.")
        return None

    chroma_db_file_check = os.path.join(chroma_db_path, "chroma.sqlite3")

    if recrear_db_flag and os.path.exists(chroma_db_path):
        print(f"Borrando base de datos ChromaDB existente en: {chroma_db_path} porque RECREAR_DB es True.")
        try:
            shutil.rmtree(chroma_db_path)
            os.makedirs(chroma_db_path, exist_ok=True) 
            print(f"Carpeta {chroma_db_path} limpiada y recreada.")
        except Exception as e_shutil:
            print(f"Error (vector_db_manager.py) al intentar borrar la carpeta de ChromaDB: {e_shutil}")
            traceback.print_exc() # Añadido para más detalle
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
                print("DEBUG (vector_db_manager.py): Antes de llamar a Chroma.from_documents()...")
                vector_db = Chroma.from_documents(
                    documents=fragmentos_base_conocimiento,
                    embedding=embedding_function,
                    persist_directory=chroma_db_path
                )
                print("¡ÉXITO (vector_db_manager.py)! Base de datos vectorial creada y fragmentos añadidos.")
            except Exception as e_chroma_create:
                # ESTE BLOQUE ES EL MÁS IMPORTANTE PARA VER EL ERROR
                print(f"--------------------------------------------------------------------")
                print(f"ERROR FATALMENTE CRÍTICO (vector_db_manager.py) durante Chroma.from_documents:")
                print(f"Tipo de error: {type(e_chroma_create)}")
                print(f"Mensaje de error: {str(e_chroma_create)}")
                print(f"--------------------------------------------------------------------")
                traceback.print_exc() # Imprime el traceback completo del error
                print(f"--------------------------------------------------------------------")
                return None # Asegura que la función retorna None si hay un error
        else:
            print("No se cargaron fragmentos de la base de conocimiento. La base de datos vectorial no se creará.")
            return None
    else:
        print(f"Cargando base de datos vectorial existente desde: {chroma_db_path}")
        try:
            vector_db = Chroma(
                persist_directory=chroma_db_path,
                embedding_function=embedding_function
            )
            if vector_db and hasattr(vector_db, '_collection') and vector_db._collection and vector_db._collection.count() > 0:
                 print(f"Base de datos vectorial cargada. Contiene {vector_db._collection.count()} fragmentos.")
            elif vector_db:
                 print("Advertencia (vector_db_manager.py): Base de datos vectorial cargada, pero la colección está vacía o su contenido no pudo ser verificado.")
            else:
                print(f"Error (vector_db_manager.py): No se pudo cargar la base de datos desde {chroma_db_path}.")
                return None
        except Exception as e_chroma_load:
            print(f"Error crítico (vector_db_manager.py) al cargar la base de datos Chroma existente: {e_chroma_load}")
            traceback.print_exc()
            return None
            
    return vector_db

if __name__ == '__main__':
    print("Módulo vector_db_manager.py cargado. Contiene funciones para gestionar ChromaDB.")
    # Para probar este módulo aisladamente:
    # (El código de prueba está comentado para no interferir con la ejecución normal desde main.py)
    # print("--- [INICIO] Probando vector_db_manager.py directamente ---")
    # import config 
    # config.inicializar_directorios_datos() 
    # config.RECREAR_DB = True 
    # print(f"Usando modelo: {config.EMBEDDING_MODEL_NAME_OR_PATH}")
    # test_embedding_func = get_embedding_function(config.EMBEDDING_MODEL_NAME_OR_PATH)
    # if test_embedding_func:
    #     print("Función de embeddings obtenida.")
    #     test_db = crear_o_cargar_chroma_db(
    #         config.CHROMA_DB_PATH, 
    #         config.DOCS_BASE_CONOCIMIENTO_PATH, 
    #         test_embedding_func,
    #         config.CHUNK_SIZE,
    #         config.CHUNK_OVERLAP,
    #         config.RECREAR_DB 
    #     )
    #     if test_db:
    #         print("Prueba de creación/carga de DB exitosa.")
    #     else:
    #         print("Prueba de creación/carga de DB fallida.")
    # else:
    #     print("Fallo al obtener la función de embeddings para la prueba.")
    # print("--- [FIN] Prueba de vector_db_manager.py ---")
