# -*- coding: utf-8 -*-
# Copyright 2018-2020 The pyXem developers
#
# This file is part of orix.
#
# orix is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# orix is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with orix.  If not, see <http://www.gnu.org/licenses/>.

import logging
import warnings

import numpy as np
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.axes import Axes
from matplotlib.projections import register_projection
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

from orix.scalar import Scalar
from orix.vector import Vector3d

_log = logging.getLogger(__name__)


class CrystalMapPlot(Axes):
    """A base class for 2D plotting of CrystalMap objects.

    Attributes
    ----------
    name : str
        Matplotlib projection name.

    Methods
    -------
    plot_map(
        crystal_map, value=None, scalebar=True, scalebar_properties=None,
        legend=True, legend_properties=None, **kwargs)
        Plot a 2D map with any CrystalMap attribute as map values.
    add_scalebar(crystal_map, **kwargs)
        Add a scalebar to the axes object via `AnchoredSizeBar`.
    add_overlay(crystal_map, item)
        Use a crystal map property as gray scale values of a phase map.
    add_colorbar(title=None, **kwargs)
        Add an opinionated colorbar to the figure.
    remove_padding()
        Remove all white padding outside of the figure.
    """

    name = "plot_map"

    def plot_map(
        self,
        crystal_map,
        value=None,
        scalebar=True,
        scalebar_properties=None,
        legend=True,
        legend_properties=None,
        **kwargs,
    ):
        """Plot a 2D map with any CrystalMap attribute as map values.

        Wraps :meth:`matplotlib.axes.Axes.imshow`, see that method for
        relevant keyword arguments.

        Parameters
        ----------
        crystal_map : orix.crystal_map.CrystalMap
            Crystal map object to obtain data to plot from.
        value : numpy.ndarray, optional
            Attribute array to plot. If value is ``None`` (default), a
            phase map is plotted.
        scalebar : bool, optional
            Whether to add a scalebar (default is ``True``) along the
            horizontal map dimension.
        scalebar_properties : dict
            Dictionary of keyword arguments passed to
            :func:`mpl_toolkits.axes_grid1.anchored_artists.AnchoredSizeBar`.
        legend : bool, optional
            Whether to add a legend to the plot. This is only implemented for
            a phase plot (in which case default is ``True``).
        legend_properties : dict
            Dictionary of keyword arguments passed to
            :meth:`matplotlib.axes.legend`.
        kwargs :
            Keyword arguments passed to
            :meth:`matplotlib.axes.Axes.imshow`.

        Returns
        -------
        im : matplotlib.image.AxesImage
            Image object, to be used further to get data from etc.

        See Also
        --------
        matplotlib.axes.Axes.imshow
        orix.plot.CrystalMapPlot.add_scalebar
        orix.plot.CrystalMapPlot.add_overlay
        orix.plot.CrystalMapPlot.add_colorbar

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> import numpy as np
        >>> from orix import plot
        >>> from orix.io import load_ang

        Import a crystal map and inspect it

        >>> cm = load_ang("/some/directory/data.ang")
        >>> cm
        Phase  Orientations   Name       Symmetry  Color
        1      5657 (48.4%)   austenite  432       tab:blue
        2      6043 (51.6%)   ferrite    432       tab:orange
        Properties: iq, dp
        Scan unit: um

        Plot a phase map

        >>> fig = plt.figure()  # Get figure
        >>> ax = fig.add_subplot(projection="plot_map")  # Get axes
        >>> im = ax.plot_map(cm)  # Get image

        Add an overlay

        >>> ax.add_overlay(cm, cm.iq)

        Plot an arbitrary map property, also changing scalebar location

        >>> ax = plt.subplot(projection="plot_map")
        >>> ax.plot_map(
        ...     cm, cm.dp, cmap="cividis", scalebar_properties={"loc": 4})

        Add a colorbar

        >>> cbar = ax.add_colorbar("Dot product")

        Plot orientation angle in degrees of one phase

        >>> cm2 = cm["austenite"]
        >>> austenite_angles = cm2.orientations.angle.data * 180 / np.pi
        >>> fig = plt.figure()
        >>> ax = fig.add_subplot(projection="plot_map")
        >>> im = ax.plot_map(cm2, austenite_angles)
        >>> ax.add_colorbar("Orientation angle [$^{\circ}$]")

        Remove all figure and axes padding

        >>> ax.remove_padding()

        Write annotated figure to file

        >>> fig.savefig(
        ...     "/some/directory/image.png",
        ...     pad_inches=0,
        ...     bbox_inches="tight"
        ...)

        Write un-annotated image to file

        >>> plt.imsave("/some/directory/image2.png", im.get_array())

        """
        patches = None
        if value is None:  # Phase map
            _log.debug("plot_map: Plot a phase map")

            # Color each map pixel with corresponding phase color RGB tuple
            phase_id = crystal_map.get_map_data("phase_id")
            unique_phase_ids = np.unique(phase_id[~np.isnan(phase_id)])
            data = np.ones(phase_id.shape + (3,))
            for i, color in zip(
                unique_phase_ids, crystal_map.phases_in_data.colors_rgb
            ):
                mask = phase_id == int(i)
                data[mask] = data[mask] * color

            # Add legend patches to plot
            patches = []
            for _, p in crystal_map.phases_in_data:
                patches.append(mpatches.Patch(color=p.color_rgb, label=p.name))
        else:  # Create masked array of correct shape
            if isinstance(value, Scalar) or isinstance(value, Vector3d):
                _log.debug(f"plot_map: Plot {type(value)} attribute data")
                value = value.data
            data = crystal_map.get_map_data(value)

        # Legend
        if legend and isinstance(patches, list):
            if legend_properties is None:
                legend_properties = {}
            self._add_legend(patches, **legend_properties)

        # Scalebar
        if scalebar:
            if scalebar_properties is None:
                scalebar_properties = {}
            _ = self.add_scalebar(crystal_map, **scalebar_properties)

        im = self.imshow(X=data, **kwargs)
        im = self._override_status_bar(im, crystal_map)

        return im

    def add_scalebar(self, crystal_map, **kwargs):
        """Add a scalebar to the axes object via `AnchoredSizeBar`.

        To find an appropriate scalebar width, this snippet from MTEX
        [Bachmann2010]_ written by Eric Payton and Philippe Pinard is used:
        https://github.com/mtex-toolbox/mtex/blob/b8fc167d06d453a2b3e212b1ac383acbf85a5a27/plotting/scaleBar.m,

        Parameters
        ----------
        crystal_map : orix.crystal_map.CrystalMap
            Crystal map object to obtain necessary data from.
        **kwargs : dict
            Keyword arguments passed to
            :func:`mpl_toolkits.axes_grid1.anchored_artists.AnchoredSizeBar`.

        Returns
        -------
        bar : mpl_toolkits.axes_grid1.anchored_artists.AnchoredSizeBar
            Scalebar.

        Examples
        --------
        >>> cm
        Phase  Orientations   Name       Symmetry  Color
        1      5657 (48.4%)   austenite  432       tab:blue
        2      6043 (51.6%)   ferrite    432       tab:orange
        Properties: iq, dp
        Scan unit: um

        Create a phase map without a scale bar and add it afterwards

        >>> fig = plt.figure()
        >>> ax = fig.add_subplot(projection="plot_map")
        >>> im = ax.plot_map(cm, scalebar=False)
        >>> sbar = ax.add_scalebar(cm, loc=4, frameon=False)
        """
        map_width = crystal_map.shape[-1]
        # TODO: Make this "dynamic"/dependable when enabling specimen reference frame
        step_size = crystal_map._step_sizes["x"]
        scan_unit = crystal_map.scan_unit

        # Initial scalebar width should be approximately 1/10 of map width
        scalebar_width = 0.1 * map_width * step_size

        # Ensure a suitable number is used, e.g. going from 1000 nm to 1 um
        scalebar_width, scan_unit, factor = convert_unit(scalebar_width, scan_unit)

        # This snippet for finding a suitable scalebar width is taken from MTEX:
        # https://github.com/mtex-toolbox/mtex/blob/b8fc167d06d453a2b3e212b1ac383acbf85a5a27/plotting/scaleBar.m,
        # written by Eric Payton and Philippe Pinard. We want a round, not too high
        # number without decimals
        good_values = np.array(
            [1, 2, 5, 10, 15, 20, 25, 50, 75, 100, 125, 150, 200, 500, 750], dtype=int,
        )
        # Find good data closest to initial scalebar width
        difference = abs(scalebar_width - good_values)
        good_value_idx = np.where(difference == difference.min())[0][0]
        scalebar_width = good_values[good_value_idx]

        # Scale width by factor from above conversion (usually factor = 1.0)
        scalebar_width = scalebar_width * factor
        scalebar_width_px = scalebar_width / step_size

        # Allow for a potential decimal in scalebar number if something didn't go as
        # planned
        if scalebar_width.is_integer():
            scalebar_width = int(scalebar_width)
        else:
            warnings.warn(f"Scalebar width {scalebar_width} is not an integer.")

        if scan_unit == "um":
            scan_unit = "\u03BC" + "m"

        # Set up arguments to AnchoredSizeBar() if not already present in kwargs
        d = {
            "loc": 3,
            "pad": 0.2,
            "sep": 3,
            "frameon": True,
            "borderpad": 0.5,
            "size_vertical": scalebar_width_px / 12,
            "fontproperties": fm.FontProperties(size=11),
        }
        [kwargs.setdefault(k, v) for k, v in d.items()]

        # Create scalebar
        bar = AnchoredSizeBar(
            transform=self.axes.transData,
            size=scalebar_width_px,
            label=str(scalebar_width) + " " + scan_unit,
            **kwargs,
        )
        bar.patch.set_alpha(0.6)

        self.axes.add_artist(bar)
        _log.debug(f"add_scalebar: To {self.axes}")

        return bar

    def add_overlay(self, crystal_map, item):
        """Use a crystal map property as gray scale values of a phase map.

        The property's range is adjusted to [0, 1] for maximum contrast.

        Parameters
        ----------
        crystal_map : orix.crystal_map.CrystalMap
            Crystal map object to obtain necessary data from.
        item : str
            Name of map property to scale phase array with. The property
            range is adjusted for maximum contrast.

        Examples
        --------
        >>> cm
        Phase  Orientations   Name       Symmetry  Color
        1      5657 (48.4%)   austenite  432       tab:blue
        2      6043 (51.6%)   ferrite    432       tab:orange
        Properties: iq, dp
        Scan unit: um

        Plot a phase map with a map property as overlay

        >>> fig = plt.figure()
        >>> ax = fig.add_subplot(projection="plot_map")
        >>> im = ax.plot_map(cm)
        >>> ax.add_overlay(cm, cm.dp)
        """
        image = self.images[0]
        image_data = image.get_array()

        if image_data.ndim < 3:
            # Adding overlay to a scalar plot (should this be allowed?)
            image_data = image.to_rgba(image_data)[:, :, :3]  # No alpha

        # Scale prop to [0, 1] to maximize image contrast
        overlay = crystal_map.get_map_data(item)
        overlay_min = np.nanmin(overlay)
        rescaled_overlay = (overlay - overlay_min) / (np.nanmax(overlay) - overlay_min)

        n_channels = 3
        for i in range(n_channels):
            image_data[:, :, i] *= rescaled_overlay

        _log.debug(f"add_overlay: To {image}")
        image.set_data(image_data)

    def add_colorbar(self, title=None, **kwargs):
        """Add an opinionated colorbar to the figure.

        Parameters
        ----------
        title : str, optional
            Colorbar title, default is ``None``.
        kwargs :
            Keyword arguments passed to
            :meth:`mpl_toolkits.axes_grid1.make_axes_locatable.append_axes`.

        Returns
        -------
        cbar : matplotlib.colorbar
            Colorbar.

        Examples
        --------
        >>> cm
        Phase  Orientations   Name       Symmetry  Color
        1      5657 (48.4%)   austenite  432       tab:blue
        2      6043 (51.6%)   ferrite    432       tab:orange
        Properties: iq, dp
        Scan unit: um

        Plot a map property and add a colorbar

        >>> fig = plt.figure()
        >>> ax = fig.add_subplot(projection="plot_map")
        >>> im = ax.plot_map(cm, cm.dp, cmap="inferno")
        >>> cbar = ax.add_colorbar("Dot product")

        If the default options are not satisfactory, the colorbar can be
        updated

        >>> cbar.ax.set_ylabel(title="dp", rotation=90)
        """
        # Keyword arguments
        d = {"position": "right", "size": "5%", "pad": 0.1}
        [kwargs.setdefault(k, v) for k, v in d.items()]

        # Add colorbar
        divider = make_axes_locatable(self)
        cax = divider.append_axes(**kwargs)
        _log.debug(f"add_colorbar: To {self.figure}")
        cbar = self.figure.colorbar(self.images[0], cax=cax)

        # Set title with padding
        cbar.ax.get_yaxis().labelpad = 15
        cbar.ax.set_ylabel(title, rotation=270)

        return cbar

    def remove_padding(self):
        """Remove all white padding outside of the figure.

        Examples
        --------
        >>> cm
        Phase  Orientations   Name       Symmetry  Color
        1      5657 (48.4%)   austenite  432       tab:blue
        2      6043 (51.6%)   ferrite    432       tab:orange
        Properties: iq, dp
        Scan unit: um

        Remove all figure and axes padding of a phase map

        >>> fig = plt.figure()
        >>> ax = fig.add_subplot(projection="plot_map")
        >>> ax.plot_map(cm)
        >>> ax.remove_padding()
        """
        self.set_axis_off()
        self.margins(0, 0)

        # Tune subplot layout
        colorbar = self.images[0].colorbar
        if colorbar is not None:
            right = self.figure.subplotpars.right
        else:
            right = 1
        _log.debug(f"remove_padding: From {self.figure}")
        self.figure.subplots_adjust(top=1, bottom=0, right=right, left=0)

    def _add_legend(self, patches, **kwargs):
        """Add a legend to the axes object.

        Parameters
        ----------
        patches : list of matplotlib.patches.Patch
            Patches with color code and name.
        **kwargs :
            Keyword arguments passed to :meth:`matplotlib.axes.legend`.
        """
        d = {
            "borderpad": 0.3,
            "handlelength": 0.75,
            "handletextpad": 0.3,
            "framealpha": 0.6,
            "prop": fm.FontProperties(size=11),
        }
        [kwargs.setdefault(k, v) for k, v in d.items()]
        _log.debug(f"add_legend: To {self.axes}")
        self.legend(handles=patches, **kwargs)

    def _override_status_bar(self, image, crystal_map):
        """Display coordinates, a property value (if scalar values are
        plotted), and Euler angles (in radians) per data point in the
        status bar.

        This is done by overriding
        :meth:`matplotlib.images.AxesImage.get_cursor_data`,
        :meth:`matplotlib.images.AxesImage.format_cursor_data` and
        :meth:`matplotlib.axes.Axes.format_coord`.

        Parameters
        ----------
        image : matplotlib.images.AxesImage
            Image object.
        crystal_map : orix.crystal_map.CrystalMap
            Crystal map object to obtain necessary data from.

        Returns
        -------
        image : matplotlib.images.AxesImage
            Image object where the above mentioned methods are overridden.
        """

        # Get map shape
        map_shape = crystal_map._original_shape
        n_rows, n_cols = map_shape

        # Get rotations, ensuring correct masking
        # TODO: Show orientations in Euler angles (computationally intensive...)
        r = crystal_map.get_map_data("rotations", decimals=3)

        # Get image data, overwriting potentially masked regions set to 0.0
        image_data = image.get_array()  # numpy.masked.MaskedArray
        image_data[image_data.mask] = np.nan

        def status_bar_data(event):
            col = int(event.xdata + 0.5)
            row = int(event.ydata + 0.5)
            return row, col, r[row, col], image_data[row, col]

        # Set width of status bar fields
        x_width = len(str(n_cols - 1))
        y_width = len(str(n_rows - 1))
        scalar_width = len(str(np.nanmax(image_data)))

        # Override
        image.get_cursor_data = status_bar_data
        self.axes.format_coord = lambda x, y: ""

        def format_status_bar_data_rgb(data):
            """Status bar format for RGB plots."""
            return (
                f"(y,x):({data[0]:{y_width}},{data[1]:{x_width}})"
                f" rot:({data[2][0]:5},{data[2][1]:5},{data[2][2]:5})"
            )

        def format_status_bar_data_scalar(data):
            """Status bar format for scalar plots."""
            return (
                f"(y,x):({data[0]:{y_width}},{data[1]:{x_width}})"
                f" val:{data[3]:{scalar_width}}"
                f" rot:({data[2][0]:5},{data[2][1]:5},{data[2][2]:5})"
            )

        # Pick status bar format and override this as well
        if image_data.shape[-1] == 3:
            image.format_cursor_data = format_status_bar_data_rgb
        else:
            image.format_cursor_data = format_status_bar_data_scalar

        _log.debug(f"override_status_bar: Of {self.axes}")
        return image


register_projection(CrystalMapPlot)


def convert_unit(value, unit):
    """Return the data with a suitable, not too large, unit.

    This algorithm is taken directly from MTEX [Bachmann2010]_
    https://github.com/mtex-toolbox/mtex/blob/a74545383160610796b9525eedf50a241800ffae/plotting/plotting_tools/switchUnit.m,
    written by Ralf Hielscher.

    Parameters
    ----------
    value : float
        The data to convert.
    unit : str
        The data unit, e.g. um.

    Returns
    -------
    new_value : float
        The input data converted to the suitable unit.
    new_unit : str
        A more suitable unit than the input.
    factor : float
        Factor to multiple `new_value` with to get the input data.

    Examples
    --------
    >>> convert_unit(17.55 * 1e3, 'nm')
    17.55 um 999.9999999999999
    >>> convert_unit(17.55 * 1e-3, 'mm')
    17.55 um 0.001
    """
    # If unit is 'px', we assume 'um', and revert unit in the end
    unit_is_px = False
    if unit == "px":
        unit = "um"
        unit_is_px = True

    # Create lookup-table with units and power
    lookup_table = []
    letters = "yzafpnum kMGTPEZY"
    new_unit_idx = None
    for i, letter in enumerate(letters):
        # Ensure 'm' is entered correctly
        current_unit = (letter + "m").strip(" ")
        lookup_table.append((current_unit, 10 ** (3 * i - 24)))
        if unit == current_unit:
            new_unit_idx = i

    # Find the lookup-table index of the most suitable unit
    value_in_metres = value * lookup_table[new_unit_idx][1]
    power_of_value = np.floor(np.log10(value_in_metres))
    suitable_unit_idx = int(np.floor(power_of_value / 3) + 8)

    # Calculate new data, unit and the conversion factor
    new_value = value_in_metres / lookup_table[suitable_unit_idx][1]
    new_unit = lookup_table[suitable_unit_idx][0]
    factor = lookup_table[suitable_unit_idx][1] / lookup_table[new_unit_idx][1]

    if unit_is_px:
        new_unit = "px"

    _log.debug(
        f"convert_unit: From {value} {unit} to {new_value} {new_unit} with factor "
        f"{factor}"
    )
    return new_value, new_unit, factor
