"""Configuration parameters for psy-view."""

# SPDX-FileCopyrightText: 2020-2021 Helmholtz-Zentrum Geesthacht
# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

from __future__ import annotations

from typing import Any, Dict, List, Optional

from psyplot.config.rcsetup import validate_dict
from psyplot_gui.config.rcsetup import (
    RcParams,
    psyplot_fname,
    validate_stringlist,
)

defaultParams: Dict[str, List[Any]] = {
    "projections": [
        ["cf", "cyl", "robin", "ortho", "moll", "northpole", "southpole"],
        validate_stringlist,
        "The names of available projections",
    ],
    "savefig_kws": [
        dict(dpi=250),
        validate_dict,
        "Options that are passed to plt.savefig when exporting images",
    ],
    "animations.export_kws": [
        dict(writer="ffmpeg"),
        validate_dict,
        "Options that are passed to FuncAnimation.save",
    ],
}


class PsyViewRcParams(RcParams):
    """RcParams for the psyplot-gui package."""

    HEADER: str = RcParams.HEADER.replace(
        "psyplotrc.yml", "psyviewrc.yml"
    ).replace("PSYVIEWRC", "psyviewrc.yml")

    def load_from_file(self, fname: Optional[str] = None):
        """
        Update rcParams from user-defined settings

        This function updates the instance with what is found in `fname`

        Parameters
        ----------
        fname: str
            Path to the yaml configuration file. Possible keys of the
            dictionary are defined by :data:`config.rcsetup.defaultParams`.
            If None, the :func:`config.rcsetup.psyplot_fname` function is used.

        See Also
        --------
        dump_to_file, psyplot_fname"""
        fname = fname or psyplot_fname(
            env_key="PSYVIEWRC", fname="psyviewrc.yml"
        )
        if fname:
            super().load_from_file(fname)


rcParams = PsyViewRcParams(defaultParams=defaultParams)
rcParams.update_from_defaultParams()
rcParams.load_from_file()
