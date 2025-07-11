"""Unit test script for the functions in hlplots/tagger.py."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np
from ftag import Flavours, get_mock_file
from ftag.hdf5 import structured_from_dict

from puma.hlplots import Results
from puma.hlplots.tagger import Tagger
from puma.utils import logger, set_log_level

set_log_level(logger, "DEBUG")


class ResultsTestCase(unittest.TestCase):
    """Test class for the Results class."""

    def test_set_signal_hcc(self):
        """Test set_signal for hcc."""
        results = Results(signal="hcc", sample="test", category="xbb")
        self.assertEqual(
            results.backgrounds,
            [*Flavours.by_category("xbb").backgrounds(Flavours.hcc)],
        )
        self.assertEqual(results.signal, Flavours.hcc)

    def test_add_duplicated(self):
        """Test empty string as model name."""
        dummy_tagger_1 = Tagger("dummy")
        dummy_tagger_2 = Tagger("dummy")
        results = Results(signal="bjets", sample="test")
        results.add(dummy_tagger_1)
        with self.assertRaises(KeyError):
            results.add(dummy_tagger_2)

    def test_add_2_taggers(self):
        """Test empty string as model name."""
        dummy_tagger_1 = Tagger("dummy")
        dummy_tagger_2 = Tagger("dummy_2")
        results = Results(signal="bjets", sample="test")
        results.add(dummy_tagger_1)
        results.add(dummy_tagger_2)
        self.assertEqual(
            list(results.taggers.keys()),
            ["dummy (dummy)", "dummy_2 (dummy_2)"],  # pylint: disable=W0212
        )

    def test_get_taggers(self):
        """Test empty string as model name."""
        dummy_tagger_1 = Tagger("dummy")
        dummy_tagger_2 = Tagger("dummy_2")
        results = Results(signal="bjets", sample="test")
        results.add(dummy_tagger_1)
        results.add(dummy_tagger_2)
        retrieved_dummy_tagger_2 = results["dummy_2 (dummy_2)"]
        self.assertEqual(retrieved_dummy_tagger_2.name, dummy_tagger_2.name)

    def test_load_taggers_from_file(self):
        """Test for Results.load_taggers_from_file function."""
        fname = get_mock_file()[0]
        results = Results(signal="bjets", sample="test")
        taggers = [Tagger("MockTagger")]
        results.load_taggers_from_file(taggers, fname)
        self.assertEqual(list(results.taggers.values()), taggers)

    def test_load_taggers_from_file_with_perf_vars(self):
        """Test for Results.load_taggers_from_file function."""
        fname = get_mock_file()[0]
        results = Results(signal="bjets", sample="test", perf_vars=["pt", "eta"])
        taggers = [Tagger("MockTagger")]
        results.load_taggers_from_file(taggers, fname)
        self.assertEqual(list(results.taggers.values()), taggers)

    def test_add_taggers_with_cuts_override_perf_vars(self):
        """Test for Results.load_taggers_from_file function."""
        rng = np.random.default_rng(seed=16)
        cuts = [("eta", ">", 0)]
        tagger_cuts = [("pt", ">", 20)]
        fname = get_mock_file(num_jets=1000)[0]
        results = Results(signal="bjets", sample="test", perf_vars=["pt", "eta"])
        taggers = [Tagger("MockTagger", cuts=tagger_cuts)]

        results.load_taggers_from_file(
            taggers,
            fname,
            cuts=cuts,
            perf_vars={
                "pt": rng.exponential(100, size=1000),
                "eta": rng.normal(0, 1, size=1000),
            },
        )
        self.assertEqual(list(results.taggers.values()), taggers)

    def test_add_taggers_with_cuts(self):
        fname = get_mock_file()[0]
        cuts = [("eta", ">", 0)]
        tagger_cuts = [("pt", ">", 20)]
        results = Results(signal="bjets", sample="test")
        taggers = [Tagger("MockTagger", cuts=tagger_cuts)]
        results.load_taggers_from_file(taggers, fname, cuts=cuts)
        self.assertEqual(list(results.taggers.values()), taggers)

    def test_add_taggers_taujets(self):
        # get mock file and rename variables match taujets
        fname = get_mock_file()[0]
        results = Results(
            signal="bjets",
            sample="test",
        )
        taggers = [Tagger("MockTagger", fxs={"fu": 0.1, "fc": 0.1, "ftau": 0.1})]
        results.load_taggers_from_file(taggers, fname)
        assert "MockTagger_ptau" in taggers[0].scores.dtype.names
        taggers[0].discriminant("bjets")

    def test_add_taggers_hbb(self):
        # get mock file and rename variables match hbb
        f = get_mock_file()[1]
        d = {}
        d["R10TruthLabel"] = f["jets"]["HadronConeExclTruthLabelID"]
        d["MockTagger_phbb"] = f["jets"]["MockTagger_pb"]
        d["MockTagger_phcc"] = f["jets"]["MockTagger_pc"]
        d["MockTagger_ptop"] = f["jets"]["MockTagger_pu"]
        d["MockTagger_pqcd"] = f["jets"]["MockTagger_pu"]
        d["pt"] = f["jets"]["pt"]
        array = structured_from_dict(d)
        with tempfile.TemporaryDirectory() as tmp_file:
            fname = Path(tmp_file) / "test.h5"
            with h5py.File(fname, "w") as f:
                f.create_dataset("jets", data=array)

            results = Results(signal="hbb", sample="test", category="xbb")
            results.load_taggers_from_file(
                [
                    Tagger(
                        "MockTagger",
                        category="xbb",
                        output_flavours=["hbb", "hcc", "top", "qcd"],
                    )
                ],
                fname,
                label_var="R10TruthLabel",
            )

    def test_add_taggers_keep_nan(self):
        # get mock file and add nans
        f = get_mock_file()[1]
        d = {}
        d["HadronConeExclTruthLabelID"] = f["jets"]["HadronConeExclTruthLabelID"]
        d["MockTagger_pb"] = f["jets"]["MockTagger_pb"]
        d["MockTagger_pc"] = f["jets"]["MockTagger_pc"]
        d["MockTagger_pu"] = f["jets"]["MockTagger_pu"]
        d["pt"] = f["jets"]["pt"]
        n_nans = np.random.choice(range(100), 10)
        d["MockTagger_pb"][n_nans] = np.nan
        array = structured_from_dict(d)
        with tempfile.TemporaryDirectory() as tmp_file:
            fname = Path(tmp_file) / "test.h5"
            with h5py.File(fname, "w") as f:
                f.create_dataset("jets", data=array)

            results = Results(signal="bjets", sample="test", remove_nan=False)
            with self.assertRaises(ValueError):
                results.load_taggers_from_file([Tagger("MockTagger")], fname)

    def test_add_taggers_remove_nan(self):
        # get mock file and add nans
        f = get_mock_file()[1]
        d = {}
        d["HadronConeExclTruthLabelID"] = f["jets"]["HadronConeExclTruthLabelID"]
        d["MockTagger_pb"] = f["jets"]["MockTagger_pb"]
        d["MockTagger_pc"] = f["jets"]["MockTagger_pc"]
        d["MockTagger_pu"] = f["jets"]["MockTagger_pu"]
        d["pt"] = f["jets"]["pt"]
        n_nans = np.random.choice(range(100), 10, replace=False)
        d["MockTagger_pb"][n_nans] = np.nan
        array = structured_from_dict(d)
        with tempfile.TemporaryDirectory() as tmp_file:
            fname = Path(tmp_file) / "test.h5"
            with h5py.File(fname, "w") as f:
                f.create_dataset("jets", data=array)

            results = Results(signal="bjets", sample="test", remove_nan=True)
            with self.assertLogs("puma", "WARNING") as cm:
                results.load_taggers_from_file(
                    taggers=[Tagger("MockTagger", output_flavours=["ujets", "cjets", "bjets"])],
                    file_path=fname,
                )
            self.assertEqual(
                cm.output,
                [f"WARNING:puma:{len(n_nans)} NaN values found in loaded data. Removing them."],
            )

    def test_add_taggers_ValueError(self):
        """Testing raise of ValueError if NaNs are still present."""
        # get mock file and add nans
        f = get_mock_file()[1]
        d = {}
        d["HadronConeExclTruthLabelID"] = f["jets"]["HadronConeExclTruthLabelID"]
        d["MockTagger_pb"] = f["jets"]["MockTagger_pb"]
        d["MockTagger_pc"] = f["jets"]["MockTagger_pc"]
        d["MockTagger_pu"] = f["jets"]["MockTagger_pu"]
        d["pt"] = f["jets"]["pt"]
        n_nans = np.random.choice(range(100), 10, replace=False)
        d["MockTagger_pb"][n_nans] = np.nan
        array = structured_from_dict(d)
        with tempfile.TemporaryDirectory() as tmp_file:
            fname = Path(tmp_file) / "test.h5"
            with h5py.File(fname, "w") as f:
                f.create_dataset("jets", data=array)

            results = Results(signal="bjets", sample="test", remove_nan=False)
            with self.assertRaises(ValueError):
                results.load_taggers_from_file(
                    taggers=[Tagger("MockTagger", output_flavours=["ujets", "cjets", "bjets"])],
                    file_path=fname,
                )


class ResultsPlotsTestCase(unittest.TestCase):
    """Test class for the Results class running plots."""

    def setUp(self) -> None:
        """Set up for unit tests."""
        f = get_mock_file()[1]
        dummy_tagger_1 = Tagger("MockTagger", output_flavours=["ujets", "cjets", "bjets"])
        dummy_tagger_1.labels = np.array(
            f["jets"]["HadronConeExclTruthLabelID"],
            dtype=[("HadronConeExclTruthLabelID", "i4")],
        )
        dummy_tagger_1.scores = f["jets"]
        dummy_tagger_1.label = "dummy tagger"
        self.dummy_tagger_1 = dummy_tagger_1

    def test_plot_probs_bjets(self):
        """Test that png file is being created."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_probs(bins=40, bins_range=(0, 1))
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_discs_bjets(self):
        """Test that png file is being created."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_discs(bins=40, bins_range=(-2, 15))
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_discs_cjets(self):
        """Test that png file is being created."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fb": 0.05, "fu": 0.95}
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="cjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_discs(bins=40, bins_range=(-2, 15), wp_vlines=[60])
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_roc_bjets(self):
        """Test that png file is being created."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_rocs()
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_roc_cjets(self):
        """Test that png file is being created."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fb": 0.05, "fu": 0.95}
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="cjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_rocs(fontsize=5)
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_var_perf_err(self):
        """Tests the performance plots throws errors with invalid inputs."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        self.dummy_tagger_1.disc_cut = 2
        rng = np.random.default_rng(seed=16)
        self.dummy_tagger_1.perf_vars = {
            "pt": rng.exponential(100, size=len(self.dummy_tagger_1.scores))
        }
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            with self.assertRaises(ValueError):
                results.plot_var_perf(
                    bins=[20, 30, 40, 60, 85, 110, 140, 175, 250],
                )
            with self.assertRaises(ValueError):
                results.plot_var_perf(
                    bins=[20, 30, 40, 60, 85, 110, 140, 175, 250],
                    disc_cut=1,
                    working_point=0.5,
                )

    def test_plot_var_eff_per_flat_rej_err(self):
        """Tests the performance vs flat rejection plots throws errors
        with invalid inputs.
        """
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        self.dummy_tagger_1.disc_cut = 2
        rng = np.random.default_rng(seed=16)
        self.dummy_tagger_1.perf_vars = {
            "pt": rng.exponential(100, size=len(self.dummy_tagger_1.scores))
        }
        with tempfile.TemporaryDirectory() as tmp_file, self.assertRaises(ValueError):
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.plot_flat_rej_var_perf(
                bins=[20, 30, 40, 60, 85, 110, 140, 175, 250],
                fixed_rejections={"cjets": 10, "ujets": 100},
                working_point=0.5,
            )
        with tempfile.TemporaryDirectory() as tmp_file, self.assertRaises(ValueError):
            results.plot_flat_rej_var_perf(
                bins=[20, 30, 40, 60, 85, 110, 140, 175, 250],
                fixed_rejections={"cjets": 10, "ujets": 100},
                disc_cut=0.5,
            )

    def test_plot_var_perf_bjets(self):
        """Test that png file is being created."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        self.dummy_tagger_1.disc_cut = 2
        rng = np.random.default_rng(seed=16)
        self.dummy_tagger_1.perf_vars = {
            "pt": rng.exponential(100, size=len(self.dummy_tagger_1.scores))
        }
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_var_perf(
                bins=[20, 30, 40, 60, 85, 110, 140, 175, 250],
                working_point=0.7,
            )
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_var_perf_bjets_disc_cut(self):
        """Test that png file is being created."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        self.dummy_tagger_1.disc_cut = 2
        rng = np.random.default_rng(seed=16)
        self.dummy_tagger_1.perf_vars = {
            "pt": rng.exponential(100, size=len(self.dummy_tagger_1.scores))
        }
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_var_perf(
                bins=[20, 30, 40, 60, 85, 110, 140, 175, 250],
                disc_cut=0.5,
            )
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_var_perf_bjets_pcft(self):
        """Test that png file is being created."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        self.dummy_tagger_1.disc_cut = 2
        rng = np.random.default_rng(seed=16)
        self.dummy_tagger_1.perf_vars = {
            "pt": rng.exponential(100, size=len(self.dummy_tagger_1.scores))
        }
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_var_perf(
                bins=[20, 30, 40, 60, 85, 110, 140, 175, 250],
                working_point=[0.5, 0.8],
            )
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_var_perf_extra_kwargs(self):
        """Test that png file is being created."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        self.dummy_tagger_1.disc_cut = 2
        rng = np.random.default_rng(seed=16)
        self.dummy_tagger_1.perf_vars = {
            "pt": rng.exponential(100, size=len(self.dummy_tagger_1.scores))
        }
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_var_perf(
                bins=[20, 30, 40, 60, 85, 110, 140, 175, 250],
                working_point=0.7,
                y_scale=1.3,
            )
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_var_perf_multi_bjets(self):
        """Test that png file is being created."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        self.dummy_tagger_1.disc_cut = 2
        rng = np.random.default_rng(seed=16)
        self.dummy_tagger_1.perf_vars = {
            "pt": rng.exponential(100, size=len(self.dummy_tagger_1.scores)),
            "eta": rng.normal(0, 1, size=len(self.dummy_tagger_1.scores)),
        }
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_var_perf(
                bins=[20, 30, 40, 60, 85, 110, 140, 175, 250],
                working_point=0.7,
                perf_var="pt",
            )
            results.plot_var_perf(
                bins=np.linspace(-0.5, 0.5, 10), working_point=0.7, perf_var="eta"
            )
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_var_perf_cjets(self):
        """Test that png file is being created."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fb": 0.05, "fu": 0.95}
        self.dummy_tagger_1.working_point = 0.5
        rng = np.random.default_rng(seed=16)
        self.dummy_tagger_1.perf_vars = {
            "pt": rng.exponential(100, size=len(self.dummy_tagger_1.scores))
        }
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="cjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_var_perf(
                h_line=self.dummy_tagger_1.working_point,
                bins=[20, 30, 40, 60, 85, 110, 140, 175, 250],
                working_point=0.7,
            )
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_beff_vs_flat_rej(self):
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        self.dummy_tagger_1.working_point = 0.5
        rng = np.random.default_rng(seed=16)
        self.dummy_tagger_1.perf_vars = {
            "pt": rng.exponential(100, size=len(self.dummy_tagger_1.scores))
        }
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_flat_rej_var_perf(
                fixed_rejections={"cjets": 10, "ujets": 100},
                bins=[20, 30, 40, 60, 85, 110, 140, 175, 250],
                h_line=0.5,
            )
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_beff_vs_flat_rej_extra_kwargs(self):
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        self.dummy_tagger_1.working_point = 0.5
        rng = np.random.default_rng(seed=16)
        self.dummy_tagger_1.perf_vars = {
            "pt": rng.exponential(100, size=len(self.dummy_tagger_1.scores))
        }
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_flat_rej_var_perf(
                fixed_rejections={"cjets": 10, "ujets": 100},
                bins=[20, 30, 40, 60, 85, 110, 140, 175, 250],
                h_line=0.5,
                y_scale=1.3,
            )
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_ceff_vs_flat_rej(self):
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fb": 0.05, "fu": 0.95}
        self.dummy_tagger_1.working_point = 0.5
        rng = np.random.default_rng(seed=16)
        self.dummy_tagger_1.perf_vars = {
            "pt": rng.exponential(100, size=len(self.dummy_tagger_1.scores))
        }
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="cjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_flat_rej_var_perf(
                fixed_rejections={"bjets": 10, "ujets": 100},
                bins=[20, 30, 40, 60, 85, 110, 140, 175, 250],
            )
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_fraction_scans_hbb_error(self):
        """Test that correct error is raised."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="hbb", sample="test", category="xbb", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            with self.assertRaises(ValueError):
                results.plot_fraction_scans(
                    backgrounds_to_plot=["cjets", "ujets"],
                    rej=False,
                    plot_optimal_fraction_values=True,
                )

    def test_plot_fraction_scans_bjets_eff(self):
        """Test that png file is being created."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_fraction_scans(
                backgrounds_to_plot=["cjets", "ujets"],
                rej=False,
                plot_optimal_fraction_values=True,
            )
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_fraction_scans_cjets_rej(self):
        """Test that png file is being created."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fb": 0.05, "fu": 0.95}
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="cjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            results.plot_fraction_scans(
                backgrounds_to_plot=["bjets", "ujets"],
                rej=False,
                plot_optimal_fraction_values=True,
            )
            for fpath in results.saved_plots:
                assert fpath.is_file()
            results.saved_plots = []

    def test_plot_fraction_scans_multiple_bkg_error(self):
        """Test error of more than two backgrounds."""
        self.dummy_tagger_1.reference = True
        self.dummy_tagger_1.fxs = {"fc": 0.05, "fu": 0.95}
        with tempfile.TemporaryDirectory() as tmp_file:
            results = Results(signal="bjets", sample="test", output_dir=tmp_file)
            results.add(self.dummy_tagger_1)
            with self.assertRaises(ValueError):
                results.plot_fraction_scans(
                    backgrounds_to_plot=["bjets", "ujets", "taujets"],
                    rej=False,
                    plot_optimal_fraction_values=True,
                )

    def test_make_plot_error(self):
        """Test error of non-existing plot type."""
        results = Results(signal="bjets", sample="test")
        with self.assertRaises(ValueError):
            results.make_plot(plot_type="crash", kwargs={})
