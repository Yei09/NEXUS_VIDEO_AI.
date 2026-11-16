# NEXUS VIDEO AI — Reconstrucción cinematográfica

Estado: diseño técnico inicial; todavía no es una implementación aceptada ni un render de aceptación.

## Rama y punto de partida

- Rama de reconstrucción: `cinematic-reconstruction`
- Base exacta: `ebd96b250bd78b2e408e30146ac9435264310a17` (`v4.2.1-cinematic-depth`)
- V4.2 permanece fuera de esta rama y no se modifica.
- No se conecta Make ni Google Drive. No se programan ejecuciones ni publicaciones.

## Auditoría confirmada

El motor actual usa Pillow para dibujar cada escena sobre una imagen RGBA/RGB y FFmpeg para codificar secuencias. `cinematic_depth_v421.py` agrega sprites RGBA sobre esa placa. La placa de arquitectura continúa aplanada; por eso el compositor no puede recuperar profundidad ni movimiento de paredes, muebles y arquitectura ya rasterizados.

El personaje actual es una silueta geométrica, no un rig reutilizable. El audio de efectos calcula el comienzo con `event_start + 0.25s`, no con marcadores de acción. El workflow actual limita la generación a 30–60 s, pero no incluye una aceptación específica de 60 s con tres fotogramas por escena y secuencias consecutivas.

Las 25 pruebas existentes verifican propiedades parciales del render, pero no prueban continuidad temporal del rig, identidad entre escenas, colisiones, sincronía por marcador ni movimiento independiente de todos los objetos. Se conservan; no deben considerarse suficientes para aceptar la reconstrucción.

## Arquitectura objetivo

La reconstrucción se divide en cuatro capas con contratos explícitos:

1. **Historia y planificación**: cada beat contiene escena, sujeto, acción, objeto objetivo, estado inicial/final, duración, cámara y marcadores audiovisuales expresados en segundos relativos al beat.
2. **Escena 3D/2.5D real**: grafo de objetos con geometría y materiales independientes. Arquitectura, suelo, mobiliario, personaje, props, luces, sombras y partículas son entidades distintas. Ningún manifiesto puede declarar movimiento si la transformación observada en los fotogramas no cambia.
3. **Cinematografía**: cámara con focal, encuadre, target, trayectoria y foco; los movimientos se derivan de acciones y no de un zoom genérico. La profundidad debe proceder de geometría/planos reales, no de desplazar una única imagen de fondo.
4. **Audio y entrega**: Piper mantiene la narración; música y efectos se programan usando marcadores temporales de acción. FFmpeg monta el vídeo, subtítulos y mezcla, y FFprobe valida el contenedor final.

## Decisión de renderizado y límite de infraestructura

Pillow + FFmpeg son adecuados para composición, subtítulos, audio, validación y codificación, pero no son por sí solos un motor 3D ni un generador de personajes realistas. La opción gratuita que merece una prueba técnica es Blender en modo headless, con escenas procedurales y render CPU; no se debe asumir que el runner de GitHub dispone de GPU. El primer prototipo debe medir instalación, compatibilidad del backend de render y tiempo por fotograma antes de migrar el pipeline completo.

No se debe degradar silenciosamente a imágenes aplanadas si Blender falla. La prueba debe terminar con un error explícito de infraestructura o renderer no disponible. Una secuencia 2.5D puede servir como fallback opcional, pero no satisface por sí sola la aceptación cinematográfica solicitada.

## Contratos de evidencia

- Movimiento de entidad: transformación mundial y bounds de píxeles medidos en varios fotogramas; delta cero repetido implica entidad estática.
- Personaje: identificador persistente, proporciones/vestuario/materiales bloqueados y métricas visuales por escena.
- Continuidad: secuencia de fotogramas consecutivos y seguimiento de articulaciones/centroide, no solo tres muestras aisladas.
- Profundidad: al menos tres planos geométricos con desplazamientos relativos coherentes bajo movimiento de cámara.
- Audio: cada efecto referencia un `action_marker` y el informe compara el instante renderizado del marcador visual con el inicio real del efecto.
- Entrega: MP4 de 60 s, 1080×1920, 30 FPS, H.264/AAC, delta A/V máximo 0.15 s, tres fotogramas auténticos por escena y clips consecutivos.

## Umbrales protegidos

- Diversidad visual mínima: 7.0.
- Movimiento mínimo: 1.25.
- Diferencia de duración y A/V: máximo 0.15 s.
- Seis escenas narrativamente conectadas.
- Se mantienen las 25 pruebas existentes; las nuevas pruebas se agregan sin debilitar ni borrar las anteriores.

## Criterio de estado

La rama y este documento representan preparación y diseño, no una reconstrucción terminada. No se aprobará el motor hasta que exista un render de 60 segundos, informes reproducibles, pruebas completas y revisión de fotogramas y secuencias del MP4 real.