# src/graph_builder.py
import json
import pathlib
import csv
import math
import networkx as nx

DATA_DIR = pathlib.Path("data")
OUT_NODES = "nodes.csv"
OUT_EDGES = "edges.csv"


def haversine(lat1, lng1, lat2, lng2):
    """Расчёт расстояния между двумя точками по формуле Haversine (в метрах)"""
    R = 6371000  # Радиус Земли в метрах
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def load_route_data():
    """Загружает все маршруты из JSON-файлов"""
    all_routes = []
    for file_path in DATA_DIR.glob("*.json"):
        if file_path.name == "all.json":
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if data:
                    all_routes.append(data)
            except json.JSONDecodeError:
                continue
    return all_routes


def build_graph():
    """Строит граф из данных маршрутов"""
    routes = load_route_data()
    
    nodes = {}  # stid -> {название, координаты}
    edges = {}  # (stid_from, stid_to) -> расстояние
    
    for route_data in routes:
        # Сортируем остановки по времени прибытия (от большего к меньшему)
        route_data.sort(key=lambda x: int(x.get("arrt", 0)), reverse=True)
        
        # Собираем узлы
        for stop in route_data:
            stid = int(stop["stid"])
            if stid not in nodes:
                lat = int(stop["lat0"]) / 1_000_000
                lng = int(stop["lng0"]) / 1_000_000
                nodes[stid] = {
                    "stname": stop["stname"].strip(),
                    "lat": lat,
                    "lng": lng
                }
        
        # Собираем рёбра (последовательные остановки)
        for i in range(len(route_data) - 1):
            st_from = int(route_data[i]["stid"])
            st_to = int(route_data[i+1]["stid"])
            
            if st_from != st_to:
                lat1 = int(route_data[i]["lat0"]) / 1_000_000
                lng1 = int(route_data[i]["lng0"]) / 1_000_000
                lat2 = int(route_data[i+1]["lat0"]) / 1_000_000
                lng2 = int(route_data[i+1]["lng0"]) / 1_000_000
                
                distance = haversine(lat1, lng1, lat2, lng2)
                
                edge_key = (st_from, st_to)
                if edge_key not in edges or distance < edges[edge_key]:
                    edges[edge_key] = distance
                
                # Обратное ребро
                reverse_key = (st_to, st_from)
                if reverse_key not in edges or distance < edges[reverse_key]:
                    edges[reverse_key] = distance
    
    # Сохраняем в CSV
    with open(OUT_NODES, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["stid", "stname", "lat", "lng"])
        for stid, info in nodes.items():
            writer.writerow([stid, info["stname"], info["lat"], info["lng"]])
    
    with open(OUT_EDGES, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target", "weight"])
        for (st_from, st_to), weight in edges.items():
            writer.writerow([st_from, st_to, round(weight, 2)])
    
    # Строим NetworkX граф
    G = nx.DiGraph()
    for stid, info in nodes.items():
        G.add_node(stid, name=info["stname"], lat=info["lat"], lng=info["lng"])
    for (st_from, st_to), weight in edges.items():
        G.add_edge(st_from, st_to, weight=weight)
    
    return G