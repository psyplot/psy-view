v0.2.0
======
Compatibility fixes and LGPL license

Fixed
-----
- psy-view is now compatible with psyplot 1.4.0

Changed
-------
- psy-view is now officially licensed under LGPL-3.0-only,
  see `#58 <https://github.com/psyplot/psy-view/pull/58>`__
- Documentation is now hosted with Github Pages at https://psyplot.github.io/psy-view.
  Redirects from the old documentation at `https://psy-view.readthedocs.io` have
  been configured.
- We use CicleCI now for a standardized CI/CD pipeline to build and test
  the code and docs all at one place, see `#57 <https://github.com/psyplot/psy-view/pull/57>`__


v0.1.0
======

Changed
-------
- The plotmethod tabs have now a more intuitive gridlayout (see
  `#46 <https://github.com/psyplot/psy-view/pull/46>`__)
- When closing the mainwindow of psy-view now, one closes all open windows (i.e.
  also the open figures, see
  `#47 <https://github.com/psyplot/psy-view/pull/47>`__)

Added
-----
- A widget to control the plot type for mapplot and plot2d (see
  `#46 <https://github.com/psyplot/psy-view/pull/46>`__)
- A button to reload all plots. This is useful, for instance, if the data on
  your disk changed and you just want to update the plot
  `#48 <https://github.com/psyplot/psy-view/pull/48>`__)
