#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import traceback
import zipfile
from io import BytesIO
from os.path import relpath
from pathlib import Path
from tokenize import NAME, tokenize
from types import ModuleType

from ocelescope import OCELExtension, Plugin

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)


def is_concrete_subclass(obj: object, base: type) -> bool:
    return (
        isinstance(obj, type)
        and issubclass(obj, base)
        and obj is not base
        and not getattr(obj, "__abstractmethods__", False)
    )


def load_package(pkg_dir: Path) -> ModuleType | None:
    init_py = pkg_dir / "__init__.py"
    if not init_py.exists():
        return None

    module_name = f"plugin_{pkg_dir.name}"
    try:
        spec = importlib.util.spec_from_file_location(
            module_name,
            init_py,
            submodule_search_locations=[str(pkg_dir)],
        )
        if spec is None or spec.loader is None:
            print(f"⚠️  Skipping {pkg_dir}: could not create import spec")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type: ignore[arg-type]
        return module
    except Exception:
        print(f"❌ Failed to import {pkg_dir} as {module_name}:\n{traceback.format_exc()}")
        sys.modules.pop(module_name, None)
        return None


def module_has_plugin(module: ModuleType) -> bool:
    found = False
    for obj in vars(module).values():
        if is_concrete_subclass(obj, Plugin):
            print(f"✅ Found Plugin: {obj.__name__} (from {module.__name__})")
            found = True
    for obj in vars(module).values():
        if is_concrete_subclass(obj, OCELExtension):
            print(f"ℹ️  Found Extension: {obj.__name__} (from {module.__name__})")
    return found


# ----------------- abs2rel embedded logic ----------------- #


def run_abs2rel_on_path(root_dir: Path) -> None:
    print(f"🔁 Converting absolute to relative imports in {root_dir} ...")

    all_py_files = tuple(root_dir.rglob("*.py"))

    path_to_abs_dotted_import = {
        path: ".".join(path.relative_to(root_dir).with_suffix("").parts) for path in all_py_files
    }

    abs_dotted_import_to_path = {v: k for k, v in path_to_abs_dotted_import.items()}

    possible_local_imports = path_to_abs_dotted_import.values()
    path_to_import_data = {}

    for path in all_py_files:
        import_data = get_imports_data(path, possible_local_imports)
        if import_data:
            path_to_import_data[path] = import_data

    no_of_imports = sum(len(imports) for imports in path_to_import_data.values())
    if no_of_imports == 0:
        print("ℹ️  No absolute imports to convert.")
        return

    print(f"✏️  Rewriting {no_of_imports} imports across {len(path_to_import_data)} files.")

    for path in path_to_import_data:
        replace_imports(
            path,
            path_to_import_data,
            path_to_abs_dotted_import,
            abs_dotted_import_to_path,
        )


def get_imports_data(path, possible_local_imports):
    local_imports_data = {}
    tokens = tokenize(BytesIO(path.read_bytes()).readline)
    line_where_found_from = None

    for (
        token_type,
        string,
        (_, string_start),
        (line_number, string_end),
        line_text,
    ) in tokens:
        if line_where_found_from is not None and line_number != line_where_found_from:
            line_where_found_from = None

        if line_where_found_from is None:
            if token_type == NAME and string == "from":
                line_where_found_from = line_number
                import_start_index = string_end + 1
        elif token_type == NAME and string == "import":
            import_end_index = string_start - 1
            abs_dotted_import = line_text[import_start_index:import_end_index].replace(" ", "")
            if abs_dotted_import in possible_local_imports:
                line_index = line_where_found_from - 1
                local_imports_data[line_index] = (
                    abs_dotted_import,
                    import_start_index,
                    import_end_index,
                )
            line_where_found_from = None

    return local_imports_data


def replace_imports(path, path_to_import_data, path_to_abs_dotted_import, abs_dotted_import_to_path):
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    import_data = path_to_import_data[path]

    for (
        line_index,
        (abs_dotted_import, import_start_index, import_end_index),
    ) in import_data.items():
        path_of_absolute_import = abs_dotted_import_to_path[abs_dotted_import]
        rpath = Path(relpath(path_of_absolute_import, path))
        rel_dotted_import = ".".join("" if part == ".." else part for part in (rpath.parts[:-1] + (rpath.stem,)))

        line_text = lines[line_index]
        head = line_text[:import_start_index]
        tail = line_text[import_end_index:]
        new_text = head + rel_dotted_import + tail
        lines[line_index] = new_text

    path.write_text("".join(lines), encoding="utf-8")


# ----------------- zipping logic ----------------- #


def zip_package(pkg_dir: Path) -> Path:
    zip_path = DIST / f"{pkg_dir.name}.zip"
    base_for_archive = pkg_dir.parent
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in pkg_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(base_for_archive))
    print(f"📦 Wrote {zip_path}")
    return zip_path


# ----------------- main ----------------- #


def main() -> int:
    if not SRC.exists():
        print(f"❌ Expected src directory at {SRC}")
        return 2

    # ✅ Run abs2rel on all of src/
    run_abs2rel_on_path(SRC)

    zipped_any = False

    for pkg_dir in sorted(SRC.iterdir()):
        if not (pkg_dir.is_dir() and (pkg_dir / "__init__.py").exists()):
            continue
        if pkg_dir.name.startswith("_"):
            continue

        print(f"\n🔎 Checking {pkg_dir} ...")
        module = load_package(pkg_dir)
        if module and module_has_plugin(module):
            zip_package(pkg_dir)
            zipped_any = True
        else:
            print(f"⏭️  No valid Plugin found in {pkg_dir}; skipping zip.")

    if not zipped_any:
        print("❌ No loadable plugin packages found in src/.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
