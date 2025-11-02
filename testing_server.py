#   Made by elot-lemaire github

"""
Added:
1) Error percent
2) Latency
3) Logging
"""


import asyncio
import signal
import logging
import statistics
import time

logging.basicConfig(
    level=logging.DEBUG,
    filename="app.log",
    encoding="utf-8",
    filemode="a",
    format="{asctime} | {levelname} | {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M"
)


"""
logging.debug("Debug message")
logging.info("Informational message")
logging.warning("Something seems off")
logging.error("An error occurred")
logging.critical("Critical failure")
"""

class connectionManager:
    def __init__(self): 
        self.active = set() 
        self.shutting_down = False

    async def add(self, writer):
        if self.shutting_down:
            writer.close()
            await writer.wait_closed()
            return False
        self.active.add(writer)
        addr = writer.get_extra_info("peername")
        logging.info(f"Connection added from {addr}")
        logging.info(f"Active connections: {len(self.active)}")
        return True
    
    def remove(self, writer):  
        if writer in self.active:
            self.active.remove(writer)
            logging.info(f"Active connections: {len(self.active)}")

    async def close_all(self):
        self.shutting_down = True
        logging.info(f"Closing {len(self.active)} active connection(s)...")
        for w in self.active:
            w.close()
        if self.active:
            await asyncio.gather(*(w.wait_closed() for w in list(self.active)), return_exceptions=True)
        logging.info("All connections closed.")

mgr = connectionManager()

async def handle_client(reader, writer):
    """
    Checks if the server is shutting down; if so, stop handling the client.
    The add() function returns True or False depending on the state.
    If it returns False, we stop the function.
    """

    if not await mgr.add(writer):  
        return
    
    addr = writer.get_extra_info("peername")
    logging.info(f"New connection: {addr}")

    output_tracker = []
    latency_list = []
    total_latency = 0

    try:
        while True:
            try:
                start = time.perf_counter()
                data = await asyncio.wait_for(reader.read(100), timeout=5.0)
                logging.debug("No timeout error, continuing communication")
                output_tracker.append(1)

            except asyncio.TimeoutError:
                logging.error(f"Timeout error from {addr}")
                output_tracker.append(0)
                break

            if not data:
                logging.info("Client sent no data — closing connection")
                logging.info(f"Graceful close: {addr}")
                break

            msg = data.decode().strip()
            writer.write(f"ECHO: {msg}\n".encode())
            await writer.drain()

            end = time.perf_counter()
            latency = (end - start)

            logging.info(f"Client {addr} : | {msg} | with a latency of {latency:.6f}ms")
            total_latency = total_latency + latency
            latency_list.append(latency)

    except ConnectionResetError:
        logging.error(f"Client unexpectedly dropped the connection: {addr}")
        output_tracker.append(0)

    finally:
        mgr.remove(writer)
        writer.close()

        if output_tracker:
            error_rate = statistics.mean(output_tracker) * 100
            if output_tracker.count(1) == len(output_tracker):
                error_rate = 0
        else:
            error_rate = 0

        if latency_list:
            logging.debug(f"Error rate: {error_rate:.2f}% from {addr}")
            logging.debug(f"Total latency from {addr} was {total_latency:.6f}ms")
            logging.debug(f"average latency time is {statistics.mean(latency_list):.6f}ms")
            logging.debug(f"The min latency was {min(latency_list):.6f}ms")
            logging.debug(f"The max latency was {max(latency_list):.6f}ms")

async def main():
    try:
        server = await asyncio.start_server(handle_client, "127.0.0.1", 9001)
    except OSError as e:
        if e.errno == 48:
            logging.error("Server is already running on port 9001")
            return

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def on_signal():
        logging.info("Received termination signal → shutting down...")
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, on_signal)

    logging.debug("Server running on localhost:9001 — press Ctrl+C to stop")

    async with server:
        await stop.wait()
        server.close()
        await server.wait_closed()
        await mgr.close_all()
    logging.info("Shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())


