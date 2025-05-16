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

# Configuración
COORDINATOR_IP = "100.120.4.105"
NODE_NAME = "worker-2"
RABBIT_HOST = "100.120.4.105"
RABBIT_PORT = 5672
RABBIT_USER = "myuser"
RABBIT_PASS = "mypassword"

# Funciones de utilidad

def get_resource_usage():
    usage = psutil.cpu_times_percent(interval=None)
    return {
        "name": NODE_NAME,
        "cpu": round(usage.user + usage.system, 2),
        "ram": psutil.virtual_memory().percent,
        "net": psutil.net_io_counters().bytes_sent,
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

        # Verificar uso de CPU
        if psutil.cpu_percent(interval=1) > 65:
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

# Consumidor de RabbitMQ
def start_rabbitmq_consumer():
    print("[🔌] Iniciando consumidor de RabbitMQ…")
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
        print("[📡] Esperando tareas de RabbitMQ…")
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue='tareas', on_message_callback=callback, auto_ack=False)
        channel.start_consuming()
    except Exception as e:
        print(f"[❌] No pude conectar/consumir RabbitMQ: {e}")

# Configuración de FastAPI con lifespan
def create_app():
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        threading.Thread(target=background_report, daemon=True).start()
        threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()
        threading.Thread(target=try_register, daemon=True).start()
        yield

    app = FastAPI(lifespan=lifespan)
    return app

app = create_app()

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8002)
