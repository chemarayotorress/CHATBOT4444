from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Iterable

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _write_line(c: canvas.Canvas, text: str, x: float, y: float) -> float:
    c.drawString(x, y, text)
    return y - 14


def build_pdf(payload, quote_id: str) -> str:
    """Genera un PDF simple con los datos de la cotización."""

    selections = getattr(payload, "selections", []) or []
    customer_name = getattr(payload, "customerName", "") or "Cliente"
    modelo = getattr(payload, "modelo", "Modelo")
    total = getattr(payload, "totalPrice", 0)
    currency = getattr(payload, "currency", "USD")

    tmp_dir = Path(tempfile.gettempdir())
    pdf_path = tmp_dir / f"quote_{quote_id}.pdf"

    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter

    margin_x = 1 * inch
    y = height - margin_x

    c.setFont("Helvetica-Bold", 16)
    y = _write_line(c, "Cotización VC999", margin_x, y)
    c.setFont("Helvetica", 12)
    y = _write_line(c, f"ID de Cotización: {quote_id}", margin_x, y)
    y = _write_line(c, f"Modelo: {modelo}", margin_x, y)
    y = _write_line(c, f"Cliente: {customer_name}", margin_x, y)
    y = _write_line(c, f"Total: {total:,.0f} {currency}", margin_x, y)

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    y = _write_line(c, "Configuración seleccionada:", margin_x, y)

    c.setFont("Helvetica", 11)
    for item in selections:  # type: ignore[assignment]
        step_id = getattr(item, "stepId", getattr(item, "step", "Paso"))
        label = getattr(item, "label", getattr(item, "value", ""))
        value = getattr(item, "value", "")
        price = getattr(item, "price", 0)
        y = _write_line(c, f"- {step_id}: {label} ({value}) - {price:,.0f}", margin_x, y)
        if y < 1 * inch:
            c.showPage()
            y = height - margin_x
            c.setFont("Helvetica", 11)

    c.showPage()
    c.save()
    return str(pdf_path)
