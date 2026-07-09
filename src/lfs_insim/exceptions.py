"""
exceptions.py - Custom exception hierarchy for the InSim framework.

These exceptions make it easy to pinpoint the origin of a failure, carrying
detailed messages and any relevant structured data.
"""

__all__ = [
    "InSimError",
    "InSimConnectionError",
    "InSimConfigurationError",
    "InSimPacketError",
    "InSimModuleError",
    "InSimCommandError",
]


class InSimError(Exception):
    """Base class for every InSim framework error."""

    pass


class InSimConnectionError(InSimError):
    """Raised on network (TCP/UDP) or LFS authentication problems."""

    def __init__(self, message, host=None, port=None):
        super().__init__(message)
        self.host = host
        self.port = port


class InSimConfigurationError(InSimError):
    """Raised when the configuration is invalid or a critical key is missing."""

    pass


class InSimPacketError(InSimError):
    """Raised when a packet cannot be decoded, is too small or malformed."""

    def __init__(self, message, packet_type=None, packet_size=None, data=None):
        super().__init__(message)
        self.packet_type = packet_type
        self.packet_size = packet_size
        self.data = data


class InSimModuleError(InSimError):
    """Raised when a module (InSimApp) fails to load, has unresolved
    dependencies or a corrupt manifest."""

    def __init__(self, message, module_name=None):
        super().__init__(message)
        self.module_name = module_name


class InSimCommandError(InSimError):
    """Command-system error type: a malformed command.

    The core does not raise it itself; it is provided so module authors can
    raise it from their own command handlers (carries ``command_name``).
    """

    def __init__(self, message, command_name=None):
        super().__init__(message)
        self.command_name = command_name
