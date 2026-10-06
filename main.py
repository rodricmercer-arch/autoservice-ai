#!/usr/bin/env python3
"""Fase 4: microservicio FastAPI que une Prolog, Scala y Pandas.
Ejecutar desde la raiz:  uvicorn main:app --reload --port 8000
Swagger UI: http://localhost:8000/docs
"""
import json
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from prolog.ejecutar_diagnostico import consultar_prolog, parsear  # Fase 1 (sin modificar)
from python_analytics.analytics_engine import obtener_kpis_y_graficos  # Fase 3

ROOT = Path(__file__).resolve().parent
SCALA_FILE = ROOT / "scala" / "AutoServiceEngine.scala"
RUTA_CATALOGO = ROOT / "contracts" / "catalogo_sintomas.json"
RUTA_INPUT_COT = ROOT / "contracts" / "input_cotizacion.json"
DIR_REPORTES = ROOT / "reports"
TIMEOUT_SCALA_SEG = 240  # la 1ra ejecucion de scala-cli compila y puede tardar
_LOCK_SCALA = threading.Lock()  # evita compilaciones simultaneas en .scala-build


def _costo_hora_defecto() -> float:
    """Default tomado de contracts/input_cotizacion.json (fallback: 60.0)."""
    try:
        datos = json.loads(RUTA_INPUT_COT.read_text(encoding="utf-8"))
        return float(datos["costo_hora_mano_obra"])
    except Exception:
        return 60.0


COSTO_HORA_DEFECTO = _costo_hora_defecto()

# ============================================================
# Modelos Pydantic (nombres exactos de contracts/)
# ============================================================
Severidad = Literal["leve", "moderada", "urgente"]


class RepuestoCantidad(BaseModel):
    codigo: str = Field(..., min_length=1, examples=["REP-001"])
    cantidad: int = Field(..., gt=0, examples=[2])


class DiagnosticoIn(BaseModel):
    vehiculo_id: Optional[str] = None
    sintomas: List[str] = Field(..., min_length=1)

    model_config = {"json_schema_extra": {"example": {
        "vehiculo_id": "V-101", "sintomas": ["ruido_frenos", "pedal_esponjoso"]}}}


class FallaOut(BaseModel):
    codigo_falla: str
    descripcion: str
    severidad: Severidad
    repuestos_requeridos: List[RepuestoCantidad]
    horas_mano_obra: float


class DiagnosticoOut(BaseModel):
    vehiculo_id: Optional[str] = None
    sintomas_evaluados: List[str]
    fallas_detectadas: List[FallaOut]
    nivel_criticidad_global: Severidad
    repuestos_totales: List[RepuestoCantidad]  # extension aprobada (no esta en el contrato)


class CotizarIn(BaseModel):
    cotizacion_id: Optional[str] = None
    vehiculo_id: Optional[str] = None
    repuestos: List[RepuestoCantidad]
    horas_mano_obra: float = Field(..., ge=0)
    costo_hora_mano_obra: float = Field(COSTO_HORA_DEFECTO, ge=0)

    model_config = {"json_schema_extra": {"example": {
        "repuestos": [{"codigo": "REP-001", "cantidad": 2}, {"codigo": "REP-002", "cantidad": 1}],
        "horas_mano_obra": 2.5}}}


class DetalleRepuesto(BaseModel):
    codigo: str
    nombre: str
    precio_unitario: float
    cantidad: int
    subtotal: float


class ItemMasCostoso(BaseModel):
    nombre: str
    subtotal: float


class CotizacionOut(BaseModel):
    cotizacion_id: str
    vehiculo_id: str
    moneda: str
    detalles_repuestos: List[DetalleRepuesto]
    repuestos_no_encontrados: List[str]
    costo_mano_obra: float
    subtotal_general: float
    descuento_porcentaje: float
    descuento_aplicado: float
    base_imponible: float
    igv_porcentaje: float
    igv_impuesto: float
    total_neto: float
    item_mas_costoso: Optional[ItemMasCostoso] = None


class CategoriaResumen(BaseModel):
    categoria: str
    total_ingresos: float
    margen_pct: float
    promedio_horas: float
    varianza_horas: float
    desviacion_horas: float


class SedeTicket(BaseModel):
    sede: str
    ticket_promedio: float


class CalidadDatos(BaseModel):
    filas_descartadas: int
    nulos_imputados: int
    atipicos_ajustados: int


class KpisOut(BaseModel):
    total_ordenes_procesadas: int
    ingreso_total_acumulado: float
    margen_global_pct: float
    promedio_ticket_orden: float
    categoria_mayor_ingreso: str
    categoria_mayor_margen: str
    tiempo_promedio_reparacion_horas: float
    varianza_tiempo_horas: float
    desviacion_tiempo_horas: float
    satisfaccion_promedio: float
    correlacion_horas_satisfaccion: float
    resumen_por_categoria: List[CategoriaResumen]
    ticket_promedio_por_sede: List[SedeTicket]
    calidad_datos: CalidadDatos


class GraficosOut(BaseModel):
    ingresos_categoria: str
    eficiencia_tiempos: str


class AnaliticaOut(BaseModel):
    kpis: KpisOut
    graficos: GraficosOut


# ============================================================
# App, CORS y estaticos
# ============================================================
app = FastAPI(title="AutoService AI - API", version="1.0.0",
              description="Prolog (diagnostico) + Scala (cotizacion) + Pandas (analitica)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                   "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DIR_REPORTES.mkdir(parents=True, exist_ok=True)  # StaticFiles falla si la carpeta no existe
app.mount("/reports", StaticFiles(directory=DIR_REPORTES), name="reports")


# ============================================================
# a) POST /api/diagnostico
# ============================================================
@app.post("/api/diagnostico", response_model=DiagnosticoOut, tags=["Prolog"])
def diagnosticar(body: DiagnosticoIn):
    catalogo = {s["codigo"] for s in json.loads(RUTA_CATALOGO.read_text(encoding="utf-8"))}
    sintomas = list(dict.fromkeys(body.sintomas))
    invalidos = [s for s in sintomas if s not in catalogo]
    if invalidos:
        raise HTTPException(422, detail=f"Sintomas fuera del catalogo: {invalidos}")
    if shutil.which("swipl") is None:
        raise HTTPException(503, detail="No se encontro 'swipl' en el PATH del servidor.")

    try:  # los puentes de la Fase 1 usan sys.exit(); lo convertimos en error HTTP
        fallas, criticidad, _horas, repuestos_total = parsear(consultar_prolog(sintomas))
    except SystemExit as e:
        raise HTTPException(500, detail=f"Error en el motor Prolog: {e.code}")

    return {
        "vehiculo_id": body.vehiculo_id,
        "sintomas_evaluados": sintomas,
        "fallas_detectadas": fallas,
        "nivel_criticidad_global": criticidad,
        "repuestos_totales": [{"codigo": c, "cantidad": q} for c, q in repuestos_total],
    }


# ============================================================
# b) POST /api/cotizar
# ============================================================
@app.post("/api/cotizar", response_model=CotizacionOut, tags=["Scala"])
def cotizar(body: CotizarIn):
    cli = shutil.which("scala-cli")
    if cli is None:
        raise HTTPException(503, detail="No se encontro 'scala-cli' en el PATH del servidor.")

    fusion: dict = {}  # Scala no fusiona codigos repetidos: lo hacemos aqui
    for r in body.repuestos:
        fusion[r.codigo] = fusion.get(r.codigo, 0) + r.cantidad

    entrada = {
        "cotizacion_id": body.cotizacion_id or f"COT-{uuid.uuid4().hex[:8].upper()}",
        "vehiculo_id": body.vehiculo_id or "SIN-ASIGNAR",
        "repuestos": [{"codigo": c, "cantidad": q} for c, q in fusion.items()],
        "horas_mano_obra": body.horas_mano_obra,
        "costo_hora_mano_obra": body.costo_hora_mano_obra,
    }
    env = {**os.environ, "JAVA_TOOL_OPTIONS": "-Dfile.encoding=UTF-8 -Dstdout.encoding=UTF-8"}

    with tempfile.TemporaryDirectory(prefix="cotizar_") as tmp:  # unico por peticion
        ruta_in, ruta_out = Path(tmp) / "input.json", Path(tmp) / "output.json"
        ruta_in.write_text(json.dumps(entrada, ensure_ascii=False), encoding="utf-8")
        try:
            with _LOCK_SCALA:
                proc = subprocess.run(
                    [cli, "run", str(SCALA_FILE), "--", str(ROOT), str(ruta_in), str(ruta_out)],
                    capture_output=True, text=True, encoding="utf-8",
                    cwd=ROOT, env=env, timeout=TIMEOUT_SCALA_SEG,
                )
        except subprocess.TimeoutExpired:
            raise HTTPException(504, detail=f"scala-cli excedio {TIMEOUT_SCALA_SEG}s.")
        if proc.returncode != 0 or not ruta_out.exists():
            raise HTTPException(500, detail=f"Error en Scala (codigo {proc.returncode}): "
                                            f"{proc.stderr[-500:]}")
        return json.loads(ruta_out.read_text(encoding="utf-8"))


# ============================================================
# c) GET /api/analitica  (alias: /api/kpis)
# ============================================================
@app.get("/api/analitica", response_model=AnaliticaOut, tags=["Pandas"])
@app.get("/api/kpis", response_model=AnaliticaOut, include_in_schema=False)
def analitica():
    try:
        return obtener_kpis_y_graficos()
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(500, detail=f"Error en la analitica: {e}")