# scripts/test_chroma_super_minimal.py
import chromadb
import os
import shutil
import traceback

print("--- INICIO PRUEBA CHROMA SUPER MÍNIMA ---")
# Usa una ruta de prueba completamente nueva para esta prueba
# __file__ se refiere a este script (test_chroma_super_minimal.py)
# os.pardir sube un nivel (a la carpeta 'scripts')
# os.pardir de nuevo sube otro nivel (a la raíz del proyecto 'tesismma')
project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
CHROMA_DB_PATH_TEST = os.path.join(project_root_path, "datos", "ChromaDB_Test_Super_Minimal")

# Limpiar directorio de prueba
if os.path.exists(CHROMA_DB_PATH_TEST):
    print(f"Borrando directorio de prueba ChromaDB existente: {CHROMA_DB_PATH_TEST}")
    try:
        shutil.rmtree(CHROMA_DB_PATH_TEST)
    except Exception as e_shutil:
        print(f"Error borrando directorio de prueba: {e_shutil}")
os.makedirs(CHROMA_DB_PATH_TEST, exist_ok=True)
print(f"Directorio de prueba ChromaDB listo: {CHROMA_DB_PATH_TEST}")

try:
    print("Paso 1: Creando cliente Chroma persistente...")
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH_TEST)
    print("Cliente Chroma creado exitosamente.")

    print("\nPaso 2: Creando/obteniendo colección (usará embedding por defecto de Chroma)...")
    # ChromaDB usará su función de embedding por defecto (all-MiniLM-L6-v2).
    # Podría intentar descargarla si no la tiene en su caché interno,
    # lo que podría dar el error SSL si ese problema de red no está 100% resuelto
    # para las descargas internas de Chroma.
    collection = client.get_or_create_collection(name="my_super_minimal_collection")
    print("Colección obtenida/creada exitosamente.")

    print("\nPaso 3: Añadiendo documentos a la colección...")
    collection.add(
        documents=["Primer documento para prueba.", "Segundo documento de ejemplo."],
        ids=["doc1", "doc2"] # Se requieren IDs únicos
    )
    print("¡ÉXITO! Documentos añadidos a la colección.")

    print("\nPaso 4: Verificando la cantidad de ítems...")
    count = collection.count()
    print(f"La colección contiene {count} ítems.")

    if count > 0:
        print("\nPaso 5: Realizando una consulta de prueba...")
        results = collection.query(
            query_texts=["documento de prueba"],
            n_results=1
        )
        print(f"Resultados de la consulta: {results}")

except Exception as e:
    print("--------------------------------------------------------------------")
    print("ERROR CRÍTICO EN PRUEBA SUPER MÍNIMA:")
    print(f"Tipo: {type(e)}, Error: {str(e)}")
    traceback.print_exc()
    print("--------------------------------------------------------------------")

print("--- FIN PRUEBA CHROMA SUPER MÍNIMA ---")
