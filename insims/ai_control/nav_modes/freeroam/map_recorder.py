from __future__ import annotations
import logging
import os
import json
import copy
import math
import threading
from dataclasses import dataclass, field, asdict, fields
from typing import Dict, Optional, List, Callable
from enum import Enum

from insims.users_management.main import Coordinates
from lfs_insim.insim_packet_class import ISP_MSL, ISP_MSO, CSVAL, SND
from lfs_insim.packet_sender_mixin import PacketSenderMixin
from lfs_insim.utils import CMDManager, calc_dist_3d, TextColors, calc_deviation_angle, calc_dist_point_to_segment_3d

from insims.ai_control.nav_modes.freeroam.enums import TrafficRule, AIManeuverState
from insims.ai_control.nav_modes.freeroam.graph import RoadLink, LateralLink, IntersectionZone, RoadSegment, LocationContext, SpecialRule
from insims.ai_control.nav_modes.freeroam.geometry import get_dist_to_polygon_edge_2d, calc_dist_point_to_segment_2d, is_point_in_polygon_2d
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
from insims.ai_control.nav_modes.freeroam.map_renderer import generate_map_image

logger = logging.getLogger(__name__)


class MapRecorder(PacketSenderMixin):
    def __init__(self, get_coords_fn: Callable[[int], Optional[Coordinates]], cmd_prefix: str = "!"):
        self.get_coords_fn = get_coords_fn
        
        # Nuestros tres pilares de datos del mapa:
        self.roads: Dict[str, RoadSegment] = {}
        self.zones: Dict[str, IntersectionZone] = {}
        self.road_links: Dict[str, RoadLink] = {}
        self.lateral_links: Dict[str, LateralLink] = {}
        self.special_rules: Dict[str, SpecialRule] = {}
        
        # Estado de grabación actual (¿Estamos grabando una vía o un enlace?)
        self.current_recording: Optional[RoadSegment|RoadLink|LateralLink|IntersectionZone|SpecialRule] = None
        self.auto_recording_enabled: bool = False
        self.default_traffic_rule: TrafficRule = TrafficRule.LHT
        
        # Nombre del mapa activo (para mostrar en los comandos y al guardar/cargar)
        self.active_map_name: Optional[str] = None
        
        # ==========================================
        # PARÁMETROS DE AJUSTE PARA LA IA (Usados en la lógica de grabación y también como referencia para la IA)
        # ==========================================
        self.TARGET_TIME_s = 0.5          
        self.MIN_DYNAMIC_DIST_m = 2.0     
        self.MAX_DYNAMIC_DIST_m = 60.0    
        self.ANGLE_DELTA_degrees = 15.0   
        
        self.recording_plid: Optional[int] = None  # PLID del jugador cuya telemetría se graba
        self._current_cmd_ucid: Optional[int] = None  # UCID del emisor del comando en curso
        self._post_record_callback: Optional[Callable[[str], None]] = None

        self.cmd_manager = CMDManager(cmd_prefix, "map")
        self._register_commands()

    # ==========================================
    # LÓGICA DE TELEMETRÍA (El "Grabador" real)
    # ==========================================
    def update_recording(self, player_coords: Coordinates, speed_kmh: float):
        """
        Grabador dinámico. Adapta la densidad de los nodos a la velocidad y curvatura del trazado.
        Soporta la grabación automática de vías, enlaces y zonas.
        """
        # Escudos: Solo grabamos si hay una sesión activa y el autograbado está en ON
        if not self.current_recording or not self.auto_recording_enabled:
            return
            
        # 1. Obtenemos la lista universal de nodos (Válido para TODO)
        nodes_list: list[Coordinates] = self.current_recording["nodes"]
        
        # Clonamos el objeto para evitar referencias mutables fantasma
        current_node = copy.deepcopy(player_coords)
        
        # 2. Si es el primer punto de la grabación, lo metemos directo
        if not nodes_list:
            nodes_list.append(current_node)
            logger.info(f"[Auto-Rec] Nodo #1 guardado (Motivo: Punto de Origen).")
            self.send(ISP_MSL(Msg=f"{TextColors.CYAN}Nodo #1: {TextColors.WHITE}Punto de Origen"))
            return
            
        # 3. Distancia 3D actual respecto al último punto guardado
        last_node = nodes_list[-1]
        
        # Pasamos los 6 argumentos posicionales extrayendo x_m, y_m, z_m
        dist_m = calc_dist_3d(
            last_node.x_m, last_node.y_m, last_node.z_m, 
            current_node.x_m, current_node.y_m, current_node.z_m
        )
        
        # 4. Calcular distancia umbral dinámica basada en la velocidad actual
        speed_ms = speed_kmh / 3.6
        ideal_dist = speed_ms * self.TARGET_TIME_s
        dynamic_dist_threshold = max(self.MIN_DYNAMIC_DIST_m, min(self.MAX_DYNAMIC_DIST_m, ideal_dist))
        
        # Si no hemos recorrido la distancia mínima absoluta, ignoramos este frame por completo
        if dist_m < self.MIN_DYNAMIC_DIST_m:
            return
            
        # 5. Si tenemos menos de 2 puntos...
        if len(nodes_list) < 2:
            if dist_m >= dynamic_dist_threshold:
                nodes_list.append(current_node)
                logger.info(f"[Auto-Rec] Nodo #2 guardado (Motivo: Distancia inicial {dist_m:.1f}m).")
                self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Nodo #2: {TextColors.WHITE}Distancia inicial ({dist_m:.1f}m)"))
            return
            
        # 6. Cálculo del ángulo de desvío (Detección de Curvas)
        point_1 = nodes_list[-2]
        point_2 = nodes_list[-1]
        
        angle_diff_lfs = calc_deviation_angle(
            int(point_1.x), int(point_1.y), 
            int(point_2.x), int(point_2.y), 
            int(current_node.x), int(current_node.y)
        )
        
        # Convertimos unidades LFS a grados reales
        angle_diff_deg = (angle_diff_lfs / 32768.0) * 180.0
        
        # 7. Evaluar condiciones de guardado y registrar el motivo
        should_save = False
        debug_reason = ""
        
        # Condición A: Hemos recorrido la distancia dinámica (Rectas y curvas amplias)
        if dist_m >= dynamic_dist_threshold:
            should_save = True
            debug_reason = f"Distancia ({dist_m:.1f}m >= umbral {dynamic_dist_threshold:.1f}m a {speed_kmh:.0f}km/h)"
            
        # Condición B: Curvatura pronunciada (horquillas, giros bruscos)
        elif abs(angle_diff_deg) > self.ANGLE_DELTA_degrees:
            should_save = True
            debug_reason = f"Ángulo ({abs(angle_diff_deg):.1f}º > {self.ANGLE_DELTA_degrees}º)"
            
        # 8. Guardar el punto y notificar por consola (o chat)
        if should_save:
            nodes_list.append(current_node)
            
            # --- DEBUG EN CONSOLA ---
            logger.info(f"[Auto-Rec] Nodo #{len(nodes_list)} guardado | {debug_reason}")
            
            # --- DEBUG EN JUEGO (Descomentar para usar) ---
            # CUIDADO: Si grabas a alta velocidad, esto puede saturar el chat de LFS.
            color = TextColors.GREEN if "Distancia" in debug_reason else TextColors.YELLOW
            self.send(ISP_MSL(Msg=f"{color}Nodo #{len(nodes_list)}: {TextColors.WHITE}{debug_reason}"))

    def get_location_context(self, px: float, py: float, pz: float, 
                             find_roads: bool = True, 
                             find_links: bool = True, 
                             find_zones: bool = True) -> LocationContext:
        """Calcula matemáticamente qué vías, enlaces y zonas hay alrededor de unas coordenadas."""
        ctx = LocationContext()
        
        # 1. Buscar la Vía más cercana
        if find_roads and self.roads:
            closest_road = self.get_closest_geometry(px, py, pz, self.roads.items(), lambda r: r.nodes)
            if closest_road['id'] is not None:
                ctx.road_id = closest_road['id']
                ctx.road_dist = closest_road['dist']
                # Sacar el nodo exacto
                closest_node = self.get_closest_geometry(px, py, pz, enumerate(self.roads[ctx.road_id].nodes), lambda node: node)
                ctx.road_node_idx = closest_node['id']

        # 2. Buscar el Enlace más cercano
        if find_links:
            all_links = {**self.road_links, **self.lateral_links}
            if all_links:
                closest_link = self.get_closest_geometry(px, py, pz, all_links.items(), lambda l: l.nodes)
                if closest_link['id'] is not None:
                    ctx.link_id = closest_link['id']
                    ctx.link_dist = closest_link['dist']
                    ctx.link_type = "LatLink" if ctx.link_id in self.lateral_links else "RoadLink"

        # 3. Buscar la Zona más cercana
        if find_zones and self.zones:
            min_dist_to_shape = float('inf')
            closest_zone_id = None
            closest_zone_obj = None

            for z_id, zone in self.zones.items():
                nodes = zone.nodes
                num_nodos = len(nodes)
                dist_to_shape = float('inf')

                if num_nodos == 1:
                    dist_to_shape = math.hypot(px - nodes[0].x_m, py - nodes[0].y_m)
                elif num_nodos == 2:
                    dist_to_shape = calc_dist_point_to_segment_2d(px, py, nodes[0].x_m, nodes[0].y_m, nodes[1].x_m, nodes[1].y_m)
                elif num_nodos >= 3:
                    if is_point_in_polygon_2d(px, py, nodes):
                        dist_to_shape = 0.0
                    else:
                        dist_to_shape = get_dist_to_polygon_edge_2d(px, py, nodes)

                if dist_to_shape < min_dist_to_shape:
                    min_dist_to_shape = dist_to_shape
                    closest_zone_id = z_id
                    closest_zone_obj = zone

            if closest_zone_id:
                ctx.zone_id = closest_zone_id
                ctx.zone_dist = min_dist_to_shape
                ctx.zone_radius = closest_zone_obj.radius_m

        return ctx

    def _register_commands(self):
        """Registra los comandos de mapeo usando el CMDManager, ordenados lógicamente."""
        (self.cmd_manager
         
            # ==========================================
            # 1. GESTIÓN DE MAPAS
            # ==========================================
            .add_cmd('list_maps', 'Muestra los mapas guardados en disco', 
                     None, self._cmd_list_maps)
            .add_cmd('set_map', 'Define el mapa actual o crea uno nuevo', 
                     (('map_name', str),), self._cmd_set_map)
            .add_cmd('save', 'Guarda el mapa activo en el disco duro', 
                     None, self._cmd_save_map)
            .add_cmd('del_map', '¡Elimina un mapa entero del disco duro!', 
                     (('map_name', str),), self._cmd_del_map)
                     
            # ==========================================
            # 2. CREACIÓN Y GRABACIÓN GEOMÉTRICA
            # ==========================================
            .add_cmd('rec_road', 'Graba los nodos de una vía nueva o existente (usa el mismo ID para actualizarla)', 
                     (('road_id', str),), self._cmd_rec_road)
            .add_cmd('rec_roadlink', 'Graba un enlace entre dos vías (origen y destino) o actualiza su geometría si ya existe', 
                     (('origen', str), ('destino', str)), self._cmd_rec_roadlink)
            .add_cmd('rec_laterallink', 'Graba un enlace entre dos carriles (izquierdo y derecho) o actualiza su geometría si ya existe', 
                     (('road_a', str), ('road_b', str)), self._cmd_rec_laterallink)
            .add_cmd('rec_zone', 'Crea o actualiza una zona de intersección grabando su área de nodos y sus reglas de prioridad',
                     (('zone_id', str),), self._cmd_rec_zone)
            .add_cmd('rec_special_rule', 'Graba una regla especial (2 nodos: inicio y fin)',
                     (('rule_id', str),), self._cmd_rec_special_rule)
            
            # ==========================================
            # 3. COMANDOS DE CONTROL DE GRABACIÓN
            # ==========================================
            .add_cmd('rec_addp', 'Agrega un nuevo punto a la grabación actual',
                     None, self._cmd_rec_add_point, is_mso_required=True)
            .add_cmd('rec_auto', 'Agrega puntos automáticamente',
                     (('true/false', str),), self._cmd_rec_auto)
            .add_cmd('end', 'Finaliza la grabación actual y guarda los cambios en memoria (usa el mismo ID para actualizar)', 
                     None, self._cmd_rec_end)
            .add_cmd('cancel', 'Cancela la grabación actual sin guardar los cambios (¡Cuidado, se perderá lo grabado hasta ahora!)', 
                     None, self._cmd_rec_cancel)
            
            # ==========================================
            # 4. INFORMACIÓN Y DEBUGGING
            # ==========================================
            .add_cmd('stats', 'Muestra el recuento y las listas de objetos en memoria', 
                     None, self._cmd_stats)
            .add_cmd('info', 'Muestra las propiedades detalladas de un objeto', 
                     (('id', str),), self._cmd_info)
            .add_cmd('whereami', 'Busca tu posición', 
                     (('road/link/zone', str),), self._cmd_whereami, is_mso_required=True)
            .add_cmd('check', 'Audita el mapa buscando errores de integridad', 
                     None, self._cmd_check_map)
            
            # ==========================================
            # 5. EDICIÓN Y LIMPIEZA
            # ==========================================
            .add_cmd('set', 'Edita propiedades de cualquier objeto de forma inteligente', 
                     (('id', str), ('prop', str), ('val', str)), self._cmd_set)
            .add_cmd('del', 'Elimina un objeto por ID (Borrado en Cascada)', 
                     (('id', str),), self._cmd_del)
            .add_cmd('rec_road_rule', 'Define la regla de tráfico (RHT o LHT) default', 
                     (('RHT/LHT', str),), self._cmd_rec_road_rule)
            
            # ==========================================
            # 6. EXTRA
            # ==========================================
            .add_cmd('closed_roads', 'Muestra un listado de los roads cerrados',
                     None, self._cmd_is_closed_road)

        )
        
    # ==========================================
    # LÓGICA DE COMANDOS
    # ==========================================
    
    # ==========================================
    # 1. GESTIÓN DE MAPAS
    # ==========================================
    
    def _cmd_list_maps(self):
        """Muestra los mapas guardados en disco."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        maps_folder = os.path.join(base_dir, "maps")
        
        if not os.path.exists(maps_folder):
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}La carpeta 'maps' aún no existe."))
            return
            
        # Filtramos solo los archivos .json y quitamos la extensión
        archivos = [f.replace('.json', '') for f in os.listdir(maps_folder) if f.endswith('.json')]
        
        if not archivos:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}No hay mapas guardados todavía."))
            return
            
        self.send(ISP_MSL(Msg=f"{TextColors.GREEN}=== {TextColors.WHITE}Mapas Disponibles {TextColors.GREEN}==="))
        
        # Mostramos los mapas de 4 en 4. 
        # Esto sirve como ANTI-CRASH natural (es casi imposible que 4 nombres superen los 100 caracteres)
        # y evita que los nombres se corten por la mitad.
        chunk_size = 4
        for i in range(0, len(archivos), chunk_size):
            chunk = archivos[i:i + chunk_size]
            line = f"{TextColors.GREEN} | {TextColors.WHITE}".join(chunk)
            
            # Cortamos a 128 por seguridad extrema (por si algún nombre de mapa es absurdamente largo)
            safe_line = f"{TextColors.WHITE}{line}"[:128]
            self.send(ISP_MSL(Msg=safe_line))

        # Indicamos cuál está cargado actualmente
        if self.active_map_name:
            self.send(ISP_MSL(Msg=f'{TextColors.YELLOW}Mapa activo actual: {TextColors.WHITE}{self.active_map_name}'))
    
    def _cmd_set_map(self, map_name: str):
        """Define el nombre del mapa y lo carga si ya existe."""
        # Protección para no perder la grabación actual
        if self.current_recording is not None:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: Estás grabando algo. Usa !map cancel primero.", Sound=SND.INVALIDKEY))
            return

        # Evitamos recargar el mismo mapa inútilmente
        if self.active_map_name == map_name:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}El mapa {map_name} ya está activo."))
            return
            
        self.active_map_name = map_name
        
        # Intentamos cargarlo
        if self._load_map_from_disk(map_name):
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Mapa {TextColors.WHITE}{map_name}{TextColors.GREEN} cargado desde el disco."))
        else:
            # Si no existe, nos aseguramos de vaciar la memoria para empezar uno nuevo limpio
            self.roads.clear()
            self.zones.clear()
            self.road_links.clear()
            self.lateral_links.clear()
            self.special_rules.clear()
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Nuevo mapa inicializado: {TextColors.WHITE}{map_name}{TextColors.YELLOW} (Vacío)."))

    def _load_map_from_disk(self, map_name: str) -> bool:
        """Intenta cargar un mapa del disco a la memoria RAM. Retorna True si existía y se cargó bien."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, "maps", f"{map_name}.json")
        
        if not os.path.exists(full_path):
            return False
            
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Limpiamos la memoria ANTES de cargar para evitar mezclas con mapas anteriores
            self.roads.clear()
            self.zones.clear()
            self.road_links.clear()
            self.lateral_links.clear()
            self.special_rules.clear()

            # ==========================================
            # 1-5. Reconstruir Objetos Dinámicamente
            # ==========================================
            # Relacionamos la clave del JSON con el diccionario destino y su Dataclass
            mapeo_carga = [
                ("roads", self.roads, RoadSegment),
                ("zones", self.zones, IntersectionZone),
                ("road_links", self.road_links, RoadLink),
                ("lateral_links", self.lateral_links, LateralLink),
                ("special_rules", self.special_rules, SpecialRule),
            ]

            for json_key, target_dict, dataclass_type in mapeo_carga:
                valid_fields = {f.name for f in fields(dataclass_type)}
                
                for item_id, item_data in data.get(json_key, {}).items():
                    # Como todos usan 'nodes', la conversión es universal
                    if "nodes" in item_data:
                        item_data["nodes"] = [Coordinates(**n) for n in item_data["nodes"]]
                        
                    # =========================================================
                    # NUEVO: Casteo de Enums (Desde JSON int/str a objeto Enum)
                    # =========================================================
                    if "traffic_rule" in item_data and item_data["traffic_rule"] is not None:
                        item_data["traffic_rule"] = TrafficRule(item_data["traffic_rule"])
                        
                    if "indicators" in item_data and item_data["indicators"] is not None:
                        item_data["indicators"] = CSVAL.INDICATORS(item_data["indicators"])
                        
                    filtered_data = {k: v for k, v in item_data.items() if k in valid_fields}
                    target_dict[item_id] = dataclass_type(**filtered_data)
                
            return True
            
        except Exception as e:
            logger.error(f"Error crítico cargando el mapa {map_name}: {e}")
            self.send(ISP_MSL(Msg=f"{TextColors.RED}El archivo del mapa está corrupto. Revisa la consola.", Sound=SND.INVALIDKEY))
            return False

    def _cmd_save_map(self):
        """Guarda el mapa activo en el disco duro."""
        # Escudo de seguridad inicial
        if not self.active_map_name:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: No has seleccionado ningún mapa. Usa {TextColors.WHITE}!map set_map <nombre>{TextColors.RED} primero.", Sound=SND.INVALIDKEY))
            return
            
        # Protección para no guardar mapas rotos/a medias
        if self.current_recording is not None:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: Termina (!map end) o cancela la grabación actual antes de guardar.", Sound=SND.INVALIDKEY))
            return

        # 1. Definimos el nombre del archivo en base al mapa activo
        filename = f"{self.active_map_name}.json"
        
        # 2. Rutas dinámicas e inteligentes
        # os.path.abspath(__file__) apunta siempre a donde esté este script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        maps_folder = os.path.join(base_dir, "maps")
        
        # Si la carpeta 'maps' no existe, la creamos (exist_ok=True ahorra el 'if not os.path.exists')
        os.makedirs(maps_folder, exist_ok=True)
            
        # La ruta final absoluta donde se guardará el JSON
        full_path = os.path.join(maps_folder, filename)
            
        try:
            # Preparamos el diccionario maestro (ADAPTADO A LA NUEVA ESTRUCTURA TOPOLÓGICA)
            data_to_save = {
                "roads": {k: asdict(v) for k, v in self.roads.items()},
                "zones": {k: asdict(v) for k, v in self.zones.items()},
                "road_links": {k: asdict(v) for k, v in self.road_links.items()},
                "lateral_links": {k: asdict(v) for k, v in self.lateral_links.items()},
                "special_rules": {k: asdict(v) for k, v in self.special_rules.items()},
            }
            
            # Guardado en disco
            with open(full_path, 'w', encoding='utf-8') as f:
                # ensure_ascii=False permite guardar bien tildes o caracteres especiales
                # EL TRUCO MÁGICO PARA LOS ENUMS: default=lambda obj...
                json.dump(
                    data_to_save, 
                    f, 
                    indent=4, 
                    ensure_ascii=False,
                    default=lambda obj: obj.value if isinstance(obj, Enum) else str(obj)
                )
                
            # Feedback al usuario
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Mapa guardado con éxito: {TextColors.WHITE}{filename}"))
            logger.info(f"Mapa guardado en ruta absoluta: {full_path}")

            # =========================================================
            # [!] EJECUCIÓN ASÍNCRONA (Segundo plano)
            # =========================================================
            logger.info(f"Iniciando hilo en segundo plano para actualizar imagen: {full_path}")
            
            # Creamos el hilo. Le pasamos la función SIN paréntesis al 'target' 
            # y los argumentos como una tupla en 'args' (recuerda la coma final si es solo 1 argumento).
            # daemon=True hace que el hilo se cierre automáticamente si apagas el script principal.
            img_thread = threading.Thread(
                target=generate_map_image, 
                args=(full_path,), 
                daemon=True
            )
            
            # Arrancamos el hilo
            img_thread.start()
            
        except TypeError as te:
            # Captura específica por si algún objeto anidado (como Coordinates) da problemas al serializar
            logger.error(f"Error de serialización JSON en el mapa: {te}")
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error de formato al guardar. Revisa la consola.", Sound=SND.INVALIDKEY))
        except Exception as e:
            logger.error(f"Error guardando el mapa: {e}")
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error interno al guardar el mapa. Revisa la consola.", Sound=SND.INVALIDKEY))

    def _cmd_del_map(self, map_name: str):
        """Elimina un mapa entero del disco duro y limpia la memoria RAM si estaba en uso."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, "maps", f"{map_name}.json")
        
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                self.send(ISP_MSL(Msg=f"{TextColors.GREEN}El mapa {TextColors.WHITE}{map_name}{TextColors.GREEN} ha sido destruido del disco."))
                logger.info(f"Archivo de mapa eliminado: {full_path}")
                
                # Si borramos el mapa en el que estábamos trabajando, reseteamos la memoria RAM
                if self.active_map_name == map_name:
                    self.active_map_name = None
                    self.roads.clear()
                    self.zones.clear()
                    self.road_links.clear()     # <-- ADAPTADO a la nueva estructura
                    self.lateral_links.clear()  # <-- ADAPTADO a la nueva estructura
                    
                    # Abortamos cualquier grabación que estuviera a medias
                    if self.current_recording:
                        self.current_recording = None
                        
                    self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}El mapa activo ha sido borrado. Memoria RAM reseteada."))
                    
            except Exception as e:
                logger.error(f"Error al borrar el mapa {map_name}: {e}")
                self.send(ISP_MSL(Msg=f"{TextColors.RED}Error de sistema al borrar el archivo. Revisa la consola.", Sound=SND.INVALIDKEY))
        else:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: No se encontró el archivo '{map_name}.json'.", Sound=SND.INVALIDKEY))

    # ==========================================
    # 2. CREACIÓN Y GRABACIÓN GEOMÉTRICA
    # ==========================================

    def _cmd_rec_road(self, road_id: str):
        """Inicia la grabación de los nodos de una vía (crea una nueva o re-graba una existente de forma segura)."""
        pass  # recording_plid se fija desde la UI antes de iniciar la grabación
        # 1. Escudo: Necesitamos un mapa activo
        if not self.active_map_name:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: Selecciona un mapa primero con {TextColors.WHITE}!map set_map <nombre>", Sound=SND.INVALIDKEY))
            return
            
        # 2. Escudo: Evitar solapamiento de grabaciones
        if self.current_recording is not None:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Ya hay una grabación en curso. Escribe !map end o !map cancel primero.", Sound=SND.INVALIDKEY))
            return
            
        # 3. Preparamos el búfer temporal con tu genial idea del flag 'is_new'
        self.current_recording = {
            "type": "road",
            "road_id": road_id,
            "nodes": [],
            "is_new": road_id not in self.roads
        }

        # 4. Feedback claro al usuario
        if self.current_recording["is_new"]:
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Grabando NUEVA vía: {TextColors.WHITE}{road_id}{TextColors.GREEN}."))
        else:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Re-grabando vía: {TextColors.WHITE}{road_id}{TextColors.YELLOW}. La original se mantendrá hasta que uses !map end."))
            
        # 5. Recordatorio rápido de los controles
        self.send(ISP_MSL(Msg=f"{TextColors.CYAN}Usa !map rec_addp para nodos manuales o !map rec_auto true para grabar en movimiento."))

    @staticmethod
    def _parse_road_arg(arg: str):
        """Separa 'road_id,sufijo' en (road_id, sufijo). Sin coma devuelve (arg, '')."""
        if ',' in arg:
            parts = arg.split(',', 1)
            return parts[0].strip(), parts[1].strip()
        return arg.strip(), ""

    def _cmd_rec_roadlink(self, origen: str, destino: str):
        """Inicia la grabación de un enlace longitudinal entre dos vías."""
        pass  # recording_plid se fija desde la UI antes de iniciar la grabación
        # Escudos básicos
        if not self.active_map_name:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: Selecciona un mapa primero con {TextColors.WHITE}!map set_map <nombre>", Sound=SND.INVALIDKEY))
            return

        if self.current_recording:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Ya hay una grabación en curso. Escribe !map end o !map cancel primero.", Sound=SND.INVALIDKEY))
            return

        from_road, from_suffix = self._parse_road_arg(origen)
        to_road,   to_suffix   = self._parse_road_arg(destino)
        link_id = f"{from_road}{from_suffix}->{to_road}{to_suffix}"

        if from_road not in self.roads:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Advertencia: La vía origen '{TextColors.WHITE}{from_road}{TextColors.YELLOW}' aún no existe en memoria."))
        if to_road not in self.roads:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Advertencia: La vía destino '{TextColors.WHITE}{to_road}{TextColors.YELLOW}' aún no existe en memoria."))

        is_new = link_id not in self.road_links

        self.current_recording = {
            "type": "road_link",
            "link_id": link_id,
            "origin_id": from_road,
            "dest_id": to_road,
            "from_suffix": from_suffix,
            "to_suffix": to_suffix,
            "nodes": [],
            "is_new": is_new
        }

        if is_new:
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Grabando NUEVO LINK: {TextColors.WHITE}{link_id}{TextColors.GREEN}."))
        else:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Re-grabando LINK: {TextColors.WHITE}{link_id}{TextColors.YELLOW}. El original se mantendrá hasta usar !map end."))

        self.send(ISP_MSL(Msg=f"{TextColors.CYAN}Conduce la trayectoria y usa !map end al terminar."))

    def _cmd_rec_laterallink(self, road_a: str, road_b: str):
        """Inicia la grabación de un enlace lateral (cambio de carril) entre dos vías paralelas."""
        pass  # recording_plid se fija desde la UI antes de iniciar la grabación
        # Escudos básicos
        if not self.active_map_name:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: Selecciona un mapa primero con {TextColors.WHITE}!map set_map", Sound=SND.INVALIDKEY))
            return

        if self.current_recording:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Ya hay una grabación en curso. Escribe !map end o cancel primero.", Sound=SND.INVALIDKEY))
            return

        a_road, suffix_a = self._parse_road_arg(road_a)
        b_road, suffix_b = self._parse_road_arg(road_b)
        link_id = f"{a_road}{suffix_a}<<>>{b_road}{suffix_b}"

        if a_road not in self.roads:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Aviso: El carril izquierdo '{TextColors.WHITE}{a_road}{TextColors.YELLOW}' no existe aún."))
        if b_road not in self.roads:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Aviso: El carril derecho '{TextColors.WHITE}{b_road}{TextColors.YELLOW}' no existe aún."))

        is_new = link_id not in self.lateral_links

        self.current_recording = {
            "type": "lateral_link",
            "link_id": link_id,
            "road_a": a_road,
            "road_b": b_road,
            "suffix_a": suffix_a,
            "suffix_b": suffix_b,
            "nodes": [],
            "is_new": is_new
        }

        if is_new:
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Grabando NUEVO ENLACE LATERAL: {TextColors.WHITE}{link_id}"))
        else:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Re-grabando ENLACE LATERAL: {TextColors.WHITE}{link_id}"))
            
        self.send(ISP_MSL(Msg=f"{TextColors.CYAN}Traza el cambio de carril y usa !map end al terminar."))
    
    def _cmd_rec_zone(self, zone_id: str):
        """Inicia la grabación de los nodos que delimitan una zona de intersección (punto, línea o polígono)."""
        pass  # recording_plid se fija desde la UI antes de iniciar la grabación
        # Escudos básicos
        if not self.active_map_name:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: Selecciona un mapa primero con {TextColors.WHITE}!map set_map", Sound=SND.INVALIDKEY))
            return

        if self.current_recording:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Ya hay una grabación en curso. Escribe !map end o !map cancel primero.", Sound=SND.INVALIDKEY))
            return

        # Comprobamos si la zona ya existe para el flag is_new
        is_new = zone_id not in self.zones

        # Preparamos el búfer temporal (CLAVES ADAPTADAS AL DATACLASS INTERSECTIONZONE)
        self.current_recording = {
            "type": "zone",
            "zone_id": zone_id,
            "nodes": [],  # <-- Match exacto con tu dataclass
            "is_new": is_new
        }

        # Feedback al usuario informando de la flexibilidad geométrica
        if is_new:
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Grabando NUEVA ZONA de conflicto: {TextColors.WHITE}{zone_id}"))
        else:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Re-grabando ZONA de conflicto: {TextColors.WHITE}{zone_id}"))
            
        self.send(ISP_MSL(Msg=f"{TextColors.CYAN}Captura: 1 punto (Centro), 2 (Línea) o 3+ (Polígono)."))
        self.send(ISP_MSL(Msg=f"{TextColors.CYAN}Usa !map rec_addp para marcar y !map end al terminar."))

    def _cmd_rec_special_rule(self, rule_id: str):
        """Inicia la grabación de una regla especial (2 nodos: inicio y fin)."""
        pass  # recording_plid se fija desde la UI antes de iniciar la grabación
        if not self.active_map_name:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: Selecciona un mapa primero con {TextColors.WHITE}!map set_map", Sound=SND.INVALIDKEY))
            return

        if self.current_recording:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Ya hay una grabación en curso. Escribe !map end o !map cancel primero.", Sound=SND.INVALIDKEY))
            return

        is_new = rule_id not in self.special_rules

        self.current_recording = {
            "type": "special_rule",
            "rule_id": rule_id,
            "nodes": [],
            "is_new": is_new
        }

        if is_new:
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Grabando NUEVA REGLA ESPECIAL: {TextColors.WHITE}{rule_id}"))
        else:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Re-grabando REGLA ESPECIAL: {TextColors.WHITE}{rule_id}"))

        self.send(ISP_MSL(Msg=f"{TextColors.CYAN}Captura EXACTAMENTE 2 nodos: inicio y fin."))
        self.send(ISP_MSL(Msg=f"{TextColors.CYAN}Usa !map rec_addp para marcar y !map end al terminar."))

    # ==========================================
    # 3. COMANDOS DE CONTROL DE GRABACIÓN
    # ==========================================

    def _cmd_rec_add_point(self, packet: ISP_MSO):
        """Agrega un punto manual a la grabación actual en base a la posición del jugador."""
        # 1. Escudo: ¿Estamos grabando algo?
        if not self.current_recording:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: No hay ninguna grabación en curso. Usa !map rec_road, rec_zone, etc.", Sound=SND.INVALIDKEY))
            return

        # 2. Obtener la posición actual del coche
        coords = self.get_coords_fn(packet.UCID)
        if not coords:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: No se pudo obtener tu telemetría (¿Estás en pista?).", Sound=SND.INVALIDKEY))
            return

        # 3. Guardar el punto directamente (funciona para vías, enlaces y zonas)
        self.current_recording["nodes"].append(coords)
        
        # 4. Feedback dinámico
        count = len(self.current_recording["nodes"])
        tipo = self.current_recording.get("type", "objeto").upper()
        
        self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Punto de {tipo} añadido {TextColors.WHITE}(Nodo/Vértice {count}){TextColors.GREEN}."))

    def _cmd_rec_auto(self, state_str: str):
        """Activa o desactiva la captura automática de coordenadas en movimiento."""
        state_lower = state_str.lower()
        
        # 1. Parseador inteligente y flexible
        if state_lower in ['true', 'on', '1', 'si', 'yes', 't']:
            new_state = True
        elif state_lower in ['false', 'off', '0', 'no', 'f']:
            new_state = False
        else:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: Usa {TextColors.WHITE}!map rec_auto true{TextColors.RED} o {TextColors.WHITE}false{TextColors.RED}.", Sound=SND.INVALIDKEY))
            return

        # 2. Advertencia amistosa si lo activan sin estar grabando nada
        if new_state and not self.current_recording:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Aviso: Autograbado listo, pero recuerda iniciar una grabación primero (!map rec_road, etc.)."))
            
        # 3. Aplicar el cambio a la variable de estado
        self.auto_recording_enabled = new_state
        
        # 4. Feedback visual claro
        if new_state:
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Autograbado {TextColors.WHITE}ACTIVADO{TextColors.GREEN}. Conduce para trazar la ruta automáticamente."))
        else:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Autograbado {TextColors.WHITE}DESACTIVADO{TextColors.YELLOW}. Usa !map rec_addp para puntos manuales."))

    def _cmd_rec_end(self):
        """Finaliza la grabación actual, instancia la Dataclass correspondiente y guarda los cambios en memoria."""
        # 1. Escudos y validaciones
        if not self.current_recording:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: No hay ninguna grabación activa.", Sound=SND.INVALIDKEY))
            return

        nodes = self.current_recording.get("nodes", [])
        if not nodes:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Aviso: No se ha grabado ningún nodo. Operación cancelada."))
            self.current_recording = None
            self.auto_recording_enabled = False
            return

        rec_type = self.current_recording.get("type")
        is_new = self.current_recording.get("is_new", True)
        mensaje_extra = ""

        # 2. Materialización basada en el 'type'
        try:
            # ==========================================
            # GUARDADO DE ROAD
            # ==========================================
            if rec_type == "road":
                obj_id = self.current_recording["road_id"]
                if not is_new and obj_id in self.roads:
                    self.roads[obj_id].nodes = nodes
                else:
                    self.roads[obj_id] = RoadSegment(road_id=obj_id, nodes=nodes, traffic_rule=self.default_traffic_rule)
                msg_tipo = "Vía"

            # ==========================================
            # GUARDADO DE ROAD LINK (Enlace longitudinal)
            # ==========================================
            elif rec_type == "road_link":
                orig = self.current_recording["origin_id"]
                dest = self.current_recording["dest_id"]
                obj_id = self.current_recording["link_id"]
                
                if not is_new and obj_id in self.road_links:
                    self.road_links[obj_id].nodes = nodes
                else:
                    self.road_links[obj_id] = RoadLink(
                        from_road_id=orig,
                        to_road_id=dest,
                        from_suffix=self.current_recording.get("from_suffix", ""),
                        to_suffix=self.current_recording.get("to_suffix", ""),
                        nodes=nodes
                    )
                msg_tipo = "Enlace longitudinal"

            # ==========================================
            # GUARDADO DE LATERAL LINK (Con auto-cálculo)
            # ==========================================
            elif rec_type == "lateral_link":
                a = self.current_recording["road_a"]
                b = self.current_recording["road_b"]
                obj_id = self.current_recording["link_id"]
                
                # MATEMÁTICAS: Auto-Detección de carriles opuestos
                es_opuesto = False
                
                # Verificamos si ambas vías ya existen y tienen geometría trazada
                if a in self.roads and b in self.roads:
                    nodos_l = self.roads[a].nodes
                    nodos_r = self.roads[b].nodes
                    
                    if len(nodos_l) >= 2 and len(nodos_r) >= 2:
                        # Calculamos el vector global de cada vía (Desde el Inicio hasta el Final)
                        vl_x = nodos_l[-1].x - nodos_l[0].x
                        vl_y = nodos_l[-1].y - nodos_l[0].y
                        
                        vr_x = nodos_r[-1].x - nodos_r[0].x
                        vr_y = nodos_r[-1].y - nodos_r[0].y
                        
                        # Producto Escalar (Dot Product)
                        # Si es negativo (< 0), significa que las vías apuntan en direcciones generales opuestas
                        dot_product = (vl_x * vr_x) + (vl_y * vr_y)
                        if dot_product < 0:
                            es_opuesto = True
                            mensaje_extra = f" {TextColors.CYAN}(¡Detectado como carril de sentido contrario!)"

                if not is_new and obj_id in self.lateral_links:
                    # Si solo estamos actualizando la geometría del link, conservamos las reglas que el usuario ya hubiera editado a mano
                    self.lateral_links[obj_id].nodes = nodes
                else:
                    # Si es nuevo, aplicamos la magia detectada
                    self.lateral_links[obj_id] = LateralLink(
                        road_a=a,
                        road_b=b,
                        suffix_a=self.current_recording.get("suffix_a", ""),
                        suffix_b=self.current_recording.get("suffix_b", ""),
                        nodes=nodes,
                        opposing=es_opuesto,
                        made_to_overtake=es_opuesto  # Si es opuesto, instintivamente es para adelantar
                    )
                msg_tipo = "Enlace lateral"

            # ==========================================
            # GUARDADO DE ZONAS
            # ==========================================
            elif rec_type == "zone":
                obj_id = self.current_recording["zone_id"]
                if not is_new and obj_id in self.zones:
                    self.zones[obj_id].nodes = nodes
                else:
                    self.zones[obj_id] = IntersectionZone(zone_id=obj_id, nodes=nodes)
                msg_tipo = "Zona"

            # ==========================================
            # GUARDADO DE REGLA ESPECIAL
            # ==========================================
            elif rec_type == "special_rule":
                obj_id = self.current_recording["rule_id"]
                if len(nodes) != 2:
                    self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: Una SpecialRule requiere exactamente 2 nodos (inicio y fin). Grabados: {len(nodes)}.", Sound=SND.INVALIDKEY))
                    return
                if not is_new and obj_id in self.special_rules:
                    self.special_rules[obj_id].nodes = nodes
                else:
                    self.special_rules[obj_id] = SpecialRule(rule_id=obj_id, nodes=nodes)
                msg_tipo = "Regla especial"

            else:
                self.send(ISP_MSL(Msg=f"{TextColors.RED}Error crítico: Tipo de geometría desconocido.", Sound=SND.INVALIDKEY))
                return

            # 3. Feedback final
            accion = "CREADO/A" if is_new else "ACTUALIZADO/A"
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}{msg_tipo} '{TextColors.WHITE}{obj_id}{TextColors.GREEN}' {accion} con {len(nodes)} nodos.{mensaje_extra}"))

            if self._post_record_callback:
                self._post_record_callback(obj_id)

        except Exception as e:
            logger.error(f"Error al finalizar la grabación: {e}")
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error interno al guardar. Revisa la consola.", Sound=SND.INVALIDKEY))

        finally:
            # 4. Limpieza garantizada
            self.current_recording = None

    def _cmd_rec_cancel(self):
        """Cancela la grabación en curso y descarta todos los nodos capturados."""
        
        # 1. Escudo defensivo
        if not self.current_recording:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: No hay ninguna grabación activa en este momento.", Sound=SND.INVALIDKEY))
            return
            
        # 2. Extraemos el tipo para dar un feedback más personalizado (opcional pero queda pro)
        geom_type = self.current_recording.get("type", "geometría")
        
        # 3. Purga completa de los estados de grabación
        self.current_recording = None
        self.auto_recording_enabled = False
        
        # 4. Feedback al usuario
        self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Grabación de '{geom_type}' cancelada. Se han descartado los nodos."))
        logger.info(f"El usuario canceló la grabación de un(a) {geom_type}.")

    # ==========================================
    # 4. INFORMACIÓN Y DEBUGGING
    # ==========================================

    def _cmd_stats(self):
        """Muestra el recuento y las listas de objetos en memoria con sistema anti-flood."""
        if not self.active_map_name:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: No hay ningún mapa activo ({TextColors.WHITE}!map set_map{TextColors.RED})."))
            return

        # 1. Encabezado principal
        self.send(ISP_MSL(Msg=f"{TextColors.GREEN}--- Info de: {TextColors.WHITE}{self.active_map_name} {TextColors.GREEN}---"))

        # 2. Función auxiliar optimizada (Mezcla de tu idea y protección de flood)
        def enviar_resumen_id(titulo: str, color_titulo: str, ids: list):
            if not ids:
                self.send(ISP_MSL(Msg=f"{color_titulo}{titulo}: {TextColors.WHITE}Ninguno"))
                return
            
            # Si hay demasiados IDs, mostramos solo los primeros 15 para no saturar el chat
            MAX_IDS_DISPLAY = 15
            display_list = ids[:MAX_IDS_DISPLAY]
            texto_unido = ", ".join(display_list)
            
            # Añadimos el sufijo si hay más de los que mostramos
            if len(ids) > MAX_IDS_DISPLAY:
                texto_unido += f" {TextColors.YELLOW}(+{len(ids) - MAX_IDS_DISPLAY} más...)"

            # Sistema de troceado (Tu lógica de chunks de 100 caracteres)
            MAX_LEN = 100
            chunks = [texto_unido[i:i+MAX_LEN] for i in range(0, len(texto_unido), MAX_LEN)]
            
            # Enviamos el primer paquete con el título y conteo total
            conteo = f"{TextColors.WHITE}[{len(ids)}] "
            self.send(ISP_MSL(Msg=f"{color_titulo}{titulo} {conteo}{TextColors.WHITE}{chunks[0]}"))
            
            # Solo enviamos hasta 2 chunks extra para evitar flood masivo
            for chunk in chunks[1:3]: 
                self.send(ISP_MSL(Msg=f"{TextColors.WHITE}{chunk}"))

        # 3. Listado por categorías (NUEVA ESTRUCTURA)
        enviar_resumen_id("Vías", TextColors.CYAN, list(self.roads.keys()))
        enviar_resumen_id("Zonas", TextColors.CYAN, list(self.zones.keys()))
        enviar_resumen_id("RoadLinks", TextColors.YELLOW, list(self.road_links.keys()))
        enviar_resumen_id("LatLinks", TextColors.YELLOW, list(self.lateral_links.keys()))
        enviar_resumen_id("SpecialRules", TextColors.YELLOW, list(self.special_rules.keys()))

        # 4. Estado de grabación (Bonus)
        if self.current_recording:
            tipo = self.current_recording.get("type", "???").upper()
            nodos = len(self.current_recording.get("nodes", []))
            self.send(ISP_MSL(Msg=f"{TextColors.RED}>> GRABANDO: {TextColors.WHITE}{tipo} ({nodos} nodos)"))

    def _cmd_info(self, obj_id: str):
        """Muestra las propiedades de un objeto y comandos rápidos para editarlas."""
        if not self.active_map_name:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: Selecciona un mapa primero (!map set_map <nombre>)."))
            return

        # 1. Búsqueda inteligente, Tipado y Comando de regrabación
        obj = None
        title = ""
        rec_cmd = ""
        
        if obj_id in self.roads:
            obj = self.roads[obj_id]
            title = f"VÍA: {obj_id}"
            rec_cmd = f"!map rec_road {obj_id}"
        elif obj_id in self.zones:
            obj = self.zones[obj_id]
            title = f"ZONA: {obj_id}"
            rec_cmd = f"!map rec_zone {obj_id}"
        elif obj_id in self.road_links:
            obj = self.road_links[obj_id]
            title = f"ROADLINK: {obj_id}"
            rec_cmd = f"!map rec_road_link {obj.from_road_id} {obj.to_road_id}"
        elif obj_id in self.lateral_links:
            obj = self.lateral_links[obj_id]
            title = f"LATLINK: {obj_id}"
            rec_cmd = f"!map rec_lateral_link {obj.road_a} {obj.road_b}"
        elif obj_id in self.special_rules:
            obj = self.special_rules[obj_id]
            title = f"SPECIALRULE: {obj_id}"
            rec_cmd = f"!map rec_special_rule {obj_id}"
        else:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: ID '{obj_id}' no encontrado en Vías, Zonas, Links o SpecialRules."))
            return
            
        # 2. Mostrar el encabezado interactivo
        self.send(ISP_MSL(Msg=f"{TextColors.CYAN}--- INFO {title} ---"))
        
        atributos_a_mostrar = [(f.name, getattr(obj, f.name)) for f in fields(obj)]
        
        # 4. Procesar cada atributo dinámicamente
        for prop_name, val in atributos_a_mostrar:
            
            editable_tag = f"{TextColors.YELLOW}[NO EDITABLE]"
            display_val = ""
            
            # Caso A: IDs base y referencias estructurales (Inmutables)
            if prop_name in ["road_id", "zone_id", "link_id", "from_road_id", "to_road_id", "road_a", "road_b"]:
                display_val = str(val)
                # Se queda con [NO EDITABLE]
                
            # Caso B: Geometría (Nodos)
            elif prop_name == "nodes":
                display_val = f"{len(val)} nodos" if val else "Sin nodos"
                editable_tag = f"{TextColors.GREEN}[EDIT: {rec_cmd}]"

            # Caso C: Reglas de prioridad de Zonas
            elif prop_name == "priority_rules":
                if not val:
                    display_val = "Sin reglas"
                else:
                    display_val = " | ".join([f"[{r[0]}>{r[1]}]" for r in val if len(r)==2])
                editable_tag = f"{TextColors.GREEN}[EDIT: !map set {obj_id} {prop_name} add/del/clear;V1,V2]"
                
            # Caso D: Enums (TrafficRule, IndicatorType...)
            elif hasattr(val, 'name') and not isinstance(val, type):
                display_val = val.name # Muestra "RHT" o "OFF" en vez del objeto en memoria
                editable_tag = f"{TextColors.GREEN}[EDIT: !map set {obj_id} {prop_name} <val>]"

            # Caso E: Valores básicos editables (Booleanos, strings, ints y floats)
            else:
                if isinstance(val, bool):
                    display_val = f"{TextColors.GREEN}Sí" if val else f"{TextColors.RED}No"
                elif isinstance(val, list):
                    display_val = ", ".join(str(v) for v in val) if val else "None"
                else:
                    display_val = str(val) if val is not None else "None"
                    
                editable_tag = f"{TextColors.GREEN}[EDIT: !map set {obj_id} {prop_name} <val>]"

            # 5. Formateo y envío final por chat
            display_val = str(display_val).replace('\n', ' ')
            self.send(ISP_MSL(Msg=f"{TextColors.WHITE}{prop_name}: {TextColors.YELLOW}{display_val} {editable_tag}"))

    @staticmethod
    def get_closest_geometry(px: float, py: float, pz: float, items_iterator: iter, extract_geom_fn: callable) -> dict:
        """
        Busca la geometría más cercana (punto o segmentos) a unas coordenadas 3D.
        """
        best_match = {
            'id': None,
            'dist': float('inf'),
            'item': None,
            'ref_node': None
        }

        for item_id, item in items_iterator:
            geom: List[Coordinates] = extract_geom_fn(item)

            # Caso A: Es una lista de nodos
            if isinstance(geom, (list, tuple)):
                if not geom:
                    continue
                    
                # NUEVO: Si la lista tiene 1 solo punto, se trata como un nodo simple
                if len(geom) == 1:
                    nodo = geom[0]
                    dist = calc_dist_3d(px, py, pz, nodo.x_m, nodo.y_m, nodo.z_m)
                    if dist < best_match['dist']:
                        best_match.update({'id': item_id, 'dist': dist, 'item': item, 'ref_node': nodo})
                        
                # Si tiene 2 o más, se trata como segmentos de línea
                else:
                    for i in range(len(geom) - 1):
                        A, B = geom[i], geom[i+1]
                        dist = calc_dist_point_to_segment_3d(px, py, pz, A.x_m, A.y_m, A.z_m, B.x_m, B.y_m, B.z_m)
                        if dist < best_match['dist']:
                            best_match.update({'id': item_id, 'dist': dist, 'item': item, 'ref_node': A})

            # Caso B: Es un nodo simple (Punto a Punto / Centro)
            else:
                dist = calc_dist_3d(px, py, pz, geom.x_m, geom.y_m, geom.z_m)
                
                if dist < best_match['dist']:
                    best_match.update({'id': item_id, 'dist': dist, 'item': item, 'ref_node': geom})

        return best_match

    def _cmd_whereami(self, packet: ISP_MSO, target_type: str):
        """Busca tu posición en relación a Vías, Zonas o Enlaces."""
        if not self.active_map_name:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: No hay ningún mapa cargado."))
            return
            
        search_by = target_type.lower()
        if search_by not in ['road', 'link', 'zone', 'all']:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: Usa '!map whereami [road/link/zone/all]'"))
            return
            
        player_coords = self.get_coords_fn(packet.UCID)
        if not player_coords: 
            self.send(ISP_MSL(Msg=f"{TextColors.RED}No se pudo obtener tu telemetría."))
            return
            
        px, py, pz = player_coords.x_m, player_coords.y_m, player_coords.z_m
        self.send(ISP_MSL(Msg=f"{TextColors.CYAN}Tus Coordenadas: {TextColors.WHITE}X:{px:.1f} Y:{py:.1f} Z:{pz:.1f}"))
        
        # --- LLAMAMOS A NUESTRA NUEVA FUNCIÓN RADAR ---
        ctx = self.get_location_context(px, py, pz)
        SEARCH_RADIUS_M = 3.0

        if search_by in ['road', 'all']:
            if ctx.road_id and ctx.road_dist <= SEARCH_RADIUS_M:
                self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Vía: {TextColors.WHITE}{ctx.road_id} {TextColors.GREEN}| Nodo: {TextColors.WHITE}{ctx.road_node_idx} {TextColors.GREEN}| Dist: {ctx.road_dist:.1f}m"))
            elif ctx.road_id:
                self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Fuera de vía. Más cercana: {TextColors.WHITE}{ctx.road_id} {TextColors.YELLOW}a {ctx.road_dist:.1f}m."))
            else:
                self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}No hay vías guardadas."))

        if search_by in ['link', 'all']:
            if ctx.link_id:
                self.send(ISP_MSL(Msg=f"{TextColors.GREEN}{ctx.link_type} '{ctx.link_id}' cercano a {ctx.link_dist:.1f}m"))
            else:
                self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}No se encontró ningún link cerca."))

        if search_by in ['zone', 'all']:
            if ctx.zone_id:
                if ctx.zone_dist <= ctx.zone_radius:
                    self.send(ISP_MSL(Msg=f"{TextColors.GREEN}DENTRO del área de zona: {TextColors.WHITE}{ctx.zone_id} {TextColors.GREEN}(Radio: {ctx.zone_radius}m)"))
                    if ctx.zone_dist <= 1.5:
                        self.send(ISP_MSL(Msg=f"{TextColors.CYAN}¡Estás SOBRE la geometría de la zona!"))
                else:
                    self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}FUERA. Zona más cercana: {TextColors.WHITE}{ctx.zone_id} {TextColors.YELLOW}a {ctx.zone_dist:.1f}m del límite."))
            else:
                self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}No hay zonas creadas."))

    def collect_check_results(self) -> tuple[list, list]:
        """Devuelve (errores, advertencias) sin enviar nada por chat."""
        errores = []
        advertencias = []

        for link_id, link in self.road_links.items():
            if not link.nodes:
                errores.append(f"[RoadLink {link_id}] Sin geometria (0 nodos).")
            if link.from_road_id not in self.roads:
                errores.append(f"[RoadLink {link_id}] Origen '{link.from_road_id}' no existe.")
            if link.to_road_id not in self.roads:
                errores.append(f"[RoadLink {link_id}] Destino '{link.to_road_id}' no existe.")
            if link.by_road_id:
                if link.by_road_id not in self.roads:
                    advertencias.append(f"[RoadLink {link_id}] 'by_road_id' apunta a via fantasma '{link.by_road_id}'.")
                elif link.from_road_id in self.roads:
                    es_vecino = any(
                        (ll.road_a == link.from_road_id and ll.road_b == link.by_road_id) or
                        (ll.road_b == link.from_road_id and ll.road_a == link.by_road_id)
                        for ll in self.lateral_links.values()
                    )
                    if not es_vecino:
                        advertencias.append(f"[RoadLink {link_id}] '{link.by_road_id}' no esta enlazado lateralmente con '{link.from_road_id}'.")

        for ll_id, llink in self.lateral_links.items():
            if not llink.nodes or len(llink.nodes) < 2:
                errores.append(f"[LatLink {ll_id}] Sin geometria (< 2 nodos).")
            if llink.road_a not in self.roads:
                errores.append(f"[LatLink {ll_id}] 'road_a' ({llink.road_a}) no existe.")
            if llink.road_b not in self.roads:
                errores.append(f"[LatLink {ll_id}] 'road_b' ({llink.road_b}) no existe.")

        for z_id, zone in self.zones.items():
            if not zone.nodes:
                errores.append(f"[Zona {z_id}] No tiene nodos de delimitacion.")
            if zone.radius_m is None or zone.radius_m <= 0:
                errores.append(f"[Zona {z_id}] 'radius_m' invalido ({zone.radius_m}).")
            if not zone.priority_rules:
                advertencias.append(f"[Zona {z_id}] 'priority_rules' esta vacio.")
            else:
                for rule in zone.priority_rules:
                    if len(rule) != 2:
                        errores.append(f"[Zona {z_id}] Regla mal formada.")
                        continue
                    via_pref, via_cede = rule
                    if via_pref not in self.roads:
                        advertencias.append(f"[Zona {z_id}] Regla usa via preferente fantasma '{via_pref}'.")
                    if via_cede not in self.roads:
                        advertencias.append(f"[Zona {z_id}] Regla obliga a ceder a via fantasma '{via_cede}'.")

        for r_id, road in self.roads.items():
            if road.speed_limit_kmh is None or road.speed_limit_kmh <= 0:
                errores.append(f"[Via {r_id}] 'speed_limit_kmh' invalido.")
            if not road.nodes or len(road.nodes) < 2:
                errores.append(f"[Via {r_id}] Demasiado corta (< 2 nodos).")
            has_entry_link = any(link.to_road_id == r_id for link in self.road_links.values())
            has_lateral_entry = any(
                (lat.road_b == r_id and lat.allow_a_to_b) or
                (lat.road_a == r_id and lat.allow_b_to_a)
                for lat in self.lateral_links.values()
            )
            if not has_entry_link and not has_lateral_entry:
                advertencias.append(f"[Via {r_id}] Inaccesible (No hay RoadLinks ni LatLinks que apunten hacia ella).")
            if not road.is_circular:
                has_exit_link = any(l.from_road_id == r_id for l in self.road_links.values())
                has_lateral_exit = any(
                    (lat.road_a == r_id and lat.allow_a_to_b) or
                    (lat.road_b == r_id and lat.allow_b_to_a)
                    for lat in self.lateral_links.values()
                )
                if not has_exit_link and not has_lateral_exit:
                    advertencias.append(f"[Via {r_id}] Callejon sin salida (Faltan enlaces directos o LatLinks para salir).")

        return errores, advertencias

    def _cmd_check_map(self):
        """Busca errores lógicos exhaustivos en el mapa según la nueva topología de grafos."""
        if not self.active_map_name:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: No hay ningun mapa activo."))
            return

        self.send(ISP_MSL(Msg=f"{TextColors.CYAN}--- Chequeando integridad de: {self.active_map_name} ---"))
        errores, advertencias = self.collect_check_results()
        tot_err, tot_adv = len(errores), len(advertencias)

        if tot_err == 0 and tot_adv == 0:
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}[OK] Mapa perfecto! La topologia es 100% solida."))
            return

        msg_color = TextColors.RED if tot_err > 0 else TextColors.YELLOW
        self.send(ISP_MSL(Msg=f"{msg_color}Chequeo finalizado: {TextColors.WHITE}{tot_err} errores {msg_color}y {TextColors.WHITE}{tot_adv} avisos."))

        for err in errores[:4]:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}ERR: {TextColors.WHITE}{err[:80]}"))
        if tot_err > 4:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}... y {tot_err - 4} errores mas."))

        if tot_err == 0 or tot_err <= 4:
            for adv in advertencias[:4]:
                self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}AVISO: {TextColors.WHITE}{adv[:80]}"))
            if tot_adv > 4:
                self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}... y {tot_adv - 4} avisos mas."))

    # ==========================================
    # 5. EDICIÓN Y LIMPIEZA
    # ==========================================

    def _get_collection_and_type(self, obj_id: str):
        """Busca el objeto en los 5 diccionarios. Devuelve (diccionario, tipo_str) o (None, None)."""
        if obj_id in self.roads: return self.roads, "Road"
        if obj_id in self.road_links: return self.road_links, "RoadLink"
        if obj_id in self.lateral_links: return self.lateral_links, "LatLink"
        if obj_id in self.zones: return self.zones, "Zone"
        if obj_id in self.special_rules: return self.special_rules, "SpecialRule"
        return None, None

    def _cmd_set(self, obj_id: str, prop: str, val_str: str):
        """Edita propiedades de cualquier objeto de forma inteligente y segura."""
        if not self.active_map_name:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: No hay ningun mapa activo."))
            return

        # 1. Busqueda polimorfica (Usando la funcion auxiliar que creamos)
        collection, obj_type = self._get_collection_and_type(obj_id)
        
        if not collection:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: ID '{obj_id}' no encontrado en ninguna categoria."))
            return
            
        obj = collection[obj_id]
        prop = prop.lower() # Asegurar lowercase para las propiedades de las Dataclasses

        # ==========================================
        # 2. BLOQUEO DE SEGURIDAD (Inmutables y Nodos)
        # ==========================================
        inmutables = ["road_id", "zone_id", "link_id", "from_road_id", "to_road_id", "road_a", "road_b", "from_suffix", "to_suffix", "suffix_a", "suffix_b", "min_speed_kmh"]
        if prop in inmutables:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}La propiedad '{prop}' es inmutable tras la creacion."))
            return
            
        if prop == "nodes":
            comando = "!map rec_road" if obj_type == "Road" else "!map rec_link" # Simplificado
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Los nodos no se editan a mano. Usa: {TextColors.WHITE}{comando} {obj_id}"))
            return

        special_rule_shortcuts = ["speed_limit", "no_lane_change"]
        if not hasattr(obj, prop) and not (obj_type == "SpecialRule" and prop in special_rule_shortcuts):
            self.send(ISP_MSL(Msg=f"{TextColors.RED}La propiedad '{prop}' no existe en este objeto ({obj_type})."))
            return

        # ==========================================
        # 3. PROCESAMIENTO INTELIGENTE DE TIPOS
        # ==========================================
        current_val = getattr(obj, prop)
        
        try:
            # --- CASO A: Sintaxis Especial priority_rules (IntersectionZone) ---
            if prop == "priority_rules" and obj_type == "Zone":
                partes = val_str.split(";")
                operacion = partes[0].lower().strip()
                
                if operacion == "clear":
                    obj.priority_rules.clear()
                    self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Todas las reglas de prioridad borradas en {obj_id}."))
                    return
                    
                elif operacion in ["add", "del"] and len(partes) == 2:
                    vias = [x.strip() for x in partes[1].split(",")]
                    if len(vias) != 2:
                        self.send(ISP_MSL(Msg=f"{TextColors.RED}Formato invalido. Usa: {operacion};ViaA,ViaB"))
                        return
                        
                    if operacion == "add":
                        if vias not in obj.priority_rules:
                            obj.priority_rules.append(vias)
                            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Regla anadida: {vias[0]} tiene prioridad sobre {vias[1]}"))
                        else:
                            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Esa regla ya existe en la zona."))
                            
                    elif operacion == "del":
                        if vias in obj.priority_rules:
                            obj.priority_rules.remove(vias)
                            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Regla eliminada: {vias[0]} > {vias[1]}"))
                        else:
                            self.send(ISP_MSL(Msg=f"{TextColors.RED}La regla no existe en esta zona."))
                else:
                    self.send(ISP_MSL(Msg=f"{TextColors.RED}Uso: clear | add;ViaA,ViaB | del;ViaA,ViaB"))
                return

            # --- CASO B: Mapeo de Intermitentes (CSVAL.INDICATORS) ---
            if prop == "indicators":
                modo = val_str.lower().strip()
                if modo in ["off", "apagado", "none"]:
                    nuevo_valor = CSVAL.INDICATORS.OFF
                elif modo in ["left", "izq", "izquierda"]:
                    nuevo_valor = CSVAL.INDICATORS.LEFT
                elif modo in ["right", "der", "derecha"]:
                    nuevo_valor = CSVAL.INDICATORS.RIGHT
                elif modo in ["hazard", "emergencia", "peligro"]:
                    nuevo_valor = CSVAL.INDICATORS.HAZARD
                else:
                    self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: Valor invalido. Usa: off | left | right | hazard"))
                    return
                
                setattr(obj, prop, nuevo_valor)
                self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Intermitente configurado a '{modo.upper()}' en {obj_id}."))
                return

            # --- CASO C: Mapeo de Normas de Trafico (TrafficRule Enum) ---
            if prop == "traffic_rule":
                modo = val_str.lower().strip()
                if modo in ["rht", "derecha", "0"]:
                    nuevo_valor = TrafficRule.RHT
                elif modo in ["lht", "izquierda", "1"]:
                    nuevo_valor = TrafficRule.LHT
                elif modo in ["none", "ninguna", "off"]:
                    nuevo_valor = None
                else:
                    self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: Usa 'rht' (der), 'lht' (izq) o 'none'."))
                    return

                setattr(obj, prop, nuevo_valor)
                self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Norma de trafico configurada en {obj_id}."))
                return

            # --- CASO C2: Edición del dict 'rules' de SpecialRule (forma corta: .map set id speed_limit 30) ---
            if obj_type == "SpecialRule" and prop in ["speed_limit", "no_lane_change"]:
                if prop == "speed_limit":
                    obj.rules["speed_limit"] = float(val_str)
                    self.send(ISP_MSL(Msg=f"{TextColors.GREEN}speed_limit = {obj.rules['speed_limit']} km/h en {obj_id}."))
                else:
                    obj.rules["no_lane_change"] = val_str.lower() in ["true", "1", "si", "yes", "on"]
                    self.send(ISP_MSL(Msg=f"{TextColors.GREEN}no_lane_change = {obj.rules['no_lane_change']} en {obj_id}."))
                return

            # --- CASO C3: Edición completa del dict 'rules' de SpecialRule ---
            if prop == "rules" and obj_type == "SpecialRule":
                partes = val_str.split(";")
                operacion = partes[0].lower().strip()

                if operacion == "clear":
                    obj.rules.clear()
                    self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Todas las reglas borradas en {obj_id}."))
                    return

                if len(partes) != 2:
                    self.send(ISP_MSL(Msg=f"{TextColors.RED}Uso: clear | speed_limit;<valor> | no_lane_change;<true/false>"))
                    return

                clave = partes[0].strip()
                valor_str = partes[1].strip()

                if clave == "speed_limit":
                    obj.rules["speed_limit"] = float(valor_str)
                    self.send(ISP_MSL(Msg=f"{TextColors.GREEN}speed_limit = {obj.rules['speed_limit']} km/h en {obj_id}."))
                elif clave == "no_lane_change":
                    obj.rules["no_lane_change"] = valor_str.lower() in ["true", "1", "si", "yes", "on"]
                    self.send(ISP_MSL(Msg=f"{TextColors.GREEN}no_lane_change = {obj.rules['no_lane_change']} en {obj_id}."))
                else:
                    self.send(ISP_MSL(Msg=f"{TextColors.RED}Clave desconocida '{clave}'. Usa: speed_limit | no_lane_change | clear"))
                return

            # --- CASO D: Asignacion Dinamica Estandar ---
            if val_str.lower() == "none":
                # Propiedades opcionales que SI permitimos que sean nulas
                campos_permitidos_none = ["by_road_id", "traffic_rule"] 
                if prop not in campos_permitidos_none:
                    self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: La propiedad '{prop}' es obligatoria y no puede ser 'None'."))
                    return
                new_val = None
                
            elif isinstance(current_val, bool) or prop in ["is_circular", "is_closed", "allow_a_to_b", "allow_b_to_a", "opposing", "made_to_overtake"]: 
                # Chequeo extra de nombres de prop por si current_val era None pero sabemos que es un bool
                new_val = val_str.lower() in ["true", "1", "si", "yes", "on"]
                
            elif isinstance(current_val, (int, float)) and not isinstance(current_val, bool):
                new_val = float(val_str) if isinstance(current_val, float) else int(val_str)
                
            else:
                new_val = val_str # Fallback a string

            # Aplicar el valor
            setattr(obj, prop, new_val)
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Cambio aplicado: {prop} = {new_val}"))

            # Advertencias residuales para IDs de vias que aun no existen
            if new_val is not None and isinstance(new_val, str):
                if prop in ["by_road_id"] and new_val not in self.roads:
                    self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Aviso: La via '{new_val}' aun no existe en el mapa."))

        except ValueError:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: El valor '{val_str}' no coincide con el tipo numerico esperado."))
        except Exception as e:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error inesperado: {str(e)}"))

    def _cmd_del(self, obj_id: str):
        """Busca el ID en cualquier categoria y aplica borrado en cascada si es una via."""
        if not self.active_map_name:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: No hay ningun mapa activo."))
            return

        collection, obj_type = self._get_collection_and_type(obj_id)
        
        if not collection:
            self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}[AVISO] No se encontro objeto con el ID '{obj_id}'."))
            return

        # ==========================================
        # 1. LOGICA DE BORRADO EN CASCADA PARA VIAS
        # ==========================================
        if obj_type == "Road":
            r_links_del = 0
            l_links_del = 0
            zonas_mod = 0
            
            # Cascada A: Borrar RoadLinks que usen esta via (Origen, Destino o Via de paso)
            links_to_remove = [l_id for l_id, link in self.road_links.items() 
                               if link.from_road_id == obj_id or link.to_road_id == obj_id or link.by_road_id == obj_id]
            for l_id in links_to_remove:
                del self.road_links[l_id]
                r_links_del += 1
                
            # Cascada B: Borrar LateralLinks que usen esta via
            lat_to_remove = [ll_id for ll_id, llink in self.lateral_links.items() 
                             if llink.road_a == obj_id or llink.road_b == obj_id]
            for ll_id in lat_to_remove:
                del self.lateral_links[ll_id]
                l_links_del += 1
                
            # Cascada C: Limpiar reglas de prioridad en Zonas
            for zone in self.zones.values():
                original_len = len(zone.priority_rules)
                # Filtramos dejando solo las reglas que NO contengan el obj_id
                zone.priority_rules = [rule for rule in zone.priority_rules if obj_id not in rule]
                if len(zone.priority_rules) != original_len:
                    zonas_mod += 1

            # Finalmente, borrar la via principal
            del self.roads[obj_id]
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}[MAPA] Via '{obj_id}' eliminada con exito."))
            
            # Reporte de limpieza
            if r_links_del > 0 or l_links_del > 0 or zonas_mod > 0:
                self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Cascada: Borrados {r_links_del} R-Links y {l_links_del} L-Links. Limpiadas {zonas_mod} Zonas."))
                
        # ==========================================
        # 2. BORRADO SIMPLE (Zonas y Enlaces)
        # ==========================================
        else:
            del collection[obj_id]
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}{obj_type} '{obj_id}' eliminado correctamente."))
    
    def _cmd_rec_road_rule(self, rule_str: str):
        """Cambia la norma de trafico por defecto para las NUEVAS vias que se graben."""
        modo = rule_str.lower().strip()
        
        if modo in ["rht", "derecha", "0"]:
            self.default_traffic_rule = TrafficRule.RHT
            texto = "DERECHA (RHT)"
        elif modo in ["lht", "izquierda", "1"]:
            self.default_traffic_rule = TrafficRule.LHT
            texto = "IZQUIERDA (LHT)"
        else:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Uso: !map rec_rule [rht|lht]"))
            return
            
        self.send(ISP_MSL(Msg=f"{TextColors.GREEN}Nuevas vias se grabaran por defecto por la {TextColors.WHITE}{texto}."))

    def _cmd_is_closed_road(self):
        """Muestra un listado de las carreteras que tienen is_closed = True."""
        if not hasattr(self, 'roads') or not self.roads:
            self.send(ISP_MSL(Msg=f"{TextColors.RED}Error: No hay vias cargadas en el mapa."))
            return

        rutas_cerradas = []

        # Buscamos directamente en self.roads tal como en _cmd_check_map
        for r_id, road in self.roads.items():
            if getattr(road, 'is_closed', False):
                rutas_cerradas.append(str(r_id))

        if not rutas_cerradas:
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}INFO: {TextColors.WHITE}Todas las vias estan abiertas. ¡Via libre!"))
            return

        total_cerradas = len(rutas_cerradas)
        texto_rutas = ", ".join(rutas_cerradas)
        
        # Enviamos el encabezado
        self.send(ISP_MSL(Msg=f"{TextColors.YELLOW}Vias cerradas ({total_cerradas}):"))
        
        # Troceamos el mensaje si es muy largo para no cortar el texto en el chat
        chunk_size = 80 
        for i in range(0, len(texto_rutas), chunk_size):
            chunk = texto_rutas[i:i+chunk_size]
            self.send(ISP_MSL(Msg=f"{TextColors.WHITE}{chunk}"))