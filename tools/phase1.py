"""Inspeciona, gera ou compila os módulos da versão base de Star Fox."""

import argparse
from collections import Counter
import hashlib
import json
import msvcrt
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "refs" / "ocarina"
REFERENCE_COMMIT = "a12af268d7474b0d63a903d3a27bf1c487d0ecbe"
PATCH_DIR = ROOT / "patches"
RUNTIME_PATCHES = tuple(PATCH_DIR / name for name in (
    "phase1-module-window.patch", "phase2-boot.patch", "phase3-nvn.patch", "phase4-shaders.patch",
    "phase5-mission.patch",
))
PROFILE = ROOT / "config" / "starfox-base.json"
BUILD = ROOT / "build"
EXEFS = BUILD / "extracted" / "base-00000000" / "exefs"
GENERATED = ROOT / "generated" / "phase1-base"
GENERATION_STAMP = GENERATED / "lifter.sha256"
RUNTIME_BUILD = BUILD / "phase1-runtime"
GAME_BUILD = BUILD / "phase1-base"
MODULES = ("main", "subsdk0", "subsdk1", "subsdk2", "subsdk3", "sdk")


def reference_patch():
    delta = subprocess.check_output([
        "git", "-C", str(REFERENCE), "diff", "--binary", "--full-index", "--no-ext-diff",
        "--no-textconv", "--no-color", "--unified=3", "--src-prefix=a/", "--dst-prefix=b/", "HEAD",
    ], text=True, encoding="utf-8")
    if not delta:
        return None
    for patch in RUNTIME_PATCHES:
        if delta == patch.read_text(encoding="utf-8"):
            return patch
    raise ValueError("O checkout de referência contém alterações fora dos patches do port")


def verify_inputs():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    for name, expected in profile["exefs_sha256"].items():
        with (EXEFS / name).open("rb") as module:
            actual = hashlib.file_digest(module, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"SHA-256 divergente no ExeFS base: {name}")

    reference = subprocess.check_output(
        ["git", "-C", str(REFERENCE), "rev-parse", "HEAD"], text=True
    ).strip()
    if reference != REFERENCE_COMMIT:
        raise ValueError(f"Revisão da referência inesperada: {reference}")
    reference_patch()
    return profile


def inspect_modules(profile):
    sys.path.insert(0, str(REFERENCE / "recomp"))
    from layout import layout
    from nso import Nso

    bases = {name: base for name, base, _ in layout(EXEFS)}
    if tuple(bases) != MODULES:
        raise ValueError("O layout do ExeFS difere do perfil base")
    modules = {name: Nso(EXEFS / name) for name in (*MODULES, "rtld")}
    sonames = {}
    exports = {}
    for name in MODULES:
        module = modules[name]
        if 14 in module.dyn:  # DT_SONAME
            sonames[module.cstr(module.strtab + module.dyn[14])] = name
        for symbol, _, section, _, _ in module.syms:
            if symbol and section:
                exports.setdefault(symbol, name)

    reports = {}
    for name, module in modules.items():
        resolved = Counter()
        missing = {"weak": [], "strong": []}
        for symbol, info, section, _, _ in module.syms:
            if not symbol or section:
                continue
            if symbol in exports:
                resolved[exports[symbol]] += 1
            else:
                missing["weak" if info >> 4 == 2 else "strong"].append(symbol)
        reports[name] = {
            "base": hex(bases[name]) if name in bases else None,
            "build_id": module.build_id,
            "image_size": module.size,
            "text_size": module.text[1],
            "needed": {soname: sonames.get(soname) for soname in module.needed},
            "relocation_counts": dict(sorted(Counter(kind for _, kind, _, _ in module.relocs).items())),
            "tlsdesc": [
                {"offset": hex(offset), "symbol_index": symbol, "addend": addend}
                for offset, kind, symbol, addend in module.relocs if kind == 1031
            ],
            "dt_init": hex(module.dyn[12]) if 12 in module.dyn else None,
            "init_array_bytes": module.dyn.get(27, 0),
            "imports_by_module": dict(sorted(resolved.items())),
            "unresolved_imports": {binding: sorted(names) for binding, names in missing.items()},
        }
    return {"profile": profile, "reference_commit": REFERENCE_COMMIT, "modules": reports}


def run_reference(script, args):
    subprocess.run([sys.executable, str(REFERENCE / script), *map(str, args)], cwd=ROOT, check=True)


def apply_reference_patch():
    current = reference_patch()
    target = RUNTIME_PATCHES[-1]
    if current != target:
        git_apply = ["git", "-C", str(REFERENCE), "apply"]
        subprocess.run([*git_apply, "--cached", "--check", str(target)], check=True)
        if current:
            subprocess.run([*git_apply, "--reverse", str(current)], check=True)
        try:
            subprocess.run([*git_apply, str(target)], check=True)
        except subprocess.CalledProcessError:
            if current:
                subprocess.run([*git_apply, str(current)], check=True)
            raise


def lifter_digest():
    delta = subprocess.check_output([
        "git", "-C", str(REFERENCE), "diff", "--binary", "--full-index", "--no-color",
        "--no-ext-diff", "--no-textconv", "HEAD", "--", "recomp",
    ])
    return hashlib.sha256(delta).hexdigest()


def build(jobs):
    if not GENERATION_STAMP.is_file() or GENERATION_STAMP.read_text(encoding="ascii").strip() != lifter_digest():
        raise ValueError("O C gerado precisa do lifter atual. Execute tools/phase1.py generate.")
    common = [
        "--version", "starfox-base", "--gen", GENERATED, "--expected", PROFILE,
        "--exefs", EXEFS, "--romfs", EXEFS.parent / "romfs",
        "--profile", BUILD / "phase1-profile", "--jobs", jobs,
    ]
    run_reference("tools/build_game.py", [
        *common, "--out", RUNTIME_BUILD, "--modules", "subsdk3", "--make-runtime-lib",
    ])
    run_reference("tools/build_game.py", [
        *common, "--out", GAME_BUILD, "--runtime-lib", RUNTIME_BUILD / "libtotkrt.a",
    ])


def run_build_action(action, jobs):
    with (BUILD / "phase1.lock").open("ab") as lock:
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise ValueError("Não foi possível reservar a saída da Fase 1. Verifique se há outro build ativo.") from error
        apply_reference_patch()
        if action == "generate":
            digest = lifter_digest()
            GENERATION_STAMP.unlink(missing_ok=True)
            run_reference("recomp/gen.py", [
                "--exefs", EXEFS, "--out", GENERATED,
                "--modules", ",".join(MODULES), "--jobs", jobs,
            ])
            if lifter_digest() != digest:
                raise ValueError("O lifter mudou durante a geração")
            GENERATION_STAMP.write_text(digest + "\n", encoding="ascii")
        else:
            build(jobs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "generate", "build"))
    parser.add_argument("--jobs", type=int, default=12)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs deve ser positivo")
    try:
        profile = verify_inputs()
        if args.action == "inspect":
            print(json.dumps(inspect_modules(profile), indent=2))
        else:
            run_build_action(args.action, args.jobs)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Erro: {error}\n")


if __name__ == "__main__":
    main()
