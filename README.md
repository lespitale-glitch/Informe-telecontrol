# Informe Telecontrol

Compara la **Rutina de Transmisión** con el **Listado del Telecontrol** del mismo día (RTA) y arma el informe: artística no emitida y no programada, publicidad no emitida, compensada y no programada, y diferencias de duración. Abre el resultado como correo nuevo en Thunderbird, listo para editar y enviar.

Funciona en Windows sin IA: es Python común.

## Uso
1. Instalar Python desde python.org, marcando **"Add python.exe to PATH"**.
2. Bajar este repo (botón verde **Code → Download ZIP**) y extraerlo.
3. Cargar los destinatarios en `config.txt` (`PARA=` y `CC=`).
4. Arrastrar los dos PDF del mismo día sobre **Generar informe.bat**.

## Estructura
- `scripts/comparar.py`: lee los PDF y hace la comparación. Las reglas están en `skill-claude/reglas/reglas.md`.
- `scripts/informe_windows.py`: guarda el informe y abre el correo en Thunderbird.
- `skill-claude/`: la misma herramienta empaquetada como Skill de Claude.
