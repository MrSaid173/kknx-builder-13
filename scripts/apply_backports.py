#!/usr/bin/env python3
"""Накладывает бэкпорты из backports/<имя>/<имя>.patch по значениям experiments.

Запуск: apply_backports.py <корень ядра>   (EXPERIMENTS берётся из окружения)

  lzorle   lzo-rle для zram (Linux 5.1): lib/lzo из 5.4, crypto/lzo-rle.c, строка lzo-rle в zcomp.c
  tcppace  TCP internal pacing (Linux 4.13): BBR и SO_MAX_PACING_RATE работают без fq (адаптация под TSQ 4.9)

Строго: патч обязан лечь без отклонений на файлы закреплённого коммита ядра. Уже наложенный патч
(обратное наложение проходит) пропускается. При смене kernel_ref патчи могут перестать ложиться: тогда сборка упадёт здесь, а не позже.
"""
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
BACKPORTS = {
    "lzorle": "backports/lzorle/lzorle.patch",
    "tcppace": "backports/tcppace/tcppace.patch",
}


def die(msg):
    print(f"[ОШИБКА] {msg}", file=sys.stderr)
    sys.exit(1)


def run_patch(args, patch):
    with open(patch, "rb") as f:
        return subprocess.run(["patch", "-p1", "--no-backup-if-mismatch", *args], cwd=ROOT, stdin=f,
                              capture_output=True, text=True)


def main():
    toks = [t.strip().lower() for t in os.environ.get("EXPERIMENTS", "").replace(";", ",").replace(" ", ",").split(",")]
    todo = [t for t in BACKPORTS if t in toks]
    if not todo:
        print("[backports] нечего накладывать")
        return
    if not (ROOT / "Makefile").exists() or not (ROOT / "net").is_dir():
        die(f"{ROOT}: не корень ядра")
    for name in todo:
        patch = REPO / BACKPORTS[name]
        if not patch.exists():
            die(f"нет файла {patch}")
        if run_patch(["--dry-run", "-R", "-s"], patch).returncode == 0:
            print(f"[backports] {name}: уже наложен")
            continue
        r = run_patch(["--dry-run", "-s"], patch)
        if r.returncode != 0:
            die(f"{name}: патч не ложится на это дерево (сменился kernel_ref?)\n{r.stdout}{r.stderr}")
        r = run_patch(["-s"], patch)
        if r.returncode != 0:
            die(f"{name}: ошибка наложения\n{r.stdout}{r.stderr}")
        files = [l.split(" b/", 1)[1] for l in patch.read_text(encoding="utf-8", errors="replace").splitlines()
                 if l.startswith("diff --git ")]
        print(f"[backports] {name}: наложен, файлов {len(files)}")


if __name__ == "__main__":
    main()
