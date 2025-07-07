#!/usr/bin/env python3
"""
Punto de entrada principal para el sistema de backup de InfluxDB
===============================================================

Este script es el punto de entrada principal del sistema de backup.
Inicializa y ejecuta el BackupOrchestrator que maneja todos los procesos
de backup en paralelo.
"""

import argparse
import os
import sys

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src import BackupOrchestrator


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="InfluxDB Backup Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                           # Use default /config directory
  python main.py --config /path/to/config # Use custom config directory
  python main.py --verbose                # Enable verbose logging
  python main.py --validate-only          # Only validate configurations
        """,
    )

    parser.add_argument(
        "--config",
        "-c",
        default="/config",
        help="Configuration directory (default: /config)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate configuration files, do not run backups",
    )

    args = parser.parse_args()

    # Crear orchestrator
    orchestrator = BackupOrchestrator(
        config_directory=args.config, verbose=args.verbose
    )

    try:
        if args.validate_only:
            # Solo validar configuraciones
            config_files = orchestrator._find_config_files()

            if not config_files:
                print("No configuration files found")
                return 1

            print(f"Validating {len(config_files)} configuration files...")

            valid_count = 0
            for config_path in config_files:
                filename = os.path.basename(config_path)
                if orchestrator._validate_config_file(config_path):
                    print(f"  ✓ {filename}")
                    valid_count += 1
                else:
                    print(f"  ✗ {filename}")

            print(
                f"\nValidation complete: {valid_count}/{len(config_files)} valid"
            )
            return 0 if valid_count == len(config_files) else 1

        else:
            # Ejecutar backups
            exit_code = orchestrator.run()
            return exit_code

    except Exception as e:
        print(f"Fatal error: {e}")
        return 1

    finally:
        orchestrator.cleanup()


if __name__ == "__main__":
    exit(main())
