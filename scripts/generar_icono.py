#!/usr/bin/env python3
"""Genera icono.ico e icono_preview.png. Requiere Pillow. (Propuesta de Codex.)"""

import argparse
import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw

TAMANOS = (16, 20, 24, 32, 40, 48, 64, 128, 256)
ESCALA = 8  # Cuadrícula de diseño: 256; lienzo: 2048.
VERDE = "#1ED760"
NEGRO = "#000000"


def crear_original():
    lado = 256 * ESCALA
    imagen = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)

    # El límite derecho/inferior es inclusivo en Pillow.
    dibujo.ellipse(
        (16 * ESCALA, 16 * ESCALA,
         240 * ESCALA - 1, 240 * ESCALA - 1),
        fill=VERDE,
    )

    # Asta y punta forman un único polígono, sin fuentes.
    puntos = (
        (108, 64),
        (148, 64),
        (148, 128),
        (184, 128),
        (128, 192),
        (72, 128),
        (108, 128),
    )
    dibujo.polygon(
        [(x * ESCALA, y * ESCALA) for x, y in puntos],
        fill=NEGRO,
    )
    return imagen


def guardar_ico(ruta, imagenes):
    """ICO de 32 bits con una imagen PNG por resolución."""
    bloques = []
    for imagen in imagenes:
        memoria = io.BytesIO()
        imagen.save(memoria, format="PNG")
        bloques.append(memoria.getvalue())

    desplazamiento = 6 + 16 * len(imagenes)
    with ruta.open("wb") as archivo:
        archivo.write(struct.pack("<HHH", 0, 1, len(imagenes)))
        for imagen, bloque in zip(imagenes, bloques):
            ancho, alto = imagen.size
            archivo.write(struct.pack(
                "<BBBBHHII",
                ancho if ancho < 256 else 0,
                alto if alto < 256 else 0,
                0, 0, 1, 32, len(bloque), desplazamiento,
            ))
            desplazamiento += len(bloque)
        for bloque in bloques:
            archivo.write(bloque)


def main():
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("salida", type=Path,
                            help="Carpeta donde guardar los archivos")
    salida = argumentos.parse_args().salida.expanduser()
    salida.mkdir(parents=True, exist_ok=True)

    original = crear_original()
    imagenes = [
        original.resize((n, n), Image.Resampling.LANCZOS)
        for n in TAMANOS
    ]
    guardar_ico(salida / "icono.ico", imagenes)
    imagenes[-1].save(salida / "icono_preview.png")

    with Image.open(salida / "icono.ico") as comprobacion:
        assert comprobacion.ico.sizes() == {(n, n) for n in TAMANOS}

    print(f"Generados y tamaños verificados en: {salida.resolve()}")


if __name__ == "__main__":
    main()
