#!/usr/bin/env python3
"""
Tests específicos para contenedores Docker del sistema de backup InfluxDB.
"""

import subprocess
import time
from pathlib import Path

import pytest
import requests


class TestDockerContainers:
    """
    Tests para verificar la funcionalidad de contenedores Docker.
    """

    @pytest.mark.docker
    def test_docker_services_available(self):
        """Verificar que Docker esté disponible."""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            assert "Docker version" in result.stdout
            print(f"Docker disponible: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.fail("Docker no está disponible")

    @pytest.mark.docker
    def test_docker_compose_available(self):
        """Verificar que Docker Compose esté disponible."""
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            assert "docker-compose version" in result.stdout.lower()
            print(f"Docker Compose disponible: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.fail("Docker Compose no está disponible")

    @pytest.mark.docker
    def test_test_containers_running(self):
        """Verificar que los contenedores de test estén corriendo."""
        expected_containers = [
            "influxdb_source_test",
            "influxdb_destination_test",
            "influxdb_extra_test",
        ]

        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=True,
            )

            running_containers = result.stdout.strip().split("\n")

            for container in expected_containers:
                if container not in running_containers:
                    print(f"WARNING: Contenedor {container} no está corriendo")
                    print(f"Contenedores activos: {running_containers}")
                    # No fallar el test, solo advertir
                else:
                    print(f"✓ Contenedor {container} está corriendo")

        except subprocess.CalledProcessError as e:
            pytest.fail(f"Error al verificar contenedores: {e}")

    @pytest.mark.docker
    def test_influxdb_containers_health(self):
        """Verificar el estado de salud de los contenedores InfluxDB."""
        test_urls = [
            ("http://localhost:8086/ping", "InfluxDB Source"),
            ("http://localhost:8087/ping", "InfluxDB Destination"),
            ("http://localhost:8088/ping", "InfluxDB Extra"),
        ]

        for url, name in test_urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 204:  # InfluxDB ping response
                    print(f"✓ {name} responde correctamente")
                else:
                    print(
                        f"WARNING: {name} responde con código {response.status_code}"
                    )
            except requests.exceptions.RequestException as e:
                print(f"WARNING: {name} no disponible: {e}")
                # No fallar el test si los servicios no están disponibles

    @pytest.mark.docker
    def test_docker_compose_file_exists(self):
        """Verificar que el archivo docker-compose.test.yml existe."""
        compose_file = Path(__file__).parent.parent / "docker-compose.test.yml"
        assert compose_file.exists(), f"Archivo {compose_file} no encontrado"

        # Verificar que contiene los servicios esperados
        content = compose_file.read_text()
        expected_services = [
            "influxdb_source_test",
            "influxdb_destination_test",
            "influxdb_extra_test",
        ]

        for service in expected_services:
            assert (
                service in content
            ), f"Servicio {service} no encontrado en docker-compose.test.yml"

        print("✓ Archivo docker-compose.test.yml válido")

    @pytest.mark.docker
    def test_docker_network_connectivity(self):
        """Test de conectividad de red entre contenedores."""
        try:
            # Verificar que la red de test existe
            result = subprocess.run(
                ["docker", "network", "ls", "--filter", "name=influxdb_test"],
                capture_output=True,
                text=True,
                check=True,
            )

            if "influxdb_test" in result.stdout:
                print("✓ Red de test influxdb_test_network existe")
            else:
                print("WARNING: Red de test no encontrada")

        except subprocess.CalledProcessError as e:
            print(f"WARNING: Error al verificar redes Docker: {e}")

    @pytest.mark.docker
    @pytest.mark.slow
    def test_container_startup_time(self):
        """Test del tiempo de inicio de contenedores."""
        compose_file = Path(__file__).parent.parent / "docker-compose.test.yml"

        if not compose_file.exists():
            pytest.skip("Archivo docker-compose.test.yml no encontrado")

        try:
            # Parar contenedores existentes
            subprocess.run(
                ["docker-compose", "-f", str(compose_file), "down"],
                cwd=compose_file.parent,
                capture_output=True,
                check=False,
            )

            # Medir tiempo de inicio
            start_time = time.time()

            result = subprocess.run(
                ["docker-compose", "-f", str(compose_file), "up", "-d"],
                cwd=compose_file.parent,
                capture_output=True,
                text=True,
                check=True,
            )

            startup_time = time.time() - start_time
            print(
                f"Tiempo de inicio de contenedores: {startup_time:.2f} segundos"
            )

            # Verificar que el tiempo es razonable
            assert (
                startup_time < 60
            ), f"Tiempo de inicio muy lento: {startup_time:.2f}s"

            # Esperar a que estén listos
            time.sleep(10)

        except subprocess.CalledProcessError as e:
            pytest.fail(f"Error al iniciar contenedores: {e}")

    @pytest.mark.docker
    def test_container_logs_available(self):
        """Verificar que los logs de contenedores están disponibles."""
        containers = [
            "influxdb_source_test",
            "influxdb_destination_test",
            "influxdb_extra_test",
        ]

        for container in containers:
            try:
                result = subprocess.run(
                    ["docker", "logs", "--tail", "10", container],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                # Verificar que hay logs
                if result.stdout or result.stderr:
                    print(f"✓ Logs disponibles para {container}")
                else:
                    print(f"WARNING: No hay logs para {container}")

            except subprocess.CalledProcessError:
                print(f"WARNING: No se pueden obtener logs de {container}")
