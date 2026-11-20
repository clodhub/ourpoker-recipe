#!/usr/bin/env python3
"""Take the recipe's example images from an install proof's screenshots.

  python3 -B authoring/set_images.py FOLDER [--prefix PREFIX]

FOLDER holds the screenshots `try_install.py` keeps for a design (`<work>/designs/default`), or copies of them named
PREFIX + name (`classes/proof/screenshots` with `--prefix default-`). The images go to images/, and `images` in
authoring/foundations.json lists them, the browser table first. Run scripts/make_component.py after.
"""
import argparse
import json
import shutil
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOTS = [
    ("browser-table.png", "table-browser.png", "web", "A hand at the table in the browser, with the possible hands and their odds"),
    ("browser-lobby.png", "lobby-browser.png", "web", "The lobby in the browser: the players seated, waiting for one more or a computer player"),
    ("browser-settled.png", "showdown-browser.png", "web", "The end of a hand in the browser, with the pot paid out"),
    ("android-table.png", "table-android.png", "android", "Your turn at the table on an Android phone, with fold, call and raise"),
    ("android-table-settled.png", "showdown-android.png", "android", "The end of a hand on an Android phone"),
    ("apple-table.png", "table-ios.png", "ios", "A hand at the table on the iPhone simulator"),
]
LIMIT = 2 * 1024 * 1024


def size(path):
    raw = path.read_bytes()[:24]
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", raw[16:24])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--prefix", default="")
    arguments = parser.parse_args()
    target = ROOT / "images"
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir()
    images = []
    for name, destination, platform, caption in SHOTS:
        source = arguments.folder / (arguments.prefix + name)
        if not source.is_file():
            continue
        if source.stat().st_size > LIMIT:
            raise SystemExit(f"{source}: larger than 2 MiB")
        shutil.copyfile(source, target / destination)
        width, height = size(source)
        images.append({"path": f"images/{destination}", "caption": caption, "platform": platform, "width": width, "height": height})
    if not images or images[0]["path"] != "images/table-browser.png":
        raise SystemExit(f"{arguments.folder}: no browser table screenshot")
    path = ROOT / "authoring/foundations.json"
    document = json.loads(path.read_text())
    document["images"] = images
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(images)} images: " + ", ".join(image["path"] for image in images))


if __name__ == "__main__":
    main()
