# D:\tesismma\app.py
import os
import sys
import logging
import traceback
import datetime
from flask import Flask, render_template_string, send_file, url_for, redirect, flash, request
from werkzeug.utils import secure_filename

# --- Configuración de Rutas para Importar Módulos del Proyecto ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Importar la función de análisis y configuración ---
try:
    from scripts.main import run_analysis
    from scripts import config
except ImportError as e:
    logging.basicConfig(level=logging.ERROR)
    logging.error(f"Error crítico al importar módulos necesarios (main, config): {e}")
    run_analysis = None
    config = None

# --- Creación de la Aplicación Flask ---
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# --- Configuraciones para Carga de Archivos ---
ALLOWED_EXTENSIONS = {'pdf'}
MAX_KB_FILES = 4
MAX_KB_TOTAL_SIZE_MB = 8 * 1024 * 1024
MAX_PROJECT_FILE_SIZE_MB = 2 * 1024 * 1024

# --- Configuración del Logging de Flask ---
if not app.debug:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers.extend(gunicorn_logger.handlers)
    app.logger.setLevel(logging.INFO)
else:
    app.logger.setLevel(logging.INFO)

# --- Información del Proyecto para la Plantilla (usada en el footer) ---
if config and hasattr(config, 'INFO_TESIS'):
    FOOTER_INFO = {
        "institucion_line1": config.INFO_TESIS.get("institucion_line1", "ITBA - Instituto Tecnológico Buenos Aires"),
        "institucion_line2": config.INFO_TESIS.get("institucion_line2", "Maestría en Management & Analytics"),
        "github_repo_url": "https://github.com/Adrielcuesta/tesismma"
    }
else:
    FOOTER_INFO = {
        "institucion_line1": "ITBA - Instituto Tecnológico Buenos Aires",
        "institucion_line2": "Maestría en Management & Analytics",
        "github_repo_url": "https://github.com/Adrielcuesta/tesismma"
    }

CURRENT_YEAR = datetime.datetime.now().year

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clear_directory(directory_path):
    if not os.path.isdir(directory_path):
        app.logger.error(f"Intento de limpiar un directorio que no existe: {directory_path}")
        return
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
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f0f2f5;
            color: #333; 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            min-height: 95vh; 
        }
        .main-container { 
            background-color: #ffffff; 
            padding: 30px 40px; 
            border-radius: 12px; 
            box-shadow: 0 6px 20px rgba(0,0,0,0.1); 
            width: 100%; 
            max-width: 1000px; 
            text-align: left; 
            margin-bottom: auto; 
        }
        
        .abstract-banner-container { 
            width: 100%; 
            height: 251px; /* Altura de tu nueva imagen del banner */
            margin: 0 auto 25px auto; 
            background-image: url("{{ url_for('static', filename='images/header_banner_abstract.png') }}"); /* Asegúrate que este sea el nombre correcto de tu banner */
            background-size: cover; 
            background-position: center;
            border-radius: 6px;
        }
        .header-content {
            text-align: center;
            margin-bottom: 30px;
        }
        .title-with-logo {
            display: flex;
            align-items: center; 
            justify-content: center; 
            gap: 10px; 
            margin-bottom: 8px; 
        }
        .title-with-logo img.logo-inline { /* Logo al lado de TESIS FIN DE MAESTRIA */
            height: 30px; 
            width: auto; 
        }
        .header-content h1 {
            color: #1a2533;
            font-size: 1.7em; 
            margin: 0; 
            font-weight: 600;
        }
        .header-content h2 {
            color: #2c3e50;
            font-size: 1.3em;
            margin-top: 8px;
            margin-bottom: 5px;
            font-weight: 500;
        }
        .header-content h3 {
            color: #4a5568;
            font-size: 1.1em;
            margin-bottom: 10px;
            font-weight: 400;
        }
        .header-content p.student-name {
            color: #333;
            font-size: 1.1em;
            font-weight: bold;
            margin-top: 15px;
        }

        .upload-sections-container {
            display: flex;
            justify-content: space-between;
            gap: 30px;
            margin-bottom: 30px;
        }
        .form-section { 
            flex: 1; 
            padding: 20px; 
            border: 1px solid #e0e0e0; 
            border-radius: 8px; 
            background-color: #f8f9fa; /* Color más sutil para las secciones de carga */
        }
        .form-section h4 {
            margin-top: 0; 
            color: #212529; 
            font-size: 1.2em; 
            border-bottom: 1px solid #e9ecef; 
            padding-bottom: 8px;
            margin-bottom: 15px;
        }
        .form-section h4 .emoji {
            margin-right: 8px;
            font-size: 1.1em;
        }
        label { display: block; margin-bottom: 8px; font-weight: 600; font-size: 0.95em; color: #343a40;}
        input[type="file"], input[type="checkbox"] { margin-bottom: 10px; }
        input[type="file"] { width: 100%; }
        input[type="file"]:disabled { background-color: #e9ecef; cursor: not-allowed; } 
        .checkbox-label { display: inline !important; font-weight: normal !important; font-size:0.9em !important; margin-left: 5px; color: #495057;}

        .button-container { text-align: center; margin-top: 10px; }
        /* --- ESTILOS DEL BOTÓN RESTAURADOS --- */
        .button {
            display: inline-block; background-color: #007bff; color: white; padding: 14px 35px;
            border: none; border-radius: 5px; cursor: pointer; font-size: 1.1em;
            text-decoration: none; transition: background-color 0.3s ease; font-weight: 500;
        }
        .button:hover { background-color: #0056b3; }
        .button-disabled { background-color: #cccccc; cursor: not-allowed; } /* Añadido de una versión anterior para consistencia */
        /* --- FIN ESTILOS DEL BOTÓN --- */
        
        .loader { border: 5px solid #f3f3f3; border-top: 5px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 30px auto 0 auto; display: none; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .flash-messages { list-style-type: none; padding: 0; margin: 20px 0; }
        .flash-messages li { padding: 12px 15px; margin-bottom: 10px; border-radius: 5px; font-size: 0.95em;}
        .flash-messages .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .flash-messages .info { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .flash-messages .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        
        /* --- ESTILOS DEL FOOTER RESTAURADOS/VERIFICADOS --- */
        .footer { 
            width: 100%; 
            text-align: center; /* CLAVE PARA CENTRAR EL CONTENIDO */
            padding: 25px 0; 
            font-size: 0.9em; 
            color: #6c757d; 
            margin-top:40px; 
            border-top: 1px solid #dee2e6; 
        }
        .footer p { 
            margin: 5px 0; 
            /* text-align: center; Ya heredado del padre .footer */
        }
        .footer img.logo-itba-footer { /* El logo ITBA institucional del footer */
            max-height: 45px; 
            margin-bottom: 10px;
            opacity: 0.9;
            /* Los <img> son inline por defecto, text-align:center del padre los centra */
        }
        .footer a { color: #007bff; text-decoration: none; }
        .footer a:hover { text-decoration: underline; }
        /* --- FIN ESTILOS DEL FOOTER --- */

        @media (max-width: 768px) { 
            .upload-sections-container { flex-direction: column; }
            .main-container { padding: 20px; }
            .header-content h1 { font-size: 1.5em; }
            .title-with-logo img.logo-inline { height: 25px; } 
            .abstract-banner-container { height: 180px; } 
        }
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
            <div class="upload-sections-container">
                <div class="form-section">
                    <h4><span class="emoji">📚</span>Base de Conocimiento</h4>
                    <div>
                        <input type="checkbox" id="use_default_kb_input" name="use_default_kb" value="yes" checked>
                        <label for="use_default_kb_input" class="checkbox-label">Usar Base de Conocimiento por defecto.</label>
                    </div>
                    <label for="kb_files_input" style="margin-top:15px;">Subir PDFs para nueva Base de Conocimiento (hasta """+str(MAX_KB_FILES)+""" archivos, total max. """+str(MAX_KB_TOTAL_SIZE_MB // (1024*1024))+"""MB):</label>
                    <input type="file" id="kb_files_input" name="kb_files" multiple accept=".pdf">
                </div>

                <div class="form-section">
                    <h4><span class="emoji">📄</span>Proyecto a Analizar</h4>
                    <label for="project_file_input">Subir PDF del Proyecto a Analizar (1 archivo, max. """+str(MAX_PROJECT_FILE_SIZE_MB // (1024*1024))+"""MB):</label>
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

        function toggleKbFileInput() {
            if (useDefaultKbCheckbox.checked) {
                kbFilesInput.disabled = true;
                kbFilesInput.value = null; 
            } else {
                kbFilesInput.disabled = false;
            }
        }
        toggleKbFileInput(); 
        useDefaultKbCheckbox.addEventListener('change', toggleKbFileInput);

        document.getElementById('analysisForm').addEventListener('submit', function(event) {
            let valid = true;
            if (!useDefaultKbCheckbox.checked && kbFilesInput.files.length > 0) { 
                if (kbFilesInput.files.length > """+str(MAX_KB_FILES)+""") {
                    alert('Puede subir un máximo de """+str(MAX_KB_FILES)+""" archivos para la base de conocimiento.');
                    valid = false;
                }
                let totalKbSize = 0;
                for (let i = 0; i < kbFilesInput.files.length; i++) {
                    totalKbSize += kbFilesInput.files[i].size;
                    if (!kbFilesInput.files[i].name.toLowerCase().endsWith('.pdf')) {
                        alert('Todos los archivos de la base de conocimiento deben ser PDF.');
                        valid = false; break;
                    }
                }
                if (totalKbSize > """+str(MAX_KB_TOTAL_SIZE_MB)+""") {
                    alert('El tamaño total de los archivos de la base de conocimiento no debe exceder """+str(MAX_KB_TOTAL_SIZE_MB // (1024*1024))+"""MB.');
                    valid = false;
                }
            }
            const projectFileInput = document.getElementById('project_file_input');
            if (projectFileInput.files.length > 0) {
                if (projectFileInput.files[0].size > """+str(MAX_PROJECT_FILE_SIZE_MB)+""") {
                    alert('El archivo del proyecto no debe exceder """+str(MAX_PROJECT_FILE_SIZE_MB // (1024*1024))+"""MB.');
                    valid = false;
                }
                if (!projectFileInput.files[0].name.toLowerCase().endsWith('.pdf')) {
                    alert('El archivo del proyecto debe ser PDF.');
                    valid = false;
                }
            }
            if (!valid) {
                event.preventDefault();
                return;
            }
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
    return render_template_string(HOME_PAGE_HTML, 
                                  footer_info=FOOTER_INFO, 
                                  MAX_KB_FILES=MAX_KB_FILES, 
                                  MAX_KB_TOTAL_SIZE_MB=MAX_KB_TOTAL_SIZE_MB, 
                                  MAX_PROJECT_FILE_SIZE_MB=MAX_PROJECT_FILE_SIZE_MB,
                                  CURRENT_YEAR=CURRENT_YEAR)

@app.route('/analyze', methods=['POST'])
def analyze_route():
    app.logger.info("Solicitud POST a /analyze recibida.")

    if run_analysis is None or config is None:
        app.logger.error("Intento de análisis, pero run_analysis/config no están disponibles.")
        flash("Error del servidor: La función de análisis o configuración no está cargada.", "error")
        return redirect(url_for('home'))

    recreate_db_for_this_run = False 
    use_default_kb_checkbox = request.form.get('use_default_kb') == 'yes'
    
    kb_files_uploaded = request.files.getlist('kb_files')
    project_file_uploaded = request.files.get('project_file')

    if not use_default_kb_checkbox:
        actual_kb_files_to_save = [f for f in kb_files_uploaded if f and f.filename != '' and allowed_file(f.filename)]
        if actual_kb_files_to_save: 
            app.logger.info("Nuevos archivos de KB subidos y 'Usar por defecto' NO está marcado. Se procesarán estos archivos.")
            if len(actual_kb_files_to_save) > MAX_KB_FILES:
                flash(f"Puede subir un máximo de {MAX_KB_FILES} archivos para la base de conocimiento.", "error")
                return redirect(url_for('home'))
            
            total_kb_size = sum(f.content_length for f in actual_kb_files_to_save)
            if total_kb_size > MAX_KB_TOTAL_SIZE_MB:
                flash(f"El tamaño total de los archivos de la base de conocimiento no debe exceder {MAX_KB_TOTAL_SIZE_MB // (1024*1024)}MB.", "error")
                return redirect(url_for('home'))

            clear_directory(config.DIRECTORIO_BASE_CONOCIMIENTO)
            for file in actual_kb_files_to_save:
                filename = secure_filename(file.filename)
                file.save(os.path.join(config.DIRECTORIO_BASE_CONOCIMIENTO, filename))
            recreate_db_for_this_run = True
            flash(f"{len(actual_kb_files_to_save)} archivo(s) de base de conocimiento guardado(s). La base de datos se recreará.", "success")
        else: 
            app.logger.info("No se subieron nuevos archivos de KB, y 'Usar por defecto' NO está marcado. Se intentará recrear la DB con el contenido actual de la carpeta BaseConocimiento.")
            recreate_db_for_this_run = True 
    else: 
        app.logger.info("'Usar por defecto' ESTÁ marcado. Se usará la DB existente. Los archivos de KB subidos (si los hay) serán ignorados.")
        if any(f for f in kb_files_uploaded if f and f.filename != ''):
             flash("Se seleccionaron archivos para la base de conocimiento, pero como 'Usar por defecto' está marcado, estos archivos no se procesarán y se usará la base de datos existente.", "info")
        recreate_db_for_this_run = False

    project_file_saved_for_analysis = False
    if project_file_uploaded and project_file_uploaded.filename != '':
        if allowed_file(project_file_uploaded.filename):
            if project_file_uploaded.content_length > MAX_PROJECT_FILE_SIZE_MB:
                flash(f"El archivo del proyecto no debe exceder {MAX_PROJECT_FILE_SIZE_MB // (1024*1024)}MB.", "error")
                return redirect(url_for('home'))
            
            clear_directory(config.DIRECTORIO_PROYECTO_ANALIZAR)
            filename = secure_filename(project_file_uploaded.filename)
            project_file_path = os.path.join(config.DIRECTORIO_PROYECTO_ANALIZAR, filename)
            project_file_uploaded.save(project_file_path)
            app.logger.info(f"Archivo de proyecto '{filename}' guardado.")
            flash(f"Archivo de proyecto '{filename}' guardado.", "success")
            project_file_saved_for_analysis = True
        else:
            flash("Tipo de archivo no permitido para el proyecto. Solo PDF.", "error")
            return redirect(url_for('home'))
    
    try:
        project_pdfs = [f for f in os.listdir(config.DIRECTORIO_PROYECTO_ANALIZAR) if f.lower().endswith(".pdf")]
        if not project_pdfs:
            flash("No se subió un archivo de proyecto y no se encontró ninguno en el servidor. Por favor, suba un PDF para analizar.", "error")
            return redirect(url_for('home'))
        if len(project_pdfs) > 1 and not project_file_saved_for_analysis:
             flash("Hay múltiples archivos de proyecto en el servidor y no se subió uno nuevo para especificar. Limpie el directorio 'ProyectoAnalizar'.", "error")
             return redirect(url_for('home'))
        app.logger.info(f"Se usará el archivo de proyecto: {project_pdfs[0]}")
    except FileNotFoundError:
        flash("Directorio de proyecto no encontrado. Error de configuración.", "error")
        return redirect(url_for('home'))
    except Exception as e:
        app.logger.error(f"Error al verificar archivo de proyecto: {e}")
        flash("Error al verificar el archivo de proyecto en el servidor.", "error")
        return redirect(url_for('home'))

    try:
        app.logger.info(f"Llamando a scripts.main.run_analysis() con force_recreate_db={recreate_db_for_this_run}...")
        dashboard_relative_path = run_analysis(force_recreate_db=recreate_db_for_this_run)
        app.logger.info(f"run_analysis() completado. Ruta dashboard: {dashboard_relative_path}")

        if dashboard_relative_path:
            dashboard_absolute_path = os.path.join(PROJECT_ROOT, dashboard_relative_path)
            if os.path.exists(dashboard_absolute_path):
                return send_file(dashboard_absolute_path)
            else:
                app.logger.error(f"Dashboard no encontrado en ruta absoluta: '{dashboard_absolute_path}'.")
                flash(f"Error: Análisis completado, pero no se encontró el dashboard.", "error")
        else:
            flash("El proceso de análisis no generó un dashboard o falló. Revisa los logs del servidor para más detalles.", "info")
    
    except Exception as e:
        app.logger.error(f"Excepción inesperada en la ruta /analyze: {e}")
        app.logger.error(traceback.format_exc())
        flash(f"Ocurrió un error interno inesperado en el servidor: {str(e)}", "error")
    
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.logger.info("Iniciando servidor Flask de desarrollo...")
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host='0.0.0.0', port=port)