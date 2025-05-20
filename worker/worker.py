import psutil, time, requests, socket
from fastapi import FastAPI
from contextlib import asynccontextmanager
from io import BytesIO
import uvicorn
import base64
import threading
from uuid import uuid4
from PIL import Image, ImageFilter
import pika
import json
import os

# Configuración
COORDINATOR_IP = "100.120.4.105"
NODE_NAME = "worker-2"
RABBIT_HOST = COORDINATOR_IP
RABBIT_PORT = 5672
RABBIT_USER = "myuser"
RABBIT_PASS = "mypassword"

# Guardar el valor anterior de bytes enviados y recibidos para calcular el uso por segundo
last_net_bytes = [0]
last_time = [time.time()]
first_call = [True]

# Funciones de utilidad

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
            usage = get_resource_usage()
            requests.post(f"http://{COORDINATOR_IP}:8000/report", json=usage, timeout=5)
        except Exception as e:
            print(f"[DEBUG] Error en background_report: {e}")
        time.sleep(1)  # Intervalo aumentado a 1 segundo para mayor estabilidad

# Registro inicial en coordinador (sin bloquear startup)
def try_register():
    try:
        data = get_resource_usage()
        requests.post(f"http://{COORDINATOR_IP}:8000/register", json=data, timeout=5)
        print("[✔️] Registro en coordinador exitoso")
    except Exception as e:
        print(f"[⚠️] Error al registrarse: {e}")

# Lógica de procesamiento de tarea

def callback(ch, method, properties, body):
    ejecutar_tarea(ch, method, properties, body)


def ejecutar_tarea(ch, method, properties, body):
    try:
        # Notificar estado ocupado
        requests.post(f"http://{COORDINATOR_IP}:8000/working", json={
            "name": NODE_NAME,
            "status": "ejecutando tarea",
            "task_id": str(uuid4())
        }, timeout=5)

        # (OPCIONAL) Puedes comentar la siguiente línea para no limitar por CPU:
        if psutil.cpu_percent(interval=1) > 100:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return

        # Procesar imagen
        task = json.loads(body)
        b64_data = task.get("image_data_b64")
        if not b64_data:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        img = Image.open(BytesIO(base64.b64decode(b64_data))).convert("L")
        buf = BytesIO()
        img.save(buf, format="PNG")
        result_hex = buf.getvalue().hex()

        # Enviar resultado
        requests.post(f"http://{COORDINATOR_IP}:8000/result-image", json={"image": result_hex}, timeout=5)
        ch.basic_ack(delivery_tag=method.delivery_tag)

        # Limpiar estado
        requests.post(f"http://{COORDINATOR_IP}:8000/working", json={
            "name": NODE_NAME,
            "status": "libre",
            "task_id": None
        }, timeout=5)

    except Exception as e:
        print(f"[❌] Error al ejecutar tarea: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def get_optimal_params():
    # Consulta el coordinador para obtener el número de workers y tareas en cola
    try:
        workers_info = requests.get(f"http://{COORDINATOR_IP}:8000/workers", timeout=5).json()
        queue_info = requests.get(f"http://{COORDINATOR_IP}:8000/queue_size", timeout=5).json()
        num_workers = len(workers_info)
        pending_tasks = queue_info.get("pending_tasks", 0)
        # Estrategia simple: más tareas en cola y menos workers => más hilos
        cpu_count = os.cpu_count() or 2
        if pending_tasks > 100:
            threads = min(cpu_count * 2, 32)  # Escala hasta el doble de núcleos, máximo 32
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

# Consumidor de RabbitMQ
def start_rabbitmq_consumer(prefetch_count=1):
    creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    params = pika.ConnectionParameters(
        host=RABBIT_HOST,
        port=RABBIT_PORT,
        virtual_host='/',
        credentials=creds,
        heartbeat=60,
        blocked_connection_timeout=30
    )
    try:
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue='tareas', durable=True)
        channel.basic_qos(prefetch_count=prefetch_count)
        channel.basic_consume(queue='tareas', on_message_callback=callback, auto_ack=False)
        channel.start_consuming()
    except Exception as e:
        print(f"[❌] No pude conectar/consumir RabbitMQ: {e}")

# Configuración de FastAPI con lifespan
def create_app():
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        threading.Thread(target=background_report, daemon=True).start()
        num_threads, prefetch = get_optimal_params()
        print(f"[Worker] Lanzando {num_threads} consumidores de RabbitMQ (prefetch={prefetch})")
        for _ in range(num_threads):
            threading.Thread(target=start_rabbitmq_consumer, args=(prefetch,), daemon=True).start()
        threading.Thread(target=try_register, daemon=True).start()
        yield

    app = FastAPI(lifespan=lifespan)
    return app

app = create_app()

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8003)
