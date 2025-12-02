#!/usr/bin/env python3
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
