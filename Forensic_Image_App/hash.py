import hashlib

def generate_hashes(image_path, algorithms=None):
    """
    Genera hashes comunes (MD5, SHA1, SHA256, SHA512, BLAKE2b) para una imagen.
    :param image_path: Ruta al archivo de imagen.
    :param algorithms: Lista opcional de algoritmos (por defecto usa 5 comunes).
    :return: Diccionario { 'MD5': ..., 'SHA1': ..., ... }
    """
    if algorithms is None:
        algorithms = ['md5', 'sha1', 'sha256', 'sha512', 'blake2b']
    
    hashes = {}
    
    try:
        with open(image_path, 'rb') as f:
            data = f.read()
            for algo in algorithms:
                h = hashlib.new(algo)
                h.update(data)
                hashes[algo.upper()] = h.hexdigest()
    except Exception as e:
        # Podrías registrar el error si lo deseas
        hashes = {"error": str(e)}

    return hashes
