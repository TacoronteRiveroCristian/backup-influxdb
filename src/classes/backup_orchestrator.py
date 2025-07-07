#!/usr/bin/env python3
"""
Orchestrator principal para el sistema de backup de InfluxDB
===========================================================

Maneja la ejecución paralela de múltiples procesos de backup
basados en archivos de configuración YAML.
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime
from multiprocessing import Event, Process, Queue
from typing import Any, Dict, List

from .backup_processor import BackupProcessor
from .config_manager import ConfigManager, ConfigurationError


class BackupOrchestrator:
    """
    Orchestrator principal para el sistema de backup.

    Maneja la ejecución paralela de múltiples procesos de backup
    basados en archivos de configuración YAML.
    """

    def __init__(
        self, config_directory: str = "/config", verbose: bool = False
    ):
        """
        Inicializa el orchestrator.

        Args:
            config_directory: Directorio con archivos de configuración
            verbose: Habilitar logging verbose
        """
        self.config_directory = config_directory
        self.verbose = verbose

        # Configurar logging básico
        self._setup_logging()

        # Estado del orchestrator
        self.processes: List[Process] = []
        self.results_queue = Queue()
        self.shutdown_event = Event()

        # Configurar manejo de señales
        self._setup_signal_handlers()

        self.logger = logging.getLogger("BackupOrchestrator")

    def _setup_logging(self) -> None:
        """Configura el logging básico del orchestrator."""
        level = logging.DEBUG if self.verbose else logging.INFO

        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def _setup_signal_handlers(self) -> None:
        """Configura los manejadores de señales."""

        def signal_handler(signum, frame):
            self.logger.info(
                f"Received signal {signum}, initiating graceful shutdown..."
            )

            # Para procesos de larga duración, solo establecer la señal de shutdown
            # pero permitir que el bucle principal maneje la terminación
            self.shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _find_config_files(self) -> List[str]:
        """
        Busca todos los archivos .yaml en el directorio de configuración.

        Returns:
            List[str]: Lista de rutas de archivos de configuración
        """
        config_files = []

        if not os.path.exists(self.config_directory):
            self.logger.error(
                f"Configuration directory not found: {self.config_directory}"
            )
            return config_files

        for filename in os.listdir(self.config_directory):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                config_path = os.path.join(self.config_directory, filename)
                if os.path.isfile(config_path):
                    config_files.append(config_path)

        return sorted(config_files)

    def _validate_config_file(self, config_path: str) -> bool:
        """
        Valida un archivo de configuración.

        Args:
            config_path: Ruta del archivo de configuración

        Returns:
            bool: True si es válido
        """
        try:
            ConfigManager(config_path)
            return True
        except ConfigurationError as e:
            self.logger.error(f"Invalid configuration file {config_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(
                f"Error validating configuration file {config_path}: {e}"
            )
            return False

    def _is_long_running_process(self, config_path: str) -> bool:
        """
        Determina si un proceso es de larga duración (incremental con scheduler).

        Args:
            config_path: Ruta del archivo de configuración

        Returns:
            bool: True si es un proceso de larga duración
        """
        try:
            config = ConfigManager(config_path)
            schedule = config.get_schedule()
            return (
                config.get_backup_mode() == "incremental"
                and schedule is not None
                and schedule.strip() != ""
            )
        except:
            return False

    def _run_backup_process(
        self, config_path: str, results_queue: Queue, shutdown_event: Event
    ) -> None:
        """
        Ejecuta un proceso de backup individual.

        Args:
            config_path: Ruta del archivo de configuración
            results_queue: Cola para resultados
            shutdown_event: Evento de shutdown
        """
        process_name = os.path.basename(config_path)

        try:
            # Crear procesador de backup
            with BackupProcessor(config_path) as processor:
                # Verificar si debemos parar
                if shutdown_event.is_set():
                    results_queue.put(
                        {
                            "config": process_name,
                            "success": False,
                            "error": "Shutdown requested",
                            "start_time": datetime.now().isoformat(),
                        }
                    )
                    return

                # Para procesos de larga duración, reportar inicio inmediatamente
                if self._is_long_running_process(config_path):
                    results_queue.put(
                        {
                            "config": process_name,
                            "success": True,
                            "long_running": True,
                            "start_time": datetime.now().isoformat(),
                            "status": "RUNNING (Scheduled backup process)",
                        }
                    )

                # Ejecutar backup
                start_time = datetime.now()
                result = processor.run()
                end_time = datetime.now()

                # Para procesos de corta duración, reportar resultado final
                if not self._is_long_running_process(config_path):
                    # Preparar resultado
                    result_data = {
                        "config": process_name,
                        "success": result.get("success", False),
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "duration": (end_time - start_time).total_seconds(),
                        "stats": result.get("stats", {}),
                    }

                    if not result.get("success"):
                        result_data["error"] = result.get(
                            "error", "Unknown error"
                        )

                    results_queue.put(result_data)

        except Exception as e:
            results_queue.put(
                {
                    "config": process_name,
                    "success": False,
                    "error": str(e),
                    "start_time": datetime.now().isoformat(),
                }
            )

    def _collect_results(
        self, expected_processes: int, long_running_configs: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Recolecta los resultados de los procesos.

        Args:
            expected_processes: Número esperado de procesos
            long_running_configs: Lista de configuraciones de larga duración

        Returns:
            List[Dict]: Lista de resultados
        """
        results = []
        collected = 0

        # Esperar resultados de TODOS los procesos (corta y larga duración)
        while collected < expected_processes:
            try:
                # Esperar resultado con timeout
                result = self.results_queue.get(timeout=30)
                results.append(result)
                collected += 1

                config_name = result.get("config", "Unknown")
                success = result.get("success", False)
                is_long_running = result.get("long_running", False)

                if is_long_running:
                    status = result.get("status", "RUNNING")
                    self.logger.info(f"Process {config_name}: {status}")
                else:
                    status = "SUCCESS" if success else "FAILED"
                    self.logger.info(f"Process {config_name}: {status}")

                    if not success:
                        error = result.get("error", "Unknown error")
                        self.logger.error(
                            f"Process {config_name} error: {error}"
                        )
                    else:
                        stats = result.get("stats", {})
                        duration = result.get("duration", 0)
                        self.logger.info(
                            f"Process {config_name} completed in {duration:.2f}s"
                        )

                        if stats:
                            records = stats.get("records_transferred", 0)
                            databases = stats.get("databases_processed", 0)
                            measurements = stats.get(
                                "measurements_processed", 0
                            )
                            self.logger.info(
                                f"  - Databases: {databases}, Measurements: {measurements}, Records: {records}"
                            )

            except Exception as e:
                self.logger.warning(f"Timeout waiting for process result: {e}")
                break

        return results

    def _print_summary(self, results: List[Dict[str, Any]]) -> None:
        """
        Imprime un resumen de los resultados.

        Args:
            results: Lista de resultados
        """
        if not results:
            self.logger.info("No results to summarize")
            return

        successful = sum(1 for r in results if r.get("success", False))
        long_running = sum(1 for r in results if r.get("long_running", False))
        failed = len(results) - successful

        self.logger.info("=" * 60)
        self.logger.info("BACKUP SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total processes: {len(results)}")
        self.logger.info(f"Successful: {successful}")
        self.logger.info(f"Long-running (Scheduled): {long_running}")
        self.logger.info(f"Failed: {failed}")

        # Estadísticas totales
        total_records = 0
        total_databases = 0
        total_measurements = 0

        for result in results:
            if result.get("success") and not result.get("long_running", False):
                stats = result.get("stats", {})
                total_records += stats.get("records_transferred", 0)
                total_databases += stats.get("databases_processed", 0)
                total_measurements += stats.get("measurements_processed", 0)

        if total_records > 0 or total_databases > 0 or total_measurements > 0:
            self.logger.info(f"Total records transferred: {total_records}")
            self.logger.info(f"Total databases processed: {total_databases}")
            self.logger.info(
                f"Total measurements processed: {total_measurements}"
            )

        # Detalles de procesos de larga duración
        if long_running > 0:
            self.logger.info(
                "\nLong-running processes (will continue in background):"
            )
            for result in results:
                if result.get("long_running", False):
                    config = result.get("config", "Unknown")
                    status = result.get("status", "RUNNING")
                    self.logger.info(f"  - {config}: {status}")

        # Detalles de fallos
        if failed > 0:
            self.logger.info("\nFailed processes:")
            for result in results:
                if not result.get("success"):
                    config = result.get("config", "Unknown")
                    error = result.get("error", "Unknown error")
                    self.logger.error(f"  - {config}: {error}")

        self.logger.info("=" * 60)

    def run(self) -> int:
        """
        Ejecuta el orchestrator principal.

        Returns:
            int: Código de salida (0 = éxito, 1 = error)
        """
        start_time = datetime.now()

        self.logger.info("Starting InfluxDB Backup Orchestrator")
        self.logger.info(f"Configuration directory: {self.config_directory}")

        # Buscar archivos de configuración
        config_files = self._find_config_files()

        if not config_files:
            self.logger.error("No configuration files found")
            return 1

        self.logger.info(f"Found {len(config_files)} configuration files")

        # Validar archivos de configuración
        valid_configs = []
        for config_path in config_files:
            self.logger.info(f"Validating {os.path.basename(config_path)}...")
            if self._validate_config_file(config_path):
                valid_configs.append(config_path)
                self.logger.info(f"  ✓ Valid")
            else:
                self.logger.error(f"  ✗ Invalid")

        if not valid_configs:
            self.logger.error("No valid configuration files found")
            return 1

        self.logger.info(f"Starting {len(valid_configs)} backup processes...")

        # Iniciar procesos de backup
        for config_path in valid_configs:
            process_name = os.path.basename(config_path)

            process = Process(
                target=self._run_backup_process,
                args=(config_path, self.results_queue, self.shutdown_event),
                name=f"BackupProcess-{process_name}",
            )

            process.start()
            self.processes.append(process)

            self.logger.info(
                f"Started process for {process_name} (PID: {process.pid})"
            )

        # Esperar resultados
        self.logger.info("Waiting for backup processes to complete...")

        try:
            # Identificar procesos de larga duración
            long_running_configs = [
                config_path
                for config_path in valid_configs
                if self._is_long_running_process(config_path)
            ]

            results = self._collect_results(
                len(valid_configs), long_running_configs
            )

            # Identificar nombres de procesos de larga duración
            long_running_process_names = [
                f"BackupProcess-{os.path.basename(config_path)}"
                for config_path in long_running_configs
            ]

            # Esperar a que todos los procesos de corta duración terminen
            for process in self.processes:
                if process.name in long_running_process_names:
                    # No matar procesos de larga duración - dejarlos corriendo
                    self.logger.info(
                        f"Leaving long-running process {process.name} active (PID: {process.pid})"
                    )
                    continue

                if process.is_alive():
                    process.join(timeout=60)
                    if process.is_alive():
                        self.logger.warning(
                            f"Process {process.name} did not terminate, killing..."
                        )
                        process.terminate()
                        process.join(timeout=10)
                        if process.is_alive():
                            process.kill()

            # Mostrar resumen
            end_time = datetime.now()
            duration = end_time - start_time

            # Verificar si hay procesos de larga duración
            long_running_count = sum(
                1 for r in results if r.get("long_running", False)
            )

            if long_running_count > 0:
                self.logger.info(
                    f"Orchestrator completed in {duration.total_seconds():.2f} seconds"
                )
                self.logger.info(
                    f"{long_running_count} scheduled backup process(es) continue running in background"
                )
            else:
                self.logger.info(
                    f"All processes completed in {duration.total_seconds():.2f} seconds"
                )

            self._print_summary(results)

            # Si hay procesos de larga duración, mantener el orquestador vivo
            if long_running_count > 0:
                self.logger.info(
                    "Orchestrator will stay alive to monitor scheduled backup processes..."
                )
                self.logger.info("Press Ctrl+C to stop all processes and exit")

                try:
                    # Monitorear procesos de larga duración
                    while True:
                        time.sleep(60)  # Verificar cada minuto

                        # Verificar si algún proceso de larga duración ha terminado
                        active_processes = []
                        for process in self.processes:
                            if (
                                process.name in long_running_process_names
                                and process.is_alive()
                            ):
                                active_processes.append(process)
                            elif (
                                process.name in long_running_process_names
                                and not process.is_alive()
                            ):
                                self.logger.warning(
                                    f"Long-running process {process.name} has terminated unexpectedly"
                                )

                        # Si no quedan procesos de larga duración activos, salir
                        if not active_processes:
                            self.logger.info(
                                "All long-running processes have terminated. Exiting orchestrator."
                            )
                            break

                        # Log de estado cada 10 minutos
                        if hasattr(self, "_status_counter"):
                            self._status_counter += 1
                        else:
                            self._status_counter = 1

                        if self._status_counter % 10 == 0:
                            self.logger.info(
                                f"Orchestrator monitoring {len(active_processes)} active backup process(es)"
                            )

                except KeyboardInterrupt:
                    self.logger.info(
                        "Received interrupt signal, stopping all processes..."
                    )
                    self.shutdown_event.set()

                    # Terminar procesos de larga duración
                    for process in self.processes:
                        if (
                            process.name in long_running_process_names
                            and process.is_alive()
                        ):
                            self.logger.info(
                                f"Terminating long-running process {process.name}"
                            )
                            process.terminate()

                    # Esperar terminación con timeout
                    for process in self.processes:
                        if process.name in long_running_process_names:
                            process.join(timeout=10)
                            if process.is_alive():
                                self.logger.warning(
                                    f"Force killing process {process.name}"
                                )
                                process.kill()

                    return 130  # Código de salida para SIGINT

            # Determinar código de salida
            failed_count = sum(
                1 for r in results if not r.get("success", False)
            )
            return 1 if failed_count > 0 else 0

        except KeyboardInterrupt:
            self.logger.info("Received interrupt, shutting down...")
            self.shutdown_event.set()

            # Terminar procesos
            for process in self.processes:
                if process.is_alive():
                    process.terminate()

            # Esperar terminación
            for process in self.processes:
                process.join(timeout=10)
                if process.is_alive():
                    process.kill()

            return 130  # Código de salida para SIGINT

        except Exception as e:
            self.logger.error(f"Orchestrator error: {e}")
            return 1

    def cleanup(self) -> None:
        """Limpia recursos."""
        self.shutdown_event.set()

        # Terminar procesos activos
        for process in self.processes:
            if process.is_alive():
                process.terminate()

        # Esperar terminación
        for process in self.processes:
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
