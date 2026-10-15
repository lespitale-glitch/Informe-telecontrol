"""
Genera el informe en Windows sin IA.
- Si arrastrás los dos PDF sobre "Generar informe.bat", usa esos.
- Si le das doble clic, usa los PDF que haya en la carpeta "pdfs".
Guarda "INFORME TELECONTROL dd-mm-aa.txt" en la carpeta "informes" y abre un correo
nuevo en Thunderbird con el informe (destinatarios en config.txt).
Si no encuentra Thunderbird, abre el .txt en el Bloc de notas.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import comparar as c

BASE = Path(__file__).resolve().parent.parent


def leer_config():
    cfg = {}
    archivo = BASE / "config.txt"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8-sig").splitlines():
            if "=" in linea and not linea.strip().startswith("#"):
                k, v = linea.split("=", 1)
                cfg[k.strip().upper()] = v.strip()
    return cfg


def buscar_thunderbird(cfg):
    candidatos = [cfg.get("THUNDERBIRD", "")]
    for var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(var)
        if base:
            candidatos.append(os.path.join(base, "Mozilla Thunderbird", "thunderbird.exe"))
    try:
        import winreg
        for raiz in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(raiz, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\thunderbird.exe") as k:
                    candidatos.append(winreg.QueryValue(k, None))
            except OSError:
                pass
    except ImportError:
        pass
    return next((c for c in candidatos if c and os.path.isfile(c)), None)


def abrir_en_thunderbird(r, cfg):
    tb = buscar_thunderbird(cfg)
    if not tb:
        return False
    # El cuerpo va en un archivo HTML en la carpeta temporal (ruta sin tildes)
    cuerpo = Path(tempfile.gettempdir()) / "informe_telecontrol.html"
    cuerpo.write_text(c.armar_html(r), encoding="utf-8")
    partes = [f"subject='INFORME TELECONTROL {r['fecha_rutina']}'", "format=1", f"message='{cuerpo}'"]
    if cfg.get("PARA"):
        partes.insert(0, f"to='{cfg['PARA']}'")
    if cfg.get("CC"):
        partes.insert(1, f"cc='{cfg['CC']}'")
    subprocess.Popen([tb, "-compose", ",".join(partes)])
    return True


def main():
    pdfs = [Path(a) for a in sys.argv[1:] if a.lower().endswith(".pdf")]
    if not pdfs:
        pdfs = sorted((BASE / "pdfs").glob("*.pdf"))
    if len(pdfs) != 2:
        print(f"ERROR: necesito exactamente 2 PDF (rutina y telecontrol) y encontré {len(pdfs)}.")
        print(f"Dejalos en la carpeta: {BASE / 'pdfs'}")
        return 1

    textos = [c.texto_pdf(p) for p in pdfs]
    rut = next((t for t in textos if "RUTINA DE TRANSMISION" in t), None)
    tc = next((t for t in textos if "LISTADO DEL TELECONTROL" in t), None)
    if not rut or not tc:
        print("ERROR: no reconozco cuál PDF es la rutina y cuál el telecontrol.")
        return 1

    r = c.comparar(rut, tc)
    if not r["misma_fecha"]:
        print(f"ERROR: los PDF no son del mismo día (rutina {r['fecha_rutina']}, "
              f"telecontrol {r['fecha_telecontrol']}). No se compara.")
        return 1

    informe = c.armar_informe(r)
    carpeta = BASE / "informes"
    carpeta.mkdir(exist_ok=True)
    salida = carpeta / f"INFORME TELECONTROL {r['fecha_rutina'].replace('/', '-')}.txt"
    salida.write_text(informe + "\n", encoding="utf-8-sig")
    print(informe)
    print(f"\nGuardado en: {salida}")
    if os.name == "nt":
        if abrir_en_thunderbird(r, leer_config()):
            print("Abriendo un correo nuevo en Thunderbird...")
        else:
            print("No encontré Thunderbird: abro el informe en el Bloc de notas.")
            os.startfile(salida)
    return 0 if r["cuadra"] else 2


if __name__ == "__main__":
    sys.exit(main())
