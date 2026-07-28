"""
Unit tests for target/qrterminal.py
"""

import unittest
import io
import sys
import os

# Add target directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import qrterminal

class TestQRTerminal(unittest.TestCase):

    def test_empty_or_short_input(self):
        buf = io.StringIO()
        qrterminal.generate("a", qrterminal.L, buf)
        out = buf.getvalue()
        self.assertIn("\033[47m", out)
        self.assertTrue(len(out) > 0)

    def test_normal_text(self):
        buf = io.StringIO()
        qrterminal.generate_half_block("Hello World!", qrterminal.M, buf)
        out = buf.getvalue()
        self.assertIn("▄", out)
        self.assertIn("█", out)

    def test_url_encoding(self):
        buf = io.StringIO()
        qrterminal.generate_half_block("https://example.com", qrterminal.L, buf)
        out = buf.getvalue()
        self.assertIn("▄", out)
        self.assertIn("█", out)

    def test_correction_levels(self):
        for lvl in [qrterminal.L, qrterminal.M, qrterminal.Q, qrterminal.H]:
            buf = io.StringIO()
            qrterminal.generate("Test Level", lvl, buf)
            out = buf.getvalue()
            self.assertTrue(len(out) > 0, f"Failed for level {lvl}")

    def test_full_block_mode(self):
        buf = io.StringIO()
        cfg = qrterminal.Config(
            level=qrterminal.L,
            writer=buf,
            half_blocks=False,
            black_char=qrterminal.BLACK,
            white_char=qrterminal.WHITE,
            quiet_zone=4
        )
        qrterminal.generate_with_config("FullBlockTest", cfg)
        out = buf.getvalue()
        self.assertIn(qrterminal.BLACK, out)
        self.assertIn(qrterminal.WHITE, out)

    def test_half_block_mode(self):
        buf = io.StringIO()
        cfg = qrterminal.Config(
            level=qrterminal.L,
            writer=buf,
            half_blocks=True,
            quiet_zone=4
        )
        qrterminal.generate_with_config("HalfBlockTest", cfg)
        out = buf.getvalue()
        self.assertIn(qrterminal.BLACK_WHITE, out)
        self.assertIn(qrterminal.WHITE_BLACK, out)

    def test_quiet_zone_values(self):
        for qz in [1, 2, 4, 6]:
            buf = io.StringIO()
            cfg = qrterminal.Config(
                level=qrterminal.L,
                writer=buf,
                half_blocks=True,
                quiet_zone=qz
            )
            qrterminal.generate_with_config("QuietZoneTest", cfg)
            out = buf.getvalue()
            self.assertTrue(len(out) > 0, f"Failed for quiet zone {qz}")

    def test_sixel_rendering(self):
        buf = io.StringIO()
        cfg = qrterminal.Config(
            level=qrterminal.L,
            writer=buf,
            with_sixel=True,
            quiet_zone=2
        )
        qrterminal.generate_with_config("SixelTest", cfg)
        out = buf.getvalue()
        self.assertIn(qrterminal.SIXEL_BEGIN, out)
        self.assertIn(qrterminal.SIXEL_END, out)

if __name__ == '__main__':
    unittest.main()
