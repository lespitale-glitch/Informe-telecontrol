---
name: comparar-telecontrol
description: Compara la Rutina de Transmisión de TVP contra el Listado del Telecontrol del mismo día y arma el informe de artística no emitida y artística no programada. Usar cuando el usuario pase los dos PDF (rutina y telecontrol) o pida el "informe telecontrol".
---

# Informe Telecontrol

Entrada: dos PDF de Radio y Televisión Argentina S.E.
- **Rutina**: título "RUTINA DE TRANSMISION DEL DIA" (lo planificado).
- **Telecontrol**: título "LISTADO DEL TELECONTROL" (lo que salió al aire).

## Pasos (seguir en este orden, sin saltear)

1. Instalar la dependencia si falta: `pip install pypdf`
2. Correr el script con los dos PDF (el orden no importa):
   ```
   python3 scripts/comparar.py RUTINA.pdf TELECONTROL.pdf --salida informe.txt
   ```
3. Si el script corta con **"las fechas no coinciden"**, NO comparar. Avisar al usuario qué fechas trae cada PDF y frenar.
4. Mostrar el informe **tal cual lo devolvió el script**. No agregar, quitar ni reescribir renglones. No "corregir" nada a ojo.
5. Revisar la línea **Control** del final:
   - `OK`: entregar el informe.
   - `NO CUADRA` o aparece **ATENCION: renglones que no se pudieron leer**: entregar el informe igual, pero avisar arriba de todo que hay renglones para revisar a mano y listarlos.

## Prohibido

- Hacer la comparación "leyendo" los PDF sin el script.
- Inventar programas, códigos o nombres que no estén en la salida del script.
- Cambiar las reglas de `reglas/reglas.md` por cuenta propia. Si un caso parece raro, preguntarle al usuario.

## Referencias

- `reglas/reglas.md`: qué cuenta como artística, no emitida, no programada y compensada.
- `plantilla/formato_informe.md`: formato del informe.
- Ejemplos con PDF reales: no se incluyen en el repo porque es público.
