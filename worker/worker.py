import psutil, time, requests, socket
from fastapi import FastAPI
from io import BytesIO
import uvicorn
import base64
import threading
from uuid import uuid4
from PIL import Image, ImageFilter
app = FastAPI()

COORDINATOR_IP = "100.124.43.17"
NODE_NAME = "worker-2"

def get_resource_usage():
    usage = psutil.cpu_times_percent(interval=None)
    return {
        "name": NODE_NAME,
        "cpu": (usage.user + usage.system).__round__(2),
        "ram": psutil.virtual_memory().percent,
        "net": psutil.net_io_counters().bytes_sent,
        "ip": socket.gethostbyname(socket.gethostname())
    }

@app.on_event("startup")
def startup():
    data = get_resource_usage()
    requests.post(f"http://{COORDINATOR_IP}:8000/register", json=data)

# Función que procesa la imagen
def process_image(b64_data):
    try:
        # Decodificar la imagen base64 y convertirla a escala de grises
        img = Image.open(BytesIO(base64.b64decode(b64_data)))

        img = img.convert("RGB")  # Convertir a RGB por si la imagen está en escala de grises
        img = img.filter(ImageFilter.GaussianBlur(radius=5))  # Filtro de desenfoque gaussiano

        # Guardar la imagen procesada en formato PNG
        buf = BytesIO()
        img.save(buf, format="PNG")
        result_hex = buf.getvalue().hex()

        # Enviar la imagen procesada al coordinador
        requests.post(f"http://{COORDINATOR_IP}:8000/result-image", json={
            "image": result_hex
        })

        return {"status": "done", "result": "Imagen procesada con filtro intensivo"}

    except Exception as e:
        return {"status": "error", "msg": str(e)}

def background_report():
    while True:
        try:
            requests.post(f"http://{COORDINATOR_IP}:8000/report", json=get_resource_usage())
        except:
            pass
        time.sleep(0.5)

import pika
import json

def callback(ch, method, properties, body):
    # Convertir el cuerpo del mensaje a un diccionario
    task = json.loads(body)
    # Pasar los parámetros necesarios a la función ejecutar_tarea
    ejecutar_tarea(ch, method, properties, body)

def ejecutar_tarea(ch, method, properties, body):
    try:
        # Notificar que el worker está ocupado
        requests.post(f"http://{COORDINATOR_IP}:8000/working", json={
            "name": NODE_NAME,
            "status": "ejecutando tarea",
            "task_id": str(uuid4())
        })

        # Verificar el uso de la CPU
        cpu_usage = psutil.cpu_percent(interval=1)
        
        if cpu_usage > 65:
            print(f"[⚠️] El uso de la CPU está al {cpu_usage}%. Rechazando tarea.")
            # Si no puede procesar la tarea, rechazamos el mensaje y lo volvemos a poner en la cola
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return

        # Procesamiento de la tarea aquí (como antes)
        task = json.loads(body)
        b64_data = task.get("image_data_b64")
        if not b64_data:
            print("[❌] No se recibió imagen.")
            return

        # El worker procesa la imagen aquí (como lo hacías antes)
        img = Image.open(BytesIO(base64.b64decode(b64_data))).convert("L")
        buf = BytesIO()
        img.save(buf, format="PNG")
        result_hex = buf.getvalue().hex()

        # Enviar la imagen procesada al coordinador
        requests.post(f"http://{COORDINATOR_IP}:8000/result-image", json={
            "image": result_hex
        })

        # Confirmar que el mensaje fue procesado correctamente
        ch.basic_ack(delivery_tag=method.delivery_tag)

        #limpiar estado al terminar
        requests.post(f"http://{COORDINATOR_IP}:8000/working", json={
            "name": NODE_NAME,
            "status": "libre",
            "task_id": None
        })

    except Exception as e:
        print("[❌] Error al ejecutar tarea:", str(e))
        # Si ocurre un error, rechazamos el mensaje y lo volvemos a poner en la cola
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def start_rabbitmq_consumer():
    # Configuración de la conexión a RabbitMQ
    credentials = pika.PlainCredentials('myuser', 'mypassword')
    parameters = pika.ConnectionParameters('100.124.43.17', credentials=credentials)
    connection = pika.BlockingConnection(parameters)
    
    channel = connection.channel()
    channel.queue_declare(queue='tareas', durable=True)

    # Configurar el consumo de mensajes de RabbitMQ
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='tareas', on_message_callback=callback, auto_ack=False)
    print("[📡] Esperando tareas de RabbitMQ...")
    
    channel.start_consuming()

# Agrega este hilo antes de iniciar uvicorn
if __name__ == "__main__":
    threading.Thread(target=background_report, daemon=True).start()
    threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()
    threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()
    threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()
    threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()
    threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()
    threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8002)