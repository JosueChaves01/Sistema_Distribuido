import psutil, time, requests, socket
from fastapi import FastAPI
from PIL import Image
from io import BytesIO
import uvicorn
import base64
import threading


app = FastAPI()

COORDINATOR_IP = "192.168.0.108"
NODE_NAME = "main"

def report_while_busy():
    for _ in range(5):  # puedes ajustar el número o usar un while con condición
        try:
            requests.post(f"http://{COORDINATOR_IP}:8000/report", json=get_resource_usage())
        except:
            pass
        time.sleep(0.5)  # enviar cada 1.5 segundos durante la ejecución


def get_resource_usage():
    return {
        "name": NODE_NAME,
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "net": psutil.net_io_counters().bytes_sent,
        "ip": socket.gethostbyname(socket.gethostname())
    }

@app.on_event("startup")
def startup():
    data = get_resource_usage()
    requests.post(f"http://{COORDINATOR_IP}:8000/register", json=data)

@app.post("/execute")
def execute_task(task: dict):
    try:
        b64_data = task.get("image_data_b64")
        if not b64_data:
            return {"status": "error", "msg": "No se recibió imagen"}

        threading.Thread(target=report_while_busy, daemon=True).start()

        img = Image.open(BytesIO(base64.b64decode(b64_data))).convert("L")
        buf = BytesIO()
        img.save(buf, format="PNG")
        result_hex = buf.getvalue().hex()

        requests.post(f"http://{COORDINATOR_IP}:8000/result-image", json={
            "image": result_hex
        })

        return {"status": "done", "result": "Imagen procesada"}

    except Exception as e:
        return {"status": "error", "msg": str(e)}

def background_report():
    while True:
        try:
            requests.post(f"http://{COORDINATOR_IP}:8000/report", json=get_resource_usage())
        except:
            pass
        time.sleep(0.5)

if __name__ == "__main__":
    import threading
    threading.Thread(target=background_report, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8001)