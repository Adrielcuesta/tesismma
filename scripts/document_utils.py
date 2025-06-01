# scripts/document_utils.py
import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging
import traceback

logger = logging.getLogger(__name__)

def obtener_ruta_pdf_proyecto(directorio_proyecto_analizar):
    if not os.path.isdir(directorio_proyecto_analizar):
        logger.error(f"El directorio para el proyecto a analizar no existe: {directorio_proyecto_analizar}")
        return None
    try:
        pdfs_en_directorio = [f for f in os.listdir(directorio_proyecto_analizar) if f.lower().endswith(".pdf")]
        if not pdfs_en_directorio:
            logger.error(f"No se encontraron archivos PDF en la carpeta '{directorio_proyecto_analizar}'.")
            return None
        if len(pdfs_en_directorio) > 1:
            logger.error(f"Se encontraron múltiples archivos PDF en '{directorio_proyecto_analizar}'. Solo debe haber uno.")
            logger.error(f"Archivos encontrados: {pdfs_en_directorio}")
            return None
        nombre_pdf_proyecto = pdfs_en_directorio[0]
        return os.path.join(directorio_proyecto_analizar, nombre_pdf_proyecto)
    except Exception as e:
        logger.error(f"Error al intentar obtener PDF del proyecto en '{directorio_proyecto_analizar}': {e}")
        logger.debug(traceback.format_exc())
        return None

def listar_documentos_kb(directorio_base_conocimiento):
    lista_pdfs = []
    try:
        if os.path.exists(directorio_base_conocimiento) and os.path.isdir(directorio_base_conocimiento):
            lista_pdfs = [f for f in os.listdir(directorio_base_conocimiento) if f.lower().endswith(".pdf")]
        if not lista_pdfs:
            logger.warning(f"No se encontraron PDFs en la carpeta de base de conocimiento: {directorio_base_conocimiento}")
    except Exception as e:
        logger.error(f"Error al listar PDFs de la base de conocimiento en '{directorio_base_conocimiento}': {e}")
        logger.debug(traceback.format_exc())
    return lista_pdfs

def cargar_y_procesar_pdfs_de_carpeta(carpeta_path, chunk_size, chunk_overlap): # Nombre de tu función original
    documentos_cargados = []
    if not os.path.isdir(carpeta_path):
        logger.error(f"Error: La carpeta de base de conocimiento especificada no existe: {carpeta_path}")
        return []

    logger.info(f"Procesando PDFs desde la carpeta de base de conocimiento: {carpeta_path}")
    pdf_files_found = False
    for filename in os.listdir(carpeta_path):
        if filename.lower().endswith(".pdf"):
            pdf_files_found = True
            file_path = os.path.join(carpeta_path, filename)
            try:
                loader = PyMuPDFLoader(file_path)
                docs_del_pdf = loader.load()
                for doc_page in docs_del_pdf:
                    doc_page.metadata["source_document"] = filename
                    doc_page.metadata["page_number"] = doc_page.metadata.get('page', -1) + 1
                documentos_cargados.extend(docs_del_pdf)
                logger.info(f"  Cargado y procesado preliminarmente: {filename} ({len(docs_del_pdf)} páginas)")
            except Exception as e:
                logger.error(f"  Error al cargar o procesar {filename}: {e}")
                logger.debug(traceback.format_exc())
    
    if not pdf_files_found:
        logger.warning(f"No se encontraron archivos PDF en la carpeta: {carpeta_path}")
        return []
    if not documentos_cargados:
        logger.error(f"No se pudieron cargar documentos PDF válidos de: {carpeta_path}")
        return []

    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            add_start_index=True
        )
        fragmentos = text_splitter.split_documents(documentos_cargados)
        logger.info(f"Total de fragmentos generados de la carpeta '{os.path.basename(carpeta_path)}': {len(fragmentos)}")
        return fragmentos
    except Exception as e:
        logger.error(f"Error durante la división de texto: {e}")
        logger.debug(traceback.format_exc())
        return []

def procesar_pdf_proyecto_para_analisis(ruta_pdf_proyecto, chunk_size, chunk_overlap, max_chars_proyecto): # Nombre de tu función original
    if not os.path.exists(ruta_pdf_proyecto):
        logger.error(f"Error: El archivo PDF del proyecto a analizar no existe: {ruta_pdf_proyecto}")
        return None

    logger.info(f"Procesando el documento para análisis: {os.path.basename(ruta_pdf_proyecto)}")
    try:
        loader_proyecto = PyMuPDFLoader(ruta_pdf_proyecto)
        doc_proyecto_raw = loader_proyecto.load()

        if not doc_proyecto_raw:
            logger.warning(f"No se pudo cargar contenido de {os.path.basename(ruta_pdf_proyecto)}.")
            return f"Análisis del proyecto contenido en el archivo {os.path.basename(ruta_pdf_proyecto)} (documento vacío o no cargable)."

        for page_doc in doc_proyecto_raw:
            page_doc.metadata["source_document"] = os.path.basename(ruta_pdf_proyecto)
            page_doc.metadata["page_number"] = page_doc.metadata.get('page', -1) + 1
        
        # Si el texto es para una consulta directa al LLM, a veces es mejor no fragmentarlo tanto,
        # o usar un chunk_size grande. Aquí se concatenará.
        text_splitter_proyecto = RecursiveCharacterTextSplitter(
            # Usar parámetros más grandes o simplemente concatenar si la fragmentación no es deseada aquí
            chunk_size=chunk_size * 5, # Ejemplo: chunks más grandes para el texto del proyecto
            chunk_overlap=chunk_overlap * 2,
            length_function=len,
            add_start_index=True
        )
        fragmentos_proyecto = text_splitter_proyecto.split_documents(doc_proyecto_raw)

        if not fragmentos_proyecto:
            logger.warning(f"No se pudieron extraer fragmentos de {os.path.basename(ruta_pdf_proyecto)}.")
            return f"Análisis del proyecto contenido en el archivo {os.path.basename(ruta_pdf_proyecto)} (no se pudo extraer contenido detallado)."
        
        descripcion_nuevo_proyecto = "\n\n".join([fp.page_content for fp in fragmentos_proyecto])
        logger.info(f"Descripción del nuevo proyecto generada a partir de {len(fragmentos_proyecto)} fragmentos, {len(descripcion_nuevo_proyecto)} caracteres.")
        
        if len(descripcion_nuevo_proyecto) > max_chars_proyecto:
            logger.warning(f"La descripción del proyecto es muy larga ({len(descripcion_nuevo_proyecto)} caracteres). Se truncará a {max_chars_proyecto} caracteres.")
            descripcion_nuevo_proyecto = descripcion_nuevo_proyecto[:max_chars_proyecto]
        
        if not descripcion_nuevo_proyecto.strip():
            logger.error("Error: La descripción del proyecto a analizar está vacía después del procesamiento.")
            # Devolver un string indicando vacío para que el LLM sepa que no hay contenido.
            return f"El documento del proyecto '{os.path.basename(ruta_pdf_proyecto)}' parece estar vacío o no contiene texto extraíble."
            
        return descripcion_nuevo_proyecto

    except Exception as e_proc_proyecto:
        logger.error(f"Error crítico al procesar el PDF del proyecto '{os.path.basename(ruta_pdf_proyecto)}': {e_proc_proyecto}")
        logger.debug(traceback.format_exc())
        return None

if __name__ == '__main__':
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger.info("Módulo document_utils.py cargado.")