"""
Ejecutor de backups entre dos instancias InfluxDB.
Soporta modos range e incremental (con estado local).
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from influxdb import InfluxDBClient

from src.classes.config_manager import ConfigManager


def _parse_duration(duration: str) -> Optional[timedelta]:
    if not duration:
        return None
    units = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 604800,
        "M": 2592000,  # aproximado 30 dias
        "y": 31536000,  # aproximado 365 dias
    }
    try:
        value, unit = int(duration[:-1]), duration[-1]
        factor = units.get(unit)
        if not factor:
            return None
        return timedelta(seconds=value * factor)
    except Exception:
        return None


def _to_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class BackupRunner:
    def __init__(self, config_path: str, state_path: str = "/var/log/backup_influxdb/state.json"):
        self.logger = logging.getLogger("backup-runner")
        self.config_path = config_path
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state: Dict[str, Dict[str, str]] = {}
        self._load_state()

        self.config_manager = ConfigManager(config_path)
        source_cfg = self.config_manager.get_source_config()
        dest_cfg = self.config_manager.get_destination_config()
        self.measurements_cfg = self.config_manager.get_measurements_config()
        self.options_cfg = self.config_manager.get_options_config()

        self.source_client = self._make_client(source_cfg["url"], source_cfg.get("user"), source_cfg.get("password"))
        self.dest_client = self._make_client(dest_cfg["url"], dest_cfg.get("user"), dest_cfg.get("password"))

        # Crear bases destino si no existen
        for db_map in source_cfg.get("databases", []):
            self._ensure_db(self.dest_client, db_map["destination"])

        self.field_obsolete_delta = _parse_duration(self.options_cfg.get("field_obsolete_threshold", ""))
        self.days_of_pagination = self.options_cfg.get("days_of_pagination", 7)
        self.backup_mode = self.options_cfg.get("backup_mode", "incremental")
        self.range_cfg = (self.options_cfg.get("range") or {})
        self.incremental_cfg = (self.options_cfg.get("incremental") or {})

    def _load_state(self) -> None:
        if self.state_path.exists():
            try:
                self.state = json.loads(self.state_path.read_text())
            except Exception:
                self.state = {}

    def _save_state(self) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=2))
        tmp.replace(self.state_path)

    @staticmethod
    def _parse_url(url: str) -> Tuple[str, int, bool]:
        parsed = urlparse(url)
        return parsed.hostname or "localhost", parsed.port or 8086, parsed.scheme == "https"

    def _make_client(self, url: str, user: Optional[str], password: Optional[str]) -> InfluxDBClient:
        host, port, ssl = self._parse_url(url)
        return InfluxDBClient(
            host=host,
            port=port,
            username=user or None,
            password=password or None,
            ssl=ssl,
            verify_ssl=ssl,
            timeout=self.options_cfg.get("timeout_client", 20),
        )

    def _ensure_db(self, client: InfluxDBClient, db_name: str) -> None:
        names = {db["name"] for db in client.get_list_database()}
        if db_name not in names:
            client.create_database(db_name)

    def _list_measurements(self, db_name: str) -> List[str]:
        include = self.measurements_cfg.get("include")
        exclude = self.measurements_cfg.get("exclude") or []
        if include:
            return include
        result = self.source_client.query("SHOW MEASUREMENTS", database=db_name)
        measures = [m["name"] for m in result.get_points()]
        return [m for m in measures if m not in exclude]

    def _should_skip_measurement(self, db_name: str, measurement: str) -> bool:
        if not self.field_obsolete_delta:
            return False
        query = f'SELECT * FROM "{measurement}" ORDER BY time DESC LIMIT 1'
        result = self.source_client.query(query, database=db_name)
        series = result.raw.get("series") if hasattr(result, "raw") else None
        if not series:
            return True
        last_time = series[0]["values"][0][0]
        last_dt = _to_datetime(last_time)
        return (datetime.now(timezone.utc) - last_dt) > self.field_obsolete_delta

    def _iter_windows(self, start: datetime, end: datetime) -> Iterable[Tuple[datetime, datetime]]:
        step = timedelta(days=self.days_of_pagination)
        cursor = start
        while cursor < end:
            window_end = min(cursor + step, end)
            yield cursor, window_end
            cursor = window_end

    def _extract_points(self, series: Dict, measurement: str) -> List[Dict]:
        tags = series.get("tags") or {}
        columns = series.get("columns", [])
        points = []
        for values in series.get("values", []):
            fields = {}
            time_val = None
            for col, val in zip(columns, values):
                if col == "time":
                    time_val = val
                    continue
                fields[col] = val
            if time_val:
                points.append(
                    {"measurement": measurement, "tags": tags, "time": time_val, "fields": fields}
                )
        return points

    def _copy_window(self, src_db: str, dst_db: str, measurement: str, start: datetime, end: datetime) -> int:
        query = (
            f'SELECT * FROM "{measurement}" '
            f"WHERE time >= '{start.isoformat()}' AND time < '{end.isoformat()}'"
        )
        result = self.source_client.query(query, database=src_db)
        series_list = result.raw.get("series") if hasattr(result, "raw") else []
        total = 0
        for series in series_list:
            points = self._extract_points(series, measurement)
            if not points:
                continue
            self.dest_client.write_points(
                points,
                database=dst_db,
                time_precision="ms",
                batch_size=5000,
            )
            total += len(points)
        return total

    def run(self) -> None:
        for db_map in self.config_manager.get_source_config().get("databases", []):
            src_db = db_map["name"]
            dst_db = db_map["destination"]
            self.logger.info("Procesando base de datos '%s' -> '%s'", src_db, dst_db)
            measurements = self._list_measurements(src_db)
            for measurement in measurements:
                if self._should_skip_measurement(src_db, measurement):
                    self.logger.info("Saltando medicion obsoleta: %s", measurement)
                    continue
                if self.backup_mode == "range":
                    self._process_range(src_db, dst_db, measurement)
                else:
                    self._process_incremental(src_db, dst_db, measurement)
        self._save_state()

    def _process_range(self, src_db: str, dst_db: str, measurement: str) -> None:
        start_str = self.range_cfg.get("start_date")
        end_str = self.range_cfg.get("end_date")
        if not start_str or not end_str:
            self.logger.warning("Modo range sin start/end, saltando %s", measurement)
            return
        start_dt = _to_datetime(start_str)
        end_dt = _to_datetime(end_str)
        copied = 0
        for win_start, win_end in self._iter_windows(start_dt, end_dt):
            copied += self._copy_window(src_db, dst_db, measurement, win_start, win_end)
        self.logger.info("Range %s: %s puntos copiados", measurement, copied)

    def _process_incremental(self, src_db: str, dst_db: str, measurement: str) -> None:
        last_ts = (
            self.state.get(src_db, {})
            .get(measurement, {})
            .get("last_ts")
        )
        start_dt = _to_datetime(last_ts) if last_ts else (datetime.now(timezone.utc) - timedelta(days=self.days_of_pagination))
        end_dt = datetime.now(timezone.utc)
        copied = 0
        for win_start, win_end in self._iter_windows(start_dt, end_dt):
            copied += self._copy_window(src_db, dst_db, measurement, win_start, win_end)
        self.state.setdefault(src_db, {}).setdefault(measurement, {})["last_ts"] = end_dt.isoformat()
        self.logger.info("Incremental %s: %s puntos copiados", measurement, copied)
