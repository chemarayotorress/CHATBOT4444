# VC999 Quote Service

Microservicio en FastAPI que recibe la cotización final desde n8n, genera un PDF y lo envía por correo al cliente.

## Configuración

1. Instala dependencias:

```bash
pip install -r requirements.txt
```

2. Exporta variables de entorno (usa tu App Password de Gmail, no la contraseña normal):

```bash
export GMAIL_USER="Manuel.rayotorresvc999@gmail.com"
export GMAIL_APP_PASSWORD="<app-password>"
```

3. Arranca el servicio:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Endpoint

`POST /api/quote`

Ejemplo de body:

```json
{
  "modelo": "CM860",
  "customerName": "Nombre Cliente",
  "customerEmail": "cliente@dominio.com",
  "currency": "USD",
  "selections": [
    { "stepId": "VOLTAGE", "label": "208V 3ph", "value": "208", "price": 0 },
    { "stepId": "LID", "label": "10 inch", "value": "10", "price": 995 }
  ],
  "totalPrice": 24995
}
```

Respuestas:
- Éxito: `{ "ok": true, "quoteId": "<uuid>", "emailedTo": "<customerEmail>" }`
- Error: `{ "ok": false, "error": "<mensaje>" }`

## n8n

En el workflow, agrega un nodo HTTP Request al final del wizard apuntando a `http://host.docker.internal:8000/api/quote` (o la URL donde corra este servicio) con el body JSON anterior. Maneja la respuesta para avisar al usuario en Telegram si el correo se envió o si hubo error.
