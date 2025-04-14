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

@app.post("/register")
def register_node(data: ResourceReport):
    workers[data.name] = {**data.dict(), "last_seen": time.time()}
    return {"status": "registered"}

@app.post("/report")
def update_node(data: ResourceReport):
    if data.name in workers:
        workers[data.name].update({**data.dict(), "last_seen": time.time()})
    return {"status": "updated"}

@app.get("/workers")
def get_workers():
    return workers

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    content = await file.read()

    if len(content) > 3 * 1024 * 1024:
        return {"status": "error", "message": "Imagen muy grande"}

    b64_data = base64.b64encode(content).decode("utf-8")

    task = {
        "task_type": "filter",
        "filter": "bw",
        "image_data_b64": b64_data
    }

    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='tareas')

        channel.basic_publish(
            exchange='',
            routing_key='tareas',
            body=json.dumps(task)
        )
        connection.close()
        return {"status": "sent", "message": "Tarea enviada a la cola"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@app.post("/result-image")
def receive_image(data: dict):
    image_data = data["image"]
    filename = f"{uuid4().hex}.png"
    path = os.path.join("results", filename)
    os.makedirs("results", exist_ok=True)
    with open(path, "wb") as f:
        f.write(bytes.fromhex(image_data))
    return {"status": "received", "filename": filename}

@app.get("/result/{filename}")
def get_result_image(filename: str):
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join("results", filename))

if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)