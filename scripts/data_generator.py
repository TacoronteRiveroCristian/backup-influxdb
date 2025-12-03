"""
Generador de datos heterogeneos para InfluxDB (origen).
 - Backfill historico configurable.
 - Flujo en tiempo real continuo.
"""

import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone

from faker import Faker
from influxdb import InfluxDBClient


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _setup_logger() -> logging.Logger:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    return logging.getLogger("data-generator")


def make_client() -> InfluxDBClient:
    host = os.getenv("INFLUX_HOST", "influxdb-source")
    port = _env_int("INFLUX_PORT", 8086)
    user = os.getenv("INFLUX_USER") or None
    password = os.getenv("INFLUX_PASSWORD") or None
    ssl = os.getenv("INFLUX_SSL", "false").lower() == "true"
    return InfluxDBClient(
        host=host,
        port=port,
        username=user,
        password=password,
        ssl=ssl,
        verify_ssl=ssl,
        timeout=10,
    )


def ensure_database(client: InfluxDBClient, db_name: str) -> None:
    existing = {db["name"] for db in client.get_list_database()}
    if db_name not in existing:
        client.create_database(db_name)
    client.switch_database(db_name)


def random_point(fake: Faker, when: datetime) -> dict:
    measurement = random.choice(
        [
            "cpu_metrics",
            "memory_stats",
            "sensor_station",
            "weather_data",
            "app_events",
            "network_io",
        ]
    )
    tags = {
        "host": fake.hostname(),
        "region": random.choice(["us-east", "us-west", "eu-west", "ap-south"]),
        "env": random.choice(["dev", "staging", "prod"]),
        "service": random.choice(["api", "worker", "scheduler"]),
    }
    fields = {
        "value": round(random.uniform(0, 100), 3),
        "temperature": round(random.uniform(-10, 45), 2),
        "humidity": round(random.uniform(10, 100), 2),
        "status": random.choice(["ok", "warn", "error"]),
        "success": random.choice([True, False]),
        "error_code": random.choice([0, 0, 0, 500, 502, 503]),
        "note": fake.sentence(nb_words=6),
    }
    return {
        "measurement": measurement,
        "tags": tags,
        "time": when.isoformat(),
        "fields": fields,
    }


def backfill(client: InfluxDBClient, db_name: str, days: int, batch_size: int = 500):
    logger = logging.getLogger("data-generator")
    fake = Faker()
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    step = timedelta(minutes=5)
    points = []
    cursor = start
    written = 0
    while cursor < now:
        points.append(random_point(fake, cursor))
        if len(points) >= batch_size:
            client.write_points(points, batch_size=batch_size, time_precision="s")
            written += len(points)
            logger.info("Backfill progresivo: %s puntos escritos", written)
            points.clear()
        cursor += step
    if points:
        client.write_points(points, batch_size=batch_size, time_precision="s")
        written += len(points)
    logger.info("Backfill completado: %s puntos escritos en %s dias", written, days)


def stream_realtime(client: InfluxDBClient, db_name: str, batch_points: int):
    logger = logging.getLogger("data-generator")
    fake = Faker()
    heartbeat_sec = _env_int("LOG_HEARTBEAT_SEC", 10)
    last_heartbeat = time.monotonic()
    total = 0
    while True:
        now = datetime.now(timezone.utc)
        points = [random_point(fake, now) for _ in range(batch_points)]
        try:
            client.write_points(points, batch_size=batch_points, time_precision="s")
            total += len(points)
        except Exception as exc:  # pragma: no cover - runtime loop
            logger.warning("Error escribiendo puntos: %s", exc)
        if time.monotonic() - last_heartbeat >= heartbeat_sec:
            logger.info("Streaming: %s puntos enviados (batch=%s)", total, batch_points)
            last_heartbeat = time.monotonic()
        time.sleep(1)


def main():
    logger = _setup_logger()
    db_name = os.getenv("INFLUX_DB", "telemetry")
    backfill_days = _env_int("GENERATOR_BACKFILL_DAYS", 7)
    realtime_batch = _env_int("GENERATOR_REALTIME_BATCH", 25)

    client = make_client()
    ensure_database(client, db_name)

    logger.info("Insertando %s dias historicos en '%s'", backfill_days, db_name)
    backfill(client, db_name, backfill_days)
    logger.info("Backfill completo. Iniciando flujo en tiempo real...")

    stream_realtime(client, db_name, realtime_batch)


if __name__ == "__main__":
    main()
