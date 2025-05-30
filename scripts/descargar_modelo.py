from sentence_transformers import SentenceTransformer
import os

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
# Asegúrate de que esta ruta coincida exactamente con la que usas en tu .env/config.py
SAVE_PATH = "D:/tesismma/modelos_locales/all-MiniLM-L6-v2" 

if not os.path.exists(SAVE_PATH):
    os.makedirs(SAVE_PATH)
    print(f"Directorio creado: {SAVE_PATH}")

print(f"Descargando y guardando el modelo '{MODEL_ID}' en '{SAVE_PATH}'...")
try:
    # Si sigues con problemas de SSL aquí, necesitarás resolverlos para esta descarga específica
    # o descargar manualmente los archivos del modelo desde el sitio web de Hugging Face.
    model = SentenceTransformer(MODEL_ID)
    model.save(SAVE_PATH)
    print(f"Modelo guardado exitosamente en {SAVE_PATH}")
except Exception as e:
    print(f"Error al descargar o guardar el modelo: {e}")
    print("Asegúrate de tener conexión a internet y de que no haya problemas de SSL.")
    print(f"Si es un problema de SSL, considera descargar los archivos manualmente desde huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/main y colocarlos en {SAVE_PATH}")