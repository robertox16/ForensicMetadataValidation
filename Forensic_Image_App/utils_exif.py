import subprocess
import json
import os
from django.conf import settings

def get_exif_data(image_path):
    """
    Llama a ExifTool (desde tools/exiftool.exe o tools/exiftool) para extraer
    todos los metadatos en formato JSON. Devuelve un diccionario con todos los
    tags y el número total de claves
    """
    if os.name == 'nt':
        exiftool_name = "exiftool.exe"
    else:
        exiftool_name = "exiftool"
    exiftool_path = os.path.join(settings.BASE_DIR, "tools", exiftool_name)

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"La imagen no existe en la ruta: {image_path}")
    
    if not os.path.exists(exiftool_path):
        raise FileNotFoundError(f"ExifTool no se encuentra en la ruta: {exiftool_path}")

    result = subprocess.run(
        [exiftool_path, "-j", "-a", "-u", "-ee", "-G", image_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Error al ejecutar exiftool: {result.stderr}")
      
    metadata_list = json.loads(result.stdout)

    if metadata_list:
        metadata_dict = metadata_list[0]
    else:
        metadata_dict = {}

    # Dimensiones reales
    real_width = metadata_dict.get("File:ImageWidth")
    real_height = metadata_dict.get("File:ImageHeight")

    # Extraemos dimensiones EXIF
    exif_width = metadata_dict.get("EXIF:ImageWidth")
    exif_height = metadata_dict.get("EXIF:ImageHeight")

    metadata_count = len(metadata_dict)
    return metadata_dict, metadata_count, real_width, real_height, exif_width, exif_height