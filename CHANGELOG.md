# Historial de cambios

## 1.1.1 — 4 de noviembre de 2026

- Icono de descarga nuevo, con círculo verde y flecha negra, en la aplicación y el instalador.
- Script `scripts/generar_icono.py` para generar el icono en nueve resoluciones.
- Corrección de la captura del mensaje de error antes de mostrarlo mediante un callback de la interfaz.
- Se simplifica el uso de sesión a las cookies del navegador; se retiran la carga de `cookies.txt`, las preferencias de sesión guardadas y el reintento asistido de playlists privadas.
- Se retiran las explicaciones detalladas de errores y el resumen de fallos de la cola. Es necesario comprobar los archivos de destino al terminar.
- Documentación ajustada a las funciones de esta revisión y firma autofirmada de desarrollo.

## 1.1.0 — 4 de noviembre de 2026

- Interfaz oscura en dos columnas, con opciones de descarga en un panel lateral.
- Archivo `cookies.txt` en formato Netscape como alternativa a las cookies del navegador.
- Se recuerda la elección de cookies de sesión en la configuración local.
- La aplicación ofrece configurar la sesión y reintentar al fallar una playlist privada por autenticación.
- Mensajes de error en español para problemas de sesión, cookies, disponibilidad del contenido y conexión.
- El aviso final de una cola informa de los enlaces que fallaron.
- Miniatura de las playlists cuando está disponible.
- Aplicación e instalador firmados con el mismo certificado autofirmado de desarrollo. Windows puede seguir mostrando un aviso de confianza.

Las opciones de sesión utilizan las credenciales del propio usuario y no dan acceso a contenido privado de otras cuentas.

## 1.0.0

- Descargas individuales, colas por lotes y playlists.
- Selección de calidad de video y extracción de audio MP3.
- Carátulas y metadatos opcionales en MP3.
- Actualización del motor yt-dlp.
- Código fuente bajo GPLv3 y distribución para Windows de 64 bits.
