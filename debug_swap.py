"""Debug: check if swap files were actually copied."""
import os, hashlib

STEAM = r"D:\SteamLibrary\steamapps\common\rocketleague\TAGame\CookedPCConsole"
EPIC = r"D:\Farming Simulator 19\rocketleague\TAGame\CookedPCConsole"
BACKUP_S = r"D:\Joga Bonito\Backups\Steam"
BACKUP_E = r"D:\Joga Bonito\Backups\Epic"

SRC_FILE = "explosion_illustrated_bursts_SF.upk"   # Abracadabra
TGT_FILE = "explosion_fs_gray_SF.upk"              # AC Milan

def sig(path):
    if not os.path.exists(path):
        return "MISSING"
    size = os.path.getsize(path)
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]
    return f"{size} bytes, sha256={h}"

print("=== STEAM ===")
print(f"  Source ({SRC_FILE}): {sig(os.path.join(STEAM, SRC_FILE))}")
print(f"  Target ({TGT_FILE}): {sig(os.path.join(STEAM, TGT_FILE))}")
print(f"  Backup ({TGT_FILE}): {sig(os.path.join(BACKUP_S, TGT_FILE))}")

# Key check: if swap worked, target should have SAME hash as source
src_path = os.path.join(STEAM, SRC_FILE)
tgt_path = os.path.join(STEAM, TGT_FILE)
bkp_path = os.path.join(BACKUP_S, TGT_FILE)

if os.path.exists(src_path) and os.path.exists(tgt_path):
    src_h = hashlib.sha256(open(src_path, "rb").read()).hexdigest()
    tgt_h = hashlib.sha256(open(tgt_path, "rb").read()).hexdigest()
    if src_h == tgt_h:
        print("  >>> TARGET = SOURCE (swap IS applied)")
    else:
        print("  >>> TARGET != SOURCE (swap NOT applied!)")
        if os.path.exists(bkp_path):
            bkp_h = hashlib.sha256(open(bkp_path, "rb").read()).hexdigest()
            if tgt_h == bkp_h:
                print("  >>> TARGET = BACKUP (still original, swap didn't stick)")

print()
print("=== EPIC ===")
print(f"  Source ({SRC_FILE}): {sig(os.path.join(EPIC, SRC_FILE))}")
print(f"  Target ({TGT_FILE}): {sig(os.path.join(EPIC, TGT_FILE))}")
print(f"  Backup ({TGT_FILE}): {sig(os.path.join(BACKUP_E, TGT_FILE))}")

src_path_e = os.path.join(EPIC, SRC_FILE)
tgt_path_e = os.path.join(EPIC, TGT_FILE)
bkp_path_e = os.path.join(BACKUP_E, TGT_FILE)

if os.path.exists(src_path_e) and os.path.exists(tgt_path_e):
    src_h = hashlib.sha256(open(src_path_e, "rb").read()).hexdigest()
    tgt_h = hashlib.sha256(open(tgt_path_e, "rb").read()).hexdigest()
    if src_h == tgt_h:
        print("  >>> TARGET = SOURCE (swap IS applied)")
    else:
        print("  >>> TARGET != SOURCE (swap NOT applied!)")

print()
print("=== BACKUP FOLDER CONTENTS ===")
for d in [BACKUP_S, BACKUP_E]:
    if os.path.isdir(d):
        files = os.listdir(d)
        print(f"  {d}: {len(files)} files — {files[:5]}")
    else:
        print(f"  {d}: DOESN'T EXIST")
