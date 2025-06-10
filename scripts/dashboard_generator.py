# scripts/dashboard_generator.py
import json
import os
import logging
import datetime
from html import escape
import base64

logger = logging.getLogger(__name__)
CURRENT_YEAR = datetime.datetime.now().year

def image_to_base64(image_filename_in_static_images):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    image_path = os.path.join(project_root, "static", "images", image_filename_in_static_images)
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        ext = image_filename_in_static_images.split('.')[-1].lower()
        mime_type_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "svg": "image/svg+xml", "gif": "image/gif"}
        mime_type = mime_type_map.get(ext, f"image/{ext}")
        return f"data:{mime_type};base64,{encoded_string}"
    except FileNotFoundError:
        logger.error(f"¡IMAGEN NO ENCONTRADA! Verifica esta ruta: {image_path}")
        return "" 
    except Exception as e:
        logger.error(f"Error codificando imagen {image_path} a Base64: {e}")
        return ""

def get_confiabilidad_class(score):
    if score is None: return "confiabilidad-none"
    if score >= 0.7: return "confiabilidad-high"
    if score >= 0.45: return "confiabilidad-medium"
    return "confiabilidad-low"

def generar_dashboard_html(ruta_json_resultados, ruta_output_dashboard_html, info_tesis_config=None):
    try:
        with open(ruta_json_resultados, 'r', encoding='utf-8') as f:
            datos_analisis = json.load(f)
    except Exception as e: 
        logger.error(f"Error abriendo o parseando JSON en {ruta_json_resultados}: {e}")
        return

    nombre_proyecto_analizado = escape(datos_analisis.get("nombre_proyecto_analizado", "Proyecto No Especificado"))
    riesgos_identificados = datos_analisis.get("riesgos_identificados_estructurados", [])
    fragmentos_fuente = datos_analisis.get("fragmentos_fuente", [])
    it = info_tesis_config or {}
    
    header_banner_base64 = image_to_base64("header_banner_abstract.png") 
    logo_inline_base64 = image_to_base64("logo-itba.png")                
    logo_itba_footer_base64 = image_to_base64("itba.png")               
    
    # --- LÓGICA PARA DETALLES DE RIESGO (MODIFICADA) ---
    risk_details_html = ""
    if riesgos_identificados:
        details_list = []
        for riesgo in riesgos_identificados:
            details_list.append(f'''
            <div class="risk-detail-item">
                <h4><span class="info-icon">ℹ️</span> {escape(riesgo.get("descripcion_riesgo", "N/A"))}</h4>
                <p><strong>Tipo de Riesgo:</strong> {escape(riesgo.get("tipo_de_riesgo", "N/D"))}</p>
                <p><strong>Explicación Detallada:</strong> {escape(riesgo.get("explicacion_riesgo", "N/A"))}</p>
                <p><strong>Impacto Estimado:</strong> {escape(riesgo.get("impacto_estimado", "N/A"))}</p>
                <p><strong>Probabilidad Estimada:</strong> {escape(riesgo.get("probabilidad_estimada", "N/A"))}</p>
                <p><strong>Nivel de Riesgo (RAG Sugerido):</strong> {escape(riesgo.get("estado_RAG_sugerido", "N/A"))}</p>
            </div>''')
        risk_details_html = "".join(details_list)
    else:
        risk_details_html = "<p class='no-content-message'>No se identificaron riesgos para detallar.</p>"

    # --- LÓGICA PARA DOCUMENTOS DE BASE DE CONOCIMIENTO (MODIFICADA) ---
    knowledge_base_html = ""
    if fragmentos_fuente:
        documentos_unicos = sorted(list(set(frag.get("nombre_documento_fuente") for frag in fragmentos_fuente if frag.get("nombre_documento_fuente"))))
        list_items = "".join([f'<li>{escape(doc)}</li>' for doc in documentos_unicos])
        knowledge_base_html = f'<ul>{list_items}</ul>'
    else:
        knowledge_base_html = "<p class='no-content-message'>No se utilizó evidencia de la base de conocimiento.</p>"

    final_html = f'''
<!DOCTYPE html>
<html lang="es" style="scroll-behavior: smooth;">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Análisis de Riesgos: {nombre_proyecto_analizado}</title>
    <style>
        body{{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;margin:0;padding:0;background-color:#f0f2f5;color:#333;display:flex;flex-direction:column;align-items:center}}
        .page-wrapper{{width:100%;display:flex;flex-direction:column;align-items:center;padding:20px;box-sizing:border-box}}
        .main-dashboard-container{{background-color:#fff;padding:30px 40px;border-radius:12px;box-shadow:0 6px 20px rgba(0,0,0,.1);width:100%;max-width:1000px;text-align:left;margin-bottom:30px}}
        .abstract-banner-container{{width:100%;height:100px;margin-bottom:25px;background-image:url("{header_banner_base64}");background-size:cover;background-position:center;border-radius:6px}}
        .header-content{{text-align:center;margin-bottom:30px}}
        .title-with-logo{{display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:8px}}
        .title-with-logo img.logo-inline{{height:37px;width:auto}}
        h1{{color:#1a2533;font-size:1.7em;margin:0}}h2{{color:#2c3e50;font-size:1.3em;margin-top:8px;font-weight:500}}
        h3{{color:#4a5568;font-size:1.1em;margin-bottom:10px;font-weight:400}}
        .section-title{{text-align:center;font-size:1.5em;color:#1a2533;margin-top:0;margin-bottom:25px;padding-bottom:15px;border-bottom:2px solid #e0e0e0}}
        .details-section,.kb-section{{margin-top:30px;padding-top:20px;border-top:1px solid #e0e0e0}}
        .details-section > h2, .kb-section > h2 {{font-size:1.4em;color:#2c3e50;border-bottom:1px solid #e0e0e0;padding-bottom:10px;margin-bottom:20px;text-align:left}}
        .risk-detail-item{{margin-bottom:15px;padding-bottom:15px;border-bottom:1px dashed #ccc}}
        .risk-detail-item:last-child{{border-bottom:none}}
        .risk-detail-item h4{{font-size:1.1em;color:#34495e;margin:0 0 12px;display:flex;align-items:center}}
        .risk-detail-item p{{font-size:.95em;line-height:1.6;margin:4px 0 8px 0;}}
        .risk-detail-item p strong{{color:#333;}}
        .info-icon{{margin-right:8px;color:#3498db;}}
        .kb-section ul {{list-style-type: square; padding-left: 20px;}}
        .kb-section li {{margin-bottom: 8px; font-size: 0.95em;}}
        .no-content-message{{text-align:center;font-style:italic;color:#6c757d;padding:40px;background-color:#f8f9fa;border-radius:8px}}
        .dashboard-page-footer{{width:100%;text-align:center;padding:25px 0;font-size:.9em;color:#6c757d;margin-top:30px;border-top:1px solid #d0d0d0}}
        .dashboard-page-footer p{{margin:5px 0}}
        .dashboard-page-footer img.logo-itba-footer{{max-height:45px;margin-bottom:10px;opacity:.9}}
        .dashboard-page-footer a{{color:#007bff;text-decoration:none}}
    </style>
</head>
<body>
<div class="page-wrapper">
    <div class="main-dashboard-container">
        <div class="abstract-banner-container"></div> 
        <div class="header-content">
            <div class="title-with-logo"><img src="{logo_inline_base64}" alt="Logo" class="logo-inline"><h1>{escape(it.get("titulo_tesis_h1", ""))}</h1></div>
            <h2>{escape(it.get("titulo_tesis_h2", ""))}</h2><h3>{escape(it.get("titulo_tesis_h3", ""))}</h3>
        </div>
        <h2 class="section-title">Resultados del Análisis para: {nombre_proyecto_analizado}</h2>
        <div class="details-section">
            <h2 class="section-title">Detalles de Riesgos Identificados</h2>
            {risk_details_html}
        </div>
        <div class="kb-section">
            <h2 class="section-title">Documentos de la Base de Conocimiento Utilizada</h2>
            {knowledge_base_html}
        </div>
    </div>
    <div class="dashboard-page-footer">
        <img src="{logo_itba_footer_base64}" alt="Logo ITBA" class="logo-itba-footer">
        <p>{escape(it.get("institucion_line1", ""))} - {escape(it.get("institucion_line2", ""))}</p>
        <p><a href="{escape(str(it.get('github_repo_url', '#')))}" target="_blank">Ver Repositorio en GitHub</a></p>
        <p>&copy; {CURRENT_YEAR} {escape(it.get("alumno", ""))}. Todos los derechos reservados.</p>
    </div>
</div>
</body></html>'''

    try:
        os.makedirs(os.path.dirname(ruta_output_dashboard_html), exist_ok=True)
        with open(ruta_output_dashboard_html, 'w', encoding='utf-8') as f_html:
            f_html.write(final_html)
        logger.info(f"Dashboard HTML generado exitosamente en: {ruta_output_dashboard_html}")
    except IOError as e:
        logger.error(f"Error al guardar el dashboard HTML en {ruta_output_dashboard_html}: {e}")