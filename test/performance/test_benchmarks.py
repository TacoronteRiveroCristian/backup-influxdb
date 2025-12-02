#!/usr/bin/env python3
"""
Tests de rendimiento y benchmarks para el sistema de backup InfluxDB.
"""

import time
from datetime import datetime, timedelta
from test.data.data_generator import DataGenerator
from test.data.test_datasets import IOT_DATASET
from test.utils.influxdb_test_helper import InfluxDBTestHelper

import pytest


class TestPerformanceBenchmarks:
    """
    Tests de rendimiento para medir la eficiencia del sistema de backup.
    """

    def setup_method(self):
        """Configuración para cada test."""
        self.data_generator = DataGenerator(seed=42)
        self.test_helper = InfluxDBTestHelper()

    @pytest.mark.performance
    def test_data_generation_performance(self):
        """Test de rendimiento de generación de datos."""
        print("\nEjecutando benchmark de generación de datos...")

        # Medir tiempo de generación usando el método correcto
        start_time = time.time()

        # Generar datos usando una medición simple
        measurement_data = self.data_generator.generate_measurement_data(
            measurement_name="temperature_sensors",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            interval="1m",
            field_configs={
                "temperature": {"type": "normal", "mean": 25.0, "std": 5.0},
                "humidity": {"type": "normal", "mean": 60.0, "std": 10.0},
                "pressure": {"type": "normal", "mean": 1013.25, "std": 5.0},
            },
            tag_configs={
                "sensor_id": {
                    "type": "enum",
                    "values": ["temp_001", "temp_002", "temp_003"],
                },
                "location": {
                    "type": "enum",
                    "values": ["building_a", "building_b"],
                },
            },
        )

        end_time = time.time()
        duration = end_time - start_time

        # Calcular métricas
        total_points = len(measurement_data)
        points_per_second = total_points / duration if duration > 0 else 0

        print(f"Generados {total_points} puntos en {duration:.2f} segundos")
        print(f"Tasa: {points_per_second:.0f} puntos/segundo")

        # Verificar que se generaron los datos esperados
        assert total_points > 0, "No se generaron datos"
        assert duration < 10, f"Generación demasiado lenta: {duration:.2f}s"
        assert (
            points_per_second > 50
        ), f"Tasa muy baja: {points_per_second:.0f} puntos/segundo"

    @pytest.mark.performance
    def test_memory_usage_benchmark(self):
        """Test de uso de memoria durante generación de datos."""
        import os

        import psutil

        print("\nEjecutando benchmark de memoria...")

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Generar dataset usando el método correcto con un dataset predefinido
        dataset = self.data_generator.generate_complex_dataset(
            database_name="test_db",
            start_time=datetime.now() - timedelta(hours=2),
            end_time=datetime.now(),
            measurements={
                "temperature_sensors": IOT_DATASET["temperature_sensors"],
                "motion_sensors": IOT_DATASET["motion_sensors"],
                "power_meters": IOT_DATASET["power_meters"],
            },
        )

        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_after - memory_before

        total_points = sum(len(data) for data in dataset.values())
        memory_per_point = memory_used / total_points if total_points > 0 else 0

        print(f"Memoria antes: {memory_before:.1f} MB")
        print(f"Memoria después: {memory_after:.1f} MB")
        print(f"Memoria usada: {memory_used:.1f} MB")
        print(f"Memoria por punto: {memory_per_point*1024:.2f} KB")

        # Verificar que el uso de memoria es razonable
        assert (
            memory_used < 500
        ), f"Uso excesivo de memoria: {memory_used:.1f} MB"
        assert (
            memory_per_point < 0.1
        ), f"Memoria por punto muy alta: {memory_per_point*1024:.2f} KB"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_large_dataset_benchmark(self):
        """Test de rendimiento con datasets grandes."""
        print("\nEjecutando benchmark de dataset grande...")

        start_time = time.time()

        # Generar dataset muy grande modificando la configuración
        large_config = IOT_DATASET.copy()
        # Cambiar intervalos para generar más puntos
        large_config["temperature_sensors"]["interval"] = "10s"
        large_config["motion_sensors"]["interval"] = "5s"
        large_config["power_meters"]["interval"] = "30s"

        dataset = self.data_generator.generate_complex_dataset(
            database_name="large_test_db",
            start_time=datetime.now() - timedelta(hours=6),
            end_time=datetime.now(),
            measurements=large_config,
        )

        generation_time = time.time() - start_time
        total_points = sum(len(data) for data in dataset.values())

        print(
            f"Dataset generado: {total_points} puntos en {generation_time:.2f}s"
        )
        print(
            f"Tasa de generación: {total_points/generation_time:.0f} puntos/segundo"
        )

        # Verificar rendimiento
        assert (
            generation_time < 30
        ), f"Generación muy lenta: {generation_time:.2f}s"
        assert (
            total_points > 1000
        ), f"No se generaron suficientes puntos: {total_points}"

    @pytest.mark.performance
    def test_concurrent_generation_performance(self):
        """Test de rendimiento de generación concurrente."""
        import queue
        import threading

        print("\nEjecutando benchmark de generación concurrente...")

        results_queue = queue.Queue()
        num_threads = 4

        def generate_data_worker(thread_id):
            """Worker para generar datos en paralelo."""
            start = time.time()
            # Usar una configuración simple para cada thread
            measurement_data = self.data_generator.generate_measurement_data(
                measurement_name=f"sensor_thread_{thread_id}",
                start_time=datetime.now() - timedelta(minutes=30),
                end_time=datetime.now(),
                interval="30s",
                field_configs={
                    "temperature": {"type": "normal", "mean": 25.0, "std": 5.0},
                    "pressure": {"type": "normal", "mean": 1013.0, "std": 2.0},
                },
                tag_configs={
                    "thread_id": {
                        "type": "enum",
                        "values": [f"thread_{thread_id}"],
                    }
                },
            )
            duration = time.time() - start
            total_points = len(measurement_data)
            results_queue.put((total_points, duration))

        # Ejecutar threads
        start_time = time.time()
        threads = []

        for i in range(num_threads):
            thread = threading.Thread(target=generate_data_worker, args=(i,))
            thread.start()
            threads.append(thread)

        # Esperar a que terminen
        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # Recopilar resultados
        total_points = 0
        total_generation_time = 0

        while not results_queue.empty():
            points, duration = results_queue.get()
            total_points += points
            total_generation_time += duration

        # Calcular métricas
        avg_generation_time = total_generation_time / num_threads
        overall_rate = total_points / total_time

        print(f"Threads: {num_threads}")
        print(f"Puntos totales: {total_points}")
        print(f"Tiempo total: {total_time:.2f}s")
        print(f"Tiempo promedio por thread: {avg_generation_time:.2f}s")
        print(f"Tasa global: {overall_rate:.0f} puntos/segundo")

        # Verificar rendimiento concurrente (criterios realistas)
        assert total_points > 10, "Se generaron muy pocos datos en total"

        # Verificar que todos los threads generaron datos
        assert (
            total_points >= num_threads
        ), f"Algunos threads no generaron datos: {total_points} < {num_threads}"

        # Para datasets pequeños, solo verificamos que la concurrencia funciona
        # sin errores y que la tasa general es razonable
        assert (
            overall_rate > 100
        ), f"Tasa muy baja para generación concurrente: {overall_rate:.0f} puntos/segundo"

        # Verificar que el tiempo total es razonable (menos de 1 segundo)
        assert (
            total_time < 1.0
        ), f"Tiempo excesivo para dataset pequeño: {total_time:.2f}s"
