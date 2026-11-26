"""try_install.py's build-output removal and emulator port choice, on ordinary temporary folders.

Run: PYTHONPATH=<clod checkout> python3.12 -B authoring/try_install_test.py
"""
import json
import os
import signal
import socket
import subprocess
import sys
import time
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import try_install  # noqa: E402


def group_running(pgid):
    """A process group with a member that has not exited."""
    return bool(try_install.group_members(pgid))


def make(path, size=4096):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


class BuildOutputs(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.work = Path(self.temporary.name).resolve()
        self.design = self.work / "designs" / "default"
        app = self.design / "app"
        (app / ".clod").mkdir(parents=True)
        self.kept = [app / ".clod/definition.json", app / "server/src/index.ts", app / "ios/OurPoker.xcodeproj/project.pbxproj",
                     self.design / "browser.png", self.design / "answers.json", self.work / "logs/default-install.log", self.work / "report.json"]
        self.removed = [app / "server/node_modules/vitest/index.js", app / "web/node_modules/vite/index.js",
                        app / "components/theme/web/node_modules/x/index.js", app / "ios/build/DerivedData/Build/Products/a.app/a",
                        app / "android/app/build/outputs/apk/debug/app-debug.apk", app / "android/.gradle/cache.bin",
                        app / "desktop/artifacts/win-unpacked/OurPoker.exe", self.design / "chrome-profile/Default/Cookies",
                        self.design / "windows-unpacked.tgz"]
        for path in self.kept + self.removed:
            make(path)

    def tearDown(self):
        self.temporary.cleanup()

    def test_removes_build_outputs_and_keeps_the_proof(self):
        _, result = try_install.remove_build_outputs(self.work, self.design, {})
        for path in self.removed:
            self.assertFalse(path.exists(), path)
        for path in self.kept:
            self.assertTrue(path.exists(), path)
        self.assertGreater(result["bytesBefore"], result["bytesAfter"])
        self.assertEqual(result["bytesAfter"], try_install.disk_bytes(self.design))
        self.assertIn("app/server/node_modules", result["removed"])
        self.assertIn("app/ios/build", result["removed"])

    def test_links_are_not_followed(self):
        outside = self.work / "outside"
        make(outside / "precious.txt")
        (self.design / "app/web/node_modules/linked").symlink_to(outside, target_is_directory=True)
        (self.design / "chrome-profile").rename(self.work / "profile-elsewhere")
        (self.design / "chrome-profile").symlink_to(self.work / "profile-elsewhere", target_is_directory=True)
        try_install.remove_build_outputs(self.work, self.design, {})
        self.assertTrue((outside / "precious.txt").exists())
        self.assertTrue((self.work / "profile-elsewhere/Default/Cookies").exists())

    def test_refuses_a_folder_outside_the_designs_folder(self):
        with self.assertRaises(try_install.Step):
            try_install.remove_build_outputs(self.work, self.work / "logs", {})

    def test_disk_bytes_counts_without_following_links(self):
        before = try_install.disk_bytes(self.design)
        make(self.work / "big", 1024 * 1024)
        (self.design / "big-link").symlink_to(self.work / "big")
        self.assertLess(try_install.disk_bytes(self.design) - before, 1024 * 1024)


class Evidence(BuildOutputs):
    """Every path the report names resolves after removal, with the same bytes."""

    def test_named_files_inside_outputs_are_copied_and_the_report_names_the_copies(self):
        app = self.design / "app"
        apk, binary = app / "android/app/build/outputs/apk/debug/app-debug.apk", app / "ios/build/DerivedData/Build/Products/a.app/a"
        digests = {path: try_install.file_digest(path) for path in (apk, binary)}
        report = {"designs": {"default": {"android": [f"apk {apk}, built"], "apple": f"built {binary}", "browser": f"shot {self.design / 'browser.png'}"}}}
        changed, storage = try_install.remove_build_outputs(self.work, self.design, report)
        self.assertEqual(try_install.missing_paths(changed, self.work), [])
        for path in try_install.named_paths(changed, self.work):
            self.assertTrue(Path(path).is_file(), path)
        copies = {self.design / "evidence" / path.relative_to(self.design): path for path in (apk, binary)}
        for copy, original in copies.items():
            self.assertEqual(try_install.file_digest(copy), digests[original])
            self.assertIn(str(copy), json.dumps(changed))
            self.assertNotIn(str(original) + ",", json.dumps(changed))
        self.assertFalse(apk.exists())
        self.assertFalse((app / "ios/build").exists())
        self.assertEqual(set(storage["evidenceCopies"]), {str(path.relative_to(self.design)) for path in (apk, binary)})

    def test_a_rewrite_changes_whole_paths_only(self):
        moves = {"/w/designs/d/app/x.apk": "/w/designs/d/evidence/app/x.apk"}
        text = "apk /w/designs/d/app/x.apk, and /w/designs/d/app/x.apk.idsig and /w/designs/d/app/x.apk."
        self.assertEqual(try_install.renamed({"a": [text]}, moves),
                         {"a": ["apk /w/designs/d/evidence/app/x.apk, and /w/designs/d/app/x.apk.idsig and /w/designs/d/evidence/app/x.apk."]})
        self.assertEqual(try_install.named_paths({"a": "see /w/designs/d/app/x.apk."}, Path("/w")), {"/w/designs/d/app/x.apk"})

    def test_an_output_holding_a_named_folder_is_kept_whole(self):
        bundle = self.design / "app/ios/build/DerivedData/Build/Products/a.app"
        report = {"designs": {"default": {"apple": f"bundle {bundle}"}}}
        changed, storage = try_install.remove_build_outputs(self.work, self.design, report)
        self.assertTrue(bundle.is_dir())
        self.assertEqual(list(storage["kept"]), ["app/ios/build"])
        self.assertFalse((self.design / "app/server/node_modules").exists())
        self.assertEqual(try_install.missing_paths(changed, self.work), [])

    def resolves(self, report):
        """Every path the report names inside the design folder exists."""
        for name in try_install.named_paths(report, self.work):
            if try_install.location(name).is_relative_to(self.design):
                self.assertTrue(os.path.lexists(name), name)

    def test_a_path_already_missing_is_listed_and_changes_nothing_else(self):
        gone = self.design / "app/ios/build/gone.app/gone"
        shot = self.design / "browser.png"
        report = {"designs": {"default": {"apple": f"failed: {gone}:12:5: error", "browser": f"shot {shot}"},
                              "other": {"error": f"{self.work}/designs/other/app/missing.txt not found"}}}
        changed, storage = try_install.remove_build_outputs(self.work, self.design, report)
        self.assertEqual(storage["alreadyMissing"], ["app/ios/build/gone.app/gone"])
        self.assertIn("app/ios/build", storage["kept"])  # the output it would be in stays
        self.assertFalse((self.design / "app/server/node_modules").exists())
        self.assertIn(str(shot), json.dumps(changed))
        self.assertTrue(shot.exists())

    def test_a_named_file_whose_name_holds_a_space_keeps_its_output(self):
        spaced = self.design / "app/ios/build/DerivedData/Logs/Build Log.txt"
        make(spaced)
        changed, storage = try_install.remove_build_outputs(self.work, self.design, {"designs": {"default": {"log": f"see {spaced}"}}})
        self.assertTrue(spaced.exists())
        self.assertIn("app/ios/build", storage["kept"])

    def test_a_file_named_as_the_start_of_a_longer_name_keeps_the_output(self):
        folder = self.design / "app/ios/build/DerivedData/Logs"
        for ending in (" File.txt", ",File.txt", ";x", ")x", ":x", "'x", '"x', ".", ". File", "\tx"):
            with self.subTest(ending=ending):
                short, longer = folder / "My", folder / ("My" + ending)
                make(short, 10)
                make(longer, 20)
                changed, storage = try_install.remove_build_outputs(self.work, self.design, {"designs": {"default": {"log": f"see {longer}"}}})
                self.assertTrue(longer.exists())
                self.assertTrue(short.exists())
                self.assertIn("app/ios/build", storage["kept"])
                self.assertEqual(storage["evidenceCopies"], {})
                self.assertEqual(changed["designs"]["default"]["log"], f"see {longer}")
                longer.unlink()

    def test_a_sibling_that_only_shares_a_prefix_does_not_keep_the_output(self):
        apk = self.design / "app/android/app/build/outputs/apk/debug/app-debug.apk"
        make(apk.with_name("app-debug.apk.idsig"))
        changed, storage = try_install.remove_build_outputs(self.work, self.design, {"designs": {"default": {"apk": f"apk {apk}"}}})
        self.assertIn("app/android/app/build/outputs/apk/debug/app-debug.apk", storage["evidenceCopies"])

    def test_the_var_spelling_of_the_folder_is_matched(self):
        if not str(self.work).startswith("/private/var/"):
            self.skipTest("the work folder is not under /private/var")
        apk = self.design / "app/android/app/build/outputs/apk/debug/app-debug.apk"
        written = str(apk)[len("/private"):]
        changed, storage = try_install.remove_build_outputs(self.work, self.design, {"designs": {"default": {"apk": f"apk {written}"}}})
        self.assertIn("app/android/app/build/outputs/apk/debug/app-debug.apk", storage["evidenceCopies"])
        self.resolves(changed)

    def test_a_named_link_keeps_its_output(self):
        link = self.design / "app/server/node_modules/linked"
        link.symlink_to(self.design / "browser.png")
        changed, storage = try_install.remove_build_outputs(self.work, self.design, {"designs": {"default": {"link": f"see {link}"}}})
        self.assertTrue(link.is_symlink())
        self.assertIn("app/server/node_modules", storage["kept"])
        self.resolves(changed)

    def test_a_signed_document_is_not_rewritten_and_keeps_its_output(self):
        apk = self.design / "app/android/app/build/outputs/apk/debug/app-debug.apk"
        envelope = {"payloadType": "application/vnd.in-toto+json", "payload": f"subject {apk}", "signatures": [{"sig": "x"}]}
        report = {"designs": {"default": {"attestation": envelope}}}
        changed, storage = try_install.remove_build_outputs(self.work, self.design, report)
        self.assertEqual(changed["designs"]["default"]["attestation"], envelope)
        self.assertTrue(apk.exists())
        self.assertIn("app/android/app/build", storage["kept"])
        self.resolves(changed)

    def test_a_copy_that_would_replace_a_different_file_keeps_the_output(self):
        apk = self.design / "app/android/app/build/outputs/apk/debug/app-debug.apk"
        clash = self.design / "evidence/app/android/app/build/outputs/apk/debug/app-debug.apk"
        make(clash, 100)
        changed, storage = try_install.remove_build_outputs(self.work, self.design, {"designs": {"default": {"apk": f"apk {apk}"}}})
        self.assertTrue(apk.exists())
        self.assertEqual(clash.stat().st_size, 100)
        self.assertIn("app/android/app/build", storage["kept"])
        self.assertIn(str(apk), json.dumps(changed))
        self.resolves(changed)

    def test_a_failed_copy_leaves_no_partial_file_and_keeps_the_output(self):
        apk = self.design / "app/android/app/build/outputs/apk/debug/app-debug.apk"
        def full(source, target):
            target.write(b"part")
            raise OSError(28, "No space left on device")
        with mock.patch.object(try_install.shutil, "copyfileobj", side_effect=full):
            changed, storage = try_install.remove_build_outputs(self.work, self.design, {"designs": {"default": {"apk": f"apk {apk}"}}})
        self.assertTrue(apk.exists())
        self.assertFalse((self.design / "evidence/app/android/app/build/outputs/apk/debug/app-debug.apk").exists())
        self.assertIn("app/android/app/build", storage["kept"])
        self.assertFalse((self.design / "app/ios/build").exists())
        self.resolves(changed)


class AdmissionAndLocks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.state = mock.patch.dict(os.environ, {"CLOD_STATE_HOME": str(Path(self.temporary.name) / "state")})
        self.state.start()

    def tearDown(self):
        self.state.stop()
        self.temporary.cleanup()

    def test_design_bytes_follow_the_targets(self):
        options = mock.Mock(windows=None, cloudflare=None, github=None)
        web = try_install.design_bytes({"answers": {"targets": ["web"]}}, options)
        every = try_install.design_bytes({"answers": {"targets": ["web", "ios", "android", "macos", "windows", "tvos"]}}, options)
        self.assertEqual(web, try_install.DESIGN_BASE)
        self.assertEqual(every, try_install.DESIGN_BASE + try_install.DESIGN_APPLE + try_install.DESIGN_ANDROID)
        options.windows, options.github = "host", "owner/name"
        self.assertEqual(try_install.design_bytes({"answers": {"targets": ["windows"]}}, options),
                         try_install.DESIGN_BASE + try_install.DESIGN_WINDOWS + try_install.DESIGN_SECOND_INSTALL)

    def test_a_locked_step_holds_the_machine_lock(self):
        work = Path(self.temporary.name) / "work"
        script = "import json, sys; from clod import locks; print(json.dumps([h['kind'] for h in locks.holders() if h['held']]))"
        output = try_install.run([sys.executable, "-B", "-c", script], work, "probe", env={**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH", "")}, lock="xcode")
        self.assertIn('"xcode"', output)
        self.assertIn("probe", try_install.LOCK_WAITS)
        output = try_install.run([sys.executable, "-B", "-c", script], work, "probe-free", env={**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH", "")})
        self.assertNotIn('"xcode"', output)

    def test_too_little_space_refuses_with_the_numbers(self):
        with mock.patch("clod.space.free_bytes", return_value=5 * try_install.GIB):
            with self.assertRaises(try_install.ClodError) as raised:
                with try_install.space.reserve(Path(self.temporary.name), try_install.DESIGN_BASE, purpose="try_install design probe"):
                    pass
        self.assertEqual(raised.exception.code, "insufficient-space")
        detail = raised.exception.document()["detail"]
        self.assertEqual((detail["required"], detail["free"]), (try_install.DESIGN_BASE, 5 * try_install.GIB))


class WorkFolderWithSpaces(unittest.TestCase):
    """A --work folder whose path holds spaces and punctuation: named files inside outputs are still copied and resolve."""

    def test_named_files_are_protected(self):
        with tempfile.TemporaryDirectory() as folder:
            work = (Path(folder) / "my proofs, run (1): ok").resolve()
            design = work / "designs" / "default"
            (design / "app/.clod").mkdir(parents=True)
            apk = design / "app/android/app/build/outputs/apk/debug/app-debug.apk"
            make(apk)
            make(design / "app/server/node_modules/x/index.js")
            report = {"designs": {"default": {"apk": f"apk {apk}, built.", "list": [str(apk)]}}}
            changed, storage = try_install.remove_build_outputs(work, design, report)
            copy = design / "evidence/app/android/app/build/outputs/apk/debug/app-debug.apk"
            self.assertEqual(changed["designs"]["default"], {"apk": f"apk {copy}, built.", "list": [str(copy)]})
            # a file address of a name inside an output, percent-encoded: found, does not exist as written, so its output stays
            source = design / "app/ios/build/a.kt"
            make(source)
            node = "file://" + str(source).replace(" ", "%20")  # how Node pathToFileURL, Java File.toURI and Swift URL write it
            every = "file://" + urllib.parse.quote(str(source))
            for address in (node, every):
                _, storage = try_install.remove_build_outputs(work, design, {"designs": {"default": {"error": f"e: {address}:3:1"}}})
                self.assertIn("app/ios/build", storage["kept"], address)
                self.assertTrue(source.exists())
            self.assertTrue(copy.is_file())
            self.assertFalse(apk.exists())
            self.assertFalse((design / "app/server/node_modules").exists())


class AnswersNamesFirst(unittest.TestCase):
    def test_a_bad_answers_name_stops_the_run_before_the_store(self):
        with tempfile.TemporaryDirectory() as folder:
            spaced = Path(folder) / "my answers.json"
            spaced.write_text("{}")
            world = mock.Mock(recipe={"tests": {"defaultAnswers": {}, "answerSets": []}})
            with mock.patch.object(try_install.recipe_world, "world", return_value=world), \
                    mock.patch.object(try_install, "prepare_store", side_effect=AssertionError("the store was built")):
                self.assertEqual(try_install.main([str(spaced), "--work", str(Path(folder) / "work")]), 2)


class AnswersNames(unittest.TestCase):
    def test_an_answers_file_name_with_a_space_is_refused(self):
        world = mock.Mock(recipe={"tests": {"defaultAnswers": {}, "answerSets": []}})
        with tempfile.TemporaryDirectory() as folder:
            spaced, plain = Path(folder) / "my answers.json", Path(folder) / "my-answers.json"
            spaced.write_text("{}")
            plain.write_text("{}")
            with self.assertRaises(try_install.Step):
                try_install.answers_for(world, str(spaced))
            self.assertEqual(try_install.answers_for(world, str(plain)), ("my-answers", {}))


class EmulatorLock(unittest.TestCase):
    def test_an_emulator_left_running_keeps_the_lock_until_the_run_ends(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {"CLOD_STATE_HOME": folder}):
            try_install.GROUPS_LEFT.clear()
            left = lambda *args: try_install.GROUPS_LEFT.append({"pgid": 1, "command": "emulator", "reason": "not stopped"})  # noqa: E731
            with mock.patch.object(try_install, "emulator_run", side_effect=left):
                try_install.android_run(Path(folder), "d", "app.apk", "p", 1, "avd")
            held = [h["kind"] for h in try_install.locks.holders() if h["held"]]
            try_install.HELD.close()
            try_install.GROUPS_LEFT.clear()
            self.assertEqual(held, ["android-emulator"])


class EmulatorPort(unittest.TestCase):
    def test_skips_used_ports_and_listed_devices(self):
        with socket.socket() as taken:
            taken.bind(("127.0.0.1", 0))
            busy = taken.getsockname()[1]
            real = try_install.port_free
            with mock.patch.object(try_install, "run", return_value="List of devices attached\nemulator-5554\tdevice\n"), \
                    mock.patch.object(try_install, "port_free", side_effect=lambda port: port not in (5556, 5559) and real(port)):
                port = try_install.emulator_port("adb", Path(tempfile.gettempdir()))
            self.assertFalse(try_install.port_free(busy))
        self.assertEqual(port % 2, 0)
        self.assertNotIn(port, (5554, 5556, 5558))
        self.assertTrue(5554 <= port <= 5682)

    def test_no_free_port_is_a_step_failure(self):
        with mock.patch.object(try_install, "run", return_value=""), mock.patch.object(try_install, "port_free", return_value=False):
            with self.assertRaises(try_install.Step):
                try_install.emulator_port("adb", Path(tempfile.gettempdir()))


SLEEPER = "import time; time.sleep(60)"


class Holders(unittest.TestCase):
    """Processes that use the run's folder are reported and keep it; none is stopped."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name).resolve()
        self.work, self.elsewhere = base / "work", base / "elsewhere"
        self.work.mkdir()
        self.elsewhere.mkdir()
        try_install.GROUPS_LEFT.clear()

    def tearDown(self):
        self.temporary.cleanup()

    def start(self, cwd, code=SLEEPER):
        process = subprocess.Popen([sys.executable, "-c", code], cwd=cwd, start_new_session=True)
        self.addCleanup(lambda: (process.poll() is None and process.kill(), process.wait()))
        return process

    def wait_for_holders(self, pids):
        deadline = time.time() + 10
        while time.time() < deadline and set(pids) - set(try_install.holders(self.work)):
            time.sleep(0.2)
        return try_install.holders(self.work)

    def test_a_process_using_two_runs_folders_is_reported_and_left_running(self):
        (self.elsewhere / "shared.lock").write_text("")
        # a shared daemon: its working folder is another run's, and it holds a file of this run
        shared = self.start(self.elsewhere, f"import time; handle = open({str(self.work / 'cache.bin')!r}, 'w'); time.sleep(60)")
        inside = self.start(self.work)
        outside = self.start(self.elsewhere)
        found = self.wait_for_holders([shared.pid, inside.pid])
        self.assertIn(shared.pid, found)
        self.assertIn(inside.pid, found)
        self.assertNotIn(outside.pid, found)
        left = try_install.blockers(self.work)
        self.assertIn(str(shared.pid), left)
        for process in (shared, inside, outside):
            self.assertIsNone(process.poll())

    def test_a_failed_inspection_keeps_the_folder(self):
        failing = subprocess.CompletedProcess([], 1, "", "lsof: no access")
        with mock.patch.object(try_install.sys, "platform", "darwin"), mock.patch.object(try_install.subprocess, "run", return_value=failing):
            self.assertEqual(list(try_install.blockers(self.work)), ["inspection"])


class LaunchedGroups(unittest.TestCase):
    """Only groups this run launched, with every member verified as its own, are stopped."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.log = Path(self.temporary.name) / "log"
        try_install.GROUPS_LEFT.clear()

    def tearDown(self):
        self.temporary.cleanup()
        try_install.GROUPS_LEFT.clear()

    def start(self, argv):
        processes = try_install.Processes()
        leader = processes.start(argv, self.temporary.name, os.environ.copy(), self.log)
        self.addCleanup(lambda: (group_running(leader.pid) and os.killpg(leader.pid, signal.SIGKILL)))
        time.sleep(0.5)
        return processes, leader

    def test_a_term_ignoring_member_is_killed(self):
        processes, leader = self.start([sys.executable, "-c", "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"])
        processes.stop()
        self.assertFalse(group_running(leader.pid))
        self.assertEqual(try_install.GROUPS_LEFT, [])

    def test_children_left_by_an_exited_leader_are_stopped(self):
        processes, leader = self.start(["/bin/sh", "-c", "sleep 60 & exit 0"])
        leader.wait(10)
        self.assertTrue(group_running(leader.pid))
        processes.stop()
        self.assertFalse(group_running(leader.pid))
        self.assertEqual(try_install.GROUPS_LEFT, [])

    def test_a_member_of_another_session_stops_nothing(self):
        processes, leader = self.start([sys.executable, "-c", SLEEPER])
        real = os.getsid
        with mock.patch.object(try_install.os, "getsid", side_effect=lambda pid: 1 if pid == leader.pid else real(pid)):
            processes.stop()
        self.assertTrue(group_running(leader.pid))
        self.assertIn("belongs to session 1", try_install.GROUPS_LEFT[0]["reason"])

    def test_a_reused_pid_is_not_signalled(self):
        processes, leader = self.start([sys.executable, "-c", SLEEPER])
        with mock.patch("clod.state.process_start", return_value="darwin:1.0"):
            processes.stop()
        self.assertTrue(group_running(leader.pid))
        self.assertIn("reused", try_install.GROUPS_LEFT[0]["reason"])

    def test_an_unreadable_process_list_stops_nothing(self):
        processes, leader = self.start([sys.executable, "-c", SLEEPER])
        with mock.patch.object(try_install, "group_members", side_effect=try_install.InspectionFailed("ps exited 1")):
            processes.stop()
        self.assertTrue(group_running(leader.pid))
        self.assertIn("ps exited 1", try_install.GROUPS_LEFT[0]["reason"])
        self.assertIn(f"group {leader.pid}", try_install.blockers(Path(self.temporary.name)))

    def test_a_leader_that_already_exited_is_not_an_error(self):
        processes, leader = self.start(["/bin/sh", "-c", "exit 0"])
        time.sleep(0.5)
        processes.stop()
        self.assertEqual(try_install.GROUPS_LEFT, [])

    def test_a_timed_out_command_whose_descendant_holds_its_output_returns(self):
        work = Path(self.temporary.name)
        marker = work / "holder.pid"
        hold = f"import os, time; os.setsid(); open({str(marker)!r}, 'w').write(str(os.getpid())); time.sleep(120)"
        code = f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', {hold!r}]); time.sleep(120)"
        started = time.time()
        with self.assertRaises(subprocess.TimeoutExpired):
            try_install.run([sys.executable, "-c", code], work, "times-out", timeout=2)
        self.assertLess(time.time() - started, 60)
        holder = int(marker.read_text())
        self.addCleanup(lambda: subprocess.run(["kill", "-9", str(holder)], capture_output=True))

    def test_run_stops_what_a_command_leaves_in_its_session_and_not_a_detached_process(self):
        work = Path(self.temporary.name)
        marker = work / "detached.pid"
        detach = f"import os, time; os.setsid(); open({str(marker)!r}, 'w').write(str(os.getpid())); time.sleep(60)"
        # the command waits until its detached child has left the session, then exits leaving both children running
        code = (f"import os, subprocess, sys, time; quiet = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
                f"kept = subprocess.Popen(['sleep', '60'], **quiet); open({str(work / 'kept.pid')!r}, 'w').write(str(kept.pid))\n"
                f"subprocess.Popen([sys.executable, '-c', {detach!r}], **quiet)\n"
                f"while not os.path.exists({str(marker)!r}): time.sleep(0.05)\ntime.sleep(0.3)")
        try_install.run([sys.executable, "-c", code], work, "leaves-children", cwd=work)
        detached = int(marker.read_text())
        self.addCleanup(lambda: os.kill(detached, signal.SIGKILL))
        os.kill(detached, 0)  # still running: it left the command's session, so the run cannot prove it is its own
        self.assertIn(str(detached), try_install.blockers(work))  # its working folder is the run's, so nothing is removed
        self.assertEqual(try_install.GROUPS_LEFT, [])
        left = int((work / "kept.pid").read_text())
        deadline = time.time() + 10
        while time.time() < deadline and subprocess.run(["ps", "-o", "stat=", "-p", str(left)], capture_output=True, text=True).stdout.strip()[:1] not in ("", "Z"):
            time.sleep(0.2)
        self.assertIn(subprocess.run(["ps", "-o", "stat=", "-p", str(left)], capture_output=True, text=True).stdout.strip()[:1], ("", "Z"))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    unittest.main()
