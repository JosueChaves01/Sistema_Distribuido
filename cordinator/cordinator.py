from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
import time, os
from uuid import uuid4
import shutil
import requests
import base64
import uvicorn
import pika
import json
from contextlib import contextmanager
import threading
import socket

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

workers: Dict[str, dict] = {}

class ResourceReport(BaseModel):
    name: str
    cpu: float
    ram: float
    net: float
    ip: str
from typing import Optional

class WorkerStatus(BaseModel):
    name: str
    status: str
    task_id: Optional[str]

@contextmanager
def rabbitmq_channel():
    connection = None
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='100.120.4.105',  # <- IP Tailscale del servidor RabbitMQ
                port=5672,   
                credentials=pika.PlainCredentials('myuser', 'mypassword')
            )
        )
        channel = connection.channel()
        yield channel
    finally:
        if connection and connection.is_open:
            connection.close()

# Obtener todas las IPs locales del coordinador (LAN, Tailscale, etc.)
def get_local_ips():
    ips = set()
    try:
        hostname = socket.gethostname()
        ips.add(socket.gethostbyname(hostname))
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ':' not in ip:  # Solo IPv4
                ips.add(ip)
    except Exception:
        pass
    # También incluye la IP de la variable de entorno si existe
    env_ip = os.environ.get("COORDINATOR_IP")
    if env_ip:
        ips.add(env_ip)
    return ips

LOCAL_IPS = get_local_ips()

@app.post("/working")
def update_worker_task(data: WorkerStatus):
    if data.name in workers:
        workers[data.name]["status"] = data.status
        workers[data.name]["task_id"] = data.task_id
        workers[data.name]["last_seen"] = time.time()
    return {"status": "updated"}

@app.post("/register")
def register_node(data: ResourceReport):
    is_local = data.ip in LOCAL_IPS
    workers[data.name] = {**data.dict(), "last_seen": time.time(), "is_local": is_local}
    return {"status": "registered", "is_local": is_local}

@app.post("/report")
def update_node(data: ResourceReport):
    is_local = data.ip in LOCAL_IPS
    if data.name in workers:
        workers[data.name].update({**data.dict(), "last_seen": time.time(), "is_local": is_local})
    return {"status": "updated", "is_local": is_local}

@app.get("/workers")
def get_workers():
    return workers

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    content = await file.read()

    if len(content) > 3 * 1024 * 1024:
        return {"status": "error", "message": "Imagen muy grande"}

    b64_data = base64.b64encode(content).decode("utf-8")

    try:
        with rabbitmq_channel() as channel:
            channel.queue_declare(queue='tareas', durable=True)
            
            for _ in range(50):
                task = {
                    "task_type": "filter",
                    "filter": "bw",
                    "image_data_b64": b64_data,
                    "task_id": uuid4().hex
                }
                channel.basic_publish(
                    exchange='',
                    routing_key='tareas',
                    body=json.dumps(task),
                    properties=pika.BasicProperties(
                        delivery_mode=2  # Persistente
                    )
                )
            
        return {"status": "sent", "message": "50 tareas con task_id enviadas a la cola"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Contador de tareas procesadas por segundo
processed_count = 0
last_tps = 0

def tps_counter():
    global processed_count, last_tps
    while True:
        time.sleep(1)
        last_tps = processed_count
        processed_count = 0

@app.post("/result-image")
def receive_image(data: dict):
    global processed_count
    image_data = data["image"]
    filename = f"{uuid4().hex}.png"
    path = os.path.join("results", filename)
    os.makedirs("results", exist_ok=True)
    #with open(path, "wb") as f:
    #    f.write(bytes.fromhex(image_data))
    processed_count += 1
    return {"status": "received", "filename": filename}

@app.get("/result/{filename}")
def get_result_image(filename: str):
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join("results", filename))

def get_queue_length(queue_name='tareas') -> int:
    try:
        with rabbitmq_channel() as channel:
            q = channel.queue_declare(queue=queue_name, durable=True, passive=True)
            return q.method.message_count
    except Exception as e:
        print(f"Error al obtener tamaño de cola: {str(e)}")
        return -1

@app.get("/queue_size")
def queue_size():
    count = get_queue_length()
    return {"pending_tasks": count}

@app.get("/tps")
def get_tps():
    return {"tps": last_tps}


if __name__ == "__main__":
    threading.Thread(target=tps_counter, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)