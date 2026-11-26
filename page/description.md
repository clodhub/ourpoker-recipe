# OurPoker

A complete Texas hold'em game with two tables of two to nine players each. People play on phones, tablets, computers or the web; a television or any shared screen shows the public table; players can see and hear each other by video; computer players can fill empty seats; play has decision clocks, rising blinds and rebuys; and the game speaks English, French, German and Spanish.

## Who it is for

A group that wants its own poker night without accounts or an app store: a book club, a club's league night, a poker league, a company event. The group's developer owns the accounts and the server; nothing runs on our platform.

## Devices

Web, iPhone and iPad, Android, Mac, Windows and Apple TV. Each is a switch; the devices question decides which are built. The television shows the public table only and cannot act or see private cards.

## House rules by default

Two to nine players at a table, 5,000 chips each, blind levels of 10 minutes that double after level 16, 30 seconds to act before the game checks or folds, one rebuy of 5,000 chips until level 3, side pots, no-limit betting.

## The questions

There are 28 questions. An agent answers them from your description and puts the rest to you in one round: four questions with no answer yet (devices, how many people play, the video service address and where the server runs), plus the ones only an earlier answer brings in, asked in the same round as "if so" questions. It asks nothing else. Building and running it on your own machine needs no secret at all.

Always asked when they apply (7): where the server runs, and the names under which your secrets are kept.

- Where does the server run? (Cloudflare or your own hardware)
- Your Cloudflare account (when the server runs on Cloudflare)
- The video service key and secret (when there is video and builds are published)
- Your app store credentials (when publishing with updates or for iPhone and iPad)
- Your Android signing key (when publishing for Android)
- Your web deployment key (when publishing for the web)

Asked unless your description settles them (4):

- Which devices? (any of web, ios, android, macos, windows, tvos)
- How many people play at the same time? (small: up to 10; medium: 11 to 100; large: 101 to 1,000)
- The video service address (when there is video; may be left empty and set later)
- The ourapps.app store invitation link (when updates are offered; may be left empty and set later)

Answered with the default unless your description says otherwise (17):

- Which languages? (en, fr, de, es)
- Which look? (night: dark green felt and striped card backs; lounge: warm brown and plain card backs; for the whole application)
- How many players per table? (2 to 9; there are always two tables, so at most 18 play at once and anyone else watches)
- Starting chips? (5,000)
- How long is each blind level? (600 seconds)
- How many rebuys? (1, until level 3)
- Decision time? (30 seconds, then check or fold)
- Computer players? (none; on request; or fill empty seats, so one person can start alone; on request)
- Video and audio between players? (yes)
- Lessons for new players? (yes)
- Offer updates through ourapps.app? (no)
- Will builds be signed and published? (no)
- The web address, the bundle identifier and the server address
- The GitHub repository for the code, and whether GitHub Actions build releases

## What the answers choose

- Devices include or leave out the web, Apple, Android and Windows hosts.
- Lessons, video and updates each include or leave out their component. Computer players are in the design unless the answer is none; the answer sets their mode (on request or fill empty) and none leaves out computer-players and poker-strategy.
- The scale answer chooses, per job, the cheapest candidate whose declared load covers it: small and medium use Cloudflare's free tier and LiveKit's free plan; large uses the paid Cloudflare plan and LiveKit's Ship plan. Your own hardware is the other server choice; with it the scale changes only the video plan.
- Chips, level length, rebuys, decision time and player count set the settings of the components that own them and the matching numbers of the house rules file, with no code change.

## What it needs from you

- A Cloudflare account, or a machine of your own, for the server.
- An Apple developer membership for iPhone, iPad, Mac and Apple TV builds.
- A LiveKit Cloud account if video is on.
- A GitHub account: the code goes to a private repository of yours.
- Signing and deployment keys for the targets you publish, kept as the repository's secrets.

Secrets are given by reference only; no key is written into the recipe, the answers or the application.

## Components

39 components in five groups (delivery and hosts; rooms, people and sessions; turn-based game framework; poker; interface and presentation) plus the recipe's own application-specific component: screen flow, artwork, text in four languages, lessons and end-to-end tests. Thirty-five of the 39 have nothing to do with poker. The diagram names every component, grouped, with the connections of the default design; store-update is dashed because it is present only when updates is yes.

Each component sits in a slot named after it: the slot's class is what the recipe relies on (the interfaces it connects and the settings it writes), and the component named is the one the recipe prefers. Any catalogue component of the same class can take its place: `clod alternatives ourpoker-recipe@<version> <slot>` lists them and `clod design ... --substitute <slot>=<name>@<version>` uses one. `pkg:clod/com.clodhub/theme-high-contrast`, for example, fills the `theme` slot with high-contrast night and lounge looks.

## Building it

With clod and the published catalogue: `clod fetch ourpoker-recipe@0.13.0 --with-dependencies --store STORE`, then read the recipe's INSTRUCTIONS.md from the fetched archive:

```
python3 -c 'import json,sys,tarfile; s,v=sys.argv[1:]; d=next(e["digest"] for e in json.load(open(s+"/catalogue.json"))["entries"] if e["name"]=="pkg:clod/com.clodhub/ourpoker-recipe" and e["version"]==v); sys.stdout.write(tarfile.open(f"{s}/objects/{d}.tar").extractfile("INSTRUCTIONS.md").read().decode())' STORE 0.13.0 > INSTRUCTIONS.md
```

The steps, all set out in INSTRUCTIONS.md:

1. `clod fetch` (above), then get INSTRUCTIONS.md with the command above.
2. `clod questions`, and the questions in one round.
3. `clod design` with your answers.
4. `clod doctor` checks this machine's build tools for the devices you chose (`--install` installs the missing ones it can).
5. `clod resolve`, then the owner's policy, then `clod install`.
6. `clod verify APP --policy POLICY --trusted --allow-network` runs every package's checks on the installed application: the policy's `trustedExecution` lists the digests in `lock.json`, `--trusted` lets the checks run package code and `--allow-network` lets them download their dependencies.
7. Build and run on each device; a local server and the web client need no account.
8. When the server runs on Cloudflare: the two-step deploy. Deploy the server (`npm run deploy`, which handles a first deploy to a new worker name), build the web client against it and publish it as its own worker; then add both addresses to your answers, update the application in place, verify it again and deploy both again.

### Repository and releases

The installed application goes to your GitHub repository (the agent proposes `<your login>/ourpoker`, made private):

```
git init -b main && git add -A && git commit -m "OurPoker from ourpoker-recipe <version>"
gh repo create <owner>/<name> --private --source . --push
```

When builds are published (or the releases answer is yes), the installation also holds GitHub Actions: checks of the server, web, Android and Windows parts on every push, and a release workflow. `git tag v0.1.0 && git push --tags` builds the web client, the Android APK and the Windows installer and publishes a GitHub Release with `my-app.json`, the file ourapps.app reads to offer the app. Signing and deployment keys are repository secrets you set yourself with `gh secret set`, named from your reference answers (INSTRUCTIONS.md lists every name); without them the Android build is signed with a temporary key, the Windows installer is unsigned and the web client is released as `web.zip`. Registering the app on ourapps.app is optional.

## Tested answer sets

The default answers, `book-club`, `poker-league`, `company-event`, `company-event-hosted`, `tv-only`, `browser-only-no-extras`, `large-paid-host`, `clinic`, `no-computers`, `web-own-hardware`, `native-no-lessons`, `local-web`, `fill-empty-own-hardware`, `lounge-web-ios` and `windows-only`; every combination of devices, video, lessons, updates, publishing, computer players, server and scale is checked to give a complete design.

## Status

Version 0.13.0. Installed with `clod install` from signed packages and built and run with the recipe's own install proof (`default` and `local-web` answers):

- Server on Node; the web client in a browser: a player sits, a computer player joins and a hand is played to its settlement with every chip counted.
- iPhone and iPad, Mac (Mac Catalyst) and Apple TV apps built for their simulators and Mac; the Android app built, unit-tested and played on the emulator to a settled hand; the desktop web build for Windows.
- Substitution: the `theme` slot filled with `pkg:clod/com.clodhub/theme-high-contrast`.
- Windows 11 in PowerShell, from a local store: `clod doctor` (Node 26 found), `clod install`, the server's type check, tests and start, the web client's type check and build, and the desktop tests and build. The installer is not built there: that machine's Smart App Control refuses the unsigned uninstaller step of packaging.
- An in-place update of an installed `local-web` application (33 components; serverAddress and webAddress changed): `clod propose-update --trusted --allow-network` staged it and ran every package's checks, then `clod approve` with the owner key, `clod apply` and `clod recover`. A tree that still holds `node_modules` is refused for its links; INSTRUCTIONS.md says which folders to remove first.
- The Android app built and unit-tested on Windows 11 with strict Gradle dependency verification.
- The GitHub workflows pass actionlint; the Android room-list check and the browser check they run were run on a Mac against a local server.

Not run: Cloudflare deployment; the Windows installer built on Windows (Smart App Control on that machine refuses packaging's unsigned uninstaller step; GitHub's Windows runner builds it) and run there; GitHub workflows and releases on GitHub; signed Android, Windows and Apple builds; App Store, TestFlight and store publishing; video with a real LiveKit account and keys. The open items are in `INTEGRATION-GAPS.md`.
