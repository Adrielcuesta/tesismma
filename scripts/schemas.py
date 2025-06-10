# scripts/schemas.py
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

ImpactoEstimado = Literal["Bajo", "Medio", "Alto"]
ProbabilidadEstimada = Literal["Baja", "Media", "Alta"]
# --- NUEVO: Tipo de Riesgo ---
TipoDeRiesgo = Literal["Explícito", "Implícito"]

class SourceChunk(BaseModel):
    """Representa un fragmento de la base de conocimiento que fue recuperado como evidencia."""
    contenido: str = Field(description="El contenido textual exacto del fragmento recuperado.")
    nombre_documento_fuente: str = Field(description="El nombre del archivo PDF de donde proviene el fragmento.")
    numero_pagina: int = Field(description="El número de página dentro del documento fuente.")
    score_relevancia: Optional[float] = Field(default=None, description="Puntuación de relevancia asignada por el re-ranker (0 a 1).")

class RiskItem(BaseModel):
    """Representa un único riesgo identificado con todos sus atributos."""
    descripcion_riesgo: str = Field(description="Descripción clara y concisa del riesgo identificado.")
    # --- CAMBIO: Añadido tipo_de_riesgo ---
    tipo_de_riesgo: TipoDeRiesgo = Field(description="Clasificación del riesgo como 'Explícito' (directamente mencionado) o 'Implícito' (deducido lógicamente).")
    impacto_estimado: ImpactoEstimado = Field(description="Impacto potencial del riesgo. Debe ser 'Bajo', 'Medio' o 'Alto'.")
    probabilidad_estimada: ProbabilidadEstimada = Field(description="Probabilidad de ocurrencia del riesgo. Debe ser 'Baja', 'Media', o 'Alta'.")
    responsabilidad_mitigacion: str = Field(description="Rol o departamento responsable de las tareas de mitigación preventivas.")
    responsable_accidente: str = Field(description="Rol o departamento que asumiría la responsabilidad principal si el riesgo se materializa.")
    explicacion_riesgo: str = Field(description="Breve explicación de por qué esto es un riesgo, citando evidencia del contexto.")
    score_confianza_compuesto: Optional[float] = Field(default=None, description="Confianza calculada para el riesgo, combinando la relevancia de la evidencia con la severidad del riesgo (0 a 1).")

class LLMResponse(BaseModel):
    """Define la estructura de datos que se espera directamente del LLM."""
    riesgos_identificados: List[RiskItem] = Field(description="Una lista de todos los riesgos identificados.")

class RiskReport(BaseModel):
    """El objeto principal que representa el informe completo de análisis de riesgos."""
    configuracion_analisis: dict = Field(default_factory=dict)
    riesgos_identificados: List[RiskItem] = Field(description="Una lista de todos los riesgos identificados en el análisis.")
    fragmentos_fuente: List[SourceChunk] = Field(default_factory=list)
    nombre_proyecto_analizado: Optional[str] = None
    timestamp_analisis: Optional[str] = None
    respuesta_cruda_llm: Optional[str] = None