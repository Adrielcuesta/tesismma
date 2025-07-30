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

def get_confidence_class(score):
    if score is None: return "conf-none-text"
    if score >= 0.7: return "conf-high-text"
    if score >= 0.45: return "conf-medium-text"
    return "conf-low-text"

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
    
    risk_category_emojis = {"Rojo": "🔥", "Ámbar": "⚠️", "Verde": "✅", "Gris (Indeterminado)": "❓"}
    estado_map = {
        "Rojo": {"clase": "rojo", "titulo": "Riesgos Altos"},
        "Ámbar": {"clase": "ambar", "titulo": "Riesgos Medios"},
        "Verde": {"clase": "verde", "titulo": "Riesgos Bajos"},
        "Gris (Indeterminado)": {"clase": "gris", "titulo": "Riesgos Indeterminados"}
    }
    riesgos_agrupados = {key: [] for key in estado_map}
    for riesgo in riesgos_identificados:
        estado = riesgo.get("estado_RAG_sugerido", "Gris (Indeterminado)")
        riesgos_agrupados.get(estado, riesgos_agrupados["Gris (Indeterminado)"]).append(riesgo)
    orden_secciones = ["Rojo", "Ámbar", "Verde", "Gris (Indeterminado)"]

    final_html = f'''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Análisis de Riesgos: {nombre_proyecto_analizado}</title>
    <style>
        body{{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;margin:0;padding:0;background-color:#f0f2f5;color:#333;}}
        .page-wrapper{{width:100%;display:flex;flex-direction:column;align-items:center;padding:20px;box-sizing:border-box;}}
        .main-dashboard-container{{background-color:#fff;padding:30px 40px;border-radius:12px;box-shadow:0 6px 20px rgba(0,0,0,.1);width:100%;max-width:1200px;text-align:left;margin-bottom:30px;}}
        .abstract-banner-container{{width:100%;height:100px;margin-bottom:25px;background-image:url("{header_banner_base64}");background-size:cover;background-position:center;border-radius:6px;}}
        .header-content{{text-align:center;margin-bottom:30px;}}
        .title-with-logo{{display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:8px;}}
        .title-with-logo img.logo-inline{{height:37px;width:auto;}}
        h1{{color:#1a2533;font-size:1.7em;margin:0;}} h2{{color:#2c3e50;font-size:1.3em;margin-top:8px;font-weight:500;}} h3{{color:#4a5568;font-size:1.1em;margin:8px 0;font-weight:400;}}
        .app-subtitle{{color:#555;font-size:1.0em;font-weight:bold;font-style:italic;margin-top:2px;margin-bottom:15px;}}
        .student-name{{color:#333;font-size:1.1em;font-weight:bold;margin-top:15px;}}
        .project-analysis-title{{text-align:center;font-size:1.6em;color:#1a2533;margin-top:0;margin-bottom:30px;padding-bottom:15px;border-bottom:2px solid #e0e0e0;}}
        .risk-section{{margin-bottom:35px;}}
        .risk-section-title{{font-size:1.4em;color:#2c3e50;border-bottom:1px solid #e0e0e0;padding-bottom:10px;margin-bottom:20px;display:flex;align-items:center;}}
        .section-emoji{{margin-right:12px;font-size:1.2em;}}
        .dashboard-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:20px;}}
        .risk-card{{background-color:#fdfdfd;border:1px solid #e9ecef;border-radius:8px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.06);transition:transform .2s,box-shadow .2s;border-left-width:5px;border-left-style:solid;display:flex;flex-direction:column;}}
        .risk-card:hover{{transform:translateY(-4px);box-shadow:0 5px 15px rgba(0,0,0,.1);}}
        .risk-card h6{{margin:0 0 12px;color:#34495e;font-size:1.05em;line-height:1.4;flex-grow:1;}}
        .risk-card-body p{{font-size:0.85em;line-height:1.5;margin:4px 0;}}
        .risk-card-confidence{{text-align:right;margin-top:12px;padding-top:8px;border-top:1px solid #eee;}}
        .risk-card.rojo{{border-left-color:#e74c3c;}} .risk-card.ambar{{border-left-color:#f39c12;}} .risk-card.verde{{border-left-color:#2ecc71;}} .risk-card.gris{{border-left-color:#95a5a6;}}
        .details-section{{margin-top:40px;padding-top:20px;border-top:2px solid #e0e0e0;}}
        .details-section-title{{text-align:left;font-size:1.4em;color:#2c3e50;margin-bottom:25px;}}
        .risk-detail-item{{margin-bottom:20px;padding-bottom:15px;border-bottom:1px dashed #ccc;}} .risk-detail-item:last-child{{border-bottom:none;}}
        .risk-detail-item h4{{font-size:1.1em;color:#34495e;margin:0 0 8px; display:flex; align-items:center;}}
        .risk-detail-item p{{font-size:.95em;line-height:1.6;margin:4px 0;}}
        .detail-label{{font-weight:600;color:#555;}}
        .kb-section{{margin-top:40px;padding-top:20px;border-top:1px solid #e8e8e8;}} .kb-section h2{{font-size:1.4em;}}
        .confidence-score{{font-size:0.9em;font-weight:700;}}
        .conf-high-text{{color:#27ae60;}} .conf-medium-text{{color:#f39c12;}} .conf-low-text{{color:#e74c3c;}} .conf-none-text{{color:#7f8c8d;}}
        .dashboard-page-footer{{width:100%;text-align:center;padding:25px 0;font-size:.9em;color:#6c757d;margin-top:30px;border-top:1px solid #d0d0d0;}}
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
        <h2 class="project-analysis-title">Resultados del Análisis para: {nombre_proyecto_analizado}</h2>
    '''

    # --- SECCIÓN DE TARJETAS DE RESUMEN ---
    summary_html_parts = []
    for estado_key in orden_secciones:
        riesgos_en_seccion = riesgos_agrupados[estado_key]
        if riesgos_en_seccion:
            info_estado = estado_map[estado_key]
            emoji = risk_category_emojis.get(estado_key, '')
            summary_html_parts.append(f'<div class="risk-section"><h3 class="risk-section-title"><span class="section-emoji">{emoji}</span>{info_estado["titulo"]}</h3><div class="dashboard-grid">')
            for riesgo in riesgos_en_seccion:
                score = riesgo.get("score_confianza_compuesto")
                score_display = f"{score:.0%}" if score is not None else "N/D"
                conf_class = get_confidence_class(score)
                summary_html_parts.append(f'''
                <div class="risk-card {info_estado['clase']}">
                    <h6>{escape(riesgo.get("descripcion_riesgo","N/A"))}</h6>
                    <div class="risk-card-body">
                        <p><span class="detail-label">Tipo:</span> {escape(riesgo.get("tipo_de_riesgo", "N/A"))}</p>
                        <p><span class="detail-label">Impacto:</span> {escape(riesgo.get("impacto_estimado","N/A"))}</p>
                        <p><span class="detail-label">Probabilidad:</span> {escape(riesgo.get("probabilidad_estimada","N/A"))}</p>
                        <p><span class="detail-label">Responsable:</span> {escape(riesgo.get("responsable_accidente", "N/A"))}</p>
                    </div>
                    <div class="risk-card-confidence">
                        <span class="confidence-score {conf_class}">{score_display}</span>
                    </div>
                </div>''')
            summary_html_parts.append('</div></div>')
    
    if not any(riesgos_agrupados.values()):
        final_html += "<p style='text-align:center; font-style:italic;'>No se identificaron riesgos.</p>"
    else:
        final_html += "".join(summary_html_parts)

    # --- SECCIÓN DE DETALLES COMPLETOS ---
    if riesgos_identificados:
        final_html += '<div class="details-section"><h3 class="details-section-title">Detalles Completos de Riesgos Identificados</h3>'
        for riesgo in riesgos_identificados:
            score = riesgo.get("score_confianza_compuesto")
            score_display = f"{score:.0%}" if score is not None else "N/D"
            conf_class = get_confidence_class(score)
            final_html += f'''
            <div class="risk-detail-item">
                <h4><span class="section-emoji">ℹ️</span>{escape(riesgo.get("descripcion_riesgo","N/A"))}</h4>
                <p><span class="detail-label">Explicación:</span> {escape(riesgo.get("explicacion_riesgo","N/A"))}</p>
                <p><span class="detail-label">Impacto:</span> {escape(riesgo.get("impacto_estimado","N/A"))} | <span class="detail-label">Probabilidad:</span> {escape(riesgo.get("probabilidad_estimada","N/A"))}</p>
                <p><span class="detail-label">Responsable (Mitigación):</span> {escape(riesgo.get("responsabilidad_mitigacion", "N/A"))}</p>
                <p><span class="detail-label">Responsable (Accidente):</span> {escape(riesgo.get("responsable_accidente", "N/A"))}</p>
                <p><span class="detail-label">Tipo de Riesgo:</span> {escape(riesgo.get("tipo_de_riesgo", "N/A"))}</p>
                <p><span class="detail-label">Score de Confianza:</span> <span class="confidence-score {conf_class}">{score_display}</span></p>
            </div>'''
        final_html += '</div>'

    # --- SECCIÓN DE BASE DE CONOCIMIENTO ---
    kb_html = ""
    if fragmentos_fuente:
        documentos_unicos = sorted(list(set(frag.get("nombre_documento_fuente") for frag in fragmentos_fuente if frag.get("nombre_documento_fuente"))))
        list_items = "".join([f'<li>{escape(doc)}</li>' for doc in documentos_unicos])
        kb_html = f'<div class="kb-section"><h2>Documentos de la Base de Conocimiento Utilizada</h2><ul>{list_items}</ul></div>'
    final_html += kb_html

    # --- FOOTER ---
    final_html += f'''
    </div>
    <div class="dashboard-page-footer">
        <img src="{logo_itba_footer_base64}" alt="Logo ITBA" style="max-height:45px;margin-bottom:10px;">
        <p>{escape(it.get("institucion_line1",""))} - {escape(it.get("institucion_line2",""))}</p>
        <p><a href="{escape(str(it.get('github_repo_url','#')))}" target="_blank">Ver Repositorio en GitHub</a></p>
        <p>&copy; {CURRENT_YEAR} {escape(it.get("alumno",""))}. Todos los derechos reservados.</p>
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

# --- MODO DE PRUEBA ---
if __name__ == '__main__':
    if not logging.getLogger().handlers: 
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    logger.info("--- Ejecutando dashboard_generator.py en modo de prueba ---")
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    test_output_dir = os.path.join(project_root, "datos", "Resultados", "ModoPrueba")
    os.makedirs(test_output_dir, exist_ok=True)
    
    dummy_json_path = os.path.join(test_output_dir, "analisis_de_prueba.json")
    dummy_dashboard_path = os.path.join(test_output_dir, "dashboard_de_prueba.html")
    
    try:
        from config import INFO_TESIS
    except ImportError:
        INFO_TESIS = {}

    dummy_data = {
        "nombre_proyecto_analizado": "Proyecto de Prueba de Diseño (Final)",
        "riesgos_identificados_estructurados": [
            {"descripcion_riesgo": "Fallo crítico en sistema por sobrecalentamiento", "tipo_de_riesgo": "Implícito", "explicacion_riesgo": "Explicación detallada...", "impacto_estimado": "Alto", "probabilidad_estimada": "Alta", "estado_RAG_sugerido": "Rojo", "score_confianza_compuesto": 0.85, "responsabilidad_mitigacion": "Mantenimiento", "responsable_accidente": "Jefe de Operaciones"},
            {"descripcion_riesgo": "Retrasos en la entrega de componentes clave", "tipo_de_riesgo": "Explícito", "explicacion_riesgo": "Explicación detallada...", "impacto_estimado": "Medio", "probabilidad_estimada": "Media", "estado_RAG_sugerido": "Ámbar", "score_confianza_compuesto": 0.65, "responsabilidad_mitigacion": "Compras", "responsable_accidente": "Logística"},
            {"descripcion_riesgo": "Documentación del manual de usuario incompleta", "tipo_de_riesgo": "Explícito", "explicacion_riesgo": "Explicación detallada...", "impacto_estimado": "Bajo", "probabilidad_estimada": "Baja", "estado_RAG_sugerido": "Verde", "score_confianza_compuesto": 0.30, "responsabilidad_mitigacion": "Ingeniería", "responsable_accidente": "Equipo de Proyecto"}
        ],
        "fragmentos_fuente": [{"nombre_documento_fuente": "Manual_Tecnico.pdf"}]
    }
    
    with open(dummy_json_path, 'w', encoding='utf-8') as f_dummy:
        json.dump(dummy_data, f_dummy, ensure_ascii=False, indent=4)
    logger.info(f"Archivo JSON de prueba creado en: {dummy_json_path}")
    
    generar_dashboard_html(
        ruta_json_resultados=dummy_json_path,
        ruta_output_dashboard_html=dummy_dashboard_path,
        info_tesis_config=INFO_TESIS
    )
    
    logger.info(f"--- Prueba completada. Abre este archivo en tu navegador: ---")
    logger.info(f"{os.path.abspath(dummy_dashboard_path)}")