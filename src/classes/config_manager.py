"""
Gestiona la configuracion del sistema leyendo un YAML.
Incluye autodeteccion de bases de datos cuando el listado queda vacio.
"""

import os
from typing import Any, Dict
from urllib.parse import urlparse

from influxdb import InfluxDBClient as NativeInfluxDBClient
import yaml

from src.exceptions import ConfigManagerError
from src.schemas import (
    DestinationConfig,  # LoggingConfig,; OptionsConfig,
    MeasurementsConfig,
    SourceConfig,
)
from src.utils import get_basic_console_handler


class ConfigManager:
    """_summary_"""

    def __init__(self, config_file: str):
        """ """
        # Obtener logger basico
        self._logger = get_basic_console_handler(self.__class__.__name__)
        self._logger.info(f"ConfigManager initialized for file: {config_file}")

        # Atributos de clase
        self._config_file = config_file

        # Comprobar que el fichero de configuracion existe y es un archivo YAML
        self._check_config_file()

        # Cargar configuracion
        self._load_config()

        # Autodescubrimiento de bases de datos si se dejo la lista vacia
        self._discover_databases()

        # Validar la configuracion del archivo de configuracion YAML
        SourceConfig(**self.get_source_config())
        DestinationConfig(**self.get_destination_config())
        MeasurementsConfig(**self.get_measurements_config())
        # OptionsConfig(**self.get_options_config())
        # LoggingConfig(**self.get_logging_config())

    def _check_config_file(self):
        """
        Comprobar que el fichero de configuracion existe y es un archivo YAML
        """

        if not os.path.exists(self._config_file):
            error_msg = f"Config file {self._config_file} does not exist"
            self._logger.critical(error_msg)
            raise FileNotFoundError(error_msg)
        elif not self._config_file.endswith(".yaml"):
            error_msg = f"Config file {self._config_file} is not a YAML file"
            self._logger.critical(error_msg)
            raise ValueError(error_msg)
        else:
            self._logger.info(f"Config file {self._config_file} exists")

    def _load_config(self):
        """
        Cargar la configuracion desde el fichero de configuracion
        """
        try:
            with open(self._config_file, "r") as f:
                self._config = yaml.load(f, Loader=yaml.FullLoader)
            self._logger.info(f"Config loaded from {self._config_file}")
        except Exception as e:
            error_msg = f"Error loading config from {self._config_file}: {e}"
            self._logger.critical(error_msg)
            raise ConfigManagerError(error_msg)

    def _discover_databases(self) -> None:
        """
        Si la lista de 'databases' esta vacia se intenta descubrir todas las
        bases de datos del servidor origen y se rellenan con el nombre de
        destino aplicando prefix/suffix.
        """
        source_cfg = self._config.get("source") or {}
        databases = source_cfg.get("databases")
        if databases:
            return  # Ya hay bases definidas

        url = source_cfg.get("url")
        if not url:
            raise ConfigManagerError(
                "No se puede autodetectar bases de datos: falta 'url' en 'source'."
            )

        parsed = urlparse(url)
        if not parsed.hostname or not parsed.port:
            raise ConfigManagerError(
                f"No se puede autodetectar bases de datos: URL invalida '{url}'."
            )

        prefix = source_cfg.get("prefix") or ""
        suffix = source_cfg.get("suffix") or ""

        self._logger.info(
            "Autodetectando bases de datos desde %s:%s", parsed.hostname, parsed.port
        )

        try:
            client = NativeInfluxDBClient(
                host=parsed.hostname,
                port=parsed.port,
                username=source_cfg.get("user") or None,
                password=source_cfg.get("password") or None,
                ssl=parsed.scheme == "https",
            )
            db_list = client.get_list_database()
        except Exception as e:
            raise ConfigManagerError(
                f"No se pudieron obtener las bases de datos desde '{url}': {e}"
            ) from e
        finally:
            try:
                client.close()
            except Exception:
                pass

        filtered = [db for db in db_list if db.get("name") and db["name"] != "_internal"]
        if not filtered:
            raise ConfigManagerError(
                "Autodeteccion no retorno bases de datos (se excluye '_internal')."
            )

        discovered = [
            {"name": db["name"], "destination": f"{prefix}{db['name']}{suffix}"}
            for db in filtered
        ]
        self._config["source"]["databases"] = discovered
        self._logger.info(
            "Autodeteccion completada, %s bases de datos configuradas.",
            len(discovered),
        )

    def get_config(self) -> dict:
        """
        Retorna la configuracion completa
        """
        return self._config

    def get_source_config(self) -> Dict[str, Any]:
        """
        Retorna la configuracion del servidor de origen
        """
        source_config = self._config.get("source", {})
        return source_config

    def get_destination_config(self) -> Dict[str, Any]:
        """
        Retorna la configuracion del servidor de destino
        """
        destination_config = self._config.get("destination", {})
        return destination_config

    def get_measurements_config(self) -> Dict[str, Any]:
        """
        Retorna la configuracion de las mediciones
        """
        return self._config.get("measurements") or {}

    def get_options_config(self) -> Dict[str, Any]:
        """
        Retorna la configuracion de las opciones
        """
        options_config = self._config.get("options", {})
        return options_config

    def get_logging_config(self) -> Dict[str, Any]:
        """
        Retorna la configuracion de los logs
        """
        return self._config.get("logging") or {}


if __name__ == "__main__":
    config_manager = ConfigManager("/app/config/conf1.yaml")
    config_manager.get_measurements_config()
