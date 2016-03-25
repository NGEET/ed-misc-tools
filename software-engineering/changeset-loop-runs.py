#!/usr/bin/env python
"""Tool to consistently run a case in several different version of
ed-clm. Inspired by 'git bisect', but manually selects changeset ids
inorder to automate the case creation and running.

* loop over a series of git commit changeset ids
* clone the ed-clm repo
* create a case from a template
* build
* run a case. 

FIXME(bja, 201603) there is a bunch of hard coded info that can easily
be moved into a configuration file to make this more generic.

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
import subprocess
from string import Template
import traceback

if sys.version_info[0] == 2:
    from ConfigParser import SafeConfigParser as config_parser
else:
    from configparser import ConfigParser as config_parser

#
# installed dependencies
#

#
# other modules in this package
#

#
# globals
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
        description='clone a series of git changes into separate repos and '
                    'run an ed-clm case in each.')

    parser.add_argument('--backtrace', action='store_true',
                        help='show exception backtraces as extra debugging '
                        'output')

    parser.add_argument('--debug', action='store_true',
                        help='extra debugging output')

    parser.add_argument('--config', nargs=1,
                        help='path to config file')

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


# -------------------------------------------------------------------------------
#
# work functions
#
# -------------------------------------------------------------------------------
def generate_id(changset_id):
    """
    """
    casename = 'ed-clm-i24-{0}'.format(changset_id)
    return casename


def create_case(case_name, logfile):
    """
    """
    newcase = Template("""
./create_newcase -case ${case_name} -res ${res} -compset ${compset} -mach ${mach}
    """)

    run_info = {'case_name': case_name,
                'res': '4x5_4x5',
                'compset': 'ICLM45ED',
                'mach': 'yellowstone',
    }
    case = newcase.substitute(run_info)
    cmd = case.split()
    print(cmd)
    output = subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)
    logfile.write(output)

    os.chdir(case_name)
    commands = [
        "./xmlchange -file env_run.xml -id STOP_OPTION -val nmonths",
        "./xmlchange -file env_run.xml -id STOP_N -val 1",
        "./xmlchange DOUT_S=FALSE",
        "./xmlchange -file env_run.xml -id CLM_BLDNML_OPTS -val \'-no-megan\' --append",
        "./cesm_setup",
        "./{0}.build".format(case_name),
        "./{0}.submit".format(case_name),
    ]

    for my_cmd in commands:
        cmd = my_cmd.split()
        print(cmd)
        output = subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)
        logfile.write(output)




# -------------------------------------------------------------------------------
#
# git wrapper functions
#
# -------------------------------------------------------------------------------
def clone_ref_repo(repo_dir, temp_repo_dir):
    """Clone the existing git repo.

    NOTE: assumes a fixed directory structure. If this script is
    executed from directory 'work', then work/ed-clm-git is the main git
    repo to pull new src into.

    """
    print("Cloning git repo at : {0} to {1}".format(repo_dir, temp_repo_dir))
    cmd = [
        "git",
        "clone",
        repo_dir,
        temp_repo_dir,
    ]
    subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)


def checkout_git_branch(changeset_id, branch_name):
    """checkout the specified changset
    """
    cmd = [
        "git",
        "checkout",
        "-b",
        branch_name,
        changeset_id
    ]
    subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)


     

# -------------------------------------------------------------------------------
#
# main
#
# -------------------------------------------------------------------------------

def main(options):
    #config = read_config_file(options.config[0])
    cwd = os.getcwd()

    ref_git_repo = 'ed-clm'
    repo_dir = os.path.abspath("{0}/{1}".format(cwd, ref_git_repo))

    changeset_ids = [
        '19fe5678',
        '8740a1a3',
        '90c37589',
        'c3a1f922',
        '2d3e7c59',
        '69a361b0',
        'eb26be69',
        'eff944c0',
        '3a8f2d85',
        '5dd2f23e',
    ]

    with open('i24.log', 'w') as logfile:
        for changeset in changeset_ids:
            os.chdir(cwd)
            run_id = generate_id(changeset)
            temp_repo_dir = "{0}/{1}".format(cwd, run_id)
            if os.path.isdir(temp_repo_dir):
                raise RuntimeError(
                    "ERROR: temporary git repo dir already exists:\n    {0}".format(temp_repo_dir))
            clone_ref_repo(repo_dir, temp_repo_dir)
            os.chdir(temp_repo_dir)
            checkout_git_branch(changeset, run_id)

            scripts_dir = "{0}/cime/scripts".format(temp_repo_dir)
            os.chdir(scripts_dir)
            create_case(run_id, logfile)

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
