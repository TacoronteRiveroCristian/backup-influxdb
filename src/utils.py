"""
Modulo con funciones utiles para el sistema.
"""

import logging


def get_basic_console_handler(name: str) -> logging.Logger:
    """
    Retorna un logger basico con un handler de consola.
    """

    # Crear logger basico
    logger = logging.getLogger(name)
    # Configurar nivel del logger
    logger.setLevel(logging.INFO)

    # Evitar handlers duplicados
    if logger.handlers:
        return logger

    # Crear Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Crear Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)

    # Agregar Consolo Handler al logger
    logger.addHandler(ch)

    return logger
