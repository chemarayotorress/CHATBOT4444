# Nota: ¿De dónde salen los precios del PDF y cómo cambiarlos?

## Origen de los precios usados en el PDF

Los precios que terminan en el PDF **no salen del JSON estático**, sino del catálogo cargado desde Google Sheets en el flujo. En concreto:

1. **Precio base de la máquina**: se lee desde la hoja **`DB_Maquinas`** del Google Sheet y se guarda en `catalog[model].basePrice`. El flujo toma la columna `precio_base` (o sinónimos como `base_price`, `precio`, etc.) y la convierte a número.【F:json3.json†L173-L254】
2. **Precios de opciones**: se leen desde la hoja **`DB_Precios`** (por modelo, paso y opción). Si no existe en `DB_Precios`, se usa como *fallback* el precio que venga en **`DB_Opciones`** (`precio`, `price`, etc.). Estos valores se guardan como `step.options[].price` en el catálogo.【F:json3.json†L173-L292】
3. **Lo que se envía al PDF** (FastAPI) proviene de `precio_base` y `precio_cambiado` en el `fastapiBody`, que se arma con el `basePrice` del catálogo + las selecciones del usuario (opciones y sus precios).【F:json3.json†L429-L472】

## Cómo cambiar los precios

1. **Abrir el Google Sheet** con ID `171OxljLpc-5-RYaaVlFJR93IcbwbijLuhPjJ2Y79H6I`.
2. **Actualizar los precios base** en la hoja **`DB_Maquinas`** (columna `precio_base`).【F:json3.json†L173-L254】
3. **Actualizar los precios de opciones** en la hoja **`DB_Precios`** (columnas para modelo/paso/opción/precio). Si un precio no está en `DB_Precios`, entonces se tomará el que esté en `DB_Opciones`, así que asegúrate de mantenerlos consistentes.【F:json3.json†L173-L292】
4. **Forzar recarga del catálogo** en el bot con `/start` para que el flujo vuelva a leer las hojas y refresque `staticData.catalog` (incluyendo `DB_Precios`).【F:json3.json†L232-L314】

---

Si necesitas que el PDF tome precios de otro origen, habría que cambiar la lógica del nodo **“Guardar en Memoria”**, que es donde se construye el catálogo y se asignan los precios base/opciones.【F:json3.json†L173-L292】
