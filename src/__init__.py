"""
Sistema de backup de InfluxDB
============================

Módulos principales del sistema de backup organizados en:
- classes/: Todas las clases del sistema
- utils: Funciones utilitarias
"""

# Importar todas las clases desde el módulo classes
from .classes import *

# Importar funciones utilitarias (mantener acceso directo)
from . import utils

__all__ = [
    # Core classes (importadas desde classes/)
    'BackupOrchestrator',
    'BackupProcessor',
    'ConfigManager',
    'InfluxDBClient',
    'LoggerManager',
    'APBackupScheduler',

    # Exceptions (importadas desde classes/)
    'ConfigurationError',
    'InfluxDBError',
    'InfluxDBConnectionError',
    'InfluxDBQueryError',
    'InfluxDBWriteError',
    'APSchedulerError',

    # Utils module
    'utils',
]

__version__ = '1.0.0'
__author__ = 'InfluxDB Backup System'
