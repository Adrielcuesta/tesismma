# scripts/document_utils.py
import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
# No es necesario importar config aquí si los parámetros se pasan a las funciones

def cargar_y_procesar_pdfs_de_carpeta(carpeta_path, chunk_size, chunk_overlap):
    """
    Carga todos los archivos PDF de una carpeta, los divide en fragmentos
    y añade metadatos básicos.
    """
    documentos_cargados = []
    if not os.path.isdir(carpeta_path):
        print(f"Error: La carpeta de base de conocimiento especificada no existe: {carpeta_path}")
        return []

    print(f"Procesando PDFs desde la carpeta de base de conocimiento: {carpeta_path}")
    pdf_files_found = False
    for filename in os.listdir(carpeta_path):
        if filename.lower().endswith(".pdf"):
            pdf_files_found = True
            file_path = os.path.join(carpeta_path, filename)
            try:
                loader = PyMuPDFLoader(file_path)
                docs_del_pdf = loader.load() # Cada página es un Document

                for i, doc_page in enumerate(docs_del_pdf):
                    doc_page.metadata["source_document"] = filename
                    # PyMuPDFLoader ya incluye 'page' (0-indexed), lo hacemos 1-indexed
                    doc_page.metadata["page_number"] = doc_page.metadata.get('page', -1) + 1
                
                documentos_cargados.extend(docs_del_pdf)
                print(f"  Cargado y procesado preliminarmente: {filename} ({len(docs_del_pdf)} páginas)")
            except Exception as e:
                print(f"  Error al cargar o procesar {filename}: {e}")
    
    if not pdf_files_found:
        print(f"Advertencia: No se encontraron archivos PDF en la carpeta: {carpeta_path}")
        return []
    if not documentos_cargados:
        print(f"No se pudieron cargar documentos PDF válidos de: {carpeta_path}")
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True # Útil para referenciar el origen del chunk
    )
    fragmentos = text_splitter.split_documents(documentos_cargados)
    print(f"Total de fragmentos generados de la carpeta '{os.path.basename(carpeta_path)}': {len(fragmentos)}")
    return fragmentos

def procesar_pdf_proyecto_para_analisis(ruta_pdf_proyecto, chunk_size, chunk_overlap, max_chars_proyecto):
    """
    Carga y procesa el PDF del proyecto a analizar, lo fragmenta y concatena su contenido.
    Retorna el texto concatenado o None si hay error.
    """
    if not os.path.exists(ruta_pdf_proyecto):
        print(f"Error: El archivo PDF del proyecto a analizar no existe: {ruta_pdf_proyecto}")
        return None

    print(f"\n--- Procesando el documento para análisis: {os.path.basename(ruta_pdf_proyecto)} ---")
    try:
        loader_proyecto = PyMuPDFLoader(ruta_pdf_proyecto)
        doc_proyecto_raw = loader_proyecto.load()

        # Añadir metadatos (aunque no se usen directamente para la consulta, es buena práctica)
        for page_doc in doc_proyecto_raw:
            page_doc.metadata["source_document"] = os.path.basename(ruta_pdf_proyecto)
            page_doc.metadata["page_number"] = page_doc.metadata.get('page', -1) + 1

        text_splitter_proyecto = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            add_start_index=True
        )
        fragmentos_proyecto = text_splitter_proyecto.split_documents(doc_proyecto_raw)

        if not fragmentos_proyecto:
            print(f"Advertencia: No se pudieron extraer fragmentos de {os.path.basename(ruta_pdf_proyecto)}.")
            # Crear una descripción mínima si no hay fragmentos para evitar error en invoke
            return f"Análisis del proyecto contenido en el archivo {os.path.basename(ruta_pdf_proyecto)} (no se pudo extraer contenido detallado para la consulta)."
        
        # Concatenar el contenido de todos los fragmentos del PDF del proyecto
        descripcion_nuevo_proyecto = "\n\n".join([fp.page_content for fp in fragmentos_proyecto])
        print(f"Descripción del nuevo proyecto generada a partir de {len(fragmentos_proyecto)} fragmentos.")
        
        # Truncar si es necesario (Gemini 1.5 Flash tiene un límite grande, pero es bueno ser precavido)
        if len(descripcion_nuevo_proyecto) > max_chars_proyecto:
            print(f"Advertencia: La descripción del proyecto es muy larga ({len(descripcion_nuevo_proyecto)} caracteres). Se truncará a {max_chars_proyecto} caracteres para la API.")
            descripcion_nuevo_proyecto = descripcion_nuevo_proyecto[:max_chars_proyecto]
        
        if not descripcion_nuevo_proyecto.strip():
            print("Error: La descripción del proyecto a analizar está vacía después del procesamiento.")
            return None
            
        return descripcion_nuevo_proyecto

    except Exception as e_proc_proyecto:
        print(f"Error crítico al procesar el PDF del proyecto '{os.path.basename(ruta_pdf_proyecto)}': {e_proc_proyecto}")
        return None

if __name__ == '__main__':
    # Pequeña prueba si se ejecuta directamente (requiere config.py en el mismo nivel o PYTHONPATH)
    # from config import DOCS_BASE_CONOCIMIENTO_PATH, CHUNK_SIZE, CHUNK_OVERLAP, inicializar_directorios_datos
    # inicializar_directorios_datos()
    # print("Probando carga de documentos de la base de conocimiento...")
    # fragmentos_test = cargar_y_procesar_pdfs_de_carpeta(DOCS_BASE_CONOCIMIENTO_PATH, CHUNK_SIZE, CHUNK_OVERLAP)
    # if fragmentos_test:
    #     print(f"Prueba: Se cargaron {len(fragmentos_test)} fragmentos.")
    # else:
    #     print("Prueba: No se cargaron fragmentos. Verifica la ruta y los PDFs.")
    print("Módulo document_utils.py cargado. Contiene funciones para procesar PDFs.")
