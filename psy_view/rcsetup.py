"""Configuration parameters for psy-view"""
from psyplot_gui.config.rcsetup import (
    RcParams, validate_stringlist, psyplot_fname)
from psyplot.config.rcsetup import validate_dict


defaultParams = {
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

    HEADER = RcParams.HEADER.replace(
        'psyplotrc.yml', 'psyviewrc.yml').replace(
            'PSYVIEWRC', 'psyviewrc.yml')

    def load_from_file(self, fname=None):
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
