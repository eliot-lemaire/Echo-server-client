import asyncio
import time
import psutil   # Gives info about system RAM, CPU, Network
"""
from prometheus_client import Counter, Gauge, Histogram, start_http_server
    Used to interact with the framework
    Counter : number that only increases
    Gauge : Value that goes up or down
    Histogram : stores a distribution
    start_http_server : spins up a light weight web server
"""
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

REQUESTS_TOTAL = Counter("requests_total", "Total requests sent")
REQUESTS_SUCCESS_TOTAL = Counter("requests_success_total", "Successful responses")
RESPONSE_ERROR_TOTAL = Counter("response_error_total", "Failed responses")
LATENCY_SECONDS = Histogram("latency_seconds", "Request latency in seconds")
CPU_USAGE_PERCENT = Gauge("cpu_usage_percent","System CPU usage percentage")
MEMORY_USAGE_MB = Gauge("memory_usage_mb", "System usage in MB")

async def monitor_system_metrics():
    while True:

        """
        CPU_USAGE_PERCENT.set() update the gauge metric
        sutil.cpu_percent(interval=None) will measure how much CPU is being used
        """
        CPU_USAGE_PERCENT.set(psutil.cpu_percent(interval=None))

        # How much memory is used in bytes and convert it to MB
        MEMORY_USAGE_MB.set(psutil.virtual_memory().used / (1024 ** 2))

        await asyncio.sleep(2)

async def run_client(id, message):
    try:
        start = time.perf_counter()

        reader, writer = await asyncio.open_connection('127.0.0.1', 9001)

        writer.write(f"{message} from {id}\n".encode())
        await writer.drain()

        data = await reader.read(100)
        response = data.decode().strip()

        writer.close()
        await writer.wait_closed()

        latency = time.perf_counter() - start
        LATENCY_SECONDS.observe(latency)

        REQUESTS_TOTAL.inc()
        REQUESTS_SUCCESS_TOTAL.inc()


    except Exception as e:
        logging.error(f"Client {id} error : {e}")
        RESPONSE_ERROR_TOTAL.inc()

async def main():
    start_http_server(8001)
    logging.info("Prometheus metrics exporter running on http://localhost:8001/metrics")

    asyncio.create_task(monitor_system_metrics())
    logging.info("System monitoring task started")

    num_clients = 50
    message = "Hello server"

    await asyncio.gather(*(run_client(i, message) for i in range(num_clients)))
    logging.info("Load test finished. All clients have completed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.warning("Load test interrupted manually.")
