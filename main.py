"""
Punto de entrada del servicio de backup.
Provee modo de validacion de configuracion (--validate-only).
"""

import argparse
import sys
from pathlib import Path
from typing import Iterable

from src.classes.config_manager import ConfigManager


def parse_args() -> argparse.Namespace:
    """Construye el parser de argumentos CLI."""
    parser = argparse.ArgumentParser(
        description="Servicio de backup InfluxDB - gestor de configuracion"
    )
    parser.add_argument(
        "--config",
        default="config/backup-config.yaml",
        help="Ruta al archivo de configuracion YAML (si es directorio, valida todos los .yaml).",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Solo valida la configuracion y termina.",
    )
    return parser.parse_args()


def iter_configs(path: Path) -> Iterable[Path]:
    """Devuelve iterador de configs a validar (salta templates)."""
    if path.is_dir():
        yield from sorted(
            p
            for p in path.glob("*.yaml")
            if not p.name.endswith(".template.yaml") and "template" not in p.name
        )
    else:
        yield path


def main() -> int:
    args = parse_args()
    path = Path(args.config)

    try:
        configs = list(iter_configs(path))
        if not configs:
            raise FileNotFoundError(f"No se encontraron .yaml en {path}")

        for cfg in configs:
            ConfigManager(str(cfg))
            print(f"Configuracion valida: {cfg}")

        if args.validate_only:
            return 0

        print(
            "Validacion completada. Ejecucion de backup no implementada en este entrypoint."
        )
        return 0
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"Error de configuracion: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
