"""Inventaria o NUP de Star Fox e prepara o ExeFS ou RomFS local."""

import argparse
import hashlib
import json
import struct
from pathlib import Path
from tempfile import TemporaryDirectory

from nup import format as nup_format
from nup.access import iter_children
from nup.read import NupReader
from zstandard import ZstdError


TITLE_ID = 0x0400E88025B1A000
EXEFS_NAMES = {b"main", b"main.npdm", b"rtld", b"sdk", b"subsdk0", b"subsdk1", b"subsdk2", b"subsdk3"}
ROMFS_NAMES = {b"data.zip", b"veclipse_build.cvar"}
MAX_MODULE_SIZE = 128 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"


def inventory(reader):
    packages = []
    for package in reader.packages:
        entry = {
            "index": package.index,
            "title_id": f"{package.title_id:016X}",
            "kind": package.kind_name,
            "revision_raw": f"{package.version:#x}",
        }
        for label, index in (("exefs", package.exefs_dir), ("romfs", package.romfs_dir)):
            files = {}
            if index != nup_format.NO_DIR:
                for node in iter_children(reader, index):
                    name = node.name.decode("utf-8", "replace")
                    if node.is_dir:
                        files[f"{name}/"] = {"directory": True}
                        continue
                    _, size, digest, _, packed, codec = reader.file_info(node.index)
                    files[name] = {
                        "size": size,
                        "stored_size": packed,
                        "codec": "zstd" if codec == nup_format.CODEC_ZSTD else "raw",
                        "sha256_from_toc": digest.hex(),
                    }
            entry[label] = files
        packages.append(entry)
    return {
        "size": reader.super["file_size"],
        "toc_sha256": reader.super["toc_sha256"].hex(),
        "packages": packages,
    }


def find_package(reader, kind):
    candidates = [p for p in reader.packages if p.title_id == TITLE_ID and p.kind_name == kind]
    if len(candidates) != 1:
        raise ValueError(f"Esperado um único pacote {kind}, encontrados {len(candidates)}")
    return candidates[0]


def extract_exefs(reader, kind):
    package = find_package(reader, kind)
    if package.exefs_dir == nup_format.NO_DIR:
        raise ValueError(f"Pacote {kind} sem ExeFS")
    nodes = iter_children(reader, package.exefs_dir)
    if len(nodes) != len(EXEFS_NAMES) or {n.name for n in nodes if not n.is_dir} != EXEFS_NAMES:
        raise ValueError(f"Layout ExeFS diferente do esperado para o pacote {kind}")

    dest = BUILD / "extracted" / f"{kind}-{package.version:08x}" / "exefs"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise FileExistsError(f"A saída já existe: {dest}")

    # A pasta final só aparece depois que todos os módulos passam na verificação.
    with TemporaryDirectory(dir=dest.parent) as tmp:
        stage = Path(tmp) / "exefs"
        stage.mkdir()
        for node in nodes:
            name, size, digest, _, packed, _ = reader.file_info(node.index)
            if max(size, packed) > MAX_MODULE_SIZE:
                raise ValueError(f"Módulo acima do limite de extração: {name!r}")
            data = reader.read_file(node.index)
            if hashlib.sha256(data).digest() != digest:
                raise ValueError(f"SHA-256 divergente: {name!r}")
            magic = b"META" if name == b"main.npdm" else b"NSO0"
            if not data.startswith(magic):
                raise ValueError(f"Assinatura inesperada: {name!r}")
            (stage / name.decode("ascii")).write_bytes(data)
        stage.rename(dest)
    print(f"{len(nodes)} arquivos conferidos e extraídos em {dest}")


def pack_romfs(reader, dump):
    package = find_package(reader, "base")
    profile = json.loads((ROOT / "config" / "starfox-base.json").read_text(encoding="utf-8"))
    if package.version != int(profile["revision_raw"], 16) or package.exefs_dir == nup_format.NO_DIR:
        raise ValueError("O pacote base não corresponde ao perfil do port")
    exefs = {n.name.decode(): reader.file_info(n.index)[2].hex()
             for n in iter_children(reader, package.exefs_dir) if not n.is_dir}
    if exefs != profile["exefs_sha256"] or package.romfs_dir == nup_format.NO_DIR:
        raise ValueError("ExeFS incompatível com o perfil base ou RomFS ausente")
    nodes = iter_children(reader, package.romfs_dir)
    if len(nodes) != len(ROMFS_NAMES) or {n.name for n in nodes if not n.is_dir} != ROMFS_NAMES:
        raise ValueError("Layout RomFS diferente do esperado para o pacote base")

    dest = BUILD / "extracted" / f"base-{package.version:08x}" / "romfs"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise FileExistsError(f"A saída já existe: {dest}")
    image_hash = hashlib.sha256()
    entries = []
    with TemporaryDirectory(dir=dest.parent) as tmp, dump.open("rb") as source:
        stage = Path(tmp) / "romfs"
        stage.mkdir()
        with (stage / "romfs.bin").open("wb") as image:
            for node in sorted(nodes, key=lambda n: n.name):
                name, size, expected, offset, packed, codec = reader.file_info(node.index)
                if codec != nup_format.CODEC_RAW or size != packed:
                    raise ValueError(f"Esperada uma entrada RomFS raw: {name!r}")
                pad = bytes(-image.tell() % 16)
                image.write(pad)
                image_hash.update(pad)
                entries.append({"path": name.decode(), "offset": image.tell(), "size": size})
                source.seek(offset)
                file_hash = hashlib.sha256()
                remaining = size
                while remaining:
                    chunk = source.read(min(remaining, 8 << 20))
                    if not chunk:
                        raise ValueError(f"Leitura incompleta no NUP: {name!r}")
                    image.write(chunk)
                    file_hash.update(chunk)
                    image_hash.update(chunk)
                    remaining -= len(chunk)
                if file_hash.digest() != expected:
                    raise ValueError(f"SHA-256 divergente: {name!r}")
            size = image.tell()
        manifest = {"status": "pass", "source": "NUP base, SHA-256 verificado por entrada",
                    "romfs_size": size, "romfs_sha256": image_hash.hexdigest(), "files": entries}
        (stage / "index.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        stage.rename(dest)
    print(f"RomFS base verificado em {dest} ({size} bytes)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--extract-exefs", choices=("base", "update"))
    mode.add_argument("--pack-romfs", action="store_true", help="prepara a imagem RomFS da base")
    args = parser.parse_args()
    try:
        with NupReader(str(args.dump)) as reader:
            if not any(p.title_id == TITLE_ID for p in reader.packages):
                raise ValueError(f"Title ID {TITLE_ID:016X} ausente no NUP")
            if args.extract_exefs:
                extract_exefs(reader, args.extract_exefs)
            elif args.pack_romfs:
                pack_romfs(reader, args.dump)
            else:
                print(json.dumps(inventory(reader), indent=2))
    except (nup_format.NupError, OSError, ValueError, struct.error, ZstdError) as error:
        parser.exit(1, f"Erro: {error}\n")


if __name__ == "__main__":
    main()
