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

TAM_MINIATURA = (288, 162)


def mejor_miniatura(datos):
    """URL de la miniatura de un video o de una entrada plana de playlist."""
    if datos.get('thumbnail'):
        return datos['thumbnail']
    miniaturas = [m for m in (datos.get('thumbnails') or []) if isinstance(m, dict) and m.get('url')]
    if not miniaturas:
        return None
    return max(miniaturas, key=lambda m: (m.get('width') or 0) * (m.get('height') or 0))['url']


def preparar_miniatura(img):
    """Recorta a 16:9 y redondea las esquinas sobre el color de la tarjeta (al doble de tamaño para pantallas HiDPI)."""
    from PIL import ImageDraw, ImageOps
    ancho, alto = TAM_MINIATURA[0] * 2, TAM_MINIATURA[1] * 2
    img = ImageOps.fit(img.convert("RGB"), (ancho, alto), Image.LANCZOS)
    mascara = Image.new("L", (ancho, alto), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, ancho - 1, alto - 1), radius=24, fill=255)
    fondo = Image.new("RGB", (ancho, alto), COLOR['panel'])
    fondo.paste(img, (0, 0), mascara)
    return fondo


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
        switch_metadata.pack(anchor="w", pady=(10, 0))

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
    lbl_contador_lote.configure(text=f"{len(lineas)} enlace(s) en cola")

# --- 5. Análisis del Enlace (Modo Individual) ---

def cargar_info_video():
    global calidades_video_actuales
    url = url_entry.get().strip()
    if not url:
        return

    plataforma = detectar_plataforma(url)
    lbl_plataforma.configure(text=f"  {plataforma}  ")

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
                miniatura_url = mejor_miniatura(info)
                entries = list(info.get('entries', []))
                if not miniatura_url and entries and isinstance(entries[0], dict):
                    miniatura_url = mejor_miniatura(entries[0])
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
                    img_pil = preparar_miniatura(Image.open(BytesIO(datos_img)))
                    img_ctk = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=TAM_MINIATURA)
                except Exception:
                    img_ctk = None

            es_lista = es_contenedor and es_modo_playlist
            titulo_corto = titulo if len(titulo) <= 90 else titulo[:87] + "..."

            def actualizar_ui():
                lbl_titulo.configure(text=titulo_corto)
                lbl_meta.configure(text=f"Playlist  ·  {tiempo_str}" if es_lista else f"Duración  ·  {tiempo_str}")
                if img_ctk:
                    lbl_miniatura.configure(image=img_ctk, text="", fg_color="transparent")
                else:
                    lbl_miniatura.configure(image=None, text="Vista previa\nno disponible", fg_color=COLOR['panel2'])

                if seg_tipo.get() == "Video (MP4)":
                    menu_calidad.configure(values=calidades_video_actuales)
                    menu_calidad.set(calidades_video_actuales[0])

                lbl_estado.configure(text="✔ Enlace verificado y listo")
                btn_descargar.configure(state="normal")
                btn_buscar.configure(state="normal")

            root.after(0, actualizar_ui)

        except Exception as e:
            error_texto = str(e)  # Python borra 'e' al salir del except; se guarda para mostrarlo después
            def mostrar_error():
                lbl_estado.configure(text="❌ Error al analizar el enlace")
                btn_buscar.configure(state="normal")
                messagebox.showerror("Error", f"No se pudo obtener información:\n{error_texto}\n\nConsejo: Si el video tiene restricción (+18) o es privado, selecciona tu navegador en 'Cookies de sesión'.")
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
    modo_pestana = seg_modo.get()
    carpeta = ruta_var.get()
    tipo = seg_tipo.get()
    calidad = menu_calidad.get()
    es_modo_playlist = switch_playlist.get() == 1
    incrustar_tags = switch_metadata.get() == 1
    navegador_cookies = combo_cookies.get()

    if modo_pestana == MODO_INDIVIDUAL:
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
    progreso_bar.configure(progress_color=COLOR['acento'])
    btn_descargar.configure(state="disabled")
    btn_buscar.configure(state="disabled")
    threading.Thread(target=ejecutar_descargas, daemon=True).start()

# --- 7. Interfaz Gráfica ---

COLOR = {
    'fondo': "#121212",
    'panel': "#181818",
    'panel2': "#1F1F1F",
    'borde': "#2A2A2A",
    'borde_vivo': "#3E3E3E",
    'texto': "#FFFFFF",
    'suave': "#B3B3B3",
    'acento': "#1ED760",
    'acento_hover': "#3BE477",
    'sobre_acento': "#000000",
    'claro': "#FFFFFF",
    'claro_hover': "#E6E6E6",
    'negativo': "#F3727F",
}
FUENTE = "Segoe UI"
MODO_INDIVIDUAL = "Un enlace"
MODO_LOTE = "Cola por lote"


def fuente(tam, peso="normal"):
    return ctk.CTkFont(family=FUENTE, size=tam, weight=peso)


def tarjeta(padre, **kw):
    return ctk.CTkFrame(padre, fg_color=COLOR['panel'], corner_radius=10, border_width=0, **kw)


def titulo_seccion(padre, texto):
    return ctk.CTkLabel(padre, text=texto.upper(), font=fuente(11, "bold"), text_color=COLOR['suave'])


# La ventana tiene que existir antes de crear fuentes
root = ctk.CTk(fg_color=COLOR['fondo'])
root.title("Universal Media Downloader")
root.geometry("1000x640")
root.resizable(False, False)

ESTILO_BOTON_SECUNDARIO = dict(
    fg_color=COLOR['panel2'], hover_color=COLOR['borde_vivo'], border_width=1,
    border_color="#4D4D4D", text_color=COLOR['texto'], font=fuente(12, "bold"),
)
ESTILO_MENU = dict(
    width=170, height=34, corner_radius=17, fg_color=COLOR['panel2'], button_color=COLOR['borde_vivo'],
    button_hover_color="#4D4D4D", dropdown_fg_color=COLOR['panel2'],
    dropdown_hover_color=COLOR['borde'], dropdown_text_color=COLOR['texto'],
    text_color=COLOR['texto'], font=fuente(12), dropdown_font=fuente(12),
)
ESTILO_ENTRADA = dict(
    corner_radius=17, fg_color=COLOR['panel2'], border_color=COLOR['borde_vivo'], border_width=1,
    text_color=COLOR['texto'], placeholder_text_color=COLOR['suave'],
)
ESTILO_SWITCH = dict(
    font=fuente(12), text_color=COLOR['texto'], progress_color=COLOR['acento'],
    button_color="#FFFFFF", button_hover_color="#E6E6E6", fg_color=COLOR['borde'],
)

try:
    if os.path.exists(ICONO_PATH):
        root.iconbitmap(ICONO_PATH)
except Exception:
    pass

# Cabecera: logotipo, nombre y estado del motor
cabecera = ctk.CTkFrame(root, fg_color="transparent")
cabecera.pack(fill="x", padx=24, pady=(20, 14))

lbl_logo = ctk.CTkLabel(cabecera, text="↓", width=46, height=46, corner_radius=23,
                        fg_color=COLOR['acento'], text_color=COLOR['sobre_acento'], font=fuente(24, "bold"))
lbl_logo.pack(side="left")

bloque_titulo = ctk.CTkFrame(cabecera, fg_color="transparent")
bloque_titulo.pack(side="left", padx=14)
ctk.CTkLabel(bloque_titulo, text="Universal Media Downloader", font=fuente(20, "bold"),
             text_color=COLOR['texto']).pack(anchor="w")
ctk.CTkLabel(bloque_titulo, text="YouTube  ·  TikTok  ·  Instagram  ·  X  ·  Facebook  ·  Reddit  ·  Twitch",
             font=fuente(12), text_color=COLOR['suave']).pack(anchor="w")

btn_check_motor = ctk.CTkButton(
    cabecera, text="ACTUALIZAR MOTOR", width=150, height=34, corner_radius=17,
    **ESTILO_BOTON_SECUNDARIO,
    command=lambda: verificar_actualizacion_motor(notificar_al_dia=True)
)
btn_check_motor.pack(side="right")
lbl_motor = ctk.CTkLabel(cabecera, text="Motor: iniciando…", font=fuente(12), text_color=COLOR['suave'])
lbl_motor.pack(side="right", padx=14)

# Cuerpo en dos columnas
cuerpo = ctk.CTkFrame(root, fg_color="transparent")
cuerpo.pack(fill="both", expand=True, padx=24, pady=(0, 22))
cuerpo.grid_columnconfigure(0, weight=1)
cuerpo.grid_columnconfigure(1, weight=0, minsize=340)
cuerpo.grid_rowconfigure(0, weight=1)

columna_izq = ctk.CTkFrame(cuerpo, fg_color="transparent")
columna_izq.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
panel_der = tarjeta(cuerpo, width=340)
panel_der.grid(row=0, column=1, sticky="nsew")


def cambiar_modo(valor):
    if valor == MODO_INDIVIDUAL:
        frame_lote.pack_forget()
        frame_individual.pack(fill="both", expand=True)
    else:
        frame_individual.pack_forget()
        frame_lote.pack(fill="both", expand=True)


seg_modo = ctk.CTkSegmentedButton(
    columna_izq, values=[MODO_INDIVIDUAL, MODO_LOTE], command=cambiar_modo,
    height=38, corner_radius=19, font=fuente(13, "bold"),
    fg_color=COLOR['panel'], selected_color=COLOR['borde_vivo'], selected_hover_color=COLOR['borde_vivo'],
    unselected_color=COLOR['panel'], unselected_hover_color=COLOR['panel2'],
    text_color=COLOR['texto'], dynamic_resizing=False, width=300,
)
seg_modo.set(MODO_INDIVIDUAL)
seg_modo.pack(anchor="w", pady=(0, 12))

contenedor_modo = ctk.CTkFrame(columna_izq, fg_color="transparent")
contenedor_modo.pack(fill="both", expand=True)
frame_individual = ctk.CTkFrame(contenedor_modo, fg_color="transparent")
frame_lote = ctk.CTkFrame(contenedor_modo, fg_color="transparent")
frame_individual.pack(fill="both", expand=True)

# Modo "Un enlace": barra de enlace
card_url = tarjeta(frame_individual)
card_url.pack(fill="x")
titulo_seccion(card_url, "Enlace").pack(anchor="w", padx=18, pady=(14, 6))

fila_url = ctk.CTkFrame(card_url, fg_color="transparent")
fila_url.pack(fill="x", padx=18, pady=(0, 16))

url_entry = ctk.CTkEntry(fila_url, placeholder_text="Pega el enlace de un video o de una playlist",
                         height=44, font=fuente(13), **dict(ESTILO_ENTRADA, corner_radius=22))
url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
url_entry.bind("<Return>", lambda e: cargar_info_video())

btn_pegar = ctk.CTkButton(fila_url, text="PEGAR", width=84, height=44, corner_radius=22,
                          **ESTILO_BOTON_SECUNDARIO, command=pegar_portapapeles_individual)
btn_pegar.pack(side="left", padx=(0, 8))

btn_buscar = ctk.CTkButton(fila_url, text="ANALIZAR", width=110, height=44, corner_radius=22,
                           fg_color=COLOR['claro'], hover_color=COLOR['claro_hover'],
                           text_color=COLOR['sobre_acento'], text_color_disabled="#6A6A6A",
                           font=fuente(13, "bold"), command=cargar_info_video)
btn_buscar.pack(side="left")

# Modo "Un enlace": vista previa
card_preview = tarjeta(frame_individual)
card_preview.pack(fill="both", expand=True, pady=(12, 0))

# Pasos de ayuda a lo ancho, en la parte baja de la tarjeta
pasos_ayuda = ctk.CTkFrame(card_preview, fg_color="transparent")
pasos_ayuda.pack(side="bottom", fill="x", padx=18, pady=(0, 18))
for _num, _texto in (("1", "Copia el enlace"), ("2", "Pulsa Analizar"), ("3", "Elige formato y descarga")):
    _paso = ctk.CTkFrame(pasos_ayuda, fg_color=COLOR['panel2'], corner_radius=8)
    _paso.pack(side="left", fill="x", expand=True, padx=(0, 8) if _num != "3" else 0)
    ctk.CTkLabel(_paso, text=_num, width=22, height=22, corner_radius=11, fg_color=COLOR['borde_vivo'],
                 text_color=COLOR['texto'], font=fuente(11, "bold")).pack(side="left", padx=(10, 8), pady=9)
    ctk.CTkLabel(_paso, text=_texto, font=fuente(12), text_color=COLOR['suave']).pack(side="left", padx=(0, 10))

fila_preview = ctk.CTkFrame(card_preview, fg_color="transparent")
fila_preview.pack(side="top", fill="both", expand=True, padx=18, pady=18)

lbl_miniatura = ctk.CTkLabel(fila_preview, text="Sin vista previa", width=TAM_MINIATURA[0],
                             height=TAM_MINIATURA[1], corner_radius=8, fg_color=COLOR['panel2'],
                             text_color=COLOR['suave'], font=fuente(12))
lbl_miniatura.pack(side="left", anchor="n")

info_preview = ctk.CTkFrame(fila_preview, fg_color="transparent")
info_preview.pack(side="left", fill="both", expand=True, padx=(18, 0))

lbl_plataforma = ctk.CTkLabel(info_preview, text="  Esperando enlace  ", height=24, corner_radius=12,
                              fg_color=COLOR['borde_vivo'], text_color=COLOR['texto'],
                              font=fuente(11, "bold"))
lbl_plataforma.pack(anchor="w")

lbl_titulo = ctk.CTkLabel(info_preview,
                          text="Pega un enlace y pulsa Analizar para ver la vista previa y las calidades disponibles.",
                          wraplength=240, justify="left", anchor="w", font=fuente(15, "bold"),
                          text_color=COLOR['texto'])
lbl_titulo.pack(anchor="w", fill="x", pady=(12, 6))

lbl_meta = ctk.CTkLabel(info_preview, text="", justify="left", anchor="w", font=fuente(12),
                        text_color=COLOR['suave'])
lbl_meta.pack(anchor="w")

# Modo "Cola por lote"
card_lote = tarjeta(frame_lote)
card_lote.pack(fill="both", expand=True)
titulo_seccion(card_lote, "Cola de enlaces").pack(anchor="w", padx=18, pady=(14, 2))
ctk.CTkLabel(card_lote, text="Un enlace por línea. Se descargan uno tras otro con las opciones de la derecha.",
             font=fuente(12), text_color=COLOR['suave']).pack(anchor="w", padx=18)

txt_lote = ctk.CTkTextbox(card_lote, corner_radius=8, fg_color=COLOR['panel2'], border_color=COLOR['borde_vivo'],
                          border_width=1, text_color=COLOR['texto'], font=fuente(12))
txt_lote.pack(fill="both", expand=True, padx=18, pady=12)
txt_lote.bind("<KeyRelease>", actualizar_contador_lote)

fila_lote = ctk.CTkFrame(card_lote, fg_color="transparent")
fila_lote.pack(fill="x", padx=18, pady=(0, 16))

btn_pegar_lote = ctk.CTkButton(fila_lote, text="PEGAR ENLACES COPIADOS", height=36, corner_radius=18,
                               **ESTILO_BOTON_SECUNDARIO, command=pegar_portapapeles_lote)
btn_pegar_lote.pack(side="left")

lbl_contador_lote = ctk.CTkLabel(fila_lote, text="0 enlace(s) en cola", font=fuente(13, "bold"),
                                 text_color=COLOR['texto'])
lbl_contador_lote.pack(side="right")

# Panel derecho: zona de acción (abajo) y opciones (arriba)
zona_accion = ctk.CTkFrame(panel_der, fg_color="transparent")
zona_accion.pack(side="bottom", fill="x", padx=20, pady=20)

lbl_estado = ctk.CTkLabel(zona_accion, text="Listo para comenzar", font=fuente(12), text_color=COLOR['suave'],
                          anchor="w", justify="left", wraplength=290)
lbl_estado.pack(fill="x")

# Sin color de progreso hasta la primera descarga, para que la barra vacía no muestre un punto
progreso_bar = ctk.CTkProgressBar(zona_accion, height=8, corner_radius=4, fg_color=COLOR['panel2'],
                                  progress_color=COLOR['panel2'])
progreso_bar.set(0)
progreso_bar.pack(fill="x", pady=(8, 14))

btn_descargar = ctk.CTkButton(zona_accion, text="DESCARGAR", height=52, corner_radius=26,
                              fg_color=COLOR['acento'], hover_color=COLOR['acento_hover'],
                              text_color=COLOR['sobre_acento'], text_color_disabled="#1A5E33",
                              font=fuente(16, "bold"), command=iniciar_descarga)
btn_descargar.pack(fill="x")

titulo_seccion(panel_der, "Formato").pack(anchor="w", padx=20, pady=(18, 6))
seg_tipo = ctk.CTkSegmentedButton(
    panel_der, values=["Video (MP4)", "Solo Audio (MP3)"], command=cambiar_tipo,
    height=38, corner_radius=19, font=fuente(13, "bold"),
    fg_color=COLOR['panel2'], selected_color=COLOR['borde_vivo'], selected_hover_color=COLOR['borde_vivo'],
    unselected_color=COLOR['panel2'], unselected_hover_color=COLOR['borde'], text_color=COLOR['texto'],
)
seg_tipo.set("Video (MP4)")
seg_tipo.pack(fill="x", padx=20)


def fila_opcion(texto, pady=(12, 0)):
    fila = ctk.CTkFrame(panel_der, fg_color="transparent")
    fila.pack(fill="x", padx=20, pady=pady)
    ctk.CTkLabel(fila, text=texto, font=fuente(13), text_color=COLOR['texto']).pack(side="left")
    return fila


menu_calidad = ctk.CTkOptionMenu(fila_opcion("Calidad", pady=(14, 0)), values=calidades_video_actuales,
                                 **ESTILO_MENU)
menu_calidad.pack(side="right")

combo_cookies = ctk.CTkOptionMenu(fila_opcion("Cookies (+18)"),
                                  values=["Desactivado", "Chrome", "Edge", "Firefox", "Brave", "Opera"],
                                  **ESTILO_MENU)
combo_cookies.pack(side="right")

combo_cookies.set("Desactivado")

frame_switches = ctk.CTkFrame(panel_der, fg_color="transparent")
frame_switches.pack(fill="x", padx=20, pady=(10, 0))
switch_playlist = ctk.CTkSwitch(frame_switches, text="Descargar la playlist completa", **ESTILO_SWITCH)
switch_playlist.pack(anchor="w")
switch_metadata = ctk.CTkSwitch(frame_switches, text="Incrustar carátula y artista en el MP3", **ESTILO_SWITCH)
switch_metadata.select()

titulo_seccion(panel_der, "Guardar en").pack(anchor="w", padx=20, pady=(18, 6))
frame_ruta = ctk.CTkFrame(panel_der, fg_color="transparent")
frame_ruta.pack(fill="x", padx=20)
ruta_var = ctk.StringVar(value=os.path.expanduser("~/Downloads"))
entry_ruta = ctk.CTkEntry(frame_ruta, textvariable=ruta_var, height=34, font=fuente(12), **ESTILO_ENTRADA)
entry_ruta.pack(side="left", fill="x", expand=True, padx=(0, 8))
btn_carpeta = ctk.CTkButton(frame_ruta, text="CAMBIAR", width=92, height=34, corner_radius=17,
                            **ESTILO_BOTON_SECUNDARIO, command=seleccionar_carpeta)
btn_carpeta.pack(side="right")

root.after(1000, lambda: verificar_actualizacion_motor(notificar_al_dia=False))

root.mainloop()
