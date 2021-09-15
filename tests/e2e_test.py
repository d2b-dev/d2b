from __future__ import annotations

import filecmp
import json
import subprocess
from pathlib import Path

from d2b.d2b import __version__


class TestE2e:
    def _check_run_results(
        self,
        data_dir: Path,
        out_dir: Path,
        sidecar_files: list[str],
        other_files: list[str],
    ):
        """generic checks for all test_run_* methods"""
        expected_out_dir = data_dir / "out"

        for f in sidecar_files:
            assert (out_dir / f).exists()

            actual_sidecar = json.loads((out_dir / f).read_text())
            expected_sidecar = json.loads((expected_out_dir / f).read_text())
            assert actual_sidecar.pop("D2bVersion") == __version__
            assert actual_sidecar == expected_sidecar

        for f in other_files:
            assert (out_dir / f).exists()
            assert filecmp.cmp(out_dir / f, expected_out_dir / f, shallow=False)

    def test_cli_run(self, d2b_run_e2e: Path, tmpdir: str):

        data_dir = d2b_run_e2e / "intended-for-fields"
        sidecar_files = [
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-AP_fmap.json",
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-PA_fmap.json",
            "sub-a/ses-1/fmap/sub-a_ses-1_fmap.json",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_bold.json",
            "sub-a/ses-1/anat/sub-a_ses-1_T1w.json",
            "sub-a/ses-1/func/sub-a_ses-1_task-fingertap_bold.json",
        ]
        other_files = [
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-AP_fmap.nii.gz",
            "sub-a/ses-1/fmap/sub-a_ses-1_dir-PA_fmap.nii.gz",
            "sub-a/ses-1/fmap/sub-a_ses-1_fmap.nii.gz",
            "sub-a/ses-1/func/sub-a_ses-1_task-rest_bold.nii.gz",
            "sub-a/ses-1/anat/sub-a_ses-1_T1w.nii.gz",
            "sub-a/ses-1/func/sub-a_ses-1_task-fingertap_bold.nii.gz",
        ]
        out_dir = Path(tmpdir) / "bids"

        config_file = data_dir / "d2b-config.json"
        in_dir = data_dir / "in"

        subprocess.run(
            (
                "d2b",
                "run",
                f"--config={config_file}",
                "--participant=a",
                "--session=1",
                f"--out-dir={out_dir}",
                in_dir,
            ),
        )

        self._check_run_results(data_dir, out_dir, sidecar_files, other_files)

    def test_cli_scaffold(self, tmpdir: str):
        scaffold_files = [
            "CHANGES",
            "README",
            "dataset_description.json",
            "participants.json",
            "participants.tsv",
        ]
        scaffold_directories = ["code", "derivatives"]

        subprocess.run(("d2b", "scaffold", tmpdir))

        for f in scaffold_files:
            assert (Path(tmpdir) / f).is_file()

        for d in scaffold_directories:
            assert (Path(tmpdir) / d).is_dir()
