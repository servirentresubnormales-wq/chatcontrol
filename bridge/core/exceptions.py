class BridgeError(Exception):
    """Base exception for Bridge errors."""
    pass


class ProtocolError(BridgeError):
    """Error in protocol serialization/deserialization."""
    pass


class ConnectionError(BridgeError):
    """Error connecting to Minecraft Core."""
    pass


class ConnectionTimeoutError(ConnectionError):
    """Connection or request timed out."""
    pass


class ConfigError(BridgeError):
    """Configuration loading or validation error."""
    pass


class CommandParseError(BridgeError):
    """Error parsing chat command."""
    pass
