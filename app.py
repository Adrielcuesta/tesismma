# D:\tesismma\app.py
import os
import sys
import logging
import traceback # Para un logging de errores más detallado
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
MAX_KB_TOTAL_SIZE_MB = 8 * 1024 * 1024  # 8 MB
MAX_PROJECT_FILE_SIZE_MB = 2 * 1024 * 1024 # 2 MB

# --- Configuración del Logging de Flask ---
if not app.debug:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers.extend(gunicorn_logger.handlers)
    app.logger.setLevel(logging.INFO)
else:
    app.logger.setLevel(logging.INFO)

# --- Información del Proyecto para la Plantilla ---
if config and hasattr(config, 'INFO_TESIS'):
    PROJECT_INFO = config.INFO_TESIS
else:
    PROJECT_INFO = {
        "titulo_tesis": "Sistema RAG para Análisis de Riesgos (Título por Defecto)",
        "institucion_line1": "ITBA (Info por Defecto)",
        "institucion_line2": "Maestría (Info por Defecto)",
        "alumno": "Adriel Cuesta (Info por Defecto)",
        "github_repo_url": "https://github.com/Adrielcuesta/tesismma",
        "project_title": "Análisis de Riesgos en Instalación de Maquinaria Industrial"
    }

# --- Funciones Auxiliares para Carga de Archivos ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clear_directory(directory_path):
    """Elimina todos los archivos dentro de un directorio."""
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

# --- Plantilla HTML para la Página de Inicio ---
HOME_PAGE_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ project_info.get('project_title', 'Análisis de Riesgos') }}</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; display: flex; flex-direction: column; align-items: center; min-height: 95vh; }
        .container { background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100%; max-width: 800px; text-align: left; margin-bottom: auto; }
        h1 { color: #1a2533; margin-bottom: 10px; font-size: 2em; text-align: center;}
        h2 { color: #4a5568; font-weight: 400; font-size: 1.2em; margin-top: 0; margin-bottom: 20px; text-align: center;}
        p { line-height: 1.6; margin-bottom: 15px; }
        .form-section { margin-bottom: 25px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 5px; }
        .form-section h3 { margin-top: 0; color: #333; font-size: 1.1em; }
        label { display: block; margin-bottom: 8px; font-weight: 600; }
        input[type="file"], input[type="checkbox"] { margin-bottom: 10px; }
        input[type="file"]:disabled { background-color: #e9ecef; cursor: not-allowed; }
        .button-container { text-align: center; }
        .button {
            display: inline-block; background-color: #007bff; color: white; padding: 12px 25px;
            border: none; border-radius: 5px; cursor: pointer; font-size: 18px;
            text-decoration: none; transition: background-color 0.3s ease;
        }
        .button:hover { background-color: #0056b3; }
        .button-disabled { background-color: #cccccc; cursor: not-allowed; }
        .loader {
            border: 5px solid #f3f3f3; border-top: 5px solid #3498db;
            border-radius: 50%; width: 40px; height: 40px;
            animation: spin 1s linear infinite; margin: 30px auto 0 auto; display: none;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .flash-messages { list-style-type: none; padding: 0; margin-bottom: 20px; }
        .flash-messages li { padding: 10px; margin-bottom: 10px; border-radius: 4px; }
        .flash-messages .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .flash-messages .info { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .flash-messages .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .footer { width: 100%; text-align: center; padding: 20px 0; font-size: 0.9em; color: #777; margin-top:30px;}
        .footer p { margin: 5px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ project_info.get('project_title', 'Análisis de Riesgos con RAG') }}</h1>
        <h2>{{ project_info.get('titulo_tesis', 'Trabajo Final de Maestría') }}</h2>
        <p style="text-align:center;"><strong>Estudiante:</strong> {{ project_info.get('alumno', 'Adriel Cuesta') }}</p>
        <p style="text-align:center;">Este sistema utiliza Generación Aumentada por Recuperación (RAG) para analizar riesgos en la instalación de maquinaria industrial.</p>
        
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
            <div class="form-section">
                <h3>Base de Conocimiento</h3>
                <div>
                    <input type="checkbox" id="use_default_kb_input" name="use_default_kb" value="yes" checked>
                    <label for="use_default_kb_input" style="display: inline; font-weight: normal;">Usar Base de Conocimiento por defecto (si está tildado, se usará la base guardada y se ignorará la subida de archivos abajo).</label>
                </div>
                <label for="kb_files_input" style="margin-top:10px;">Subir PDFs para nueva Base de Conocimiento (hasta """+str(MAX_KB_FILES)+""" archivos, total max. """+str(MAX_KB_TOTAL_SIZE_MB // (1024*1024))+"""MB):</label>
                <input type="file" id="kb_files_input" name="kb_files" multiple accept=".pdf">
            </div>

            <div class="form-section">
                <h3>Proyecto a Analizar</h3>
                <label for="project_file_input">Subir PDF del Proyecto a Analizar (1 archivo, max. """+str(MAX_PROJECT_FILE_SIZE_MB // (1024*1024))+"""MB):</label>
                <input type="file" id="project_file_input" name="project_file" accept=".pdf">
            </div>
            
            <div class="button-container">
                <button type="submit" id="analyzeButton" class="button">Iniciar Análisis</button>
            </div>
        </form>
        <div id="loader" class="loader"></div>
    </div>

    <div class="footer">
        <p>{{ project_info.get('institucion_line1', 'ITBA') }} - {{ project_info.get('institucion_line2', 'Maestría') }}</p>
        <p><a href="{{ project_info.get('github_repo_url', '#') }}" target="_blank">Ver Repositorio en GitHub</a></p>
    </div>

    <script>
        const useDefaultKbCheckbox = document.getElementById('use_default_kb_input');
        const kbFilesInput = document.getElementById('kb_files_input');

        function toggleKbFileInput() {
            if (useDefaultKbCheckbox.checked) {
                kbFilesInput.disabled = true;
                kbFilesInput.value = null; // Limpiar archivos seleccionados si se deshabilita
            } else {
                kbFilesInput.disabled = false;
            }
        }

        // Estado inicial al cargar la página
        toggleKbFileInput();
        useDefaultKbCheckbox.addEventListener('change', toggleKbFileInput);

        // Script para el loader y deshabilitar botón
        document.getElementById('analysisForm').addEventListener('submit', function(event) {
            let valid = true;
            // Validaciones de archivos (pueden ser más exhaustivas)
            if (!useDefaultKbCheckbox.checked && kbFilesInput.files.length > 0) { // Solo validar si el input está activo y tiene archivos
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
            // No se requiere que el project_file sea siempre subido si ya existe uno en el servidor.
            // La lógica del servidor verificará si existe uno si no se sube.

            if (!valid) {
                event.preventDefault(); // Detener envío del formulario
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
    # Pasar las constantes al template para que el JS las pueda usar dinámicamente si se prefiere.
    return render_template_string(HOME_PAGE_HTML, project_info=PROJECT_INFO, 
                                  MAX_KB_FILES=MAX_KB_FILES, 
                                  MAX_KB_TOTAL_SIZE_MB=MAX_KB_TOTAL_SIZE_MB, 
                                  MAX_PROJECT_FILE_SIZE_MB=MAX_PROJECT_FILE_SIZE_MB)

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

    # --- Manejo de Archivos de Base de Conocimiento (KB) ---
    # Procesar archivos de KB solo si la casilla "Usar por defecto" NO está marcada Y se subieron archivos
    if not use_default_kb_checkbox:
        actual_kb_files_to_save = [f for f in kb_files_uploaded if f and f.filename != '' and allowed_file(f.filename)]
        if actual_kb_files_to_save: # Si hay archivos válidos para guardar
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
        else: # No se subieron archivos de KB pero la casilla "Usar por defecto" NO está marcada
            app.logger.info("No se subieron nuevos archivos de KB, y 'Usar por defecto' NO está marcado. Se intentará recrear la DB con el contenido actual de la carpeta BaseConocimiento (si existe).")
            recreate_db_for_this_run = True 
            # Si la carpeta BaseConocimiento está vacía, se creará una DB vacía. Esto es un comportamiento a considerar.
            # Podríamos añadir un flash info aquí si es relevante.
    else: # "Usar por defecto" ESTÁ MARCADO
        app.logger.info("'Usar por defecto' ESTÁ marcado. Se usará la DB existente. Los archivos de KB subidos (si los hay) serán ignorados para la creación de la DB.")
        if any(f for f in kb_files_uploaded if f and f.filename != ''): # Si se intentó subir archivos
             flash("Se seleccionaron archivos para la base de conocimiento, pero como 'Usar por defecto' está marcado, estos archivos no se procesarán y se usará la base de datos existente.", "info")
        recreate_db_for_this_run = False


    # --- Manejo del Archivo de Proyecto a Analizar ---
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
    
    # Verificar si hay un archivo de proyecto para analizar (ya sea recién subido o existente)
    try:
        project_pdfs = [f for f in os.listdir(config.DIRECTORIO_PROYECTO_ANALIZAR) if f.lower().endswith(".pdf")]
        if not project_pdfs:
            flash("No se subió un archivo de proyecto y no se encontró ninguno en el servidor. Por favor, suba un PDF para analizar.", "error")
            return redirect(url_for('home'))
        if len(project_pdfs) > 1 and not project_file_saved_for_analysis: # Si hay muchos y no acabamos de subir uno que limpió el dir
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

    # --- Ejecutar Análisis ---
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
            # Si run_analysis devuelve None, es probable que haya logueado el error específico.
            # main.py podría devolver None si hay un error fatal (API key, no se pudo crear DB, etc.)
            # o si, por ejemplo, no se encontró el PDF del proyecto a analizar (lo cual ahora app.py debería prevenir mejor).
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