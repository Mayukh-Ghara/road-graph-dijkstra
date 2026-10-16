# Road Network Graph & Dijkstra Shortest Path

A Python implementation that builds a weighted undirected road network graph from GeoJSON `LineString` features and calculates the shortest route between nodes using a from-scratch implementation of Dijkstra's algorithm.

## Features & Deliverables

1. **GeoJSON-to-Graph Importer (`build_graph_from_geojson`)**
   - Parses `LineString` road features from `road_network.geojson`.
   - Uses **Shapely** (`intersection`, `split`, `transform`) to detect shared endpoints and interior road intersections, splitting road geometries into discrete graph edges.
   - Normalizes coordinates to 6 decimal places so shared endpoints and intersections map to the same integer node ID.
   - Converts WGS84 `(longitude, latitude)` coordinates into metric distances (meters) before computing segment lengths.

2. **Adjacency-List Graph Structure**
   - Stored as a Python dictionary mapping each `node_id` (`int`) to its `(lon, lat)` coordinate and a list of connected edge dictionaries:
     ```python
     {
         0: {
             "coord": (77.59, 12.97),
             "edges": [
                 {
                     "to": 1,
                     "distance": 217.14,
                     "road_id": "R1",
                     "name": "Main Street",
                     "segment_coords": [(77.59, 12.97), (77.592, 12.97)]
                 },
                 ...
             ]
         },
         ...
     }
     ```

3. **Dijkstra's Shortest-Path Algorithm (`dijkstra_shortest_path`)**
   - Implemented from scratch using a min-heap priority queue (`heapq`).
   - Returns the shortest path by total road distance as an ordered list of `(lon, lat)` coordinates from `from_node` to `to_node`.
   - Gracefully handles identical source/destination nodes and unreachable/disconnected destinations (returns `[]`).

4. **Automated Unit Tests (`test_main.py`)**
   - Verifies a valid multi-segment shortest route (`N5` -> `N1` -> `N2` -> `N7`).
   - Verifies identical source and destination node handling.
   - Verifies unreachable destination node handling.

---

## Project Structure

```text
road_graph_dijkstra/
├── main.py                 # Graph builder, Dijkstra implementation, and Matplotlib plotter
├── test_main.py            # Pytest test suite covering all required scenarios
├── road_network.geojson    # Sample synthetic WGS84 road network dataset
├── route_plot.png          # Generated visualization of the graph and shortest route
├── pyproject.toml          # Project configuration and dependencies
├── uv.lock                 # Locked dependency versions for reproducible runs
└── README.md               # Project documentation