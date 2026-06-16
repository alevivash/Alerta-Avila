import zipfile
import xml.etree.ElementTree as ET
import json
import ee

# Suponiendo que tu archivo se llama 'avila.kmz'
kmz_path = r"C:\Users\Alejandro\Documents\Projects\ALERTAS\googlemaps-avila-warairarepano.kmz.zip"

with zipfile.ZipFile(kmz_path, 'r') as z:
    # El KMZ típicamente contiene un archivo .kml (podría llamarse doc.kml o similar)
    kml_file = [f for f in z.namelist() if f.endswith('.kml')][0]
    with z.open(kml_file) as f:
        kml_content = f.read().decode('utf-8')

# Parsear KML (es XML)
root = ET.fromstring(kml_content)
# Buscar las coordenadas del polígono (namespaces de KML)
ns = {'kml': 'http://www.opengis.net/kml/2.2'}
coordenadas_texto = root.find('.//kml:Polygon/kml:outerBoundaryIs/kml:LinearRing/kml:coordinates', ns).text
# Convertir a lista de pares (lon, lat)
pares = [list(map(float, coord.split(',')[:2])) for coord in coordenadas_texto.strip().split()]
# GeoJSON espera anillo cerrado (repetir primer punto al final)
if pares[0] != pares[-1]:
    pares.append(pares[0])

# Crear polígono en GEE
roi = ee.Geometry.Polygon(pares)
print(f"Polígono cargado desde KMZ. Área: {roi.area().getInfo()/1e6:.2f} km²")