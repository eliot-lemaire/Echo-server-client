import asyncio
import time
import statistics

async def client(client_id, message_amount, message = input("Message?\n")):
    try:
        reader, writer = await asyncio.open_connection('127.0.0.1', 9001)

        total_latency = 0
        latency_list = []
        output_list = []    # 1 = correct output 2 = error or wrong output
        test_output_list = [1,0,0,1,1]

        for i in range(message_amount):
            start = time.perf_counter()
            
            writer.write(f"{message} from {client_id}\n".encode())
            await writer.drain()
            
            data = await reader.read(100)
            response = data.decode().strip()

            end = time.perf_counter()
            latency = (end - start) * 1000

            output = f"Client {client_id}: {response} with a {latency:.6f}ms latency"

            print(output)
            output_list.append(1)

            total_latency = total_latency + latency
            latency_list.append(latency)

        writer.close()
        await writer.wait_closed()

    except Exception as e:
        output = f"Client {client_id} failed: {e}"
        print(output)
        output_list.append(0)

    finally:
        print(f"Output correctness: {statistics.mean(output_list)*100}%")
        print(f"Total time : {total_latency:.6f}ms")
        print(f"average latency time is {statistics.mean(latency_list):.6f}ms")
        print(f"The min latency was {min(latency_list):.6f}ms")
        print(f"The max latency was {max(latency_list):.6f}ms")

async def main():
    await client(1, 5)
    #await asyncio.gather(*(client(i) for i in range(5)))

if __name__ == "__main__":
    asyncio.run(main())
