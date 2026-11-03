"""Offline regressions for the real Python media worker; no external services required."""
import importlib.util
import socket
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

path = Path(__file__).resolve().parents[1] / 'server/media/media_worker.py'
spec = importlib.util.spec_from_file_location('media_worker', path)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
# Importing a production worker installs its socket guard. Keep this test runner isolated.
socket.getaddrinfo = w.GUARD._original_getaddrinfo
socket.socket.connect = w.GUARD._original_connect


class MediaWorkerTests(unittest.TestCase):
    def test_dns_failure_is_not_reported_as_missing_worker(self):
        guard = w.NetworkGuard()
        guard._original_getaddrinfo = MagicMock(side_effect=socket.gaierror("DNS unavailable"))
        with self.assertRaises(w.MediaError) as caught:
            guard.resolve("example.com", 443)
        self.assertEqual(caught.exception.code, "network_unavailable")

    def test_discovers_deno_without_env(self):
        with patch.dict(w.os.environ, {}, clear=True), patch.object(w.shutil, 'which', return_value='/bin/deno'):
            self.assertEqual(w.ytdlp_options()['js_runtimes'], {'deno': {'path': '/bin/deno'}})
            self.assertEqual(w.ytdlp_options()['remote_components'], set())

    def test_invalid_explicit_runtime_does_not_silently_fallback(self):
        with patch.dict(w.os.environ, {'AREV_DENO': '/nonexistent/deno'}):
            self.assertIsNone(w.runtime_path())

    def test_missing_ejs_has_actionable_error(self):
        with patch.object(w.importlib.metadata, 'version', side_effect=w.importlib.metadata.PackageNotFoundError):
            with self.assertRaises(w.MediaError) as caught:
                w.require_youtube_dependencies('https://youtu.be/abcdefghijk')
            self.assertEqual(caught.exception.code, 'ejs_unavailable')

    def test_missing_runtime_has_actionable_error(self):
        with patch.object(w.importlib.metadata, 'version', return_value='1'), patch.object(w, 'runtime_path', return_value=None):
            with self.assertRaises(w.MediaError) as caught:
                w.require_youtube_dependencies('https://www.youtube.com/watch?v=abcdefghijk')
            self.assertEqual(caught.exception.code, 'runtime_unavailable')

    def test_other_sites_do_not_require_youtube_components(self):
        with patch.object(w.importlib.metadata, 'version', side_effect=AssertionError):
            w.require_youtube_dependencies('https://example.com/movie')

    def test_head_refusal_still_uses_extractor(self):
        with patch.object(w, 'safe_open', side_effect=w.MediaError('media_not_found')), patch.object(w, 'ytdlp_inspect', return_value={'title': 'ok'}) as extract:
            self.assertEqual(w.inspect('https://example.com/movie'), {'title': 'ok'})
            extract.assert_called_once()

    def test_probe_does_not_hide_private_destination(self):
        with patch.object(w, 'safe_open', side_effect=w.MediaError('private_url')), patch.object(w, 'ytdlp_inspect') as extract:
            with self.assertRaises(w.MediaError):
                w.inspect('https://example.com/movie')
            extract.assert_not_called()

    def test_mp4_prefers_m4a_over_higher_bitrate_opus(self):
        info = {'formats': [
            {'format_id': 'v', 'ext': 'mp4', 'vcodec': 'avc1', 'acodec': 'none', 'height': 720},
            {'format_id': 'a', 'ext': 'm4a', 'vcodec': 'none', 'acodec': 'mp4a', 'abr': 128},
            {'format_id': 'o', 'ext': 'webm', 'vcodec': 'none', 'acodec': 'opus', 'abr': 160}]}
        self.assertEqual(w.build_ytdlp_formats(info)[1][0]['selector'], 'v+a')

    def test_errors_have_same_classification_in_inspect_and_download(self):
        fake = types.SimpleNamespace(YoutubeDL=MagicMock(side_effect=RuntimeError("Sign in to confirm you're not a bot")))
        with patch.dict(sys.modules, {'yt_dlp': fake}), patch.object(w, 'require_youtube_dependencies'):
            with self.assertRaises(w.MediaError) as inspected:
                w.ytdlp_inspect('https://youtube.com/watch?v=abcdefghijk')
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(w.MediaError) as downloaded:
                    w.download_ytdlp({'pageUrl': 'https://youtube.com/watch?v=abcdefghijk', 'ext': 'mp4', 'selector': 'v+a'}, Path(directory))
            self.assertEqual(inspected.exception.code, 'source_blocked')
            self.assertEqual(downloaded.exception.code, 'source_blocked')

    def test_diagnostics_report_missing_tools_without_claiming_access(self):
        with patch.object(w.importlib.metadata, 'version', side_effect=w.importlib.metadata.PackageNotFoundError), patch.object(w, 'runtime_path', return_value=None), patch.object(w.shutil, 'which', return_value=None):
            result = w.diagnostics()
        self.assertFalse(result['ready'])
        self.assertFalse(result['sourceAccessVerified'])
        self.assertIn('yt-dlp-ejs', result['missing'])
        self.assertIn('deno', result['missing'])

    def test_drm_and_live_stay_rejected(self):
        for info in ({'has_drm': True}, {'is_live': True}):
            with self.assertRaises(w.MediaError):
                w.build_ytdlp_formats(info)


if __name__ == '__main__':
    unittest.main()
