"""
exceptions.py - Catálogo de excepciones personalizadas para el framework InSim.

Estas excepciones permiten identificar rápidamente el origen de un fallo
proporcionando mensajes detallados y estructuras de datos relevantes.
"""

class InSimError(Exception):
    """Clase base para todos los errores del framework InSim."""
    pass

class InSimConnectionError(InSimError):
    """
    Excepción lanzada cuando hay problemas con la conexión de red (TCP/UDP)
    o con la autenticación en LFS.
    """
    def __init__(self, message, host=None, port=None):
        super().__init__(message)
        self.host = host
        self.port = port

class InSimConfigurationError(InSimError):
    """
    Lanzada cuando la configuración (settings.py o diccionarios)
    es inválida o faltan parámetros críticos.
    """
    pass

class InSimPacketError(InSimError):
    """
    Lanzada cuando un paquete no puede ser decodificado,
    es demasiado pequeño o tiene un formato inválido.
    """
    def __init__(self, message, packet_type=None, packet_size=None, data=None):
        super().__init__(message)
        self.packet_type = packet_type
        self.packet_size = packet_size
        self.data = data

class InSimModuleError(InSimError):
    """
    Lanzada cuando un módulo (InSimApp) falla al cargarse,
    tiene dependencias no resueltas o un manifiesto corrupto.
    """
    def __init__(self, message, module_name=None):
        super().__init__(message)
        self.module_name = module_name

class InSimProtocolError(InSimError):
    """
    Lanzada cuando LFS responde con un error de protocolo (ej: versión incorrecta)
    o se viola la lógica del protocolo InSim.
    """
    pass

class InSimCommandError(InSimError):
    """
    Lanzada cuando un comando está mal formado
    """
    def __init__(self, message, command_name=None):
        super().__init__(message)
        self.command_name = command_name