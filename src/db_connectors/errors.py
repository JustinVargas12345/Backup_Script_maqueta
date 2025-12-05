class DatabaseNotFoundError(Exception):
    """Excepción lanzada cuando la base de datos solicitada no existe en el servidor local.

    Los conectores deben lanzar esta excepción cuando detecten el caso específico de
    "database not found". El CLI capturará esta excepción y mostrará un mensaje corto
    al usuario mientras que los conectores registran el detalle completo en el log.
    """
    pass
