"""Offline tests: python3 -m unittest discover -s collector -v"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import classify as C  # noqa: E402


class TestRelevance(unittest.TestCase):
    def test_core(self):
        for t in ("7.4 A 112Gb/s DSP-Based PAM-4 Receiver with an LC-Resonator-Based CTLE for >52dB Loss Compensation in 4nm FinFET",
                  "A 5-Gb/s ADC-Based Feed-Forward CDR in 65 nm CMOS",
                  "A 112-Gb/s —8.2-dBm Sensitivity 4-PAM Linear TIA in 16-nm CMOS With Co-Packaged Photodiodes",
                  "A Single-Ended Inverter-Based Addition-Only Feed-Forward Equalization Transmitter",
                  "Far-End Crosstalk Cancellation With MIMO OFDM for >200 Gb/s ADC-Based Serial Links"):
            self.assertEqual(C.relevance(t, ""), "core", t)

    def test_wireless_and_non_links_are_out(self):
        for t in ("A Four-Channel Bidirectional D-Band Phased-Array Transceiver for 200 Gb/s 6G Wireless Communications",
                  "A 5.76 Gb/s 79.7 pJ/b 128×32 Massive Deep-Learning Uplink MIMO Detector in 28nm CMOS Technology",
                  "6.4Gb/s multi-threaded BCH encoder and decoder for multi-channel SSD controllers",
                  "A 3.3-Gb/s SPAD-Based Quantum Random Number Generator"):
            self.assertIsNone(C.relevance(t, ""), t)


class TestSpecs(unittest.TestCase):
    def test_title(self):
        t = "A 1.41-pJ/b 224-Gb/s PAM4 6-bit ADC-Based SerDes Receiver With Hybrid AFE Capable of Supporting Long Reach Channels"
        s = C.parse_specs(t, "")
        self.assertEqual((s["rate"], s["eff"], s["resadc"]), (224e9, 1.41, 6))
        self.assertEqual((C.link_type(t, ""), C.modulations(t, "")), ("ADC/DAC-based", ["PAM4"]))
        self.assertEqual(C.link_type("A 112Gb/s DSP-Based PAM-4 Receiver", ""), "DSP (no ADC)")
        self.assertEqual(C.link_type("A 112Gb/s DSP-Based PAM-4 Receiver", "The receiver uses a 7-b 56-GS/s ADC-based front end."), "ADC/DAC-based")
        self.assertIn("ADC-based RX", C.architectures(t, ""))

    def test_abstract_and_derived(self):
        s = C.parse_specs("A wireline receiver", "The 56-Gb/s receiver compensates 35-dB channel loss and consumes 280 mW in 7-nm FinFET.")
        self.assertEqual((s["rate"], s["loss"], s["p"], s["node"]), (56e9, 35.0, 0.28, 7))
        self.assertEqual(C.derived(s), {"eff_calc": 5.0})

    def test_several_rates_are_left_out(self):
        self.assertNotIn("rate", C.parse_specs("A transceiver", "It runs at 56 Gb/s in PAM4 and 28 Gb/s in NRZ."))


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cache = os.path.join(self.tmp, "cache")
        os.makedirs(self.cache)
        self._papers, self._meta = build.PAPERS, build.META
        build.PAPERS = os.path.join(self.tmp, "papers.json")
        build.META = os.path.join(self.tmp, "meta.json")

    def tearDown(self):
        build.PAPERS, build.META = self._papers, self._meta
        shutil.rmtree(self.tmp)

    def put(self, n, title, pub, abstract="", year=2025):
        with open(os.path.join(self.cache, "%d.json" % n), "w", encoding="utf-8") as f:
            json.dump({"article_number": n, "title": title, "publication_title": pub, "abstract": abstract,
                       "publication_year": year, "publication_date": "Feb. %d" % year, "doi": "10.1109/x.%d" % n,
                       "authors": {"authors": [{"full_name": "A. Kim", "author_order": 1,
                                                "affiliation": "KAIST, Daejeon, South Korea"}]}}, f)

    def test_rebuild(self):
        config = build.load_json(build.CONFIG, None)
        self.put(1, "A 112-Gb/s ADC-Based PAM-4 Receiver With MLSD", "IEEE Journal of Solid-State Circuits", "It consumes 560 mW.")
        self.put(2, "A 12-b SAR ADC", "IEEE Journal of Solid-State Circuits")
        self.put(3, "A 32-Gb/s NRZ Transmitter With FFE", "2025 IEEE Custom Integrated Circuits Conference (CICC)")
        meta = build.rebuild(config, self.cache, "2026-10-24")
        papers = {p["id"]: p for p in build.load_json(build.PAPERS, [])}
        self.assertEqual(set(papers), {"1", "3"})
        p = papers["1"]
        self.assertEqual((p["ty"], p["mod"], p["x"]["eff_calc"]), ("ADC/DAC-based", ["PAM4"], 5.0))
        self.assertEqual(papers["3"]["ty"], "Analog/mixed-signal")
        self.assertNotIn("abstract", json.dumps(list(papers.values())))
        self.assertEqual(meta["core"], 2)


if __name__ == "__main__":
    unittest.main()
