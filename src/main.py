from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from .io_datos import cargar_hotel
from .simulacion import SimuladorUnificado
from .sugerencias import generar_sugerencias_habitabilidad


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulación educativa de iluminación hotelera")
    parser.add_argument("--entrada", default="data/datos_hotel.json")
    parser.add_argument("--salida", default="outputs")
    args = parser.parse_args()

    hotel = cargar_hotel(args.entrada)
    resultados, resumen, propuestas = SimuladorUnificado(hotel).ejecutar()
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    por_hora = {}
    for r in resultados:
        por_hora[r.hora] = por_hora.get(r.hora, 0.0) + r.potencia_asignada
    demanda_maxima = max(por_hora.values(), default=0.0)
    capacidad = hotel.generador.capacidad_kw * 1000.0
    generador_info = {
        "capacidad_w": capacidad,
        "demanda_maxima_w": demanda_maxima,
        "reserva_w": max(0.0, capacidad - demanda_maxima),
        "porcentaje_usado": 0.0 if capacidad == 0 else min(100.0, demanda_maxima / capacidad * 100.0),
        "estado": "CAPACIDAD_LIMITADA" if demanda_maxima > capacidad else ("ALTA_DEMANDA" if demanda_maxima > capacidad * 0.8 else "OPERACION_NORMAL"),
    }
    sugerencias = generar_sugerencias_habitabilidad(hotel, resumen, resultados, generador_info, propuestas)
    _guardar_json(salida / "resultados.json", resultados, resumen, propuestas, sugerencias)
    _guardar_csv(salida / "reporte.csv", resultados)
    _guardar_json(salida / "resumen.json", [], resumen, propuestas, sugerencias)
    print(f"Simulación completada: {len(resultados)} resultados")
    print(f"Zonas evaluadas: {len(resumen)}")
    print(f"Propuestas de reasignación: {len(propuestas)}")
    print(f"Sugerencias de habitabilidad generadas: {len(sugerencias)}")


def _guardar_json(ruta: Path, resultados, resumen, propuestas, sugerencias) -> None:
    payload = {
        "resultados": [asdict(resultado) | {"modo": resultado.modo.value, "estado": resultado.estado.value} for resultado in resultados],
        "resumen": resumen,
        "reasignaciones": propuestas,
        "sugerencias_habitabilidad": sugerencias,
    }
    ruta.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _guardar_csv(ruta: Path, resultados) -> None:
    campos = ["zona_id", "hora", "periodo", "modo", "luz_natural", "luz_reflejada", "luz_artificial", "luz_total", "potencia_asignada", "estado"]
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=campos)
        writer.writeheader()
        for resultado in resultados:
            row = asdict(resultado)
            row["modo"] = resultado.modo.value
            row["estado"] = resultado.estado.value
            writer.writerow(row)


if __name__ == "__main__":
    main()
