# scripts/document_utils.py
import os
import re
import logging
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from . import config

logger = logging.getLogger(__name__)

# --- INICIO: Lógica de Filtros Locales (Con capa de Metadatos) ---

def is_ignorable_page(page_text: str, min_chars=150) -> bool:
    text = (page_text or "").strip()
    if len(text) < min_chars:
        logger.info("      └─ Página ignorada por tener muy poco contenido.")
        return True
    return False

def is_metadata_page(page_text: str) -> bool:
    """Detecta si una página parece ser principalmente de metadatos (copyright, etc.)."""
    text_lower = page_text.lower()
    metadata_keywords = ["copyright", "todos los derechos reservados", "traducción oficial", "official translation", "ics", "isbn", "user licence only"]
    
    hits = sum(1 for keyword in metadata_keywords if keyword in text_lower)
    
    # Si la página tiene varias de estas palabras clave, es probablemente una página de metadatos.
    if hits >= 2:
        logger.info(f"      └─ Página descartada por [Filtro de Metadatos - {hits} palabras clave encontradas].")
        return True
    return False

def is_table_of_contents_page(page_text: str) -> bool:
    """Determina si una página parece ser una tabla de contenido."""
    lines = [line.strip() for line in page_text.strip().split('\n') if line.strip()]
    if len(lines) < 7: return False

    first_lines_text = " ".join(lines[:3]).lower()
    toc_keywords = ["índice", "contenido", "tabla de contenido", "table of contents", "sumario"]
    if any(keyword in first_lines_text for keyword in toc_keywords):
        logger.info("      └─ Página descartada por [Filtro de Índice - Palabra Clave].")
        return True

    short_numbered_lines = sum(1 for line in lines if len(line) < 150 and re.search(r'\d', line))
    ratio = short_numbered_lines / len(lines)
    if ratio > 0.4:
        logger.info(f"      └─ Página descartada por [Filtro de Índice - Densidad de Líneas Cortas y Numeradas: {ratio:.2f}].")
        return True

    dotted_lines = sum(1 for line in lines if '....' in line)
    if len(lines) > 0 and (dotted_lines / len(lines)) > 0.3:
        logger.info("      └─ Página descartada por [Filtro de Índice - Densidad de Puntos].")
        return True

    return False

def procesar_y_filtrar_paginas(docs: list) -> list:
    """Filtra una lista de páginas aplicando todas las capas de filtrado."""
    filtered_pages = []
    logger.info(f"  Iniciando filtrado de {len(docs)} páginas del documento...")
    for i, doc in enumerate(docs):
        page_content = doc.page_content
        
        # Aplicar todos los filtros
        if is_ignorable_page(page_content) or is_metadata_page(page_content):
            continue

        if i < config.MAX_PAGES_TO_CHECK_FOR_INDEX:
            if is_table_of_contents_page(page_content):
                continue
        
        filtered_pages.append(doc)

    logger.info(f"  Páginas retenidas tras todos los filtros: {len(filtered_pages)} de {len(docs)}.")
    return filtered_pages

# ... (El resto del archivo 'document_utils.py' no necesita cambios y se mantiene igual)

def cargar_y_procesar_pdfs_de_carpeta(carpeta_path, chunk_size, chunk_overlap):
    documentos_cargados_finales = []
    if not os.path.isdir(carpeta_path): return []
    logger.info(f"Procesando PDFs desde la carpeta: {carpeta_path}")
    for filename in os.listdir(carpeta_path):
        if filename.lower().endswith(".pdf"):
            logger.info(f"Procesando documento: {filename}")
            try:
                file_path = os.path.join(carpeta_path, filename)
                loader = PyMuPDFLoader(file_path)
                docs_del_pdf = loader.load()
                for doc_page in docs_del_pdf:
                    doc_page.metadata["source_document"] = filename
                    doc_page.metadata["page_number"] = doc_page.metadata.get('page', -1) + 1
                paginas_filtradas = procesar_y_filtrar_paginas(docs_del_pdf)
                if paginas_filtradas:
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len)
                    fragmentos = text_splitter.split_documents(paginas_filtradas)
                    logger.info(f"  Documento '{filename}' aportó {len(fragmentos)} fragmentos a la base de datos.")
                    documentos_cargados_finales.extend(fragmentos)
                else:
                    logger.warning(f"  El documento '{filename}' no generó contenido útil tras el filtrado.")
            except Exception as e:
                logger.error(f"  Error al cargar o procesar {filename}: {e}", exc_info=True)
    return documentos_cargados_finales

def procesar_pdf_proyecto_para_analisis(ruta_pdf_proyecto, max_chars_proyecto):
    if not os.path.exists(ruta_pdf_proyecto):
        logger.error(f"El archivo de proyecto no existe en la ruta: {ruta_pdf_proyecto}")
        return None
    logger.info(f"Procesando el documento para análisis: {os.path.basename(ruta_pdf_proyecto)}")
    try:
        loader_proyecto = PyMuPDFLoader(ruta_pdf_proyecto)
        doc_proyecto_raw = loader_proyecto.load()
        doc_proyecto_filtrado = [doc for doc in doc_proyecto_raw if not is_ignorable_page(doc.page_content)]
        if not doc_proyecto_filtrado:
            logger.warning(f"El documento del proyecto '{os.path.basename(ruta_pdf_proyecto)}' no contiene páginas con contenido sustancial.")
            return f"El documento del proyecto '{os.path.basename(ruta_pdf_proyecto)}' parece estar vacío o solo contiene portadas."
        descripcion_nuevo_proyecto = "\n\n".join([doc.page_content for doc in doc_proyecto_filtrado])
        logger.info(f"Descripción del proyecto generada desde {len(doc_proyecto_filtrado)} páginas útiles, total {len(descripcion_nuevo_proyecto)} caracteres.")
        if len(descripcion_nuevo_proyecto) > max_chars_proyecto:
            logger.warning(f"La descripción del proyecto excede el límite de {max_chars_proyecto} y será truncada.")
            descripcion_nuevo_proyecto = descripcion_nuevo_proyecto[:max_chars_proyecto]
        return descripcion_nuevo_proyecto
    except Exception as e_proc_proyecto:
        logger.error(f"Error crítico al procesar el PDF del proyecto: {e_proc_proyecto}", exc_info=True)
        return None

def obtener_ruta_pdf_proyecto(directorio_proyecto_analizar):
    if not os.path.isdir(directorio_proyecto_analizar): return None
    pdfs = [f for f in os.listdir(directorio_proyecto_analizar) if f.lower().endswith(".pdf")]
    return os.path.join(directorio_proyecto_analizar, pdfs[0]) if pdfs else None

def listar_documentos_kb(directorio_base_conocimiento):
    return [f for f in os.listdir(directorio_base_conocimiento) if f.lower().endswith(".pdf")] if os.path.isdir(directorio_base_conocimiento) else []