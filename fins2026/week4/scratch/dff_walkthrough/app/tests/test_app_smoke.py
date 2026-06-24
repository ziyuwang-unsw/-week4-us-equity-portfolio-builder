"""Smoke test for the 50-stock portfolio app."""

from __future__ import annotations

import os
import platform
import shutil
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
VIEWS = {
    "Portfolio Weights": "Portfolio weights",
    "Growth of $1": "Growth of $1",
    "Efficient Frontier": "Efficient frontier",
    "Data": "Data and downloads",
}


def test_dff_streamlit_app_smoke(monkeypatch) -> None:
    if platform.system() == "Windows" and not os.environ.get("RUN_STREAMLIT_APPTEST_ON_WINDOWS"):
        pytest.skip(
            "Streamlit AppTest can leave locked temp files on native Windows; "
            "run in Linux CI or set RUN_STREAMLIT_APPTEST_ON_WINDOWS=1."
        )

    temp_root = ROOT / ".tmp-dff-streamlit-test"
    temp_root.mkdir(exist_ok=True)
    monkeypatch.setenv("TMP", str(temp_root))
    monkeypatch.setenv("TEMP", str(temp_root))
    tempfile.tempdir = str(temp_root)

    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    for view, expected_text in VIEWS.items():
        at = AppTest.from_file(app_path, default_timeout=60)
        at.query_params["view"] = view
        at.query_params["constraints"] = "unconstrained"
        at.run()
        assert not at.exception, f"{view} tab raised: {at.exception}"
        rendered = "\n".join(
            str(element.value)
            for collection in [
                at.title,
                at.subheader,
                at.caption,
                at.markdown,
                at.info,
                at.warning,
                at.button,
                getattr(at, "download_button", []),
            ]
            for element in collection
        )
        assert "50-Stock Portfolio Builder" in rendered
        assert expected_text in rendered
    shutil.rmtree(temp_root, ignore_errors=True)
