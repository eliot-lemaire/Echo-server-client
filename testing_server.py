import asyncio
import signal
import logging
import statistics

class connectionManager:
    def __init__(self): # Used to initialise the variables for the class
        self.active = set() # List that's unordered, doesn't allow duplicates and is optimised for speed
        self.shutting_down = False

    async def add(self, writer):
        if self.shutting_down:
            writer.close()
            await writer.wait_closed()
            return False
        self.active.add(writer)
        addr = writer.get_extra_info("peername")
        print(f"Connection added from {addr}")
        print(f"active: {len(self.active)}")
        return True
    
    def remove(self, writer):  
        if writer in self.active:
            self.active.remove(writer)
            print(f"Active : {len(self.active)}")

    async def close_all(self):
        self.shutting_down = True
        print(f"\nClosing {len(self.active)} connections...")
        for w in self.active:
            w.close()
        if self.active:
            await asyncio.gather(*(w.wait_closed() for w in list(self.active)), return_exceptions=True) # look in notes for breakdown
        print("All connections closed.")

mgr = connectionManager()

async def handle_client(reader, writer):

    #################################################################################

    """
    Seeing is the server is shutting down, if it is then stop the handle client function.
    We are seeing if the add function returns True or False.
    If it returns False we stop the function.
    """

    if not await mgr.add(writer):  
        return
    
    #################################################################################
    
    addr = writer.get_extra_info("peername")
    print(f"New: {addr}")

    output_tracker = []

    try:
        while True:

            try:
                data = await asyncio.wait_for(reader.read(100), timeout=30.0)
                print("No timeout error continuing the communication")
                output_tracker.append(1)

            except asyncio.TimeoutError:
                print(f"Timeout error from {addr}")
                output_tracker.append(0)
                break   # Breaks from the while true loop

            if not data:
                print("Client sent no data shutting down client")
                print(f"Graceful close {addr}")
                break   # Breaks from the while true loop

            msg = data.decode().strip()
            writer.write(f"ECHO: {msg}\n".encode())
            await writer.drain()

            print("Client sucsessful")

    except ConnectionResetError:    # Error if the client drops the connection
        print(f"Client dropped connection, how rude: {addr}")
        output_tracker.append(0)

    finally:
        mgr.remove(writer)
        writer.close()
        print(f"Error rate: {(statistics.mean(output_tracker)*100)-100}%")

async def main():
    try:
        server = await asyncio.start_server(handle_client, "127.0.0.1", 9001)
    except OSError as e:
        if e.errno == 48:
            print("Server already running")
            return
    loop = asyncio.get_running_loop()   # Gets the current event loop
    stop = asyncio.Event()  # Define event False
    def on_signal():
        print("\nSignal -> shutdown...")
        stop.set()  # sets event to True

    #   After this dont know
    for sig in (signal.SIGINT, signal.SIGTERM): # Ctrl + C && Unix kill command
        loop.add_signal_handler(sig, on_signal) # When one signal is called on_signal is run
    print("Server on localhost:9001 - Ctrl + C to stop")
    
    async with server:
        await stop.wait()
        server.close()
        await server.wait_closed()
        await mgr.close_all()
    print("Shutdown complete")
    #print(output_tracker)

if __name__ == "__main__":
    asyncio.run(main())