import os
import django
import re
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Forensic_Image_App.settings')
django.setup()

from DataBaseApp.models import (
    Brand,
    Device,
    Sensor,
    Feature,
    Media_Format,
    Camera,
    DeviceCamera,
    Camera_Features,
    Camera_Medias,
)

CAMERA_KEYS = {
    "Principal": {
        "sensor": "Camera Image Sensor",
        "format": "Image Sensor Format",
        "pixel_size": "Image Sensor Pixel Size",
        "resolution": "Camera Resolution",
        "num_pixels": "Number of effective pixels",
        "aperture": "Aperture (W)",
        "focus": "Focus",
        "mefl": "Min. Equiv. Focal Length",
        "features": "Camera Extra Functions",
        "photo_formats": "Recordable Image Formats",
        "video_formats": "Recordable Video Formats",
        "placement": "Camera Placement",
    },
    "Aux. Camera": {
        "sensor": "Aux. Camera Image Sensor",
        "format": "Aux. Cam. Image Sensor Format",
        "pixel_size": "Aux. Cam. Image Sensor Pixel Size",
        "num_pixels": "Aux. Camera Number of Pixels",
        "aperture": "Aux. Camera Aperture (W)",
        "focus": "Aux. Camera Focus",
        "mefl": "Aux. Cam. Min. Equiv. Focal Length",
        "features": "Aux. Camera Extra Functions",
        "photo_formats": "Recordable Image Formats",
        "video_formats": "Recordable Video Formats",
    },
    "Aux. 2 Camera": {
        "sensor": "Aux. 2 Camera Image Sensor",
        "format": "Aux. 2 Cam. Image Sensor Format",
        "pixel_size": "Aux. 2 Cam. Image Sensor Pixel Size",
        "num_pixels": "Aux. 2 Camera Number of Pixels",
        "aperture": "Aux. 2 Camera Aperture (W)",
        "focus": "Aux. 2 Camera Focus",
        "mefl": "Aux. 2 Cam. Min. Equiv. Focal Length",
        "features": "Aux. 2 Camera Extra Functions",
    },
    "Aux. 3 Camera": {
        "sensor": "Aux. 3 Camera Image Sensor",
        "format": "Aux. 3 Cam. Image Sensor Format",
        "pixel_size": "Aux. 3 Cam. Image Sensor Pixel Size",
        "num_pixels": "Aux. 3 Camera Number of Pixels",
        "aperture": "Aux. 3 Camera Aperture (W)",
        "focus": "Aux. 3 Camera Focus",
        "mefl": "Aux. 3 Cam. Min. Equiv. Focal Length",
        "features": "Aux. 3 Camera Extra Functions",
    },
    "Aux. 4 Camera": {
        "sensor": "Aux. 4 Camera Image Sensor",
        "format": "Aux. 4 Cam. Image Sensor Format",
        "pixel_size": "Aux. 4 Cam. Image Sensor Pixel Size",
        "num_pixels": "Aux. 4 Camera Number of Pixels",
        "aperture": "Aux. 4 Camera Aperture (W)",
        "focus": "Aux. 4 Camera Focus",
        "mefl": "Aux. 4 Cam. Min. Equiv. Focal Length",
        "features": "Aux. 4 Camera Extra Functions",
    },
    "Secondary Camera": {
        "sensor": "Secondary Camera Sensor",
        "format": "Secondary Image Sensor Format",
        "pixel_size": "Secondary Image Sensor Pixel Size",
        "num_pixels": "Secondary Camera Number of pixels",
        "resolution": "Secondary Camera Resolution",
        "aperture": "Secondary Aperture (W)",
        "focus": "",
        "mefl": "Secondary Min. Equiv. Focal Length",
        "features": "Secondary Camera Extra Functions",
        "photo_formats": "Secondary Recordable Image Formats",
        "video_formats": "Secondary Recordable Video Formats",
        "placement": "Secondary Camera Placement",
    },
    "Sec. Aux. Cam.": {
        "sensor": "Sec. Aux. Cam. Image Sensor"
    },
    "Sec. Aux. 2 Cam.": {
        "sensor": "Sec. Aux. 2 Cam. Image Sensor"
    },
}

def get_or_create(model, **kwargs):
    
    return model.objects.get_or_create(**kwargs)[0]

def parse_device_block(block_text):
    return {
        k.strip(): v.strip()
        for line in block_text.strip().splitlines()
        if ':' in line
        for k, v in [line.split(':', 1)]
    }
def is_valid(value):
    return bool(value and value.strip().lower() != 'no')

def has_camera_data(data, fields):
    return any(is_valid(data.get(f, '')) for f in fields.values())

def clean_format_string(fmt):
    fmt = fmt.strip()
    if '.' in fmt:
        base, ext = fmt.rsplit('.', 1)
        return base.strip(), ext.strip()
    return fmt, fmt

def populate_database():
    with open('metadatos.txt', encoding='utf-8') as f:
        content = f.read()

    devices_raw = re.split(r'-{10,}', content)
    devices_raw = [d for d in devices_raw if d.strip()]

    total = len(devices_raw)
    print(f"Iniciando poblado de {total} dispositivos")
    count = 0

    for device_block in devices_raw:
        try:
            data = parse_device_block(device_block)
 
            brand, _ = Brand.objects.get_or_create(name=data.get('Brand', 'Unknown'))

            display_res = data.get('Resolution', '').strip()
            dw, dh = None, None
            if display_res:
                m = re.search(r'(\d+)\s*[x×]\s*(\d+)', display_res)
                if m:
                    dw = int(m.group(1))
                    dh = int(m.group(2))


            device = Device.objects.create(
                brand=brand,
                codename=data.get('Codename', '').strip() or None,
                category=data.get('Device Category', '').strip() or None,
                platform=data.get('Platform', '').strip() or None,
                os=data.get('Operating System', '').strip() or None,
                url=data.get('URL', '').strip() or None,
                flash=data.get('Flash', '').strip() or None,
                model=data.get('Model', '').strip() or None,
                display_width_px=dw,
                display_height_px=dh
            )

            for cam_type, fields in CAMERA_KEYS.items():
                if not has_camera_data(data, fields):
                    continue

                sensor_type   = data.get(fields.get('sensor', ''), '').strip() or None
                sensor_format = data.get(fields.get('format', ''), '').strip() or None
                pixel_size    = data.get(fields.get('pixel_size', ''), '').strip() or None

                sensor = None
                if sensor_type or sensor_format or pixel_size:
                    sensor = Sensor.objects.get_or_create(
                        sensor_type=sensor_type,
                        sensor_format=sensor_format,
                        pixel_size=pixel_size
                    )[0]

                resolution = data.get(fields.get('resolution',''), '').strip() or None
                num_pixels = data.get(fields.get('num_pixels',''), '').strip() or None
                aperture   = data.get(fields.get('aperture',''), '').strip() or None
                MEFL       = data.get(fields.get('mefl',''), '').strip() or None
                focus      = data.get(fields.get('focus',''), '').strip() or None
                placement  = data.get(fields.get('placement',''), '').strip() or None

                zoom = None
                if cam_type == 'Principal':
                    zoom = data.get('Zoom', '').strip() or None

                camera = Camera.objects.create(
                    sensor=sensor,
                    type=cam_type,
                    resolution=resolution,
                    num_pixels=num_pixels,
                    aperture=aperture,
                    MEFL=MEFL,
                    focus=focus,
                    zoom=zoom,
                    placement=placement
                )

                DeviceCamera.objects.get_or_create(device=device, camera=camera)

                features_str = data.get(fields.get('features', ''), '')
                for feat_name in [f.strip() for f in features_str.split(',') if is_valid(f)]:
                    feat = Feature.objects.get_or_create(name=feat_name)[0]
                    Camera_Features.objects.get_or_create(camera=camera, feature=feat)

                for media_field in ('photo_formats', 'video_formats'):
                    media_type = media_field.split('_')[0].capitalize()  
                    media_str  = data.get(fields.get(media_field, ''), '')
                    for fmt in [f.strip() for f in media_str.split(',') if is_valid(f)]:
                        base, ext = clean_format_string(fmt)
                        media_obj = Media_Format.objects.get_or_create(
                            format_type=media_type,
                            format_extension=ext
                        )[0]
                        Camera_Medias.objects.get_or_create(camera=camera, format=media_obj)

            count += 1
            percent = (count / total) * 100
            sys.stdout.write(f"\rProcesando dispositivos: {count}/{total} ({percent:.1f}%)")
            sys.stdout.flush()

        except Exception as e:
            modelo = data.get('Model', 'desconocido') if 'data' in locals() else 'n/a'
            print(f"\nError al procesar dispositivo '{modelo}': {e}")

    print("\nPoblado completado.")

if __name__ == '__main__':
    populate_database()
