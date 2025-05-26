#!/usr/bin/env python3
"""
Script para probar el rendimiento del endpoint de streaming SSE.

Mide latencia, throughput y otros métricas de rendimiento.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
import httpx
import json
from datetime import datetime
import argparse


class StreamPerformanceTester:
    """Clase para realizar pruebas de rendimiento del streaming."""

    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        self.results = []

    async def measure_single_stream(self, message: str) -> Dict[str, Any]:
        """
        Mide el rendimiento de una sola petición de streaming.

        Returns:
            Diccionario con métricas de rendimiento
        """
        metrics = {
            "start_time": time.time(),
            "first_chunk_time": None,
            "end_time": None,
            "chunk_count": 0,
            "total_bytes": 0,
            "chunks": [],
            "errors": [],
        }

        try:
            async with httpx.AsyncClient() as client:
                # Iniciar request
                start = time.time()

                async with client.stream(
                    "POST",
                    f"{self.base_url}/stream/chat",
                    json={"message": message},
                    headers=self.headers,
                    timeout=30.0,
                ) as response:
                    response.raise_for_status()

                    buffer = ""
                    async for chunk in response.aiter_text():
                        chunk_time = time.time()

                        # Registrar tiempo del primer chunk
                        if metrics["first_chunk_time"] is None:
                            metrics["first_chunk_time"] = chunk_time
                            metrics["time_to_first_byte"] = chunk_time - start

                        metrics["chunk_count"] += 1
                        metrics["total_bytes"] += len(chunk.encode())

                        # Procesar eventos SSE
                        buffer += chunk
                        lines = buffer.split("\n")
                        buffer = lines.pop()

                        for line in lines:
                            if line.startswith("data:"):
                                data_str = line[5:].strip()
                                if data_str:
                                    try:
                                        data = json.loads(data_str)
                                        metrics["chunks"].append(
                                            {"time": chunk_time - start, "data": data}
                                        )
                                    except json.JSONDecodeError:
                                        pass

                metrics["end_time"] = time.time()
                metrics["total_time"] = metrics["end_time"] - metrics["start_time"]

        except Exception as e:
            metrics["errors"].append(str(e))
            metrics["end_time"] = time.time()
            metrics["total_time"] = metrics["end_time"] - metrics["start_time"]

        return metrics

    async def run_concurrent_streams(
        self, num_streams: int, message: str
    ) -> List[Dict[str, Any]]:
        """Ejecuta múltiples streams concurrentes."""
        tasks = [
            self.measure_single_stream(f"{message} (stream {i})")
            for i in range(num_streams)
        ]
        return await asyncio.gather(*tasks)

    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analiza los resultados y calcula estadísticas."""
        successful_results = [r for r in results if not r.get("errors")]

        if not successful_results:
            return {"error": "No successful results to analyze"}

        # Extraer métricas
        time_to_first_bytes = [
            r["time_to_first_byte"]
            for r in successful_results
            if r.get("time_to_first_byte")
        ]
        total_times = [r["total_time"] for r in successful_results]
        chunk_counts = [r["chunk_count"] for r in successful_results]
        bytes_received = [r["total_bytes"] for r in successful_results]

        analysis = {
            "total_requests": len(results),
            "successful_requests": len(successful_results),
            "failed_requests": len(results) - len(successful_results),
            "time_to_first_byte": {
                "min": min(time_to_first_bytes) if time_to_first_bytes else 0,
                "max": max(time_to_first_bytes) if time_to_first_bytes else 0,
                "avg": (
                    statistics.mean(time_to_first_bytes) if time_to_first_bytes else 0
                ),
                "median": (
                    statistics.median(time_to_first_bytes) if time_to_first_bytes else 0
                ),
            },
            "total_time": {
                "min": min(total_times),
                "max": max(total_times),
                "avg": statistics.mean(total_times),
                "median": statistics.median(total_times),
            },
            "chunks_per_request": {
                "min": min(chunk_counts),
                "max": max(chunk_counts),
                "avg": statistics.mean(chunk_counts),
            },
            "bytes_per_request": {
                "min": min(bytes_received),
                "max": max(bytes_received),
                "avg": statistics.mean(bytes_received),
            },
            "throughput": {
                "requests_per_second": len(successful_results) / max(total_times),
                "bytes_per_second": sum(bytes_received) / sum(total_times),
            },
        }

        # Agregar percentiles si hay suficientes datos
        if len(time_to_first_bytes) >= 10:
            analysis["time_to_first_byte"]["p95"] = statistics.quantiles(
                time_to_first_bytes, n=20
            )[18]
            analysis["total_time"]["p95"] = statistics.quantiles(total_times, n=20)[18]

        return analysis

    async def run_performance_test(self, test_config: Dict[str, Any]):
        """Ejecuta una suite completa de pruebas de rendimiento."""
        print(f"\\n{'='*60}")
        print(f"Iniciando pruebas de rendimiento de streaming SSE")
        print(f"URL: {self.base_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"{'='*60}\\n")

        all_results = {}

        # Test 1: Latencia de una sola petición
        print("Test 1: Latencia de petición única...")
        single_result = await self.measure_single_stream("Test de latencia única")
        all_results["single_request"] = self.analyze_results([single_result])
        print(
            f"  - Tiempo hasta primer byte: {single_result.get('time_to_first_byte', 0):.3f}s"
        )
        print(f"  - Tiempo total: {single_result['total_time']:.3f}s")
        print(f"  - Chunks recibidos: {single_result['chunk_count']}")

        # Test 2: Concurrencia baja
        print("\\nTest 2: Concurrencia baja (5 requests)...")
        low_concurrent = await self.run_concurrent_streams(5, "Test concurrencia baja")
        all_results["low_concurrency"] = self.analyze_results(low_concurrent)
        print(
            f"  - Tiempo promedio: {all_results['low_concurrency']['total_time']['avg']:.3f}s"
        )
        print(
            f"  - Requests exitosos: {all_results['low_concurrency']['successful_requests']}/5"
        )

        # Test 3: Concurrencia media
        print("\\nTest 3: Concurrencia media (20 requests)...")
        medium_concurrent = await self.run_concurrent_streams(
            20, "Test concurrencia media"
        )
        all_results["medium_concurrency"] = self.analyze_results(medium_concurrent)
        print(
            f"  - Tiempo promedio: {all_results['medium_concurrency']['total_time']['avg']:.3f}s"
        )
        print(
            f"  - Requests exitosos: {all_results['medium_concurrency']['successful_requests']}/20"
        )

        # Test 4: Mensajes largos
        print("\\nTest 4: Mensajes largos...")
        long_message = "Explica detalladamente " * 20
        long_result = await self.measure_single_stream(long_message)
        all_results["long_message"] = self.analyze_results([long_result])
        print(f"  - Tiempo total: {long_result['total_time']:.3f}s")
        print(f"  - Bytes recibidos: {long_result['total_bytes']}")

        # Resumen final
        print(f"\\n{'='*60}")
        print("RESUMEN DE RENDIMIENTO")
        print(f"{'='*60}")

        for test_name, results in all_results.items():
            if "error" not in results:
                print(f"\\n{test_name.replace('_', ' ').title()}:")
                print(f"  - Tiempo promedio: {results['total_time']['avg']:.3f}s")
                if results.get("time_to_first_byte"):
                    print(
                        f"  - TTFB promedio: {results['time_to_first_byte']['avg']:.3f}s"
                    )
                print(
                    f"  - Éxito: {results['successful_requests']}/{results['total_requests']}"
                )

        return all_results


async def main():
    parser = argparse.ArgumentParser(
        description="Test de rendimiento para streaming SSE"
    )
    parser.add_argument(
        "--url", default="http://localhost:8000", help="URL base del servidor"
    )
    parser.add_argument("--token", required=True, help="Token JWT de autenticación")
    parser.add_argument("--output", help="Archivo para guardar resultados JSON")

    args = parser.parse_args()

    tester = StreamPerformanceTester(args.url, args.token)

    # Configuración de tests
    test_config = {
        "single_request_count": 1,
        "low_concurrency_count": 5,
        "medium_concurrency_count": 20,
        "high_concurrency_count": 50,
    }

    results = await tester.run_performance_test(test_config)

    # Guardar resultados si se especifica archivo de salida
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\\nResultados guardados en: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
