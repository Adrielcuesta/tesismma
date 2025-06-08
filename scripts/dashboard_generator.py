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

def generar_dashboard_html(ruta_json_resultados, ruta_output_dashboard_html, lista_pdfs_base_conocimiento, info_tesis_config=None):
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
    
    risk_category_emojis = {"Rojo": "🔥", "Ámbar": "⚠️", "Verde": "🟢", "Gris (Indeterminado)": "❓"}
    estado_map = {
        "Rojo": {"clase": "rojo", "titulo": "Riesgos Altos"}, "Ámbar": {"clase": "ambar", "titulo": "Riesgos Medios"},
        "Verde": {"clase": "verde", "titulo": "Riesgos Bajos"}, "Gris (Indeterminado)": {"clase": "gris", "titulo": "Riesgos Indeterminados"}
    }
    orden_secciones = ["Rojo", "Ámbar", "Verde", "Gris (Indeterminado)"]

    # 1. Riesgos (Tarjetas Resumen)
    riesgos_html = ""
    if riesgos_identificados:
        secciones_html = []
        riesgos_con_indices = list(enumerate(riesgos_identificados))
        for estado_key in orden_secciones:
            riesgos_en_categoria = [(i, r) for i, r in riesgos_con_indices if r.get("estado_RAG_sugerido") == estado_key]
            if not riesgos_en_categoria: continue

            cards_html = []
            for i, riesgo in riesgos_en_categoria:
                score = riesgo.get("score_confianza_compuesto")
                confiabilidad_class = get_confiabilidad_class(score)
                confiabilidad_text = f"Confiabilidad: {score:.0%}" if score is not None else "Confiabilidad: N/A"
                
                cards_html.append(f'''
                <a href="#risk-detail-{i}" class="risk-card {escape(estado_map[estado_key]["clase"])}">
                    <h6>{escape(riesgo.get("descripcion_riesgo", "N/A"))}</h6>
                    <div class="risk-summary-details">
                        <p><span class="details-label">Impacto:</span> <span class="details-value">{escape(riesgo.get("impacto_estimado", "N/A"))}</span></p>
                        <p><span class="details-label">Probabilidad:</span> <span class="details-value">{escape(riesgo.get("probabilidad_estimada", "N/A"))}</span></p>
                        <p><span class="details-label">Mitigación:</span> <span class="details-value">{escape(riesgo.get("responsabilidad_mitigacion", "N/A"))}</span></p>
                        <p><span class="details-label">Responsable:</span> <span class="details-value">{escape(riesgo.get("responsable_accidente", "N/A"))}</span></p>
                    </div>
                    <p class="risk-confiabilidad {confiabilidad_class}">{confiabilidad_text}</p>
                </a>''')
            
            secciones_html.append(f'''
            <div class="risk-section">
                <h5><span class="section-title-emoji">{risk_category_emojis.get(estado_key, '')}</span>{escape(estado_map[estado_key]["titulo"])}</h5>
                <div class="dashboard-grid">{"".join(cards_html)}</div>
            </div>''')
        riesgos_html = "".join(secciones_html)
    else:
        riesgos_html = "<p class='no-content-message'>No se identificaron riesgos en este análisis.</p>"

    # 2. Detalles de Riesgos
    risk_details_html = ""
    if riesgos_identificados:
        details_list = [f'''
            <div class="risk-detail-item" id="risk-detail-{i}">
                <h4><span class="section-title-emoji">ℹ️</span>{escape(riesgo.get("descripcion_riesgo", "N/A"))}</h4>
                <div class="details-grid-full">
                    <div><span class="detail-label">Nivel de Riesgo (RAG):</span> {escape(riesgo.get("estado_RAG_sugerido", "N/A"))}</div>
                    <div><span class="detail-label">Impacto Estimado:</span> {escape(riesgo.get("impacto_estimado", "N/A"))}</div>
                    <div><span class="detail-label">Probabilidad Estimada:</span> {escape(riesgo.get("probabilidad_estimada", "N/A"))}</div>
                    <div><span class="detail-label">Responsable de Mitigación:</span> {escape(riesgo.get("responsabilidad_mitigacion", "N/A"))}</div>
                    <div><span class="detail-label">Responsable en Caso de Accidente:</span> {escape(riesgo.get("responsable_accidente", "N/A"))}</div>
                </div>
                <p class="explanation-paragraph"><span class="detail-label">Explicación Detallada:</span> {escape(riesgo.get("explicacion_riesgo", "N/A"))}</p>
            </div>''' 
            for i, riesgo in enumerate(riesgos_identificados)
        ]
        risk_details_html = "".join(details_list)
        
    # 3. Evidencia Utilizada
    evidence_html = ""
    if fragmentos_fuente:
        fragmentos_ordenados = sorted(
            fragmentos_fuente, 
            key=lambda x: -1 if x.get("score_relevancia") is None else x.get("score_relevancia"), 
            reverse=True)
        evidence_list = [f'''
            <div class="source-chunk">
                <div class="chunk-header">
                    <span>Fuente: {escape(frag.get("nombre_documento_fuente", "N/A"))}, Pág: {escape(str(frag.get("numero_pagina", "N/A")))}</span>
                    <span class="relevance-score">Relevancia: {f'{frag.get("score_relevancia"):.0%}' if frag.get("score_relevancia") is not None else "N/A"}</span>
                </div>
                <div class="chunk-content"><p>{escape(frag.get("contenido", ""))}</p></div>
            </div>'''
            for frag in fragmentos_ordenados
        ]
        evidence_html = "".join(evidence_list)

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
        h4.app-subtitle{{color:#555;font-size:1em;font-weight:700;font-style:italic;margin-top:2px;margin-bottom:15px}}
        p.student-name{{color:#333;font-size:1.1em;font-weight:700;margin-top:15px;margin-bottom:20px}}
        .project-analysis-title,.section-title{{text-align:center;font-size:1.5em;color:#1a2533;margin-top:0;margin-bottom:25px;padding-bottom:15px;border-bottom:2px solid #e0e0e0}}
        .risk-section > h5, .details-section > h2, .evidence-section > h2{{font-size:1.4em;color:#2c3e50;border-bottom:1px solid #e0e0e0;padding-bottom:10px;margin-bottom:20px;text-align:left}}
        .section-title-emoji{{margin-right:8px}}
        .dashboard-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}}
        .risk-card{{background-color:#fdfdfd;border:1px solid #e9ecef;border-radius:8px;padding:15px;box-shadow:0 2px 8px rgba(0,0,0,.06);transition:all .2s ease-in-out;border-top-width:5px;border-top-style:solid;display:flex;flex-direction:column;text-decoration:none;color:inherit}}
        .risk-card:hover{{transform:translateY(-4px);box-shadow:0 5px 15px rgba(0,0,0,.08)}}
        .risk-card h6{{margin:0 0 8px;color:#34495e;font-size:1em;flex-grow:1}}
        .risk-card .risk-summary-details p{{font-size:.8em;line-height:1.4;margin:0 0 4px;color:#666;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
        .risk-card .details-label{{font-weight:600;color:#444}}.risk-card .details-value{{font-weight:400}}
        .risk-confiabilidad{{font-size:.85em;font-weight:600;margin-top:10px;padding-top:8px;border-top:1px solid #f0f0f0}}
        .confiabilidad-high{{color:#1E8449}} .confiabilidad-medium{{color:#B9770E}}
        .confiabilidad-low{{color:#707B7C}} .confiabilidad-none{{color:#707B7C}}
        .risk-card.rojo{{border-top-color:#e74c3c}}.risk-card.ambar{{border-top-color:#f39c12}}
        .risk-card.verde{{border-top-color:#2ecc71}}.risk-card.gris{{border-top-color:#95a5a6}}
        .details-section,.evidence-section{{margin-top:30px;padding-top:20px;border-top:1px solid #e0e0e0}}
        .risk-detail-item{{margin-bottom:20px;padding-bottom:15px;border-bottom:1px dashed #ccc}}
        .risk-detail-item:last-child{{border-bottom:none}}
        .risk-detail-item h4{{font-size:1.1em;color:#34495e;margin:0 0 12px}}
        .risk-detail-item .details-grid-full{{display:grid;grid-template-columns:1fr;gap:8px;margin-bottom:12px;font-size:.9em}}
        .risk-detail-item .details-grid-full div{{background-color:#f8f9fa;padding:8px 12px;border-radius:4px}}
        .risk-detail-item p.explanation-paragraph{{font-size:.9em;line-height:1.6;margin:0}}
        .risk-detail-item .detail-label{{font-weight:700;color:#444}}
        .source-chunk{{border:1px solid #e9ecef;border-radius:8px;margin-bottom:15px}}
        .chunk-header{{display:flex;justify-content:space-between;align-items:center;padding:10px 15px;background-color:#f8f9fa;border-bottom:1px solid #e9ecef;font-size:.9em}}
        .relevance-score{{font-weight:500;color:#555}}
        .chunk-content p{{margin:0;white-space:pre-wrap;padding:15px;font-size:.9em;line-height:1.6}}
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
            <h4 class="app-subtitle">{escape(it.get("app_subtitle", ""))}</h4><p class="student-name">Alumno: {escape(it.get("alumno", ""))}</p>
        </div>
        <h2 class="project-analysis-title">Resultados del Análisis para: {nombre_proyecto_analizado}</h2>
        {riesgos_html}
        <div class="details-section">
            <h2 class="section-title">Detalles de Riesgos Identificados</h2>
            {risk_details_html if riesgos_identificados else "<p class='no-content-message'>No se identificaron riesgos para detallar.</p>"}
        </div>
        <div class="evidence-section">
            <h2 class="section-title">Evidencia Utilizada</h2>
            {evidence_html if fragmentos_fuente else "<p class='no-content-message'>No se recuperó evidencia de la base de conocimiento.</p>"}
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