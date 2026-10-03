# Firma digital de desarrollo

Este proyecto utiliza un **certificado autofirmado**, creado localmente por el mantenedor. No se utiliza SignPath ni se solicita una firma a un servicio externo.

Una firma de desarrollo permite identificar el certificado con el que se firmó el archivo y detectar cambios posteriores. No constituye una identidad de editor verificada por una autoridad certificadora. Windows puede mostrar **«Windows protegió su PC»** o **«Editor desconocido»**. PowerShell puede informar `NotTrusted` o `UnknownError` con un mensaje de raíz no confiable; el código nativo `0x800B0109` identifica esa situación.

## Certificado y clave privada

- El certificado público está en [`certificates/UniversalDownloader-development.cer`](../certificates/UniversalDownloader-development.cer).
- Su huella y vigencia están en [`certificates/signing-info.json`](../certificates/signing-info.json).
- La clave privada permanece en el almacén personal de certificados del usuario que realizó la firma (`CurrentUser\My`), con exportación deshabilitada.
- El script no instala certificados en los almacenes de raíces de confianza ni modifica SmartScreen.
- El script verifica la firma sin acceso a la red y acepta únicamente una firma válida o el error específico de raíz autofirmada no confiable. Otros errores, incluido un contenido modificado, interrumpen el proceso.
- La firma se realiza sin conexión a un servicio de sellado de tiempo. Después del vencimiento del certificado, Windows puede dejar de aceptar su vigencia.
- El certificado público por sí solo no permite firmar nuevas versiones.

## Compilar y firmar (Windows)

Instala las dependencias de `requirements-dev.txt`, coloca FFmpeg junto al código e instala Inno Setup y las herramientas de firma del Windows SDK.

En PowerShell, desde la raíz del repositorio:

```powershell
python -m PyInstaller --clean --noconfirm app_descargador.spec
.\scripts\sign-local.ps1 -FilePath .\dist\app_descargador.exe
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" .\instalador.iss
.\scripts\sign-local.ps1 -FilePath .\dist_instalador\Instalador_UniversalDownloader_v1.0.exe
Get-FileHash .\dist_instalador\Instalador_UniversalDownloader_v1.0.exe -Algorithm SHA256
```

Ajusta la ruta de Inno Setup según su instalación. El orden es necesario: primero se firma la aplicación, después se incluye en el instalador y finalmente se firma el instalador. Calcula y publica el SHA256 **después** de firmarlo.

En la primera ejecución, si no hay una huella registrada, el script crea el certificado. En ejecuciones posteriores utiliza esa misma huella y necesita acceso a su clave privada en el equipo del mantenedor. Una copia del repositorio en otro equipo no puede reutilizar la clave.

## Comprobar una descarga

```powershell
Get-FileHash .\Instalador_UniversalDownloader_v1.0.exe -Algorithm SHA256
Get-AuthenticodeSignature .\Instalador_UniversalDownloader_v1.0.exe |
    Select-Object Status, @{Name='Thumbprint'; Expression={$_.SignerCertificate.Thumbprint}}
```

Compara el SHA256 con el adjunto de la publicación y la huella con `signing-info.json`. Estas comprobaciones no sustituyen un análisis antivirus ni garantizan por sí solas la seguridad del programa.

Referencia: [SmartScreen y certificados autofirmados, Microsoft](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).
