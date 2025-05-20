import asyncio
import aio_pika
import psutil, time, requests, socket, base64, json, os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from io import BytesIO
from uuid import uuid4
from PIL import Image
import uvicorn
import threading

COORDINATOR_IP = "100.120.4.105"
NODE_NAME = "worker-1"
RABBIT_HOST = COORDINATOR_IP
RABBIT_PORT = 5672
RABBIT_USER = "myuser"
RABBIT_PASS = "mypassword"
last_net_bytes = [0]
last_time = [time.time()]
first_call = [True]



def get_resource_usage():
    usage = psutil.cpu_times_percent(interval=None)
    # Calcular MB/s de red sumando todas las interfaces (incluyendo loopback si existe)
    net = psutil.net_io_counters(pernic=True)
    total_bytes = 0
    for iface, counters in net.items():
        total_bytes += counters.bytes_sent + counters.bytes_recv
    current_time = time.time()
    elapsed = current_time - last_time[0]
    if first_call[0]:
        net_mbs = 0.0
        first_call[0] = False
    elif elapsed > 0:
        net_mbs = (total_bytes - last_net_bytes[0]) / 1024 / 1024 / elapsed
    else:
        net_mbs = 0.0
    last_net_bytes[0] = total_bytes
    last_time[0] = current_time
    return {
        "name": NODE_NAME,
        "cpu": round(usage.user + usage.system, 2),
        "ram": psutil.virtual_memory().percent,
        "net": round(net_mbs, 2),  # MB/s (envío + recepción)
        "ip": socket.gethostbyname(socket.gethostname())
    }

# Reporte periódico de recursos

def background_report():
    while True:
        try:
            requests.post(f"http://{COORDINATOR_IP}:8000/report", json=get_resource_usage(), timeout=5)
        except Exception:
            pass
        time.sleep(0.5)

# Registro inicial en coordinador

def try_register():
    try:
        data = get_resource_usage()
        requests.post(f"http://{COORDINATOR_IP}:8000/register", json=data, timeout=5)
        print("[✔️] Registro en coordinador exitoso")
    except Exception as e:
        print(f"[⚠️] Error al registrarse: {e}")

# Procesamiento de tarea
async def process_task(body):
    try:
        # Notificar estado ocupado
        requests.post(f"http://{COORDINATOR_IP}:8000/working", json={
            "name": NODE_NAME,
            "status": "ejecutando tarea",
            "task_id": str(uuid4())
        }, timeout=5)

        task = json.loads(body)
        b64_data = task.get("image_data_b64")
        if not b64_data:
            return
        img = Image.open(BytesIO(base64.b64decode(b64_data))).convert("L")
        buf = BytesIO()
        img.save(buf, format="PNG")
        result_hex = buf.getvalue().hex()

        # Enviar resultado
        requests.post(f"http://{COORDINATOR_IP}:8000/result-image", json={"image": result_hex}, timeout=5)

        # Limpiar estado
        requests.post(f"http://{COORDINATOR_IP}:8000/working", json={
            "name": NODE_NAME,
            "status": "libre",
            "task_id": None
        }, timeout=5)
    except Exception as e:
        print(f"[❌] Error al ejecutar tarea: {e}")

# Optimización de parámetros

def get_optimal_params():
    try:
        workers_info = requests.get(f"http://{COORDINATOR_IP}:8000/workers", timeout=5).json()
        queue_info = requests.get(f"http://{COORDINATOR_IP}:8000/queue_size", timeout=5).json()
        pending_tasks = queue_info.get("pending_tasks", 0)
        cpu_count = os.cpu_count() or 2
        if pending_tasks > 100:
            threads = min(cpu_count * 2, 32)
            prefetch = 4
        elif pending_tasks > 0:
            threads = cpu_count
            prefetch = 2
        else:
            threads = max(1, cpu_count // 2)
            prefetch = 1
        return threads, prefetch
    except Exception as e:
        print(f"[⚠️] No se pudo optimizar parámetros automáticamente: {e}")
        return os.cpu_count() or 2, 1

# Consumidor asíncrono de RabbitMQ
async def start_async_rabbitmq_consumer(prefetch_count=1):
    connection = await aio_pika.connect_robust(
        host=RABBIT_HOST,
        port=RABBIT_PORT,
        login=RABBIT_USER,
        password=RABBIT_PASS,
        virtualhost="/"
    )
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=prefetch_count)
    queue = await channel.declare_queue("tareas", durable=True)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                await process_task(message.body)

# FastAPI y arranque
app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=background_report, daemon=True).start()
    num_threads, prefetch = get_optimal_params()
    print(f"[Worker] Lanzando {8} consumidores asíncronos de RabbitMQ (prefetch={10})")
    tasks = []
    for _ in range(num_threads):
        tasks.append(asyncio.create_task(start_async_rabbitmq_consumer(prefetch)))
    threading.Thread(target=try_register, daemon=True).start()
    yield
    for t in tasks:
        t.cancel()

app = FastAPI(lifespan=lifespan)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8002)
