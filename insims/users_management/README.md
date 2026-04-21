# 🔐 Users Management - InSim

InSim para gestionar y monitorizar usuarios conectados al servidor Live for Speed.

## 📋 Características

- **Seguimiento en tiempo real**: Monitorea conexiones, desconexiones y posiciones de jugadores
- **Soporte para IA**: Gestiona tanto jugadores humanos como coches de IA
- **Sistema de comandos**: Interfaz de chat para consultar información de usuarios
- **Estado detallado**: Mantiene mapping completo UCID ↔ PLID ↔ Username

## 🚀 Instalación y Uso

### Ejecución
```bash
lfs-insim run users-management
```

### Configuración
Asegúrate de tener configurado el prefijo de comandos en tu `insim.json`. Por defecto usa `!`.

## 💬 Comandos Disponibles

Todos los comandos usan el prefijo `!um`:

| Comando | Descripción |
|---------|-------------|
| `!um` | Muestra la ayuda con todos los comandos disponibles |
| `!um user-info <username>` | Muestra información detallada de un usuario específico |
| `!um users-info` | Lista información de todos los usuarios conectados |

### Ejemplos de uso

```
!um user-info SpeedRacer
!um users-info
```

## 🔍 Información Monitoreada

El sistema mantiene seguimiento de:

### Usuarios Humanos
- **UCID**: Unique Connection ID
- **PLID**: Player ID (en pista) o "(Espectador)"
- **Username**: Nombre de usuario de LFS
- **PlayerName**: Nombre visible en el juego
- **Posición**: Coordenadas X, Y en tiempo real
- **Velocidad**: Velocidad actual en km/h

### Coches de IA
- **PLID**: Player ID del coche IA
- **Owner**: UCID del jugador que controla la IA
- **Nombre**: Nombre asignado al coche IA

## 📊 Estados Internos

El InSim mantiene las siguientes estructuras de datos:

```python
# Usuarios conectados
uname_ucid: dict[str, int]        # username -> UCID
ucid_plid: dict[int, int]         # UCID -> PLID
ucid_pname: dict[int, str]        # UCID -> PlayerName

# Información en pista
plid_position: dict[int, tuple]    # PLID -> (X, Y)
plid_speed_kmh: dict[int, float]   # PLID -> velocidad km/h

# Coches IA por usuario
ai_ucid_plid: dict[int, set]       # UCID -> {PLIDs de IA}
ai_plid_pname: dict[int, str]      # PLID -> Nombre IA
```

## 🔧 Dependencias

- **Framework**: `lfs-insim` v0.2.0+
- **Python**: 3.9+
- **LFS**: 0.7F+ con protocolo InSim v10

## 🚨 Consideraciones Técnicas

- Solicita información inicial con paquetes TINY (NCN, NPL)
- Usa flags `ISF.LOCAL | ISF.MCI` para recibir información completa
- Actualiza estado en tiempo real con paquetes MCI (Multi Car Info)
- Limpia estado automáticamente al recibir TINY.MPE (Multi Player End)

## 📝 Notas de Desarrollo

Este módulo está diseñado como base para sistemas más complejos de administración de servidores. Puede extenderse con:

- Persistencia de datos en base de datos
- Sistema de permisos y roles
- Histórico de conexiones
- Comandos de administración (kick, ban, etc.)

## 🤝 Contribuciones

Las mejoras son bienvenidas. Considera:
- Añadir tests unitarios
- Mejorar manejo de errores
- Optimizar rendimiento para muchos usuarios
- Agregar persistencia de datos