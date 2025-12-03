import argparse
import logging
from pathlib import Path

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.classes.backup_runner import BackupRunner
from src.classes.config_manager import ConfigManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ejecutor de backups InfluxDB")
    parser.add_argument(
        "--config",
        default="/config",
        help="Ruta a archivo o directorio con .yaml de configuracion",
    )
    parser.add_argument(
        "--state",
        default="/var/log/backup_influxdb/state.json",
        help="Ruta al fichero de estado incremental",
    )
    return parser.parse_args()


def iter_configs(path: Path):
    if path.is_dir():
        yield from sorted(
            p
            for p in path.glob("*.yaml")
            if not p.name.endswith(".template.yaml") and "template" not in p.name
        )
    else:
        yield path


def run_once(config_path: Path, state_path: Path, logger: logging.Logger):
    try:
        runner = BackupRunner(str(config_path), state_path=str(state_path))
        runner.run()
    except Exception as exc:
        logger.error("Error ejecutando backup para %s: %s", config_path, exc)


def schedule_config(
    scheduler: BlockingScheduler, config_path: Path, state_path: Path, logger: logging.Logger
):
    cfg = ConfigManager(str(config_path))
    options = cfg.get_options_config() or {}
    mode = options.get("backup_mode", "incremental")
    schedule_expr = (options.get("incremental") or {}).get("schedule", "")

    if mode == "incremental" and schedule_expr:
        try:
            trigger = CronTrigger.from_crontab(schedule_expr)
            scheduler.add_job(
                run_once,
                trigger=trigger,
                args=[config_path, state_path, logger],
                id=str(config_path),
                replace_existing=True,
                coalesce=True,
                misfire_grace_time=60,
            )
            logger.info(
                "Programado backup incremental %s con CRON '%s'", config_path, schedule_expr
            )
        except Exception as exc:
            logger.error(
                "CRON '%s' invalido para %s: %s. Ejecutando una vez.", schedule_expr, config_path, exc
            )
            run_once(config_path, state_path, logger)
    else:
        logger.info("Ejecutando backup on-demand para %s (modo=%s)", config_path, mode)
        run_once(config_path, state_path, logger)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    args = parse_args()
    cfg_path = Path(args.config)
    configs = list(iter_configs(cfg_path))
    if not configs:
        raise SystemExit(f"No se encontraron configs en {cfg_path}")

    logger = logging.getLogger("backup-runner")

    # Ejecutar/scheduler por config
    scheduler = BlockingScheduler(
        executors={"default": ThreadPoolExecutor(max_workers=max(4, len(configs)))}  # paralelo por config
    )
    for cfg in configs:
        schedule_config(scheduler, cfg, Path(args.state), logger)

    # Si no hay ningun job programado (solo ejecuciones on-demand), terminar
    if not scheduler.get_jobs():
        return 0

    logger.info("Scheduler iniciado con %s jobs", len(scheduler.get_jobs()))
    scheduler.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
