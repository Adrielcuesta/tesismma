# Etapa 1: Constructor (Builder) - Para instalar dependencias y mantener la imagen final ligera
FROM python:3.12-slim-bookworm AS builder

# Establecer variables de entorno recomendadas para Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establecer el directorio de trabajo para esta etapa
WORKDIR /opt/venv

# Instalar dependencias del sistema operativo si son necesarias.
# Descomenta y adapta estas líneas si la instalación de pip para pymupdf o onnxruntime falla,
# o si encuentras errores de bibliotecas faltantes en tiempo de ejecución.
# RUN apt-get update && apt-get install -y --no-install-recommends \
#    # Para PyMuPDF (si las wheels no son suficientes):
#    # libmupdf-dev \
#    # libmupdf-tools \
#    # Para ONNXRuntime (si las wheels no son suficientes):
#    # libgomp1 \ 
#    && rm -rf /var/lib/apt/lists/*

# Crear un entorno virtual dentro de la imagen de construcción
RUN python -m venv .

# Copiar el archivo de requisitos
COPY requirements.txt .

# Activar el entorno virtual e instalar las dependencias de Python
# Usar --no-cache-dir para reducir el tamaño de la capa
RUN . bin/activate && pip install --no-cache-dir -r requirements.txt


# Etapa 2: Imagen Final de Producción
FROM python:3.12-slim-bookworm AS final

# Establecer el directorio de trabajo para la aplicación
WORKDIR /app

# Crear un usuario y grupo no root para ejecutar la aplicación por seguridad [cite: 20, 25]
# ARG UID=10001 # Puedes definir un UID específico si es necesario
RUN adduser --system --group app_user # Crea app_user y su grupo app_user
# RUN adduser --system --uid ${UID} app_user # Alternativa si quieres un UID específico

# Copiar el entorno virtual con las dependencias instaladas desde la etapa de construcción
COPY --from=builder /opt/venv /opt/venv

# Copiar todo el código de la aplicación al directorio de trabajo /app
# Establecer la propiedad de los archivos copiados al usuario app_user
# Esto requiere BuildKit (habilitado por defecto en Docker más recientes)
COPY --chown=app_user:app_user . /app/

# La lógica en config.py (inicializar_directorios_datos) crea las carpetas 
# datos/ChromaDB_V1 y datos/Resultados. 
# Como /app ahora es propiedad de app_user, la aplicación tendrá permisos para escribir allí.

# Cambiar al usuario no root
USER app_user

# Añadir el directorio bin del entorno virtual al PATH
# Esto permite ejecutar gunicorn directamente.
ENV PATH="/opt/venv/bin:$PATH"

# Exponer el puerto en el que la aplicación escuchará.
# Cloud Run pasará la variable de entorno PORT, comúnmente 8080. [cite: 43]
EXPOSE 8080

# Comando para ejecutar la aplicación Flask usando Gunicorn.
# "app:app" se refiere al archivo app.py y a la instancia de Flask llamada 'app' dentro de ese archivo.
# Gunicorn escuchará en todas las interfaces (0.0.0.0) en el puerto especificado por $PORT.
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]