import psutil
import platform
import os
import subprocess
import requests

LHM_URL = "http://localhost:8085/data.json"

def get_lhm_data():
    """Obtiene todos los datos de LibreHardwareMonitor."""
    try:
        r = requests.get(LHM_URL, timeout=3)
        return r.json()
    except:
        return None

def buscar_sensor(nodo, nombre_buscar, tipo_buscar=None):
    """Busca un sensor por nombre recursivamente."""
    resultados = []
    if isinstance(nodo, dict):
        if "Text" in nodo and "Value" in nodo:
            texto = nodo.get("Text", "")
            tipo  = nodo.get("Type", "")
            if nombre_buscar.lower() in texto.lower():
                if tipo_buscar is None or tipo_buscar.lower() in tipo.lower():
                    resultados.append(nodo)
        for child in nodo.get("Children", []):
            resultados.extend(buscar_sensor(child, nombre_buscar, tipo_buscar))
    elif isinstance(nodo, list):
        for item in nodo:
            resultados.extend(buscar_sensor(item, nombre_buscar, tipo_buscar))
    return resultados

def get_todos_sensores(nodo, tipo_filtro=None):
    """Obtiene todos los sensores de un tipo."""
    resultados = []
    if isinstance(nodo, dict):
        sensor_type = nodo.get("Type", "")
        if "Value" in nodo and "Text" in nodo:
            if tipo_filtro is None or tipo_filtro.lower() in sensor_type.lower():
                resultados.append({
                    "nombre": nodo.get("Text",""),
                    "valor":  nodo.get("Value",""),
                    "min":    nodo.get("Min",""),
                    "max":    nodo.get("Max",""),
                    "tipo":   sensor_type
                })
        for child in nodo.get("Children", []):
            resultados.extend(get_todos_sensores(child, tipo_filtro))
    elif isinstance(nodo, list):
        for item in nodo:
            resultados.extend(get_todos_sensores(item, tipo_filtro))
    return resultados

def limpiar_valor(v):
    """Limpia el valor devuelto por LHM (quita unidades raras)."""
    if not v:
        return "?"
    return str(v).strip()

def get_temperaturas():
    data = get_lhm_data()
    if not data:
        try:
            r = subprocess.run(
                ["nvidia-smi","--query-gpu=name,temperature.gpu","--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                p = [x.strip() for x in r.stdout.strip().split(",")]
                return f"La GPU está a {p[1]} grados. Para más datos abre LibreHardwareMonitor."
        except:
            pass
        return "LibreHardwareMonitor no está activo."

    sensores = get_todos_sensores(data, "Temperature")
    if not sensores:
        return "No encontré sensores de temperatura."

    # Extraer solo los más importantes
    cpu_temp = gpu_temp = gpu_hot = ram_temp = ssd_temp = None
    for s in sensores:
        n = s["nombre"].lower()
        v = limpiar_valor(s["valor"]).replace(",",".").split()[0]
        try: v_num = float(v)
        except: continue
        if "tctl" in n or "tdie" in n and "ccd" not in n:
            if not cpu_temp: cpu_temp = v_num
        if "gpu core" in n and not gpu_temp:
            gpu_temp = v_num
        if "gpu hot spot" in n and not gpu_hot:
            gpu_hot = v_num
        if "dimm #0" in n and not ram_temp:
            ram_temp = v_num
        if "composite temperature" in n and not ssd_temp:
            ssd_temp = v_num

    partes = []
    if cpu_temp: partes.append(f"CPU a {cpu_temp:.0f} grados")
    if gpu_temp: partes.append(f"GPU a {gpu_temp:.0f} grados")
    if gpu_hot:  partes.append(f"punto caliente GPU {gpu_hot:.0f} grados")
    if ram_temp: partes.append(f"RAM a {ram_temp:.0f} grados")
    if ssd_temp: partes.append(f"SSD a {ssd_temp:.0f} grados")

    if not partes:
        return "No pude leer las temperaturas."
    return "Ahora mismo tienes: " + ", ".join(partes) + "."

def get_gpu_info():
    data = get_lhm_data()
    gpu_temp = gpu_load = gpu_vram_used = gpu_vram_total = gpu_hotspot = None

    if data:
        sensores = get_todos_sensores(data)
        for s in sensores:
            n = s["nombre"].lower()
            tp = s["tipo"].lower()
            if "gpu core" in n and "temperature" in tp and not gpu_temp:
                gpu_temp = limpiar_valor(s["valor"])
            if "gpu hot spot" in n and not gpu_hotspot:
                gpu_hotspot = limpiar_valor(s["valor"])
            if "gpu core" in n and "load" in tp and not gpu_load:
                gpu_load = limpiar_valor(s["valor"])
            if "gpu memory used" in n and "data" in tp and not gpu_vram_used:
                gpu_vram_used = limpiar_valor(s["valor"])
            if "gpu memory total" in n and not gpu_vram_total:
                gpu_vram_total = limpiar_valor(s["valor"])

    if gpu_temp:
        # Detectar el nombre real de la GPU desde los sensores
        nombre_gpu = "GPU"
        if data:
            for s in get_todos_sensores(data):
                tp = s["tipo"].lower()
                nm = s["nombre"]
                if "gpu" in nm.lower() and ("nvidia" in nm.lower() or "amd" in nm.lower() or "radeon" in nm.lower() or "geforce" in nm.lower() or "rtx" in nm.lower() or "gtx" in nm.lower()):
                    nombre_gpu = nm
                    break
        resultado = f"{nombre_gpu}: temperatura {gpu_temp}"
        if gpu_hotspot: resultado += f", hotspot {gpu_hotspot}"
        if gpu_load:    resultado += f", uso {gpu_load}"
        if gpu_vram_used and gpu_vram_total:
            resultado += f", VRAM {gpu_vram_used} de {gpu_vram_total}."
        return resultado

    # Fallback nvidia-smi solo si LHM no tiene datos
    try:
        r = subprocess.run(
            ["nvidia-smi","--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            p = [x.strip() for x in r.stdout.strip().split(",")]
            return f"GPU {p[0]}: {p[1]}°C, uso {p[2]}%, VRAM {p[3]}MB de {p[4]}MB."
    except:
        pass
    return "No pude leer la GPU."

def get_cpu_info():
    data = get_lhm_data()
    # Detectar el nombre real de la CPU
    try:
        nombre = platform.processor() or "CPU"
        # En Windows, platform.processor() a veces devuelve algo genérico; probar wmi
        if not nombre or "family" in nombre.lower():
            try:
                import wmi
                nombre = wmi.WMI().Win32_Processor()[0].Name.strip()
            except Exception:
                nombre = "CPU"
    except Exception:
        nombre = "CPU"
    uso = psutil.cpu_percent(interval=1)
    freq = psutil.cpu_freq()
    nucleos = psutil.cpu_count(logical=False)
    hilos   = psutil.cpu_count(logical=True)

    temp_cpu = None
    if data:
        todos = get_todos_sensores(data)
        for s in todos:
            n = s["nombre"].lower()
            t = s["tipo"].lower()
            if ("tctl" in n or "tdie" in n or "core (tctl" in n) and "temperature" in t:
                temp_cpu = limpiar_valor(s["valor"])
                break
    if not temp_cpu:
        # Fallback: buscar cualquier temperatura de CPU
        if data:
            for s in get_todos_sensores(data):
                n = s["nombre"].lower()
                t = s["tipo"].lower()
                if "temperature" in t and ("cpu" in n or "core" in n or "ccd" in n):
                    temp_cpu = limpiar_valor(s["valor"])
                    break

    resultado = f"CPU {nombre}: {nucleos} núcleos, {hilos} hilos"
    if freq:
        resultado += f", {freq.current:.0f} MHz"
    resultado += f", uso {uso}%"
    if temp_cpu:
        resultado += f", temperatura {temp_cpu}"
    return resultado + "."

def get_ram_info():
    ram  = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return (f"RAM: {ram.total/1024**3:.1f} GB totales, "
            f"{ram.used/1024**3:.1f} GB usados ({ram.percent}%), "
            f"{ram.available/1024**3:.1f} GB libres. "
            f"Swap: {swap.total/1024**3:.1f} GB.")

def get_discos_info():
    data = get_lhm_data()
    discos_hw = {}

    if data:
        # Extraer info de discos desde LHM
        def buscar_discos(nodo, disco_actual=None):
            if isinstance(nodo, dict):
                texto = nodo.get("Text", "")
                # Detectar nodo de disco
                if any(d in texto for d in ["KINGSTON", "WDC", "Samsung", "Seagate", "Toshiba", "Crucial"]):
                    disco_actual = texto
                    discos_hw[disco_actual] = {}

                if disco_actual and "Value" in nodo:
                    nombre = nodo.get("Text","").lower()
                    if "life" in nombre:
                        discos_hw[disco_actual]["vida"] = limpiar_valor(nodo["Value"])
                    if "temperature" in nombre and "composite" not in nombre:
                        discos_hw[disco_actual]["temp"] = limpiar_valor(nodo["Value"])
                    if "composite temperature" in nombre:
                        discos_hw[disco_actual]["temp"] = limpiar_valor(nodo["Value"])
                    if "used space" in nombre:
                        discos_hw[disco_actual]["uso"] = limpiar_valor(nodo["Value"])
                    if "free space" in nombre and "data" in nodo.get("Type","").lower():
                        discos_hw[disco_actual]["libre"] = limpiar_valor(nodo["Value"])
                    if "total space" in nombre:
                        discos_hw[disco_actual]["total"] = limpiar_valor(nodo["Value"])

                for child in nodo.get("Children", []):
                    buscar_discos(child, disco_actual)
            elif isinstance(nodo, list):
                for item in nodo:
                    buscar_discos(item, disco_actual)

        buscar_discos(data)

    # Info de particiones con psutil
    partes = []
    for p in psutil.disk_partitions():
        try:
            uso = psutil.disk_usage(p.mountpoint)
            partes.append(
                f"Disco {p.device}: {uso.total/1024**3:.0f} GB totales, "
                f"{uso.used/1024**3:.0f} GB usados, "
                f"{uso.free/1024**3:.0f} GB libres ({uso.percent}% usado)"
            )
        except:
            pass

    resultado = " | ".join(partes)

    # Añadir salud de discos si tenemos datos LHM
    if discos_hw:
        salud = []
        for nombre, info in discos_hw.items():
            s = nombre
            if "vida" in info: s += f" vida {info['vida']}"
            if "temp" in info: s += f" temp {info['temp']}"
            salud.append(s)
        resultado += ". Estado discos: " + ", ".join(salud) + "."

    return resultado

def get_temperaturas_completas():
    """Versión detallada para cuando pide todas las temperaturas."""
    return get_temperaturas()

def get_procesos_top():
    procs = []
    for p in psutil.process_iter(['pid','name','cpu_percent','memory_info']):
        try:
            procs.append(p.info)
        except:
            pass
    procs = sorted(procs, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:5]
    resultado = []
    for p in procs:
        ram_mb = (p['memory_info'].rss/1024**2) if p['memory_info'] else 0
        resultado.append(f"{p['name']} (PID {p['pid']}): CPU {p['cpu_percent']}%, RAM {ram_mb:.0f} MB")
    return "Procesos más activos: " + " | ".join(resultado)

def get_red_info():
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    activas = []
    for iface, stat in stats.items():
        if stat.isup:
            ips = [a.address for a in addrs.get(iface,[]) if '.' in a.address and not a.address.startswith('169')]
            if ips:
                activas.append(f"{iface}: {', '.join(ips)}")
    return "Interfaces activas: " + (", ".join(activas) if activas else "ninguna.")

def get_sistema_info():
    try:
        import wmi
        w = wmi.WMI()
        os_info  = w.Win32_OperatingSystem()[0]
        cpu_info = w.Win32_Processor()[0]
        nombre_os  = os_info.Caption.strip()
        arq        = os_info.OSArchitecture.strip()
        cpu_nombre = cpu_info.Name.strip()
        try:
            placa = w.Win32_BaseBoard()[0].Product.strip()
        except:
            placa = "desconocida"
        return f"Sistema: {nombre_os} {arq}. CPU: {cpu_nombre}. Placa: {placa}."
    except:
        return f"Sistema: {platform.system()} {platform.release()}."

def get_todo():
    return "\n".join([
        get_sistema_info(),
        get_cpu_info(),
        get_ram_info(),
        get_gpu_info(),
        get_discos_info(),
        get_red_info(),
    ])
