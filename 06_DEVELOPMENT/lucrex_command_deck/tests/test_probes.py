import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import probes

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


class TestSession(unittest.TestCase):
    def test_token_sums_and_turns(self):
        s = probes.session(transcript_dir=FIX)
        self.assertIsNone(s["error"])
        self.assertEqual(s["turns"], 2)
        self.assertEqual(s["model"], "claude-opus-4-8")
        self.assertEqual(s["tokens"]["input"], 300)
        self.assertEqual(s["tokens"]["output"], 100)
        self.assertEqual(s["tokens"]["cache_read"], 30)
        self.assertEqual(s["tokens"]["cache_creation"], 5)
        self.assertEqual(s["tokens"]["total"], 435)
        self.assertEqual(s["recent_output"], 100)  # last <=3 turns

    def test_missing_dir_is_soft_error(self):
        s = probes.session(transcript_dir="/no/such/dir")
        self.assertIsNotNone(s["error"])
        self.assertEqual(s["tokens"]["total"], 0)


class TestVitals(unittest.TestCase):
    def test_vitals_shape(self):
        v = probes.vitals()
        for k in ("uptime", "load", "mem_pct", "disk_pct"):
            self.assertIn(k, v)


if __name__ == "__main__":
    unittest.main()
