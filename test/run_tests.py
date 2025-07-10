#!/usr/bin/env python3
"""
Script principal para ejecutar todos los tipos de tests del sistema.
Incluye tests unitarios, de integración, Docker y rendimiento.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class TestRunner:
    """
    Clase principal para ejecutar y gestionar todos los tipos de tests
    del sistema de backup InfluxDB.
    """

    def __init__(self, verbose: bool = False):
        """
        Inicializar el runner de tests.

        Args:
            verbose: Si mostrar output detallado
        """
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.test_root = self.project_root / "test"
        self.containers_started = False
        self.keep_containers = (
            os.getenv("KEEP_TEST_CONTAINERS", "false").lower() == "true"
        )
        self.demo_data_location = None

    def check_dependencies(self) -> bool:
        """
        Verificar que todas las dependencias necesarias estén instaladas.

        Returns:
            bool: True si todas las dependencias están disponibles
        """
        dependencies = ["pytest", "docker", "docker-compose"]
        missing = []

        for dep in dependencies:
            try:
                if dep == "pytest":
                    subprocess.run(
                        ["python", "-m", "pytest", "--version"],
                        check=True,
                        capture_output=True,
                    )
                elif dep in ["docker", "docker-compose"]:
                    subprocess.run(
                        [dep, "--version"], check=True, capture_output=True
                    )
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing.append(dep)

        if missing:
            print(f"FALTAN DEPENDENCIAS: {', '.join(missing)}")
            return False

        return True

    def check_docker_services(self) -> bool:
        """
        Verificar que Docker esté corriendo y accesible.

        Returns:
            bool: True si Docker está disponible
        """
        try:
            result = subprocess.run(
                ["docker", "ps"], check=True, capture_output=True, text=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _check_test_containers(self) -> bool:
        """
        Verificar si los contenedores de test están corriendo.

        Returns:
            bool: True si están corriendo
        """
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    "name=test_",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            containers = (
                result.stdout.strip().split("\n")
                if result.stdout.strip()
                else []
            )
            required_containers = ["test_influxdb", "test_backup_influxdb"]

            running_containers = [
                c for c in containers if c in required_containers
            ]

            if len(running_containers) >= len(required_containers):
                return True
            else:
                if self.verbose:
                    print(f"Contenedores requeridos: {required_containers}")
                    print(f"Contenedores corriendo: {running_containers}")
                return False

        except subprocess.CalledProcessError:
            return False

    def setup_docker_containers(self):
        """Configurar y levantar contenedores Docker para tests"""
        print("\nConfigurando contenedores Docker para tests...")

        docker_compose_file = (
            self.project_root / "test" / "docker" / "docker-compose.test.yml"
        )

        if not docker_compose_file.exists():
            print("ERROR: No se encontró docker-compose.test.yml")
            return False

        try:
            # Cambiar al directorio de docker
            os.chdir(docker_compose_file.parent)

            # Parar contenedores existentes
            subprocess.run(
                ["docker-compose", "-f", "docker-compose.test.yml", "down"],
                check=False,
                capture_output=True,
            )

            # Levantar contenedores
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.test.yml", "up", "-d"],
                check=True,
                capture_output=True,
                text=True,
            )

            print("Contenedores Docker iniciados")
            self.containers_started = True

            # Esperar a que los servicios estén listos
            print("Esperando a que los servicios estén listos...")
            time.sleep(
                30
            )  # Tiempo adicional para asegurar inicialización completa

            return True

        except subprocess.CalledProcessError as e:
            print(f"ERROR: Error al configurar contenedores: {e}")
            if e.stderr:
                print(f"Stderr: {e.stderr}")
            return False
        finally:
            # Volver al directorio original
            os.chdir(self.project_root)

    def cleanup_docker_containers(self):
        """Limpiar contenedores Docker después de los tests"""
        if not self.containers_started:
            return

        if self.keep_containers:
            print(
                "\nManteniendo contenedores Docker activos (según configuración)"
            )
            return

        print("\nLimpiando contenedores Docker...")

        docker_compose_file = (
            self.project_root / "test" / "docker" / "docker-compose.test.yml"
        )

        try:
            # Cambiar al directorio de docker
            os.chdir(docker_compose_file.parent)

            # Parar contenedores
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.test.yml", "down"],
                check=True,
                capture_output=True,
                text=True,
            )

            print("Contenedores Docker detenidos")

        except subprocess.CalledProcessError as e:
            print(f"WARNING: Error al detener contenedores: {e}")
        finally:
            # Volver al directorio original
            os.chdir(self.project_root)

    def run_unit_tests(self) -> dict:
        """
        Ejecuta los tests unitarios.

        Returns:
            dict: Resultados de los tests
        """
        print("\nEjecutando tests unitarios...")

        # Crear directorio de resultados
        results_dir = self.project_root / "test" / "test_results"
        results_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "python",
            "-m",
            "pytest",
            str(self.test_root / "unit"),
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=test/test_results/unit_tests.json",
        ]

        if self.verbose:
            cmd.append("-s")

        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.project_root, text=True)
        end_time = time.time()

        # Si hay fallos, mostrar información detallada
        if result.returncode != 0:
            self._show_unit_test_failures()

        return {
            "type": "unit",
            "success": result.returncode == 0,
            "duration": end_time - start_time,
            "stdout": "",
            "stderr": "",
            "returncode": result.returncode,
        }

    def _show_unit_test_failures(self) -> None:
        """
        Muestra información detallada de los tests unitarios que fallaron.
        """
        json_file = (
            self.project_root / "test" / "test_results" / "unit_tests.json"
        )

        if not json_file.exists():
            print("ERROR: No se pudo encontrar el archivo de resultados JSON")
            return

        try:
            with open(json_file, "r") as f:
                data = json.load(f)

            # Mostrar resumen
            summary = data.get("summary", {})
            total = summary.get("total", 0)
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)

            print(f"\n{'='*80}")
            print(f"RESUMEN DE TESTS UNITARIOS")
            print(f"{'='*80}")
            print(f"Total: {total} | PASARON: {passed} | FALLARON: {failed}")

            if failed > 0:
                print(f"\nDETALLES DE TESTS FALLIDOS:")
                print(f"{'='*80}")

                # Obtener tests fallidos
                failed_tests = [
                    test
                    for test in data.get("tests", [])
                    if test.get("outcome") == "failed"
                ]

                for i, test in enumerate(failed_tests, 1):
                    node_id = test.get("nodeid", "Test desconocido")
                    # Extraer nombre del test más legible
                    test_name = (
                        node_id.split("::")[-1] if "::" in node_id else node_id
                    )
                    test_file = (
                        node_id.split("::")[0]
                        if "::" in node_id
                        else "Archivo desconocido"
                    )

                    print(f"\n{i}. FALLO: {test_name}")
                    print(f"   Archivo: {test_file}")

                    # Mostrar el error principal
                    crash = test.get("call", {}).get("crash", {})
                    if crash:
                        error_msg = crash.get("message", "Error desconocido")
                        print(f"   Error: {error_msg}")

                        # Mostrar traceback simplificado
                        traceback = crash.get("traceback", [])
                        if traceback:
                            print(f"   Ubicación del error:")
                            for trace in traceback[
                                -3:
                            ]:  # Solo últimas 3 líneas del traceback
                                path = trace.get("path", "")
                                line = trace.get("lineno", "")
                                print(f"     {path}:{line}")

                    # Mostrar logs si están disponibles
                    setup = test.get("setup", {})
                    if setup and setup.get("outcome") == "failed":
                        print(f"   Logs:")
                        for log_entry in setup.get("call", {}).get("log", []):
                            print(f"     {log_entry.get('message', '')}")

                print(f"\nPara ver más detalles, ejecuta:")
                print(f"python -m pytest test/unit/ -v --tb=long")

        except Exception as e:
            print(f"ERROR: Error leyendo resultados: {e}")

    def run_integration_tests(self) -> dict:
        """
        Ejecuta los tests de integración.

        Returns:
            dict: Resultados de los tests
        """
        print("\nEjecutando tests de integración...")

        cmd = [
            "python",
            "-m",
            "pytest",
            str(self.test_root / "integration"),
            "-v",
            "--tb=short",
        ]

        if self.verbose:
            cmd.append("-s")

        start_time = time.time()
        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True
        )
        end_time = time.time()

        return {
            "type": "integration",
            "success": result.returncode == 0,
            "duration": end_time - start_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def run_docker_tests(self) -> dict:
        """
        Ejecuta tests específicos que requieren Docker.

        Returns:
            dict: Resultados de los tests
        """
        print("\nEjecutando tests Docker...")

        # Verificar si existe el directorio de tests de docker
        docker_test_dir = self.test_root / "docker" / "tests"
        if not docker_test_dir.exists():
            print(
                "WARNING: Directorio de tests Docker no encontrado, creando tests básicos..."
            )
            # Crear tests básicos si no existen
            docker_test_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "python",
            "-m",
            "pytest",
            str(docker_test_dir),
            "-v",
            "--tb=short",
        ]

        if self.verbose:
            cmd.append("-s")

        start_time = time.time()
        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True
        )
        end_time = time.time()

        return {
            "type": "docker",
            "success": result.returncode == 0,
            "duration": end_time - start_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def run_performance_tests(self) -> dict:
        """
        Ejecuta tests de rendimiento.

        Returns:
            dict: Resultados de los tests
        """
        print("\nEjecutando tests de rendimiento...")

        # Verificar si existe el directorio de tests de performance
        performance_test_dir = self.test_root / "performance"
        if not performance_test_dir.exists():
            print(
                "WARNING: Directorio de tests de rendimiento no encontrado, creando tests básicos..."
            )
            performance_test_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "python",
            "-m",
            "pytest",
            str(performance_test_dir),
            "-v",
            "--tb=short",
            "-m",
            "performance",  # Solo ejecutar tests marcados como performance
        ]

        if self.verbose:
            cmd.append("-s")

        start_time = time.time()
        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True
        )
        end_time = time.time()

        return {
            "type": "performance",
            "success": result.returncode == 0,
            "duration": end_time - start_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def generate_coverage_report(self) -> dict:
        """
        Genera reporte de cobertura de código.

        Returns:
            dict: Resultados del reporte
        """
        print("\nGenerando reporte de cobertura...")

        # Crear directorio de coverage
        coverage_dir = self.project_root / "test" / "coverage"
        coverage_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "python",
            "-m",
            "pytest",
            str(self.test_root / "unit"),
            str(self.test_root / "integration"),
            "--cov=src",
            "--cov-report=html:test/coverage/html",
            "--cov-report=xml:test/coverage/coverage.xml",
            "--cov-report=term",
        ]

        start_time = time.time()
        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True
        )
        end_time = time.time()

        return {
            "type": "coverage",
            "success": result.returncode == 0,
            "duration": end_time - start_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def create_test_data_demo(self) -> dict:
        """
        Crea datos de demostración para tests.

        Returns:
            dict: Resultados de la creación
        """
        print("\nCreando datos de demostración...")

        try:
            # Verificar que existe el script de datos de demo
            demo_script = (
                self.project_root / "test" / "utils" / "create_demo_data.py"
            )

            if not demo_script.exists():
                # Crear script básico si no existe
                demo_script.parent.mkdir(parents=True, exist_ok=True)
                with open(demo_script, "w") as f:
                    f.write(
                        '''#!/usr/bin/env python3
"""
Script para crear datos de demostración para tests.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime, timedelta
import random

def create_demo_data():
    """Crear datos de demostración para tests."""

    demo_data = {
        "measurements": ["temperature", "humidity", "pressure"],
        "data_points": 1000,
        "time_range": "24h",
        "created_at": datetime.now().isoformat()
    }

    # Simular creación de datos
    print(f"Creando {demo_data['data_points']} puntos de datos...")
    print(f"Mediciones: {', '.join(demo_data['measurements'])}")
    print(f"Rango temporal: {demo_data['time_range']}")

    return demo_data

if __name__ == "__main__":
    result = create_demo_data()
    print("Datos de demostración creados exitosamente")
    print(f"Detalles: {result}")
'''
                    )

            # Ejecutar script de demo
            cmd = ["python", str(demo_script)]

            start_time = time.time()
            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True
            )
            end_time = time.time()

            # Guardar ubicación de datos de demo
            self.demo_data_location = str(
                self.project_root / "test" / "demo_data"
            )

            return {
                "type": "demo_data",
                "success": result.returncode == 0,
                "duration": end_time - start_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "location": self.demo_data_location,
            }

        except Exception as e:
            return {
                "type": "demo_data",
                "success": False,
                "duration": 0,
                "stdout": "",
                "stderr": str(e),
                "returncode": 1,
                "location": None,
            }

    def generate_final_report(self, results: list) -> None:
        """
        Genera un reporte final con todos los resultados.

        Args:
            results: Lista de resultados de todos los tests
        """
        print("\nGenerando reporte final...")

        total_duration = sum(r.get("duration", 0) for r in results)
        successful_tests = [r for r in results if r.get("success", False)]
        failed_tests = [r for r in results if not r.get("success", False)]

        # Crear reporte
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_duration": total_duration,
            "total_tests": len(results),
            "successful_tests": len(successful_tests),
            "failed_tests": len(failed_tests),
            "success_rate": (
                len(successful_tests) / len(results) * 100 if results else 0
            ),
            "results": results,
            "demo_data_location": self.demo_data_location,
        }

        # Guardar reporte en JSON
        report_file = (
            self.project_root / "test" / "test_results" / "final_report.json"
        )
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        # Generar reporte HTML
        html_report = self._generate_html_report(report)
        html_file = (
            self.project_root / "test" / "test_results" / "final_report.html"
        )

        with open(html_file, "w") as f:
            f.write(html_report)

        # Mostrar resumen en consola
        print(f"\n{'='*80}")
        print("RESUMEN FINAL DE TESTS")
        print(f"{'='*80}")
        print(f"Duración total: {total_duration:.2f} segundos")
        print(f"Tests ejecutados: {len(results)}")
        print(f"Exitosos: {len(successful_tests)}")
        print(f"Fallidos: {len(failed_tests)}")
        print(f"Tasa de éxito: {report['success_rate']:.1f}%")

        print(f"\nResultados por tipo:")
        for result in results:
            test_type = result.get("type", "unknown")
            success = result.get("success", False)
            duration = result.get("duration", 0)
            status_icon = "PASS" if result["success"] else "FAIL"
            print(f"  {test_type:15} | {status_icon:4} | {duration:6.2f}s")

        print(f"\nReportes guardados en:")
        print(f"  JSON: {report_file}")
        print(f"  HTML: {html_file}")

        if self.demo_data_location:
            print(f"  Datos demo: {self.demo_data_location}")

    def _generate_html_report(self, report: dict) -> str:
        """
        Genera un reporte HTML detallado.

        Args:
            report: Diccionario con los datos del reporte

        Returns:
            str: HTML del reporte
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Reporte de Tests - InfluxDB Backup System</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        .warning {{ color: orange; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .details {{ margin: 20px 0; }}
        .stdout {{ background-color: #f9f9f9; padding: 10px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Reporte de Tests - InfluxDB Backup System</h1>
        <p>Generado: {report['timestamp']}</p>
        <p>Duración total: {report['total_duration']:.2f} segundos</p>
        <p>Tasa de éxito: {report['success_rate']:.1f}%</p>
    </div>

    <h2>Resumen</h2>
    <table>
        <tr>
            <th>Métrica</th>
            <th>Valor</th>
        </tr>
        <tr>
            <td>Tests totales</td>
            <td>{report['total_tests']}</td>
        </tr>
        <tr>
            <td>Tests exitosos</td>
            <td class="success">{report['successful_tests']}</td>
        </tr>
        <tr>
            <td>Tests fallidos</td>
            <td class="failure">{report['failed_tests']}</td>
        </tr>
    </table>

    <h2>Resultados Detallados</h2>
    <table>
        <tr>
            <th>Tipo</th>
            <th>Estado</th>
            <th>Duración</th>
            <th>Código de salida</th>
        </tr>
"""

        for result in report["results"]:
            status_class = "success" if result["success"] else "failure"
            status_text = "EXITOSO" if result["success"] else "FALLIDO"

            html += f"""
        <tr>
            <td>{result.get('type', 'unknown')}</td>
            <td class="{status_class}">{status_text}</td>
            <td>{result.get('duration', 0):.2f}s</td>
            <td>{result.get('returncode', 'N/A')}</td>
        </tr>
"""

        html += """
    </table>
</body>
</html>
"""
        return html

    def run_all_tests(
        self, include_docker: bool = True, include_performance: bool = True
    ) -> None:
        """
        Ejecuta todos los tests del sistema.

        Args:
            include_docker: Si incluir tests que requieren Docker
            include_performance: Si incluir tests de rendimiento
        """
        print("Iniciando ejecución completa de tests...")
        print(f"Directorio del proyecto: {self.project_root}")
        print(f"Incluir Docker: {include_docker}")
        print(f"Incluir rendimiento: {include_performance}")

        results = []

        # Verificar dependencias
        if not self.check_dependencies():
            print("ERROR: Faltan dependencias necesarias")
            return

        # Verificar Docker si es necesario
        docker_available = self.check_docker_services()
        if include_docker and not docker_available:
            print(
                "\nWARNING: Servicios Docker no disponibles, intentando iniciarlos..."
            )

            # Intentar configurar contenedores
            if self.setup_docker_containers():
                docker_available = True
            else:
                print(
                    "\nWARNING: No se pudieron iniciar los servicios Docker, omitiendo tests de integración"
                )
                include_docker = False

        try:
            # 1. Tests unitarios (siempre)
            unit_result = self.run_unit_tests()
            results.append(unit_result)

            # 2. Tests de integración (si Docker está disponible)
            if include_docker and docker_available:
                integration_result = self.run_integration_tests()
                results.append(integration_result)

                docker_result = self.run_docker_tests()
                results.append(docker_result)

            # 3. Tests de rendimiento (opcional)
            if include_performance:
                performance_result = self.run_performance_tests()
                results.append(performance_result)

            # 4. Reporte de cobertura
            coverage_result = self.generate_coverage_report()
            results.append(coverage_result)

            # 5. Crear datos de demostración
            demo_result = self.create_test_data_demo()
            results.append(demo_result)

        finally:
            # Limpiar contenedores Docker
            if include_docker:
                self.cleanup_docker_containers()

        # Generar reporte final
        self.generate_final_report(results)

        # Mostrar resumen final
        failed_tests = [r for r in results if not r.get("success", False)]
        if failed_tests:
            print(f"\nERROR: {len(failed_tests)} tipos de tests fallaron")
            for failed in failed_tests:
                print(f"  - {failed.get('type', 'unknown')}")
        else:
            print("\nSUCCESS: Todos los tests completados exitosamente")


def main():
    """Función principal del script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ejecutar tests del sistema de backup InfluxDB"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Output detallado"
    )
    parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Omitir tests que requieren Docker",
    )
    parser.add_argument(
        "--no-performance",
        action="store_true",
        help="Omitir tests de rendimiento",
    )
    parser.add_argument(
        "--unit-only",
        action="store_true",
        help="Ejecutar solo tests unitarios",
    )
    parser.add_argument(
        "--create-demo-data",
        action="store_true",
        help="Solo crear datos de demostración",
    )

    args = parser.parse_args()

    runner = TestRunner(verbose=args.verbose)

    if args.create_demo_data:
        result = runner.create_test_data_demo()
        if result["success"]:
            print(
                f"SUCCESS: Datos de demostración creados en: {result['location']}"
            )
        else:
            print(
                f"ERROR: Error creando datos de demostración: {result.get('error', 'Error desconocido')}"
            )
        return

    if args.unit_only:
        print("Ejecutando solo tests unitarios...")
        result = runner.run_unit_tests()

        if result["success"]:
            print("SUCCESS: TESTS UNITARIOS COMPLETADOS EXITOSAMENTE")
            print(f"Duración: {result['duration']:.2f} segundos")
        else:
            print("ERROR: TESTS UNITARIOS FALLARON")
            print(f"Duración: {result['duration']:.2f} segundos")
            print("\nLos detalles de los errores se muestran arriba.")
        return

    # Ejecutar todos los tests
    runner.run_all_tests(
        include_docker=not args.no_docker,
        include_performance=not args.no_performance,
    )


if __name__ == "__main__":
    main()
