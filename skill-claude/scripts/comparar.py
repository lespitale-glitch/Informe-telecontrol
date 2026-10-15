#!/usr/bin/env python3
"""
Compara la Rutina de Transmisión contra el Listado del Telecontrol (RTA).

Uso:
    python3 comparar.py RUTINA.pdf TELECONTROL.pdf [--salida informe.txt] [--json datos.json]

El orden de los PDF no importa: el script detecta cuál es cuál por el título.
Requiere: pip install pypdf
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("Falta pypdf. Instalalo con:  pip install pypdf")

# --- Reglas (ver reglas/reglas.md) -------------------------------------------
CODIGO_ARTISTICO_MIN = 50000          # material desde 50000 = artística a emitir en el bloque del programa
TIPOS_PUBLICIDAD = {"1020", "1030"}    # en telecontrol: avisos comerciales de tanda
TIPOS_NO_PROG = {"1003", "1005", "1006"}       # en telecontrol: PNT/menciones; si vienen SIN código, son "no programadas"
EXCLUIR_CODIGOS = set()                # códigos a ignorar siempre (completar en reglas si hace falta)

HORA = r"\d{1,2}:\d{2}:\d{2}"


def texto_pdf(ruta):
    lector = PdfReader(str(ruta))
    texto = "\n".join((p.extract_text() or "") for p in lector.pages)
    # El PDF a veces parte las horas ("0:00 :45", "1:15:4 7"): se reparan
    texto = re.sub(r"(\d) ?: ?(\d)", r"\1:\2", texto)
    texto = re.sub(r"(\d{1,2}:\d{2}:\d)\s+(\d)(?!\d)", r"\1\2", texto)
    texto = re.sub(r"(\d{1,2}:\d)\s+(\d:\d{2})", r"\1\2", texto)
    return texto


def normalizar(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


# --- RUTINA ------------------------------------------------------------------
RE_FECHA_RUTINA = re.compile(r"(Lunes|Martes|Mi.rcoles|Jueves|Viernes|S.bado|Domingo)\s+(\d{2}/\d{2}/\d{2})")
RE_PROGRAMA = re.compile(r"^\s*(?P<hora>\d{1,2}:\d{2})\s+(?:[\d*]+'\s*(?:\d+\")?\s+|\*+\"\s+)?(?P<cod>\d{2,5})\s+(?P<nom>\S.*)$")
RE_PUBLI = re.compile(r"(?P<dur>\d+)\"\s+(?P<desc>.+?)\s+(?P<cod>\d{4,6})\s+(\d{6})\s*$")   # aviso en tanda: código + n° de orden
RE_ITEM = re.compile(r"(?P<dur>\d+)\"\s+(?P<desc>.+?)\s+(?P<cod>\d{5,7})(?:\s+\d{5,7})?\s*$")


def leer_rutina(texto):
    m = RE_FECHA_RUTINA.search(texto)
    fecha = m.group(2) if m else None
    programas = {}          # codigo -> nombre
    planificado = []        # dicts: programa, nombre_prog, codigo, descripcion
    actual = None
    en_corte = False
    sin_leer = []
    publicidad = []         # avisos comerciales dentro de los cortes
    horas = {}              # programa -> hora de inicio en la rutina
    for linea in texto.splitlines():
        if "FIN DE RUTINA" in linea:
            break
        mp = RE_PROGRAMA.match(linea)
        if mp and "CORTE NRO" not in linea and "PARTE NRO" not in linea:
            actual = mp.group("cod")
            programas[actual] = mp.group("nom").strip()
            horas[actual] = mp.group("hora")
            en_corte = False
            continue
        if "CORTE NRO" in linea:
            en_corte = True
            continue
        if "Duraci" in linea and "Corte" in linea:
            en_corte = False
            continue
        if actual is None or "FILESERV" in linea:
            continue
        if en_corte:
            mpub = RE_PUBLI.search(linea)
            if mpub:
                publicidad.append({"programa": actual, "nombre_programa": programas[actual],
                                   "codigo": mpub.group("cod"), "descripcion": mpub.group("desc").strip(),
                                   "hora": horas[actual], "dur": mpub.group("dur") + '"'})
            continue
        mi = RE_ITEM.search(linea)
        if not mi:
            if re.search(r"\b9\d{5}\b", linea) or re.fullmatch(r"\s*(?:[\d.]+\s*[tc]?\s+|M\s+)?\d+\"\s*", linea):
                sin_leer.append(linea.strip())   # parece artística pero el renglón vino cortado
            continue
        codigo = mi.group("cod")
        if int(codigo) < CODIGO_ARTISTICO_MIN or codigo in EXCLUIR_CODIGOS:
            continue
        planificado.append({
            "programa": actual,
            "nombre_programa": programas[actual],
            "codigo": codigo,
            "descripcion": mi.group("desc").strip(),
            "hora": horas[actual],
            "dur": mi.group("dur") + '"',
        })
    return fecha, programas, planificado, sin_leer, publicidad


# --- TELECONTROL -------------------------------------------------------------
RE_FECHA_TC = re.compile(r"Correspondiente a la Fecha:\s*(\d{2}/\d{2}/\d{2})")
RE_BLOQUE = re.compile(rf"^\s*\**\s*({HORA})\s+({HORA})\s+([BCE])\s+(\d+)\s+(\d+)\s+(.+?)\s+{HORA}")
RE_INICIO_FILA = re.compile(rf"^\s*\**\s*{HORA}\s+{HORA}\s+\S")
RE_FILA_VACIA = re.compile(rf"^\s*{HORA}\s+{HORA}\s+\d+\s*$")
RE_FILA = re.compile(rf"^\s*({HORA})\s+({HORA})\s+(\d{{2,4}})\s+(?:(\d{{4,7}})\s+)?(.+?)\s+({HORA})(?:\s+(.*))?$")


def leer_telecontrol(texto):
    m = RE_FECHA_TC.search(texto)
    fecha = m.group(1) if m else None
    nombres = {}
    emitido = defaultdict(Counter)      # programa -> Counter(codigo)
    no_prog = defaultdict(list)         # programa -> [descripciones]
    actual = None
    sin_leer = []                       # renglones que parecen datos pero no se pudieron leer
    publi = defaultdict(list)           # programa -> [(codigo, descripcion, hora, obs)] tipo 1020
    for linea in texto.splitlines():
        mb = RE_BLOQUE.match(linea)
        if mb:
            actual = mb.group(5)
            nombres.setdefault(actual, mb.group(6).strip())
            continue
        mf = RE_FILA.match(linea)
        if not mf:
            if RE_INICIO_FILA.match(linea) and not RE_FILA_VACIA.match(linea):
                sin_leer.append(linea.strip())
            continue
        if actual is None:
            continue
        tipo, codigo, desc, obs = mf.group(3), mf.group(4), mf.group(5).strip(), (mf.group(7) or "")
        if tipo in TIPOS_PUBLICIDAD:
            publi[actual].append((codigo, desc, mf.group(1), obs.strip(), mf.group(6), tipo))
            continue
        if codigo:
            emitido[actual][codigo] += 1
        if tipo in TIPOS_NO_PROG and (not codigo or "NO PROG" in obs.upper()):
            no_prog[actual].append(f"{desc}  [{mf.group(1)}]")
    return fecha, nombres, emitido, no_prog, sin_leer, publi


# --- COMPARACIÓN -------------------------------------------------------------
def comparar(rutina_txt, tc_txt):
    f_r, progs_r, plan, sin_leer_r, publi_plan = leer_rutina(rutina_txt)
    f_t, progs_t, emitido, no_prog, sin_leer, publi_emit = leer_telecontrol(tc_txt)

    # Cada aparición cuenta: si un código está 2 veces en un programa, tienen que salir 2
    plan_count = defaultdict(Counter)
    for it in plan:
        plan_count[it["programa"]][it["codigo"]] += 1
    excedente = defaultdict(Counter)      # lo que salió de más en cada programa
    for q in emitido:
        for c, n in emitido[q].items():
            if n > plan_count[q][c]:
                excedente[q][c] = n - plan_count[q][c]

    emitidos, no_emitidos, compensados = [], [], []
    usados = Counter()                    # por (programa, código): cuántas apariciones ya se contaron
    for it in plan:
        p, c = it["programa"], it["codigo"]
        usados[(p, c)] += 1
        if usados[(p, c)] <= emitido[p][c]:
            emitidos.append(it)
            continue
        q = next((q for q in excedente if q != p and excedente[q][c] > 0), None)
        if q:
            excedente[q][c] -= 1
            compensados.append({**it, "programa_emision": q,
                                "nombre_programa_emision": progs_t.get(q, progs_r.get(q, q))})
        else:
            no_emitidos.append(it)
    unicos = plan

    pub = comparar_publicidad(publi_plan, publi_emit, progs_r, progs_t)

    total = len(unicos)
    cuadra = total == len(emitidos) + len(no_emitidos) + len(compensados)
    return {
        "fecha_rutina": f_r, "fecha_telecontrol": f_t,
        "misma_fecha": f_r is not None and f_r == f_t,
        "total_artistica": total, "emitidos": len(emitidos),
        "no_emitidos": no_emitidos, "compensados": compensados,
        "no_prog": [{"programa": p, "nombre_programa": progs_r.get(p, progs_t.get(p, p)), "items": v}
                    for p, v in sorted(no_prog.items(), key=lambda x: list(progs_r).index(x[0]) if x[0] in progs_r else 999)],
        "publicidad": pub,
        "cuadra": cuadra and pub["cuadra"] and not sin_leer and not sin_leer_r,
        "renglones_sin_leer": sin_leer,
        "renglones_sin_leer_rutina": sin_leer_r,
    }


def comparar_publicidad(plan, emit, progs_r, progs_t):
    """Avisos de tanda: se cuentan por programa (cada aparición cuenta)."""
    nombre = lambda p: progs_r.get(p, progs_t.get(p, p))
    plan_c, desc, info = defaultdict(Counter), {}, {}
    for it in plan:
        plan_c[it["programa"]][it["codigo"]] += 1
        desc[it["codigo"]] = it["descripcion"]
        info[(it["programa"], it["codigo"])] = (it.get("hora", ""), it.get("dur", ""))
    emit_c, sin_codigo, obs = defaultdict(Counter), [], {}
    for p, filas in emit.items():
        for codigo, d, hora, o, _dur, _tipo in filas:
            if "F.O.P" in o.replace(" ", ""):
                o = "F.O.P. (fuera de orden)"
            if codigo:
                emit_c[p][codigo] += 1
                desc.setdefault(codigo, d)
                obs.setdefault((p, codigo), []).append((hora, o))
            else:
                sin_codigo.append({"programa": p, "nombre_programa": nombre(p), "codigo": "",
                                   "descripcion": d, "hora": hora, "obs": o})

    faltan, sobran = [], []
    for p in sorted(set(plan_c) | set(emit_c), key=lambda x: int(x)):
        for c in sorted(set(plan_c[p]) | set(emit_c[p])):
            dif = plan_c[p][c] - emit_c[p][c]
            for _ in range(max(dif, 0)):
                hp, dp = info.get((p, c), ("", ""))
                faltan.append({"programa": p, "nombre_programa": nombre(p), "codigo": c, "descripcion": desc[c],
                               "hora_prog": hp, "dur": dp})
            for k in range(max(-dif, 0)):
                # el que sobra suele ser el marcado fuera de orden: se lo prioriza
                horas = sorted(obs.get((p, c), []), key=lambda x: "F.O.P" not in x[1])
                h, o = horas[k] if k < len(horas) else ("", "")
                sobran.append({"programa": p, "nombre_programa": nombre(p), "codigo": c,
                               "descripcion": desc[c], "hora": h, "obs": o})

    compensados, no_emitidos = [], []
    for f in faltan:
        m = next((s for s in sobran if s["codigo"] == f["codigo"]), None)
        if m:
            sobran.remove(m)
            compensados.append({**f, "programa_emision": m["programa"],
                                "nombre_programa_emision": m["nombre_programa"], "hora": m["hora"], "obs": m["obs"]})
        else:
            no_emitidos.append(f)

    # Diferencias de duración: cada aviso emitido contra la duración que figura en la rutina
    dur_plan = {}
    for it in plan:
        dur_plan.setdefault(it["codigo"], int(it.get("dur", "0").rstrip('"') or 0))
    duraciones = []
    for p in emit:
        for codigo, d, hora, o, dur_tc, tipo in emit[p]:
            if not codigo or codigo not in dur_plan:
                continue
            h, m, sg = (int(x) for x in dur_tc.split(":"))
            real = h * 3600 + m * 60 + sg
            dif = real - dur_plan[codigo]
            if dif:
                duraciones.append({"programa": p, "nombre_programa": nombre(p), "codigo": codigo,
                                   "descripcion": desc.get(codigo, d), "hora": hora, "tipo": tipo,
                                   "programada": dur_plan[codigo], "emitida": real, "diferencia": dif})

    total = sum(sum(c.values()) for c in plan_c.values())
    en_su_programa = total - len(faltan)
    return {
        "total": total, "emitidos": en_su_programa,
        "no_emitidos": no_emitidos, "compensados": compensados,
        "no_programados": sobran + sin_codigo,
        "duraciones": duraciones,
        "cuadra": total == en_su_programa + len(compensados) + len(no_emitidos),
    }


def _tabla(items, extra=None):
    ancho = max(len(x["nombre_programa"]) for x in items)
    filas = []
    for x in items:
        fila = f"{x['nombre_programa']:<{ancho}}  {x['programa']:>5}   {x['descripcion']:<30} {x['codigo']}"
        if extra:
            fila += extra(x)
        filas.append(fila.rstrip())
    return filas


def armar_informe(r):
    L = []
    L.append(f"INFORME TELECONTROL {r['fecha_rutina']}")
    L.append("")
    L.append("ARTISTICA NO EMITIDA")
    if r["no_emitidos"]:
        ancho = max(len(x["nombre_programa"]) for x in r["no_emitidos"])
        for x in r["no_emitidos"]:
            L.append(f"{x['nombre_programa']:<{ancho}}  {x['programa']:>5}   {x['descripcion']:<30} {x['codigo']}")
    else:
        L.append("(no hay)")
    if r["compensados"]:
        L.append("")
        L.append("ARTISTICA COMPENSADA EN OTRO PROGRAMA")
        for x in r["compensados"]:
            L.append(f"{x['nombre_programa']} {x['programa']}  {x['descripcion']} {x['codigo']}"
                     f"  -> salió en {x['nombre_programa_emision']} {x['programa_emision']}")
    L.append("")
    L.append("ARTISTICA NO PROG")
    if r["no_prog"]:
        L.append(", ".join(f"{x['programa']} {x['nombre_programa'].strip('./ ')}" for x in r["no_prog"]))
        L.append(f"Detalle ({sum(len(x['items']) for x in r['no_prog'])}):")
        for x in r["no_prog"]:
            L.append(f"{x['programa']} {x['nombre_programa'].strip('./ ')}")
            for item in x["items"]:
                L.append(f"      - {item}")
    else:
        L.append("(no hay)")
    pub = r["publicidad"]
    L.append("")
    L.append("PUBLICIDAD NO EMITIDA")
    L.extend(_tabla(pub["no_emitidos"]) if pub["no_emitidos"] else ["(no hay)"])
    if pub["compensados"]:
        L.append("")
        L.append("PUBLICIDAD COMPENSADA EN OTRO PROGRAMA")
        L.extend(_tabla(pub["compensados"], lambda x: f"  -> salió en {x['nombre_programa_emision']} "
                        f"{x['programa_emision']} [{x['hora']}] {x['obs']}"))
    L.append("")
    L.append("PUBLICIDAD NO PROGRAMADA")
    L.extend(_tabla(pub["no_programados"], lambda x: f"  [{x['hora']}] {x['obs']}")
             if pub["no_programados"] else ["(no hay)"])
    L.append("")
    L.append("DIFERENCIA DE DURACION (programada vs. telecontrol)")
    if pub["duraciones"]:
        for x in pub["duraciones"]:
            L.append(f"{x['hora']:>8}  {x['nombre_programa']} {x['programa']}  {x['descripcion']} {x['codigo']}  "
                     f"prog {x['programada']}\" / salió {x['emitida']}\" ({x['diferencia']:+d}\")")
    else:
        L.append("(no hay)")
    L.append("")
    L.append("-" * 60)
    L.append(f"Control: {r['total_artistica']} artísticas programadas = "
             f"{r['emitidos']} emitidas + {len(r['no_emitidos'])} no emitidas + "
             f"{len(r['compensados'])} compensadas  ->  {'OK' if r['cuadra'] else 'NO CUADRA, REVISAR'}")
    L.append(f"Control: {pub['total']} avisos programados = {pub['emitidos']} emitidos + "
             f"{len(pub['no_emitidos'])} no emitidos + {len(pub['compensados'])} compensados  ->  "
             f"{'OK' if pub['cuadra'] else 'NO CUADRA, REVISAR'}")
    if r["renglones_sin_leer"]:
        L.append("ATENCION: renglones del telecontrol que no se pudieron leer (revisar a mano):")
        L.extend(f"   {x}" for x in r["renglones_sin_leer"])
    if r["renglones_sin_leer_rutina"]:
        L.append("ATENCION: renglones de la rutina que no se pudieron leer (revisar a mano):")
        L.extend(f"   {x}" for x in r["renglones_sin_leer_rutina"])
    return "\n".join(L)


def armar_html(r):
    """Cuerpo del correo: fondo blanco, títulos en rojo, franjas grises por sección, filas simples.
    Todo es HTML común, así que se puede editar en Thunderbird antes de enviar."""
    from html import escape as e
    F = "font-family:Arial,Helvetica,sans-serif;"
    T_ROJO = f'style="{F}color:#c00000;font-size:17px;font-weight:bold;margin:22px 0 8px 0"'
    TABLA = f'style="{F}border-collapse:collapse;width:100%;font-size:13px;color:#000;background:#fff"'
    BANDA = f'style="{F}background:#eeeeee;padding:6px 8px;font-size:13px;border-bottom:1px solid #ccc"'
    TD = 'style="padding:5px 8px;border-bottom:1px solid #e3e3e3;vertical-align:top;white-space:nowrap"'
    TD_DESC = 'style="padding:5px 8px;border-bottom:1px solid #e3e3e3;vertical-align:top;width:100%"'
    TD_DER = 'style="padding:5px 8px;border-bottom:1px solid #e3e3e3;vertical-align:top;text-align:right;white-space:nowrap"'
    LILA = 'style="color:#6a1b9a"'
    NOTA = 'style="font-size:11px;color:#666"'
    COLS = 6

    def banda(titulo, n, explicacion):
        return (f'<tr><td colspan="{COLS}" {BANDA}><b>{e(titulo)} · {n}</b> '
                f'<span style="color:#555">{e(explicacion)}</span></td></tr>')

    def fila(hora, programa, num, codigo, descripcion, dur="", nota=""):
        d = e(descripcion) + (f"<br><span {NOTA}>{e(nota)}</span>" if nota else "")
        return (f"<tr><td {TD}>{e(hora)}</td><td {TD}><span {LILA}>{e(programa.strip('./ '))}</span></td>"
                f"<td {TD}>{e(num)}</td><td {TD}>{e(codigo)}</td><td {TD_DESC}>{d}</td>"
                f"<td {TD_DER}>{e(dur)}</td></tr>")

    def bloque(titulo, secciones):
        total = sum(len(filas) for _, _, filas in secciones)
        html = f"<p {T_ROJO}>{e(titulo)} ({total})</p><table {TABLA}>"
        for (sub, expl, filas) in secciones:
            html += banda(sub, len(filas), expl)
            html += "".join(filas) if filas else (
                f'<tr><td colspan="{COLS}" {TD}><span {NOTA}>(no hay)</span></td></tr>')
        return html + "</table>"

    pub = r["publicidad"]
    partes = []

    # 1) Artística
    secs = [("ARTÍSTICA NO EMITIDA", "Estaba en la rutina del programa y no figura en su telecontrol.",
             [fila(x.get("hora", ""), x["nombre_programa"], x["programa"], x["codigo"], x["descripcion"], x.get("dur", ""))
              for x in r["no_emitidos"]])]
    if r["compensados"]:
        secs.append(("COMPENSADA EN OTRO PROGRAMA", "No salió en su programa pero sí en otro.",
                     [fila(x.get("hora", ""), x["nombre_programa"], x["programa"], x["codigo"], x["descripcion"],
                           x.get("dur", ""), f"salió en {x['nombre_programa_emision'].strip('./ ')} {x['programa_emision']}")
                      for x in r["compensados"]]))
    partes.append(bloque("Artística que faltó", secs))

    # 2) Artística no programada
    filas_np = []
    for x in r["no_prog"]:
        for item in x["items"]:
            texto, _, hora = item.rpartition("  [")
            filas_np.append(fila(hora.rstrip("]"), x["nombre_programa"], x["programa"], "", texto or item))
    resumen = ", ".join(f"{x['programa']} {x['nombre_programa'].strip('./ ')}" for x in r["no_prog"])
    partes.append(f"<p {T_ROJO}>Artística no programada</p>"
                  f'<p style="{F}font-size:13px;margin:0 0 10px 0">{e(resumen) if resumen else "(no hay)"}</p>')
    if filas_np:
        partes.append(bloque("Detalle de lo que salió sin programar",
                             [("ARTÍSTICA NO PROG", "PNT y menciones del telecontrol sin código de material.", filas_np)]))

    # 3) Publicidad
    secs = [("PUBLICIDAD NO EMITIDA", "Aviso de tanda de la rutina que no salió.",
             [fila(x.get("hora_prog", ""), x["nombre_programa"], x["programa"], x["codigo"], x["descripcion"], x.get("dur", ""))
              for x in pub["no_emitidos"]])]
    if pub["compensados"]:
        secs.append(("COMPENSADA EN OTRO PROGRAMA", "Faltó en su programa pero salió de más en otro.",
                     [fila(x.get("hora_prog", ""), x["nombre_programa"], x["programa"], x["codigo"], x["descripcion"],
                           x.get("dur", ""), f"salió en {x['nombre_programa_emision'].strip('./ ')} "
                           f"{x['programa_emision']} a las {x['hora']} {x['obs']}".strip())
                      for x in pub["compensados"]]))
    secs.append(("PUBLICIDAD NO PROGRAMADA", "Aviso (tipo 1020, 1030) que salió de más o sin código.",
                 [fila(x["hora"], x["nombre_programa"], x["programa"], x["codigo"], x["descripcion"], "", x["obs"])
                  for x in pub["no_programados"]]))
    partes.append(bloque("Publicidad", secs))

    # 4) Diferencias de duración
    filas_dur = [fila(x["hora"], x["nombre_programa"], x["programa"], x["codigo"], x["descripcion"],
                      f"{x['diferencia']:+d}\"", f"programada {x['programada']}\" · salió {x['emitida']}\" (tipo {x['tipo']})")
                 for x in pub["duraciones"]]
    partes.append(bloque("Diferencia de duración", [
        ("PROGRAMADA VS. TELECONTROL", "Avisos de tanda (1020, 1030) cuya duración no coincide con la rutina.", filas_dur)]))

    control = (f"Control artística: {r['total_artistica']} programadas = {r['emitidos']} emitidas + "
               f"{len(r['no_emitidos'])} no emitidas + {len(r['compensados'])} compensadas. "
               f"Control publicidad: {pub['total']} avisos = {pub['emitidos']} emitidos + "
               f"{len(pub['no_emitidos'])} no emitidos + {len(pub['compensados'])} compensados. "
               + ("OK" if r["cuadra"] else "NO CUADRA, REVISAR"))
    partes.append(f'<p style="{F}font-size:11px;color:#888;margin-top:24px">{e(control)}</p>')
    return ('<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"></head>'
            '<body style="background:#fff">' + "".join(partes) + "</body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_a")
    ap.add_argument("pdf_b")
    ap.add_argument("--salida")
    ap.add_argument("--json")
    a = ap.parse_args()

    textos = {Path(p): texto_pdf(p) for p in (a.pdf_a, a.pdf_b)}
    rut = next((t for t in textos.values() if "RUTINA DE TRANSMISION" in t), None)
    tc = next((t for t in textos.values() if "LISTADO DEL TELECONTROL" in t), None)
    if not rut or not tc:
        sys.exit("ERROR: no identifiqué cuál PDF es la Rutina y cuál el Telecontrol.")

    r = comparar(rut, tc)
    if not r["misma_fecha"]:
        sys.exit(f"ERROR: las fechas no coinciden (rutina {r['fecha_rutina']}, "
                 f"telecontrol {r['fecha_telecontrol']}). No se compara.")

    informe = armar_informe(r)
    print(informe)
    if a.salida:
        Path(a.salida).write_text(informe + "\n", encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    if not r["cuadra"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
