import psutil
import time

# Primero obtenemos el porcentaje de uso de la CPU
def get_cpu_usage():
    prev = psutil.cpu_times_percent(interval=None)  # Primero medimos
    time.sleep(0.1)  # Esperamos un pequeño intervalo de 0.1 segundos
    curr = psutil.cpu_times_percent(interval=None)  # Después medimos nuevamente

    # Calculamos la diferencia de CPU usada
    total_diff = (curr.user - prev.user) + (curr.system - prev.system)  # Usuarios y sistema
    total_time = sum(curr) - sum(prev)

    # Calculamos el uso
    cpu_usage = (total_diff / total_time) * 100
    return cpu_usage

print(f"Uso de la CPU: {get_cpu_usage():.2f}%")