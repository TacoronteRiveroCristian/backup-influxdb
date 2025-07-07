"""
Clases del sistema de backup de InfluxDB
========================================

Todas las clases principales del sistema organizadas por responsabilidad.
"""

from .apscheduler_backup import APBackupScheduler, APSchedulerError
from .backup_orchestrator import BackupOrchestrator
from .backup_processor import BackupProcessor
from .config_manager import ConfigManager, ConfigurationError
from .influxdb_client import (
    InfluxDBClient,
    InfluxDBConnectionError,
    InfluxDBError,
    InfluxDBQueryError,
    InfluxDBWriteError,
)
from .logger_manager import LoggerManager

__all__ = [
    # Core classes
    "BackupOrchestrator",
    "BackupProcessor",
    "ConfigManager",
    "InfluxDBClient",
    "LoggerManager",
    "APBackupScheduler",
    # Exceptions
    "ConfigurationError",
    "InfluxDBError",
    "InfluxDBConnectionError",
    "InfluxDBQueryError",
    "InfluxDBWriteError",
    "APSchedulerError",
]

__version__ = "1.0.0"
