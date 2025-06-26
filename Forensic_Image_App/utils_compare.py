# utils_compare.py

import re
import math
# Agregamos esta lista de “aspectos habituales” como constantes:
COMMON_RATIOS = [
    ("4:3", 4/3),
    ("16:9", 16/9),
    ("3:2", 3/2),
    ("1:1", 1.0),
    ("2:1", 2.0),       # equivalente a 18:9 o 2:1
    ("19.5:9", 19.5/9), # ratio iPhone “full screen”
]

def build_field_keywords():
    """
    Devuelve un diccionario donde la clave es el nombre 'canónico' de
    cada campo que nos interesa, y el valor es una lista de keywords
    (en minúsculas) que consideramos equivalentes para ese campo.
    """
    return {
        "model": [
            "model",
            "xiaomimodel",
            "iphonemodel",
            "phone:model",
            "device:model"
        ],
        
        "file_format": [
            "filetypeextension",
            "filetype",
            "mimetype"
        ],
        "make": [
            "make",
            "manufacturer"
        ],
        "placement": [
            "sensortype",
            "camera:sensortype",
            "sensor:type"
        ],
        "sensor_format": [
            "imagesensorformat",
            "sensorformat",
            "camera:sensorformat"
        ],
        "pixel_size": [
            "imagesensorpixelsize",
            "pixelxsize",
            "sensorpixelsize"
        ],
        "image_width": [
            "imagewidth",
            "imagesizewidth"
        ],
        "image_height": [
            "imageheight",
            "imagesizeheight"
        ],
        "fnumber": [
            "fnumber",
            "aperturevalue",
            "aperture"
        ],

        "focal_length_real": [
           "focallength"   
       ],
        "focal_length_35mm": [
            "focallengthin35mmformat",
            "min. equiv. focallength",
            
        ],
        "zoom_multiple": [
            "zoommultiple",
            "zoom"
        ],
        "scale_factor35efl": [
            "scalefactor35efl"
        ],
    }


def extract_relevant_exif(exif_dict, field_keywords=None):
    """
    Recorre el dict exif_dict y, para cada campo 'canónico' en field_keywords, 
    busca la primera etiqueta en exif_dict cuya clave contenga
    alguna de las keywords asignadas. 
    """
    if field_keywords is None:
        field_keywords = build_field_keywords()

    resultado = {campo: None for campo in field_keywords.keys()}
    lowercase_exif = {clave.lower(): valor for clave, valor in exif_dict.items()}

    for campo, keywords in field_keywords.items():
        for kw in keywords:
            for exif_key_lower, valor in lowercase_exif.items():
                if kw in exif_key_lower:
                    resultado[campo] = valor
                    break
            if resultado[campo] is not None:
                break
    return resultado


def _extract_first_float(text):   
    if text is None:
        return None
    s = str(text).strip().lower().replace(',', '.')
    m = re.search(r'(-?\d+(\.\d+)?)', s)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None





def normalize_aperture(raw):
    if raw is None:
        return None
    s = str(raw).strip().lower()
    # Quitamos prefijo "f/" si existe
    s = re.sub(r'^(f\/?)', '', s)
    return _extract_first_float(s)


def normalize_focal_length(raw):
    if raw is None:
        return None
    s = str(raw).strip().lower().replace('mm', '')
    return _extract_first_float(s)


def normalize_zoom(raw):
    if raw is None:
        return None
    s = str(raw).strip().lower()
    s = s.replace('optical zoom', '').replace('x', '')
    return _extract_first_float(s)


def normalize_resolution(db_resolution=None, exif_w=None, exif_h=None):
    try:
        if exif_w is not None and exif_h is not None:
            return (int(exif_w), int(exif_h))
    except (ValueError, TypeError):
        pass

    if db_resolution:
        s = str(db_resolution).strip().lower()
        m = re.search(r'(\d+)\s*[x×]\s*(\d+)', s)
        if m:
            try:
                return (int(m.group(1)), int(m.group(2)))
            except ValueError:
                return None
    return None


def normalize_string(raw):
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None


def compare_strings(a, b):
    if a is None or b is None:
        return None
    sa = str(a).strip().lower()
    sb = str(b).strip().lower()
    return sa == sb

from datetime import datetime

def compare_exif_vs_file_dates(exif_dict):
    exif_date_str = exif_dict.get("EXIF:DateTimeOriginal")
    file_date_str = exif_dict.get("EXIF:ModifyDate:")

    def parse_date(s):
        try:
            return datetime.strptime(s[:19], "%Y:%m:%d %H:%M:%S")
        except:
            return None

    exif_date = parse_date(exif_date_str)
    file_date = parse_date(file_date_str)

    if not exif_date or not file_date:
        return {
            "status": None,
            "exif": exif_date_str,
            "file": file_date_str,
            "note": "Fechas no disponibles o mal formateadas"
        }

    diff = abs((file_date - exif_date).total_seconds())
    dias = diff / 86400

    return {
        "status": dias < 1,  # Por ejemplo, toleramos < 1 día
        "exif": exif_date_str,
        "file": file_date_str,
        "note": f"Diferencia de {dias:.2f} días entre EXIF y archivo"
    }

def check_subsecond_consistency(exif_dict):
    sub1 = exif_dict.get("EXIF:SubSecTime")
    sub2 = exif_dict.get("EXIF:SubSecTimeOriginal")
    sub3 = exif_dict.get("EXIF:SubSecTimeDigitized")

    all_present = all([sub1, sub2, sub3])
    all_equal = sub1 == sub2 == sub3

    return {
        "status": not (all_present and all_equal),
        "SubSecTime": sub1,
        "SubSecTimeOriginal": sub2,
        "SubSecTimeDigitized": sub3,
        "note": "Los tres campos son idénticos" if all_equal else "Hay variación o campos ausentes"
    }

def check_aperture_consistency(exif_dict):
    try:
        fnum = float(exif_dict.get("EXIF:FNumber", 0))
        max_ap = float(exif_dict.get("EXIF:MaxApertureValue", 0))
        if fnum == 0 or max_ap == 0:
            return {
                "status": None,
                "fnumber": fnum,
                "max_aperture": max_ap,
                "note": "Faltan datos o son cero"
            }
        return {
            "status": fnum >= max_ap,
            "fnumber": fnum,
            "max_aperture": max_ap,
            "note": "Correcto" if fnum <= max_ap else "FNumber menor que la apertura máxima"
        }
    except:
        return {
            "status": None,
            "fnumber": exif_dict.get("EXIF:FNumber"),
            "max_aperture": exif_dict.get("EXIF:MaxApertureValue"),
            "note": "No se pudo analizar"
        }

def compare_physical_vs_exif_dimensions(real_w, real_h, exif_w, exif_h):
    try:
        rw = int(real_w)
        rh = int(real_h)
        ew = int(exif_w)
        eh = int(exif_h)
    except (TypeError, ValueError):
        return {
            "real_width": real_w,
            "real_height": real_h,
            "exif_width": exif_w,
            "exif_height": exif_h,
            "status": None,
            "note": "Dimensiones no válidas o faltantes"
        }

    status = (rw == ew) and (rh == eh)
    return {
        "real_width": rw,
        "real_height": rh,
        "exif_width": ew,
        "exif_height": eh,
        "status": status,
        "note": "Coinciden" if status else "Discrepancia entre EXIF y dimensiones reales"
    }


def compare_numeric(a, b, threshold=0.1):
    if a is None or b is None:
        return None
    try:
        diff = abs(float(a) - float(b))
    except (ValueError, TypeError):
        return None
    return diff <= threshold


def compare_resolution(exif_res, db_res, aspect_tolerance=0.02):
    

    if exif_res is None or db_res is None:
        return None, None

    try:
        ex_w, ex_h = exif_res

        # Calculamos el ratio EXIF independientemente de orientación
        ratio_ex = max(ex_w, ex_h) / min(ex_w, ex_h)

        # Si coincide (dentro de tolerance) con cualquiera de los COMMON_RATIOS es correcto
        for label, ratio in COMMON_RATIOS:
            if abs(ratio_ex - ratio) <= aspect_tolerance:
                return True, label

        # Si no coincide con ninguno discrepancia
        return False, None

    except Exception:
        return None, None



def compare_device_level(exif_fields, device_dict,
                         model_substring_color="#4aa3df",
                         focal_tol=3.0):
    resultado = {}

    ex_m = normalize_string(exif_fields.get("model"))
    db_m = normalize_string(device_dict.get("model"))
    model_cmp = {
        "db_raw": db_m,
        "exif_raw": ex_m,
        "status": None,
        "highlighted": db_m  
    }
    if ex_m and db_m:
        if ex_m.lower() in db_m.lower():
            model_cmp["status"] = True
            
            pattern = re.escape(ex_m)
            def repl(match):
                return f'<span style="color: {model_substring_color};">{match.group(0)}</span>'
            highlighted = re.sub(pattern, repl, db_m, flags=re.IGNORECASE)
            model_cmp["highlighted"] = highlighted
        else:
            model_cmp["status"] = False
            model_cmp["highlighted"] = db_m
    resultado["model"] = model_cmp


    ex_make = normalize_string(exif_fields.get("make"))
    db_make = normalize_string(device_dict.get("brand"))
    make_cmp = {
        "db_raw": db_make,
        "exif_raw": ex_make,
        "status": compare_strings(ex_make, db_make)
    }
    resultado["make"] = make_cmp

  

    return resultado


def compare_camera_level(exif_fields, camera_dict, thresholds=None):
    if thresholds is None:
        thresholds = {
            "fnumber": 0.05,
            "focal_length_35mm": 3.0,
            "zoom_multiple": 0.1,
        }

    resultado = {}

    ex_sens = normalize_string(exif_fields.get("sensor_type"))
    db_sens = normalize_string(camera_dict.get("sensor", {}).get("sensor_type"))
    sens_cmp = {
        "db_raw": db_sens,
        "exif_raw": ex_sens,
        "status": compare_strings(ex_sens, db_sens)
    }
    resultado["sensor_type"] = sens_cmp


    ex_fmt = normalize_string(exif_fields.get("sensor_format"))
    db_fmt = normalize_string(camera_dict.get("sensor", {}).get("sensor_format"))
    fmt_cmp = {
        "db_raw": db_fmt,
        "exif_raw": ex_fmt,
        "status": compare_strings(ex_fmt, db_fmt)
    }
    resultado["sensor_format"] = fmt_cmp

  
    ex_pix = normalize_string(exif_fields.get("pixel_size"))
    db_pix = normalize_string(camera_dict.get("sensor", {}).get("pixel_size"))
    pix_cmp = {
        "db_raw": db_pix,
        "exif_raw": ex_pix,
        "status": compare_strings(ex_pix, db_pix)
    }
    resultado["pixel_size"] = pix_cmp


    ex_w = exif_fields.get("image_width")
    ex_h = exif_fields.get("image_height")
    ex_res = normalize_resolution(None, ex_w, ex_h)

    #  cámara vs COMMON_RATIOS
    db_res = normalize_resolution(camera_dict.get("resolution"), None, None)
    res_status, res_matched = compare_resolution(ex_res, db_res, aspect_tolerance=0.02)

    # 2) modo FULL 
    disp_w = camera_dict.get("display_width_px")
    disp_h = camera_dict.get("display_height_px")
    if (res_status is False or res_status is None) and ex_res and disp_w and disp_h:
        #Match exacto de FULL
        if ex_res == (disp_w, disp_h) or ex_res == (disp_h, disp_w):
            res_status = True
            res_matched = "full"
        else:
            # Match por aspect-ratio 
            try:
                ratio_ex = max(ex_res) / min(ex_res)
                display_ratio = disp_h / disp_w
                if abs(ratio_ex - display_ratio) <= 0.01:
                    res_status = True
                    res_matched = "FULL frame"
                else:
                    res_status = False
                    res_matched = None
            except Exception:
                pass

    res_cmp = {
        "db_raw": camera_dict.get("resolution"),
        "exif_raw": ex_res,
        "status": res_status,
        "matched_ratio": res_matched  # "4:3", "16:9", "full" o None
    }
    resultado["resolution"] = res_cmp

   
    ex_np = normalize_string(exif_fields.get("num_pixels"))
    db_np = normalize_string(camera_dict.get("num_pixels"))
    np_cmp = {
        "db_raw": db_np,
        "exif_raw": ex_np,
        "status": compare_strings(ex_np, db_np)
    }
    resultado["num_pixels"] = np_cmp


    ex_ap = normalize_aperture(exif_fields.get("fnumber"))
    db_ap = normalize_aperture(camera_dict.get("aperture"))
    ap_note = None
    if ex_ap is None or db_ap is None or ex_ap <= 0 or db_ap <= 0:
        ap_status = None
    else:
        # Δ stops = 2 · log2(F_ex / F_db)
        delta_stops = 2 * math.log2(ex_ap / db_ap)
        abs_delta = abs(delta_stops)
        # umbrales (en stops) — pueden venir desde thresholds
        warn_thr = (thresholds or {}).get("aperture_warning", 0.2)
        error_thr = (thresholds or {}).get("aperture_error",   0.5)

        if abs_delta <= warn_thr:
            # dentro de tolerancia estricta
            ap_status = True
            # si además el EXIF fue más abierto (delta_stops < 0),
            # ponemos una nota amarilla explicando F-stop vs T-stop
            if delta_stops < 0:
                ap_note = (
                    f"⚠️ Apertura EXIF ({ex_ap:.2f}) más abierta que BDD ({db_ap:.2f}). "
                    
                )
        elif abs_delta <= error_thr:
            # entre warn_thr y error_thr → aviso
            ap_status = True
            ap_note = f"⚠️ Diferencia de apertura de {abs_delta:.2f} stops (≤ {error_thr} stops)"
        else:
            # > error_thr → error real
            ap_status = False
            ap_note = f"✖️ Desviación de apertura de {abs_delta:.2f} stops (> {error_thr} stops)"

    ap_cmp = {
        "db_raw":   camera_dict.get("aperture"),
        "exif_raw": exif_fields.get("fnumber"),
        "status":   ap_status,
        "note":     ap_note
    }
    resultado["aperture"] = ap_cmp

  

    ex_zoom = normalize_zoom(exif_fields.get("zoom_multiple"))
    f_real  = normalize_focal_length(exif_fields.get("focal_length_real"))
    f35     = _extract_first_float(exif_fields.get("focal_length_35mm"))

    fl_status = None
    db_raw    = None
    fl_note   = None

    
    db_focal = normalize_focal_length(camera_dict.get("MEFL"))
    if f35 is not None and db_focal is not None:
        if abs(f35 - db_focal) <= thresholds.get("focal_length_35mm", 2.0):
            fl_status = True
            db_raw    = camera_dict.get("MEFL")
        else:
          
            if ex_zoom is not None and ex_zoom < 1.0:
                try:
                    W_px = int(exif_fields.get("image_width") or 0)
                    H_px = int(exif_fields.get("image_height") or 0)
                    # Toma pixel_size de la cámara auxiliar
                    aux_cam = next(
                        (c for c in camera_dict.get("all_cameras", [])
                         if c.get("type") == "Aux. Camera"),
                        None
                    )
                    pix_um = _extract_first_float(
                        aux_cam.get("sensor", {}).get("pixel_size")
                    ) if aux_cam else None
                    if W_px and H_px and pix_um and f_real is not None:
                        ancho_mm   = W_px * pix_um / 1000.0
                        alto_mm    = H_px * pix_um / 1000.0
                        diag_mm    = math.hypot(ancho_mm, alto_mm)
                        crop       = 43.3 / diag_mm if diag_mm else None
                        mefl_calc  = f_real * crop if crop else None
                        mefl_round = round(mefl_calc) if mefl_calc is not None else None
                        if mefl_round is not None:
                            # tolerancia ±2 mm en dinámico
                            fl_status = abs(mefl_round - f35) <= 2.0
                            db_raw    = f"{mefl_round} mm (calc. aux ±2 mm)"
                            fl_note   = "⚠️ MEFL calculado dinámicamente; validar posible manipulación"
                except:
                    pass

            # Zoom ≃ 1: recálculo con principal
            elif ex_zoom is not None and abs(ex_zoom - 1.0) < 1e-2:
                # ─ Recalculo con crop real (ScaleFactor35efl) en lugar del sensor teórico
                scale = _extract_first_float(exif_fields.get("scale_factor35efl"))
                if scale is not None and f_real is not None:
                    mefl_calc  = f_real * scale
                    mefl_round = round(mefl_calc)
                    fl_status  = abs(mefl_round - f35) <= 2.0
                    db_raw     = f"{mefl_round} mm (calc. SF ±2 mm)"
                    fl_note   = "⚠️ MEFL calculado dinámicamente; validar posible manipulación"

            # zoom > 1 (tele/digital): no hay recálculo, dejamos fl_status=False

    # Si nunca se estableció db_raw, mantenemos lo original
        resultado["MEFL"] = {
        "db_raw":   db_raw,
        "exif_raw": exif_fields.get("focal_length_35mm"),
        "status":   fl_status,
        "note":     fl_note
    }


    zm_cmp = {
        "db_raw": camera_dict.get("zoom"),
        "exif_raw": exif_fields.get("zoom_multiple"),
        "status": None    # Desactivada la comparación de zoom
    }
    resultado["zoom"] = zm_cmp


    ex_focus = normalize_string(exif_fields.get("focus"))
    db_focus = normalize_string(camera_dict.get("focus"))
    focus_cmp = {
        "db_raw": db_focus,
        "exif_raw": ex_focus,
        "status": compare_strings(ex_focus, db_focus)
    }
    resultado["focus"] = focus_cmp

    


    ex_place = normalize_string(exif_fields.get("placement"))
    db_place = normalize_string(camera_dict.get("placement"))
    place_cmp = {
        "db_raw": db_place,
        "exif_raw": ex_place,
        "status": compare_strings(ex_place, db_place)
    }
    resultado["placement"] = place_cmp


    ex_fmt = normalize_string(exif_fields.get("file_format"))

    # Construimos la lista de formatos permitidos
    db_fmts = camera_dict.get("image_formats") or []
    if isinstance(db_fmts, str):
        db_fmts = [normalize_string(s) for s in db_fmts.split(",")]
    db_norm = [s for s in db_fmts if s]

    fmt_ok = None
    note = None
    if ex_fmt is not None:
        ex_low = ex_fmt.lower()
        if ex_low == "heic":
            # Si BD admite HEIF → válido sin nota
            if any(f.lower() == "heif" for f in db_norm):
                fmt_ok = True
            else:
                #Si es iPhone >= 7 → válido y anotamos la razón
                ex_model = normalize_string(exif_fields.get("model")) or ""
                m = re.search(r'iphone\s*(\d+)', ex_model, re.IGNORECASE)
                if m and int(m.group(1)) > 6:
                    fmt_ok = True
                    note = "Modelo de iPhone superior a iPhone 6 --> heic/heif es válido"
                else:
                    fmt_ok = False
        else:
            # resto de extensiones, comparación normal
            fmt_ok = any(ex_low == f.lower() for f in db_norm)

    resultado["file_format"] = {
        "db_raw":   ", ".join(db_norm) if db_norm else None,
        "exif_raw": ex_fmt,
        "status":   fmt_ok,
        "note":     note
    }



    return resultado



def compare_exif_to_device(exif_fields, device_dict, thresholds=None):

    informe = {
        "device": compare_device_level(
            exif_fields,
            device_dict,
            focal_tol=(thresholds or {}).get("focal_length_35mm", 3.0)
        ),
        "cameras": []
    }
    cam_list = device_dict.get("cameras") or []
    for cam in cam_list:
       
        cam_dict = cam.copy()
        cam_dict["all_cameras"] = cam_list
        informe["cameras"].append({
            "type": cam_dict.get("type"),
            "comparisons": compare_camera_level(exif_fields, cam_dict, thresholds)
        })
    return informe
