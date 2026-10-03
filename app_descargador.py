# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Sergio (https://github.com/Sergio5331)
# Distribuido bajo GNU GPL versión 3; consulta LICENSE.

import os
import sys
import re
import json
import zipfile
import threading
import urllib.request
from io import BytesIO
from tkinter import filedialog, messagebox
from PIL import Image
import customtkinter as ctk

# --- 1. Configuración del Motor Dinámico en AppData ---

APPDATA_DIR = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
MOTOR_DIR = os.path.join(APPDATA_DIR, 'UniversalDownloader', 'motor')
os.makedirs(MOTOR_DIR, exist_ok=True)

if MOTOR_DIR not in sys.path:
    sys.path.insert(0, MOTOR_DIR)

import yt_dlp

# Configuración visual
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- 2. Detección de Recursos Portables (.exe / icono) ---

def obtener_ruta_recurso(nombre_archivo):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, nombre_archivo)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre_archivo)

FFMPEG_PATH = obtener_ruta_recurso('ffmpeg.exe')
ICONO_PATH = obtener_ruta_recurso('icono.ico')

calidades_video_actuales = ["Mejor disponible"]
calidades_audio = ["320 kbps (Alta)", "192 kbps (Media)", "128 kbps (Básica)"]

enlace_actual_idx = 0
total_enlaces_cola = 1

# --- 3. Actualizador Automático del Motor ---

def parse_version(v_str):
    return tuple(int(x) for x in re.findall(r'\d+', str(v_str)))

def verificar_actualizacion_motor(notificar_al_dia=False):
    def _tarea():
        global yt_dlp
        try:
            ver_actual = getattr(yt_dlp.version, '__version__', 'Base')
            root.after(0, lambda: lbl_motor.configure(
                text=f"⚡ Motor: v{ver_actual} • Buscando actualizaciones...",
                text_color="#AAAAAA"
            ))

            url_pypi = "https://pypi.org/pypi/yt-dlp/json"
            req = urllib.request.Request(url_pypi, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            ver_remota = data['info']['version']

            if parse_version(ver_remota) > parse_version(ver_actual):
                root.after(0, lambda: lbl_motor.configure(
                    text=f"⬇ Actualizando motor a v{ver_remota}...",
                    text_color="#3B8ED0"
                ))

                url_wheel = None
                for u in data.get('urls', []):
                    if u.get('packagetype') == 'bdist_wheel':
                        url_wheel = u.get('url')
                        break

                if url_wheel:
                    req_whl = urllib.request.Request(url_wheel, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req_whl, timeout=20) as resp_whl:
                        whl_bytes = resp_whl.read()

                    with zipfile.ZipFile(BytesIO(whl_bytes), 'r') as zf:
                        for member in zf.namelist():
                            if member.startswith('yt_dlp/'):
                                zf.extract(member, MOTOR_DIR)

                    modules_to_del = [m for m in sys.modules if m == 'yt_dlp' or m.startswith('yt_dlp.')]
                    for m in modules_to_del:
                        del sys.modules[m]

                    import yt_dlp

                    ver_nueva = getattr(yt_dlp.version, '__version__', ver_remota)
                    root.after(0, lambda: lbl_motor.configure(
                        text=f"✨ Motor actualizado con éxito: v{ver_nueva}",
                        text_color="#4CAF50"
                    ))
                    if notificar_al_dia:
                        root.after(0, lambda: messagebox.showinfo(
                            "Motor Actualizado",
                            f"El motor de descargas se ha actualizado a la versión {ver_nueva}."
                        ))
            else:
                root.after(0, lambda: lbl_motor.configure(
                    text=f"⚡ Motor: v{ver_actual} (Al día ✔)",
                    text_color="#888888"
                ))
                if notificar_al_dia:
                    root.after(0, lambda: messagebox.showinfo(
                        "Motor al día",
                        f"Ya tienes la versión más reciente del motor ({ver_actual})."
                    ))
        except Exception as e:
            ver_actual = getattr(yt_dlp.version, '__version__', 'Activo')
            root.after(0, lambda: lbl_motor.configure(
                text=f"⚡ Motor: v{ver_actual} (Modo sin conexión)",
                text_color="#888888"
            ))
            if notificar_al_dia:
                root.after(0, lambda: messagebox.showwarning("Aviso", f"No se pudo consultar actualizaciones:\n{e}"))

    threading.Thread(target=_tarea, daemon=True).start()

# --- 4. Detección y Utilidades ---

def detectar_plataforma(url):
    u = url.lower()
    es_playlist = "list=" in u or "/playlist" in u
    tipo_extra = " [Playlist]" if es_playlist else ""

    if "youtube.com" in u or "youtu.be" in u:
        return f"YouTube 🔴{tipo_extra}"
    elif "tiktok.com" in u:
        return "TikTok 🎵 (Sin marca de agua)"
    elif "instagram.com" in u:
        return "Instagram 📸 (Reel / Post)"
    elif "twitter.com" in u or "x.com" in u:
        return "X / Twitter 🐦"
    elif "facebook.com" in u or "fb.watch" in u:
        return "Facebook 📘"
    elif "reddit.com" in u:
        return "Reddit 🤖"
    elif "twitch.tv" in u:
        return "Twitch 🟣"
    return f"Enlace Web / Multiplataforma 🌐{tipo_extra}"

def seleccionar_carpeta():
    carpeta = filedialog.askdirectory()
    if carpeta:
        ruta_var.set(carpeta)

def cambiar_tipo(seleccion):
    if seleccion == "Video (MP4)":
        menu_calidad.configure(values=calidades_video_actuales)
        menu_calidad.set(calidades_video_actuales[0])
        switch_metadata.pack_forget()
    else:
        menu_calidad.configure(values=calidades_audio)
        menu_calidad.set(calidades_audio[0])
        switch_metadata.pack(anchor="w", padx=16, pady=(0, 4))

def pegar_portapapeles_individual():
    try:
        texto = root.clipboard_get().strip()
        url_entry.delete(0, "end")
        url_entry.insert(0, texto)
        cargar_info_video()
    except Exception:
        messagebox.showwarning("Aviso", "No hay texto válido copiado en el portapapeles.")

def pegar_portapapeles_lote():
    try:
        texto = root.clipboard_get().strip()
        txt_lote.insert("end", "\n" + texto if txt_lote.get("1.0", "end").strip() else texto)
        actualizar_contador_lote()
    except Exception:
        messagebox.showwarning("Aviso", "No hay texto válido copiado en el portapapeles.")

def actualizar_contador_lote(*args):
    lineas = [l.strip() for l in txt_lote.get("1.0", "end").splitlines() if l.strip().startswith("http")]
    lbl_contador_lote.configure(text=f"Total de enlaces detectados: {len(lineas)}")

# --- 5. Análisis del Enlace (Modo Individual) ---

def cargar_info_video():
    global calidades_video_actuales
    url = url_entry.get().strip()
    if not url:
        return

    plataforma = detectar_plataforma(url)
    lbl_plataforma.configure(text=f"Plataforma: {plataforma}")

    if "list=" in url.lower() or "/playlist" in url.lower():
        switch_playlist.select()

    lbl_estado.configure(text="🔍 Analizando enlace...")
    btn_buscar.configure(state="disabled")

    def _tarea_info():
        global calidades_video_actuales
        es_modo_playlist = switch_playlist.get() == 1
        navegador_cookies = combo_cookies.get()

        try:
            opciones_info = {
                'quiet': True,
                'skip_download': True,
                'extract_flat': 'in_playlist' if es_modo_playlist else False,
                'noplaylist': not es_modo_playlist
            }
            if navegador_cookies != "Desactivado":
                opciones_info['cookiesfrombrowser'] = (navegador_cookies.lower(),)

            with yt_dlp.YoutubeDL(opciones_info) as ydl:
                info = ydl.extract_info(url, download=False)

            es_contenedor = 'entries' in info or info.get('_type') == 'playlist'

            if es_contenedor and es_modo_playlist:
                titulo = info.get('title', 'Lista de reproducción')
                total_items = len(list(info.get('entries', []))) or info.get('playlist_count', 'Varios')
                tiempo_str = f"{total_items} videos / audios"
                miniatura_url = None
                entries = list(info.get('entries', []))
                if entries and isinstance(entries[0], dict):
                    miniatura_url = entries[0].get('thumbnail')
                calidades_video_actuales = ["Mejor disponible"]
            else:
                titulo = info.get('title', 'Video sin título')
                if len(titulo) > 75:
                    titulo = titulo[:72] + "..."

                duracion = info.get('duration')
                if duracion:
                    minutos, segundos = divmod(int(duracion), 60)
                    tiempo_str = f"{minutos}:{segundos:02d}"
                else:
                    tiempo_str = "No disponible / Corto"

                miniatura_url = info.get('thumbnail')

                resoluciones = set()
                for f in info.get('formats', []):
                    h = f.get('height')
                    vcodec = f.get('vcodec')
                    if h and vcodec and vcodec != 'none':
                        resoluciones.add(h)

                if resoluciones:
                    res_ordenadas = sorted(list(resoluciones), reverse=True)
                    lista = ["Mejor disponible"]
                    for r in res_ordenadas:
                        if r >= 2160:
                            lista.append(f"{r}p (4K)")
                        elif r >= 1440:
                            lista.append(f"{r}p (2K)")
                        elif r >= 1080:
                            lista.append(f"{r}p (FHD)")
                        elif r >= 720:
                            lista.append(f"{r}p (HD)")
                        else:
                            lista.append(f"{r}p")
                    calidades_video_actuales = lista
                else:
                    calidades_video_actuales = ["Mejor disponible (Original)"]

            img_ctk = None
            if miniatura_url:
                try:
                    req = urllib.request.Request(
                        miniatura_url,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                    )
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        datos_img = resp.read()
                    img_pil = Image.open(BytesIO(datos_img))
                    img_ctk = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(200, 112))
                except Exception:
                    img_ctk = None

            def actualizar_ui():
                prefix_tipo = "📂 Playlist: " if (es_contenedor and es_modo_playlist) else ""
                lbl_titulo.configure(text=f"{prefix_tipo}{titulo}\n\n⏱ Duración/Total: {tiempo_str}")
                if img_ctk:
                    lbl_miniatura.configure(image=img_ctk, text="")
                else:
                    lbl_miniatura.configure(image=None, text="Vista previa\nno disponible")

                if seg_tipo.get() == "Video (MP4)":
                    menu_calidad.configure(values=calidades_video_actuales)
                    menu_calidad.set(calidades_video_actuales[0])

                lbl_estado.configure(text="✔ Enlace verificado y listo")
                btn_descargar.configure(state="normal")
                btn_buscar.configure(state="normal")

            root.after(0, actualizar_ui)

        except Exception as e:
            def mostrar_error():
                lbl_estado.configure(text="❌ Error al analizar el enlace")
                btn_buscar.configure(state="normal")
                messagebox.showerror("Error", f"No se pudo obtener información:\n{e}\n\nConsejo: Si el video tiene restricción (+18) o es privado, selecciona tu navegador en 'Cookies de sesión'.")
            root.after(0, mostrar_error)

    threading.Thread(target=_tarea_info, daemon=True).start()

# --- 6. Proceso de Descarga (Individual o Lote) ---

def hook_progreso(d):
    global enlace_actual_idx, total_enlaces_cola
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate')
        descargado = d.get('downloaded_bytes', 0)
        velocidad = d.get('speed', 0)
        vel_str = f"{velocidad / 1024 / 1024:.1f} MB/s" if velocidad else "-- MB/s"

        prefijo_cola = f"[{enlace_actual_idx}/{total_enlaces_cola}] " if total_enlaces_cola > 1 else ""

        if total:
            pct = descargado / total
            progreso_bar.set(pct)
            lbl_estado.configure(text=f"{prefijo_cola}Descargando: {pct * 100:.1f}% ({vel_str})")
    elif d['status'] == 'finished':
        progreso_bar.set(1.0)
        lbl_estado.configure(text="⚙ Procesando, convirtiendo carátula y empaquetando...")

def ejecutar_descargas():
    global enlace_actual_idx, total_enlaces_cola
    modo_pestana = tabview.get()
    carpeta = ruta_var.get()
    tipo = seg_tipo.get()
    calidad = menu_calidad.get()
    es_modo_playlist = switch_playlist.get() == 1
    incrustar_tags = switch_metadata.get() == 1
    navegador_cookies = combo_cookies.get()

    if modo_pestana == "Descarga Individual":
        url_ind = url_entry.get().strip()
        if not url_ind:
            messagebox.showwarning("Aviso", "Por favor introduce un enlace antes de descargar.")
            btn_descargar.configure(state="normal")
            return
        lista_urls = [url_ind]
    else:
        lineas = [l.strip() for l in txt_lote.get("1.0", "end").splitlines() if l.strip().startswith("http")]
        if not lineas:
            messagebox.showwarning("Aviso", "No hay enlaces válidos en la caja de texto.\nPega enlaces que empiecen con http:// o https://")
            btn_descargar.configure(state="normal")
            return
        lista_urls = lineas

    total_enlaces_cola = len(lista_urls)

    for idx, url in enumerate(lista_urls, start=1):
        enlace_actual_idx = idx
        lbl_estado.configure(text=f"Iniciando enlace [{idx}/{total_enlaces_cola}]...")
        progreso_bar.set(0)

        if es_modo_playlist:
            plantilla_salida = os.path.join(carpeta, '%(playlist_title,playlist)s', '%(playlist_index)02d - %(title).80s [%(id)s].%(ext)s')
        else:
            plantilla_salida = os.path.join(carpeta, '%(title).90s [%(id)s].%(ext)s')

        opciones = {
            'outtmpl': plantilla_salida,
            'progress_hooks': [hook_progreso],
            'ffmpeg_location': FFMPEG_PATH,
            'noplaylist': not es_modo_playlist,
            'ignoreerrors': True,
        }

        if navegador_cookies != "Desactivado":
            opciones['cookiesfrombrowser'] = (navegador_cookies.lower(),)

        if tipo == "Solo Audio (MP3)":
            bitrate = "320" if "320" in calidad else ("128" if "128" in calidad else "192")
            postprocessors = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': bitrate,
            }]

            if incrustar_tags:
                opciones['writethumbnail'] = True
                postprocessors.append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
                postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})
                postprocessors.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})

            opciones.update({
                'format': 'bestaudio/best',
                'postprocessors': postprocessors,
            })
        else:
            opciones['merge_output_format'] = 'mp4'
            match = re.search(r'(\d+)', calidad)
            if match and "Mejor" not in calidad:
                altura = match.group(1)
                opciones['format'] = f'bestvideo[height<={altura}]+bestaudio/best[height<={altura}]/best'
            else:
                opciones['format'] = 'bestvideo+bestaudio/best'

        try:
            with yt_dlp.YoutubeDL(opciones) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"Error procesando enlace {url}: {e}")

    lbl_estado.configure(text=f"✔ Completadas {total_enlaces_cola} descarga(s)")
    messagebox.showinfo("Proceso Finalizado", f"Se procesaron los {total_enlaces_cola} enlace(s) correctamente en:\n{carpeta}")
    btn_descargar.configure(state="normal")
    btn_buscar.configure(state="normal")

def iniciar_descarga():
    btn_descargar.configure(state="disabled")
    btn_buscar.configure(state="disabled")
    threading.Thread(target=ejecutar_descargas, daemon=True).start()

# --- 7. Interfaz Gráfica ---

root = ctk.CTk()
root.title("Universal Media Downloader Pro")
root.geometry("630x840")
root.resizable(False, False)

try:
    if os.path.exists(ICONO_PATH):
        root.iconbitmap(ICONO_PATH)
except Exception:
    pass

# Encabezado
lbl_app = ctk.CTkLabel(root, text="Descargador Universal de Medios", font=ctk.CTkFont(size=20, weight="bold"))
lbl_app.pack(pady=(12, 2))

lbl_sub = ctk.CTkLabel(root, text="YouTube (+18) • Cola por Lote • TikTok • Instagram • X • Facebook", font=ctk.CTkFont(size=11), text_color="#888888")
lbl_sub.pack(pady=(0, 6))

# Pestañas
tabview = ctk.CTkTabview(root, width=590, height=210)
tabview.pack(padx=20, pady=4)

tab_ind = tabview.add("Descarga Individual")
tab_lote = tabview.add("Cola por Lote (Enlaces Múltiples)")

# Pestaña 1
frame_url = ctk.CTkFrame(tab_ind, fg_color="transparent")
frame_url.pack(fill="x", pady=(2, 4))

url_entry = ctk.CTkEntry(frame_url, placeholder_text="Pega aquí el enlace del video o playlist...", font=ctk.CTkFont(size=12), height=34)
url_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

btn_pegar = ctk.CTkButton(frame_url, text="📋 Pegar", width=70, height=34, command=pegar_portapapeles_individual)
btn_pegar.pack(side="left", padx=3)

btn_buscar = ctk.CTkButton(frame_url, text="🔍 Buscar", width=75, height=34, fg_color="#1f538d", hover_color="#14375e", command=cargar_info_video)
btn_buscar.pack(side="left")

card_preview = ctk.CTkFrame(tab_ind, corner_radius=10, height=115)
card_preview.pack(fill="x", pady=4)

lbl_miniatura = ctk.CTkLabel(card_preview, text="Sin miniatura", width=200, height=112, fg_color="#2b2b2b", corner_radius=8)
lbl_miniatura.pack(side="left", padx=8, pady=8)

lbl_titulo = ctk.CTkLabel(card_preview, text="Pega un enlace y presiona 'Buscar'\npara obtener vista previa y calidades.", wraplength=270, justify="left", font=ctk.CTkFont(size=12))
lbl_titulo.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)

# Pestaña 2
txt_lote = ctk.CTkTextbox(tab_lote, height=110, font=ctk.CTkFont(size=12))
txt_lote.pack(fill="both", expand=True, padx=4, pady=(2, 4))
txt_lote.bind("<KeyRelease>", actualizar_contador_lote)

frame_btn_lote = ctk.CTkFrame(tab_lote, fg_color="transparent")
frame_btn_lote.pack(fill="x", padx=4, pady=(0, 2))

btn_pegar_lote = ctk.CTkButton(frame_btn_lote, text="📋 Pegar enlaces copiados", height=28, command=pegar_portapapeles_lote)
btn_pegar_lote.pack(side="left")

lbl_contador_lote = ctk.CTkLabel(frame_btn_lote, text="Total de enlaces detectados: 0", font=ctk.CTkFont(size=12, weight="bold"), text_color="#3B8ED0")
lbl_contador_lote.pack(side="right")

lbl_plataforma = ctk.CTkLabel(root, text="Modo: Listo para recibir descargas", font=ctk.CTkFont(size=12, weight="bold"), text_color="#3B8ED0")
lbl_plataforma.pack(pady=(2, 4))

# Opciones de Descarga
card_config = ctk.CTkFrame(root, corner_radius=12)
card_config.pack(fill="x", padx=20, pady=4)

seg_tipo = ctk.CTkSegmentedButton(card_config, values=["Video (MP4)", "Solo Audio (MP3)"], command=cambiar_tipo, font=ctk.CTkFont(size=13, weight="bold"))
seg_tipo.set("Video (MP4)")
seg_tipo.pack(fill="x", padx=15, pady=(10, 6))

switch_playlist = ctk.CTkSwitch(card_config, text="Descargar playlist completa (si el enlace es de una lista)", font=ctk.CTkFont(size=12))
switch_playlist.pack(anchor="w", padx=16, pady=(0, 4))

switch_metadata = ctk.CTkSwitch(card_config, text="🏷️ Incrustar carátula y artista en archivos MP3", font=ctk.CTkFont(size=12))
switch_metadata.select()

frame_filas = ctk.CTkFrame(card_config, fg_color="transparent")
frame_filas.pack(fill="x", padx=15, pady=4)

ctk.CTkLabel(frame_filas, text="Calidad de salida:", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", pady=2)
menu_calidad = ctk.CTkOptionMenu(frame_filas, values=calidades_video_actuales, width=170)
menu_calidad.grid(row=0, column=1, sticky="e", padx=(10, 0), pady=2)

ctk.CTkLabel(frame_filas, text="Cookies (+18 / Sesión):", font=ctk.CTkFont(size=13)).grid(row=1, column=0, sticky="w", pady=4)
combo_cookies = ctk.CTkOptionMenu(frame_filas, values=["Desactivado", "Chrome", "Edge", "Firefox", "Brave", "Opera"], width=170)
combo_cookies.set("Desactivado")
combo_cookies.grid(row=1, column=1, sticky="e", padx=(10, 0), pady=4)
frame_filas.grid_columnconfigure(0, weight=1)

frame_ruta = ctk.CTkFrame(card_config, fg_color="transparent")
frame_ruta.pack(fill="x", padx=15, pady=(4, 10))
ruta_var = ctk.StringVar(value=os.path.expanduser("~/Downloads"))
entry_ruta = ctk.CTkEntry(frame_ruta, textvariable=ruta_var, height=32)
entry_ruta.pack(side="left", fill="x", expand=True, padx=(0, 8))
btn_carpeta = ctk.CTkButton(frame_ruta, text="Examinar", width=85, height=32, command=seleccionar_carpeta)
btn_carpeta.pack(side="right")

# Progreso y Estado
lbl_estado = ctk.CTkLabel(root, text="Listo para comenzar", font=ctk.CTkFont(size=12), text_color="#aaaaaa")
lbl_estado.pack(pady=(4, 2))

progreso_bar = ctk.CTkProgressBar(root, width=590, height=12)
progreso_bar.set(0)
progreso_bar.pack(pady=3)

btn_descargar = ctk.CTkButton(root, text="⬇ Iniciar Descarga", height=44, font=ctk.CTkFont(size=15, weight="bold"), fg_color="#2e7d32", hover_color="#1b5e20", command=iniciar_descarga)
btn_descargar.pack(fill="x", padx=20, pady=(6, 8))

frame_footer = ctk.CTkFrame(root, height=34, corner_radius=8, fg_color="#1a1a1a")
frame_footer.pack(fill="x", padx=20, pady=(0, 8))

lbl_motor = ctk.CTkLabel(frame_footer, text="⚡ Motor: Iniciando...", font=ctk.CTkFont(size=11), text_color="#888888")
lbl_motor.pack(side="left", padx=12, pady=4)

btn_check_motor = ctk.CTkButton(
    frame_footer,
    text="🔄 Actualizar motor",
    width=125,
    height=24,
    font=ctk.CTkFont(size=11),
    fg_color="#2b2b2b",
    hover_color="#3a3a3a",
    command=lambda: verificar_actualizacion_motor(notificar_al_dia=True)
)
btn_check_motor.pack(side="right", padx=8, pady=4)

root.after(1000, lambda: verificar_actualizacion_motor(notificar_al_dia=False))

root.mainloop()
