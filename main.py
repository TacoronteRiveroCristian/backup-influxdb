"""
Punto de entrada del servicio de backup.
Provee modo de validacion de configuracion (--validate-only).
"""

import argparse
import sys

from src.classes.config_manager import ConfigManager


def parse_args() -> argparse.Namespace:
    """Construye el parser de argumentos CLI."""
    parser = argparse.ArgumentParser(
        description="Servicio de backup InfluxDB - gestor de configuracion"
    )
    parser.add_argument(
        "--config",
        default="config/backup-config.yaml",
        help="Ruta al archivo de configuracion YAML",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Solo valida la configuracion y termina.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        ConfigManager(args.config)
        if args.validate_only:
            print(f"Configuracion valida: {args.config}")
            return 0
        # Punto de extension futuro: ejecutar proceso de backup real.
        print(
            "Configuracion valida. Ejecucion de backup no implementada en este entrypoint."
        )
        return 0
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"Error de configuracion: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
