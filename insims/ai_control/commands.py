from __future__ import annotations
import threading
import time
import random
from typing import TYPE_CHECKING, Optional

from lfs_insim.insim_packet_class import SND, AIInputVal as AIV, CSVAL, CS
from lfs_insim.utils import TextColors, CMDManager
from insims.ai_control.behavior import AIBehavior, AdaptiveSpeedConfig
from insims.ai_control.nav_modes.route.mode import RouteMode
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
from insims.ai_control.base import _MixinBase

if TYPE_CHECKING:
    from insims.users_management.main import AI
    from lfs_insim.insim_packet_class import ISP_MSO


class _CommandsMixin(_MixinBase):
    def _init_commands(self):
        """Concentra el registro de todos los comandos de la arquitectura AI."""
        
        # ==========================================
        # 1. COMANDOS AIC (Comportamiento General)
        # ==========================================
        self.cmds_aic: CMDManager = CMDManager(self.cmd_prefix, self.cmd_base)
        (self.cmds_aic
            .add_cmd(name='add', description='Añade una IA', 
                     args=None, funct=self._cmd_add, is_mso_required=False)
            .add_cmd(name='my-ais', description='Lista de IAs activas', 
                     args=None, funct=self._show_my_ais_list, is_mso_required=True)
            .add_cmd(name='speed-kmh', description='Velocidad constante', 
                     args=(('plid', int), ('speed', float)), funct=self._cmd_speed_kmh, is_mso_required=True)
            .add_cmd(name='stop', description='Detiene la IA', 
                     args=(('plid', int),), funct=self._cmd_stop, is_mso_required=True)
            .add_cmd(name='direction-point', description='Va a coordenadas X Y', 
                     args=(('plid', int), ('x', int), ('y', int)), funct=self._cmd_direction_point, is_mso_required=True)
            .add_cmd(name='follow', description='Sigue a un PLID', 
                     args=(('plid_ai', int), ('plid_target', int)), funct=self._cmd_follow, is_mso_required=True)
            .add_cmd(name='run-away', description='Huye de un PLID', 
                     args=(('plid_ai', int), ('plid_target', int)), funct=self._cmd_run_away, is_mso_required=True)
            .add_cmd(name='adaptive', description='Configura velocidad adaptativa', 
                     args=(('plid', int), ('min_speed', float), ('max_speed', float), ('min_dist', float), ('max_dist', float)), 
                     funct=self._cmd_adaptive, is_mso_required=True)
            .add_cmd(name='spec', description='Pone la IA en spectate', 
                     args=(('plid', int),), funct=self._cmd_spec)
            .submit()
        )
        
        # ==========================================
        # 2. COMANDOS ROUTE (Navegación Clásica)
        # ==========================================
        self.cmds_route: CMDManager = CMDManager(self.cmd_prefix, 'route')
        (self.cmds_route
            .add_cmd(name='rec-start', description='Graba ruta por telemetría',
                     args=(('plid', int), ('route_name', str)), funct=self._route_start)
            .add_cmd(name='rec-stop', description='Para y guarda la ruta',
                     args=(('plid', int),), funct=self._route_stop)
            .add_cmd(name='follow', description='Sigue una ruta grabada',
                     args=(('route_name', str), ('plid', int)), funct=self._cmd_route_follow, is_mso_required=True)
            .add_cmd(name='test', description='Carga AI\'s en las rutas indicadas',
                     args='routes', funct=self._test_routes, is_mso_required=True)
            .submit()
        )
        
        # ==========================================
        # 3. COMANDOS MAP + Extensiones
        # ==========================================
        
        (self.map_recorder.cmd_manager
            .add_cmd(name='ai_state', description='Muestra el estado de un coche ai',
                     args=(('ai_plid', int),), funct=self._cmd_ai_state, is_mso_required=True)
            .add_cmd(name='freeroam', description='Activa modo explorador en una AI',
                     args=(('plid_ai', int),), funct=self._cmd_map_freeroam, is_mso_required=True)
            .add_cmd(name='test', description='Spawnea AI\'s hasta el <num> indicado activandoles el modo freeroam',
                     args=(('num', int),), funct=self._test_freeroam, is_mso_required=True)
            .submit()
        )
    

    def _cmd_add(self):
        """Añade una IA enviando el comando nativo /ai."""
        self.send_ISP_MST(Msg='/ai')
    
    def _show_my_ais_list(self, packet: ISP_MSO):
        """Lista las IAs del usuario que envía el comando."""
        user_ucid = packet.UCID
        plids_ais = self.user_manager.users[user_ucid].plids_ais_actives
        if not plids_ais:
            self.send_ISP_MSL(Msg=f'{TextColors.YELLOW}No tienes ninguna AI activa.')
            return
        for plid in plids_ais:
            ai_plid = self.user_manager.ais[plid].player.plid
            ai_name = self.user_manager.ais[plid].ai_name
            self.send_ISP_MSL(Msg=f'{TextColors.CYAN}PLID: {TextColors.WHITE}{ai_plid} {TextColors.CYAN}| AIName: {TextColors.WHITE}{ai_name}')

    def _cmd_speed_kmh(self, packet: ISP_MSO, plid: str, speed_kmh: float):
        """Fija una velocidad objetivo constante."""
        behavior = self._get_behavior(packet.UCID, plid)
        if not behavior: return
        
        behavior.reset_speed()
        behavior.target_speed_kmh = speed_kmh
        self.send_ISP_MSL(Msg=f"{TextColors.GREEN}Velocidad fijada para PLID {plid} a {speed_kmh} km/h")

    def _cmd_stop(self, packet: ISP_MSO, plid: str):
        """Detiene el control de dirección y velocidad."""
        behavior = self._get_behavior(packet.UCID, plid)
        if not behavior: return
        
        behavior.reset_direction()
        behavior.reset_speed()
        self.send_ISP_MSL(Msg=f"{TextColors.YELLOW}Control desactivado para PLID {plid}")

    def _cmd_direction_point(self, packet: ISP_MSO, plid: str, x: float, y: float):
        """Dirige la IA hacia una coordenada X, Y fija."""
        behavior = self._get_behavior(packet.UCID, plid)
        if not behavior: return
        
        behavior.reset_direction()
        behavior.target_point_m = (x, y)
        behavior.logic_reversed = False
        self.send_ISP_MSL(Msg=f"{TextColors.GREEN}Punto fijado para PLID {plid} en ({x}, {y})")

    def _cmd_follow(self, packet: ISP_MSO, plid_ai: int, plid_target: int):
        """Fija a otro vehículo como objetivo."""
        behavior = self._get_behavior(packet.UCID, plid_ai)
        if not behavior: return
        
        if plid_ai == plid_target:
            self.send_ISP_MSL(Msg=f'{TextColors.RED}Error: El objetivo no puede ser la propia AI.')
            return
        
        if plid_target not in self.user_manager.players and plid_target not in self.user_manager.ais:
            self.send_ISP_MSL(Msg=f'{TextColors.RED}Error: El PLID {plid_target} no existe.')
            return
        
        behavior.reset_direction()
        behavior.target_point_m = plid_target
        behavior.logic_reversed = False
        self.send_ISP_MSL(Msg=f"{TextColors.GREEN}Siguiendo a PLID {plid_target} (IA {plid_ai})")

    def _cmd_run_away(self, packet: ISP_MSO, plid_ai: int, plid_target: int):
        """Ordena a la IA huir de otro vehículo."""
        behavior = self._get_behavior(packet.UCID, plid_ai)
        if not behavior: return
        
        if plid_ai == plid_target:
            self.send_ISP_MSL(Msg=f'{TextColors.RED}Error: El objetivo no puede ser la propia AI.')
            return
        
        if plid_target not in self.user_manager.players and plid_target not in self.user_manager.ais:
            self.send_ISP_MSL(Msg=f'{TextColors.RED}Error: El PLID {plid_target} no existe.')
            return
        
        behavior.reset_direction()
        behavior.target_point_m = plid_target
        behavior.logic_reversed = True
        self.send_ISP_MSL(Msg=f"{TextColors.GREEN}Huyendo de PLID {plid_target} (IA {plid_ai})")

    def _cmd_adaptive(self, packet: ISP_MSO, plid: int, min_speed: float, max_speed: float, min_dist: float, max_dist: float):
        """Configura los límites de velocidad dinámica."""
        behavior = self._get_behavior(packet.UCID, plid)
        if not behavior: return
        
        behavior.target_speed_kmh = AdaptiveSpeedConfig(min_speed, max_speed, min_dist, max_dist)
        self.send_ISP_MSL(Msg=f"{TextColors.GREEN}Modo adaptativo configurado para PLID {plid}")

    def _get_oldest_my_ai_plid(self, ucid: int) -> int | None:
        """Devuelve el PLID de la IA más antigua del usuario, o None si no tiene ninguna."""
        user = self.user_manager.users.get(ucid)
        if not user:
            return None
        my_plids = user.plids_ais_actives
        # ais mantiene orden de inserción → primer match = más antigua en pista
        return next((plid for plid in self.user_manager.ais if plid in my_plids), None)

    def _cmd_spec(self, plid: int):
        """Envía a la IA al modo espectadores."""
        if plid not in self.user_manager.ais:
            self.send_ISP_MSL(Msg=f'{TextColors.RED}Error: PLID {plid} no asociado a ninguna AI')
            return
        ai_name = self.user_manager.ais[plid].ai_name
        self.send_ISP_MST(Msg=f'/spec {ai_name}')

    # BLOQUE 2 ==============================================

    def _cmd_route_follow(self, packet: ISP_MSO, route_name: str, plid: int):
        """Inicia el seguimiento de una ruta pre-grabada."""
        behavior = self._get_behavior(packet.UCID, plid)
        if not behavior: return
        
        if route_name not in self.route_manager.loaded_routes:
            self.send_ISP_MSL(Msg=f"{TextColors.RED}Error: La ruta '{route_name}' no existe.")
            return
            
        behavior.reset_direction()
        behavior.reset_speed()
        behavior.active_mode = RouteMode(route_name)
        self.send_ISP_MSL(Msg=f"{TextColors.CYAN}Siguiendo ruta: {TextColors.WHITE}{route_name} {TextColors.CYAN}(IA {plid})")
    
    def _route_start(self, plid: int, route_name: str):
        """Comienza la grabación de nodos para una nueva ruta."""
        if plid in self.user_manager.players:
            self.route_manager.start(self.user_manager.players[plid], route_name)
            return
        if plid in self.user_manager.ais:
            self.route_manager.start(self.user_manager.ais[plid], route_name)
            return
        self.send_ISP_MSL(Msg=f'{TextColors.RED}Error: El PLID {plid} no está en pista.')
            
    def _route_stop(self, plid: int):
        """Finaliza y guarda la grabación de la ruta actual."""
        self.route_manager.stop(plid)

    # BLOQUE 3 ==============================================

    def _cmd_map_freeroam(self, packet: ISP_MSO, plid_ai: int):
        """Activa el modo explorador (GPS) en la IA indicada."""
        ai = self.user_manager.ais.get(plid_ai)
        if not ai:
            self.send_ISP_MSL(Msg=f'{TextColors.RED}Error: El PLID {plid_ai} no es una IA.')
            return
        
        behavior = self._get_behavior(packet.UCID, plid_ai)
        if not behavior: return
        behavior.reset_direction()
        behavior.reset_speed()
        behavior.active_mode = FreeroamMode(speed_limit_bias=random.uniform(-0.05, 1.05))
        
        self.send_ISP_MSL(Msg=f"{TextColors.CYAN}Modo Explorador activado para {TextColors.WHITE}{ai.ai_name} {TextColors.CYAN}(PLID {plid_ai})")

    def _cmd_ai_state(self, packet: ISP_MSO, ai_plid: int):
        """Comando para ver el estado interno y decisiones de navegación de una IA."""
        
        # 1. Obtener la IA
        ai = self.user_manager.ais.get(ai_plid)
        if not ai:
            self.send_ISP_MSL(Msg=f'^1Error: El PLID {ai_plid} no es una IA o no existe.')
            return
        
        # 2. Obtener su behavior (Cerebro)
        behavior: AIBehavior = self._get_behavior(packet.UCID, ai_plid)
        if not behavior:
            self.send_ISP_MSL(UCID=packet.UCID, Msg=f'^1Error: La IA {ai.ai_name} no tiene inicializado su AIBehavior.')
            return

        mode: FreeroamMode = behavior.active_mode
        
        # Formateo seguro de Target Speed (por si es AdaptiveSpeedConfig o None)
        t_speed = 0.0
        if isinstance(behavior.target_speed_kmh, (int, float)):
            t_speed = behavior.target_speed_kmh
        
        # 3. Mostrar Información General (AIBehavior)
        self.send_ISP_MSL(Msg=f'^3=== ESTADO IA: {ai.ai_name} (PLID: {ai_plid}) ===')
        self.send_ISP_MSL(Msg=f'^7Velocidad Objetivo: ^2{t_speed:.1f} km/h ^7| Marcha: ^2{getattr(behavior.gear_mode, "name", behavior.gear_mode)}')
        
        # 4. Mostrar Información Específica si está en FreeroamMode
        if type(mode).__name__ == 'FreeroamMode':
            # Estado táctico y maniobra
            maneuver = getattr(mode.maneuver_state, "name", mode.maneuver_state)
            state = getattr(mode, 'overtake_state', 'IDLE')
            self.send_ISP_MSL(Msg=f'^7Modo: ^6Freeroam ^7| Maniobra actual: ^6{maneuver} ^7| Estado actual: ^6{state}')
            
            # Localización
            c_type = mode.current_type if mode.current_type else "Ninguno"
            c_id = mode.current_id if mode.current_id else "N/A"
            self.send_ISP_MSL(Msg=f'^7Loc: ^2{c_type} ({c_id}) ^7| Nodo actual: ^2{mode.node_index}')
            
            # Micronavegación (Triggers y desvíos)
            n_type = mode.next_link_type if mode.next_link_type else "Ninguno"
            n_id = mode.next_link_id if mode.next_link_id else "N/A"
            self.send_ISP_MSL(Msg=f'^7Próximo Enlace: ^3{n_type} ({n_id})')
            
            # Estados del coche y entorno
            blinkers = getattr(mode.blinkers_active, "name", mode.blinkers_active)
            self.send_ISP_MSL(Msg=f'^7Intermitente: ^3{blinkers}^7| Sentido contrario: ^2{mode.is_driving_opposing}')
            
            # Rutas para contexto
            p_road = mode.previous_road_id if mode.previous_road_id else "N/A"
            c_road = mode.current_road_id if mode.current_road_id else "N/A"
            self.send_ISP_MSL(Msg=f'^7Contexto Vía -> Viene de: ^7{p_road} ^7| Vía general: ^7{c_road}')
            
        else:
            # Por si está en RouteMode o Parada (None)
            modo_str = type(mode).__name__ if mode else "Ninguno (Parada/Desactivada)"
            self.send_ISP_MSL(Msg=f'^7Modo Activo: ^3{modo_str}')

        self.send_ISP_MSL(Msg=f'^3======================================')

    # ==========================================
    # 4. TEST'S Y UTILIDADES DE DESARROLLO
    # ==========================================

    # [!] OJO: Como añadiste el comando con 'True' al final en add_cmd, recibe packet y args
    def _test_routes(self, packet: ISP_MSO, routes: str):
        # daemon=True hace que el hilo muera automáticamente si cierras InSim
        threading.Thread(target=self._test, args=(packet, routes), daemon=True).start()
    
    def _test(self, packet: ISP_MSO, routes: str):
        routes_list = routes.strip().split()
        
        if not routes_list:
            self.send_ISP_MSL(Msg=f"{TextColors.RED}[TEST] Error: Debes especificar al menos una ruta.")
            return
        
        for route in routes_list:
            if route not in self.route_manager.loaded_routes:
                self.send_ISP_MSL(Msg=f"{TextColors.RED}[TEST] Error: Falta cargar la ruta '{route}'.")
                return

        self.send_ISP_MSL(Msg=f"{TextColors.YELLOW}[TEST] Iniciando carga masiva de tráfico...")
        
        index = 0
        # Bucle de gestión persistente
        while True:
            # Cálculo de ocupación sumando humanos e IAs
            count_players_ais = len(self.user_manager.players) + len(self.user_manager.ais)
            
            # 2. FIX: Si estamos en el límite (39), dormimos el hilo para no quemar la CPU
            if count_players_ais == 39:
                time.sleep(5)
                continue
            
            # Si nos hemos pasado del límite (40 o más), mandamos a spectate la IA más antigua del usuario
            if count_players_ais > 39:
                plid_to_remove = self._get_oldest_my_ai_plid(packet.UCID)
                if plid_to_remove is not None:
                    self._cmd_spec(plid_to_remove)
                    self.logger.info(f"IA PLID {plid_to_remove} (más antigua del usuario) removida para hacer espacio")
                    time.sleep(1)  # Pequeña pausa para que LFS la procese
            
            # Si faltan coches (menos de 39)
            elif count_players_ais < 39:
            
                # 1. Mandamos crear una IA
                self._cmd_add()
            
                # 2. Esperamos a que LFS la cree y nuestro InSim la procese
                time.sleep(1.5)
                
                # 3. FIX: ¡Volvemos a pedir las AIs porque ahora hay una nueva en pista!
                ais_actualizadas = tuple(self.user_manager.ais.values())
                if not ais_actualizadas:
                    continue
                    
                ai_nueva = ais_actualizadas[-1]
                
                # Buen prunto para añadir extras como luces, etc
                
                self.send_ISP_AIC(PLID=ai_nueva.player.plid, Inputs=[AIV(Input=CS.HEADLIGHTS, Value=CSVAL.HEADLIGHTS.LOW)])
                
                # Turnamos la ruta
                route = routes_list[index]
                index+=1
                if index == len(routes_list): index = 0
                
                # 4. Asignación de ruta a la nueva IA
                self._cmd_route_follow(packet, route, ai_nueva.player.plid)
                
                self.logger.info(f"IA {ai_nueva.ai_name} (PLID {ai_nueva.player.plid}) asignada a la ruta {route}")
                
                # Dejamos que la AI recorra camino antes de sacar otra
                time.sleep(random.uniform(2.5, 6))
    

    def _test_freeroam(self, packet: ISP_MSO, num: int):
        # 1. Validación de los límites (entre 1 y 40)
        if num < 1 or num > 40:
            # Mandamos un mensaje de error al chat de LFS
            self.send_ISP_MSL(Msg=f"{TextColors.RED}[ERROR] El límite debe estar entre 1 y 40 jugadores.")
            return

        # 2. Guardamos la cantidad deseada en la instancia
        self._target_freeroam_count = num

        # 3. Control de hilos: Si ya hay un bucle corriendo, simplemente actualizamos la meta y avisamos
        if getattr(self, '_is_freeroam_loop_running', False):
            self.send_ISP_MSL(Msg=f"{TextColors.YELLOW}[TEST] Límite actualizado a {num} jugadores.")
            return

        # Si no hay un hilo corriendo, lo marcamos como activo y lo iniciamos
        self._is_freeroam_loop_running = True
        self.send_ISP_MSL(Msg=f"{TextColors.YELLOW}[TEST] Iniciando gestor automático de tráfico. Límite: {num}")
        
        # daemon=True hace que el hilo muera automáticamente si cierras InSim
        threading.Thread(target=self._run_test_freeroam, args=(packet,), daemon=True).start()
    
    def _run_test_freeroam(self, packet: ISP_MSO):
        # Bucle de gestión persistente
        while True:
            # Leemos la meta actual (por si ha cambiado mientras el bucle dormía)
            target_num = self._target_freeroam_count

            # Cálculo de ocupación sumando humanos e IAs
            count_players_ais = len(self.user_manager.players) + len(self.user_manager.ais)
            
            # Si estamos en el límite, dormimos el hilo para no quemar la CPU
            if count_players_ais == target_num:
                time.sleep(5)
                continue
            
            # Si nos hemos pasado del límite, mandamos a spectate la IA más antigua del usuario
            if count_players_ais > target_num:
                plid_to_remove = self._get_oldest_my_ai_plid(packet.UCID)
                if plid_to_remove is not None:
                    self._cmd_spec(plid_to_remove)
                    self.logger.info(f"IA PLID {plid_to_remove} (más antigua del usuario) removida para ajustar al límite de {target_num}")
                    time.sleep(0.05)  # Pequeña pausa para que LFS la procese
            
            # Si faltan coches (menos del límite actual)
            elif count_players_ais < target_num:
            
                # 1. Mandamos crear una IA
                self._cmd_add()
            
                # 2. Esperamos a que LFS la cree y nuestro InSim la procese
                time.sleep(1.5)
                
                # 3. Volvemos a pedir las AIs porque ahora hay una nueva en pista
                ais_actualizadas = tuple(self.user_manager.ais.values())
                if not ais_actualizadas:
                    continue
                    
                ai_nueva = ais_actualizadas[-1]
                
                # Buen punto para añadir extras como luces, etc
                self.send_ISP_AIC(PLID=ai_nueva.player.plid, Inputs=[AIV(Input=CS.HEADLIGHTS, Value=CSVAL.HEADLIGHTS.LOW)])
                
                # 4. Despertamos a la nueva IA en modo Freeroam usando tu comando
                self._cmd_map_freeroam(packet, ai_nueva.player.plid)
                
                self.logger.info(f"IA {ai_nueva.ai_name} (PLID {ai_nueva.player.plid}) iniciada en Freeroam")
                
                # Dejamos que la AI recorra camino antes de sacar otra
                time.sleep(2)



