#!/usr/bin/env python3
"""Follow INSTRUCTIONS.md part 3 as a reader does, with the shell steps taken from the file itself.

  AEPM_CHECKOUT=<aepm checkout> python3.12 -B authoring/prove_instructions.py --work DIR [--answers FILE]

The packages come from a local store that try_install.py packs, releases, reviews and guardian-signs with stand-in keys,
because an unpublished recipe version is not on clodhub.com. Two lines of the text change for that, and only these:
`aepm fetch` (the packages are already in the store) and the `curl` of levelnpolicy.json (the stand-in release and
guardian keys are written there instead). Every other step runs as written, with STORE, POLICY, APP and <version>
filled in, in a reader folder of its own. report.json holds each step's command, exit status and output tail, and the
summary aepm verify prints. Exit status 0 when every step passed.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def blocks():
    text = (ROOT / "INSTRUCTIONS.md").read_text()
    part = text[text.index("## 3. Install"):text.index("On Windows, in PowerShell (Windows PowerShell 5.1")]
    return [re.sub(r"(?m)^   ", "", match.group(1)) for match in re.finditer(r"```\n(.*?)```", part, re.S)]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--answers", type=Path, help="answers.json for step 3 (default: the text's example)")
    arguments = parser.parse_args()
    aepm_checkout = Path(os.environ["AEPM_CHECKOUT"]).resolve()
    work = arguments.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / "authoring"))
    sys.path.insert(0, str(aepm_checkout))
    import try_install
    store, stand_in_policy, refs, reviews, blocked = try_install.prepare_store(work, ROOT.parent.parent / "components")
    if blocked:
        raise SystemExit(f"packages not guardian-signed: {sorted(blocked)}")
    version = json.loads((ROOT / "recipe.json").read_text())["version"]
    reader = work / "reader"
    reader.mkdir()
    (reader / "aepm").symlink_to(aepm_checkout)
    level_n = json.loads(stand_in_policy.read_text())
    (reader / "stand-in-levelnpolicy.json").write_text(json.dumps({"keys": {k: level_n["keys"][k] for k in ("release", "guardian")}}))
    names = {"STORE": str(store), "POLICY": str(reader / "policy.json"), "APP": str(reader / "app"), "<version>": version}
    found = blocks()
    steps = [("define aepm", found[0]),
             ("1 read INSTRUCTIONS.md", found[1].split("\n", 1)[1]),  # the fetch line is the change named above
             ("2 questions", found[2]),
             ("3 answers", None),
             ("4 design", found[4]), ("4 doctor", found[5]),
             ("5 resolve", found[7]),
             ("6 policy", found[8].replace("curl -fsSL https://clodhub.com/policy/levelnpolicy.json -o levelnpolicy.json",
                                           "cp stand-in-levelnpolicy.json levelnpolicy.json")),
             ("7 install", found[9]), ("8 verify", found[10])]
    answers = arguments.answers.read_text() if arguments.answers else found[3]
    (reader / "answers.json").write_text(answers)
    report = {"aepm": subprocess.run(["git", "-C", str(aepm_checkout), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
              "aepmStatus": subprocess.run(["git", "-C", str(aepm_checkout), "status", "--short"], capture_output=True, text=True).stdout,
              "version": version, "answers": json.loads(answers), "steps": []}
    script = ""
    ok = True
    for name, block in steps:
        if block is None:
            report["steps"].append({"step": name, "status": 0, "file": "answers.json"})
            continue
        for key, value in names.items():
            block = block.replace(key, value)
        script += block
        if name == "define aepm":
            continue
        result = subprocess.run(["bash", "-c", "set -e\n" + script], cwd=reader, capture_output=True, text=True, timeout=7200)
        script = found[0]  # each later step runs after the definition only
        entry = {"step": name, "command": block.strip(), "status": result.returncode,
                 "output": (result.stdout + result.stderr).strip().splitlines()[-12:]}
        if name == "8 verify":
            try:
                entry["result"] = json.loads(result.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                pass
        if name == "4 doctor" and result.returncode:
            entry["note"] = "doctor exits 1 when a tool for another target is missing; the text leaves that to the reader"
        report["steps"].append(entry)
        if result.returncode and name != "4 doctor":
            ok = False
            break
    (work / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    for entry in report["steps"]:
        print(entry["step"], "passed" if entry["status"] == 0 else f"exit {entry['status']}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
