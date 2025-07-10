#!/usr/bin/env python3
"""
Script principal para ejecutar todos los tests
==============================================

Script que ejecuta todos los tests del sistema de backup de InfluxDB,
incluyendo tests unitarios, de integración y de calidad de datos.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """
    Ejecutor principal de tests para el sistema de backup.
    """

    def __init__(self, verbose: bool = False):
        """
        Inicializa el ejecutor de tests.

        Args:
            verbose: Habilitar output verbose
        """
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.test_root = self.project_root / "test"

        # Configurar variables de entorno para testing
        os.environ["TESTING"] = "true"
        os.environ["PYTHONPATH"] = str(self.project_root)

    def check_dependencies(self) -> bool:
        """
        Verifica que todas las dependencias estén instaladas.

        Returns:
            bool: True si todas las dependencias están disponibles
        """
        try:
            import faker
            import numpy
            import pandas
            import pytest

            print("✓ Dependencias básicas disponibles")
            return True
        except ImportError as e:
            print(f"✗ Falta dependencia: {e}")
            print(
                "Instale las dependencias con: pip install -r test/requirements-test.txt"
            )
            return False

    def check_docker_services(self) -> bool:
        """
        Verifica que los servicios Docker estén disponibles.

        Returns:
            bool: True si los servicios están disponibles
        """
        try:
            import requests

            # URLs de los servidores de testing
            source_url = os.getenv(
                "INFLUXDB_SOURCE_URL", "http://localhost:8086"
            )
            dest_url = os.getenv(
                "INFLUXDB_DESTINATION_URL", "http://localhost:8087"
            )

            # Verificar servidor origen
            try:
                response = requests.get(f"{source_url}/ping", timeout=5)
                if response.status_code == 200:
                    print("✓ Servidor InfluxDB origen disponible")
                else:
                    print(
                        "✗ Servidor InfluxDB origen no responde correctamente"
                    )
                    return False
            except requests.exceptions.RequestException:
                print("✗ Servidor InfluxDB origen no disponible")
                return False

            # Verificar servidor destino
            try:
                response = requests.get(f"{dest_url}/ping", timeout=5)
                if response.status_code == 200:
                    print("✓ Servidor InfluxDB destino disponible")
                else:
                    print(
                        "✗ Servidor InfluxDB destino no responde correctamente"
                    )
                    return False
            except requests.exceptions.RequestException:
                print("✗ Servidor InfluxDB destino no disponible")
                return False

            return True

        except ImportError:
            print("✗ Requests no disponible para verificar servicios Docker")
            return False

    def run_unit_tests(self) -> dict:
        """
        Ejecuta los tests unitarios.

        Returns:
            dict: Resultados de los tests
        """
        print("\n🧪 Ejecutando tests unitarios...")

        # Crear directorio de resultados
        results_dir = self.project_root / "test_results"
        results_dir.mkdir(exist_ok=True)

        cmd = [
            "python",
            "-m",
            "pytest",
            str(self.test_root / "unit"),
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=test_results/unit_tests.json",
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
        json_file = self.project_root / "test_results" / "unit_tests.json"

        if not json_file.exists():
            print("❌ No se pudo encontrar el archivo de resultados JSON")
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
            print(f"📊 RESUMEN DE TESTS UNITARIOS")
            print(f"{'='*80}")
            print(
                f"Total: {total} | ✅ Pasaron: {passed} | ❌ Fallaron: {failed}"
            )

            if failed > 0:
                print(f"\n🔍 DETALLES DE TESTS FALLIDOS:")
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

                    print(f"\n{i}. ❌ {test_name}")
                    print(f"   📁 Archivo: {test_file}")

                    # Mostrar el error principal
                    crash = test.get("call", {}).get("crash", {})
                    if crash:
                        error_msg = crash.get("message", "Error desconocido")
                        print(f"   💥 Error: {error_msg}")

                        # Mostrar traceback simplificado
                        traceback = crash.get("traceback", [])
                        if traceback:
                            print(f"   📍 Ubicación del error:")
                            for trace in traceback[
                                -3:
                            ]:  # Solo últimas 3 líneas del traceback
                                path = trace.get("path", "")
                                lineno = trace.get("lineno", "")
                                message = trace.get("message", "")
                                if path and lineno:
                                    print(
                                        f"      → {path}:{lineno} - {message}"
                                    )

                    # Mostrar logs si existen
                    logs = test.get("call", {}).get("log", [])
                    if logs:
                        print(f"   📋 Logs:")
                        for log in logs[-2:]:  # Solo últimos 2 logs
                            msg = log.get("msg", "")
                            level = log.get("levelname", "INFO")
                            if msg:
                                print(f"      [{level}] {msg}")

                print(f"\n{'='*80}")
                print(f"💡 Para ver más detalles, ejecuta:")
                print(f"   python -m pytest test/unit -v --tb=long")
                print(f"   O revisa el archivo: test_results/unit_tests.json")

        except Exception as e:
            print(f"❌ Error leyendo resultados: {e}")

    def run_integration_tests(self) -> dict:
        """
        Ejecuta los tests de integración.

        Returns:
            dict: Resultados de los tests
        """
        print("\n🔗 Ejecutando tests de integración...")

        cmd = [
            "python",
            "-m",
            "pytest",
            str(self.test_root / "integration"),
            "-v",
            "--tb=short",
            "-m",
            "integration",
            "--json-report",
            "--json-report-file=test_results/integration_tests.json",
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
        Ejecuta los tests que requieren Docker.

        Returns:
            dict: Resultados de los tests
        """
        print("\n🐳 Ejecutando tests con Docker...")

        cmd = [
            "python",
            "-m",
            "pytest",
            str(self.test_root / "integration"),
            "-v",
            "--tb=short",
            "-m",
            "docker",
            "--json-report",
            "--json-report-file=test_results/docker_tests.json",
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
        print("\n⚡ Ejecutando tests de rendimiento...")

        cmd = [
            "python",
            "-m",
            "pytest",
            str(self.test_root / "integration"),
            "-v",
            "--tb=short",
            "-k",
            "performance",
            "--json-report",
            "--json-report-file=test_results/performance_tests.json",
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
            dict: Información del reporte de cobertura
        """
        print("\n📊 Generando reporte de cobertura...")

        cmd = [
            "python",
            "-m",
            "pytest",
            str(self.test_root / "unit"),
            "--cov=src",
            "--cov-report=html:test_results/coverage_html",
            "--cov-report=json:test_results/coverage.json",
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
        Crea datos de demostración para testing manual.

        Returns:
            dict: Información de la creación de datos
        """
        print("\n📊 Creando datos de demostración...")

        try:
            import json
            import tempfile
            from test.data.data_generator import DataGenerator
            from test.data.test_datasets import get_available_datasets

            generator = DataGenerator(seed=42)

            # Crear directorio temporal para datos de demo
            demo_dir = self.project_root / "test_results" / "demo_data"
            demo_dir.mkdir(parents=True, exist_ok=True)

            # Generar datasets de ejemplo
            datasets_info = {}

            for dataset_name, description in get_available_datasets().items():
                print(f"  Generando dataset: {dataset_name}")

                # Generar datos pequeños para demo
                start_time = datetime.now() - timedelta(hours=1)
                end_time = datetime.now()

                try:
                    from test.data.test_datasets import get_dataset_config

                    dataset_config = get_dataset_config(dataset_name)

                    # Reducir intervalos para generar menos datos
                    for measurement_config in dataset_config.values():
                        measurement_config["interval"] = "5m"  # 5 minutos

                    dataset = generator.generate_complex_dataset(
                        database_name=f"demo_{dataset_name}",
                        start_time=start_time,
                        end_time=end_time,
                        measurements=dataset_config,
                    )

                    # Guardar información del dataset
                    datasets_info[dataset_name] = {
                        "description": description,
                        "measurements": list(dataset.keys()),
                        "total_records": sum(
                            len(records) for records in dataset.values()
                        ),
                        "time_range": {
                            "start": start_time.isoformat(),
                            "end": end_time.isoformat(),
                        },
                    }

                    # Guardar datos de muestra (primeros 10 registros de cada medición)
                    sample_data = {}
                    for measurement_name, records in dataset.items():
                        sample_data[measurement_name] = records[:10]

                    # Guardar en archivo JSON
                    sample_file = demo_dir / f"{dataset_name}_sample.json"
                    with open(sample_file, "w") as f:
                        json.dump(sample_data, f, indent=2, default=str)

                except Exception as e:
                    print(f"    Error generando {dataset_name}: {e}")
                    datasets_info[dataset_name] = {
                        "description": description,
                        "error": str(e),
                    }

            # Guardar resumen
            summary_file = demo_dir / "datasets_summary.json"
            with open(summary_file, "w") as f:
                json.dump(datasets_info, f, indent=2)

            print(f"  Datos de demo guardados en: {demo_dir}")

            return {
                "type": "demo_data",
                "success": True,
                "datasets": len(datasets_info),
                "location": str(demo_dir),
            }

        except Exception as e:
            return {"type": "demo_data", "success": False, "error": str(e)}

    def generate_final_report(self, results: list) -> None:
        """
        Genera reporte final de todos los tests.

        Args:
            results: Lista de resultados de tests
        """
        print("\n📋 Generando reporte final...")

        # Crear directorio de resultados
        results_dir = self.project_root / "test_results"
        results_dir.mkdir(exist_ok=True)

        # Calcular estadísticas
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r["success"])
        total_duration = sum(r.get("duration", 0) for r in results)

        # Crear reporte
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": total_tests - successful_tests,
                "success_rate": (
                    successful_tests / total_tests if total_tests > 0 else 0
                ),
                "total_duration": total_duration,
            },
            "results": results,
        }

        # Guardar reporte JSON
        report_file = results_dir / "test_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        # Generar reporte HTML simple
        html_report = self._generate_html_report(report)
        html_file = results_dir / "test_report.html"
        with open(html_file, "w") as f:
            f.write(html_report)

        # Mostrar resumen
        print(f"\n{'='*60}")
        print("📊 RESUMEN FINAL DE TESTS")
        print(f"{'='*60}")
        print(f"Tests ejecutados: {total_tests}")
        print(f"Tests exitosos: {successful_tests}")
        print(f"Tests fallidos: {total_tests - successful_tests}")
        print(f"Tasa de éxito: {successful_tests / total_tests * 100:.1f}%")
        print(f"Duración total: {total_duration:.1f} segundos")
        print(f"\nReportes guardados en: {results_dir}")
        print(f"  - JSON: {report_file}")
        print(f"  - HTML: {html_file}")

    def _generate_html_report(self, report: dict) -> str:
        """
        Genera reporte HTML.

        Args:
            report: Datos del reporte

        Returns:
            str: HTML del reporte
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Reporte de Tests - InfluxDB Backup Toolkit</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background: #e8f4f8; padding: 15px; border-radius: 5px; text-align: center; }}
        .success {{ background: #d4edda; color: #155724; }}
        .failure {{ background: #f8d7da; color: #721c24; }}
        .result {{ margin: 10px 0; padding: 10px; border-left: 4px solid #ddd; }}
        .result.success {{ border-color: #28a745; }}
        .result.failure {{ border-color: #dc3545; }}
        pre {{ background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 Reporte de Tests - InfluxDB Backup Toolkit</h1>
        <p>Generado el: {report['timestamp']}</p>
    </div>

    <div class="summary">
        <div class="metric success">
            <h3>{report['summary']['successful_tests']}</h3>
            <p>Tests Exitosos</p>
        </div>
        <div class="metric failure">
            <h3>{report['summary']['failed_tests']}</h3>
            <p>Tests Fallidos</p>
        </div>
        <div class="metric">
            <h3>{report['summary']['success_rate']:.1%}</h3>
            <p>Tasa de Éxito</p>
        </div>
        <div class="metric">
            <h3>{report['summary']['total_duration']:.1f}s</h3>
            <p>Duración Total</p>
        </div>
    </div>

    <h2>Resultados Detallados</h2>
"""

        for result in report["results"]:
            status_class = "success" if result["success"] else "failure"
            status_icon = "✅" if result["success"] else "❌"

            html += f"""
    <div class="result {status_class}">
        <h3>{status_icon} {result['type'].title()} Tests</h3>
        <p><strong>Duración:</strong> {result.get('duration', 0):.2f} segundos</p>
        <p><strong>Estado:</strong> {'Exitoso' if result['success'] else 'Fallido'}</p>
"""

            if not result["success"] and result.get("stderr"):
                html += f"<details><summary>Ver errores</summary><pre>{result['stderr']}</pre></details>"

            html += "</div>"

        html += """
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
            include_docker: Incluir tests que requieren Docker
            include_performance: Incluir tests de rendimiento
        """
        print("🚀 Iniciando ejecución completa de tests...")
        print(f"Proyecto: {self.project_root}")
        print(f"Tests: {self.test_root}")

        # Verificar dependencias
        if not self.check_dependencies():
            sys.exit(1)

        # Crear directorio de resultados
        results_dir = self.project_root / "test/test_results"
        results_dir.mkdir(exist_ok=True)

        results = []

        # 1. Tests unitarios (siempre se ejecutan)
        results.append(self.run_unit_tests())

        # 2. Crear datos de demostración
        results.append(self.create_test_data_demo())

        # 3. Tests de integración (si Docker disponible)
        if include_docker:
            if self.check_docker_services():
                results.append(self.run_integration_tests())
                results.append(self.run_docker_tests())

                if include_performance:
                    results.append(self.run_performance_tests())
            else:
                print(
                    "\n⚠️  Servicios Docker no disponibles, omitiendo tests de integración"
                )
                print("   Para ejecutar tests de integración:")
                print(
                    "   docker-compose -f test/docker/docker-compose.test.yml up -d"
                )

        # 4. Reporte de cobertura
        results.append(self.generate_coverage_report())

        # 5. Generar reporte final
        self.generate_final_report(results)

        # Determinar código de salida
        failed_tests = [r for r in results if not r["success"]]
        if failed_tests:
            print(f"\n❌ {len(failed_tests)} tipos de tests fallaron")
            sys.exit(1)
        else:
            print("\n✅ Todos los tests completados exitosamente")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Ejecutor de tests para InfluxDB Backup Toolkit"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Output verbose"
    )
    parser.add_argument(
        "--unit-only", action="store_true", help="Solo tests unitarios"
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
        "--demo-data-only",
        action="store_true",
        help="Solo generar datos de demostración",
    )

    args = parser.parse_args()

    runner = TestRunner(verbose=args.verbose)

    if args.demo_data_only:
        result = runner.create_test_data_demo()
        if result["success"]:
            print(f"✅ Datos de demostración creados en: {result['location']}")
        else:
            print(
                f"❌ Error creando datos de demostración: {result.get('error', 'Error desconocido')}"
            )
        return

    if args.unit_only:
        print("🚀 Ejecutando solo tests unitarios...")
        result = runner.run_unit_tests()

        print(f"\n{'='*60}")
        if result["success"]:
            print("✅ TESTS UNITARIOS COMPLETADOS EXITOSAMENTE")
            print(f"⏱️  Duración: {result['duration']:.2f} segundos")
        else:
            print("❌ TESTS UNITARIOS FALLARON")
            print(f"⏱️  Duración: {result['duration']:.2f} segundos")
            print("\n💡 Los detalles de los errores se muestran arriba.")
            print(
                "   Para más información usa: python -m pytest test/unit -v --tb=long"
            )
            sys.exit(1)
        print(f"{'='*60}")
        return

    # Ejecutar todos los tests
    runner.run_all_tests(
        include_docker=not args.no_docker,
        include_performance=not args.no_performance,
    )


if __name__ == "__main__":
    main()
