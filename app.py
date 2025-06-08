# app.py
import os
import sys
import logging
import traceback
import datetime
from flask import Flask, render_template_string, send_file, url_for, redirect, flash, request
from werkzeug.utils import secure_filename
from pydantic import ValidationError

# --- Configuración de Rutas y Módulos ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from scripts.main import run_analysis
    from scripts import config
    from scripts.descargar_modelo import descargar_modelo
except ImportError as e:
    logging.basicConfig(level=logging.ERROR)
    logging.error(f"Error crítico al importar módulos necesarios: {e}")
    run_analysis, config, descargar_modelo = None, None, None

# --- Creación y Configuración de la App Flask ---
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

if descargar_modelo and config:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger_startup = logging.getLogger(__name__)

    logger_startup.info("--- Verificando existencia de modelo de embeddings local ---")
    if not os.path.exists(config.LOCAL_EMBEDDING_MODEL_PATH):
        logger_startup.warning(f"Modelo no encontrado en '{config.LOCAL_EMBEDDING_MODEL_PATH}'.")
        logger_startup.info("Iniciando descarga automática del modelo. Esto puede tardar unos minutos...")
        try:
            descargar_modelo()
            logger_startup.info("✅ Descarga del modelo completada exitosamente.")
        except Exception as e:
            logger_startup.error(f"❌ FALLO CRÍTICO: No se pudo descargar el modelo de embedding. La aplicación no podrá funcionar. Error: {e}")
    else:
        logger_startup.info(f"✅ Modelo ya existe en '{config.LOCAL_EMBEDDING_MODEL_PATH}'. No se necesita descarga.")

ALLOWED_EXTENSIONS = {'pdf'}
MAX_KB_FILES = 4
MAX_KB_TOTAL_SIZE_MB = 8 * 1024 * 1024
MAX_PROJECT_FILE_SIZE_MB = 2 * 1024 * 1024
FOOTER_INFO = getattr(config, 'INFO_TESIS', {})
CURRENT_YEAR = datetime.datetime.now().year

if not app.debug:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers.extend(gunicorn_logger.handlers)
    app.logger.setLevel(logging.INFO)
else:
    app.logger.setLevel(logging.INFO)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clear_directory(directory_path):
    if not os.path.isdir(directory_path): return
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e:
            app.logger.error(f'Error al eliminar {file_path}. Razón: {e}')

HOME_PAGE_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análisis de Riesgos - Tesis Adriel Cuesta</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f0f2f5; color: #333; display: flex; flex-direction: column; align-items: center; min-height: 95vh; }
        .main-container { background-color: #ffffff; padding: 30px 40px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.1); width: 100%; max-width: 1000px; text-align: left; margin-bottom: auto; }
        .abstract-banner-container { width: 100%; height: 100px; margin-bottom: 25px; background-image: url("{{ url_for('static', filename='images/header_banner_abstract.png') }}"); background-size: cover; background-position: center; border-radius: 6px; background-color: #f0f0f0; }
        .header-content { text-align: center; margin-bottom: 30px; }
        .title-with-logo { display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 8px; }
        .title-with-logo img.logo-inline { height: 37px; width: auto; }
        .header-content h1 { color: #1a2533; font-size: 1.7em; margin: 0; font-weight: 600; }
        .header-content h2 { color: #2c3e50; font-size: 1.3em; margin-top: 8px; margin-bottom: 5px; font-weight: 500; }
        .header-content h3 { color: #4a5568; font-size: 1.1em; margin-bottom: 10px; font-weight: 400; }
        .header-content h4.app-subtitle { color: #555; font-size: 1.0em; font-weight: bold; font-style: italic; margin-top: 2px; margin-bottom: 15px; }
        .header-content p.student-name { color: #333; font-size: 1.1em; font-weight: bold; margin-top: 15px; }
        .upload-sections-container { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 20px; }
        .config-section-container { grid-column: 1 / -1; }
        .form-section { padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #f8f9fa; }
        .form-section h4 { margin-top: 0; color: #212529; font-size: 1.2em; border-bottom: 1px solid #e9ecef; padding-bottom: 8px; margin-bottom: 15px; }
        .form-section h4 .emoji { margin-right: 8px; font-size: 1.1em; }
        label { display: block; margin-bottom: 8px; font-weight: 600; font-size: 0.95em; color: #343a40;}
        .checkbox-container div { margin-bottom: 10px; }
        input[type="file"], select { width: 100%; box-sizing: border-box; margin-top: 5px; margin-bottom:10px; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
        input[type="checkbox"] { vertical-align: middle; margin-bottom:0; margin-right:3px;}
        input[type="file"]:disabled { background-color: #e9ecef; cursor: not-allowed; }
        .checkbox-label { display: inline !important; font-weight: normal !important; font-size:0.9em !important; vertical-align:middle; color: #495057;}
        .button-container { text-align: center; margin-top: 30px; }
        .button { display: inline-block; background-color: #007bff; color: white; padding: 14px 35px; border: none; border-radius: 5px; cursor: pointer; font-size: 1.1em; text-decoration: none; transition: background-color 0.3s ease; font-weight: 500; }
        .button:hover { background-color: #0056b3; }
        .button-disabled { background-color: #cccccc; cursor: not-allowed; }
        .loader { border: 5px solid #f3f3f3; border-top: 5px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 30px auto 0 auto; display: none; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .flash-messages { list-style-type: none; padding: 0; margin: 20px 0; }
        .flash-messages li { padding: 12px 15px; margin-bottom: 10px; border-radius: 5px; font-size: 0.95em;}
        .flash-messages .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .flash-messages .info { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .flash-messages .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .footer { width: 100%; text-align: center; padding: 25px 0; font-size: 0.9em; color: #6c757d; margin-top:40px; border-top: 1px solid #dee2e6; }
        .footer p { margin: 5px 0; }
        .footer img.logo-itba-footer { max-height: 45px; margin-bottom: 10px; opacity: 0.9; }
        .footer a { color: #007bff; text-decoration: none; }
        .footer a:hover { text-decoration: underline; }
        @media (max-width: 768px) { .upload-sections-container { grid-template-columns: 1fr; } .main-container { padding: 20px; } .header-content h1 { font-size: 1.5em; } .title-with-logo img.logo-inline { height: 28px; } .abstract-banner-container { height: 180px; } }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="abstract-banner-container"></div>
        <div class="header-content">
            <div class="title-with-logo">
                <img src="{{ url_for('static', filename='images/logo-itba.png') }}" alt="Logo RAG" class="logo-inline">
                <h1>TESIS FIN DE MAESTRÍA</h1>
            </div>
            <h2>Innovación en entornos empresariales</h2>
            <h3>Sistemas RAG para la Optimización de la Gestión de Proyectos y Análisis Estratégico.</h3>
            <h4 class="app-subtitle">ANALIZADOR DE RIESGOS CON IA.</h4>
            <p class="student-name">Alumno: Adriel J. Cuesta</p>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <ul class="flash-messages">
                {% for category, message in messages %}
                    <li class="{{ category }}">{{ message }}</li>
                {% endfor %}
                </ul>
            {% endif %}
        {% endwith %}
        <form id="analysisForm" action="{{ url_for('analyze_route') }}" method="post" enctype="multipart/form-data">
            <div class="config-section-container">
                <div class="form-section">
                    <h4><span class="emoji">⚙️</span>Configuración del Análisis</h4>
                    <label for="llm_model_input">Seleccionar Modelo de Lenguaje (LLM):</label>
                    <select id="llm_model_input" name="llm_model">
                        {% for model_id, model_info in llm_models.items() %}
                            <option value="{{ model_id }}">{{ model_info.display_name }}</option>
                        {% endfor %}
                    </select>
                </div>
            </div>
            <div class="upload-sections-container">
                <div class="form-section">
                    <h4><span class="emoji">📚</span>Base de Conocimiento</h4>
                    <div class="checkbox-container">
                        <input type="checkbox" id="use_default_kb_input" name="use_default_kb" value="yes" checked>
                        <label for="use_default_kb_input" class="checkbox-label">Usar Base de Conocimiento por defecto.</label>
                    </div>
                    <label for="kb_files_input" style="margin-top:10px;">Subir PDFs para nueva Base de Conocimiento:</label>
                    <input type="file" id="kb_files_input" name="kb_files" multiple accept=".pdf">
                </div>
                <div class="form-section">
                    <h4><span class="emoji">📄</span>Proyecto a Analizar</h4>
                    <div class="checkbox-container">
                        <input type="checkbox" id="use_existing_project_file_input" name="use_existing_project_file" value="yes" checked>
                        <label for="use_existing_project_file_input" class="checkbox-label">Utilizar documento previamente cargado.</label>
                    </div>
                    <label for="project_file_input" style="margin-top:10px;">Subir PDF del Proyecto a Analizar:</label>
                    <input type="file" id="project_file_input" name="project_file" accept=".pdf">
                </div>
            </div>
            <div class="button-container">
                <button type="submit" id="analyzeButton" class="button">Iniciar Análisis</button>
            </div>
        </form>
        <div id="loader" class="loader"></div>
    </div>
    <div class="footer">
        <img src="{{ url_for('static', filename='images/itba.png') }}" alt="Logo ITBA" class="logo-itba-footer">
        <p>{{ footer_info.institucion_line1 }} - {{ footer_info.institucion_line2 }}</p>
        <p><a href="{{ footer_info.github_repo_url }}" target="_blank">Ver Repositorio en GitHub</a></p>
        <p>&copy; {{ CURRENT_YEAR }} Adriel J. Cuesta. Todos los derechos reservados.</p>
    </div>
    <script>
        const useDefaultKbCheckbox = document.getElementById('use_default_kb_input');
        const kbFilesInput = document.getElementById('kb_files_input');
        const useExistingProjectCheckbox = document.getElementById('use_existing_project_file_input');
        const projectFileInput = document.getElementById('project_file_input');
        function toggleKbFileInput() { kbFilesInput.disabled = useDefaultKbCheckbox.checked; if (useDefaultKbCheckbox.checked) kbFilesInput.value = null; }
        function toggleProjectFileInput() { projectFileInput.disabled = useExistingProjectCheckbox.checked; if (useExistingProjectCheckbox.checked) projectFileInput.value = null; }
        toggleKbFileInput();
        useDefaultKbCheckbox.addEventListener('change', toggleKbFileInput);
        toggleProjectFileInput();
        useExistingProjectCheckbox.addEventListener('change', toggleProjectFileInput);
        document.getElementById('analysisForm').addEventListener('submit', function(event) {
            document.getElementById('loader').style.display = 'block';
            const analyzeBtn = document.getElementById('analyzeButton');
            analyzeBtn.disabled = true;
            analyzeBtn.classList.add('button-disabled');
            analyzeBtn.innerText = 'Procesando...';
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    app.logger.info("Acceso a la ruta de inicio ('/').")
    if run_analysis is None or config is None:
        flash("Error crítico: La aplicación no está configurada correctamente. Revise los logs del servidor.", "error")

    llm_models_for_template = getattr(config, 'LLM_MODELS', {})
    return render_template_string(HOME_PAGE_HTML, footer_info=FOOTER_INFO, llm_models=llm_models_for_template, CURRENT_YEAR=CURRENT_YEAR)

@app.route('/analyze', methods=['POST'])
def analyze_route():
    app.logger.info("Solicitud POST a /analyze recibida.")

    if run_analysis is None or config is None:
        flash("Error del servidor: La función de análisis o configuración no está cargada.", "error")
        return redirect(url_for('home'))

    selected_llm_model_id = request.form.get('llm_model')
    use_default_kb_checkbox = request.form.get('use_default_kb') == 'yes'
    use_existing_project_file_checkbox = request.form.get('use_existing_project_file') == 'yes'
    kb_files_uploaded = request.files.getlist('kb_files')
    project_file_uploaded = request.files.get('project_file')

    recreate_db_for_this_run = not use_default_kb_checkbox

    if not use_default_kb_checkbox:
        actual_kb_files_to_save = [f for f in kb_files_uploaded if f and f.filename != '' and allowed_file(f.filename)]
        if actual_kb_files_to_save:
            clear_directory(config.DIRECTORIO_BASE_CONOCIMIENTO)
            for file in actual_kb_files_to_save:
                filename = secure_filename(file.filename)
                file.save(os.path.join(config.DIRECTORIO_BASE_CONOCIMIENTO, filename))
            flash(f"{len(actual_kb_files_to_save)} archivo(s) guardados para la Base de Conocimiento.", "success")
        else:
             flash("Se usará el contenido actual de la carpeta BaseConocimiento.", "info")

    if not use_existing_project_file_checkbox:
        if project_file_uploaded and project_file_uploaded.filename != '' and allowed_file(project_file_uploaded.filename):
            clear_directory(config.DIRECTORIO_PROYECTO_ANALIZAR)
            filename = secure_filename(project_file_uploaded.filename)
            project_file_uploaded.save(os.path.join(config.DIRECTORIO_PROYECTO_ANALIZAR, filename))
            flash(f"Archivo de proyecto '{filename}' guardado.", "success")
        else:
            flash("Debe subir un archivo de proyecto si no utiliza el existente.", "error")
            return redirect(url_for('home'))

    try:
        app.logger.info(f"Llamando a run_analysis() con modelo='{selected_llm_model_id}'")

        dashboard_relative_path = run_analysis(
            selected_llm_model_id=selected_llm_model_id,
            force_recreate_db=recreate_db_for_this_run
        )

        if not dashboard_relative_path:
            flash("El proceso de análisis no generó un dashboard. Revisa los logs.", "info")
            return redirect(url_for('home'))

        dashboard_absolute_path = os.path.join(PROJECT_ROOT, dashboard_relative_path)
        if not os.path.exists(dashboard_absolute_path):
            app.logger.error(f"Dashboard no encontrado en ruta: '{dashboard_absolute_path}'.")
            flash("Error: Análisis completado, pero no se encontró el dashboard HTML.", "error")
            return redirect(url_for('home'))

        return send_file(dashboard_absolute_path)

    except (ValidationError, TypeError) as e_val:
        app.logger.error(f"Error de validación o tipo en la respuesta del LLM: {e_val}")
        flash(f"Error Crítico: La respuesta del LLM no cumplió con el formato esperado. Detalles: {e_val}", "error")
    except Exception as e:
        app.logger.error(f"Excepción inesperada en la ruta /analyze: {e}", exc_info=True)
        flash(f"Ocurrió un error interno inesperado en el servidor: {str(e)}", "error")

    return redirect(url_for('home'))

if __name__ == '__main__':
    app.logger.info("Iniciando servidor Flask de desarrollo...")
    port = int(os.environ.get("PORT", 8080))
    # --- CAMBIO REALIZADO: Añadido use_reloader=False ---
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)