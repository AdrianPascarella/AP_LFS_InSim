#!/usr/bin/env python3
"""
users_management/main.py - Gestión Centralizada de Usuarios y Jugadores.
"""

from lfs_insim import InSimApp
from lfs_insim.packets import *
from insims.users_management.um_class import *
from lfs_insim.utils import separate_command_args, CMDManager

# ---------------------------------------------------------
# 2. MÓDULO PRINCIPAL
# ---------------------------------------------------------

class UsersManagement(InSimApp):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # --- Configuración ---
        self.cmd_base = 'um'
        self.cmd_prefix = '.'      # self.config.get('prefix', '!')
        self.cmds_white_list: set[str] = {
            self.config.get('user_name', 'AdrianPascarella'), 
            'AngeloPascarella',
            'Guest'
        }
        
        # --- Almacenamiento Centralizado (Single Source of Truth) ---
        self.users: dict[int, User] = {}             # UCID -> Objeto User
        self.players: dict[int, Player] = {}         # PLID -> Objeto Player
        self.ais: dict[int, AI] = {}                 # PLID -> Objeto AI

        self.logger.info(f"Módulo {self.name} inicializado con arquitectura de objetos.")

    def set_isi_packet(self):
        """Configura los flags necesarios para rastrear posiciones e IAs."""
        super().set_isi_packet()
        self.isi.Flags |= (ISF.LOCAL | ISF.MCI)

    # ---------------------------------------------------------
    # 3. LÓGICA DE EVENTOS Y LIMPIEZA
    # ---------------------------------------------------------

    def on_connect(self):
        # Sincronización inicial
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NCN)
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NPL)
        
        self.cmds_um = CMDManager(self.cmd_prefix, self.cmd_base)
        self.cmds_um.add_cmd(
            name='user-info',
            description='Mostrar la información de un usuario',
            args='user_name',
            funct=self._show_user_info
        ).add_cmd(
            name='users-info',
            description='Mostrar un listado de las conecciones con sus datos',
            args=None,
            funct=self._show_users_list
        ).add_cmd(
            name='ais-info',
            description='Mostrar un listado de las AI\'s',
            args=None,
            funct=self._show_ais_list
        ).add_cmd(
            name='cmds-white-list',
            description='Mostrar listado de usuarios con el poder de ejecutar comandos',
            args=None,
            funct=self._show_white_list
        ).add_cmd(
            name='add-user-cmds-white-list',
            description='Da a un usuario privilegios de usar comandos',
            args='user_name',
            funct=self._add_user_to_cmds_white_list
        ).add_cmd(
            name='remove-user-cmds-white-list',
            description='Quitarle a un usuario sus privilegios de usar comandos',
            args='user_name',
            funct=self._remove_user_to_cmds_white_list
        ).submit()
    
    def on_ISP_ISM(self, packet):
        # Sincronización al conectarse a un servidor online
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NCN)
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NPL)
        self.send_ISP_MSL(Msg=f'Te has conectado al servidor {packet.Hname}')

    def on_ISP_TINY(self, packet: ISP_TINY):
        if packet.SubT == TINY.MPE: # Fin de carrera / Limpieza de pista
            self._clear_all_memory()

    def _clear_all_memory(self):
        self.users.clear()
        self.players.clear()
        self.ais.clear()
        self.logger.info("Memoria de usuarios y jugadores liberada.")

    # --- Gestión de Conexiones (UCID) ---

    def on_ISP_NCN(self, packet: ISP_NCN):
        """Nueva conexión."""
        user = User(
            packet.UName, packet.UCID, packet.PName,
            packet.Admin, packet.Flags
        )
        self.users[packet.UCID] = user

    def on_ISP_CNL(self, packet: ISP_CNL):
        """Desconexión."""
        user = self.users.pop(packet.UCID, None)
        if not user:
            return
        self.logger.info(f"Usuario {user.user_name} desconectado. Limpieza realizada.")
        
        # Borramos todos los coches (IAs) que pertenecían a este usuario usando una lista auxiliar
        plids_a_borrar = [plid for plid, ai in self.ais.items() if ai.player.ucid == packet.UCID]
        for plid in plids_a_borrar:
            ai = self.ais.pop(plid)
            self.logger.info(f'AI "{ai.ai_name}" desconectada y limpiada.')
            
        # Borrar también el Player principal si estaba en pista
        if user.plid and user.plid in self.players:
            self.players.pop(user.plid)

    # --- Gestión de Pista (PLID) ---

    def on_ISP_NPL(self, packet: ISP_NPL):
        """Nuevo coche en pista."""
        is_ai = bool(packet.PType & PTYPE.AI)
        
        player = Player(
            packet.PLID, packet.PType, packet.Plate,
            packet.Flags, packet.CName,packet.SName,
            packet.Tyres, packet.H_Mass, packet.H_TRes,
            packet.Model, packet.Pass, packet.RWAdj,
            packet.FWAdj, packet.SetF, packet.Config,
            packet.Fuel, packet.UCID
        )

        # Vincular el PLID a su dueño (User)
        if not is_ai:
            self.players[player.plid] = player
            self.users[packet.UCID].plid = player.plid
            return
        
        ai = AI(player, packet.PName)
        self.ais[ai.player.plid] = ai
        # PROTEGER: Asegurarnos de que el usuario dueño existe antes de asignarle la IA
        if ai.player.ucid in self.users:
            self.users[ai.player.ucid].plids_ais_actives.add(ai.player.plid)
        else:
            self.logger.warning(f"IA {packet.PName} añadida, pero su UCID dueño ({ai.player.ucid}) no está en self.users!")

    def on_ISP_PLL(self, packet: ISP_PLL):
        """Coche sale de pista."""
        plid = packet.PLID
        if plid in self.players:
            player = self.players.pop(plid)
            self.users[player.ucid].plid = None
            self.logger.info(f'Salió de pista el jugador {self.users[player.ucid].player_name} y su plid volvió a None')
            return
        if plid in self.ais:
            ai = self.ais.pop(plid)
            self.users[ai.player.ucid].plids_ais_actives.remove(plid)
            self.logger.info(f'Salió de pista la ai {ai.ai_name} que pertenecía al jugador {self.users[ai.player.ucid].player_name}')
            return

    def on_ISP_MCI(self, packet: ISP_MCI):
        """Telemetría de alta frecuencia. (CORREGIDO)"""
        for car in packet.Info:
            # 1. ESCUDO ANTI RACE-CONDITION Y OPTIMIZACIÓN
            # Si el coche aún no existe en nuestros registros, saltamos al siguiente.
            if car.PLID not in self.players and car.PLID not in self.ais:
                continue

            # 2. Ahora sí, creamos el objeto (solo para coches válidos)
            telemetry = Telemetry(
                node=car.Node,
                lap=car.Lap,
                position_race=car.Position,
                info=CCIFlags(car.Info),
                coordinates=Coordinates(car.X,car.Y,car.Z),
                speed=Speed(car.Speed),
                direction=Angle(car.Direction),
                heading=Angle(car.Heading),
                angvel=AngularVelocity(car.AngVel)
            )
            
            # 3. Asignación directa
            if car.PLID in self.players:
                self.players[car.PLID].telemetry = telemetry
            else: # Ya sabemos que si no es player, es ai por el filtro de arriba
                self.ais[car.PLID].player.telemetry = telemetry

    # ---------------------------------------------------------
    # 4. COMANDOS
    # ---------------------------------------------------------

    def user_autorized_cmd(self, white_list: set, cmd_base: str, cmd: str, ucid: int) -> bool:
        """Valida si un UCID tiene permiso para ejecutar un comando."""
        if cmd != cmd_base: return False
        
        if ucid == 0: return True # El servidor siempre tiene permiso
        user_name = self.users[ucid].user_name
        if user_name in white_list: return True
        
        # Intento fallido
        self.logger.warning(f"Acceso denegado: {user_name} intentó usar '{cmd}'")
        self.send_ISP_MSL(Msg=f"^1Acceso denegado para {user_name}")
        return False

    def on_ISP_MSO(self, packet: ISP_MSO):
        cmd, args = separate_command_args(self.cmd_prefix, packet)
        if self.user_autorized_cmd(self.cmds_white_list, self.cmd_base, cmd, packet.UCID):
            self.cmds_um.handle_commands(packet, args)

    def _show_user_info(self, searched_name: str):
        # Búsqueda optimizada de usuario
        user = next((u for u in self.users.values() if u.user_name == searched_name), None)
        
        if not user:
            self.send_ISP_MSL(Msg=f'Usuario "{searched_name}" no encontrado.')
            return
            
        self.send_ISP_MSL(Msg=f"^7Info: ^3{user.user_name} ^7(UCID {user.ucid})")
        
        user_info = ' | '.join((f'UCID: {user.ucid}', f'Admin: {user.admin}'))
        all_info = [user_info]
        
        if not user.plid:
            all_info.append('(No está en pista)')
        else:
            player = self.players[user.plid]
            player_info = ' | '.join((f'Plate: {player.plate}', f'CarName: {player.car_name}', f'SkinName: {player.skin_name}'))
            all_info.append(player_info)
            
            # Comprobación de seguridad para la telemetría
            telemetry = player.telemetry
            if telemetry:
                telemetry_info = f"Pos: ({telemetry.coordinates.x_m:.2f}, {telemetry.coordinates.y_m:.2f}) | Vel: {telemetry.speed.speed_kmh:.1f} km/h"
                all_info.append(telemetry_info)
            else:
                all_info.append('Telemetría: Calculando...')
                
        if not user.plids_ais_actives:
            all_info.append("(No tiene AI's)")
        else:
            ais_info = (' | '.join(f'PLID: {ai.player.plid}, AIName: {ai.ai_name}' for ai in self.ais.values() if ai.player.plid))
            all_info.append(ais_info)
        
        for info in all_info:
            self.send_ISP_MSL(Msg=info)

    def _show_users_list(self):
        if not self.users:
            self.send_ISP_MSL(Msg="Servidor vacío.")
            return

        self.send_ISP_MSL(Msg="=== USUARIOS CONECTADOS ===")
        for user in self.users.values():
            # Corregido el error de len(user.plid)
            status = f"^2En Pista (PLID: {user.plid})" if user.plid else "^8Espectador"
            self.send_ISP_MSL(Msg=f"UCID:{user.ucid} | {user.user_name} | {status}")
    
    def _show_ais_list(self):
        if not self.ais:
            self.send_ISP_MSL(Msg="No hay AI's en pista")
            return
        for ai in self.ais.values():
            # Comprobación de seguridad para la telemetría
            telemetry = ai.player.telemetry
            if telemetry:
                self.send_ISP_MSL(Msg=' | '.join((f'PLID: {ai.player.plid}', f'DueñoUCID: {ai.player.ucid}', f'AIName: {ai.ai_name}', f'Car: {ai.player.car_name}', f'Coordinates: ({telemetry.coordinates.x_m}, {telemetry.coordinates.y_m}, {telemetry.coordinates.z_m})', f'SpeedKmh: {telemetry.speed.speed_kmh:.2f}')))
            else:
                self.send_ISP_MSL(Msg=' | '.join((f'PLID: {ai.player.plid}', f'DueñoUCID: {ai.player.ucid}', f'AIName: {ai.ai_name}', f'Car: {ai.player.car_name}', 'Telemetría: Calculando...')))

    def _show_white_list(self):
        if not self.cmds_white_list:
            self.send_ISP_MSL(Msg='"cmds_white_list" está vacío')
            return
        for user_name in self.cmds_white_list:
            status = 'Desconectado'
            for user in self.users.values():
                if user.user_name == user_name:
                    status = 'Conectado'
            self.send_ISP_MSL(Msg=f'{user_name}: {status}')
    
    def _add_user_to_cmds_white_list(self, user_name: str):
        self.cmds_white_list.add(user_name)
        self.send_ISP_MSL(Msg=f'Usuario "{user_name}" añadido a "cmds_white_list"')
    
    def _remove_user_to_cmds_white_list(self, user_name: str):
        if user_name not in self.cmds_white_list:
            self.send_ISP_MSL(Msg=f'El usuario "{user_name}" no se encuentra en "cmds_white_list"')
            return
        self.cmds_white_list.remove(user_name)
        self.send_ISP_MSL(Msg=f'Usuario "{user_name}" eliminado de "cmds_white_list"')