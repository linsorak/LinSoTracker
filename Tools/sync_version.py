import argparse
import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
CORE_SERVICE = ROOT / "Tools" / "CoreService.py"
PROPERTIES = ROOT / "properties.rc"


def read_core_version():
    content = CORE_SERVICE.read_text(encoding="utf-8")
    match = re.search(r'self\.version\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        raise RuntimeError("Unable to find self.version in CoreService.py")
    return match.group(1)


def version_tuple(version):
    parts = version.split(".")
    numbers = []
    for part in parts[:4]:
        number = re.match(r"\d+", part)
        numbers.append(int(number.group(0)) if number else 0)
    while len(numbers) < 4:
        numbers.append(0)
    return tuple(numbers)


def update_properties(version):
    content = PROPERTIES.read_text(encoding="utf-8")
    fixed = ", ".join(str(part) for part in version_tuple(version))
    content = re.sub(r"filevers=\([^)]+\)", f"filevers=({fixed})", content)
    content = re.sub(r"prodvers=\([^)]+\)", f"prodvers=({fixed})", content)
    content = re.sub(
        r"StringStruct\(u'FileVersion', u'[^']*'\)",
        f"StringStruct(u'FileVersion', u'{version}')",
        content,
    )
    content = re.sub(
        r"StringStruct\(u'ProductVersion', u'[^']*'\)",
        f"StringStruct(u'ProductVersion', u'{version}')",
        content,
    )
    PROPERTIES.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-version", action="store_true")
    args = parser.parse_args()

    version = read_core_version()
    if args.print_version:
        print(version)
        return

    update_properties(version)
    print(f"Synchronized properties.rc to version {version}")


if __name__ == "__main__":
    main()
