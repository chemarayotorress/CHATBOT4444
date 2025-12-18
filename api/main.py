import logging
import os
import uuid
from typing import List

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from .mailer import send_email
from .pdf_generator import build_pdf

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SelectionItem(BaseModel):
    stepId: str = Field(..., description="Identificador del paso")
    label: str = Field(..., description="Texto visible de la opción")
    value: str = Field(..., description="Valor elegido")
    price: float = Field(..., description="Precio de la opción")


class QuoteRequest(BaseModel):
    modelo: str = Field(..., description="Modelo de máquina")
    customerName: str = Field(..., description="Nombre del cliente")
    customerEmail: EmailStr = Field(..., description="Correo del cliente")
    currency: str = Field("USD", description="Moneda de la cotización")
    selections: List[SelectionItem]
    totalPrice: float = Field(..., description="Precio total")


app = FastAPI(title="VC999 Quote Service", version="1.0.0")


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


@app.post("/api/quote")
async def create_quote(payload: QuoteRequest) -> JSONResponse:
    if not payload.selections:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Faltan selections"})

    if payload.totalPrice is None:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Falta totalPrice"})

    pdf_path = None
    quote_id = str(uuid.uuid4())

    try:
        pdf_path = build_pdf(payload, quote_id)

        subject = f"Cotización VC999 - {payload.modelo} - {payload.customerName}"
        body = (
            f"Hola {payload.customerName},\n\n"
            f"Adjuntamos la cotización solicitada para el modelo {payload.modelo}.\n"
            f"Total: {payload.totalPrice:,.0f} {payload.currency}.\n\n"
            "Si tienes alguna duda o necesitas ajustar la configuración, responde a este correo.\n\n"
            "Saludos,\nEquipo VC999"
        )

        send_email(
            to_address=payload.customerEmail,
            subject=subject,
            body=body,
            attachment_path=pdf_path,
        )

        return JSONResponse(
            status_code=200,
            content={"ok": True, "quoteId": quote_id, "emailedTo": payload.customerEmail},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error al generar o enviar la cotización")
        return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})
    finally:
        if pdf_path:
            try:
                os.remove(pdf_path)
            except OSError:
                logger.warning("No se pudo eliminar el PDF temporal %s", pdf_path)
