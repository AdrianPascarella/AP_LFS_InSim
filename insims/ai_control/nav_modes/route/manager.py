from __future__ import annotations
import os
import ast
import logging
import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from insims.ai_control.nav_modes.route.mode import RouteMode
from insims.users_management.main import Coordinates, Speed
from lfs_insim.utils import calc_dist_3d, calc_deviation_angle
from lfs_insim.insim_packet_class import ISP_MSL
from lfs_insim.packet_sender_mixin import PacketSenderMixin

if TYPE_CHECKING:
    from insims.users_management.main import Player

logger = logging.getLogger(__name__)


@dataclass
class Waypoint:
    """Representa un objetivo 3D para la IA. Almacena valores RAW de LFS."""
    coordinates: Coordinates
    speed: Speed
        
@dataclass
class Route:
    """Estructura de datos para una ruta guardada."""
    name: str
    waypoints: list[Waypoint] = field(default_factory=list)

# ---------------------------------------------------------
# 3. GRABADOR DE RUTAS
# ---------------------------------------------------------

@dataclass
class Recorder(PacketSenderMixin):
    """Gestiona el usuario que está grabando una ruta"""
    player: 'Player'
    route_name: str
    
    waypoints: list[Waypoint] = field(default_factory=list)
    
    def __post_init__(self):
        # Configuración de Muestreo Dinámico (Adaptive Sampling)
        self.TARGET_TIME_s = 2.0          # Segundos de viaje que queremos entre cada punto
        self.MIN_DYNAMIC_DIST_m = 5.0     # Metros mínimos absolutos
        self.MAX_DYNAMIC_DIST_m = 60.0    # Metros máximos absolutos
        
        # Umbrales fijos
        self.SPEED_DELTA_kmh = 10.0       # Guardar si la velocidad varía > 10 km/h
        self.ANGLE_DELTA_degrees = 15.0   # Guardar en curvas pronunciadas
    
    def _add_waypoint(self, coordinates: Coordinates, speed: Speed):
        # Como los objetos ya vienen clonados y seguros desde process(), 
        # simplemente los añadimos a la lista.
        self.waypoints.append(Waypoint(coordinates, speed))
        msg = f'^8[REC] ^7Punto guardado en "{self.route_name}": X: {coordinates.x_m:.2f}, Y: {coordinates.y_m:.2f} | Vel: {speed.speed_kmh:.2f} km/h'
        self.send(ISP_MSL(Msg=msg))

# ---------------------------------------------------------
# 4. GESTOR DE RUTAS
# ---------------------------------------------------------

class RouteManager(PacketSenderMixin):
    """Gestiona la creación, grabación y carga de rutas."""
    def __init__(self):
        self.recorders: dict[int, Recorder] = {}    
        self.loaded_routes: dict[str, Route] = {}   
        self.load_routes()                          
        
    def load_routes(self):
        if not os.path.exists("rutas_grabadas.txt"): 
            return
            
        try:
            with open("rutas_grabadas.txt", "r") as f:
                lines = [line for line in f if not line.strip().startswith('#')]
            
            dict_str = "{" + "".join(lines) + "}"
            raw_routes = ast.literal_eval(dict_str)
            
            for name, wps in raw_routes.items():
                route = Route(name)
                for coords, spd in wps:
                    c = Coordinates(coords[0], coords[1], coords[2])
                    s = Speed(spd)
                    route.waypoints.append(Waypoint(c, s))
                self.loaded_routes[name] = route
                
            logger.info(f"Cargadas {len(self.loaded_routes)} rutas desde el disco.")
        except Exception as e:
            logger.error(f"Error cargando rutas desde el disco: {e}")

    def start(self, player: 'Player', name: str):
        self.recorders[player.plid] = Recorder(player, name)
        self.send(ISP_MSL(Msg=f"^2[REC] Grabación iniciada: ^7{name} siguiendo al plid {player.plid}"))

    def stop(self, plid: int):
        recorder = self.recorders.get(plid)
        if not recorder:
            self.send(ISP_MSL(Msg=f'No se estaba grabando ninguna ruta con el plid {plid}'))
            return
            
        if not self._save_to_disk(plid):
            self.send(ISP_MSL(Msg=f'Error: No se puedo guardar la ruta {recorder.route_name}. Se sigue grabando.'))
            return 
            
        nueva_ruta = Route(recorder.route_name)
        nueva_ruta.waypoints = list(recorder.waypoints)
        self.loaded_routes[recorder.route_name] = nueva_ruta
            
        count = len(recorder.waypoints)
        self.send(ISP_MSL(Msg=f"^1[REC] Guardada: ^7{recorder.route_name} ({count} pts)"))
        self.recorders.pop(plid)

    def process(self, plid: int, coordinates: Coordinates, speed: Speed):
        """Analiza la telemetría y decide si soltar un waypoint."""
        recorder = self.recorders.get(plid)
        if not recorder: return

        # [!] FIX 1: Escudo de memoria. Clonamos los objetos para evitar 
        # que InSim sobreescriba los valores de los waypoints guardados.
        safe_coords = copy.deepcopy(coordinates)
        safe_speed = copy.deepcopy(speed)

        # Si es el primer punto de la historia
        if not recorder.waypoints:
            recorder._add_waypoint(safe_coords, safe_speed)
            return

        # 1. Calcular distancia actual recorrida
        previous = recorder.waypoints[-1].coordinates
        dist_m = calc_dist_3d(previous.x_m, previous.y_m, previous.z_m, safe_coords.x_m, safe_coords.y_m, safe_coords.z_m)
        
        # Calcular umbral de distancia dinámica basado en la velocidad
        speed_ms = safe_speed.speed_kmh / 3.6
        ideal_dist = speed_ms * recorder.TARGET_TIME_s
        dynamic_dist_threshold = max(recorder.MIN_DYNAMIC_DIST_m, min(recorder.MAX_DYNAMIC_DIST_m, ideal_dist))

        # Si no hemos recorrido ni el mínimo absoluto, ignoramos
        if dist_m < recorder.MIN_DYNAMIC_DIST_m: 
            return

        # Si tenemos menos de 2 puntos, solo usamos la distancia
        if len(recorder.waypoints) < 2:
            if dist_m >= dynamic_dist_threshold:
                recorder._add_waypoint(safe_coords, safe_speed)
            return

        # 2. Calcular ángulo actual de diferencia respecto la trayectoria
        point_1 = recorder.waypoints[-2].coordinates
        point_2 = recorder.waypoints[-1].coordinates
        angle_diff_lfs = calc_deviation_angle(point_1.x, point_1.y, point_2.x, point_2.y, safe_coords.x, safe_coords.y)
        
        # [!] FIX 2: Conversión de unidades brutas LFS a grados reales
        angle_diff_deg = (angle_diff_lfs / 32768.0) * 180.0
        
        # 3. Lógica de decisión
        should_save = False
        
        if dist_m >= dynamic_dist_threshold: 
            should_save = True
        elif abs(safe_speed.speed_kmh - recorder.waypoints[-1].speed.speed_kmh) > recorder.SPEED_DELTA_kmh: 
            should_save = True
        elif abs(angle_diff_deg) > recorder.ANGLE_DELTA_degrees:  # Usamos grados contra grados
            should_save = True

        if should_save:
            recorder._add_waypoint(safe_coords, safe_speed)

    def _save_to_disk(self, plid: int):
        try:
            with open("rutas_grabadas.txt", "a") as f:
                f.write(f"\n# --- {self.recorders[plid].route_name} ---\n")
                f.write(f"'{self.recorders[plid].route_name}': [\n")
                for waypoint in self.recorders[plid].waypoints:
                    f.write(f"    (({waypoint.coordinates.x}, {waypoint.coordinates.y}, {waypoint.coordinates.z}), {waypoint.speed.speed_lfs}),\n")
                f.write("],\n")
            return True
        except Exception as e:
            print(f"\n[!] ERROR FATAL GUARDANDO RUTA EN DISCO: {e}\n")
            return False
