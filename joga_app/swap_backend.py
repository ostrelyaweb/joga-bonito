import base64
import copy
import csv
import os
import shutil
import struct
from datetime import datetime, timezone

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from joga_app.config import (
    BACKUPS_DIR,
    GAME_SIG_FILE,
    KEYS_FILE,
    PRESETS_FILE,
    PRODUCTS_CSV,
    SWAPS_LOG_FILE,
    TRANSACTIONS_DIR,
)
from joga_app.core.storage import atomic_write_json, read_json
from joga_app.core.transactions import FileTransaction, ensure_within, file_signature


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _file_sig(path):
    return file_signature(path)


def _norm_install_dir(path):
    return os.path.normpath(path or "")


class AESDatabase:
    """Manages Rocket League AES encryption keys for UPK packages."""

    def __init__(self, products_csv_path=PRODUCTS_CSV, keys_path=KEYS_FILE):
        self.package_keys = {}
        self.all_keys = []
        self._load(products_csv_path, keys_path)

    def _load(self, products_csv_path, keys_path):
        if os.path.exists(products_csv_path):
            try:
                with open(products_csv_path, "r", encoding="utf-8", errors="replace") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        pkg = row.get("Package", "").strip().lower()
                        aes = row.get("AES", "").strip()
                        if pkg and aes:
                            self.package_keys[pkg] = aes
            except Exception as e:
                print(f"[AESDatabase] Error loading products.csv: {e}")

        if os.path.exists(keys_path):
            try:
                with open(keys_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        k = line.strip()
                        if k:
                            self.all_keys.append(k)
            except Exception as e:
                print(f"[AESDatabase] Error loading keys.txt: {e}")

    def get_key_for_package(self, package_name):
        pkg = (package_name or "").lower().strip()
        # Direct lookup
        if pkg in self.package_keys:
            return self.package_keys[pkg]
        # Clean prefix/suffix
        clean = pkg.replace("_sf", "").replace("_t", "")
        if clean in self.package_keys:
            return self.package_keys[clean]
        # Fallback to default common key if present
        default_key = "x99rEyUqzHFHu1HJitfjS3/lALd/pfqyk+LyTmsX53k="
        return default_key


# Global key database instance
_aes_db = None


def get_aes_db():
    global _aes_db
    if _aes_db is None:
        _aes_db = AESDatabase()
    return _aes_db


def patch_and_reencrypt_upk(src_path, tgt_path, src_key_b64=None, tgt_key_b64=None):
    """
    Decrypts source UPK header using src_key (AES-256-ECB) and
    re-encrypts with tgt_key so Rocket League can load the swapped item.
    """
    with open(src_path, "rb") as f:
        data = f.read()

    if len(data) < 64:
        shutil.copyfile(src_path, tgt_path)
        return

    # Check UE3 UPK magic
    tag = struct.unpack("<I", data[:4])[0]
    if tag != 0x9E2A83C1:
        shutil.copyfile(src_path, tgt_path)
        return

    try:
        tag, ver, lic, hdr_size = struct.unpack("<IHHI", data[:12])
        folder_len = struct.unpack("<i", data[12:16])[0]
        pos = 16 + folder_len
        pkg_flags, name_cnt, name_off = struct.unpack("<III", data[pos:pos+12])
    except Exception:
        shutil.copyfile(src_path, tgt_path)
        return

    if name_off <= 0 or hdr_size <= name_off or hdr_size > len(data):
        shutil.copyfile(src_path, tgt_path)
        return

    src_key = base64.b64decode(src_key_b64) if src_key_b64 else None
    tgt_key = base64.b64decode(tgt_key_b64) if tgt_key_b64 else None

    enc_len = ((hdr_size - name_off + 15) // 16) * 16
    if name_off + enc_len > len(data):
        enc_len = ((len(data) - name_off) // 16) * 16

    raw_header_enc = data[name_off:name_off+enc_len]

    # Decrypt with Source Key
    if src_key:
        try:
            cipher = Cipher(algorithms.AES(src_key), modes.ECB(), backend=default_backend())
            dec = cipher.decryptor()
            decrypted = dec.update(raw_header_enc) + dec.finalize()
        except Exception:
            decrypted = raw_header_enc
    else:
        decrypted = raw_header_enc

    # Re-encrypt with Target Key
    if tgt_key:
        try:
            cipher = Cipher(algorithms.AES(tgt_key), modes.ECB(), backend=default_backend())
            enc = cipher.encryptor()
            reencrypted = enc.update(decrypted) + enc.finalize()
        except Exception:
            reencrypted = decrypted
    else:
        reencrypted = decrypted

    output_data = data[:name_off] + reencrypted + data[name_off+enc_len:]

    with open(tgt_path, "wb") as f:
        f.write(output_data)


class Swap:
    def __init__(self, install, source, target, timestamp=None):
        self.install_cooked_dir = install.get("cookedDir")
        self.install_id = install.get("id", "")
        self.install_source = install.get("source", install.get("name", ""))
        self.install_name = install.get("name", "")
        self.source_file = source.file
        self.source_label = source.label
        self.target_file = target.file
        self.target_label = target.label
        self.timestamp = timestamp or _now()

    def to_dict(self):
        return {
            "installId": self.install_id,
            "installCookedDir": self.install_cooked_dir,
            "installSource": self.install_source,
            "installName": self.install_name,
            "sourceFile": self.source_file,
            "sourceLabel": self.source_label,
            "targetFile": self.target_file,
            "targetLabel": self.target_label,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d):
        s = cls.__new__(cls)
        s.install_cooked_dir = d.get("installCookedDir")
        s.install_id = d.get("installId", "")
        s.install_source = d.get("installSource", "")
        s.install_name = d.get("installName", "")
        s.source_file = d.get("sourceFile")
        s.source_label = d.get("sourceLabel", "")
        s.target_file = d.get("targetFile")
        s.target_label = d.get("targetLabel", "")
        s.timestamp = d.get("timestamp", "")
        return s

    def key(self):
        install_key = self.install_id or _norm_install_dir(self.install_cooked_dir or "")
        return install_key + "|" + (self.target_file or "").lower()


class PresetStore:
    def __init__(self):
        self.current_preset = "Default"
        self.presets = [{"name": "Default", "swaps": []}]

    def load(self, path=None):
        path = path or PRESETS_FILE
        data = read_json(path, None)
        if not isinstance(data, dict):
            return
        self.current_preset = data.get("currentPreset", "Default")
        presets = data.get("presets")
        if isinstance(presets, list) and presets:
            self.presets = presets
        if not any(p.get("name") == self.current_preset for p in self.presets):
            self.current_preset = self.presets[0]["name"]

    def save(self, path=None):
        path = path or PRESETS_FILE
        data = {"currentPreset": self.current_preset, "presets": self.presets}
        atomic_write_json(path, data)

    def names(self):
        return [p.get("name") for p in self.presets]

    def _current(self):
        for p in self.presets:
            if p.get("name") == self.current_preset:
                return p
        self.presets.append({"name": "Default", "swaps": []})
        self.current_preset = "Default"
        return self.presets[-1]

    def active_swaps(self):
        return [Swap.from_dict(d) for d in self._current().get("swaps", [])]

    def active_by_install(self, name=""):
        swaps = self.active_swaps()
        if name:
            swaps = [s for s in swaps if s.install_name == name]
        return swaps

    def add_swap(self, swap):
        lst = self._current().setdefault("swaps", [])
        for i, d in enumerate(lst):
            if Swap.from_dict(d).key() == swap.key():
                lst[i] = swap.to_dict()
                self.save()
                return
        lst.append(swap.to_dict())
        self.save()

    def remove_swap(self, swap):
        p = self._current()
        key = swap.key()
        p["swaps"] = [d for d in p.get("swaps", []) if Swap.from_dict(d).key() != key]
        self.save()

    def save_as(self, name):
        snapshot = [s.to_dict() for s in self.active_swaps()]
        p = self._current()
        if p.get("name") == name:
            p["swaps"] = snapshot
        elif any(x.get("name") == name for x in self.presets):
            target = next(x for x in self.presets if x.get("name") == name)
            target["swaps"] = snapshot
        else:
            self.presets.append({"name": name, "swaps": snapshot})
        self.current_preset = name
        self.save()

    def switch(self, name):
        for p in self.presets:
            if p.get("name") == name:
                self.current_preset = name
                self.save()
                return True
        return False

    def delete(self, name):
        if len(self.presets) <= 1:
            return False
        self.presets = [p for p in self.presets if p.get("name") != name]
        if not self.presets:
            self.presets = [{"name": "Default", "swaps": []}]
        if not any(p.get("name") == self.current_preset for p in self.presets):
            self.current_preset = self.presets[0]["name"]
        self.save()
        return True

    def export_preset(self, name, path):
        preset = None
        for p in self.presets:
            if p.get("name") == name:
                preset = p
                break
        if preset is None:
            return False
        atomic_write_json(path, preset)
        return True

    def import_preset(self, path):
        data = read_json(path, None)
        if not isinstance(data, dict):
            return None
        name = data.get("name")
        swaps = data.get("swaps")
        if not name or not isinstance(swaps, list):
            return None
        existing = {p.get("name") for p in self.presets}
        orig_name = name
        counter = 2
        while name in existing:
            name = f"{orig_name} ({counter})"
            counter += 1
        self.presets.append({"name": name, "swaps": swaps})
        self.save()
        return name


class SwapBackend:
    def __init__(self, cfg):
        self.cfg = cfg
        self.recovered_transactions = FileTransaction.recover_incomplete(
            TRANSACTIONS_DIR,
            [install.get("cookedDir") for install in cfg.installs],
        )
        self.presets = PresetStore()
        self.presets.load()
        self.aes_db = get_aes_db()
        os.makedirs(BACKUPS_DIR, exist_ok=True)

    def backups_dir(self, install):
        install_id = install.get("id") or self.cfg._install_id(install)
        d = os.path.join(BACKUPS_DIR, install_id)
        legacy = os.path.join(BACKUPS_DIR, install.get("name", "install"))
        if os.path.isdir(legacy) and not os.path.exists(d):
            shutil.move(legacy, d)
        os.makedirs(d, exist_ok=True)
        return d

    def _read_sig(self):
        data = read_json(GAME_SIG_FILE, {})
        return data if isinstance(data, dict) else {}

    def _write_sig(self, data):
        atomic_write_json(GAME_SIG_FILE, data)

    def _sig_of_install(self, install, target_file):
        data = self._read_sig()
        key = _norm_install_dir(install.get("cookedDir", ""))
        return data.get(key, {}).get(target_file)

    def _record_sig(self, install, target_file, sig):
        data = self._read_sig()
        key = _norm_install_dir(install.get("cookedDir", ""))
        data.setdefault(key, {})[target_file] = sig
        self._write_sig(data)

    def _append_log(self, swap):
        log = read_json(SWAPS_LOG_FILE, [])
        if not isinstance(log, list):
            log = []
        log.append(swap.to_dict())
        atomic_write_json(SWAPS_LOG_FILE, log)

    @staticmethod
    def _safe_game_file(cooked, filename):
        if not filename or os.path.basename(filename) != filename:
            raise ValueError(f"Unsafe game filename: {filename}")
        return str(ensure_within(cooked, os.path.join(cooked, filename)))

    @staticmethod
    def _check_space(cooked, paths):
        required = sum(os.path.getsize(path) for path in paths if os.path.isfile(path)) * 2
        if shutil.disk_usage(cooked).free < required:
            raise OSError("Not enough free disk space for a safe swap and rollback")

    def _extract_pkg_name(self, filename):
        """Extract base package name (e.g. 'WHEEL_Hydra_SF.upk' -> 'WHEEL_Hydra')."""
        base = os.path.splitext(filename)[0]
        if base.endswith("_SF") or base.endswith("_sf"):
            base = base[:-3]
        return base

    def _find_texture_file(self, cooked_dir, base_pkg):
        """Find companion texture file (e.g. 'WHEEL_Hydra_T_SF.upk')."""
        candidates = [
            f"{base_pkg}_T_SF.upk",
            f"{base_pkg}_t_sf.upk",
            f"{base_pkg}_T.upk",
            f"{base_pkg}_t.upk",
        ]
        for c in candidates:
            p = os.path.join(cooked_dir, c)
            if os.path.exists(p):
                return c
        return None

    def _find_sound_file(self, cooked_dir, base_pkg):
        """Find companion sound bank (e.g. 'SFX_GoalExplosion_...bnk')."""
        clean = base_pkg.lower().replace("explosion_", "").replace("boost_", "").replace("_", "")
        # Search for .bnk files
        for f in os.listdir(cooked_dir):
            if f.lower().endswith(".bnk"):
                clean_f = f.lower().replace("sfx_", "").replace("goalexplosion_", "").replace("boost_", "").replace("_", "")
                if clean in clean_f or clean_f in clean:
                    return f
        return None

    def apply_swap(self, install, source, target):
        cooked = install.get("cookedDir")
        if not cooked or not os.path.isdir(cooked):
            return False, "msg.install_missing", cooked

        try:
            src_path = self._safe_game_file(cooked, source.file)
            tgt_path = self._safe_game_file(cooked, target.file)
        except ValueError as exc:
            return False, "msg.swap_failed", str(exc)

        if not os.path.exists(src_path):
            return False, "msg.source_missing", source.file
        if not os.path.exists(tgt_path):
            return False, "msg.target_missing", target.file

        back = self.backups_dir(install)
        baseline = os.path.join(back, target.file)

        src_pkg = self._extract_pkg_name(source.file)
        tgt_pkg = self._extract_pkg_name(target.file)
        src_key = self.aes_db.get_key_for_package(src_pkg)
        tgt_key = self.aes_db.get_key_for_package(tgt_pkg)
        src_tex = self._find_texture_file(cooked, src_pkg)
        tgt_tex = self._find_texture_file(cooked, tgt_pkg)
        src_bnk = self._find_sound_file(cooked, src_pkg)
        tgt_bnk = self._find_sound_file(cooked, tgt_pkg)
        source_paths = [src_path, tgt_path]
        if src_tex and tgt_tex:
            source_paths.extend(
                [self._safe_game_file(cooked, src_tex), self._safe_game_file(cooked, tgt_tex)]
            )
        if src_bnk and tgt_bnk:
            source_paths.extend(
                [self._safe_game_file(cooked, src_bnk), self._safe_game_file(cooked, tgt_bnk)]
            )

        transaction = None
        preset_snapshot = copy.deepcopy(self.presets.presets)
        current_preset_snapshot = self.presets.current_preset
        history_snapshot = read_json(SWAPS_LOG_FILE, [])
        try:
            self._check_space(cooked, source_paths)
            if not os.path.exists(baseline):
                shutil.copy2(tgt_path, baseline)
                self._record_sig(install, target.file, _file_sig(baseline))

            transaction = FileTransaction(
                "apply_swap",
                cooked,
                install.get("id") or self.cfg._install_id(install),
                {"source": source.file, "target": target.file},
                TRANSACTIONS_DIR,
            )

            def write_main(output):
                try:
                    patch_and_reencrypt_upk(src_path, output, src_key, tgt_key)
                except Exception:
                    shutil.copyfile(src_path, output)

            transaction.replace(tgt_path, write_main)

            if src_tex and tgt_tex:
                src_tex_path = self._safe_game_file(cooked, src_tex)
                tgt_tex_path = self._safe_game_file(cooked, tgt_tex)
                tex_backup = os.path.join(back, tgt_tex)
                if not os.path.exists(tex_backup):
                    shutil.copy2(tgt_tex_path, tex_backup)

                def write_texture(output):
                    try:
                        patch_and_reencrypt_upk(src_tex_path, output, src_key, tgt_key)
                    except Exception:
                        shutil.copyfile(src_tex_path, output)

                transaction.replace(tgt_tex_path, write_texture)

            if src_bnk and tgt_bnk:
                src_bnk_path = self._safe_game_file(cooked, src_bnk)
                tgt_bnk_path = self._safe_game_file(cooked, tgt_bnk)
                bnk_backup = os.path.join(back, tgt_bnk)
                if not os.path.exists(bnk_backup):
                    shutil.copy2(tgt_bnk_path, bnk_backup)
                transaction.replace(
                    tgt_bnk_path,
                    lambda output: shutil.copyfile(src_bnk_path, output),
                )

            swap = Swap(install, source, target)
            self.presets.add_swap(swap)
            self._append_log(swap)
            transaction.commit()
            return True, "msg.swap_applied", source.label, target.label
        except Exception as exc:
            self.presets.presets = preset_snapshot
            self.presets.current_preset = current_preset_snapshot
            try:
                self.presets.save()
                atomic_write_json(
                    SWAPS_LOG_FILE,
                    history_snapshot if isinstance(history_snapshot, list) else [],
                )
            except OSError:
                pass
            if transaction is not None:
                transaction.rollback()
            return False, "msg.swap_failed", str(exc)

    def restore_swap(self, install, swap):
        back = self.backups_dir(install)
        baseline = os.path.join(back, swap.target_file)
        cooked = install.get("cookedDir", "")
        try:
            tgt = self._safe_game_file(cooked, swap.target_file)
        except ValueError as exc:
            return False, "msg.restore_failed", str(exc)

        if not os.path.exists(baseline):
            return False, "msg.no_backup", swap.target_file
        if not os.path.isdir(cooked):
            return False, "msg.install_missing", cooked

        transaction = None
        preset_snapshot = copy.deepcopy(self.presets.presets)
        current_preset_snapshot = self.presets.current_preset
        try:
            transaction = FileTransaction(
                "restore_swap",
                cooked,
                install.get("id") or self.cfg._install_id(install),
                {"target": swap.target_file},
                TRANSACTIONS_DIR,
            )
            transaction.replace(tgt, lambda output: shutil.copyfile(baseline, output))

            tgt_pkg = self._extract_pkg_name(swap.target_file)
            tgt_tex = self._find_texture_file(back, tgt_pkg)
            if tgt_tex:
                destination = self._safe_game_file(cooked, tgt_tex)
                transaction.replace(
                    destination,
                    lambda output: shutil.copyfile(os.path.join(back, tgt_tex), output),
                )

            tgt_bnk = self._find_sound_file(back, tgt_pkg)
            if tgt_bnk:
                destination = self._safe_game_file(cooked, tgt_bnk)
                transaction.replace(
                    destination,
                    lambda output: shutil.copyfile(os.path.join(back, tgt_bnk), output),
                )

            self.presets.remove_swap(swap)
            transaction.commit()
            return True, "msg.swap_restored", swap.target_label
        except Exception as exc:
            self.presets.presets = preset_snapshot
            self.presets.current_preset = current_preset_snapshot
            try:
                self.presets.save()
            except OSError:
                pass
            if transaction is not None:
                transaction.rollback()
            return False, "msg.restore_failed", str(exc)

    def restore_all(self, install):
        swaps = self.presets.active_by_install(install.get("name", ""))
        count = 0
        errors = []
        for swap in list(swaps):
            ok, *msg = self.restore_swap(install, swap)
            if ok:
                count += 1
            else:
                errors.append(msg)
        return count, errors

    def remove_record(self, swap):
        self.presets.remove_swap(swap)
        return True, "msg.record_removed", swap.target_label

    def _install_for_swap(self, swap):
        install = self.cfg.get_install(swap.install_id or swap.install_name)
        if install is None:
            return {
                "name": swap.install_name or swap.install_source,
                "source": swap.install_source,
                "cookedDir": swap.install_cooked_dir,
            }
        return install

    def ensure_swap_applied(self, d):
        swap = Swap.from_dict(d)
        install = self._install_for_swap(swap)
        cooked = install.get("cookedDir", "")
        if not cooked or not os.path.isdir(cooked):
            return False, f"Install missing: {cooked}"

        tgt = os.path.join(cooked, swap.target_file)
        src = os.path.join(cooked, swap.source_file)
        if not os.path.exists(tgt):
            return False, f"File {swap.target_file} missing"

        back = self.backups_dir(install)
        baseline = os.path.join(back, swap.target_file)
        if not os.path.exists(baseline):
            return False, f"No backup for {swap.target_file}"

        if _file_sig(tgt) == _file_sig(baseline):
            if not os.path.exists(src):
                return False, f"Source {swap.source_file} missing"
            # Re-apply full swap
            from joga_app.catalog import CatalogItem
            dummy_src = CatalogItem(swap.source_file, swap.source_label, "")
            dummy_tgt = CatalogItem(swap.target_file, swap.target_label, "")
            ok, *msg = self.apply_swap(install, dummy_src, dummy_tgt)
            if ok:
                return True, f"Re-applied: {swap.source_label} → {swap.target_label}"
            return False, f"Failed: {msg}"
        return True, "Already active"

    def check_for_drift(self):
        results = []
        for swap in self.presets.active_swaps():
            ok, msg = self.ensure_swap_applied(swap.to_dict())
            if ok and msg.startswith("Re-applied"):
                results.append(msg)
        return results

    @staticmethod
    def load_history():
        data = read_json(SWAPS_LOG_FILE, [])
        return data if isinstance(data, list) else []

    @staticmethod
    def clear_history():
        atomic_write_json(SWAPS_LOG_FILE, [])
