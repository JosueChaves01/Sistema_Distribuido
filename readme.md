# Sistema Distribuido

**Sistema Distribuido** es una aplicación distribuida desarrollada en Python, diseñada para gestionar información académica en una institución educativa. Implementa servicios web utilizando tecnologías como RabbitMQ para la comunicación entre componentes, permitiendo operaciones CRUD sobre entidades como profesores y grupos.

## 🛠️ Tecnologías Utilizadas

- **Python 3.13**: Lenguaje de programación principal.
- **RabbitMQ**: Sistema de mensajería para la comunicación entre componentes distribuidos.
- **Erlang**: Lenguaje utilizado por RabbitMQ para la gestión de procesos concurrentes.
- **React**: Biblioteca de JavaScript para la construcción de interfaces de usuario.
- **Node.js & npm**: Entorno de ejecución y gestor de paquetes para JavaScript.

## 🚀 Instalación

### Requisitos Previos

- **Python 3.13**: 
- **RabbitMQ**: 

### Pasos de Instalación

1. **Instalar Node.js y npm**:

   winget install Schniz.fnm
   fnm install 22

### Verificar la version de Node.js:

- Ejecuta en la terminal:

     ```cmd
     node -v 
     ```


### Verificar la version de npm:

- Ejecuta en la terminal:

     ```cmd
     npm -v 
     ```

---

## 🌐 Uso de Tailscale para Red Privada

Este sistema está pensado para funcionar en una red privada virtual usando [Tailscale](https://tailscale.com/), lo que permite que los servicios distribuidos (coordinador, workers, frontend) se comuniquen de forma segura aunque estén en diferentes redes físicas.

### Pasos para usar Tailscale:

1. **Crea una cuenta en [Tailscale](https://tailscale.com/)** (puedes usar Google, Microsoft, etc.).
2. **Descarga e instala Tailscale** en cada máquina que participará en el sistema (coordinador, cada worker, etc.):
   - [Descargar Tailscale](https://tailscale.com/download)
3. **Inicia sesión** en Tailscale en cada máquina.
4. **Verifica la IP de Tailscale** de cada nodo:
   - Ejecuta en la terminal:
     ```powershell
     tailscale ip -4
     ```
   - O abre la app de Tailscale y copia la IP que aparece.
5. **Usa la IP de Tailscale** en las variables `COORDINATOR_IP`, `RABBIT_HOST`, etc., en los scripts Python para asegurar la conectividad entre nodos.
6. **Verifica la conectividad**:
   - Haz ping entre nodos usando la IP de Tailscale:
     ```powershell
     ping <ip-tailscale-del-otro-nodo>
     ```

**Nota:** Tailscale debe estar activo en todos los nodos mientras el sistema esté funcionando. Si cambias de red (WiFi, Ethernet), Tailscale mantiene la conectividad.

---

## ⚠️ Notas de Configuración

- **IP del Coordinador:**
  - Asegúrate de ajustar la variable `COORDINATOR_IP` en los scripts (`worker.py`, `cordinator.py`, etc.) para que apunte a la IP real del coordinador en tu red o en Tailscale.

- **Credenciales de RabbitMQ:**
  - Debes crear un usuario en RabbitMQ con usuario `myuser` y contraseña `mypassword` y otorgarle permisos sobre la cola. Puedes hacerlo desde el panel web de RabbitMQ o con los siguientes comandos en la terminal del servidor RabbitMQ:
    ```powershell
    rabbitmqctl add_user myuser mypassword
    rabbitmqctl set_permissions -p / myuser ".*" ".*" ".*"
    ```

- **Variables de entorno:**
  - Si cambias la IP, usuario o contraseña, recuerda actualizar estos valores en todos los scripts del sistema distribuido.

---

## 🛠️ Solución de Problemas

### Problemas comunes y soluciones

- **No puedo conectarme a RabbitMQ desde otro equipo (por Tailscale):**
  - Asegúrate de que el puerto 5672 está abierto en el firewall del servidor RabbitMQ:
    ```powershell
    New-NetFirewallRule -DisplayName "RabbitMQ AMQP" -Direction Inbound -LocalPort 5672 -Protocol TCP -Action Allow
    ```
  - Verifica que RabbitMQ esté escuchando en todas las interfaces (usa `netstat -an | findstr 5672` y busca `0.0.0.0:5672`).
  - Comprueba que la IP de Tailscale es la correcta y que puedes hacer ping desde el worker al servidor.
  - Reinicia el servicio RabbitMQ después de cualquier cambio.

- **No puedo acceder al panel web de RabbitMQ (http://localhost:15672):**
  - Habilita el plugin de administración:
    ```powershell
    rabbitmq-plugins enable rabbitmq_management
    ```
  - Asegúrate de que el puerto 15672 está abierto en el firewall:
    ```powershell
    New-NetFirewallRule -DisplayName "RabbitMQ Management" -Direction Inbound -LocalPort 15672 -Protocol TCP -Action Allow
    ```
  - Reinicia el servicio RabbitMQ.

- **Error de conexión con RabbitMQ (Erlang cookie):**
  - Asegúrate de que el archivo `.erlang.cookie` es idéntico en tu usuario y en el usuario del sistema (ver instrucciones en la documentación de RabbitMQ).
  - Reinicia el servicio después de copiar el archivo.

- **El worker no procesa tareas:**
  - Verifica que el worker puede hacer ping y telnet al servidor RabbitMQ en el puerto 5672.
  - Revisa los logs del worker y del coordinador para mensajes de error.
  - Asegúrate de que las credenciales de RabbitMQ son correctas.

- **No se guardan los resultados de las imágenes:**
  - Verifica que la carpeta `results/` existe y tiene permisos de escritura.
  - Revisa los logs del coordinador para errores al guardar archivos.

---

## 🏎️ Worker asíncrono con aio-pika (`worker_async.py`)

A partir de la versión actual, el sistema soporta dos tipos de worker para procesar tareas desde RabbitMQ:

### 1. Worker tradicional (`worker.py`)
- **Tecnología:** `threading` + `pika.BlockingConnection`
- **Ventajas:**
  - Sencillo de entender y depurar.
  - Adecuado para cargas moderadas y entornos donde la compatibilidad es prioritaria.
- **Limitaciones:**
  - El Global Interpreter Lock (GIL) de Python limita el paralelismo real en tareas intensivas de CPU.
  - El consumo de recursos puede escalar menos eficientemente con muchos hilos.

### 2. Worker asíncrono (`worker_async.py`)
- **Tecnología:** `asyncio` + `aio-pika`
- **Ventajas:**
  - Mejor manejo de concurrencia y escalabilidad, especialmente en tareas I/O intensivas o cuando hay muchos mensajes pendientes.
  - Permite lanzar múltiples consumidores asíncronos, autoajustando el número de "hilos" lógicos y el prefetch según la carga y los workers activos.
  - Menor sobrecarga de contexto que el threading tradicional.
- **Limitaciones:**
  - Requiere Python 3.7+ y la librería `aio-pika`.
  - La lógica de procesamiento debe ser compatible con `asyncio`.

### ¿Cuándo usar cada uno?
- **Usa `worker.py`** si tu entorno no soporta bien `asyncio`, si prefieres un modelo clásico de hilos, o para pruebas rápidas.
- **Usa `worker_async.py`** para máxima eficiencia, especialmente si tienes muchas tareas pendientes, workers distribuidos, o buscas aprovechar mejor los recursos del sistema.

### Instalación de dependencias para el worker asíncrono

Ejecuta en la carpeta `worker/`:

```powershell
pip install aio-pika
```

### Ejecución del worker asíncrono

```powershell
python worker_async.py
```

### Recomendaciones y autoajuste
- El worker asíncrono ajusta automáticamente el número de consumidores y el prefetch según la carga y el número de workers activos.
- Puedes modificar la función `get_optimal_params()` en `worker_async.py` para personalizar la lógica de autoajuste.
- Si quieres forzar el máximo rendimiento, asegúrate de que no hay límites artificiales de CPU y que la red no es un cuello de botella.


- **Optimización de procesamiento en el worker:**
  - El worker ahora lanza automáticamente tantos hilos consumidores de RabbitMQ como núcleos de CPU tenga la máquina, para aprovechar al máximo los recursos disponibles.
  - El límite de procesamiento por uso de CPU es configurable. Si quieres medir el máximo rendimiento, puedes comentar la línea que limita el procesamiento por uso de CPU en el archivo `worker.py`:
    ```python
    # if psutil.cpu_percent(interval=1) > 95:
    #     ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    #     return
    ```
  - Esto permite que el sistema procese tareas a la máxima velocidad posible según el hardware y la red.

---
Si tienes problemas adicionales, revisa los logs de RabbitMQ y de los servicios Python, y consulta la documentación oficial de cada componente.


---

## 📚 Documentación de la API

El coordinador expone una API REST para interactuar con el sistema distribuido. Los endpoints principales son:

- `POST /upload`: Sube una imagen y genera tareas de procesamiento en la cola RabbitMQ.
- `POST /task`: (Personalizable) Permite enviar tareas personalizadas, como instrucciones de juegos retro o comandos arbitrarios. El cuerpo debe ser un JSON con los datos de la tarea.
- `GET /workers`: Devuelve el estado de todos los workers registrados.
- `GET /queue_size`: Devuelve el número de tareas pendientes en la cola.
- `GET /tps`: Devuelve el número de tareas procesadas por segundo (TPS).
- `POST /report`, `POST /register`, `POST /working`: Usados internamente por los workers para reportar estado y recursos.
- `POST /result-image`: Recibe los resultados procesados por los workers.
- `GET /result/{filename}`: Descarga el resultado de una tarea procesada.

---

## 🤝 Contribuciones y Créditos

- **Autores principal:** Josue Chaves. Josue Quesada. Joyce Ugalde. 
- 
- **Tecnologías y recursos utilizados:**
  - [FastAPI](https://fastapi.tiangolo.com/)
  - [RabbitMQ](https://www.rabbitmq.com/)
  - [aio-pika](https://aio-pika.readthedocs.io/)
  - [React](https://react.dev/)
  - [Tailscale](https://tailscale.com/)
  - [Pillow](https://python-pillow.org/)
  - [psutil](https://psutil.readthedocs.io/)
  - [uvicorn](https://www.uvicorn.org/)
  - [pika](https://pika.readthedocs.io/)
- **Agradecimientos:**
  - A la comunidad de código abierto y a los autores de las librerías utilizadas.
---

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/JosueChaves01/Sistema_Distribuido)