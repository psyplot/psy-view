"""Configuration parameters for psy-view

**Disclaimer**

Copyright (C) 2020 Philipp S. Sommer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see https://www.gnu.org/licenses/.
"""
from __future__ import annotations
from typing import (
    Dict,
    List,
    Any,
    Optional,
)

from psyplot_gui.config.rcsetup import (
    RcParams, validate_stringlist, psyplot_fname)
from psyplot.config.rcsetup import validate_dict


defaultParams: Dict[str, List[Any]] = {
    "projections": [
        ["cf", "cyl", "robin", "ortho", "moll"], validate_stringlist,
        "The names of available projections"],
    "savefig_kws": [
        dict(dpi=250), validate_dict,
        "Options that are passed to plt.savefig when exporting images"],
    "animations.export_kws": [
        dict(writer="ffmpeg"), validate_dict,
        "Options that are passed to FuncAnimation.save"],
    }


class PsyViewRcParams(RcParams):
    """RcParams for the psyplot-gui package."""

    HEADER: str = RcParams.HEADER.replace(
        'psyplotrc.yml', 'psyviewrc.yml').replace(
            'PSYVIEWRC', 'psyviewrc.yml')

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
        fname = fname or psyplot_fname(env_key='PSYVIEWRC',
                                       fname='psyviewrc.yml')
        if fname:
            super().load_from_file(fname)


rcParams = PsyViewRcParams(defaultParams=defaultParams)
rcParams.update_from_defaultParams()
rcParams.load_from_file()
