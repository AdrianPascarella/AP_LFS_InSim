from __future__ import annotations  # SIEMPRE EN LA LÍNEA 1

import logging
import math
import re
from dataclasses import dataclass
from typing import Any, Callable

from lfs_insim.insim_enums import SND
from lfs_insim.packet_sender_mixin import PacketSenderMixin
from lfs_insim.packets import ISP_MSL, ISP_MSO

__all__ = [
    # Chat / comandos
    "separate_message",
    "separate_command_args",
    "strip_lfs_colors",
    "TextColors",
    "Command",
    "CMDManager",
    # Control
    "PIDController",
    # Conversión de unidades LFS
    "lfs_pos_to_meters",
    "lfs_speed_to_kmh",
    "lfs_angle_to_degrees",
    "lfs_angvel_to_degrees_per_second",
    # Geometría 3D genérica
    "calc_dist_3d",
]

logger = logging.getLogger(__name__)


def separate_message(packet: ISP_MSO) -> tuple[str, str]:
    """De un mensaje recibido por LFS, separa al usuario del contenido."""
    user = packet.Msg[: packet.TextStart].strip()
    content = packet.Msg[packet.TextStart :].strip()
    return user, content


def separate_command_args(
    prefix: str, packet: ISP_MSO
) -> tuple[str, list[str]] | tuple[None, None]:
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
    return re.sub(r"\^[0-9^Lhsv]", "", text).strip()


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
    DEFAULT = "^8"  # Color estándar del InSim
    NORMAL = "^9"  # Resetea al color original del chat


class PIDController:
    """
    Controlador PID optimizado para SimRacing (Anti-Windup & Anti-Derivative Kick).
    """

    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        out_min: float = -1.0,
        out_max: float = 1.0,
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd

        # Límites reales de salida (ej: -1.0 a 1.0 para pedales o volante)
        self.out_min = out_min
        self.out_max = out_max

        self.integral = 0.0
        self.prev_current = 0.0  # [!] FIX: Guardamos la medición, no el error
        self.first_run = True  # Para evitar un pico en el primer frame

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
    args: tuple[tuple[str, Any]] | str | None
    funct: Callable
    _prefix: str
    is_mso_required: bool = False

    def __post_init__(self):
        self.how_to_use = self._how_to_use()

    def _how_to_use(self):
        if not self.args:
            text_args = ""
        elif isinstance(self.args, str):
            text_args = f"[{self.args} (puede contener espacios)]"
        elif isinstance(self.args[0], tuple):
            text_args = " ".join(
                (f"[{arg[0]} ({arg[1].__name__})]" for arg in self.args)
            )
        else:
            raise Exception(
                f"Tipo de argumento invalido en la creación del comando {self.name}"
            )

        # Le damos color a la instrucción de uso
        return f"{TextColors.YELLOW}Uso: {TextColors.WHITE}{self._prefix} {self.name} {text_args}"

    # CAMBIO 1: El tipado de retorno ahora es más limpio (Lista de argumentos o False si falló)
    def _prepare_args(self, using_args) -> list[Any] | bool:
        expected_args = self.args
        usefull_args = []

        # CAMBIO 2: Si no hay argumentos, devolvemos una lista vacía en vez de None
        if not expected_args:
            return []

        if isinstance(expected_args, str):
            args_str = " ".join(using_args)
            if not args_str:
                self.send(
                    ISP_MSL(
                        Msg=f'{TextColors.RED}Error: el comando "{self.name}" requiere texto.',
                        Sound=SND.INVALIDKEY,
                    )
                )
                self.send(ISP_MSL(Msg=self.how_to_use))
                return False  # CAMBIO 3: Devolvemos False en vez de -1

            # CAMBIO 4: Metemos el string en una lista para uniformidad
            return [args_str]

        if isinstance(expected_args, tuple):
            if len(using_args) < len(expected_args):
                self.send(
                    ISP_MSL(
                        Msg=f"{TextColors.RED}Error: faltan argumentos. ({len(using_args)} de {len(expected_args)} requeridos)",
                        Sound=SND.INVALIDKEY,
                    )
                )
                self.send(ISP_MSL(Msg=self.how_to_use))
                return False  # CAMBIO 3

            count = 0
            while count < len(expected_args):
                try:
                    usefull_args.append(expected_args[count][1](using_args[count]))
                    count += 1
                except Exception as e:
                    logger.info(
                        f"Error por el argumento {using_args[count]} en el comando {self.name}: {e}"
                    )
                    self.send(
                        ISP_MSL(
                            Msg=f'{TextColors.RED}Argumento invalido: "{using_args[count]}"',
                            Sound=SND.INVALIDKEY,
                        )
                    )
                    self.send(ISP_MSL(Msg=self.how_to_use))
                    return False  # CAMBIO 3
            return usefull_args

    def use(self, packet: "ISP_MSO", using_args: list[Any]):
        args = self._prepare_args(using_args)

        # CAMBIO 5: Comprobamos si la validación falló comparando con False
        if args is False:
            logger.info(f"No se pudo ejecutar el comando {self.name}")
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

    def submit(self) -> "CMDManager":
        self.send(
            ISP_MSL(
                Msg=f'{TextColors.YELLOW}Usa "{TextColors.WHITE}{self._prefix}{TextColors.YELLOW}" para ver los comandos.'
            )
        )
        return self

    def add_cmd(
        self,
        name: str,
        description: str,
        args: tuple[tuple[str, Any]] | str | None,
        funct: Callable,
        is_mso_required: bool = False,
    ) -> "CMDManager":
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
            self.send(
                ISP_MSL(
                    Msg=f'{TextColors.YELLOW}No hay comandos "{self.cmd_base}" disponibles'
                )
            )
            return

        self.send(
            ISP_MSL(
                Msg=f"{TextColors.GREEN}=== {TextColors.WHITE}Comandos de {self._prefix} {TextColors.GREEN}==="
            )
        )

        # Extraemos los nombres y los agrupamos de 4 en 4
        cmd_names = list(self._cmds.keys())
        chunk_size = 4

        for i in range(0, len(cmd_names), chunk_size):
            chunk = cmd_names[i : i + chunk_size]
            # Formateamos la línea: cmd1 | cmd2 | cmd3 | cmd4
            line = f"{TextColors.GREEN} | {TextColors.WHITE}".join(chunk)
            self.send(ISP_MSL(Msg=f"{TextColors.WHITE}{line}"))

        # Mini-tutorial al final
        self.send(
            ISP_MSL(
                Msg=f"{TextColors.YELLOW}Info detallada: {TextColors.WHITE}{self._prefix} <comando> ?"
            )
        )

    def handle_commands(self, packet: "ISP_MSO", args: list):
        if not args or not self._cmds:
            self._show_cmds()
            return

        cmd = args.pop(0)

        # [NUEVO] Si el usuario pone "?", "!map help" o "!map ?"
        if cmd in ["?", "help"]:
            if args and args[0] in self._cmds:
                target = self._cmds[args[0]]
                self.send(
                    ISP_MSL(
                        Msg=f"{TextColors.GREEN}{target.name}: {TextColors.WHITE}{target.description}"
                    )
                )
                self.send(ISP_MSL(Msg=target.how_to_use))
            else:
                self._show_cmds()
            return

        # Si el comando no existe
        if cmd not in self._cmds:
            self.send(
                ISP_MSL(
                    Msg=f'{TextColors.RED}Comando "{cmd}" no reconocido.',
                    Sound=SND.INVALIDKEY,
                )
            )
            self._show_cmds()
            return

        # [NUEVO] Si el usuario pone "!map comando ?" para ver la descripción de algo concreto
        if args and args[0] == "?":
            target = self._cmds[cmd]
            self.send(
                ISP_MSL(
                    Msg=f"{TextColors.GREEN}{target.name}: {TextColors.WHITE}{target.description}"
                )
            )
            self.send(ISP_MSL(Msg=target.how_to_use))
            return

        # Si todo está correcto, ejecutamos
        self._cmds[cmd].use(packet, args)


# Transformación de unidades


def lfs_pos_to_meters(unit: int | float, rev: bool = False) -> float | int:
    """
    Convierte unidades de posición LFS (1m = 65536 units) a metros.
    Si rev=True hace lo contrario.
    """
    if rev:
        return int(unit * 65536.0)
    return unit / 65536.0


def lfs_speed_to_kmh(speed: int, rev: bool = False) -> float | int:
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


def lfs_angvel_to_degrees_per_second(
    unit: int | float, rev: bool = False
) -> float | int:
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


def calc_dist_3d(
    x1: float, y1: float, z1: float, x2: float, y2: float, z2: float
) -> float:
    """Calcula la distancia real en 3D (indiferente de unidades aunque todos los datos deben estar en la misma unidad)."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
