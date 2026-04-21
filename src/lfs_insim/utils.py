from __future__ import annotations  # SIEMPRE EN LA LÍNEA 1
from lfs_insim.insim_packet_class import ISP_MSO, ISP_MSL, SND
from lfs_insim.packet_sender_mixin import PacketSenderMixin
from dataclasses import dataclass, field
from typing import Any, Callable
import re
import math
import logging
from lfs_insim.exceptions import InSimCommandError

logger = logging.getLogger(__name__)

def separate_message(packet: ISP_MSO) -> tuple[str, str]:
    """De un mensaje recibido por LFS, separa al usuario del contenido."""
    user = packet.Msg[:packet.TextStart].strip()
    content = packet.Msg[packet.TextStart:].strip()
    return user, content

def separate_command_args(prefix: str, packet: ISP_MSO) -> tuple[str, list[str]] | tuple[None, None]:
    """
    Separa un comando de sus argumentos.
    Args:
        prefix: Prefijo del comando
        message: Contenido completo del mensaje
    Returns:
        Tupla (comando sin el prefijo, lista de argumentos),
        None si no coincide el prefijo o el mensaje está vacío.
    """
    _, message = separate_message(packet)
    if len(message) > 0 and message.startswith(prefix):
        parts = message.strip().split()
        cmd = parts[0][1:]
        args = parts[1:] if len(parts) > 1 else []
        return cmd, args
    else:
        return None, None

def strip_lfs_colors(text: str) -> str:
    """Elimina los códigos de color de LFS (ej: ^7, ^h, ^L)."""
    # Regex busca el ^ seguido de un caracter de color común
    return re.sub(r'\^[0-9^Lhsv]', '', text).strip()

class TextColors:
    """
    Colores a usar al enviar mensajes al chat de LFS
    """
    BLACK = "^0"
    RED = "^1"
    GREEN = "^2"
    YELLOW = "^3"
    BLUE = "^4"
    MAGENTA = "^5"
    CYAN = "^6"
    WHITE = "^7"
    DEFAULT = "^8" # Color estándar del InSim
    NORMAL = "^9"  # Resetea al color original del chat

class PIDController:
    """
    Controlador PID optimizado para SimRacing (Anti-Windup & Anti-Derivative Kick).
    """
    def __init__(self, kp: float, ki: float, kd: float, out_min: float = -1.0, out_max: float = 1.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        # Límites reales de salida (ej: -1.0 a 1.0 para pedales o volante)
        self.out_min = out_min
        self.out_max = out_max
        
        self.integral = 0.0
        self.prev_current = 0.0  # [!] FIX: Guardamos la medición, no el error
        self.first_run = True    # Para evitar un pico en el primer frame

    def update(self, target: float, current: float, dt: float) -> float:
        if dt <= 0.0: 
            return 0.0
            
        if self.first_run:
            self.prev_current = current
            self.first_run = False

        error = target - current
        
        # --- 1. Proporcional (P) ---
        p_term = self.kp * error
        
        # --- 2. Integral (I) con Anti-Windup Clamping ---
        self.integral += error * dt
        i_term = self.ki * self.integral
        
        # [!] FIX: Clampeamos el I-Term para que no exija más del máximo/mínimo físico
        # y luego recalculamos self.integral para que no siga creciendo en la sombra
        i_term = max(self.out_min, min(self.out_max, i_term))
        if self.ki != 0:
            self.integral = i_term / self.ki 

        # --- 3. Derivativo (D) (Anti-Derivative Kick) ---
        # Usamos el cambio en la variable de proceso (current), no en el error.
        # El negativo es importante matemáticamente aquí.
        d_term = -self.kd * (current - self.prev_current) / dt
        self.prev_current = current
        
        # --- 4. Salida Total Segura ---
        output = p_term + i_term + d_term
        return max(self.out_min, min(self.out_max, output))
        
    def reset(self):
        self.integral = 0.0
        self.prev_current = 0.0
        self.first_run = True

@dataclass
class Command(PacketSenderMixin):
    """
    Generador de comandos con validación de uso
    """
    name: str
    description: str
    args: tuple[tuple[str,Any]]|str|None
    funct: Callable
    _prefix: str
    is_mso_required: bool = False
    
    def __post_init__(self):
        self.how_to_use = self._how_to_use()
    
    def _how_to_use(self):
        if not self.args:
            text_args=''
        elif isinstance(self.args, str):
            text_args = f'[{self.args} (puede contener espacios)]'
        elif isinstance(self.args[0], tuple):
            text_args = ' '.join((f'[{arg[0]} ({arg[1].__name__})]' for arg in self.args))
        else:
            raise Exception(f'Tipo de argumento invalido en la creación del comando {self.name}')
        
        # Le damos color a la instrucción de uso
        return f'{TextColors.YELLOW}Uso: {TextColors.WHITE}{self._prefix} {self.name} {text_args}'
        
    # CAMBIO 1: El tipado de retorno ahora es más limpio (Lista de argumentos o False si falló)
    def _prepare_args(self, using_args) -> list[Any] | bool:
        expected_args = self.args
        usefull_args = []
        
        # CAMBIO 2: Si no hay argumentos, devolvemos una lista vacía en vez de None
        if not expected_args: 
            return [] 
            
        if isinstance(expected_args, str):
            args_str = ' '.join(using_args)
            if not args_str:
                self.send(ISP_MSL(Msg=f'{TextColors.RED}Error: el comando "{self.name}" requiere texto.', Sound=SND.INVALIDKEY))
                self.send(ISP_MSL(Msg=self.how_to_use))
                return False # CAMBIO 3: Devolvemos False en vez de -1
            
            # CAMBIO 4: Metemos el string en una lista para uniformidad
            return [args_str] 
            
        if isinstance(expected_args, tuple):
            if len(using_args) < len(expected_args):
                self.send(ISP_MSL(Msg=f'{TextColors.RED}Error: faltan argumentos. ({len(using_args)} de {len(expected_args)} requeridos)', Sound=SND.INVALIDKEY))
                self.send(ISP_MSL(Msg=self.how_to_use))
                return False # CAMBIO 3
                
            count = 0
            while count<len(expected_args):
                try:
                    usefull_args.append(expected_args[count][1](using_args[count]))
                    count+=1
                except Exception as e:
                    logger.info(f'Error por el argumento {using_args[count]} en el comando {self.name}: {e}')
                    self.send(ISP_MSL(Msg=f'{TextColors.RED}Argumento invalido: "{using_args[count]}"', Sound=SND.INVALIDKEY))
                    self.send(ISP_MSL(Msg=self.how_to_use))
                    return False # CAMBIO 3
            return usefull_args
    
    def use(self, packet: 'ISP_MSO', using_args: list[Any]):
        args = self._prepare_args(using_args)
        
        # CAMBIO 5: Comprobamos si la validación falló comparando con False
        if args is False:
            logger.info(f'No se pudo ejecutar el comando {self.name}')
            return
            
        # CAMBIO 6: Desempaquetado mágico (*args). 
        # Como 'args' SIEMPRE es una lista (vacía o llena), esto funciona perfectamente.
        # Si la lista está vacía, no pasa ningún argumento extra.
        # Si tiene datos, los pasa separados por comas como espera tu función.
        if not self.is_mso_required:
            self.funct(*args)
        else:
            self.funct(packet, *args)


@dataclass
class CMDManager(PacketSenderMixin):
    cmd_prefix: str
    cmd_base: str
    
    def __post_init__(self):
        self._cmds: dict[str, Command] = {}
        self._prefix: str = self.cmd_prefix + self.cmd_base
    
    def submit(self) -> 'CMDManager':
        self.send(ISP_MSL(Msg=f'{TextColors.YELLOW}Usa "{TextColors.WHITE}{self._prefix}{TextColors.YELLOW}" para ver los comandos.'))
        return self
    
    def add_cmd(self, name: str, description: str, args: tuple[tuple[str,Any]]|str|None, funct: Callable, is_mso_required: bool = False) -> 'CMDManager':
        """
        Crea y añade un comando al almacenamiento.
        Devuelve 'self' para permitir el anidamiento (Fluent Interface).
        """
        cmd = Command(name, description, args, funct, self._prefix, is_mso_required)
        self._cmds[cmd.name] = cmd
        return self 
    
    def _show_cmds(self):
        """Muestra los comandos de 4 en 4 en una misma línea"""
        if not self._cmds:
            self.send(ISP_MSL(Msg=f'{TextColors.YELLOW}No hay comandos "{self.cmd_base}" disponibles'))
            return
            
        self.send(ISP_MSL(Msg=f'{TextColors.GREEN}=== {TextColors.WHITE}Comandos de {self._prefix} {TextColors.GREEN}==='))
        
        # Extraemos los nombres y los agrupamos de 4 en 4
        cmd_names = list(self._cmds.keys())
        chunk_size = 4
        
        for i in range(0, len(cmd_names), chunk_size):
            chunk = cmd_names[i:i + chunk_size]
            # Formateamos la línea: cmd1 | cmd2 | cmd3 | cmd4
            line = f"{TextColors.GREEN} | {TextColors.WHITE}".join(chunk)
            self.send(ISP_MSL(Msg=f"{TextColors.WHITE}{line}"))
            
        # Mini-tutorial al final
        self.send(ISP_MSL(Msg=f'{TextColors.YELLOW}Info detallada: {TextColors.WHITE}{self._prefix} <comando> ?'))
    
    def handle_commands(self, packet: 'ISP_MSO', args: list):
        if not args or not self._cmds:
            self._show_cmds()
            return
            
        cmd = args.pop(0)
        
        # [NUEVO] Si el usuario pone "?", "!map help" o "!map ?"
        if cmd in ["?", "help"]:
            if args and args[0] in self._cmds:
                target = self._cmds[args[0]]
                self.send(ISP_MSL(Msg=f"{TextColors.GREEN}{target.name}: {TextColors.WHITE}{target.description}"))
                self.send(ISP_MSL(Msg=target.how_to_use))
            else:
                self._show_cmds()
            return

        # Si el comando no existe
        if cmd not in self._cmds:
            self.send(ISP_MSL(Msg=f'{TextColors.RED}Comando "{cmd}" no reconocido.', Sound=SND.INVALIDKEY))
            self._show_cmds()
            return
            
        # [NUEVO] Si el usuario pone "!map comando ?" para ver la descripción de algo concreto
        if args and args[0] == "?":
            target = self._cmds[cmd]
            self.send(ISP_MSL(Msg=f"{TextColors.GREEN}{target.name}: {TextColors.WHITE}{target.description}"))
            self.send(ISP_MSL(Msg=target.how_to_use))
            return
            
        # Si todo está correcto, ejecutamos
        self._cmds[cmd].use(packet, args)

# Transformación de unidades

def lfs_pos_to_meters(unit: int|float, rev: bool = False) -> float|int:
    """
    Convierte unidades de posición LFS (1m = 65536 units) a metros.
    Si rev=True hace lo contrario.
    """
    if rev:
        return int(unit * 65536.0)
    return unit / 65536.0

def lfs_speed_to_kmh(speed: int, rev: bool = False) -> float|int:
    """
    Convierte la unidad de velocidad de LFS a Km/h.
    Si rev=True hace lo contrario.
    """
    if rev:
        return int((speed * 32768.0) / 360.0)
    return (speed * 360.0) / 32768.0

def lfs_angle_to_degrees(unit: int | float, rev: bool = False) -> float | int:
    """
    Convierte unidades angulares de LFS (0-65535) a grados (-180.0 a 180.0).
    Si rev=True hace lo contrario (de grados a unidades LFS).
    """
    if rev:
        # Convertir de grados a LFS y asegurar que queda en el rango 0-65535
        unidades_lfs = int(unit * (65536.0 / 360.0))
        return unidades_lfs % 65536
        
    # Convertir de LFS a grados (-180 a 180)
    unidades_lfs = int(unit) % 65536
    
    # Desplazamos la mitad superior del círculo al rango negativo
    if unidades_lfs > 32767:
        unidades_lfs -= 65536
        
    return unidades_lfs * (360.0 / 65536.0)

def lfs_angvel_to_degrees_per_second(unit: int | float, rev: bool = False) -> float | int:
    """
    Convierte unidades de velocidad angular de LFS a grados por segundo.
    (16384 unidades en LFS = 360 grados por segundo).
    Si rev=True hace lo contrario (de grados/s a unidades LFS).
    """
    if rev:
        # Convertir de grados por segundo a unidades LFS AngVel
        return int(unit * (16384.0 / 360.0))
    
    # Convertir de unidades LFS AngVel a grados por segundo
    return unit * (360.0 / 16384.0)


# CALCULOS

def calc_dist_3d(x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> float:
    """Calcula la distancia real en 3D (indiferente de unidades aunque todos los datos deben estar en la misma unidad)."""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

def calc_target_heading(current_x: int, current_y: int, target_x: int, target_y: int, rev: bool = False) -> int:
    """
    Calcula el rumbo (Heading) necesario para mirar hacia un objetivo.
    Devuelve el ángulo en unidades LFS (0 - 65535).
    Si rev=True, devuelve el rumbo opuesto (ideal para dirigir el coche en marcha atrás).
    """
    # En LFS: +Y es Norte, +X es Oeste.
    dx = current_x - target_x
    dy = target_y - current_y
    rad = math.atan2(dx, dy)
    
    if rad < 0:
        rad += 2 * math.pi
        
    heading = int((rad / (2 * math.pi)) * 65536) % 65536
    
    if rev:
        # Sumamos media vuelta entera (180 grados = 32768 unidades LFS)
        return (heading + 32768) % 65536
        
    return heading

def get_heading_diff(target_h: int, current_h: int) -> int:
    """
    Calcula el error direccional más corto.
    Recibe y devuelve valores en unidades LFS (-32768 a 32768).
    """
    return (target_h - current_h + 32768) % 65536 - 32768

def calc_deviation_angle(x1: int, y1: int, x2: int, y2: int, x3: int, y3: int) -> int:
    """
    Calcula el ángulo de desviación entre la línea de los 2 puntos 
    previos y el nuevo punto.
    
    Segmento 1: De (x1, y1) a (x2, y2)
    Segmento 2: De (x2, y2) a (x3, y3)
    
    Retorna:
        int: Ángulo de desviación en unidades LFS (-32768 a 32768).
             0 significa que la trayectoria sigue en línea recta perfecta.
             Valores positivos/negativos indican giro a la izquierda o derecha.
    """
    # 1. Calculamos el ángulo (rumbo) de ambos segmentos en radianes
    theta1 = math.atan2(y2 - y1, x2 - x1)
    theta2 = math.atan2(y3 - y2, x3 - x2)
    
    # 2. Encontramos la diferencia
    diff_rad = theta2 - theta1
    
    # 3. Normalizamos el ángulo para que esté en el rango de -pi a pi radianes
    diff_rad = (diff_rad + math.pi) % (2 * math.pi) - math.pi
    
    # 4. Convertimos de radianes a unidades LFS (pi radianes = 32768 unidades)
    return int((diff_rad / math.pi) * 32768)

import math

def calc_dist_point_to_segment_3d(px, py, pz, ax, ay, az, bx, by, bz):
    """Calcula la distancia mínima entre un punto (P) y un segmento de línea (A-B)."""
    # Vector AB (El segmento de la calle)
    abx, aby, abz = bx - ax, by - ay, bz - az
    
    # Vector AP (Del inicio del segmento hasta el jugador)
    apx, apy, apz = px - ax, py - ay, pz - az
    
    # Producto punto para proyectar AP sobre AB
    ap_ab = apx * abx + apy * aby + apz * abz
    ab_ab = abx * abx + aby * aby + abz * abz
    
    if ab_ab == 0:
        # Los puntos A y B son idénticos (el segmento es un punto)
        return math.sqrt(apx**2 + apy**2 + apz**2)
        
    # 't' es la posición normalizada (0 a 1) en el segmento AB
    t = ap_ab / ab_ab
    
    if t <= 0.0:
        # El jugador está "por detrás" del inicio del segmento (Punto A es el más cercano)
        return math.sqrt(apx**2 + apy**2 + apz**2)
    elif t >= 1.0:
        # El jugador está "por delante" del final del segmento (Punto B es el más cercano)
        bpx, bpy, bpz = px - bx, py - by, pz - bz
        return math.sqrt(bpx**2 + bpy**2 + bpz**2)
    else:
        # El jugador está paralelo al segmento (Calculamos la distancia perpendicular)
        # CORRECCIÓN: Faltaba calcular cx y cy
        cx = ax + t * abx
        cy = ay + t * aby
        cz = az + t * abz
        
        cpx, cpy, cpz = px - cx, py - cy, pz - cz
        return math.sqrt(cpx**2 + cpy**2 + cpz**2)

# ==========================================
# UTILIDADES DE NAVEGACIÓN AI (MATEMÁTICAS PÚBLICAS)
# ==========================================

def get_closest_node_index(my_coords: Any, list_of_nodes: list[Any], is_waypoint: bool = False) -> int:
    """
    Encuentra el índice del nodo o waypoint más cercano a unas coordenadas.
    Args:
        my_coords: Objeto con x_m, y_m, z_m
        list_of_nodes: Lista de Nodos (Route.waypoints o RoadSegment.nodes)
        is_waypoint: Si es True, asume que list_of_nodes contiene objetos Waypoint y 
                     accede a .coordinates. De lo contrario, asume que los nodos en sí tienen x_m...
    """
    min_dist = float('inf')
    best_idx = 0
    total_nodes = len(list_of_nodes)
    
    for i in range(total_nodes):
        node = list_of_nodes[i]
        coords = node.coordinates if is_waypoint else node
        
        dist = calc_dist_3d(
            my_coords.x_m, my_coords.y_m, my_coords.z_m,
            coords.x_m, coords.y_m, coords.z_m
        )
        if dist < min_dist:
            min_dist = dist
            best_idx = i
            
    return best_idx

def determine_smart_spawn_index(my_coords: Any, closest_idx: int, list_of_nodes: list[Any], is_waypoint: bool = False) -> int:
    """
    Decide lógicamente si el coche debe apuntar al nodo más cercano o al siguiente en la serie (Smart Spawn).
    Evita que el coche intente girar 180º para ir a un nodo que acaba de pasar.
    """
    total_nodes = len(list_of_nodes)
    if total_nodes < 2: return closest_idx
    
    # En rutas (circuito cerrado) damos la vuelta. En freeroam (segmento abierto) tenemos límites.
    prev_idx = (closest_idx - 1) % total_nodes if is_waypoint else max(0, closest_idx - 1)
    next_idx = (closest_idx + 1) % total_nodes if is_waypoint else min(total_nodes - 1, closest_idx + 1)
    
    node_prev = list_of_nodes[prev_idx].coordinates if is_waypoint else list_of_nodes[prev_idx]
    node_next = list_of_nodes[next_idx].coordinates if is_waypoint else list_of_nodes[next_idx]
    
    dist_to_prev = calc_dist_3d(
        my_coords.x_m, my_coords.y_m, my_coords.z_m,
        node_prev.x_m, node_prev.y_m, node_prev.z_m
    )
    dist_to_next = calc_dist_3d(
        my_coords.x_m, my_coords.y_m, my_coords.z_m,
        node_next.x_m, node_next.y_m, node_next.z_m
    )
    
    if dist_to_next < dist_to_prev:
        return next_idx
    return closest_idx

def apply_antilag_window(my_coords: Any, current_idx: int, list_of_nodes: list[Any], window_size: int = 15, is_waypoint: bool = False, is_driving_opposing: bool = False) -> int:
    """
    Escanea hacia el futuro para recuperar el hilo si un nodo ha quedado por detrás debido 
    a ping, lagazos de física o un spawn agresivo. Soporta sentido contrario.
    """
    total_nodes = len(list_of_nodes)
    if total_nodes == 0: return current_idx
    if not is_driving_opposing and current_idx >= total_nodes: return current_idx
    if is_driving_opposing and current_idx < 0: return current_idx
    
    best_index = current_idx
    min_dist = float('inf')
    
    # Calcular hasta dónde podemos mirar sin salirnos de la lista
    if is_waypoint:
        search_window = min(window_size, total_nodes)
    else:
        if is_driving_opposing:
            search_window = min(window_size, current_idx + 1) # Solo podemos retroceder hasta el índice 0
        else:
            search_window = min(window_size, total_nodes - current_idx)
        
    for i in range(search_window):
        if is_waypoint:
            # Ventana circular
            check_idx = (current_idx - i) % total_nodes if is_driving_opposing else (current_idx + i) % total_nodes
        else:
            # Ventana lineal
            check_idx = current_idx - i if is_driving_opposing else current_idx + i
            
        node_check = list_of_nodes[check_idx].coordinates if is_waypoint else list_of_nodes[check_idx]
        
        dist = calc_dist_3d(
            my_coords.x_m, my_coords.y_m, my_coords.z_m,
            node_check.x_m, node_check.y_m, node_check.z_m
        )
        
        if dist < min_dist:
            min_dist = dist
            best_index = check_idx
            
    return best_index


def evaluate_dynamic_capture(my_coords: Any, current_target_idx: int, list_of_nodes: list[Any], speed_kmh: float, 
                             min_radius: float = 1.0, max_radius: float = 10.0, lookahead_time: float = 0.5, 
                             is_waypoint: bool = False, is_driving_opposing: bool = False) -> int:
    """
    Calcula el Radio de Captura Dinámico. 
    Si está en modo opposing, decrementa el índice al capturar el nodo en lugar de incrementarlo.
    """
    total_nodes = len(list_of_nodes)
    if not is_driving_opposing and current_target_idx >= total_nodes: return current_target_idx
    if is_driving_opposing and current_target_idx < 0: return current_target_idx
    
    speed_ms = speed_kmh / 3.6
    dynamic_capture_radius = max(min_radius, min(max_radius, min_radius + (speed_ms * lookahead_time)))
    
    target_node = list_of_nodes[current_target_idx].coordinates if is_waypoint else list_of_nodes[current_target_idx]
    
    dist_to_target = calc_dist_3d(
        my_coords.x_m, my_coords.y_m, my_coords.z_m,
        target_node.x_m, target_node.y_m, target_node.z_m
    )
    
    if dist_to_target < dynamic_capture_radius:
        # Aquí invertimos la matemática de progresión
        next_idx = current_target_idx - 1 if is_driving_opposing else current_target_idx + 1
        
        if is_waypoint:
            if not is_driving_opposing and next_idx >= total_nodes: return 0
            if is_driving_opposing and next_idx < 0: return total_nodes - 1
            
        return next_idx 
        
    return current_target_idx

def is_target_ahead_and_in_lane(my_coords: Any, target_point: Any, other_car_coords: Any, 
                                max_lateral_dist: float = 2.5, min_ahead_dist: float = 0.0, max_ahead_dist: float = 120.0) -> tuple[bool, float, float]:
    """
    Usa el Producto Punto (para saber si está delante o detrás) y Producto Cruz (para la distancia lateral).
    Útil para radares láser físicos, desvinculados de waypoints.
    Argumentos:
        my_coords: Dónde estoy yo
        target_point: Hacia dónde estoy yendo yo (Nodo al que apunto). Da el vector de dirección.
        other_car_coords: Posición del rival a chequear.
    Retorna:
        (bool es_peligroso, distancia_longidutinal, distancia_lateral)
        distancia_longidutinal: Distancia de frente al coche (real 3D). Negativo si está detrás.
    """
    dist_to_car = calc_dist_3d(
        my_coords.x_m, my_coords.y_m, my_coords.z_m,
        other_car_coords.x_m, other_car_coords.y_m, other_car_coords.z_m
    )
    
    if dist_to_car > max_ahead_dist: 
        return False, dist_to_car, 0.0
        
    # 1. Nuestro vector de dirección (Hacia el nodo al que apuntamos)
    vec_forward_x = target_point.x_m - my_coords.x_m
    vec_forward_y = target_point.y_m - my_coords.y_m
    
    # Normalizamos el vector
    mag_forward = (vec_forward_x**2 + vec_forward_y**2)**0.5
    if mag_forward == 0: 
        return False, dist_to_car, 0.0
        
    norm_f_x = vec_forward_x / mag_forward
    norm_f_y = vec_forward_y / mag_forward
    
    # Vector desde nosotros hacia el otro coche
    vec_to_other_x = other_car_coords.x_m - my_coords.x_m
    vec_to_other_y = other_car_coords.y_m - my_coords.y_m
    
    # 2. ¿Está por DELANTE? (Producto Punto)
    dot_product = (norm_f_x * vec_to_other_x) + (norm_f_y * vec_to_other_y)
    
    if dot_product > min_ahead_dist:
        # 3. ¿Está en NUESTRO CARRIL? (Producto Cruz)
        cross_product = (norm_f_x * vec_to_other_y) - (norm_f_y * vec_to_other_x)
        lateral_dist = abs(cross_product)
        
        if lateral_dist < max_lateral_dist:
            return True, dist_to_car, lateral_dist
            
    return False, dist_to_car, 0.0
