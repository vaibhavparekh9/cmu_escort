This project is to enhance the driver/rider experience in CMU Escort buses. These buses run late at night to drop students at intersections closest to their homes. Currently, the rider has to tap the ID card while boarding the bus - and manually tell the driver the closest intersection to their house. this projects allows this _address_ information to be stored in the ID card so that - it can be captured when a student taps it. For the driver side - all the captured _addresses_ can be used to design an optimized route which the driver can navigate using Google Maps.

Files:
1. ```kml_to_json.py```: converts the .kml file downloaded from My Google Maps into a custom structured JSON format.
2. ```pickups.json```: JSON dict of all pickup locations.
3. ```Shadyside.json```: JSON dict of all possible (superset) pickup locations for Blue Zone (Shadyside). This file is created from the ```kml_to_json.py``` for input ```Shadyside.kml```.
4. ```Shadyside.kml```: exported from My Google Maps; it has information _'name'_ and _'lat/lon coordinates'_ of all marked pins.
5. ```build_matrix.py```: builds an NxN matrix for the superset of all stops - as a precompute for running the TSP on only selected stops.
6. ```route_planner.py```: plans the final route starting at the last pickup spot in pickups.json thru all (simulated/sample) stops in stops.json
7. ```stops.json```: JSON dict of student-tapped stops (subset of Shadyside.json) that the route planner uses as waypoints.
8. ```requirements.txt```: Python dependencies for the project.
9. ```dashboard/server.py```: Flask backend that serves the mobile dashboard and exposes APIs for managing stops and running the route planner.
10. ```dashboard/index.html```: mobile-optimized web UI for simulating taps, adding/removing stops, and planning routes.

Steps:
1. Use My Google Maps to create a layer of all desired pins (superset of stops for a given Escort Zone). Export it as a .kml file.
2. Run ```kml_to_json.py``` file to convert it into a JSON file. Saves a .json file.
3. Run ```build_matrix.py``` to precompute an NxN matrix for TSP. Saves a _matrix.npz and a _index.json file. 
4. Run ```route_planner.py``` to return optimized waypoints path & Google Maps deep-link URL.

## Running Instructions

```bash
pip install -r requirements.txt
cd dashboard
python3 server.py
```

Open http://localhost:5001 in a browser. Use DevTools device toolbar (9:16 portrait) for the intended mobile layout. Use the buttons to simulate taps, add/remove stops, and plan a route — "Plan Route" runs the TSP solver and redirects to Google Maps.