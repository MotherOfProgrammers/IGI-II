import json
import struct
import subprocess
import tempfile
from pathlib import Path

CONV = r"D:\IGI-II\igi2conv-windows-x86_64-qt-r9\igi2conv\igi2conv.exe"
MODELS = Path(r"D:\IGI-II\igi2_collected\common\models")
CODES = ["139_01_1", "107_01_1", "108_01_1", "142_01_1", "147_01_1", "130_01_1"]

for code in CODES:
    src = MODELS / (code + ".mef")
    if not src.exists():
        print(code, "missing")
        continue
    out = Path(tempfile.mkdtemp()) / "m.json"
    subprocess.run([CONV, "asset", "to-json", str(src), str(out)], check=True)
    d = json.loads(out.read_text())
    ch = {c["tag"]: bytes.fromhex(c["data"]) for c in d["chunks"] if c["data"]}
    hs = struct.unpack("<%dI" % (len(ch["HSEM"]) // 4), ch["HSEM"])
    d3 = struct.unpack("<%dI" % (len(ch["D3DR"]) // 4), ch["D3DR"])
    print(code, "verts", len(ch["XTRV"]) // 32, "tris", len(ch["ECAF"]) // 6, "xtrv", len(ch["XTRV"]), "ecaf", len(ch["ECAF"]))
    print(" HSEM", hs[:30])
    print(" D3DR", d3)