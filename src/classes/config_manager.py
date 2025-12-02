"""
Clase encargada de la gestion de la configuracion del sistema para un servicio
con un archivo de configuracion en formato YAML.

Esta clase comienza con un logger basico, luego carga toda la configuracion
pertinente y finalmente expone los datos de configuracion a traves de atributos
de la clase para que se pueda acceder a ellos desde cualquier parte del codigo.
"""

import os
from typing import Any, Dict

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
