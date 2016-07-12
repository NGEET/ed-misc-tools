#!/usr/bin/env python
"""Tool to consistently run a case in several different versions of
ed-clm. Inspired by 'git bisect', but manually selects changeset ids
inorder to automate the case creation and running.

* loop over a series of git commit changeset ids
* clone the ed-clm repo
* create a case from a template
* build
* run a case.

The changeset ids and test commands are specified in a cfg/ini format
configuration file. Run this script with --write-template to generate
a template configuration file.

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
VERSION_CONTROL = 'version_control'
GIT_REF_REPO = 'git_ref_repo'
BRANCH_BASE = 'branch_base'
CHANGESET_IDS = 'changeset_ids'

BISECT_TEST = 'bisect_test'
BISECT_TYPE = 'type'
RUN_TEST = 'test'
RESOLUTION = 'resolution'
COMPSET = 'compset'
MACHINE = 'machine'
COMPILER = 'compiler'
TEST_MODS = 'test_mods'
TEST_COMMANDS = 'test_commands'



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

    parser.add_argument('--config', nargs=1,
                        help='path to config file')

    parser.add_argument('--debug', action='store_true',
                        help='extra debugging output')

    parser.add_argument('--dry-run', action='store_true',
                        help='just do a try run, don\' execute commands')

    parser.add_argument('--write-template', nargs='?',
                        const='template.cfg', default=None,
                        help='write a template config file')

    options = parser.parse_args()
    return options


def write_config_template(filename):
    """
    """
    print(filename)
    template = config_parser()
    section = VERSION_CONTROL
    template.add_section(section)
    template.set(section, GIT_REF_REPO, 'relative path to main repository')
    template.set(section, BRANCH_BASE,
                 '"base name of branch. changeset will be appended. '
                 'example foo-bar becomes foo-bar-ID."')
    template.set(section, CHANGESET_IDS, 'comma separeted list of '
                 'changeset ids')

    section = BISECT_TEST
    template.add_section(section)
    template.set(section, BISECT_TYPE, '"test" or "newcase"')
    template.set(section, RUN_TEST, 'only if "test" type, e.g. ERS_D_Ld3')
    template.set(section, RESOLUTION, 'e.g. f10_f10')
    template.set(section, COMPSET, 'e.g. ICLM50BGC')
    template.set(section, MACHINE, 'supported machine name')
    template.set(section, COMPILER, 'supported compiler name')
    template.set(section, TEST_MODS, 'only if "test" type, e.g. clm-default')
    template.set(section, TEST_COMMANDS, 'comma separated list of quoted strings with commands needed to run the test.')

    with open('{0}.cfg'.format(filename), 'wb') as configfile:
        template.write(configfile)


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
def generate_id(basename, changset_id):
    """
    """
    casename = '{0}-{1}'.format(basename, changset_id)
    return casename


def generate_newcase_command(config, case_name):
    """
    """
    newcase = Template("""
    ./create_newcase -case ${case_name} -res ${resolution} -compset ${compset} -mach ${machine} -compiler ${COMPILER}
    """)

    run_info = {'case_name': case_name,
                'resolution': config.get(BISECT_TEST, RESOLUTION),
                'compset': config.get(BISECT_TEST, COMPSET),
                'machine': config.get(BISECT_TEST, MACHINE),
                'compiler': config.get(BISECT_TEST, COMPILER),
    }
    case = newcase.substitute(run_info)
    cmd = case.split()
    return case_name, cmd


def generate_test_command(config, case_name):
    """
    """
    testname = Template("""${test_type}.${resolution}.${compset}.${machine}_${compiler}.${test_mods}""")

    newtest = Template("""
    ./create_test -testname ${testname} -testid ${case_name}
    """)

    run_info = {'case_name': case_name,
                'resolution': config.get(BISECT_TEST, RESOLUTION),
                'compset': config.get(BISECT_TEST, COMPSET),
                'machine': config.get(BISECT_TEST, MACHINE),
                'compiler': config.get(BISECT_TEST, COMPILER),
                'test_type': config.get(BISECT_TEST, RUN_TEST),
                'test_mods': config.get(BISECT_TEST, TEST_MODS)
    }
    name = testname.substitute(run_info)
    run_info['testname'] = name
    case = newtest.substitute(run_info)
    cmd = case.split()
    name = '{0}.{1}'.format(name, case_name)
    return name, cmd


def bisect_test(config, case_id, logfile, dry_run):
    """
    """
    if config.get(BISECT_TEST, BISECT_TYPE) == 'newcase':
        case_name, command = generate_newcase_command(config, case_id)
    else:
        case_name, command = generate_test_command(config, case_id)

    print(command)
    if not dry_run:
        output = subprocess.check_output(
            command, shell=False, stderr=subprocess.STDOUT)
        logfile.write(output)

    if not dry_run:
        os.chdir(case_name)

    commands = config.get(BISECT_TEST, TEST_COMMANDS)
    for my_cmd in commands.split():
        cmd = my_cmd.format(case_name=case_name)
        print(cmd)
        if not dry_run:
            output = subprocess.check_output(
                cmd, shell=False, stderr=subprocess.STDOUT)
            logfile.write(output)


# -------------------------------------------------------------------------------
#
# git wrapper functions
#
# -------------------------------------------------------------------------------
def clone_ref_repo(repo_dir, temp_repo_dir, dry_run):
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
    if not dry_run:
        subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)


def checkout_git_branch(changeset_id, branch_name, dry_run):
    """checkout the specified changset
    """
    cmd = [
        "git",
        "checkout",
        "-b",
        branch_name,
        changeset_id
    ]
    if not dry_run:
        subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)


# -------------------------------------------------------------------------------
#
# main
#
# -------------------------------------------------------------------------------
def main(options):
    if options.write_template:
        write_config_template(options.write_template)
        return 0

    dry_run = options.dry_run
    config = read_config_file(options.config[0])

    if not config.has_section('version_control'):
        raise RuntimeError('Configuration file must have a "version_control"'
                           ' section.')
    cwd = os.getcwd()
    ref_git_repo = config.get(VERSION_CONTROL, GIT_REF_REPO)
    repo_dir = os.path.abspath("{0}/{1}".format(cwd, ref_git_repo))

    changeset_ids = config.get(VERSION_CONTROL, CHANGESET_IDS).split()
    print(changeset_ids)

    log_filename = '{0}.log'.format(config.get(VERSION_CONTROL, BRANCH_BASE))
    with open(log_filename, 'w') as logfile:
        for changeset in changeset_ids:
            os.chdir(cwd)
            run_id = generate_id(config.get(VERSION_CONTROL, BRANCH_BASE),
                                 changeset)
            temp_repo_dir = "{0}/{1}".format(cwd, run_id)
            if os.path.isdir(temp_repo_dir):
                raise RuntimeError(
                    "ERROR: temporary git repo dir already exists:\n    {0}".format(temp_repo_dir))
            clone_ref_repo(repo_dir, temp_repo_dir, dry_run)
            if not dry_run:
                os.chdir(temp_repo_dir)
            checkout_git_branch(changeset, run_id, dry_run)

            scripts_dir = "{0}/cime/scripts".format(temp_repo_dir)
            if not dry_run:
                os.chdir(scripts_dir)
            bisect_test(config, run_id, logfile, dry_run)

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
