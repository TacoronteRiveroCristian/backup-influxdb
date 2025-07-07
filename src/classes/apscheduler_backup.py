"""
APScheduler-based Backup Scheduler
==================================

Scheduler avanzado usando APScheduler con mejores características:
- Prevención automática de solapamientos
- Mejor manejo de errores y reintentos
- Persistencia de jobs
- Timezone support
- Event listeners para monitoreo
"""

import logging
import signal
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
)
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from ..utils import get_process_id


class APSchedulerError(Exception):
    """Excepción para errores del APScheduler"""

    pass


class APBackupScheduler:
    """
    Scheduler avanzado para backups usando APScheduler.

    Características:
    - Prevención automática de overlapping jobs
    - Mejor error handling y recovery
    - Event listeners para monitoreo
    - Configuración flexible
    """

    def __init__(self, config_name: str, logger: logging.Logger):
        """
        Inicializa el scheduler.

        Args:
            config_name: Nombre de la configuración
            logger: Logger para mensajes
        """
        self.config_name = config_name
        self.logger = logger
        self.process_id = get_process_id()

        # Configurar APScheduler
        jobstores = {"default": MemoryJobStore()}

        executors = {
            "default": ThreadPoolExecutor(max_workers=1)  # Un job a la vez
        }

        job_defaults = {
            "coalesce": True,  # Combinar jobs atrasados
            "max_instances": 1,  # Solo una instancia por job
            "misfire_grace_time": 300,  # 5 minutos de gracia para jobs atrasados
        }

        self.scheduler = BlockingScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

        # Configurar listeners para monitoreo
        self._setup_listeners()

        # Configurar señales para parada graceful
        self._setup_signal_handlers()

        # Estado
        self.is_running = False
        self.current_job_id = None

    def _setup_listeners(self) -> None:
        """Configura listeners para eventos del scheduler."""

        def job_listener(event):
            """Listener para eventos de jobs."""
            if event.exception:
                self.logger.error(
                    f"Job {event.job_id} failed: {event.exception}"
                )
                # Aquí podrías implementar lógica de reintentos o notificaciones
            else:
                self.logger.info(f"Job {event.job_id} completed successfully")

        def job_missed_listener(event):
            """Listener para jobs perdidos."""
            self.logger.warning(f"Job {event.job_id} missed its scheduled time")

        self.scheduler.add_listener(
            job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        self.scheduler.add_listener(job_missed_listener, EVENT_JOB_MISSED)

    def _setup_signal_handlers(self) -> None:
        """Configura los manejadores de señales."""

        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, stopping scheduler...")
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def schedule_backup(
        self, cron_expr: str, backup_function: Callable, *args, **kwargs
    ) -> None:
        """
        Programa un backup usando una expresión cron.

        Args:
            cron_expr: Expresión cron
            backup_function: Función de backup a ejecutar
            *args: Argumentos para la función
            **kwargs: Argumentos nombrados para la función
        """

        # Crear wrapper para mejor logging
        def backup_wrapper():
            start_time = datetime.now()
            self.logger.info(f"=== SCHEDULED BACKUP STARTED ===")
            self.logger.info(f"Config: {self.config_name}")
            self.logger.info(f"Start time: {start_time}")

            try:
                result = backup_function(*args, **kwargs)

                end_time = datetime.now()
                duration = end_time - start_time

                self.logger.info(f"=== SCHEDULED BACKUP COMPLETED ===")
                self.logger.info(f"Duration: {duration}")
                self.logger.info(f"Result: {result}")

                return result

            except Exception as e:
                end_time = datetime.now()
                duration = end_time - start_time

                self.logger.error(f"=== SCHEDULED BACKUP FAILED ===")
                self.logger.error(f"Duration: {duration}")
                self.logger.error(f"Error: {e}")
                self.logger.exception("Full traceback:")

                raise

        # Validar expresión cron
        try:
            trigger = CronTrigger.from_crontab(cron_expr, timezone="UTC")
        except Exception as e:
            raise APSchedulerError(
                f"Invalid cron expression '{cron_expr}': {e}"
            )

        # Agregar job
        self.current_job_id = f"backup_{self.config_name}"
        self.scheduler.add_job(
            backup_wrapper,
            trigger=trigger,
            id=self.current_job_id,
            name=f"Backup job for {self.config_name}",
            replace_existing=True,
        )

        # Log next run time
        try:
            job = self.scheduler.get_job(self.current_job_id)
            next_run = getattr(job, "next_run_time", "Unknown")
            self.logger.info(f"Backup scheduled with cron: {cron_expr}")
            self.logger.info(f"Next run: {next_run}")
        except Exception as e:
            self.logger.warning(f"Could not get next run time: {e}")
            self.logger.info(f"Backup scheduled with cron: {cron_expr}")

    def start(self) -> None:
        """Inicia el scheduler."""
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return

        self.logger.info(
            f"Scheduler loop started for config: {self.config_name}"
        )
        self.is_running = True

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Scheduler interrupted")
            self.stop()
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
            self.is_running = False
            raise

    def stop(self) -> None:
        """Detiene el scheduler."""
        if not self.is_running:
            return

        self.logger.info("Stopping scheduler...")

        try:
            self.scheduler.shutdown(wait=True)
        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {e}")

        self.is_running = False
        self.logger.info("Scheduler stopped")

    def get_status(self) -> Dict[str, Any]:
        """
        Retorna el estado actual del scheduler.

        Returns:
            Dict: Estado del scheduler
        """
        status = {
            "config_name": self.config_name,
            "is_running": self.is_running,
            "process_id": self.process_id,
            "scheduler_state": self.scheduler.state if self.scheduler else None,
            "jobs": [],
        }

        if self.scheduler and self.is_running:
            for job in self.scheduler.get_jobs():
                status["jobs"].append(
                    {
                        "id": job.id,
                        "name": job.name,
                        "next_run_time": getattr(
                            job, "next_run_time", "Unknown"
                        ),
                        "trigger": str(job.trigger),
                    }
                )

        return status

    def reschedule_backup(self, new_cron_expr: str) -> None:
        """
        Reprograma el backup con una nueva expresión cron.

        Args:
            new_cron_expr: Nueva expresión cron
        """
        if not self.current_job_id:
            raise APSchedulerError("No job currently scheduled")

        try:
            trigger = CronTrigger.from_crontab(new_cron_expr, timezone="UTC")
        except Exception as e:
            raise APSchedulerError(
                f"Invalid cron expression '{new_cron_expr}': {e}"
            )

        self.scheduler.modify_job(self.current_job_id, trigger=trigger)

        try:
            job = self.scheduler.get_job(self.current_job_id)
            next_run = getattr(job, "next_run_time", "Unknown")
            self.logger.info(f"Job rescheduled with cron: {new_cron_expr}")
            self.logger.info(f"Next run: {next_run}")
        except Exception as e:
            self.logger.warning(
                f"Could not get next run time after rescheduling: {e}"
            )
            self.logger.info(f"Job rescheduled with cron: {new_cron_expr}")

    def run_once(self, backup_function: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta un backup una sola vez (modo incremental sin schedule).

        Args:
            backup_function: Función de backup
            *args: Argumentos para la función
            **kwargs: Argumentos nombrados

        Returns:
            Any: Resultado de la función de backup
        """
        start_time = datetime.now()

        self.logger.info(f"=== SINGLE BACKUP STARTED ===")
        self.logger.info(f"Config: {self.config_name}")
        self.logger.info(f"Start time: {start_time}")

        try:
            result = backup_function(*args, **kwargs)

            end_time = datetime.now()
            duration = end_time - start_time

            self.logger.info(f"=== SINGLE BACKUP COMPLETED ===")
            self.logger.info(f"Duration: {duration}")

            return result

        except Exception as e:
            end_time = datetime.now()
            duration = end_time - start_time

            self.logger.error(f"=== SINGLE BACKUP FAILED ===")
            self.logger.error(f"Duration: {duration}")
            self.logger.error(f"Error: {e}")
            self.logger.exception("Full traceback:")

            raise

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def __repr__(self) -> str:
        """Representación en string del scheduler."""
        return (
            f"APBackupScheduler(config='{self.config_name}', "
            f"running={self.is_running})"
        )
