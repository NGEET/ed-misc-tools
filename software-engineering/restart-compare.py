#!/usr/bin/env python
"""Tool to help analyze clm restarat problems. Compare history files
from a restart test, align the data and detect when the pre and post
restart data deviate.

Author: Ben Andre <andre@ucar.edu>

"""

from __future__ import print_function

import sys

if sys.hexversion < 0x02070000:
    print(70 * "*")
    print("ERROR: {0} requires python >= 2.7.x. ".format(sys.argv[0]))
    print("It appears that you are running python {0}".format(
        ".".join(str(x) for x in sys.version_info[0:3])))
    print(70 * "*")
    sys.exit(1)

#
# built-in modules
#
import argparse
import os
import traceback

if sys.version_info[0] == 2:
    from ConfigParser import SafeConfigParser as config_parser
else:
    from configparser import ConfigParser as config_parser

#
# installed dependencies
#
import numpy as np
import scipy.io.netcdf as netcdf
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap

#
# other modules in this package
#

# -------------------------------------------------------------------------------
#
# User input
#
# -------------------------------------------------------------------------------

def commandline_options():
    """Process the command line arguments.

    """
    parser = argparse.ArgumentParser(
        description='tool to help analyze clm restart problems.')

    parser.add_argument('--backtrace', action='store_true',
                        help='show exception backtraces as extra debugging '
                        'output')

    parser.add_argument('--debug', action='store_true',
                        help='extra debugging output')

    # parser.add_argument('--config', nargs=1, required=True,
    #                     help='path to config file')

    parser.add_argument('--base-file', nargs=1, required=True,
                        help='path to config baseline history file')

    parser.add_argument('--restart-file', nargs=1, required=True,
                        help='path to restart history file')

    options = parser.parse_args()
    return options


def read_config_file(filename):
    """Read the configuration file and process

    """
    print("Reading configuration file : {0}".format(filename))

    cfg_file = os.path.abspath(filename)
    if not os.path.isfile(cfg_file):
        raise RuntimeError("Could not find config file: {0}".format(cfg_file))

    config = config_parser()
    config.read(cfg_file)

    return config


def open_netcdf(filename):
    """
    """
    print('Reading netcdf file :\n   {0}'.format(filename))
    return netcdf.netcdf_file(filename, 'r')


# -------------------------------------------------------------------------------
#
# worker functions
#
# -------------------------------------------------------------------------------
def diff_dict(a, b, compare_values):
    """Return the difference between two dictionaries
    """
    a_not_b = []
    b_not_a = []
    different = {}
    for key in a:
        if key in b:
            if compare_values and a[key] != b[key]:
                different[key] = (a[key], b[key])
        else:
            # key in a, not b
            a_not_b.append(key)

    for key in b:
        if key not in a:
            # key in b, not a
            b_not_a.append(key)

    diff = {}
    if a_not_b:
        diff['a_not_b'] = a_not_b
    if b_not_a:
        diff['b_not_a'] = b_not_a
    if different:
        diff['different'] = different

    return diff


def check_stuff(name, base, rest, compare_values=True):
    """
    """
    diff = diff_dict(base, rest, compare_values)
    if diff:
        print('{0} of base and restart file differ:'.format(name))
        print(diff)


def sanity_check(base_file, restart_file):
    """basic sanity check of the files to ensure that dimensions are the
    same, the same variables are on the file, etc.

    """
    check_stuff('Dimensions', base_file.dimensions, restart_file.dimensions)
    check_stuff('Variables', base_file.variables, restart_file.variables,
                compare_values=False)


def get_time_vars(base_file):
    """
    """
    time_vars = []
    for var in base_file.variables:
        if 'time' in base_file.variables[var].dimensions:
            time_vars.append(var)
    return time_vars


def compare_variables(variables, base_file, restart_file):
    """
    """
    times = base_file.variables['time'].data
    lat = base_file.variables['lat'].data
    lon = base_file.variables['lon'].data
    for var in variables:
        base = base_file.variables[var].data
        rest = restart_file.variables[var].data
        if not np.array_equal(base, rest):
            print('{0} differs. dims = {1}'.format(
                var, base_file.variables[var].dimensions))
            for index, time in enumerate(times):
                base_data = base[index]
                rest_data = rest[index]
                if not np.array_equal(base_data, rest_data):
                    print('{0} differs at time = {1}'.format(var, time))
                    if len(base_file.variables[var].dimensions) == 3:
                        title = '{0} t[{1}] = {2}'.format(var, index, time)
                        diff = base_data - rest_data
                        diff_points = np.where(diff != 0)
                        diff_points = np.transpose(diff_points)
                        print('{0} differs at {1} points:'.format(var, len(diff_points)))
                        for point in diff_points:
                            print('{0} == ({1}, {2})'.format(point, lat[point[0]], lon[point[1]]))
                        plot_lat_lon(title, lat, lon, diff)


# -------------------------------------------------------------------------------
#
# plot
#
# -------------------------------------------------------------------------------
def plot_lat_lon(title, lats, lons, data):
    """
    """
    m = Basemap(projection='robin', lon_0=0.5*(lons[0]+lons[-1]))
    # compute map projection coordinates for lat/lon grid.
    x, y = m(*np.meshgrid(lons, lats))
    # make filled contour plot.
    cs = m.contourf(x, y, data, 30, cmap=plt.cm.jet)
    m.colorbar()
    m.drawcoastlines()
    m.drawmapboundary()
    m.drawparallels(np.arange(-90., 120., 30.), labels=[1, 0, 0, 0])
    m.drawmeridians(np.arange(0., 420., 60.), labels=[0, 0, 0, 1])
    plt.title(title)
    plt.show()

# -------------------------------------------------------------------------------
#
# main
#
# -------------------------------------------------------------------------------
def main(options):
    # config = read_config_file(options.config[0])
    base_file = open_netcdf(options.base_file[0])
    restart_file = open_netcdf(options.restart_file[0])

    sanity_check(base_file, restart_file)
    time_vars = get_time_vars(base_file)
    compare_variables(time_vars, base_file, restart_file)
    return 0


if __name__ == "__main__":
    options = commandline_options()
    try:
        status = main(options)
        sys.exit(status)
    except Exception as error:
        print(str(error))
        if options.backtrace:
            traceback.print_exc()
        sys.exit(1)
