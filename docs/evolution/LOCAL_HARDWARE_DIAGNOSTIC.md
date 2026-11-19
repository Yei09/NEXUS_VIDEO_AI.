# Diagnóstico local de hardware — NEXUS VIDEO AI

**Estado:** diagnóstico preliminar de arquitectura y modelos. La medición real del Lenovo está pendiente de que el usuario ejecute `scripts/diagnose-local-hardware.ps1` en Windows 11.

**Rama:** `cinematic-reconstruction`  
**HEAD de partida verificado:** `c20d172231754f71cb52528b9eb9e313cc22468a`  
**Alcance:** solo lectura. No se descargaron pesos ni se instalaron programas.

---

## 1. Hardware conocido y nivel de verificación

Los datos siguientes proceden de la descripción anterior del equipo, no de una lectura en vivo del portátil:

| Elemento | Dato conocido | Estado |
|---|---|---|
| Equipo | Lenovo V14 G4 | Pendiente de confirmar por SMBIOS |
| Sistema | Windows 11 | Pendiente de confirmar |
| CPU | AMD Ryzen 5 5500U | Pendiente de confirmar |
| CPU cores / threads | 6 / 12 | Especificación oficial del modelo, no lectura del equipo |
| RAM | 8 GB DDR4-3200 | Pendiente de confirmar; también hay que medir RAM libre |
| GPU | Radeon integrada | Pendiente de identificar el nombre exacto y driver |
| Memoria gráfica | Compartida/dinámica esperada en iGPU | Pendiente de lectura; no se debe sumar a la RAM física |

AMD publica para el Ryzen 5 5500U 6 núcleos, 12 hilos, boost de hasta 4.0 GHz, TDP predeterminado de 15 W, memoria DDR4 hasta 3200 MT/s y Radeon Graphics de 7 unidades gráficas. Esto valida que el modelo de CPU descrito existe con esas especificaciones, pero no demuestra que ese CPU siga instalado en este portátil.

Fuente: https://www.amd.com/en/support/downloads/drivers.html/processors/ryzen/ryzen-5000-series/amd-ryzen-5-5500u.html

## 2. Script de diagnóstico

Archivo: `scripts/diagnose-local-hardware.ps1`

El script consulta:
- Nombre y fabricante de CPU, núcleos físicos y procesadores lógicos.
- RAM física total y disponible.
- Memoria virtual total y disponible.
- Archivo de paginación: tamaño asignado, uso actual, pico y configuración publicada por WMI.
- Adaptadores gráficos, nombre, memoria que WMI reporta y versión del controlador.
- Contadores de memoria de GPU si la clase WMI está disponible.
- Unidades locales fijas, tamaño y espacio libre.
- Arquitectura, edición, versión y compilación de Windows.
- Presencia y versión de Python, Python Launcher, FFmpeg y Blender.

### Ejecución en Windows 11

Abre PowerShell normal, sin ejecutar como administrador, desde la carpeta del repositorio:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\diagnose-local-hardware.ps1
```

Para guardar la evidencia local como JSON:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\diagnose-local-hardware.ps1 | Tee-Object -FilePath .\hardware-diagnostic.json
```

El segundo comando crea únicamente el archivo de evidencia en la carpeta actual. El script no crea ese archivo por sí solo. `-ExecutionPolicy Bypass` se aplica a ese proceso de PowerShell y no cambia la política persistente del equipo.

**Importante:** el script no mide la capacidad de VRAM compartida máxima con fiabilidad universal. En una iGPU Radeon, la memoria se toma dinámicamente de la RAM del sistema. `AdapterRAM` de WMI puede estar limitado y no equivale a la memoria disponible para inferencia. Si Windows no expone los contadores de GPU, el informe lo dejará vacío en vez de inventar un valor.

## 3. Evaluación de modelos para el hardware conocido

Las cifras de tamaño de archivo que aparecen a continuación son las publicadas para artefactos concretos. La RAM de inferencia y el espacio de trabajo son **estimaciones de planificación**, no mediciones del Lenovo. La memoria real depende del backend, longitud de contexto, tamaño de imagen, offload, versión del runtime y procesos abiertos.

| Modelo / variante | Descarga del artefacto | RAM aproximada de proceso | Espacio libre prudente | Evaluación preliminar |
|---|---:|---:|---:|---|
| Qwen2.5-1.5B-Instruct Q4_K_M GGUF | 1.12 GB | 2–3.5 GB estimados con contexto moderado | 2–3 GB | Candidato recomendado para primera prueba CPU |
| Qwen3-4B Q4_K_M GGUF | 2.50 GB | 4.5–6.5 GB estimados | 4–5 GB | No recomendado como primera prueba con 8 GB totales |
| Qwen2.5-VL-3B Q4_K_M GGUF + proyector mmproj Q8 | 1.93 GB + 0.845 GB | 5–7 GB o más estimados, según imagen/contexto | 4–5 GB | No recomendado en 8 GB; visión puede agotar RAM |
| FLUX.1 schnell BF16 checkpoint | 23.8 GB para el checkpoint principal | No razonable en 8 GB; requiere mucha más memoria que el tamaño del archivo durante la ejecución | Más de 30 GB para checkpoint y componentes adicionales | Descartado para este equipo |
| Kokoro-82M | 327.2 MB para el peso principal `kokoro-v1_0.pth` | 1–2.5 GB estimados con runtime CPU | 2–4 GB para entorno y dependencias | Posible candidato posterior para voz, no ahora |
| ComfyUI | No hay un tamaño único; aplicación, entorno Python/PyTorch, nodos y modelos se descargan por separado | Depende del workflow; CPU es posible pero lento | Varios GB sin contar modelos; FLUX suma decenas de GB | No instalar en esta fase; no resuelve la limitación de memoria de FLUX |

### Fuentes de tamaños y licencias

- Qwen2.5-1.5B-Instruct-GGUF: el repositorio oficial lista Q4_K_M de 1.12 GB y Apache-2.0. https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF
- Qwen3-4B-GGUF: ggml-org lista Q4_K_M de 2.5 GB y Apache-2.0. https://huggingface.co/ggml-org/Qwen3-4B-GGUF
- Qwen2.5-VL-3B-GGUF: ggml-org lista Q4_K_M de 1.93 GB y el archivo mmproj Q8_0 de 845 MB; el repositorio GGUF declara Apache-2.0. https://huggingface.co/ggml-org/Qwen2.5-VL-3B-Instruct-GGUF
- Kokoro: Apache-2.0 para los pesos; el model card documenta el uso de `kokoro`, `misaki`, PyTorch y `soundfile`, y el ejemplo instala `espeak-ng`. Los componentes y voces adicionales deben revisarse por separado. https://huggingface.co/hexgrad/Kokoro-82M
- FLUX.1 schnell: Apache-2.0 y 12B parámetros; el checkpoint principal BF16 aparece con 23.8 GB en el catálogo de modelos de ComfyUI. https://huggingface.co/black-forest-labs/FLUX.1-schnell y https://github.com/Comfy-Org/ComfyUI-Manager/blob/main/model-list.json
- ComfyUI admite CPU con la opción correspondiente, pero documenta PyTorch y dependencias propias; el modo CPU no convierte FLUX en una carga práctica para un equipo con 8 GB. https://github.com/Comfy-Org/ComfyUI

## 4. Compatibilidad con CPU AMD y velocidad esperada

### Qwen2.5-1.5B Q4_K_M

- GGUF está diseñado para runtimes como llama.cpp.
- llama.cpp dispone de backend CPU para Windows x64; el Ryzen 5 5500U es una CPU AMD x86-64 de 6C/12T.
- La primera ejecución debe usar CPU y un contexto limitado (por ejemplo 2K–4K), sin GPU offload. La compatibilidad del binario concreto debe comprobarse con la CPU y el sistema detectados.
- **Velocidad esperada:** será la opción de texto más ligera de esta lista y debería ser la más viable para interacción local. No asigno tokens/segundo porque no existe un benchmark de este equipo y la frecuencia sostenida, refrigeración, memoria y backend afectan mucho el resultado.
- Riesgos: presión de RAM con muchas aplicaciones abiertas, paginación, throttling térmico y latencia creciente con contexto largo.

### Qwen3-4B Q4_K_M

- Compatible con llama.cpp en GGUF.
- Más capacidad y más memoria que 1.5B. Con 8 GB físicos, Windows, navegador y memoria compartida de iGPU compiten con el modelo.
- **Velocidad esperada:** sensiblemente más lento que 1.5B en la misma CPU.
- Riesgo principal: paginación y falta de memoria disponible. No se recomienda para primera prueba.

### Qwen2.5-VL-3B

- Requiere el GGUF principal y un proyector visual `mmproj`; no basta con descargar el archivo de 1.93 GB.
- La imagen de entrada y el procesamiento visual añaden memoria temporal.
- **Velocidad esperada:** más lenta que el modelo de texto; depende también de resolución y número de recortes.
- No se recomienda en este equipo hasta conocer RAM disponible, pagefile y comportamiento de memoria.

### FLUX.1 schnell y ComfyUI

- FLUX.1 schnell tiene 12B parámetros y su checkpoint BF16 principal ocupa 23.8 GB; además necesita VAE y codificadores de texto según el workflow.
- La Radeon integrada comparte RAM y no equivale a una GPU discreta con VRAM propia. El soporte AMD de PyTorch/ComfyUI en Windows depende de la generación y backend exactos; no se debe asumir que esta iGPU tendrá aceleración compatible.
- ComfyUI puede ejecutarse en CPU, pero la generación con FLUX en CPU y 8 GB no es una opción práctica.
- **Velocidad esperada:** no viable para uso razonable en este portátil con la configuración conocida.

### Kokoro TTS

- 82M parámetros; el peso principal es mucho menor que los modelos de lenguaje e imagen.
- Requiere runtime Python/PyTorch, paquetes de Kokoro/Misaki y dependencias de fonemización/audio según idioma y pipeline.
- **Velocidad esperada:** podría ser utilizable en CPU para síntesis por lotes o fragmentos, pero debe medirse con el paquete y voz concretos.
- No se declara instalado ni probado.

## 5. Recomendación provisional

**Modelo elegido para la primera inferencia real, sujeto a confirmar el diagnóstico:**  
`Qwen2.5-1.5B-Instruct Q4_K_M GGUF` (archivo de aproximadamente 1.12 GB).

Condiciones previas:
1. Confirmar Windows 11 x64 y CPU real.
2. Confirmar RAM total y libre al cerrar aplicaciones innecesarias.
3. Confirmar espacio libre en la unidad destino.
4. Comprobar que el pagefile está habilitado y conocer su tamaño actual.
5. Confirmar que no hay una carga de trabajo pesada activa.

Como umbral conservador de planificación, buscar al menos unos 3 GB de RAM física disponible antes de cargar el modelo; más margen es preferible. Esto es una recomendación prudencial, no un requisito oficial del modelo. Si el reporte muestra menos margen o un pagefile muy activo, posponer la prueba.

No se elige Qwen3-4B ni Qwen2.5-VL para esta primera prueba. FLUX.1 schnell queda descartado para 8 GB. Kokoro puede evaluarse en una fase separada.

## 6. Seguridad y evidencia

Revisión estática del script:
- No contiene URLs, direcciones IP, clientes HTTP ni llamadas a APIs.
- No contiene comandos de descarga.
- No contiene instaladores ni gestores de paquetes.
- No escribe en el registro.
- No modifica variables de entorno.
- No inicia procesos servidor.
- Solo invoca los comandos locales de versión de Python, FFmpeg y Blender, si existen en PATH.
- Las consultas de hardware usan CIM/WMI local.

**Límite de evidencia:** el script se ha añadido al repositorio, pero no se ha ejecutado en el Lenovo del usuario. No existe todavía una lectura real de CPU, RAM libre, pagefile, GPU, unidades ni herramientas instaladas. La evidencia de ejecución debe ser el JSON generado localmente por el usuario. Una ejecución en GitHub Actions no sustituye esa medición.

## 7. Próximos pasos

1. Ejecutar el script y compartir `hardware-diagnostic.json`.
2. Revisar los valores reales y actualizar este informe con fecha, mediciones y limitaciones.
3. Solo después de que el usuario revise y autorice la descarga, preparar llama.cpp para Windows x64 y descargar un único archivo GGUF Q4_K_M.
4. Ejecutar una inferencia corta local, con contexto limitado, monitorizando RAM libre, uso de CPU, memoria de proceso, latencia y tokens/segundo.
5. Marcar el modelo como verificado únicamente si produce una respuesta real y se conservan los datos del benchmark.

### Comando previsto para la futura prueba (NO ejecutar todavía)

Cuando el usuario haya autorizado la instalación de llama.cpp y la descarga del modelo, la prueba de servidor local sería:

```powershell
.\llama-server.exe -m "C:\NEXUS\models\qwen2.5-1.5b-instruct-q4_k_m.gguf" -c 4096 -t 6 --host 127.0.0.1 --port 8080
```

Este comando presupone que el ejecutable y el archivo GGUF ya existen en esas rutas. No se han descargado ni instalado. No se debe ejecutar en esta fase.
