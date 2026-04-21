import json
import logging
import os
import matplotlib
# [!] FORZAR MOTOR NO INTERACTIVO (Debe ir antes de importar pyplot)
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

logger = logging.getLogger(__name__)

def generate_map_image(json_path: str):
    """
    Reads a map JSON file and generates a PNG image with the exact topology,
    saving it in the same folder where this script resides.
    Safe for background threading.
    """
    # 1. Load the JSON file
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error leyendo el JSON del mapa: {e}")
        return

    # Create a large canvas with good resolution
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Color palette to alternate between roads
    colors = plt.get_cmap('tab10')
    color_idx = 0

    # 2. Draw Roads
    if "roads" in data:
        for road_id, road in data["roads"].items():
            # Convert LFS units to meters
            xs = [node["x"] / 65536.0 for node in road["nodes"]]
            ys = [node["y"] / 65536.0 for node in road["nodes"]]
            
            # If the road is circular, connect the last point to the first to close the drawing
            if road.get("is_circular", False) and len(xs) > 0:
                xs.append(xs[0])
                ys.append(ys[0])
                
            current_color = colors(color_idx % 10)
            color_idx += 1
            
            # Draw the line
            ax.plot(xs, ys, marker='.', linestyle='-', linewidth=2.5, color=current_color, label=f"Road: {road_id}")

    # 3. Draw Intersection Zones
    if "zones" in data:
        for z_idx, (zone_id, zone) in enumerate(data["zones"].items()):
            nodes = zone["nodes"]
            radius = zone.get("radius_m", 10.0)
            
            # Only add the legend label to the first zone to avoid duplicates
            label_zone = "Zones (Influence Radius)" if z_idx == 0 else ""
            
            if len(nodes) == 1:
                # It's a point -> Draw a circle
                cx = nodes[0]["x"] / 65536.0
                cy = nodes[0]["y"] / 65536.0
                circle = patches.Circle((cx, cy), radius, color='red', alpha=0.2, label=label_zone)
                ax.add_patch(circle)
                ax.text(cx, cy, zone_id, fontsize=8, ha='center', color='darkred')
                
            elif len(nodes) >= 3:
                # It's a polygon -> Draw the shape
                xs = [n["x"] / 65536.0 for n in nodes]
                ys = [n["y"] / 65536.0 for n in nodes]
                poly = patches.Polygon(xy=list(zip(xs, ys)), closed=True, color='red', alpha=0.2, label=label_zone)
                ax.add_patch(poly)
                cx, cy = sum(xs)/len(xs), sum(ys)/len(ys) # Approximate centroid for the text
                ax.text(cx, cy, zone_id, fontsize=8, ha='center', color='darkred')

    # 4. Draw Lateral Links
    if "lateral_links" in data:
        for l_idx, (link_id, link) in enumerate(data["lateral_links"].items()):
            xs = [node["x"] / 65536.0 for node in link["nodes"]]
            ys = [node["y"] / 65536.0 for node in link["nodes"]]
            label_lat = "Lateral Link" if l_idx == 0 else ""
            
            # Draw with dashed gray line
            ax.plot(xs, ys, marker='', linestyle='--', linewidth=1.5, color='gray', alpha=0.7, label=label_lat)

    # 5. Draw Longitudinal Links (Road Links)
    if "road_links" in data:
        for r_idx, (link_id, link) in enumerate(data["road_links"].items()):
            nodes = link["nodes"]
            if not nodes: continue
            xs = [n["x"] / 65536.0 for n in nodes]
            ys = [n["y"] / 65536.0 for n in nodes]
            label_road = "Link Point (RoadLink)" if r_idx == 0 else ""
            
            # Mark with a thick cyan cross
            ax.plot(xs, ys, marker='X', color='c', linestyle='', markersize=8, label=label_road)

    # 6. Visual chart configuration (Orientado a objetos para Thread-Safety)
    ax.set_aspect('equal', adjustable='datalim') 
    ax.set_title("Map Visualization", fontsize=16, fontweight='bold')
    ax.set_xlabel("X (Meters)", fontsize=12)
    ax.set_ylabel("Y (Meters)", fontsize=12)
    ax.grid(True, linestyle=':', alpha=0.6)
    
    # Legend outside the chart so it doesn't cover the roads
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    fig.tight_layout()
    
    # 7. Save to disk
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_name = os.path.basename(json_path).replace(".json", "")
    output_path = os.path.join(script_dir, f"{base_name}_rendered.png")
    
    # Usar fig.savefig en lugar de plt.savefig
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f"Imagen del mapa guardada en '{output_path}'")
    
    # [!] MUY IMPORTANTE: Liberar explícitamente la memoria de ESTA figura
    fig.clf()
    plt.close(fig)

# --- HOW TO USE IT ---
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "..", "test.json")
    json_path = os.path.abspath(json_path)
    generate_map_image(json_path)