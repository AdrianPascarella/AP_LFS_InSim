from enum import IntEnum, IntFlag

# Versión del Protocolo
INSIM_VERSION = 10

class LFS_LIMITS:
    """
    Límites y restricciones en Live for Speed.
    Estos valores definen los máximos permitidos en varios aspectos del juego.
    """

    # Límites de Conexiones y Jugadores
    PLH_MAX_PLAYERS = 48    # Máximo de jugadores en un paquete PLH
    REO_MAX_PLAYERS = 48    # Máximo de jugadores en un paquete REO
    NLP_MAX_CARS = 40       # Máximo de coches en un paquete NLP (Node and Lap)
    MCI_MAX_CARS = 16       # Máximo de coches en un paquete MCI (Multi Car Info)

    # Límites de Contenido y Seguridad
    MAL_MAX_MODS = 120      # Máximo de Mods permitidos en la lista MAL
    IPB_MAX_BANS = 120      # Máximo de IPs en la lista de baneo (IPB)

    # Objetos y Control
    AXM_MAX_OBJECTS = 60    # Máximo de objetos de layout por paquete AXM
    AIC_MAX_INPUTS = 20     # Máximo de entradas de control de IA

NOT_CHANGED = 255



class ISP(IntEnum):
    """
    Packet Types - El segundo byte de cualquier paquete es uno de estos.
    Referencia exacta del archivo proporcionado (0 a 69).
    """
    NONE = 0         # not used
    ISI = 1          # instruction : insim initialise
    VER = 2          # info        : version info
    TINY = 3         # both ways   : multi purpose
    SMALL = 4        # both ways   : multi purpose
    STA = 5          # info        : state info
    SCH = 6          # instruction : single character
    SFP = 7          # instruction : state flags pack
    SCC = 8          # instruction : set car camera
    CPP = 9          # both ways   : cam pos pack
    ISM = 10         # info        : start multiplayer
    MSO = 11         # info        : message out
    III = 12         # info        : hidden /i message
    MST = 13         # instruction : type message or /command
    MTC = 14         # instruction : message to a connection
    MOD = 15         # instruction : set screen mode
    VTN = 16         # info        : vote notification
    RST = 17         # info        : race start
    NCN = 18         # info        : new connection
    CNL = 19         # info        : connection left
    CPR = 20         # info        : connection renamed
    NPL = 21         # info        : new player (joined race)
    PLP = 22         # info        : player pit (keeps slot in race)
    PLL = 23         # info        : player leave (spectate - loses slot)
    LAP = 24         # info        : lap time
    SPX = 25         # info        : split x time
    PIT = 26         # info        : pit stop start
    PSF = 27         # info        : pit stop finish
    PLA = 28         # info        : pit lane enter / leave
    CCH = 29         # info        : camera changed
    PEN = 30         # info        : penalty given or cleared
    TOC = 31         # info        : take over car
    FLG = 32         # info        : flag (yellow or blue)
    PFL = 33         # info        : player flags (help flags)
    FIN = 34         # info        : finished race
    RES = 35         # info        : result confirmed
    REO = 36         # both ways   : reorder (info or instruction)
    NLP = 37         # info        : node and lap packet
    MCI = 38         # info        : multi car info
    MSX = 39         # instruction : type message
    MSL = 40         # instruction : message to local computer
    CRS = 41         # info        : car reset
    BFN = 42         # both ways   : delete buttons / receive button requests
    AXI = 43         # info        : autocross layout information
    AXO = 44         # info        : hit an autocross object
    BTN = 45         # instruction : show a button on local or remote screen
    BTC = 46         # info        : sent when a user clicks a button
    BTT = 47         # info        : sent after typing into a button
    RIP = 48         # both ways   : replay information packet
    SSH = 49         # both ways   : screenshot
    CON = 50         # info        : contact between cars (collision report)
    OBH = 51         # info        : contact car + object (collision report)
    HLV = 52         # info        : report incidents that would violate HLVC
    PLC = 53         # instruction : player cars
    AXM = 54         # both ways   : autocross multiple objects
    ACR = 55         # info        : admin command report
    HCP = 56         # instruction : car handicaps
    NCI = 57         # info        : new connection - extra info for host
    JRR = 58         # instruction : reply to a join request (allow / disallow)
    UCO = 59         # info        : report InSim checkpoint / InSim circle
    OCO = 60         # instruction : object control (currently used for lights)
    TTC = 61         # instruction : multi purpose - target to connection
    SLC = 62         # info        : connection selected a car
    CSC = 63         # info        : car state changed
    CIM = 64         # info        : connection's interface mode
    MAL = 65         # both ways   : set mods allowed
    PLH = 66         # both ways   : set player handicaps
    IPB = 67         # both ways   : set IP bans
    AIC = 68         # instruction : set AI control value
    AII = 69         # info        : info about AI car

class TINY(IntEnum):
    """
    TINY Subtypes - El cuarto byte de un paquete ISP_TINY es uno de estos.
    Referencia exacta de la documentación (0 a 30).
    
    Se utiliza en: ISP_TINY.SubT
    """
    NONE = 0         # keep alive      : see "maintaining the connection"
    VER = 1          # info request    : get version
    CLOSE = 2        # instruction     : close insim
    PING = 3         # ping request    : external progam requesting a reply
    REPLY = 4        # ping reply      : reply to a ping request
    VTC = 5          # both ways       : game vote cancel (info or request)
    SCP = 6          # info request    : send camera pos
    SST = 7          # info request    : send state info
    GTM = 8          # info request    : get time in ms (in SMALL_RTP)
    MPE = 9          # info            : multi player end
    ISM = 10         # info request    : get multiplayer info (in ISP_ISM)
    REN = 11         # info            : race end (return to race setup screen)
    CLR = 12         # info            : all players cleared from race
    NCN = 13         # info request    : get NCN for all connections
    NPL = 14         # info request    : get all players
    RES = 15         # info request    : get all results
    NLP = 16         # info request    : send an IS_NLP
    MCI = 17         # info request    : send an IS_MCI
    REO = 18         # info request    : send an IS_REO
    RST = 19         # info request    : send an IS_RST
    AXI = 20         # info request    : send an IS_AXI - AutoX Info
    AXC = 21         # info            : autocross cleared
    RIP = 22         # info request    : send an IS_RIP - Replay Information Packet
    NCI = 23         # info request    : get NCI for all guests (on host only)
    ALC = 24         # info request    : send a SMALL_ALC (allowed cars)
    AXM = 25         # info request    : send IS_AXM packets for the entire layout
    SLC = 26         # info request    : send IS_SLC packets for all connections
    MAL = 27         # info request    : send IS_MAL listing the allowed mods
    PLH = 28         # info request    : send IS_PLH listing player handicaps
    IPB = 29         # info request    : send IS_IPB listing the IP bans
    LCL = 30         # info request    : send a SMALL_LCL for local car's lights

class SMALL(IntEnum):
    """
    SMALL Subtypes - El cuarto byte de un paquete ISP_SMALL es uno de estos.
    Referencia exacta de la documentación (0 a 11).
    
    Se utiliza en: ISP_SMALL.SubT
    """
    NONE = 0         # not used
    SSP = 1          # instruction     : start sending positions
    SSG = 2          # instruction     : start sending gauges
    VTA = 3          # report          : vote action
    TMS = 4          # instruction     : time stop
    STP = 5          # instruction     : time step
    RTP = 6          # info            : race time packet (reply to TINY_GTM)
    NLI = 7          # instruction     : set node lap interval
    ALC = 8          # both ways       : set or get allowed cars (reply to TINY_ALC)
    LCS = 9          # instruction     : set local car switches (flash, horn, siren)
    LCL = 10         # both ways       : set or get local car lights (reply to TINY_LCL)
    AII = 11         # info request    : get local AI info

class TTC(IntEnum):
    """
    TTC Subtypes - El cuarto byte de un paquete ISP_TTC es uno de estos.
    Referencia exacta de la documentación (0 a 3).
    
    Se utiliza en: ISP_TTC.SubT
    """
    NONE = 0          # not used
    SEL = 1           # info request    : send IS_AXM for a layout editor selection
    SEL_START = 2     # info request    : send IS_AXM every time the selection changes
    SEL_STOP = 3      # instruction     : switch off IS_AXM requested by TTC_SEL_START

class CIM(IntEnum):
    """
    CIM - Identificadores de modo de la interfaz.
    Referencia exacta de la documentación (0 a 7).
    
    Se utiliza en: ISP_CIM.Mode
    """
    NORMAL = 0              # 0 - not in a special mode
    OPTIONS = 1             # 1
    HOST_OPTIONS = 2        # 2
    GARAGE = 3              # 3
    CAR_SELECT = 4          # 4
    TRACK_SELECT = 5        # 5
    SHIFTU = 6              # 6 - free view mode
    NUM = 7                 # 7

class NRM(IntEnum):
    """
    NRM Subtypes - Identificadores de submodo para CIM_NORMAL.
    Referencia exacta de la documentación (0 a 5).
    
    Se utiliza en: ISP_CIM.SubMode
    """
    NORMAL = 0              # 0
    WHEEL_TEMPS = 1         # 1 - F9
    WHEEL_DAMAGE = 2        # 2 - F10
    LIVE_SETTINGS = 3       # 3 - F11
    PIT_INSTRUCTIONS = 4    # 4 - F12
    NUM = 5                 # 5

class GRG(IntEnum):
    """
    GRG Subtypes - Identificadores de submodo para CIM_GARAGE.
    Referencia exacta de la documentación (0 a 9).
    
    Se utiliza en: ISP_CIM.SubMode
    """
    INFO = 0           # 0
    COLOURS = 1        # 1
    BRAKE_TC = 2       # 2
    SUSP = 3           # 3
    STEER = 4          # 4
    DRIVE = 5          # 5
    TYRES = 6          # 6
    AERO = 7           # 7
    PASS = 8           # 8
    NUM = 9            # 9

class FVM(IntEnum):
    """
    FVM Subtypes - Identificadores de submodo para CIM_SHIFTU.
    Referencia exacta de la documentación (0 a 3).
    
    Se utiliza en: ISP_CIM.SubMode
    """
    PLAIN = 0               # no buttons displayed
    BUTTONS = 1             # buttons displayed (not editing)
    EDIT = 2                # edit mode
    NUM = 3                 # 3

class MARSH:
    """
    
    """
    IS_CP   = 252  # Checkpoint de InSim
    IS_AREA = 253  # Círculo/Área de InSim
    MARSHAL = 254  # Área restringida (si entras, el juego puede penalizar)
    ROUTE   = 255  # Verificador de ruta (para evitar que los jugadores acorten)

class ISF(IntFlag):
    """
    ISF - InSim Flags.
    Configuración de la sesión InSim enviada en el paquete IS_ISI.
    Referencia exacta de la documentación (Bits 0 a 11).
    
    Se utiliza en: ISP_ISI.Flags
    """
    RES_0 = 1 << 0          # bit 0: spare
    RES_1 = 1 << 1          # bit 1: spare
    LOCAL = 1 << 2          # bit 2: guest or single player
    MSO_COLS = 1 << 3       # bit 3: keep colours in MSO text
    NLP = 1 << 4            # bit 4: receive NLP packets (posiciones simples)
    MCI = 1 << 5            # bit 5: receive MCI packets (posiciones detalladas)
    CON = 1 << 6            # bit 6: receive CON packets (colisiones coche-coche)
    OBH = 1 << 7            # bit 7: receive OBH packets (colisiones coche-objeto)
    HLV = 1 << 8            # bit 8: receive HLV packets (infracciones de salud)
    AXM_LOAD = 1 << 9       # bit 9: receive AXM when loading a layout
    AXM_EDIT = 1 << 10      # bit 10: receive AXM when changing objects
    REQ_JOIN = 1 << 11      # bit 11: process join requests

class ISS(IntFlag):
    """
    ISS - InSim State Flags.
    Describe el estado actual de la interfaz y el motor del juego.
    Referencia exacta de la documentación (Bits 0 a 15).
    
    Se utiliza en: ISP_STA.Flags, ISP_CPP.Flags
    """
    GAME = 1 << 0              # 1     - in game (or MPR)
    REPLAY = 1 << 1            # 2     - in SPR (Single Player Replay)
    PAUSED = 1 << 2            # 4     - paused
    SHIFTU = 1 << 3            # 8     - free view mode
    DIALOG = 1 << 4            # 16    - in a dialog
    SHIFTU_FOLLOW = 1 << 5     # 32    - FOLLOW view
    SHIFTU_NO_OPT = 1 << 6     # 64    - free view buttons hidden
    SHOW_2D = 1 << 7           # 128   - showing 2d display
    FRONT_END = 1 << 8         # 256   - entry screen
    MULTI = 1 << 9             # 512   - multiplayer mode
    MPSPEEDUP = 1 << 10        # 1024  - multiplayer speedup option
    WINDOWED = 1 << 11         # 2048  - LFS is running in a window
    SOUND_MUTE = 1 << 12       # 4096  - sound is switched off
    VIEW_OVERRIDE = 1 << 13    # 8192  - override user view
    VISIBLE = 1 << 14          # 16384 - InSim buttons visible
    TEXT_ENTRY = 1 << 15       # 32768 - in a text entry dialog

class ISS_SFP(IntFlag):
    """
    ISS_SFP - InSim State Flags for State Flags Pack
    Permite ajustar el estado de la interfaz y el motor del juego mediante el paquete ISP_SFP
    """
    SHIFTU_NO_OPT = ISS.SHIFTU_NO_OPT
    SHOW_2D = ISS.SHOW_2D
    MPSPEEDUP = ISS.MPSPEEDUP
    SOUND_MUTE = ISS.SOUND_MUTE

class ISS_CPP(IntFlag):
    ISS_SHIFTU = ISS.SHIFTU			        # - in free view mode
    ISS_SHIFTU_FOLLOW = ISS.SHIFTU_FOLLOW	# - FOLLOW view
    ISS_VIEW_OVERRIDE = ISS.VIEW_OVERRIDE	# - override user view
    

class OFFON(IntEnum):
    """
    Off/On - Encender/Apagar
    Permite encender o apagar
    
    Se utiliza en: ISP_SFP.OffOn
    """
    OFF = 0
    ON = 1

class SCH_FLAGS(IntFlag):
    NONE  = 0
    SHIFT = 1 << 0  # Bit 0
    CTRL  = 1 << 1  # Bit 1

class HG(IntEnum):
    GUEST = 0
    HOST = 1

class MOD_BIT(IntEnum):
    BIT32 = 0
    BIT16 = 1
    
class NCN_FLAGS(IntFlag):
    LOCAL  = 0      # Valor por defecto (bit 2 apagado)
    REMOTE = 1 << 2 # Valor 4 (bit 2 encendido)

class AD_NOAD(IntEnum):
    NO_ADMIN = 0    # El usuario no ingresó con contraseña de admin
    ADMIN = 1       # El usuario ingresó con contraseña de admin

class CAR_CONFIG(IntEnum):
    """
    Configuración específica de la carrocería (campo Config en IS_NPL).
    """
    DEFAULT   = 0  # Techo cerrado (UF1, LX4, LX6) o Carrocería base (GTR)
    ALTERNATE = 1  # Techo abierto (UF1, LX4, LX6) o Carrocería GTR alternativa

class BYF(IntEnum):
    BLUE = 1    # 1 - given blue flag (you are in the way of a leader)
    YELLOW = 2  # 2 - causing yellow flag (you are slow/stopped in danger)

class CHARS(IntEnum):
    """
    Caracteres aceptados por el campo CharB del paquete IS_SCH.
    Valores basados en códigos ASCII.
    Nota: LFS requiere mayúsculas para teclas de control estándar.
    """
    # --- Letras (Controles principales) ---
    A = ord('A')
    B = ord('B')
    C = ord('C')
    D = ord('D')
    E = ord('E')
    F = ord('F')
    G = ord('G')
    H = ord('H')  # Bocina (Horn)
    I = ord('I')  # Ignición
    J = ord('J')
    K = ord('K')
    L = ord('L')  # Luces (Lights)
    M = ord('M')
    N = ord('N')
    O = ord('O')
    P = ord('P')
    Q = ord('Q')
    R = ord('R')
    S = ord('S')  # Arranque (Starter)
    T = ord('T')
    U = ord('U')
    V = ord('V')  # Cámara (View)
    W = ord('W')
    X = ord('X')
    Y = ord('Y')
    Z = ord('Z')

    # --- Números ---
    N0 = ord('0')
    N1 = ord('1')
    N2 = ord('2')
    N3 = ord('3')
    N4 = ord('4')
    N5 = ord('5')
    N6 = ord('6')
    N7 = ord('7')
    N8 = ord('8')
    N9 = ord('9')

    # --- Teclas Especiales ---
    SPACE     = ord(' ')
    ENTER     = 13
    ESCAPE    = 27
    TAB       = 9
    COMMA     = ord(',')
    PERIOD    = ord('.')
    MINUS     = ord('-')
    EQUALS    = ord('=')
    BRACKET_L = ord('[')
    BRACKET_R = ord(']')
    SLASH     = ord('/')

class LFS(IntEnum):
    """
    LFS - Identificadores de idioma del usuario.
    Referencia exacta de la documentación (0 a 37).
    """
    ENGLISH = 0                 # 0
    DEUTSCH = 1                 # 1
    PORTUGUESE = 2              # 2
    FRENCH = 3                  # 3
    SUOMI = 4                   # 4
    NORSK = 5                   # 5
    NEDERLANDS = 6              # 6
    CATALAN = 7                 # 7
    TURKISH = 8                 # 8
    CASTELLANO = 9              # 9
    ITALIANO = 10               # 10
    DANSK = 11                  # 11
    CZECH = 12                  # 12
    RUSSIAN = 13                # 13
    ESTONIAN = 14               # 14
    SERBIAN = 15                # 15
    GREEK = 16                  # 16
    POLSKI = 17                 # 17
    CROATIAN = 18               # 18
    HUNGARIAN = 19              # 19
    BRAZILIAN = 20              # 20
    SWEDISH = 21                # 21
    SLOVAK = 22                 # 22
    GALEGO = 23                 # 23
    SLOVENSKI = 24              # 24
    BELARUSSIAN = 25            # 25
    LATVIAN = 26                # 26
    LITHUANIAN = 27             # 27
    TRADITIONAL_CHINESE = 28    # 28
    SIMPLIFIED_CHINESE = 29     # 29
    JAPANESE = 30               # 30
    KOREAN = 31                 # 31
    BULGARIAN = 32              # 32
    LATINO = 33                 # 33
    UKRAINIAN = 34              # 34
    INDONESIAN = 35             # 35
    ROMANIAN = 36               # 36
    NUM_LANG = 37               # 37

class LEAVR(IntEnum):
    """
    LEAVR - Motivos por los que una conexión abandona el servidor.
    Referencia exacta de la documentación (0 a 10).
    """
    DISCO = 0           # 0 - none
    TIMEOUT = 1         # 1 - timed out
    LOSTCONN = 2        # 2 - lost connection
    KICKED = 3          # 3 - kicked
    BANNED = 4          # 4 - banned
    SECURITY = 5        # 5 - security
    CPW = 6             # 6 - cheat protection wrong
    OOS = 7             # 7 - out of sync with host
    JOOS = 8            # 8 - join OOS (initial sync failed)
    HACK = 9            # 9 - invalid packet
    NUM = 10            # 10

class PTYPE(IntFlag):
    """
    PType - Player Type (en el paquete IS_NPL).
    Define el género, si es IA y si es un jugador remoto.
    """
    FEMALE = 1 << 0  # Bit 0 (1): Si está activo es mujer, si no, hombre.
    AI     = 1 << 1  # Bit 1 (2): ¡ESTE ES EL QUE USAS! 1 para IA, 0 para Humano.
    REMOTE = 1 << 2  # Bit 2 (4): 1 para Remoto, 0 para Local.

class SETF(IntFlag):
    """
    SETF - Setup Flags.
    Indican la configuración de ayudas y ajustes del coche en el paquete NPL.
    Referencia exacta de la documentación (Bits 0 a 2).
    """
    SYMM_WHEELS = 1 << 0    # 1 - Ruedas simétricas (ajuste de setup)
    TC_ENABLE = 1 << 1      # 2 - Control de tracción activado
    ABS_ENABLE = 1 << 2     # 4 - ABS activado

class TYRE(IntEnum):
    """
    TYRE - Compuestos de neumáticos.
    El orden en los paquetes suele ser: trasera izq, trasera der, delantera izq, delantera der.
    Referencia exacta de la documentación (0 a 8).
    """
    R1 = 0              # 0 - Racing Slick (Super Soft)
    R2 = 1              # 1 - Racing Slick (Soft)
    R3 = 2              # 2 - Racing Slick (Medium)
    R4 = 3              # 3 - Racing Slick (Hard)
    ROAD_SUPER = 4      # 4 - Road Super
    ROAD_NORMAL = 5     # 5 - Road Normal
    HYBRID = 6          # 6 - Hybrid
    KNOBBLY = 7         # 7 - Knobbly (Off-road)
    NUM = 8             # 8

class PASS(IntFlag):
    """
    PASS - Passengers. NPL Packet Flags.
    Identifica la ocupación y género de los pasajeros en el vehículo.
    Referencia exacta de la documentación (Bits 0 a 7).
    """
    FRONT_MALE = 1 << 0         # Bit 0: Frontal Masculino
    FRONT_FEMALE = 1 << 1       # Bit 1: Frontal Femenino
    REAR_LEFT_MALE = 1 << 2     # Bit 2: Trasero Izquierdo Masculino
    REAR_LEFT_FEMALE = 1 << 3   # Bit 3: Trasero Izquierdo Femenino
    REAR_MIDDLE_MALE = 1 << 4   # Bit 4: Trasero Central Masculino
    REAR_MIDDLE_FEMALE = 1 << 5 # Bit 5: Trasero Central Femenino
    REAR_RIGHT_MALE = 1 << 6    # Bit 6: Trasero Derecho Masculino
    REAR_RIGHT_FEMALE = 1 << 7  # Bit 7: Trasero Derecho Femenino

class HOSTF(IntFlag):
    """
    HOSTF - Host Flags.
    Define las reglas y opciones activas en el servidor/host.
    Referencia exacta de la documentación (Bits 0 a 9).
    """
    CAN_VOTE = 1 << 0       # 1   - Los jugadores pueden votar (kick/ban/etc)
    CAN_SELECT = 1 << 1     # 2   - Los jugadores pueden seleccionar pista/coche
    MID_RACE = 1 << 5       # 32  - Permitido unirse a mitad de carrera
    MUST_PIT = 1 << 6       # 64  - Parada en boxes obligatoria
    CAN_RESET = 1 << 7      # 128 - Permitido resetear el coche
    FCV = 1 << 8            # 256 - Force Cockpit View (Vista forzada de cabina)
    CRUISE = 1 << 9         # 512 - Modo Cruise (sin sentido de carrera, tráfico libre)

class PENALTY(IntEnum):
    """
    PENALTY - Valores de penalización.
    'VALID' significa que la penalización ya puede ser cumplida/limpiada.
    Referencia exacta de la documentación (0 a 7).
    """
    NONE = 0            # 0
    DT = 1              # 1 - Drive-through
    DT_VALID = 2        # 2
    SG = 3              # 3 - Stop-go
    SG_VALID = 4        # 4
    S30 = 5             # 5 - 30 second time penalty
    S45 = 6             # 6 - 45 second time penalty
    NUM = 7             # 7

class PENR(IntEnum):
    """
    PENR - Motivos por los que se ha recibido una penalización.
    Referencia exacta de la documentación (0 a 7).
    """
    UNKNOWN = 0         # 0 - unknown or cleared penalty
    ADMIN = 1           # 1 - penalty given by admin
    WRONG_WAY = 2       # 2 - wrong way driving
    FALSE_START = 3     # 3 - starting before green light
    SPEEDING = 4        # 4 - speeding in pit lane
    STOP_SHORT = 5      # 5 - stop-go pit stop too short
    STOP_LATE = 6       # 6 - compulsory stop is too late
    NUM = 7             # 7

class PITLANE(IntEnum):
    """
    PITLANE - Hechos y eventos del Pit Lane.
    Referencia exacta de la documentación (0 a 5).
    """
    EXIT = 0            # 0 - left pit lane
    ENTER = 1           # 1 - entered pit lane
    NO_PURPOSE = 2      # 2 - entered for no purpose
    DT = 3              # 3 - entered for drive-through
    SG = 4              # 4 - entered for stop-go
    NUM = 5             # 5

class PSE(IntFlag):
    """
    PSE - Pit Work Flags. 
    Representan los trabajos realizados en una parada en boxes.
    Referencia exacta de la documentación (Bits 0 a 17).
    """
    NOTHING = 1 << 0        # bit 0 (1)
    STOP = 1 << 1           # bit 1 (2)
    FR_DAM = 1 << 2         # bit 2 (4)
    FR_WHL = 1 << 3         # etc...
    LE_FR_DAM = 1 << 4
    LE_FR_WHL = 1 << 5
    RI_FR_DAM = 1 << 6
    RI_FR_WHL = 1 << 7
    RE_DAM = 1 << 8
    RE_WHL = 1 << 9
    LE_RE_DAM = 1 << 10
    LE_RE_WHL = 1 << 11
    RI_RE_DAM = 1 << 12
    RI_RE_WHL = 1 << 13
    BODY_MINOR = 1 << 14
    BODY_MAJOR = 1 << 15
    SETUP = 1 << 16
    REFUEL = 1 << 17
    NUM = 18                # 18

class CCI(IntFlag):
    """
    CCI - CompCar Info.
    Banderas de estado para cada coche individual.
    Referencia exacta de la documentación (Bits 0 a 7).
    """
    BLUE = 1 << 0           # 1   - Blue flag: car is in the way of a leader
    YELLOW = 1 << 1         # 2   - Yellow flag: car is slow/stopped in danger
    OOB = 1 << 2            # 4   - Out of Bounds: car is outside the track path
    
    LAG = 1 << 5            # 32  - Lagging: missing or delayed position packets
    
    FIRST = 1 << 6          # 64  - First compcar in this set of MCI packets
    LAST = 1 << 7           # 128 - Last compcar in this set of MCI packets

class MSO(IntEnum):
    """
    MSO Subtypes - El cuarto byte de un paquete ISP_MSO es uno de estos.
    Referencia exacta de la documentación (0 a 4).
    """
    SYSTEM = 0        # 0 - system message
    USER = 1          # 1 - normal visible user message
    PREFIX = 2        # 2 - hidden message starting with special prefix (see ISI)
    O = 3             # 3 - hidden message typed on local pc with /o command
    NUM = 4           # 4 - (número de tipos definidos, no se usa como tipo)

class SND(IntEnum):
    """
    SND - Sonidos de mensaje para el byte 'Sound'.
    Referencia exacta de la documentación (0 a 5).
    """
    SILENT = 0        # 0
    MESSAGE = 1       # 1
    SYSMESSAGE = 2    # 2
    INVALIDKEY = 3    # 3
    ERROR = 4         # 4
    NUM = 5           # 5

class CS(IntEnum):
    """
    CS - Control System.
    Identificadores para controlar físicamente el vehículo mediante paquetes IS_JRR.
    """
    # Controles Analógicos (0 a 65535)
    STEER = 0          # 32768 es el centro
    THROTTLE = 1       # Acelerador
    BRAKE = 2          # Freno
    CLUTCH = 11        # Embrague
    HANDBRAKE = 12     # Freno de mano

    # Controles de Acción (Hold / Toggle)
    CHUP = 3           # Subir marcha (Hold)
    CHDN = 4           # Bajar marcha (Hold)
    IGNITION = 5       # Contacto/Arranque (Toggle)
    EXTRALIGHT = 6     # Luces extra (Toggle)
    HEADLIGHTS = 7     # Luces: 1:off / 2:side / 3:low / 4:high
    SIREN = 8          # Sirena (Hold) - 1:rápida / 2:lenta
    HORN = 9           # Claxon (Hold) - 1 a 5
    FLASH = 10         # Ráfagas (Hold) - 1:on
    INDICATORS = 13    # Intermitentes: 1:off / 2:izq / 3:der / 4:warning
    GEAR = 14          # Marcha directa (shifter). 255 para secuencial.
    LOOK = 15          # Mirar: 0:nada / 4:izq / 6:der
    PITSPEED = 16      # Limitador de pits (Toggle)
    TCDISABLE = 17     # Desactivar TC (Toggle)
    FOGREAR = 18       # Antiniebla trasera (Toggle)
    FOGFRONT = 19      # Antiniebla delantera (Toggle)

    # Valores Especiales / Comandos de Sistema
    SEND_AI_INFO = 240    # Solicitar un paquete IS_AII
    REPEAT_AI_INFO = 241  # Configurar envío regular de IS_AII
    SET_HELP_FLAGS = 253  # Configurar ayudas (PIF_AUTOGEARS, etc.)
    RESET_INPUTS = 254    # Resetear todos los controles a su estado neutral
    STOP_CONTROL = 255    # El piloto automático detendrá el coche

class HEADLIGHTS(IntEnum):
    OFF      = 1
    SIDE     = 2  # Posición
    LOW      = 3  # Cortas
    HIGH     = 4  # Largas

class SIREN(IntEnum):
    OFF      = 0
    FAST     = 1
    SLOW     = 2

class LOOK(IntEnum):
    CENTRE   = 0
    LEFT     = 4
    LEFT_MAX = 5
    RIGHT    = 6
    RIGHT_MAX = 7

class INDICATORS(IntEnum):
    OFF      = 1
    LEFT     = 2
    RIGHT    = 3
    HAZARD   = 4  # Emergencia / Warning

class MIN_MID_MAX(IntEnum):
    MIN     = 0
    MID     = 32768
    MAX     = 65535

class STEER(IntEnum):
    HARD_LEFT    = 1
    CENTRE  = 32768
    HARD_RIGHT   = 65535

class TOGGLE(IntEnum):
    T=1
    OFF=2
    ON=3

class GEAR(IntEnum):
    REVERSE = 0
    NEUTRAL = 1
    FIRST = 2
    SECOND = 3
    THIRD = 4
    FOURTH = 5
    FIFTH = 6
    SIXTH = 7
    SEVENTH = 8
    EIGHTH = 9

class PIF(IntFlag):
    """
    PIF - Player Info Flags.
    Describe los ajustes de control y estado del jugador.
    Referencia exacta de la documentación (Bits 0 a 13).
    """
    LEFTSIDE = 1 << 0          # 1     - Driver on left side
    RESERVED_2 = 1 << 1        # 2     - (reserved)
    RESERVED_4 = 1 << 2        # 4     - (reserved)
    AUTOGEARS = 1 << 3         # 8     - Automatic transmission
    SHIFTER = 1 << 4           # 16    - Using a shifter device
    FLEXIBLE_STEER = 1 << 5    # 32    - Flexible steering enabled
    HELP_B = 1 << 6            # 64    - Braking help enabled
    AXIS_CLUTCH = 1 << 7       # 128   - Clutch is on an axis (not a button)
    INPITS = 1 << 8            # 256   - Player is currently in pits
    AUTOCLUTCH = 1 << 9        # 512   - Automatic clutch enabled
    MOUSE = 1 << 10           # 1024  - Steering with mouse
    KB_NO_HELP = 1 << 11       # 2048  - Keyboard (no help)
    KB_STABILISED = 1 << 12    # 4096  - Keyboard (stabilised)
    CUSTOM_VIEW = 1 << 13      # 8192  - Using a custom view

class AI_HELP:
    AUTOGEARS=PIF.AUTOGEARS
    HELP_B=PIF.HELP_B
    AUTOCLUTCH=PIF.AUTOCLUTCH

class CSVAL:
    """
    Se usa en: AIInputVal.Value
    """
    MIN_MID_MAX=MIN_MID_MAX
    HEADLIGHTS=HEADLIGHTS
    SIREN=SIREN
    LOOK=LOOK
    INDICATORS=INDICATORS
    TOGGLE=TOGGLE
    GEAR=GEAR
    AI_HELP=AI_HELP
    STEER=STEER

class CARS(IntFlag):
    """
    Lista de coches de Live for Speed y sus valores de bit correspondientes.
    Utilizado habitualmente en IS_ISM (InSim Multi) o configuraciones de servidor.
    """
    NONE               = 0
    XF_GTI             = 1          # XFG
    XR_GT              = 2          # XRT
    XR_GT_TURBO        = 4          # XRG
    RB4_GT             = 8          # RB4
    FXO_TURBO          = 0x10       # FXO
    LX4                = 0x20       # LX4
    LX6                = 0x40       # LX6
    MRT5               = 0x80       # MRT
    UF_1000            = 0x100      # UF1
    RACEABOUT          = 0x200      # RAC
    FZ50               = 0x400      # FZ5
    FORMULA_XR         = 0x800      # FOX
    XF_GTR             = 0x1000     # XFR
    UF_GTR             = 0x2000     # UFR
    FORMULA_V8         = 0x4000     # FOV
    FXO_GTR            = 0x8000     # FXR
    XR_GTR             = 0x10000    # XRR
    FZ50_GTR           = 0x20000    # FZR
    BMW_SAUBER_F1_06   = 0x40000    # BF1
    FORMULA_BMW_FB02   = 0x80000    # FBM

class AI_FLAGS(IntFlag):
    """
    AI_FLAGS - Estado de la IA y el motor.
    Indican si el motor está en marcha y la posición actual de las levas de cambio.
    """
    IGNITION = 1 << 0  # 1 - Detecta si el motor está encendido
    # Bit 1 (2) está reservado o no documentado aquí
    CHUP = 1 << 2      # 4 - La leva de subir marcha está accionada
    CHDN = 1 << 3      # 8 - La leva de bajar marcha está accionada

class LCL(IntFlag):
    """
    LCL - Local Car Lights.
    Banderas para el control detallado de luces en el paquete SMALL_LCL.
    Referencia exacta de la documentación (Bits 0 a 6).
    """
    SET_SIGNALS = 1 << 0      # 1    - bit 0
    SPARE_2 = 1 << 1          # 2    - bit 1 (do not set)
    SET_LIGHTS = 1 << 2       # 4    - bit 2
    SPARE_8 = 1 << 3          # 8    - bit 3 (do not set)
    SET_FOG_REAR = 1 << 4     # 16   - bit 4 (0x10)
    SET_FOG_FRONT = 1 << 5    # 32   - bit 5 (0x20)
    SET_EXTRA = 1 << 6        # 64   - bit 6 (0x40)

class PMO(IntEnum):
    """
    PMO Action - El byte de acción en un paquete IS_PMO.
    Controla la carga, adición y eliminación de objetos del layout.
    Referencia exacta de la documentación (0 a 9).
    """
    LOADING_FILE = 0    # 0 - sent by the layout loading system only
    ADD_OBJECTS = 1     # 1 - adding objects (from InSim or editor)
    DEL_OBJECTS = 2     # 2 - delete objects (from InSim or editor)
    CLEAR_ALL = 3       # 3 - clear all objects (NumO must be zero)
    TINY_AXM = 4        # 4 - a reply to a TINY_AXM request
    TTC_SEL = 5         # 5 - a reply to a TTC_SEL request
    SELECTION = 6       # 6 - set a connection's layout editor selection
    POSITION = 7        # 7 - user pressed O without anything selected
    GET_Z = 8           # 8 - request Z values / reply with Z values
    NUM = 9             # 9

class IS_OBJECT_TYPE(IntEnum):
    """
    Identificadores especiales de objetos InSim.
    """
    INSIM_CHECKPOINT = 252  # Objeto tipo Checkpoint
    INSIM_CIRCLE = 253      # Objeto tipo Círculo

class UCO(IntEnum):
    """
    UCO Action - El byte de acción en un paquete ISP_UCO.
    Referencia exacta de la documentación (0 a 3).
    """
    CIRCLE_ENTER = 0    # entered a circle
    CIRCLE_LEAVE = 1    # left a circle
    CP_FWD = 2          # crossed cp in forward direction
    CP_REV = 3          # crossed cp in reverse direction

class CPK_INDEX(IntEnum):
    """
    CPK_INDEX - Identificación de Checkpoints InSim (Index 252).
    Extraído de los bits 0 y 1 del byte 'Flags'.
    Nota: El índice es informativo; para muchos CP usar coordenadas X, Y.
    """
    FINISH = 0          # 00 - Línea de meta
    CHECKPOINT_1 = 1    # 01 - 1er punto de control
    CHECKPOINT_2 = 2    # 10 - 2do punto de control
    CHECKPOINT_3 = 3    # 11 - 3er punto de control

class OCO(IntEnum):
    """
    OCO Action - El byte de acción en un paquete IS_OCO.
    Se utiliza principalmente para manipular luces y semáforos.
    Referencia exacta de la documentación (0 a 7).
    """
    ZERO = 0            # 0 - reserved
    RESERVED_1 = 1      # 1 - reserved
    RESERVED_2 = 2      # 2 - reserved
    RESERVED_3 = 3      # 3 - reserved
    LIGHTS_RESET = 4    # 4 - give up control of all lights
    LIGHTS_SET = 5      # 5 - use Data byte to set the bulbs
    LIGHTS_UNSET = 6    # 6 - give up control of the specified lights
    NUM = 7             # 7

class IS_RECT:
    """
    IS_RECT - Área recomendada para botones de InSim.
    Define los límites de la zona 'limpia' donde LFS no colocará sus propios botones.
    El sistema de coordenadas de LFS va de 0 a 200 en ambos ejes.
    """
    X_MIN = 0
    X_MAX = 110
    
    Y_MIN = 30
    Y_MAX = 170

class INST(IntFlag):
    """
    INST - InSim Style Flags.
    """
    ALWAYS_ON = 128    # El botón es visible en todas las pantallas (Garage, Opciones, etc.)
    DEFAULT = 0

class ISB_STYLE(IntFlag):
    """
    ISB - Button Style Flags.
    Controlan el aspecto y el comportamiento básico del clic.
    """
    # Colores (Bits 0-2): Ver abajo ISB_COLOUR
    C1 = 1
    C2 = 2
    C4 = 4
    
    CLICK = 8          # El botón envía un paquete IS_BTC al ser pulsado
    LIGHT = 16         # Apariencia clara
    DARK = 32          # Apariencia oscura
    LEFT = 64          # Alinear texto a la izquierda
    RIGHT = 128        # Alinear texto a la derecha (centro es por defecto)
    
    """
    Colores estándar de la interfaz de LFS.
    Se obtienen combinando los bits C1, C2 y C4.
    """
    LIGHT_GREY = 0     # Gris claro
    TITLE = 1          # Color de título (Amarillo)
    UNSELECTED = 2     # Texto no seleccionado (Negro)
    SELECTED = 3       # Texto seleccionado (Blanco)
    OK = 4             # Confirmación (Verde)
    CANCEL = 5         # Cancelación (Rojo)
    TEXT_STRING = 6    # Cadena de texto (Azul pálido)
    UNAVAILABLE = 7    # No disponible (Gris)

class BFN(IntEnum):
    """
    BFN - Funciones de los botones.
    Define acciones para borrar botones o informa de peticiones del usuario.
    Referencia exacta de la documentación (0 a 3).
    
    Se utiliza en: ISP_BFN.SubT
    """
    DEL_BTN = 0         # 0 - instruction : delete one button or range of buttons
    CLEAR = 1           # 1 - instruction : clear all buttons made by this instance
    USER_CLEAR = 2      # 2 - info        : user cleared this instance's buttons
    REQUEST = 3         # 3 - user request: SHIFT+B or SHIFT+I - request for buttons

class TYPEIN_FLAGS:
    NONE = 0
    MAX_CHARS_MASK = 0x7F # Los primeros 7 bits (0-127)
    INIT_WITH_TEXT = 128  # Bit 7 para inicializar con el texto actual

class ISB_CLICK(IntFlag):
    """
    ISB_CLICK - CFlags (Click Flags).
    Indican qué botón del ratón y qué modificadores de teclado se usaron al pulsar un botón.
    Recibido en el paquete IS_BTC.
    """
    LMB = 1 << 0      # 1 - Clic con el botón izquierdo (Left Mouse Button)
    RMB = 1 << 1      # 2 - Clic con el botón derecho (Right Mouse Button)
    CTRL = 1 << 2     # 4 - Ctrl + Clic
    SHIFT = 1 << 3    # 8 - Shift + Clic

class OG(IntFlag):
    """
    OG - OutGauge Flags.
    Banderas de estado para la telemetría del tablero (OutGauge).
    Referencia exacta de la documentación (Bits 0 a 15).
    """
    SHIFT = 1 << 0          # 1     - Tecla Shift pulsada (o indicador de cambio)
    CTRL = 1 << 1           # 2     - Tecla Control pulsada
    
    TURBO = 1 << 13         # 8192  - Mostrar el medidor de Turbo
    KM = 1 << 14            # 16384 - Si está activo: KM/H. Si no: MPH.
    BAR = 1 << 15           # 32768 - Si está activo: BAR. Si no: PSI.

class DL(IntFlag):
    """
    DL - Dash Lights.
    Representan los testigos y luces del salpicadero del coche.
    Referencia exacta de la documentación (Bits 0 a 17+).
    
    Se utilza en: OutGaugePack.DashLights, OutGaugePack.ShowLights, ISP_AII.ShowLights
    """
    SHIFT = 1 << 0          # bit 0 - shift light
    FULLBEAM = 1 << 1       # bit 1 - full beam
    HANDBRAKE = 1 << 2      # bit 2 - handbrake
    PITSPEED = 1 << 3       # bit 3 - pit speed limiter
    TC = 1 << 4             # bit 4 - TC active or switched off
    SIGNAL_L = 1 << 5       # bit 5 - left turn signal
    SIGNAL_R = 1 << 6       # bit 6 - right turn signal
    SIGNAL_ANY = 1 << 7      # bit 7 - shared turn signal
    OILWARN = 1 << 8        # bit 8 - oil pressure warning
    BATTERY = 1 << 9        # bit 9 - battery warning
    ABS = 1 << 10           # bit 10 - ABS active or switched off
    ENGINE = 1 << 11        # bit 11 - engine damage
    FOG_REAR = 1 << 12      # bit 12
    FOG_FRONT = 1 << 13     # bit 13
    DIPPED = 1 << 14        # bit 14 - dipped headlight symbol
    FUELWARN = 1 << 15      # bit 15 - low fuel warning light
    SIDELIGHTS = 1 << 16    # bit 16 - sidelights symbol
    NEUTRAL = 1 << 17       # bit 17 - neutral light
    _18 = 1 << 18
    _19 = 1 << 19
    _20 = 1 << 20
    _21 = 1 << 21
    _22 = 1 << 22
    _23 = 1 << 23
    NUM = 24                # 24

class OSO(IntFlag):
    """
    OSO - OutSim Options.
    Define qué bloques de datos se incluyen en el paquete de telemetría OutSim.
    Configurable en el archivo cfg.txt de LFS (OutSim Opts).
    """
    NONE        = 0
    HEADER      = 1 << 0    # 1   - Cabecera de verificación
    ID          = 1 << 1    # 2   - ID del paquete
    TIME        = 1 << 2    # 4   - Tiempo de simulación
    MAIN        = 1 << 3    # 8   - Posición, velocidad, aceleración y orientación
    INPUTS      = 1 << 4    # 16  - Entradas (acelerador, freno, dirección, etc.)
    DRIVE       = 1 << 5    # 32  - Datos de transmisión (marcha, RPM, par motor)
    DISTANCE    = 1 << 6    # 64  - Distancia recorrida y de pista
    WHEELS      = 1 << 7    # 128 - Suspensión, carga, velocidad y ángulo de las 4 ruedas
    EXTRA_1     = 1 << 8    # 256 - Datos adicionales (orientación del cuerpo, etc.)
    
    ALL_NOID    = HEADER|TIME|MAIN|INPUTS|DRIVE|DISTANCE|WHEELS|EXTRA_1
    ALL         = ALL_NOID|ID

class VOTE(IntEnum):
    """
    VOTE - Acciones de votación.
    Referencia exacta de la documentación (0 a 4).
    """
    NONE = 0          # 0 - no vote
    END = 1           # 1 - end race
    RESTART = 2       # 2 - restart
    QUALIFY = 3       # 3 - qualify
    NUM = 4           # 4
    
class RST_TIMING(IntFlag):
    """
    RST Timing - Desglose del byte 'Timing' en el paquete IS_RST.
    """
    # Máscara para obtener el número de checkpoints (Bits 0 y 1)
    NUM_CP_MASK = 0x03
    
    # Tipos de cronometraje (Bits 6 y 7)
    STANDARD    = 0x40  # 64  - Cronometraje estándar LFS
    CUSTOM      = 0x80  # 128 - Checkpoints personalizados
    NO_TIMING   = 0xC0  # 192 - Configuración abierta / Sin vueltas

class VIEW(IntEnum):
    """
    VIEW - Identificadores de vista de cámara.
    Referencia exacta de la documentación (0 a 5).
    """
    FOLLOW = 0      # 0 - arcade
    HELI = 1        # 1 - helicopter
    CAM = 2         # 2 - tv camera
    DRIVER = 3      # 3 - cockpit
    CUSTOM = 4      # 4 - custom
    MAX = 5         # 5
    ANOTHER = 255   # 255 - viewing another car

class JRR(IntEnum):
    """
    JRR - Acciones de respuesta a una solicitud de entrada (Join Request).
    Determina qué sucede con el coche cuando se procesa la solicitud.
    Referencia exacta de la documentación (0 a 7).
    """
    REJECT = 0             # 0 - Denegar entrada
    SPAWN = 1              # 1 - Aparecer en pista
    _2 = 2                 # 2 - (reservado)
    _3 = 3                 # 3 - (reservado)
    RESET = 4              # 4 - Reset de coche (reparado)
    RESET_NO_REPAIR = 5    # 5 - Reset de coche (sin reparar)
    _6 = 6                 # 6 - (reservado)
    _7 = 7                 # 7 - (reservado)

class CSC(IntEnum):
    """
    CSC Action - El byte de acción en un paquete IS_CSC.
    Identifica si el coche se ha detenido o ha reanudado la marcha.
    Referencia exacta de la documentación (0 a 1).
    """
    STOP = 0            # 0 - El coche se ha detenido
    START = 1           # 1 - El coche ha comenzado a moverse

class RIP(IntEnum):
    """
    RIP Error Codes - Códigos de respuesta para instrucciones de repetición.
    Indican si una petición de carga o salto en el tiempo de un replay fue exitosa.
    Referencia exacta de la documentación (0 a 11).
    """
    OK = 0              # 0 - OK: completed instruction
    ALREADY = 1         # 1 - OK: already at the destination
    DEDICATED = 2       # 2 - can't run a replay - dedicated host
    WRONG_MODE = 3      # 3 - can't start a replay - not in a suitable mode
    NOT_REPLAY = 4      # 4 - RName is zero but no replay is currently loaded
    CORRUPTED = 5       # 5 - IS_RIP corrupted (e.g. RName does not end with zero)
    NOT_FOUND = 6       # 6 - the replay file was not found
    UNLOADABLE = 7      # 7 - obsolete / future / corrupted
    DEST_OOB = 8        # 8 - destination is beyond replay length
    UNKNOWN = 9         # 9 - unknown error found starting replay
    USER = 10           # 10 - replay search was terminated by user
    OOS = 11            # 11 - can't reach destination - SPR is out of sync

class SSH(IntEnum):
    """
    SSH Error Codes - Códigos de respuesta para instrucciones de captura de pantalla.
    Referencia exacta de la documentación (0 a 3).
    """
    OK = 0              # 0 - OK: completed instruction
    DEDICATED = 1       # 1 - can't save a screenshot - dedicated host
    CORRUPTED = 2       # 2 - IS_SSH corrupted (e.g. Name does not end with zero)
    NO_SAVE = 3         # 3 - could not save the screenshot

class LCS(IntFlag):
    """
    LCS - Lights and Control Signals.
    Banderas para controlar luces, claxon y sirena.
    Referencia exacta de la documentación (Bits 0 a 4).
    """
    SET_SIGNALS = 1 << 0      # 1    - bit 0 (intermitentes)
    SET_FLASH = 1 << 1        # 2    - bit 1 (ráfagas)
    SET_HEADLIGHTS = 1 << 2   # 4    - bit 2 (luces de cruce)
    SET_HORN = 1 << 3         # 8    - bit 3 (claxon)
    SET_SIREN = 1 << 4        # 16   - bit 4 (0x10 - sirena)

class CONF(IntFlag):
    """
    CONF - Confirmation Flags.
    Banderas de confirmación para penalizaciones y estados de carrera.
    Incluye máscaras para descalificación y penalizaciones de tiempo.
    
    Se utiliza en: ISP_FIN.Confirm, ISP_RES.Confirm
    """
    MENTIONED = 1 << 0       # 1
    CONFIRMED = 1 << 1       # 2
    PENALTY_DT = 1 << 2      # 4  - Drive-through
    PENALTY_SG = 1 << 3      # 8  - Stop-go
    PENALTY_30 = 1 << 4      # 16 - 30s
    PENALTY_45 = 1 << 5      # 32 - 45s
    DID_NOT_PIT = 1 << 6     # 64 - No paró en boxes

    # Máscaras de conveniencia (Equivalentes a los #define)
    DISQ = PENALTY_DT | PENALTY_SG | DID_NOT_PIT
    TIME = PENALTY_30 | PENALTY_45

class OBH(IntFlag):
    """
    OBH Flags - Información sobre el objeto colisionado.
    Se utiliza en el paquete IS_OBH para describir el estado del objeto.
    Referencia exacta de la documentación (Bits 0 a 3).
    """
    LAYOUT = 1 << 0      # 1 - Un objeto añadido (parte de un layout AXM)
    CAN_MOVE = 1 << 1    # 2 - Un objeto móvil (conos, barreras de plástico, etc.)
    WAS_MOVING = 1 << 2  # 4 - El objeto ya se estaba moviendo antes del impacto
    ON_SPOT = 1 << 3     # 8 - El objeto estaba en su posición original

class OCO_DATA_MAIN(IntFlag):
    RED1 = 1 << 0
    RED2 = 1 << 1
    RED3 = 1 << 2
    GREEN = 1 << 3

class OCO_DATA_AXO(IntFlag):
    RED = 1 << 0
    AMBER = 1 << 1
    GREEN = 1 << 3

class HLVC(IntEnum):
    """
    HLVC - Health, Limits, Violations, Collisions.
    Tipo de infracción reportada en ISP_HLV.
    """
    GROUND = 0       # 0 - hit the ground
    WALL = 1         # 1 - hit a wall
    SPEEDING = 4     # 4 - speeding in pit lane
    OUT_OF_BOUNDS = 5  # 5 - out of bounds

class AXO_INDEX(IntEnum):
    """
    Índices de objetos de Autocross (AXO) y de sistema (MARSH)
    utilizados en paquetes como IS_OBH o la estructura ObjectInfo.
    """
    NULL          = 0    # Objeto desconocido o inexistente
    
    # --- CONOS Y POSTES ---
    CONE_RED      = 1
    CONE_BLUE     = 2
    CONE_YELLOW   = 3
    CONE_WHITE    = 4
    CONE_GREEN    = 5
    CONE_ORANGE   = 6
    POST_RED      = 7
    POST_BLUE     = 8
    POST_YELLOW   = 9
    POST_WHITE    = 10
    POST_GREEN    = 11
    POST_ORANGE   = 12
    
    # --- BARRERAS Y MUROS ---
    TYRE_STACK    = 21   # Pila de neumáticos
    TYRE_WALL     = 22   # Muro de neumáticos
    CONCRETE_WALL = 23   # Bloque de hormigón
    BRAMA_WALL    = 24   # Valla publicitaria/muro
    
    # --- SEÑALES ---
    ARROW_LEFT    = 29
    ARROW_RIGHT   = 30
    KEEP_LEFT     = 31
    KEEP_RIGHT    = 32
    
    # --- OBJETOS DINÁMICOS / ESPECIALES ---
    START_LIGHTS1 = 149  # Semáforo de salida tipo 1
    START_LIGHTS2 = 150  # Semáforo de salida tipo 2
    START_LIGHTS3 = 151  # Semáforo de salida tipo 3
    
    # --- SISTEMAS DE MARSHAL / INSIM (Zonas lógicas) ---
    # Estos valores aparecen en el campo Index cuando se golpea un sensor
    MARSH_IS_CP    = 252  # InSim Checkpoint (Punto de control)
    MARSH_IS_AREA  = 253  # InSim Circle (Área circular)
    MARSH_MARSHAL  = 254  # Zona restringida / Marshal
    MARSH_ROUTE    = 255  # Verificador de ruta (Route checker)

class PMOF(IntFlag):
    """
    PMO - Pre-fabricated Object Flags.
    Controlan el flujo de carga, modificación y validación de objetos de layout.
    """
    FILE_END = 1 << 0        # 1  - Fin de archivo de layout (último paquete AXM)
    MOVE_MODIFY = 1 << 1     # 2  - Indica que un objeto está siendo movido/editado
    SELECTION_REAL = 1 << 2  # 4  - Selección real de objetos (tipo CTRL+clic)
    AVOID_CHECK = 1 << 3     # 8  - Salta la validación de "posición inválida"

class LICENSE(IntEnum):
    DEMO = 0
    S1 = 1
    S2 = 2
    S3 = 3

class RESULT(IntEnum):
    PROCESSED = 1
    REJECTED = 2
    UNKNOWN_COMMAND = 3

class RIPOPT(IntFlag):
    """
    RIPOPT - Replay Options.
    Opciones para la reproducción y análisis de archivos de repetición (MPR/SPR).
    """
    LOOP = 1 << 0           # 1 - La repetición volverá a empezar al terminar
    SKINS = 1 << 1          # 2 - Descargar automáticamente skins que falten
    FULL_PHYS = 1 << 2      # 4 - Usar físicas completas al buscar en un MPR

class INST(IntFlag):
    """
    INST - InSim Style Flags.
    """
    DEFAULT = 0        # Visible solo en pista
    ALWAYS_ON = 128    # El botón es visible en todas las pantallas (Garage, Opciones, etc.)

class SMPR(IntEnum):
    SPR = 0     # Single Player Replay
    MPR = 1     # Multi Player Replay

class DLF(IntFlag):
    """
    DLF - Damage Loss Flags.
    Estado de daños críticos del vehículo.
    """
    ENGINE_SEVERE = 0x10000000  # Motor severamente dañado (pérdida total de potencia)

class PHC(IntFlag):
    """
    PHC - Player Handicap Flags.
    Se utiliza en: Paquete IS_PLH (Atributo: Flags dentro de la struct PlayerHCap).
    Define qué handicaps se aplicarán al jugador y si se notificará en el chat.
    
    Se utiliza en: PlayerHCap.Flags
    """
    MASS    = 1 << 0    # 1   - Aplicar masa adicional (H_Mass)
    TRES    = 1 << 1    # 2   - Aplicar restricción de admisión (H_TRes)
    SILENT  = 1 << 7    # 128 - El cambio se aplica de forma silenciosa (sin mensaje en el chat)

class RAINPR(IntEnum):
    """
    RAINPR - Race In Progres value
    
    Se utiliza en: ISP_STA.RaceInProg
    """
    NO_RACE = 0
    RACE = 1
    QUALIFYING = 2
    
class SERVER(IntEnum):
    """
    SERVER - Estado de la conexión con el Master Server.
    Se utiliza en: Paquete IS_STA (Atributo: ServerStatus).
    Nota: FAILURE correstponde a: ServerStatus > 1
    """
    UNKNOWN = 0
    SUCCESS = 1
    FAILURE = 2  # Realmente cualquier valor > 1 es fallo

class WEATHER(IntEnum):
    """
    WEATHER - Condición meteorológica visual.
    Se utiliza en: ISP_STA.Weather, ISP_RST.Weather
    """
    CLEAR = 0       # 0 - clear sky
    CLOUDY = 1      # 1 - light cloud / overcast
    RAIN = 2        # 2 - rain

class WIND(IntEnum):
    """
    WIND - Estado del viento.
    Se utiliza en: ISP_STA.Wind, ISP_RST.Wind
    """
    OFF = 0     # 0 - no wind
    WEAK = 1    # 1 - weak wind
    STRONG = 2  # 2 - strong wind