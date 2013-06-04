# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""\
Common utilities used in the rbit extensions.

"""
import os
import logging
import subprocess
import requests

__all__ = ('logger', 'unpack_zip', 'get_completezip', 'get_offlinezip',)

logger = logging.getLogger('roadrunners')

def unpack_zip(file, working_dir=None):
    """Unpacks a zip file and returns the contents file path."""
    # Get a listing of the current directory if we are working in
    #   one. This is used later to differentiate the unpacked contents
    #   from those that were previously there.
    directory_listing = os.listdir(working_dir)

    command = ['unzip', '-n', file]
    if working_dir is not None:
        command.extend(['-d', working_dir])
    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=working_dir)
    logger.debug("Running: " + ' '.join(command))
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise RuntimeError(stdout + "\n\n" + stderr)

    return [x for x in os.listdir(working_dir) if x not in directory_listing]

def get_zip(pkg_name, version, base_uri, working_dir, unpack=True, zipname='complete'):
    """"Acquire the collection data from a (Plone based) Connexions
    repository in the completezip format.

    An assumption is made that the working_dir is empty. This is so that
    the unpacked contents can be discovered.

    """
    filename = "{0}-{1}.{2}.zip".format(pkg_name, version, zipname)
    url = '{0}/content/{1}/{2}/{3}'.format(base_uri, pkg_name, version, zipname)

    # Download the completezip
    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError("Could not download file at '{0}' with "
                           "response ({1}):\n{2}".format(url,
                                                         response.status_code,
                                                         response.text))
    filepath = os.path.join(working_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(response.content)

    if unpack is True:
        unpacked_file_list = unpack_zip(filename, working_dir)
        unpacked_filename = unpacked_file_list[0]
        return unpacked_filename
    else:
        return os.path.join(working_dir, filename)


def get_completezip(pkg_name, version, base_uri, working_dir, unpack=True, zipname='complete'):
    return get_zip(pkg_name, version, base_uri, working_dir, unpack, zipname)

def get_offlinezip(pkg_name, version, base_uri, working_dir, unpack=True, zipname='offline'):
    return get_zip(pkg_name, version, base_uri, working_dir, unpack, zipname)
