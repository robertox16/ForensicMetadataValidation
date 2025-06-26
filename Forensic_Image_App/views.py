from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
import base64
import mimetypes
import os
import re

from django.conf import settings
from django.forms.models import model_to_dict

from DataBaseApp.models import (
    Device,
    DeviceCamera,
    Camera,
    Sensor,
    Feature,
    Media_Format
)

from .utils_exif import get_exif_data
from .utils_compare import build_field_keywords, extract_relevant_exif
from .utils_compare import compare_exif_to_device, compare_physical_vs_exif_dimensions,compare_exif_vs_file_dates, check_subsecond_consistency, check_aperture_consistency
from .generate_ela import generate_ela_datauris

from fractions import Fraction

def is_scaled_valid(db_res: str, exif_w: int, exif_h: int):
    try:
        w_db, h_db = map(int, db_res.split('x'))
    except ValueError:
        return False, "Formato BDD inválido"
    if (exif_w, exif_h) == (w_db, h_db):
        return True, "Correcto"
    if Fraction(exif_w, exif_h) == Fraction(w_db, h_db):
        return True, f"Escalado legítimo {w_db//h_db:d}:{h_db//h_db:d}"
    return False, "Discrepancia"

def welcome(request):
    return render(request, 'welcome.html')

@ensure_csrf_cookie
@csrf_protect
def analizar_imagen(request):
    """
    - Guarda N imágenes temporalmente en MEDIA_ROOT
    - Para cada imagen:
        • Extrae EXIF (agrupados por categoría).
        • Normaliza campos clave (model, make, flash, etc.) usando keywords.
        • Extrae “Model” normalizado y busca Devices cuyo campo 'model' contenga esa cadena.
        • Codifica la imagen a data URI.
        • Construye un dict con:
            { filename, data_uri, exif_fields, model, exif_grouped, device_data_list }
    - Borra los archivos subidos y renderiza results2.html con results_list.
    """

    if request.method == 'POST':
        
        files = request.FILES.getlist('imagen')
        if not files:
            return render(request, 'welcome.html', {
                'mensaje': "No se recibió ninguna imagen."
            })

        results_list = []

        for img_file in files:
            # Se almacenan temporalmente las imágenes            
            fs = FileSystemStorage()
            filename = fs.save(img_file.name, img_file)
            filepath = fs.path(filename)

            # Leer archivo y codificar a Data URI (base64)
            mime_type, _ = mimetypes.guess_type(filepath)
            if not mime_type:
                mime_type = 'application/octet-stream'
            with open(filepath, "rb") as f:
                raw_data = f.read()
            b64_data = base64.b64encode(raw_data).decode('utf-8')
            data_uri = f"data:{mime_type};base64,{b64_data}"
            
            # ELA
            try:
                ela_dict = generate_ela_datauris(filepath)
            except Exception as e:
                ela_dict = {} 


            try:
                metadatos_dict, total, real_w, real_h, exif_w, exif_h = get_exif_data(filepath)
                dimension_check = compare_physical_vs_exif_dimensions(real_w, real_h, exif_w, exif_h)
                date_check = compare_exif_vs_file_dates(metadatos_dict)
                subsec_check = check_subsecond_consistency(metadatos_dict)
                aperture_check = check_aperture_consistency(metadatos_dict)
            except Exception:
                metadatos_dict = {}
                dimension_check = None
                date_check = None
                subsec_check = None
                aperture_check = None


            
            # Normalizar campos clave usando keyword
            field_kws = build_field_keywords()
            exif_fields = extract_relevant_exif(metadatos_dict, field_kws)

            
            # Agrupar EXIF por categoría
            exif_grouped = {}
            for full_key, value in metadatos_dict.items():
                if ":" in full_key:
                    category, subkey = full_key.split(":", 1)
                else:
                    category, subkey = "OTHER", full_key
                exif_grouped.setdefault(category, {})[subkey] = value

            
            model_name = None
            if exif_fields.get("model"):
                model_name = exif_fields["model"]

            stripped_model = model_name
            used_fallback   = False
            
            # Búsqueda modelo
            device_data_list = []
            if model_name:

                make_name  = exif_fields.get("make", "").strip()
                model_name = exif_fields.get("model", "").strip()

                qs = Device.objects.filter(model__icontains=model_name)

                if not qs.exists() and make_name and model_name:
                    pattern = r'^' + re.escape(make_name) + r'\s*'
                    tmp = re.sub(pattern, '', model_name, flags=re.IGNORECASE).strip()
                    if tmp:
                        stripped_model = tmp
                        qs = Device.objects.filter(model__icontains=stripped_model)
                        used_fallback = qs.exists()

                
                if qs.exists():
                    dispositivo = qs.first()
                else:
                   
                    dispositivo = None



                for device in qs:
                    # Campos básicos de Device
                    campos_device = [
                        "codename", "category", "platform", "os",
                        "url", "flash", "model"
                    ]
                    device_dict = model_to_dict(device, fields=campos_device)
                    device_dict["display_width_px"]  = device.display_width_px
                    device_dict["display_height_px"] = device.display_height_px
                    device_dict["brand"] = device.brand.name

                    # Se recorren las cámaras asociadas
                    camaras = []
                    for enlace in DeviceCamera.objects.filter(device=device):
                        cam = enlace.camera
                        cam_dict = model_to_dict(cam, fields=[
                            "type", "resolution", "num_pixels", "aperture",
                            "MEFL", "focus", "zoom", "placement", "display_width_px", "display_height_px"
                        ])
                        cam_dict["display_width_px"]  = device_dict.get("display_width_px")
                        cam_dict["display_height_px"] = device_dict.get("display_height_px")
                        
                        if cam.sensor:
                            sensor = cam.sensor
                            cam_dict["sensor"] = model_to_dict(sensor, fields=[
                                "sensor_type", "sensor_format", "pixel_size"
                            ])
                        else:
                            cam_dict["sensor"] = None

                        
                        features_qs = cam.features.all()
                        if features_qs.exists():
                            nombres = [f.name for f in features_qs]
                            cam_dict["features"] = ", ".join(nombres)
                        else:
                            cam_dict["features"] = ""

                        
                        mf_qs = cam.media_formats.all()
                        if mf_qs.exists():
                            fotos_qs = mf_qs.filter(format_type="Photo")
                            vids_qs  = mf_qs.filter(format_type="Video")

                           
                            if fotos_qs.exists():
                                foto_exts = [m.format_extension for m in fotos_qs]
                                cam_dict["image_formats"] = ", ".join(foto_exts)
                            else:
                                cam_dict["image_formats"] = ""

                            
                            if vids_qs.exists():
                                vid_exts = [m.format_extension for m in vids_qs]
                                cam_dict["video_formats"] = ", ".join(vid_exts)
                            else:
                                cam_dict["video_formats"] = ""
                        else:
                            cam_dict["image_formats"] = ""
                            cam_dict["video_formats"] = ""

                        exif_w = exif_fields.get("image_width")
                        exif_h = exif_fields.get("image_height")
                        if exif_w and exif_h and cam_dict.get("resolution"):
                            valido, msg = is_scaled_valid(
                                cam_dict["resolution"],
                                int(exif_w),
                                int(exif_h)
                            )
                            cam_dict["resolution_valid"] = valido
                            cam_dict["resolution_msg"]   = msg
                        else:
                            cam_dict["resolution_valid"] = None
                            cam_dict["resolution_msg"]   = "(sin datos)"
                        

                        camaras.append(cam_dict)

                    device_dict["cameras"] = camaras
                    device_data_list.append(device_dict)

            
            
            comp_thresholds = {
                "aperture_warning": 0.2,
                "aperture_error":   0.5
            }
            comparison_reports = [
                compare_exif_to_device(exif_fields, dev_dict, comp_thresholds)
                for dev_dict in device_data_list
            ]

            
            if used_fallback:
                for rpt in comparison_reports:
                    
                    model_cmp = rpt["device"].get("model")
                    if model_cmp and model_cmp["status"] is False:
                       
                        model_cmp["status"] = True

                        color = "#4aa3df"
                        pattern = re.escape(stripped_model)
                        def _hl(m):
                            return f'<span style="color: {color};">{m.group(0)}</span>'
                        highlighted = re.sub(pattern,
                                            _hl,
                                            model_cmp["db_raw"],
                                            flags=re.IGNORECASE)
                        model_cmp["highlighted"] = highlighted

            
            # Añadir al listado de resultados 
            
            results_list.append({
                "filename":          filename,
                "data_uri":          data_uri,
                "ela": ela_dict,
                "exif_fields":       exif_fields,
                "model":             model_name,
                "stripped_model":    stripped_model,
                "used_fallback":     used_fallback,
                "exif_grouped":      exif_grouped,
                "device_data_list":  device_data_list,
                "comparison_reports": comparison_reports,
                "dimension_check":   dimension_check,
                "date_check": date_check,
                "subsec_check": subsec_check,
                "aperture_check": aperture_check
            })

      
        # Borrar archivos temporales
      
        for item in results_list:
            nombre_fichero = item["filename"]
            ruta_absoluta = os.path.join(settings.MEDIA_ROOT, nombre_fichero)
            if os.path.exists(ruta_absoluta):
                try:
                    os.remove(ruta_absoluta)
                except Exception:
                    pass

        
        #  Calcular cámara más proable 
        
        for item in results_list:
            comp_reports = item.get("comparison_reports", [])
            dev_list     = item.get("device_data_list", [])

            for dev_idx, dev_dict in enumerate(dev_list):
                if dev_idx >= len(comp_reports):
                    continue

                report     = comp_reports[dev_idx]
                cam_reports = report.get("cameras", [])

                # Calculamos el score para cada cámara
                scores = []
                for cam_report in cam_reports:
                    comps = cam_report.get("comparisons", {})
                    sc = sum(1 for cmp_dict in comps.values() if cmp_dict.get("status") is True)
                    scores.append(sc)

                # Determinamos el/los índice(s) con puntuación máxima
                if scores:
                    max_score = max(scores)
                    best_idxs = [i for i, sc in enumerate(scores) if sc == max_score]
                    # Guardamos todos los índices empatados
                    report["best_cam_idxs"] = best_idxs
                    # Para compatibilidad, también guardamos el primero
                    report["best_cam_idx"]  = best_idxs[0]
                else:
                    report["best_cam_idxs"] = []
                    report["best_cam_idx"]  = None


            # AGRUPAR DISPOSITIVOS POR NÚMERO DE COINCIDENCIAS
            match_counts = []
            for idx, report in enumerate(comp_reports):
                bi = report.get("best_cam_idx")
                if bi is None:
                    match_counts.append(0)
                else:
                    comps = report["cameras"][bi]["comparisons"]
                    match_counts.append(sum(1 for c in comps.values() if c.get("status") is True))

            # Agrupamos índices de dispositivo por su match_count
            groups = {}
            for idx, cnt in enumerate(match_counts):
                groups.setdefault(cnt, []).append(idx)

            item["grouped_devices"] = sorted(groups.items(), key=lambda x: x[0], reverse=True)


        return render(request, "results2.html", {
            "results_list": results_list
        })

    return render(request, 'welcome.html')


# Vista para mostrar resultados directos vía GET
def results(request):
    model_name = request.GET.get('model')
    filename   = request.GET.get('filename')

    exif_data = {}
    if filename:
        filepath = os.path.join(settings.MEDIA_ROOT, filename)
        try:
            exif_data, total = get_exif_data(filepath)
        except Exception:
            exif_data = {}

    # Agrupar EXIF por categoría
    exif_grouped = {}
    for full_key, value in exif_data.items():
        if ":" in full_key:
            category, subkey = full_key.split(":", 1)
        else:
            category, subkey = "OTHER", full_key

        if category not in exif_grouped:
            exif_grouped[category] = {}
        exif_grouped[category][subkey] = value

    # Obtener datos del Device en BD 
    device_data = None
    if model_name:
        try:
            device = Device.objects.get(model__iexact=model_name)
            campos_device = [
                "codename", "category", "platform", "os",
                "url", "flash", "model"
            ]
            # lógica FULL
            device_dict = model_to_dict(device, fields=campos_device)
            device_dict["display_width_px"]  = device.display_width_px
            device_dict["display_height_px"] = device.display_height_px
            device_dict["brand"] = device.brand.name

            camaras = []
            for enlace in DeviceCamera.objects.filter(device=device):
                cam = enlace.camera
                cam_dict = model_to_dict(cam, fields=[
                    "type", "resolution", "num_pixels", "aperture",
                    "MEFL", "focus", "zoom", "placement", "display_width_px", "display_height_px"
                ])
                cam_dict["display_width_px"]  = device_dict.get("display_width_px")
                cam_dict["display_height_px"] = device_dict.get("display_height_px")
                
                if cam.sensor:
                    sensor = cam.sensor
                    cam_dict["sensor"] = model_to_dict(sensor, fields=[
                        "sensor_type", "sensor_format", "pixel_size"
                    ])
                else:
                    cam_dict["sensor"] = None

                
                features_qs = cam.features.all()
                cam_dict["features"] = [f.name for f in features_qs]

                mf_qs = cam.media_formats.all()
                if mf_qs.exists():
                    fotos_qs = mf_qs.filter(format_type="Photo")
                    vids_qs  = mf_qs.filter(format_type="Video")

                    if fotos_qs.exists():
                        cam_dict["image_formats"] = [m.format_extension for m in fotos_qs]
                    else:
                        cam_dict["image_formats"] = []

                    if vids_qs.exists():
                        cam_dict["video_formats"] = [m.format_extension for m in vids_qs]
                    else:
                        cam_dict["video_formats"] = []
                else:
                    cam_dict["image_formats"] = []
                    cam_dict["video_formats"] = []

                # Validación de resolución escalada para TODAS las cámaras
                exif_w = exif_fields.get("image_width")
                exif_h = exif_fields.get("image_height")
                if exif_w and exif_h and cam_dict.get("resolution"):
                    valido, msg = is_scaled_valid(
                        cam_dict["resolution"],
                        int(exif_w),
                        int(exif_h)
                    )
                    cam_dict["resolution_valid"] = valido
                    cam_dict["resolution_msg"]   = msg
                else:
                    cam_dict["resolution_valid"] = None
                    cam_dict["resolution_msg"]   = "(sin datos)"


                camaras.append(cam_dict)

            device_dict["cameras"] = camaras
            device_data = device_dict

        except Device.DoesNotExist:
            device_data = None

    return render(request, "results2.html", {
        "model":        model_name,
        "exif_grouped": exif_grouped,
        "device_data":  device_data
    })


