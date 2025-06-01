# scripts/dashboard_generator.py
import json
import os
import logging
import traceback

logger = logging.getLogger(__name__)

def generar_dashboard_html(ruta_json_resultados, ruta_output_dashboard_html, lista_pdfs_base_conocimiento):
    # La información de la tesis ahora se toma de config.INFO_TESIS,
    # que main.py pasa (o debería pasar) a esta función si es necesario.
    # O, si se mantiene hardcodeada aquí, está bien para esta etapa.
    # Por ahora, usaremos los valores hardcodeados como en tu versión original.
    # Si INFO_TESIS se pasara desde config, aquí la recibirías como un argumento.

    try:
        with open(ruta_json_resultados, 'r', encoding='utf-8') as f:
            datos_analisis = json.load(f)
    except FileNotFoundError:
        logger.error(f"No se encontró el archivo JSON de resultados en {ruta_json_resultados}")
        return
    except json.JSONDecodeError:
        logger.error(f"No se pudo decodificar el archivo JSON en {ruta_json_resultados}")
        logger.debug(traceback.format_exc())
        return
    except Exception as e_open:
        logger.error(f"Error inesperado al abrir/leer JSON en {ruta_json_resultados}: {e_open}")
        logger.debug(traceback.format_exc())
        return

    nombre_proyecto_analizado = datos_analisis.get("nombre_proyecto_analizado", "Proyecto No Especificado")
    riesgos_identificados = datos_analisis.get("riesgos_identificados_estructurados", [])

    # Información de la tesis (hardcodeada como en tu original)
    titulo_tesis = "Sistema RAG para el Análisis de Riesgos en la Instalación de Maquinaria Industrial"
    institucion_line1 = "ITBA - Instituto Tecnológico Buenos Aires"
    institucion_line2 = "Maestría en Management & Analytics"
    alumno = "Adriel Cuesta"

    estado_map = {
        "Rojo": {"clase": "rojo", "titulo": "Riesgos Altos (Rojo)"},
        "Ámbar": {"clase": "ambar", "titulo": "Riesgos Medios (Ámbar/Naranja)"},
        "Verde": {"clase": "verde", "titulo": "Riesgos Bajos (Verde)"},
        "Gris (Indeterminado)": {"clase": "gris", "titulo": "Riesgos Indeterminados (Gris)"}
    }
    riesgos_agrupados = { key: [] for key in estado_map }
    for riesgo in riesgos_identificados:
        estado = riesgo.get("estado_RAG_sugerido", "Gris (Indeterminado)")
        riesgos_agrupados.get(estado, riesgos_agrupados["Gris (Indeterminado)"]).append(riesgo)
    orden_secciones = ["Rojo", "Ámbar", "Verde", "Gris (Indeterminado)"]

    html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análisis de Riesgos: {nombre_proyecto_analizado}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f0f2f5; color: #333; }}
        .container {{ max-width: 1200px; margin: auto; }}
        .main-header-container {{ text-align: center; margin-bottom: 15px; padding: 10px; }}
        .main-header-container p {{ margin: 3px 0; font-size: 1.1em; color: #4a5568; }}
        .main-header-container .institution {{ font-weight: bold; }}
        .main-header-container .degree {{ font-style: italic; }}
        .main-header-container .student {{ margin-top: 8px; }}
        .project-header-container {{ text-align: center; margin-bottom: 30px; padding: 20px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        .project-header-container h1 {{ color: #1a2533; margin-bottom: 5px; font-size: 2em; }}
        .project-header-container h2 {{ color: #4a5568; font-weight: 400; font-size: 1.2em; margin-top: 0; }}
        .risk-section {{ margin-bottom: 30px; }}
        .risk-section > h2 {{ font-size: 1.8em; color: #2c3e50; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px; margin-bottom: 20px; }}
        .dashboard-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 25px; }}
        .risk-card {{ background-color: #ffffff; border-radius: 10px; padding: 20px; box-shadow: 0 3px 10px rgba(0,0,0,0.07); transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out; border-top-width: 6px; border-top-style: solid; }}
        .risk-card:hover {{ transform: translateY(-5px); box-shadow: 0 6px 20px rgba(0,0,0,0.1); }}
        .risk-card h3 {{ margin-top: 0; color: #34495e; font-size: 1.2em; margin-bottom: 12px; }}
        .risk-card p {{ font-size: 0.95em; line-height: 1.65; margin-bottom: 8px; }}
        .risk-card .details-label {{ font-weight: 600; color: #555; }}
        .risk-card .details-value {{ color: #222; font-weight: 500; }}
        .footer-info, .thesis-title-footer {{ margin-top: 40px; padding: 20px; background-color: #34495e; color: #ecf0f1; border-radius: 12px; text-align: center; box-shadow: 0 -2px 10px rgba(0,0,0,0.05); }}
        .footer-info h3, .thesis-title-footer h3 {{ color: #ffffff; margin-bottom: 15px; font-size: 1.3em; }}
        .footer-info ul {{ list-style-type: none; padding: 0; display: flex; flex-wrap: wrap; justify-content: center; }}
        .footer-info li {{ margin: 5px 10px; padding: 8px 15px; background-color: #4a5568; color: #f0f2f5; border-radius: 6px; font-size: 0.9em; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
        .risk-card.rojo {{ border-top-color: #e74c3c; }}
        .risk-card.ambar {{ border-top-color: #f39c12; }}
        .risk-card.verde {{ border-top-color: #2ecc71; }}
        .risk-card.gris {{ border-top-color: #95a5a6; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="main-header-container">
            <p class="institution">{institucion_line1}</p>
            <p class="degree">{institucion_line2}</p>
            <p class="student">Alumno: {alumno}</p>
        </div>
        <div class="project-header-container">
            <h1>Análisis de Riesgos del Proyecto</h1>
            <h2>Proyecto Analizado: {nombre_proyecto_analizado}</h2>
        </div>
"""
    for estado_key in orden_secciones:
        riesgos_en_seccion = riesgos_agrupados[estado_key]
        info_estado = estado_map[estado_key]
        if riesgos_en_seccion:
            html_content += f"""
        <div class="risk-section">
            <h2>{info_estado['titulo']}</h2>
            <div class="dashboard-grid">
"""
            for riesgo in riesgos_en_seccion:
                descripcion = riesgo.get("descripcion_riesgo", "N/A")
                explicacion = riesgo.get("explicacion_riesgo_llm", "N/A")
                impacto = riesgo.get("impacto_estimado_llm", "N/A")
                probabilidad = riesgo.get("probabilidad_estimada_llm", "N/A")
                clase_color_tarjeta = info_estado['clase']
                html_content += f"""
                <div class="risk-card {clase_color_tarjeta}">
                    <h3>{descripcion}</h3>
                    <p>{explicacion}</p>
                    <p><span class="details-label">Impacto:</span> <span class="details-value">{impacto}</span> | <span class="details-label">Probabilidad:</span> <span class="details-value">{probabilidad}</span></p>
                </div>
"""
            html_content += """
            </div> 
        </div> 
"""
    if not riesgos_identificados:
         html_content += "<p>No se identificaron riesgos estructurados en este análisis.</p>"
    if lista_pdfs_base_conocimiento:
        html_content += """
    <div class="footer-info">
        <h3>Documentos de la Base de Conocimiento Utilizada</h3>
        <ul>
"""
        for pdf_name in lista_pdfs_base_conocimiento:
            html_content += f"            <li>{pdf_name}</li>\n"
        html_content += """
        </ul>
    </div>
"""
    html_content += f"""
        <div class="thesis-title-footer">
            <h3>Título del Trabajo: {titulo_tesis}</h3>
        </div>
    </div> 
</body>
</html>
"""
    try:
        with open(ruta_output_dashboard_html, 'w', encoding='utf-8') as f_html:
            f_html.write(html_content)
        logger.info(f"Dashboard HTML generado exitosamente en: {ruta_output_dashboard_html}")
    except IOError as e:
        logger.error(f"Error al guardar el dashboard HTML en {ruta_output_dashboard_html}: {e}")
        logger.debug(traceback.format_exc())

if __name__ == '__main__':
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger.info("Módulo dashboard_generator.py cargado.")