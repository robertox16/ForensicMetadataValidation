import requests
from bs4 import BeautifulSoup
import warnings
from urllib3.exceptions import InsecureRequestWarning
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.simplefilter('ignore', InsecureRequestWarning)

archivo_catalogo    = "catalogo_urls.txt"   
archivo_metadatos   = "metadatos3.txt"
archivo_interesados = "interesados.txt"     
base_url            = "https://phonedb.net/"

categorias_excluidas = ["Smartwatch", "Subnotebook"]

file_lock = threading.Lock()

def cargar_interesados():
    with open(archivo_interesados, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

interesados = cargar_interesados()

def obtener_urls_dispositivos(catalogo_url):
    page = requests.get(catalogo_url, verify=False)
    soup = BeautifulSoup(page.text, "html.parser")

    urls_dispositivos = []
    for enlace in soup.find_all("a", title="See detailed datasheet"):
        href = enlace.get("href")
        if href:
            urls_dispositivos.append(base_url + href)

    print(f"Se encontraron {len(urls_dispositivos)} dispositivos en: {catalogo_url}")
    return urls_dispositivos

def es_dispositivo_excluido_soup(soup, device_url):
    for strong in soup.find_all("strong"):
        texto = strong.get_text(strip=True).lower()
        for categoria in categorias_excluidas:
            if categoria.lower() in texto:
                print(f"{device_url} es un dispositivo excluido (contiene: {categoria}).")
                return True
    return False

def tiene_camara_soup(soup):
    for strong in soup.find_all("strong"):
        texto = strong.get_text(strip=True).lower()
        if "camera" in texto:
            return True
    return False

def limpiar_dato(texto):
    partes = [parte.strip() for parte in texto.replace("\n", ", ").split(",") if parte.strip()]
    return ", ".join(partes)

def obtener_datos_dispositivo_soup(soup):
    resultados = {}
    for strong in soup.find_all('strong'):
        titulo = strong.get_text(strip=True)
        if titulo in interesados:
            fila = strong.find_parent('tr')
            if fila:
                tds = fila.find_all('td')
                if len(tds) > 1:
                    dato_crudo = tds[1].get_text(" ", strip=True)
                    parte_limpia = limpiar_dato(dato_crudo)
                    resultados[titulo] = parte_limpia
    return resultados

def guardar_metadatos(url, datos):
    with file_lock:
        with open(archivo_metadatos, "a", encoding="utf-8") as f:
            f.write(f"URL: {url}\n")
            for clave, valor in datos.items():
                f.write(f"{clave}: {valor}\n")
            f.write("---------------------------------------------------------------------------\n")

def procesar_un_dispositivo(device_url):
    try:
        page = requests.get(device_url, verify=False)
        soup = BeautifulSoup(page.text, "html.parser")

        if es_dispositivo_excluido_soup(soup, device_url):
            return  
        if not tiene_camara_soup(soup):
            print(f"{device_url} es un dispositivo sin cámara")
            return

        datos = obtener_datos_dispositivo_soup(soup)
        guardar_metadatos(device_url, datos)

    except Exception as e:
        print(f"Error al procesar {device_url}: {type(e).__name__}")

def procesar_catalogo():
    with open(archivo_catalogo, "r", encoding="utf-8") as f:
        urls_catalogo = [line.strip() for line in f if line.strip()]

    print(f"\nProcesando {len(urls_catalogo)} URLs\n")

    for catalogo_url in urls_catalogo:
        dispositivos_urls = obtener_urls_dispositivos(catalogo_url)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futuros = [executor.submit(procesar_un_dispositivo, url) 
                       for url in dispositivos_urls]
            for _ in as_completed(futuros):
                pass

if __name__ == "__main__":
    procesar_catalogo()
    print("\n Proceso completado")
