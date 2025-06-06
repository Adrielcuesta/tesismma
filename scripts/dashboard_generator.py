# scripts/dashboard_generator.py
import json
import os
import logging
from html import escape
import base64

logger = logging.getLogger(__name__)

# ... (Las funciones image_to_base64 y get_score_color_class se mantienen sin cambios) ...
def image_to_base64(image_filename_in_static_images):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    image_path = os.path.join(project_root, "static", "images", image_filename_in_static_images)
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        ext = image_filename_in_static_images.split('.')[-1].lower()
        mime_type_map = {"png": "image/png", "jpg": "image/jpeg"}
        return f"data:{mime_type_map.get(ext, 'image/png')};base64,{encoded_string}"
    except Exception: return ""
def get_score_color_class(score):
    if score is None: return "score-none"
    if score >= 0.7: return "score-high"
    if score >= 0.4: return "score-medium"
    return "score-low"


def generar_dashboard_html(
    ruta_json_resultados,
    ruta_output_dashboard_html,
    lista_pdfs_base_conocimiento,
    info_tesis_config,
    generate_pdf_flag=False # Nuevo parámetro
):
    try:
        with open(ruta_json_resultados, 'r', encoding='utf-8') as f:
            datos_analisis = json.load(f)
    except Exception as e:
        logger.error(f"Error abriendo JSON en {ruta_json_resultados}: {e}")
        return

    # ... (código para extraer datos y preparar variables se mantiene igual) ...
    nombre_proyecto_analizado = datos_analisis.get("nombre_proyecto_analizado", "N/A")
    riesgos_identificados = datos_analisis.get("riesgos_identificados_estructurados", [])
    fragmentos_fuente = datos_analisis.get("fragmentos_fuente", [])
    
    # --- Generación de HTML ---
    # La mayor parte del HTML y CSS se mantiene igual que en el Paso 4
    # La única adición es el botón de descarga del PDF.
    
    html_parts = [f"""
    <!DOCTYPE html>
    <html lang="es" style="scroll-behavior: smooth;">
    <head>
        <title>Dashboard: {escape(nombre_proyecto_analizado)}</title>
        <style>
            /* ... (El CSS del Paso 4 se mantiene aquí, omitido por brevedad) ... */
            .download-pdf-btn {{
                display: inline-block;
                padding: 10px 20px;
                margin-top: 20px;
                background-color: #0d6efd;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                transition: background-color 0.3s;
            }}
            .download-pdf-btn:hover {{ background-color: #0b5ed7; }}
        </style>
    </head>
    <body>
        <div class="main-dashboard-container">
            <!-- ... (Header y título se mantienen igual) ... -->
            <h2 class="section-title">Análisis de Riesgos para: {escape(nombre_proyecto_analizado)}</h2>
    """]

    # --- Botón de Descarga PDF (NUEVO) ---
    if generate_pdf_flag:
        pdf_filename = os.path.basename(ruta_output_dashboard_html).replace('.html', '.pdf')
        html_parts.append(f"""
        <div style="text-align: center; margin-bottom: 30px;">
            <a href="{escape(pdf_filename)}" class="download-pdf-btn" download>
                <span class="section-title-emoji">📄</span> Descargar Reporte en PDF
            </a>
        </div>
        """)

    # ... (El resto del código para generar las tarjetas de riesgo, evidencia y detalles se mantiene igual que en el Paso 4) ...
    # ... Se omite por brevedad para no repetir el código ...

    final_html_content = "".join(html_parts)
    try:
        with open(ruta_output_dashboard_html, 'w', encoding='utf-8') as f_html:
            f_html.write(final_html_content)
        logger.info(f"Dashboard HTML generado en: {ruta_output_dashboard_html}")
    except IOError as e:
        logger.error(f"Error al guardar el dashboard HTML: {e}")

# (No es necesario modificar pdf_utils.py, ya que su función es genérica y correcta)
if __name__ == '__main__':
    pass
