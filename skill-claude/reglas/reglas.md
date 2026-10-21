# Reglas del informe

Estas reglas salen del informe hecho a mano del 06/10/26 y están programadas en `scripts/comparar.py`.

## Antes de comparar
- La fecha de la rutina ("Martes 06/10/26") tiene que ser igual a la del telecontrol ("Correspondiente a la Fecha: 06/10/26"). Si no, no se compara.

## Qué es "artística" (rutina)
- Renglones dentro del bloque de un programa con **código de material desde 50000** (PNT, barridas, placas, zócalos, spots, auspicios, menciones "M").
- **No** cuenta lo que está dentro de un CORTE (tanda comercial y promos FILESERV).
- **Cada aparición cuenta**: si un código está 2 veces en el mismo programa, tienen que salir 2. Ej. 10/10: ZOCALO GDM y PNT GDM estaban 2 veces cada uno en Aires de Campo y no salió ninguno, entonces faltan 2 de cada uno.

## ARTISTICA NO EMITIDA
- El código programado en un programa no aparece en el telecontrol **de ese mismo programa** (se identifica por el número de programa, ej. 6115).
- Que haya salido en otro programa donde también estaba programado **no** lo salva. Ejemplo del 06/10: BARRIDA QUINI 6 salió en MBA (donde estaba programada) pero no en Iluminadas, entonces Iluminadas la tiene como no emitida.

## ARTISTICA COMPENSADA EN OTRO PROGRAMA
- No salió en su programa, pero en otro programa salió **más veces de las que estaba programada allí**. Ese excedente se toma como compensación.
- El 06/10 no hubo ninguna.

## ARTISTICA NO PROG
- Programas donde el telecontrol muestra renglones de **tipo 1003, 1005 o 1006 sin código de material** (o marcados "NO PROG.EN RUTINA"). Ej. 10/10: 943 Claves para un mundo mejor tiene auspicios 1003 sin código.
- No cuentan los tipo 1001 sin código (placas/menciones sueltas) ni los 9999 (invitados).
- También es no programada la **artística con código** (tipos 1001 a 1006) que salió en un programa donde no estaba en la rutina, o salió más veces de las programadas, y no compensa a ningún otro programa. Ej. 13/10: 9 YUYOS YERBA MATE PNT (967808) salió en Andino y no estaba en la rutina. Se muestra con el código entre paréntesis.
- No cuenta el propio programa marcado con su código (ej. CAPSULA LOTO 967338 en el programa CAPSULA LOTO).

## Excepciones (completar si hace falta)
- Códigos a ignorar siempre: ninguno por ahora. Se agregan en `EXCLUIR_CODIGOS` dentro del script.

## PUBLICIDAD (avisos de tanda)
- La rutina puede venir en dos formatos: el viejo (`20" SECCO VASOS 20  40004  106944`) y el nuevo, con número de evento y código `PA-CO` (`45 2.84 20" SECCO VASOS 20 PA-CO040004`). Se leen los dos; los `PA-PR` y `PA-ID` son promos/IDs y no cuentan.
- En la rutina: renglones **dentro de los CORTES** que no son FILESERV y tienen código + número de orden (ej. `20" SECCO VASOS 20  40004  106944`).
- En el telecontrol: renglones de **tipo 1020 y 1030**.
- Se cuentan por programa y **cada aparición cuenta** (si SECCO está 2 veces en un programa, tienen que salir 2).
- **PUBLICIDAD NO EMITIDA**: programada en un programa y no salió ahí ni salió de más en otro.
- **PUBLICIDAD COMPENSADA EN OTRO PROGRAMA**: faltó en su programa pero salió de más en otro. Ej. 06/10: SECCO de Feliz Vida 6055 salió en TVP Noticias Noche 4599 (marcado F.O.P.).
- **PUBLICIDAD NO PROGRAMADA**: tipo 1020 que salió de más en un programa y no compensa a ninguno, o que salió sin código.

## ARTISTICA NO PROG (formato)
- Primero una línea con los programas que tuvieron algo no programado, cada uno una sola vez, separados por coma (en orden de la rutina).
- Después el detalle de todo lo que salió sin programar, con la cantidad total.

## DIFERENCIA DE DURACION
- Avisos de tanda del telecontrol (tipos 1020 y 1030) cuya duración real no coincide con la que figura en la rutina para ese código. Se lista cada uno con programada, emitida y diferencia en segundos.
