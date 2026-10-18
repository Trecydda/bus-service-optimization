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


def build_graph():
    print("Строим граф из сохраненных файлов...")
    
    nodes = {}  # stid -> {название, координаты}
    edges = {}  # (stid_from, stid_to) -> расстояние
    
    # Проходимся по всем JSON файлам в папке data
    for file_path in DATA_DIR.glob("*.json"):
        if file_path.name == "all.json":
            continue
        
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                route_data = json.load(f)
            except json.JSONDecodeError:
                continue
        
        if not route_data:
            continue
        
        # Сортируем остановки по времени прибытия (от большего к меньшему)
        route_data.sort(key=lambda x: x.get("arrt", 0), reverse=True)
        
        # Собираем данные об остановках (узлы)
        for stop in route_data:
            stid = stop["stid"]
            if stid not in nodes:
                # Координаты нужно делить на 10^6
                lat = int(stop["lat0"]) / 1_000_000
                lng = int(stop["lng0"]) / 1_000_000
                nodes[stid] = {
                    "stname": stop["stname"].strip(),
                    "lat": lat,
                    "lng": lng
                }
        
        # Собираем связи (рёбра) между последовательными остановками
        for i in range(len(route_data) - 1):
            st_from = route_data[i]["stid"]
            st_to = route_data[i+1]["stid"]
            
            if st_from != st_to:
                # Рассчитываем расстояние
                lat1 = int(route_data[i]["lat0"]) / 1_000_000
                lng1 = int(route_data[i]["lng0"]) / 1_000_000
                lat2 = int(route_data[i+1]["lat0"]) / 1_000_000
                lng2 = int(route_data[i+1]["lng0"]) / 1_000_000
                
                distance = haversine(lat1, lng1, lat2, lng2)
                
                # Сохраняем ребро (если уже есть, берём минимальное расстояние)
                edge_key = (st_from, st_to)
                if edge_key not in edges or distance < edges[edge_key]:
                    edges[edge_key] = distance
                
                # Добавляем обратное ребро (транспорт ездит в обе стороны)
                reverse_key = (st_to, st_from)
                if reverse_key not in edges or distance < edges[reverse_key]:
                    edges[reverse_key] = distance
    
    # Сохраняем узлы в CSV
    with open(OUT_NODES, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["stid", "stname", "lat", "lng"])
        for stid, info in nodes.items():
            writer.writerow([stid, info["stname"], info["lat"], info["lng"]])
    
    # Сохраняем рёбра в CSV
    with open(OUT_EDGES, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target", "weight"])
        for (st_from, st_to), weight in edges.items():
            writer.writerow([st_from, st_to, round(weight, 2)])
    
    print(f"Готово!")
    print(f"Найдено уникальных остановок (узлов): {len(nodes)}")
    print(f"Найдено уникальных связей (рёбер): {len(edges)}")
    print(f"Данные сохранены в файлы: {OUT_NODES} и {OUT_EDGES}")
    
    # Строим граф NetworkX
    G = nx.DiGraph()
    
    # Добавляем узлы
    for stid, info in nodes.items():
        G.add_node(stid, name=info["stname"], lat=info["lat"], lng=info["lng"])
    
    # Добавляем рёбра
    for (st_from, st_to), weight in edges.items():
        G.add_edge(st_from, st_to, weight=weight)
    
    return G


if __name__ == "__main__":
    G = build_graph()
    
    # Рассчитываем характеристики графа
    print("\n=== Характеристики графа ===")
    print(f"Количество узлов: {G.number_of_nodes()}")
    print(f"Количество рёбер: {G.number_of_edges()}")
    print(f"Плотность графа: {nx.density(G):.4f}")
    
    if nx.is_strongly_connected(G):
        print("Граф сильно связный")
    else:
        print("Граф не является сильно связным")
        print(f"Количество компонент сильной связности: {nx.number_strongly_connected_components(G)}")
    
    # Центральность по степени
    degree_centrality = nx.degree_centrality(G)
    top_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
    print("\nТоп-5 узлов по центральности степени:")
    for node, centrality in top_nodes:
        name = G.nodes[node].get('name', 'Unknown')
        print(f"  {name}: {centrality:.4f}")