# OurPoker: review guide

Paths are relative to this repository. `PY` is `python3 -B` (Python 3.12) with an aepm checkout on `PYTHONPATH`; `OURPOKER_COMPONENTS` names a folder with one checkout per component and `OURAPPS` a checkout of the ourapps catalogue (INSTRUCTIONS.md part 5).

## 1. What exists

- `recipe.json` (package `ourapps-ae/ourpoker` 0.8.0): 28 questions, 39 slots each naming an exact class reference and preferred component version, 65 connections, 3 jobs, 3 scale bands, 15 answer sets plus the default.
- The application-specific component: screen flow on web, Apple and Android, the server's wiring, house rules, text in four languages, lessons, art, sounds, the desktop entry, end-to-end specs, the build files, the stand-ins, the 39 authoritative class bundles and the pinned Android and Apple dependency inputs (`component.json`, 299 artefacts, 63 conditional, 18 stand-ins).
- `page/` drawings, `INSTRUCTIONS.md` (asking, accounts, install, build and run, maintenance), `INTEGRATION-GAPS.md` (status and decisions).
- `authoring/` and `scripts/` (not packaged): the generators, the conditional artefact check, the install proof (`try_install.py`) and the Kotlin stand-in type-check (`kotlin-stand-ins/`).

## 2. How to inspect

- The recipe: `page/diagram.svg` (all 39), `page/diagram-*.svg` (by group), `page/diagram-application.svg`, `page/description.md`, `recipe.json`.
- One design: `PY -m aepm design ourpoker@0.8.0 --store STORE --answers answers.json --out definition.json` on a store that holds the packages (`authoring/try_install.py` makes one).
- What a design installs: `PY authoring/check_conditional_artefacts.py -v`.
- Gaps and decisions: `INTEGRATION-GAPS.md`.

## 3. How to run every check

INSTRUCTIONS.md part 5 lists the commands. The install proof: `PY authoring/try_install.py` (default `default`, `local-web`, `fill-empty-own-hardware`, `lounge-web-ios`; any answer-set id or answers file).

## 4. Verified and not verified

Verified:
- Recipe tests: `tests/recipe.test.ts` and `tests/portable.test.ts` (38 tests), `tests/evaluate_recipe_test.py` (47 tests: aepm's evaluator over every combination of the deciding answers, with the CEL parity check against `@bufbuild/cel`), `tests/conditional_artefacts_test.py` (17 tests), `authoring/check_conditional_artefacts.py` (16 answer sets, no violations), the ourapps catalogue validator with every component's class, provenance and platform declarations.
- `authoring/try_install.py` for `default`, `local-web` and `default` with `--substitute theme=ourapps-ae/theme-high-contrast@0.4.0`: the 39 components, the alternative theme and the recipe packed, released, reviewed (including every class-owned check) and guardian-signed with disposable identities, each design installed with `aepm install`; server and web type-checked, server tests passed, the server ran on Node; in headless Chrome a player sat, a computer player joined and a hand was played through the page's Fold control to its settlement with every chip counted, the table inside a 1280x800 window; Apple designs built for the iOS and tvOS simulators and Mac Catalyst with only the answered languages and the pinned Swift packages; Android built with the pinned Gradle locks and checksums, unit-tested, and played on the emulator to a settled hand; the desktop web build.
- The Kotlin stand-ins type-check on the JVM against the calls the application makes (`authoring/kotlin-stand-ins`).
- Windows 11 in PowerShell from a local store: `aepm doctor`, `aepm install`, the server's type check, tests and start, the web build, and the desktop tests and build (INSTRUCTIONS.md part 3 and part 4, Windows). `npm run package:win` exits 1 there: Smart App Control refuses packaging's unsigned uninstaller step.
- In-place update of an installed `local-web` application (33 components, serverAddress and webAddress changed): `aepm propose-update --trusted --allow-network` (every package's checks run on the stage), `aepm approve` with the owner key, `aepm apply`, `aepm recover`; `node_modules` removed first, as INSTRUCTIONS.md part 4 step 2 says (a tree holding dependency links is refused).
- The Android app built and unit-tested on Windows 11 with strict Gradle dependency verification.
- The workflows in `implementation/repository/workflows/` pass actionlint; the Android room-list check (`android_screen.py`) and the browser check were run on a Mac against a local server.

Not verified: Apple apps running on a simulator or device, the Windows installer built or run on Windows, Cloudflare deployment, GitHub workflows and releases run on GitHub, the aepm-update workflow on GitHub, real video and store services, `aepm fetch` from the published catalogue.

## 5. Decisions

`INTEGRATION-GAPS.md` "Decisions"; each names the place to change it (`authoring/make_recipe.py`, `scripts/make_component.py`, `implementation/stand-ins/`).

## 6. Open items

- Deferred: client items G9.2 to G9.6; paper rows G7.15 and G7.16; G7.6 chip colours; G7.17 SVG safety rule.
- Licence wording stays deferred.
