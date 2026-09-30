import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import collect_ncr_gfs as gfs


SPEC = gfs.forecast_spec("2026-09-30", 12, 3)
GRIB = b"GRIB" + b"\0\0\0\x02" + (20).to_bytes(8, "big") + b"7777"


def inventory():
    lines = [f"{i + 1}:{20 * i}:d=2026093012:{var}:{level}:3 hour fcst:"
             for i, (var, level) in enumerate(gfs.SELECT)]
    lines.append("8:140:d=2026093012:OTHER:surface:3 hour fcst:")
    return ("\n".join(lines) + "\n").encode()


def csv_payload():
    output = io.StringIO()
    writer = csv.writer(output)
    for variable, level in gfs.SELECT:
        for x in range(8):
            for y in range(7):
                writer.writerow(["2026-09-30 12:00:00", "2026-09-30 15:00:00", variable,
                                 level, 76.5 + x * 0.25, 28 + y * 0.25, 1.2])
    return output.getvalue().encode()


def fake_fetch(url, limit, byte_range=None):
    return (inventory() if url.endswith(".idx") else GRIB), {"Last-Modified": "archive metadata"}


def fake_decode(binary, folder, spec):
    (folder / "ncr.grib2").write_bytes(GRIB * len(gfs.SELECT))
    (folder / "ncr.csv").write_bytes(csv_payload())


class GfsScientificBoundaryTests(unittest.TestCase):
    def test_forecast_rollover_keeps_initialization_separate_from_valid_time(self):
        spec = gfs.forecast_spec("2026-09-30", 18, 12)
        self.assertEqual(spec["model_reference_time_utc"], "2026-09-30T18:00:00Z")
        self.assertEqual(spec["valid_time_utc"], "2026-10-01T06:00:00Z")
        self.assertTrue(spec["source_url"].endswith("gfs.t18z.pgrb2.0p25.f012"))
        for date, cycle, lead in [("2026-9-30", 12, 3), ("2026-09-30", 3, 3),
                                  ("2026-09-30", 12, -1), ("2026-09-30", 12, 121)]:
            with self.subTest(date=date, cycle=cycle, lead=lead), self.assertRaises(ValueError):
                gfs.forecast_spec(date, cycle, lead)

    def test_inventory_rejects_wrong_cycle_lead_ambiguity_and_unbounded_field(self):
        self.assertEqual(len(gfs.select_ranges(inventory(), SPEC)), 7)
        bad = [inventory().replace(b"d=2026093012", b"d=2026093006"),
               inventory().replace(b"3 hour fcst", b"6 hour fcst"),
               inventory().replace(b"OTHER:surface", b"CAPE:surface"),
               b"\n".join(inventory().splitlines()[:-1]),
               inventory().replace(b"2:20:", b"2:0:")]
        for payload in bad:
            with self.subTest(payload=payload[:50]), self.assertRaises(ValueError):
                gfs.select_ranges(payload, SPEC)

    def test_csv_enforces_field_time_coverage_and_unique_cells(self):
        payload = csv_payload()
        self.assertEqual(len(gfs.validate_csv(payload, SPEC)), 392)
        rows = payload.splitlines()
        altered = [payload.replace(b"15:00:00", b"16:00:00"),
                   payload.replace(b",1.2", b",nan"),
                   payload.replace(b",1.2", b",9.999e20"),
                   payload.replace(b",76.5,", b",75.5,"),
                   payload.replace(b",76.5,", b",76.51,"),
                   b"\n".join([rows[0], rows[0], *rows[2:]])]
        for bad in altered:
            with self.subTest(payload=bad[:100]), self.assertRaises(ValueError):
                gfs.validate_csv(bad, SPEC)


class GfsCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "snapshots"
        self.snapshot = self.output / SPEC["snapshot_id"]

    def collect(self, **kwargs):
        return gfs.collect("2026-09-30", 12, 3, self.output, **kwargs)

    @patch.object(gfs, "decoder_path", return_value="existing-wgrib2")
    @patch.object(gfs, "decode", side_effect=fake_decode)
    @patch.object(gfs, "fetch", side_effect=fake_fetch)
    def test_repeat_and_verify_only_reuse_immutable_context_snapshot(self, fetch, decode, decoder):
        manifest = self.collect()
        before = {p.name: p.read_bytes() for p in self.snapshot.iterdir()}
        self.assertEqual(manifest["data_role"], "nwp_context")
        self.assertFalse(manifest["is_observation_or_label"])
        self.assertIsNone(manifest["historical_available_at_utc"])
        self.assertEqual(manifest["forecast"], SPEC)
        self.assertTrue(manifest["retrieved_at_utc"].endswith("Z"))
        self.assertFalse((self.snapshot / "selected_global.grib2").exists())
        self.assertEqual(fetch.call_count, 8)
        self.assertEqual(self.collect(), manifest)
        self.assertEqual(self.collect(verify_only=True), manifest)
        self.assertEqual(fetch.call_count, 8)
        self.assertEqual(decode.call_count, 1)
        self.assertEqual(decoder.call_count, 1)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.snapshot.iterdir()})
        (self.snapshot / "ncr.csv").write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "Checksum"):
            self.collect()
        self.assertEqual(fetch.call_count, 8)

    @patch.object(gfs, "decoder_path")
    @patch.object(gfs, "fetch")
    def test_verify_only_missing_snapshot_never_downloads_or_creates_directories(self, fetch, decoder):
        with self.assertRaises(FileNotFoundError):
            self.collect(verify_only=True)
        self.assertFalse(self.output.exists())
        fetch.assert_not_called()
        decoder.assert_not_called()

    @patch.object(gfs, "decoder_path", return_value="existing-wgrib2")
    @patch.object(gfs, "decode", side_effect=RuntimeError("decoder failed"))
    @patch.object(gfs, "fetch", side_effect=fake_fetch)
    def test_failed_decode_does_not_publish_and_can_retry(self, fetch, decode, decoder):
        with self.assertRaisesRegex(RuntimeError, "decoder failed"):
            self.collect()
        self.assertFalse(self.snapshot.exists())
        self.assertEqual(list(self.output.iterdir()), [])
        decode.side_effect = fake_decode
        self.assertEqual(self.collect()["csv_rows"], 392)

    @patch.object(gfs, "decoder_path", return_value="existing-wgrib2")
    @patch.object(gfs, "decode", side_effect=fake_decode)
    @patch.object(gfs, "fetch", side_effect=fake_fetch)
    def test_manifest_role_or_path_tampering_rejected(self, fetch, decode, decoder):
        original = self.collect()
        manifest_path = self.snapshot / "manifest.json"
        altered = dict(original, data_role="rain_label")
        manifest_path.write_text(json.dumps(altered), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "manifest checksum"):
            self.collect(verify_only=True)
        original["files"][0]["path"] = "../provider.idx"
        manifest_path.write_text(json.dumps(original), encoding="utf-8")
        (self.snapshot / "manifest.sha256").write_text(gfs.sha(manifest_path.read_bytes()) + "\n")
        with self.assertRaisesRegex(ValueError, "files"):
            self.collect(verify_only=True)

    @patch.object(gfs, "decoder_path", return_value="existing-wgrib2")
    @patch.object(gfs, "decode", side_effect=fake_decode)
    @patch.object(gfs, "fetch", side_effect=fake_fetch)
    def test_manifest_time_mutation_fails_before_availability_can_be_used(self, fetch, decode, decoder):
        manifest = self.collect()
        manifest["retrieved_at_utc"] = "2020-01-01T00:00:00Z"
        (self.snapshot / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "manifest checksum"):
            gfs.read_latest(self.output)

    @patch.object(gfs, "decoder_path", return_value="existing-wgrib2")
    @patch.object(gfs, "decode", side_effect=fake_decode)
    @patch.object(gfs, "fetch", side_effect=fake_fetch)
    def test_latest_uses_directory_identity_and_ignores_staging(self, fetch, decode, decoder):
        self.assertIsNone(gfs.read_latest(self.output))
        manifest = self.collect()
        stage = self.output / ".gfs-stage-unfinished"
        stage.mkdir()
        (stage / "manifest.json").write_text("broken")
        self.assertEqual(gfs.read_latest(self.output), manifest)
        # A more recently initialized snapshot takes precedence over a longer
        # forecast lead from an older run, regardless of filesystem write time.
        older = self.output / "gfs_20260929_18_f120_ncr"
        older.mkdir()
        (older / "manifest.json").write_text("broken")
        self.assertEqual(gfs.read_latest(self.output), manifest)
        newer_lead = self.output / "gfs_20260930_12_f006_ncr"
        newer_lead.mkdir()
        with self.assertRaises(FileNotFoundError):
            gfs.read_latest(self.output)

    def test_import_and_empty_latest_do_not_require_optional_requests(self):
        code = (
            "import sys; sys.modules['requests']=None; "
            "from scripts.collect_ncr_gfs import read_latest; "
            f"assert read_latest({str(self.output)!r}) is None"
        )
        subprocess.run([sys.executable, "-c", code], cwd=gfs.ROOT, check=True,
                       capture_output=True, text=True, timeout=15)


if __name__ == "__main__":
    unittest.main()
