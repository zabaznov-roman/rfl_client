#!/usr/bin/env python3
"""
prepare_deps.py — скачивает недостающие для сборки RF Online клиента зависимости.

Скачивает:
  1. DirectX 8.1 SDK (dx81sdk.exe, ~90 МБ) с официального архива Microsoft,
     распаковывает в dx81_extract/, кладёт путь в GITHUB_OUTPUT.
  2. BASS 2.4 SDK (bassenc.zip с un4seen.com) — на случай, если где-то
     используется bass.h (в текущем коде не обнаружен, но оставляем запас).

Все артефакты складываются в каталог, указанный переменной окружения
DEPS_DIR (по умолчанию ./_deps).

Выходные данные (GITHUB_OUTPUT):
  dxsdk_include  — каталог с заголовками DX8 SDK (Include)
  dxsdk_lib      — каталог с библиотеками DX8 SDK (Lib)
  dxsdk_redist   — каталог redist DLL из состава SDK
"""
import os
import subprocess
import sys
import urllib.request
import zipfile

DX81_URLS = [u for u in [os.environ.get("DX81SDK_URL", "")] if u] + [
    # Официальный архив Microsoft
    "https://download.microsoft.com/download/8/4/A/84A35BF1-CCD0-460F-AE7B-DBFA71F5CD66/dx81sdk.exe",
    # Зеркала (иногда меняют хеш-сегмент в URL)
    "https://download.microsoft.com/download/a/1/9/a19cf9fe-6e0f-433a-a3ef-fd104f31b18c/DX81SDK.exe",
    "https://archive.org/download/DX81SDK/dx81sdk.exe",
]

BASS_URLS = [
    "https://www.un4seen.com/stuff/bass24.zip",
    "https://www.un4seen.com/files/bass24.zip",
]


def log(msg):
    print(f"[prepare_deps] {msg}", flush=True)


def download(url, dest):
    """Скачать url в dest. Возвращает True при успехе."""
    try:
        log(f"downloading {url}")
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (Windows NT; build-bot)"}
        )
        with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length", "0"))
            done = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(
                        f"\r  {done // (1 << 20)} MiB / {total // (1 << 20)} MiB",
                        end="",
                        flush=True,
                    )
        print()
        return os.path.getsize(dest) > 1_000_000
    except Exception as e:  # noqa: BLE001
        print()
        log(f"  failed: {e}")
        if os.path.exists(dest):
            os.remove(dest)
        return False


def extract_dx81(exe_path, out_dir):
    """Распаковать self-extracting DX8.1 SDK archive.

    dx81sdk.exe — это SFX-архив с встроенным zip-контентом (как и старые
    SDK-установщики MS). Пробуем: 7z -> unzip через Python zipfile
    (поиск EOCD-записи) -> nsis extraction.
    """
    os.makedirs(out_dir, exist_ok=True)

    # 1) пробуем 7z, если доступен (GitHub runners его имеют)
    for tool in ("7z", "7za"):
        try:
            rc = subprocess.call(
                [tool, "x", "-y", f"-o{out_dir}", exe_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if rc == 0 and os.listdir(out_dir):
                log(f"extracted with {tool}")
                return True
        except FileNotFoundError:
            pass

    # 2) Python zipfile: найти начало zip по сигнатуре PK\x03\x04 или EOCD
    with open(exe_path, "rb") as f:
        data = f.read()
    idx = data.find(b"PK\x05\x06")  # EOCD
    if idx != -1:
        # от EOCD идём назад к первому локальному заголовку
        start = data.rfind(b"PK\x03\x04", 0, idx)
        if start != -1:
            tmp = exe_path + ".inner.zip"
            with open(tmp, "wb") as f:
                f.write(data[start:])
            try:
                with zipfile.ZipFile(tmp) as z:
                    z.extractall(out_dir)
                log("extracted embedded zip with python zipfile")
                return True
            except Exception as e:  # noqa: BLE001
                log(f"embedded zip extraction failed: {e}")

    # 3) прямой zip (если файл оказался обычным архивом)
    try:
        with zipfile.ZipFile(exe_path) as z:
            z.extractall(out_dir)
        log("extracted as plain zip")
        return True
    except Exception:  # noqa: BLE001
        pass

    return False


def find_subdir(root, name):
    """Найти каталог `name` (регистронезависимо) в дереве root."""
    name_l = name.lower()
    for dp, dns, _ in os.walk(root):
        for d in dns:
            if d.lower() == name_l:
                return os.path.join(dp, d)
    return None


def set_output(kv):
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        log(f"GITHUB_OUTPUT not set, would output: {kv}")
        return
    with open(out, "a", encoding="utf-8") as f:
        for k, v in kv.items():
            f.write(f"{k}={v}\n")
    log(f"outputs: {kv}")


def main():
    deps = os.environ.get("DEPS_DIR", os.path.join(os.getcwd(), "_deps"))
    os.makedirs(deps, exist_ok=True)

    ok = True

    # --- DirectX 8.1 SDK ---
    dx_exe = os.path.join(deps, "dx81sdk.exe")
    dx_dir = os.path.join(deps, "dx81sdk")
    got = False
    if os.path.exists(dx_exe) and os.path.getsize(dx_exe) > 1_000_000:
        got = True
    else:
        for u in DX81_URLS:
            if download(u, dx_exe):
                got = True
                break
    extracted = False
    if got:
        extracted = extract_dx81(dx_exe, dx_dir)
    if extracted:
        inc = find_subdir(dx_dir, "Include")
        lib = find_subdir(dx_dir, "Lib")
        if inc and lib:
            set_output({"dxsdk_include": inc, "dxsdk_lib": lib, "dxsdk_found": "true"})
            log(f"DX8 SDK ready:\n  include={inc}\n  lib={lib}")
        else:
            log("ERROR: распаковка прошла, но Include/Lib не найдены")
            ok = False
            set_output({"dxsdk_found": "false"})
    else:
        log("WARNING: DirectX 8.1 SDK скачать/распаковать не удалось.")
        log("Положите dx81sdk.exe вручную в release 'DirectX SDK Downloads' ")
        log("https://www.microsoft.com/en-us/download/details.aspx?id=8568 ")
        log("или используйте секрет DX81SDK_URL с прямой ссылкой.")
        set_output({"dxsdk_found": "false"})

    # --- BASS (опционально) ---
    bass_zip = os.path.join(deps, "bass24.zip")
    for u in BASS_URLS:
        if download(u, bass_zip):
            try:
                with zipfile.ZipFile(bass_zip) as z:
                    z.extractall(os.path.join(deps, "bass"))
                set_output({"bass_found": "true"})
            except Exception as e:  # noqa: BLE001
                log(f"bass unzip failed: {e}")
                set_output({"bass_found": "false"})
            break
    else:
        set_output({"bass_found": "false"})

    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
