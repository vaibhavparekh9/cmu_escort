from xml.dom import minidom
import json

doc = minidom.parse('Shadyside.kml')
placemarks = doc.getElementsByTagName('Placemark')

stops = {}
for p in placemarks:
    name = p.getElementsByTagName('name')[0].firstChild.data
    coords = p.getElementsByTagName('coordinates')[0].firstChild.data.strip()
    lon, lat, *_ = coords.split(',')
    stops[name.replace(' ', '+')] = {
        "name": name,
        "latitude": float(lat),
        "longitude": float(lon)
    }

with open("Shadyside.json", "w") as f:
    json.dump(stops, f, indent=2)