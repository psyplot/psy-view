.. _psy-view-vs-ncview:

psy-view vs. ncview
===================
When developping *psy-view*, we had the intuitiveness of ncview_ in mind, a 
light-weight graphical user interface to visualize the contents of netCDF files.

In general, `psy-view` can do everything that `ncview` does, and more.

.. image:: _static/ncview.png
    :alt: ncview screenshot
    :target: http://meteora.ucsd.edu/~pierce/ncview_home_page.html

.. _ncview: http://meteora.ucsd.edu/~pierce/ncview_home_page.html

The following table tries to summarize the differences of the features for both
softwares. If you feel like anything is missing or wrong, please tell us by 
creating a new issue at https://github.com/psyplot/psy-view/issues/

.. list-table:: psy-view vs. ncview
    :stub-columns: 1
    :header-rows: 1
    :widths: 2 4 2

    * - Feature
      - psy-view
      - ncview
    * - supported grids
      - 
          * rectilinear (i.e. standard :math:`nx\times ny` grid)
          * ICON_ (triangular, hexagonal, etc.)
          * UGRID_ (triangular, hexagonal, etc.)
      - rectilinear
    * - supported plots
      - 
          * georeferenced plots
          * standard 2D-plots
          * line plots
      - 
          * georeferenced plots
          * standard 2D-plots
          * line plots
    * - mouse features
      - 
          * plot a time series when clicking on a plot 
          * show coordinates and data when hovering the plot
      - 
          * plot a time series when clicking on a plot 
          * show coordinates and data when hovering the plot
    * - View the data
      - not yet implemented
      - comes with a simple and basic editor
    * - image export
      - all common formats (e.g.
        :abbr:`PDF (Portable Document Format)`, 
        :abbr:`PNG (Portable Network Graphics)`, 
        :abbr:`GIF (Graphics Interchange Format)`, etc.) with high resolution
      - :abbr:`PS (PostScript)`
    * - animation export
      - GIF, MP4 (using ffmpeg or imagemagick)
        
        .. note::

            This is a beta feature

      - not implemented
    * - :abbr:`GUI (Graphical User Interface`) startup time
      - fast locally, slow via X11
      - fast
    * - projection support
      - 
          * decodes CF-conformal grid_mapping_ attributes
          * flexibly choose the `projection of the plot via cartopy`_
      - 
          * decodes CF-conformal grid_mapping_ attributes
          * plots on standard lat-lon projection only
    * - supported files
      - anything that is supported by xarray (netCDF, GRIB, GeoTIFF, etc.)

        .. todo::

            add more documentation for supported file types
      - netCDF files only
    * - Language
      - Entirely written in Python with the use of

        * xarray_
        * matplotlib_
        * PyQt5_
        * cartopy_
      - Entirely written in C
    * - Extensibility
      - psy-view is built upon psyplot, so you can

        * export the plot settings
        * use it in python scripts
        * use the more general `psyplot GUI`_
      - cannot be extended


.. _grid_mapping: http://cfconventions.org/Data/cf-conventions/cf-conventions-1.8/cf-conventions.html#appendix-grid-mappings
.. _projection of the plot via cartopy: https://scitools.org.uk/cartopy/docs/latest/crs/projections.html
.. _xarray: http://xarray.pydata.org/en/stable/
.. _matplotlib: https://matplotlib.org/
.. _PyQt5: https://riverbankcomputing.com/software/pyqt
.. _cartopy: https://scitools.org.uk/cartopy/docs/latest
.. _psyplot GUI: https://psyplot.readthedocs.io/projects/psyplot-gui/en/latest/
.. _ICON: https://mpimet.mpg.de/en/communication/news/focus-on-overview/icon-development
.. _UGRID: http://ugrid-conventions.github.io/ugrid-conventions/
