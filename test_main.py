from main import build_graph_from_geojson, dijkstra_shortest_path, normalize_coord


def get_node_id_by_coord(graph: dict, coord: tuple[float, float]) -> int:
    target = normalize_coord(coord)
    for node_id, data in graph.items():
        if data["coord"] == target:
            return node_id
    raise KeyError(f"Coordinate {target} not found in graph")


def test_valid_route():
    graph = build_graph_from_geojson("road_network.geojson")
    source_id = get_node_id_by_coord(graph, (77.59, 12.972))
    target_id = get_node_id_by_coord(graph, (77.596, 12.968))

    path = dijkstra_shortest_path(graph=graph, from_node=source_id, to_node=target_id)

    assert path == [
        (77.59, 12.972),
        (77.592, 12.97),
        (77.594, 12.97),
        (77.596, 12.97),
        (77.596, 12.968),
    ]


def test_identical_source_and_destination():
    graph = build_graph_from_geojson("road_network.geojson")
    node_id = get_node_id_by_coord(graph, (77.592, 12.97))

    path = dijkstra_shortest_path(graph=graph, from_node=node_id, to_node=node_id)

    assert path == [(77.592, 12.97)]


def test_unreachable_destination():
    graph = build_graph_from_geojson("road_network.geojson")
    source_id = get_node_id_by_coord(graph, (77.59, 12.97))

    # Add a disconnected node to the graph
    isolated_node_id = max(graph.keys()) + 1
    graph[isolated_node_id] = {"coord": (77.605, 12.985), "edges": []}

    path = dijkstra_shortest_path(
        graph=graph,
        from_node=source_id,
        to_node=isolated_node_id,
    )

    assert path == []