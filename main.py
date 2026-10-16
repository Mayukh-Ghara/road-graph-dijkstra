import json
import math
import heapq
from pathlib import Path
import shapely
from shapely.geometry import LineString, Point, MultiPoint
from shapely.ops import split
import matplotlib.pyplot as plt

COORD_PRECISION = 6


def normalize_coord(coord) -> tuple[float, float]:
    """Round (lon, lat) to consistent decimal precision to merge shared nodes."""
    return (round(float(coord[0]), COORD_PRECISION), round(float(coord[1]), COORD_PRECISION))


def wgs84_linestring_length_meters(line: LineString) -> float:
    """
    Convert WGS84 (lon, lat) coordinates into local meters using
    shapely.transform() and return the LineString length.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    mean_lat_rad = math.radians(sum(c[1] for c in coords) / len(coords))
    meters_per_deg_lat = 111_132.92 - 559.82 * math.cos(2 * mean_lat_rad)
    meters_per_deg_lon = 111_412.84 * math.cos(mean_lat_rad)

    metric_line = shapely.transform(
        line,
        lambda c: c * [meters_per_deg_lon, meters_per_deg_lat],
    )
    return float(metric_line.length)


def build_graph_from_geojson(geojson_path: str | Path) -> dict[int, dict]:
    """
    Deliverables 1 & 2:
    Read LineString features from GeoJSON, create nodes at endpoints and
    intersections, and store the graph as a Python dictionary adjacency list.
    """
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = []
    for feature in data.get("features", []):
        geom = feature.get("geometry", {})
        if geom.get("type") == "LineString":
            coords = [normalize_coord(c) for c in geom.get("coordinates", [])]
            if len(coords) >= 2:
                features.append({
                    "props": feature.get("properties", {}),
                    "line": LineString(coords),
                })

    split_points_per_road: list[set[tuple[float, float]]] = [set() for _ in features]

    for i, feat_i in enumerate(features):
        line_i = feat_i["line"]
        coords_i = list(line_i.coords)
        split_points_per_road[i].add(normalize_coord(coords_i[0]))
        split_points_per_road[i].add(normalize_coord(coords_i[-1]))

        for j in range(i + 1, len(features)):
            line_j = features[j]["line"]
            inter = line_i.intersection(line_j)
            if inter.is_empty:
                continue
            if isinstance(inter, Point):
                pt = normalize_coord((inter.x, inter.y))
                split_points_per_road[i].add(pt)
                split_points_per_road[j].add(pt)
            elif isinstance(inter, MultiPoint):
                for p in inter.geoms:
                    pt = normalize_coord((p.x, p.y))
                    split_points_per_road[i].add(pt)
                    split_points_per_road[j].add(pt)

    coord_to_node_id: dict[tuple[float, float], int] = {}
    graph: dict[int, dict] = {}

    def get_or_create_node(coord: tuple[float, float]) -> int:
        coord = normalize_coord(coord)
        if coord not in coord_to_node_id:
            node_id = len(coord_to_node_id)
            coord_to_node_id[coord] = node_id
            graph[node_id] = {"coord": coord, "edges": []}
        return coord_to_node_id[coord]

    for i, feat in enumerate(features):
        line = feat["line"]
        props = feat["props"]
        road_id = props.get("road_id", f"R_{i}")
        road_name = props.get("name", "")

        start_pt = normalize_coord(line.coords[0])
        end_pt = normalize_coord(line.coords[-1])
        interior_pts = [
            Point(pt) for pt in split_points_per_road[i] if pt not in (start_pt, end_pt)
        ]

        segments = list(split(line, MultiPoint(interior_pts)).geoms) if interior_pts else [line]

        for seg in segments:
            seg_coords = [normalize_coord(c) for c in seg.coords]
            u = get_or_create_node(seg_coords[0])
            v = get_or_create_node(seg_coords[-1])
            dist = round(wgs84_linestring_length_meters(seg), 2)

            graph[u]["edges"].append({
                "to": v,
                "distance": dist,
                "road_id": road_id,
                "name": road_name,
                "segment_coords": seg_coords,
            })
            graph[v]["edges"].append({
                "to": u,
                "distance": dist,
                "road_id": road_id,
                "name": road_name,
                "segment_coords": list(reversed(seg_coords)),
            })

    return graph


def dijkstra_shortest_path(
    graph: dict,
    from_node: int,
    to_node: int,
) -> list[tuple[float, float]]:
    """
    Deliverable 3:
    Find the shortest path by total road distance from scratch and return
    the ordered list of (lon, lat) coordinates.
    """
    if from_node not in graph or to_node not in graph:
        return []

    if from_node == to_node:
        return [graph[from_node]["coord"]]

    distances: dict[int, float] = {node_id: math.inf for node_id in graph}
    distances[from_node] = 0.0
    previous: dict[int, tuple[int, dict] | None] = {node_id: None for node_id in graph}
    visited: set[int] = set()

    pq: list[tuple[float, int]] = [(0.0, from_node)]

    while pq:
        current_dist, current_node = heapq.heappop(pq)

        if current_node in visited:
            continue
        visited.add(current_node)

        if current_node == to_node:
            break

        for edge in graph[current_node]["edges"]:
            neighbor = edge["to"]
            weight = edge["distance"]
            if neighbor in visited:
                continue

            new_dist = current_dist + weight
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                previous[neighbor] = (current_node, edge)
                heapq.heappush(pq, (new_dist, neighbor))

    if distances[to_node] == math.inf:
        return []

    route_segments: list[list[tuple[float, float]]] = []
    curr = to_node
    while previous[curr] is not None:
        pred_node, edge_used = previous[curr]
        route_segments.append(
            edge_used.get("segment_coords", [graph[pred_node]["coord"], graph[curr]["coord"]])
        )
        curr = pred_node

    route_segments.reverse()

    ordered_coords: list[tuple[float, float]] = []
    for seg_coords in route_segments:
        for coord in seg_coords:
            if not ordered_coords or ordered_coords[-1] != coord:
                ordered_coords.append(coord)

    return ordered_coords


def plot_route(graph: dict, path: list[tuple[float, float]], output_file: str = "route_plot.png") -> None:
    """Save a visualization of the road network graph and shortest route."""
    plt.figure(figsize=(8, 6))

    for node_id, data in graph.items():
        for edge in data["edges"]:
            xs = [c[0] for c in edge["segment_coords"]]
            ys = [c[1] for c in edge["segment_coords"]]
            plt.plot(xs, ys, color="lightgray", linewidth=2, zorder=1)

    for node_id, data in graph.items():
        x, y = data["coord"]
        plt.scatter(x, y, color="steelblue", s=50, zorder=2)
        plt.text(x + 0.00008, y + 0.00008, f"N{node_id}", fontsize=9)

    if path:
        px = [c[0] for c in path]
        py = [c[1] for c in path]
        plt.plot(px, py, color="crimson", linewidth=3, label="Shortest Path", zorder=3)

    plt.ticklabel_format(useOffset=False, style="plain")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Road Network Graph & Dijkstra Shortest Route")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    print(f"\nSaved network plot to: {output_file}")


if __name__ == "__main__":
    graph = build_graph_from_geojson("road_network.geojson")

    print("=== Built Adjacency-List Graph ===")
    for node_id, info in graph.items():
        edges_summary = [(e["to"], f"{e['distance']}m", e["road_id"]) for e in info["edges"]]
        print(f"Node {node_id} {info['coord']} -> {edges_summary}")

    source_node_id = 5  # (77.59, 12.972) - Top-left intersection (R3 & R5)
    target_node_id = 7  # (77.596, 12.968) - Bottom-right endpoint of Market Road (R4)

    path = dijkstra_shortest_path(
        graph=graph,
        from_node=source_node_id,
        to_node=target_node_id,
    )
    print(f"\nShortest path from Node {source_node_id} to Node {target_node_id}:")
    print(path)

    plot_route(graph, path)