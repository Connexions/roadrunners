# -*- coding: utf-8 -*-
"""\
Common utilities used in the rbit extensions.

Author: Michael Mulich
Copyright (c) 2013 Rice University

This software is subject to the provisions of the GNU Lesser General
Public License Version 2.1 (LGPL).  See LICENSE.txt for details.
"""
import os
import logging
import subprocess


logger = logging.getLogger('rbit-ext')

def get_completezip(pkg_name, version, base_uri, working_dir):
    """"Acquire the collection data from a (Plone based) Connexions
    repository in the completezip format.

    An assumption is made that the working_dir is empty. This is so that
    the unpacked contents can be discovered.

    """
    filename = "{0}-{1}.complete.zip".format(pkg_name, version)
    url = '{0}/content/{1}/{2}/complete'.format(base_uri, pkg_name, version)

    # Download the completezip
    command = ['wget', '-O', filename, url]
    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=working_dir)
    logger.debug("Running: " + ' '.join(command))
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise RuntimeError(stdout + "\n\n" + stderr)

    # Unpack the zip
    command = ['unzip', filename]
    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=working_dir)
    logger.debug("Running: " + ' '.join(command))
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise RuntimeError(stdout + "\n\n" + stderr)

    # The unpacked directory name does not always match the zip file
    #   name. In addition, the version may differ if 'latest' is used.
    #   Therefore, we must discover the name by looking at the
    #   contents of the directory. This is simple enough, because
    #   there should only ever be two items in the directory at this
    #   time.
    unpacked_filename = [d for d in os.listdir(working_dir)
                         if not d.endswith('.zip')][0]
    return unpacked_filename
