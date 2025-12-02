"""
Definicion de los esquemas de los datos de configuracion
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Set

from pydantic import (
    AnyUrl,
    BaseModel,
    DirectoryPath,
    Field,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError


def _validate_url(url: AnyUrl) -> AnyUrl:
    """
    Validacion reutilizable para URLs que requieren puerto explicito
    """
    if not url:
        raise PydanticCustomError("url_empty", "La URL no puede ser vacia")

    # Comprobar que se especifica puerto de forma explicita (slash final opcional)
    if url.port is None:
        raise PydanticCustomError(
            "url_missing_port",
            "La URL '{url}' debe contener un puerto de servicio explicito (ej: http://localhost:8086).",
            {"url": str(url)},
        )

    # Comprobar que el puerto esta en rango valido
    if url.port is not None and not (1 <= url.port <= 65535):
        raise PydanticCustomError(
            "port_out_of_range",
            "El puerto '{port}' debe estar entre 1 y 65535",
            {"port": url.port},
        )

    return url


def _validate_required_fields(
    cls, data: Dict[str, str], required: Set[str]
) -> Dict[str, str]:
    """
    Valida que los campos requeridos esten presentes antes de la
    validacion de Pydantic.
    """
    missing = required - set(data.keys())
    if missing:
        missing_str = ", ".join([f"'{f}'" for f in sorted(list(missing))])
        raise PydanticCustomError(
            "source_config_missing_fields",
            "Los siguientes campos son obligatorios en la configuracion 'source': {missing_fields}.",
            {"missing_fields": missing_str},
        )
    return data


class SourceConfig(BaseModel):
    """Configuracion del servidor de origen."""

    url: AnyUrl = Field(description="URL del servidor de origen")
    databases: list[Dict[str, str]] = Field(
        description="Lista de bases de datos a procesar. Si se deja vacia se intentara autodetectar."
    )
    prefix: Optional[str] = Field(
        default=None, description="Prefijo de la medicion"
    )
    suffix: Optional[str] = Field(
        default=None, description="Sufijo de la medicion"
    )
    user: Optional[str] = Field(
        default=None, description="Usuario de la medicion"
    )
    password: Optional[str] = Field(
        default=None, description="Password de la medicion"
    )
    group_by: Optional[str] = Field(
        default=None, description="Grupo de la medicion"
    )

    @model_validator(mode="before")
    def validate_required_fields(cls, data: Dict[str, str]) -> Dict[str, str]:
        """
        Valida que los campos requeridos esten presentes antes de la
        validacion de Pydantic.
        """
        return _validate_required_fields(cls, data, {"url", "databases"})

    @field_validator("databases", mode="before")
    def validate_databases(
        cls, data: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Valida que la estructura de cada base de datos sea correcta.
        La lista puede estar vacia para habilitar autodeteccion.
        """
        if data is None:
            raise PydanticCustomError(
                "source_config_missing_databases",
                "El campo 'databases' es obligatorio en la configuracion 'source'.",
            )

        if len(data) == 0:
            return data  # Se usara autodeteccion

        for d in data:
            if not d.get("name") or not d.get("destination"):
                raise PydanticCustomError(
                    "source_config_missing_databases",
                    "Las entradas de 'databases' no pueden tener 'name' o 'destination' vacios.",
                )
        return data

    @field_validator("databases", mode="before")
    def validate_no_duplicates(
        cls, data: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Valida que no existan valores duplicados en las claves name ni destination
        """
        if not data:
            return data

        names = set()
        destinations = set()
        for d in data:
            name = d.get("name")
            destination = d.get("destination")
            if name in names:
                raise PydanticCustomError(
                    "source_config_duplicate_name",
                    "No se permiten valores duplicados en la clave 'name' de databases. Valor duplicado: '{value}'",
                    {"value": name},
                )
            if destination in destinations:
                raise PydanticCustomError(
                    "source_config_duplicate_destination",
                    "No se permiten valores duplicados en la clave 'destination' de databases. Valor duplicado: '{value}'",
                    {"value": destination},
                )
            names.add(name)
            destinations.add(destination)
        return data

    @field_validator("url")
    def validate_url(cls, v: AnyUrl) -> AnyUrl:
        """
        Valida la URL del servidor de origen
        """
        return _validate_url(v)

    @field_validator("group_by")
    def validate_group_by(cls, v: Optional[str]) -> Optional[str]:
        """
        Validar el grupo de la medicion
        """
        if v is None or v == "":
            return v  # Sin agregacion es valido

        # Validar patron correcto de numero + letra
        time_pattern = r"^(\d+)(\w)$"
        match = re.match(time_pattern, v)
        if not match:
            raise PydanticCustomError(
                "group_by_invalid_format",
                "El formato de 'group_by' ('{value}') no es valido. Debe ser un numero seguido de una letra (ej: '1m', '30s').",
                {"value": v},
            )
        return v


class DestinationConfig(BaseModel):
    """Configuracion del servidor de destino"""

    url: AnyUrl = Field(description="URL del servidor de destino")
    user: Optional[str] = Field(
        default=None, description="Usuario del servidor de destino"
    )
    password: Optional[str] = Field(
        default=None, description="Password del servidor de destino"
    )

    @model_validator(mode="before")
    def validate_required_fields(cls, data: Dict[str, str]) -> Dict[str, str]:
        """
        Valida que los campos requeridos esten presentes antes de la
        validacion de Pydantic.
        """
        return _validate_required_fields(cls, data, {"url"})

    @field_validator("url")
    def validate_url(cls, v: AnyUrl) -> AnyUrl:
        return _validate_url(v)


class FieldsConfig(BaseModel):
    """
    Configuracion de los campos del diccionario de mediciones, specific
    """

    include: Optional[list[str]] = Field(
        min_length=1,
        default=None,
        description="Campos a incluir",
    )
    exclude: Optional[list[str]] = Field(
        min_length=1,
        default=None,
        description="Campos a excluir",
    )
    types: Optional[list[Literal["numeric", "string", "boolean"]]] = Field(
        min_length=1,
        default=None,
        description="Tipos de datos soportados",
    )


class SpecificMeasurementsConfig(BaseModel):
    """
    Configuracion de las mediciones especificas
    """

    fields: FieldsConfig = Field(description="Configuracion de los campos")

    @model_validator(mode="before")
    def _validate_required_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            if "fields" not in data:
                raise PydanticCustomError(
                    "specific_measurement_fields_missing",
                    "La clave 'fields' es obligatoria en una configuracion de medicion especifica.",
                )
        return data


class MeasurementsConfig(BaseModel):
    """Configuracion de las mediciones"""

    include: Optional[list[str]] = Field(
        min_length=1, default=None, description="Mediciones a incluir"
    )
    exclude: Optional[list[str]] = Field(
        min_length=1, default=None, description="Mediciones a excluir"
    )
    # specific: Optional[dict[str, SpecificMeasurementsConfig]] = Field(
    #     default_factory=dict,
    #     description="Configuracion de las mediciones especificas",
    # )

    @model_validator(mode="before")
    def validate_specific(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida el formato correcto de la configuracion de mediciones en el caso
        de que se haya especificado al menos una.
        """
        specific_config = data.get("specific")
        if not specific_config:
            return data

        for key, value in specific_config.items():
            if not isinstance(value, dict):
                raise PydanticCustomError(
                    "specific_measurement_invalid_format",
                    "La configuracion para la medicion especifica '{measurement_name}' debe ser un diccionario, no de tipo '{value_type}'.",
                    {
                        "measurement_name": key,
                        "value_type": type(value).__name__,
                    },
                )

            if value.get("fields") is None:
                raise PydanticCustomError(
                    "specific_measurement_fields_missing",
                    "La clave 'fields' en la medicion especifica '{measurement_name}' no puede estar vacia o ser nula.",
                    {"measurement_name": key},
                )
        return data


# class OptionsRangeConfig(BaseModel):
#     """Configuracion para modo range"""

#     start_date: Optional[datetime] = Field(
#         default=None, description="Fecha de inicio (opcional, formato ISO 8601)"
#     )
#     end_date: Optional[datetime] = Field(
#         default=None, description="Fecha de fin (opcional, formato ISO 8601)"
#     )

#     @model_validator(mode="after")
#     def validate_dates(self) -> "OptionsRangeConfig":
#         # Solo se valida si ambas fechas estan presentes
#         if self.start_date and self.end_date:
#             if self.end_date <= self.start_date:
#                 raise PydanticCustomError(
#                     "range_end_date_before_start",
#                     "La fecha de fin ('{end_date}') debe ser posterior a la fecha de inicio ('{start_date}').",
#                     {
#                         "start_date": self.start_date.isoformat(),
#                         "end_date": self.end_date.isoformat(),
#                     },
#                 )
#         return self


# class OptionsIncrementalConfig(BaseModel):
#     """Configuracion para modo incremental"""

#     schedule: str = Field(
#         description="Expresion CRON para automatizacion (requerida)"
#     )

#     @model_validator(mode="before")
#     def _validate_required_fields(cls, data: object) -> object:
#         """
#         Valida que el campo 'schedule' este presente para el modo incremental.
#         """
#         if isinstance(data, dict):
#             if "schedule" not in data:
#                 raise PydanticCustomError(
#                     "incremental_config_missing_schedule",
#                     "El campo 'schedule' es obligatorio en la configuracion 'incremental'.",
#                 )
#         return data

#     @field_validator("schedule")
#     def validate_schedule(cls, v: str) -> str:
#         """
#         Valida que la expresion CRON no este vacia y tenga 5 campos.
#         """
#         if not v:
#             raise PydanticCustomError(
#                 "cron_expression_empty",
#                 "La expresion CRON no puede estar vacia para el modo incremental.",
#             )

#         cron_parts = v.split()
#         if len(cron_parts) != 5:
#             raise PydanticCustomError(
#                 "cron_expression_invalid",
#                 "La expresion CRON '{cron}' no es valida. Debe tener exactamente 5 campos separados por espacios.",
#                 {"cron": v},
#             )
#         return v


# class OptionsConfig(BaseModel):
#     """
#     Configuracion de las opciones de backup. Valida la configuracion del modo
#     de backup seleccionado.
#     """

#     backup_mode: Literal["incremental", "range"] = Field(
#         description="Modo de backup"
#     )
#     range: Optional[OptionsRangeConfig] = Field(
#         description="Configuracion para modo range"
#     )
#     incremental: Optional[OptionsIncrementalConfig] = Field(
#         description="Configuracion para modo incremental"
#     )
#     timeout_client: int = Field(description="Timeout por consulta (segundos)")
#     retries: int = Field(description="Numero de reintentos por operacion")
#     retry_delay: int = Field(
#         description="Intervalo entre reintentos (segundos)"
#     )
#     initial_connection_retry_delay: int = Field(
#         description="Retraso para reconexion inicial"
#     )
#     days_of_pagination: int = Field(description="Dias de paginacion")
#     parallel_workers: int = Field(
#         description="Numero de trabajadores en paralelo"
#     )
#     field_obsolete_threshold: Optional[str] = Field(
#         description="Umbral de obsolescencia de campos"
#     )

#     @model_validator(mode="before")
#     def _validate_required_fields(cls, data: object) -> object:
#         if isinstance(data, dict):
#             required = {
#                 "backup_mode",
#                 "timeout_client",
#                 "retries",
#                 "retry_delay",
#                 "initial_connection_retry_delay",
#                 "days_of_pagination",
#                 "parallel_workers",
#             }
#             missing = required - set(data.keys())
#             if missing:
#                 missing_str = ", ".join(
#                     [f"'{f}'" for f in sorted(list(missing))]
#                 )
#                 raise PydanticCustomError(
#                     "options_config_missing_fields",
#                     "Los siguientes campos son obligatorios en la configuracion 'options': {missing_fields}.",
#                     {"missing_fields": missing_str},
#                 )
#         return data

#     @model_validator(mode="after")
#     def _validate_backup_mode_config(self) -> "OptionsConfig":
#         if self.backup_mode == "range" and self.range is None:
#             raise PydanticCustomError(
#                 "options_config_missing_range",
#                 "El bloque de configuracion 'range' es obligatorio cuando 'backup_mode' es 'range'.",
#             )
#         if self.backup_mode == "incremental" and self.incremental is None:
#             raise PydanticCustomError(
#                 "options_config_missing_incremental",
#                 "El bloque de configuracion 'incremental' es obligatorio cuando 'backup_mode' es 'incremental'.",
#             )
#         return self


# class LogRotationConfig(BaseModel):
#     """Configuracion de la rotacion de logs"""

#     enabled: Optional[bool] = Field(
#         default=None,
#         description="Indica si la rotacion de logs esta habilitada",
#     )
#     when: Optional[Literal["D", "H", "M"]] = Field(
#         default=None, description="Frecuencia de rotacion"
#     )
#     interval: Optional[int] = Field(
#         default=None, description="Intervalo de rotacion"
#     )
#     backup_count: Optional[int] = Field(
#         default=None, description="Numero de backups a mantener"
#     )

#     @model_validator(mode="after")
#     def validate_log_rotation(self) -> "LogRotationConfig":
#         """
#         Valida que si la rotacion de logs esta habilitada, entonces los
#         demas campos deben estar presentes.
#         """
#         if self.enabled is True:
#             missing_fields = []
#             if self.interval is None:
#                 missing_fields.append("interval")
#             if self.backup_count is None:
#                 missing_fields.append("backup_count")
#             if self.when is None:
#                 missing_fields.append("when")

#             if missing_fields:
#                 raise PydanticCustomError(
#                     "log_rotation_incomplete",
#                     "La rotacion de logs esta habilitada pero faltan los siguientes campos requeridos: {missing_fields}. Todos los campos (interval, backup_count, when) deben estar presentes cuando enabled=True.",
#                     {"missing_fields": ", ".join(missing_fields)},
#                 )
#         return self


# class LokiConfig(BaseModel):
#     """Configuracion de Loki"""

#     enabled: bool = Field(
#         default=False, description="Indica si Loki esta habilitado"
#     )
#     url: Optional[AnyUrl] = Field(default=None, description="URL de Loki")
#     tags: Optional[dict[str, str]] = Field(
#         default_factory=dict, description="Tags de Loki"
#     )

#     @field_validator("url")
#     def validate_loki_url(cls, v: Optional[AnyUrl]) -> Optional[AnyUrl]:
#         """Valida la URL de Loki solo si se proporciona."""
#         if v:
#             return _validate_url(v)
#         return v

#     @model_validator(mode="after")
#     def check_loki_url_if_enabled(self) -> "LokiConfig":
#         """Valida que la URL exista si Loki esta habilitado."""
#         if self.enabled and not self.url:
#             raise PydanticCustomError(
#                 "loki_url_required_when_enabled",
#                 "El campo 'url' es obligatorio en la configuracion de Loki cuando 'enabled' es True.",
#             )
#         return self


# class LoggingConfig(BaseModel):
#     """Configuracion de los logs"""

#     log_directory: Optional[DirectoryPath] = Field(
#         default=None, description="Directorio de logs"
#     )
#     log_rotation: Optional[LogRotationConfig] = Field(
#         default=None, description="Configuracion de la rotacion de logs"
#     )
#     loki: Optional[LokiConfig] = Field(
#         default=None, description="Configuracion de Loki"
#     )
#     log_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR"]] = Field(
#         default="INFO", description="Nivel de logs"
#     )
