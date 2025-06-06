# scripts/schemas.py
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# Definimos los tipos literales para restringir los valores que puede devolver el LLM.
# Esto es mucho más robusto que un simple string.
ImpactoEstimado = Literal["Bajo", "Medio", "Alto"]
ProbabilidadEstimada = Literal["Baja", "Media", "Alta"]

class SourceChunk(BaseModel):
    """
    Representa un fragmento de la base de conocimiento que fue recuperado como evidencia.
    """
    contenido: str = Field(description="El contenido textual exacto del fragmento recuperado.")
    nombre_documento_fuente: str = Field(description="El nombre del archivo PDF de donde proviene el fragmento.")
    numero_pagina: int = Field(description="El número de página dentro del documento fuente.")
    score_relevancia: Optional[float] = Field(
        default=None,
        description="Puntuación de relevancia asignada por el re-ranker (entre 0 y 1). Será None si no se usa re-ranking."
    )

class RiskItem(BaseModel):
    """
    Representa un único riesgo identificado con todos sus atributos.
    """
    descripcion_riesgo: str = Field(description="Descripción clara y concisa del riesgo identificado.")
    impacto_estimado: ImpactoEstimado = Field(description="Impacto potencial del riesgo. Debe ser 'Bajo', 'Medio' o 'Alto'.")
    probabilidad_estimada: ProbabilidadEstimada = Field(description="Probabilidad de ocurrencia del riesgo. Debe ser 'Baja', 'Media' o 'Alta'.")
    responsabilidad_mitigacion: str = Field(description="Rol o departamento responsable de las tareas de mitigación preventivas antes de que ocurra el riesgo.")
    responsable_accidente: str = Field(description="Rol o departamento que asumiría la responsabilidad principal si el riesgo se materializa.")
    explicacion_riesgo: str = Field(description="Breve explicación de por qué esto es un riesgo, citando evidencia del contexto proporcionado.")

class RiskReport(BaseModel):
    """
    El objeto principal que representa el informe completo de análisis de riesgos.
    Esta es la estructura que el LLM debe generar.
    """
    configuracion_analisis: dict = Field(
        description="Metadatos sobre la configuración utilizada para este análisis, como el modelo LLM usado.",
        default_factory=dict
    )
    riesgos_identificados: List[RiskItem] = Field(
        description="Una lista de todos los riesgos identificados en el análisis. Si no se identifican riesgos, esta lista debe estar vacía."
    )
    fragmentos_fuente: List[SourceChunk] = Field(
        description="Una lista de los fragmentos de la base de conocimiento utilizados como contexto para generar la respuesta.",
        default_factory=list
    )
    # Metadatos adicionales que llenaremos después de la respuesta del LLM
    nombre_proyecto_analizado: Optional[str] = None
    timestamp_analisis: Optional[str] = None
    respuesta_cruda_llm: Optional[str] = None

if __name__ == '__main__':
    # Esto es solo para verificar que los modelos funcionan como se espera
    print("Módulo de esquemas Pydantic cargado correctamente.")
    try:
        ejemplo_riesgo = {
            "descripcion_riesgo": "Fallo eléctrico en la nueva maquinaria.",
            "impacto_estimado": "Alto",
            "probabilidad_estimada": "Media",
            "responsabilidad_mitigacion": "Equipo de Mantenimiento Eléctrico",
            "responsable_accidente": "Jefe de Producción",
            "explicacion_riesgo": "Basado en el manual técnico que indica una alta demanda de energía."
        }
        item = RiskItem(**ejemplo_riesgo)
        print("\nEjemplo de RiskItem validado:")
        print(item.model_dump_json(indent=2))

        # Ejemplo de validación fallida
        ejemplo_fallido = {**ejemplo_riesgo, "impacto_estimado": "Muy Alto"} # Valor no permitido
        RiskItem(**ejemplo_fallido)

    except Exception as e:
        print(f"\nSe detectó un error de validación esperado:")
        print(e)