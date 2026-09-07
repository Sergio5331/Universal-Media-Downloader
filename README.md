<p align="center"><img src="assets/downloader.svg" width="100%" alt="Universal Media Downloader Pro — Beta para Windows"></p>

<p align="center">
  <a href="https://github.com/Sergio5331/Universal-Media-Downloader/releases/tag/v1.0.0-beta.1"><strong>Descargar la beta</strong></a>
  &nbsp; · &nbsp;
  <a href="https://github.com/Sergio5331/Universal-Media-Downloader/issues/new?template=error.yml">Reportar un problema</a>
</p>

**Universal Media Downloader Pro** es una aplicación de escritorio para descargar video y extraer audio desde enlaces compatibles con su motor yt-dlp. Reúne descargas individuales, colas por lotes y opciones para playlists en una interfaz en español.

> **Versión beta 1.0.0.** El proyecto está en desarrollo. La disponibilidad de cada descarga depende del sitio de origen, del enlace y del motor de descarga.

## Funciones

| Función | Descripción |
| :--- | :--- |
| Descarga individual | Analiza un enlace y muestra el título, la miniatura y las calidades disponibles |
| Cola por lotes | Procesa varios enlaces, uno por línea |
| Playlists | Permite activar la descarga de listas completas y organizarlas en carpetas |
| Video | Selección de calidad y combinación de video/audio con salida MP4 cuando los formatos lo permiten |
| Audio MP3 | Conversión a 128, 192 o 320 kbps |
| Carátulas y etiquetas | Opción para incorporar miniatura y metadatos al MP3 cuando estén disponibles |
| Motor actualizable | Comprobación al iniciar y botón para actualizar yt-dlp |
| Destino | Selección de la carpeta donde se guardarán los archivos |

## Descargar e instalar

1. Abre [Universal Media Downloader Pro 1.0.0 Beta](https://github.com/Sergio5331/Universal-Media-Downloader/releases/tag/v1.0.0-beta.1).
2. En **Assets**, descarga **Instalador_UniversalDownloader_v1.0.exe** (aproximadamente **64 MB**).
3. Ejecuta el instalador y sigue el asistente en español. Puede solicitar permisos de administrador.
4. Si quieres, activa la opción de crear un acceso directo en el escritorio.
5. Abre **Universal Media Downloader** desde el menú Inicio o el acceso directo.

La distribución es para **Windows de 64 bits**. El ejecutable está empaquetado con Python y FFmpeg. No necesitas instalar Python por separado para abrirlo. Se requiere conexión a Internet para descargar contenido y actualizar el motor.

## Uso básico

**Un enlace:** pégalo en *Descarga Individual*, pulsa **Buscar**, elige video o audio, selecciona la calidad y la carpeta, y pulsa **Iniciar Descarga**.

**Varios enlaces:** abre la pestaña de lotes y pega un enlace por línea. La aplicación los procesa en una cola.

Las cookies del navegador son opcionales y están desactivadas inicialmente. Puedes elegir un navegador si el sitio necesita una sesión disponible en tu equipo.

## Estado de la beta

- La compatibilidad con sitios puede cambiar. Actualizar el motor puede ayudar, pero no garantiza que todos los enlaces funcionen.
- El mensaje final de la cola indica que terminó el procesamiento; en esta versión no garantiza que todos los archivos se hayan descargado. Comprueba la carpeta de destino.
- El instalador todavía no tiene firma digital de editor; Windows puede mostrar un aviso.
- Esta publicación utiliza el instalador existente del proyecto. Se ha verificado su integridad, pero no se ha realizado una prueba de descarga de cada plataforma para esta publicación.

## Ayuda y comentarios

[Reporta un error](https://github.com/Sergio5331/Universal-Media-Downloader/issues/new?template=error.yml) indicando la versión de Windows, la versión del motor que aparece en la aplicación y los pasos para reproducirlo.

Este repositorio reúne instaladores, documentación y reportes de la beta. No contiene el código fuente de la aplicación.

---

Desarrollado por [Sergio](https://github.com/Sergio5331). También puedes conocer [OctaStudio](https://github.com/Sergio5331/OctaStudio), su editor de video y audio para Windows.
