import requests
import re

def obtener_offset_maximo(url_base):
    respuesta = requests.get(url_base + "0", verify=False)
    respuesta.raise_for_status()

    html = respuesta.text
    offsets = re.findall(r"filter=(\d+)", html)
    offsets_int = [int(x) for x in offsets]
    if not offsets_int:
        raise RuntimeError("No se encontraron offsets en la página.")
    return max(offsets_int)

def generar_urls_catalogo(auto_detectar=True,
                          limite=None,
                          paso=29,
                          archivo="catalogo_urls.txt"):
    url_base = "https://phonedb.net/index.php?m=device&s=list&filter="

    if auto_detectar:
        print("Descargando primera página…")
        limite = obtener_offset_maximo(url_base)
        print(f"Offset máximo detectado: {limite}")
    else:
        if limite is None:
            raise ValueError("Si no auto-detectas, debes pasar un 'limite' manual.")

    offsets = list(range(0, limite + 1, paso))
    urls = [f"{url_base}{offset}" for offset in offsets]

    with open(archivo, "w", encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")

    print(f"Se han generado {len(urls)} URLs (offsets 0..{limite} de {paso} en {paso}) y se han guardado en '{archivo}'.")

if __name__ == "__main__":
    generar_urls_catalogo(auto_detectar=True)
