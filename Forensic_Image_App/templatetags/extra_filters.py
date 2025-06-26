# Forensic_Image_App/templatetags/extra_filters.py

from django import template

register = template.Library()

@register.filter
def index(sequence, idx):
    """
    Toma una lista o tupla y devuelve sequence[int(idx)] si existe, 
    o None en caso contrario.
    Uso en template: {{ mi_lista|index:2 }} -> accede a mi_lista[2]
    """
    try:
        return sequence[int(idx)]
    except Exception:
        return None


@register.filter
def attr(value, arg):
    """
    Permite navegar en diccionarios u objetos anidados usando una ruta de puntos.
    Ejemplo en template: {{ mi_dict|attr:"cameras.0.comparisons.aperture.status" }}
    devolverá mi_dict["cameras"][0]["comparisons"]["aperture"]["status"] 
    (o None si falta alguna clave/atributo).
    """
    try:
        current = value
        for part in arg.split("."):
            if current is None:
                return None
            # Si es dict, sacamos la clave
            if isinstance(current, dict):
                current = current.get(part)
            else:
                # Si es un objeto con atributo, lo obtenemos
                current = getattr(current, part, None)
        return current
    except Exception:
        return None
