import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import download_imerg as script

ROW = {"granule_id": "G123-GES_DISC", "interval_start_utc": "2026-09-29T00:00:00Z",
       "interval_end_utc": "2026-09-29T00:29:59.999Z", "links": [
           {"href": "https://data.gesdisc.earthdata.nasa.gov/data/sample.HDF5", "rel": "http://esipfed.org/ns/fedsearch/1.1/data#"}]}


def session(body):
    response = Mock(status_code=200)
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.iter_content.return_value = [body]
    return Mock(get=Mock(return_value=response))


class ImergDownloadTests(unittest.TestCase):
    def test_missing_local_credentials_do_not_trigger_interactive_login(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, "Configure local"):
            script.authenticated_session()

    def test_html_and_oversize_responses_do_not_publish_scientific_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for body in (b"<html>Login</html>", b"\x89HDF\r\n\x1a\n" + b"x" * 40):
                with patch.object(script, "LIMIT", 32), self.assertRaises(ValueError):
                    script.download(ROW, root, lambda: session(body))
                self.assertEqual(list(root.iterdir()), [])

    def test_retry_reuses_verified_container_without_implying_decoded_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fake = session(b"\x89HDF\r\n\x1a\n" + b"fixture only, not a scientific dataset")
            first = script.download(ROW, root, lambda: fake)
            second = script.download(ROW, root, Mock(side_effect=AssertionError("Must reuse")))
            self.assertEqual(first, second)
            self.assertFalse(first["label_eligible"])
            self.assertFalse(first["quality_screened"])
            fake.close.assert_called_once()
            (root / ROW["granule_id"] / "precipitation.HDF5").write_bytes(b"broken")
            with self.assertRaises(ValueError):
                script.download(ROW, root, lambda: fake)

    def test_credentials_cannot_be_sent_to_unapproved_links(self):
        for url in ("http://data.gesdisc.earthdata.nasa.gov/file.HDF5", "https://example.com/file.HDF5",
                    "https://user:pass@data.gesdisc.earthdata.nasa.gov/file.HDF5"):
            row = dict(ROW, links=[dict(ROW["links"][0], href=url)])
            with self.assertRaises(ValueError):
                script.data_url(row)


if __name__ == "__main__":
    unittest.main()
