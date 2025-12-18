import base64
import logging
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, root_validator, validator
from fpdf import FPDF

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

app = FastAPI(title="VC999 Cotizador", version="1.0.0")


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_str = normalized.encode("ASCII", "ignore").decode()
    clean = "".join(ch if ch.isalnum() else "_" for ch in ascii_str)
    clean = "_".join(filter(None, clean.split("_")))
    return clean or "cotizacion"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _salidas_dir() -> Path:
    salida_dir = _repo_root() / "salidas"
    salida_dir.mkdir(parents=True, exist_ok=True)
    return salida_dir


class Selection(BaseModel):
    paso: Optional[str] = Field(None, description="Paso del configurador")
    opcion: Optional[str] = Field(None, description="Opción elegida")
    precio: float = Field(0, description="Precio de la opción")
    step: Optional[str] = None
    option: Optional[str] = None
    value: Optional[str] = None
    label: Optional[str] = None
    price: Optional[float] = None

    class Config:
        extra = "allow"

    @root_validator(pre=True)
    def normalize(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        paso = values.get("paso") or values.get("step")
        opcion = (
            values.get("opcion")
            or values.get("option")
            or values.get("value")
            or values.get("label")
        )
        precio = values.get("precio")
        if precio is None:
            precio = values.get("price")
        try:
            precio_num = float(precio)
        except (TypeError, ValueError):
            precio_num = 0.0

        return {"paso": paso, "opcion": opcion, "precio": precio_num}


class Customer(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None

    class Config:
        extra = "allow"


class CotizacionRequest(BaseModel):
    modelo: Optional[str] = Field(None, description="Modelo de máquina")
    nombre_cliente: Optional[str] = Field(None, description="Nombre del cliente")
    email: Optional[str] = Field(None, description="Correo del cliente")
    precio_base: Optional[float] = Field(None, description="Precio base")
    precio_cambiado: Optional[float] = Field(None, description="Precio modificado")
    selecciones: List[Selection] = Field(default_factory=list, description="Selecciones")
    machine: Optional[str] = None
    model: Optional[str] = None
    totalPrice: Optional[float] = None
    basePrice: Optional[float] = None
    selections: Optional[List[Selection]] = None
    customer: Optional[Customer] = None

    class Config:
        extra = "allow"

    @root_validator(pre=True)
    def map_aliases(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        mapped = dict(values)
        customer_data = mapped.get("customer") if isinstance(mapped.get("customer"), dict) else {}
        mapped["modelo"] = mapped.get("modelo") or mapped.get("model") or mapped.get("machine")
        mapped["nombre_cliente"] = mapped.get("nombre_cliente") or mapped.get("customer_name")
        mapped["email"] = (
            mapped.get("email")
            or mapped.get("customer_email")
            or customer_data.get("email")
        )
        if not mapped.get("nombre_cliente"):
            mapped["nombre_cliente"] = customer_data.get("name")

        mapped["precio_base"] = mapped.get("precio_base")
        if mapped.get("precio_base") is None:
            mapped["precio_base"] = mapped.get("basePrice") or mapped.get("base_price")

        mapped["precio_cambiado"] = mapped.get("precio_cambiado")
        if mapped.get("precio_cambiado") is None:
            mapped["precio_cambiado"] = mapped.get("totalPrice")

        mapped["selecciones"] = (
            mapped.get("selecciones")
            or mapped.get("selections")
            or []
        )
        return mapped

    @validator("precio_base", "precio_cambiado", pre=True)
    def coerce_float(cls, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


class CotizacionResponse(BaseModel):
    ok: bool = True
    filename: str
    pdf_base64: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
    details: Optional[str] = None
    where: Optional[str] = None


@app.exception_handler(ValidationError)
async def validation_exception_handler(_request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            ok=False,
            error="payload_invalid",
            details=exc.json(),
            where="validation",
        ).dict(),
    )


def _normalize_payload(data: CotizacionRequest) -> Dict[str, Any]:
    precio_base = data.precio_base if data.precio_base is not None else 0.0
    precio_cambiado = (
        data.precio_cambiado
        if data.precio_cambiado is not None
        else precio_base
    )

    normalized = {
        "modelo": (data.modelo or "").strip(),
        "nombre_cliente": (data.nombre_cliente or "").strip(),
        "email": (data.email or "").strip(),
        "precio_base": float(precio_base),
        "precio_cambiado": float(precio_cambiado),
        "selecciones": [sel.dict() for sel in data.selecciones],
    }

    logger.info("Payload normalizado: %s", normalized)
    return normalized


def _build_filename(modelo: str, nombre_cliente: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parts = ["Cotizacion", _slugify(modelo), _slugify(nombre_cliente), timestamp]
    return "_".join(filter(None, parts)) + ".pdf"


def _render_pdf(payload: Dict[str, Any]) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Cotización VC999", ln=1)

    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Modelo: {payload['modelo']}", ln=1)
    pdf.cell(0, 10, f"Cliente: {payload['nombre_cliente']}", ln=1)
    pdf.cell(0, 10, f"Email: {payload['email']}", ln=1)
    pdf.cell(0, 10, f"Precio base: ${payload['precio_base']:,.2f}", ln=1)
    pdf.cell(0, 10, f"Precio total: ${payload['precio_cambiado']:,.2f}", ln=1)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Selecciones:", ln=1)
    pdf.set_font("Arial", size=11)

    if payload["selecciones"]:
        for sel in payload["selecciones"]:
            paso = sel.get("paso") or "Paso"
            opcion = sel.get("opcion") or "-"
            precio = float(sel.get("precio") or 0)
            pdf.multi_cell(0, 8, f"- {paso}: {opcion} (+${precio:,.2f})")
    else:
        pdf.cell(0, 8, "- Sin selecciones", ln=1)

    return pdf.output(dest="S").encode("latin-1")


@app.post(
    "/generar-cotizacion",
    response_model=CotizacionResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generar_cotizacion(request: Request, body: CotizacionRequest):
    try:
        payload = _normalize_payload(body)

        if not payload["modelo"]:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    ok=False,
                    error="modelo_requerido",
                    details="Falta el modelo",
                    where="normalization",
                ).dict(),
            )

        if not payload["nombre_cliente"] or not payload["email"]:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    ok=False,
                    error="cliente_incompleto",
                    details="Faltan nombre o correo",
                    where="normalization",
                ).dict(),
            )

        filename = _build_filename(payload["modelo"], payload["nombre_cliente"])
        salida_dir = _salidas_dir()
        pdf_bytes = _render_pdf(payload)
        file_path = salida_dir / filename
        file_path.write_bytes(pdf_bytes)

        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        logger.info("PDF generado en: %s", file_path)
        logger.info("Tamaño del PDF (bytes): %s", len(pdf_bytes))

        return CotizacionResponse(
            ok=True,
            filename=filename,
            pdf_base64=pdf_base64,
            meta={"path": str(file_path)},
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - catch-all
        logger.exception("Error al generar cotización")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                ok=False,
                error="error_interno",
                details=str(exc),
                where="generacion_pdf",
            ).dict(),
        )
