# -*- coding: utf-8 -*-
"""\
rbit extensions for producing legacy files on the cnx plone repo codebase.

Author: Michael Mulich
Copyright (c) 2012 Rice University

This software is subject to the provisions of the GNU Lesser General
Public License Version 2.1 (LGPL).  See LICENSE.txt for details.
"""
import os
import sys
import tempfile
import traceback
import subprocess
import shutil
import jsonpickle
import requests

import rbit
from .utils import logger, get_completezip, unpack_zip


def make_completezip(build_request, settings={}):
    """\
    Creates a completezip by calling the (plone based) repository.

    Available settings:

    - **output-dir** - Directory where the produced file is stuck.
    - **username** - Self explanitory
    - **password** - Self explanitory
    - **path-to-content** - Useful for communication without a web server
      in front of zope. (default: /content)

    """
    output_dir = settings['output-dir']
    username = settings['username']
    password = settings['password']
    content_path = settings.get('path-to-content', '/content')
    content_path = content_path.rstrip('/')

    # Acquire the collection's data in a collection directory format.
    id = build_request.get_package()
    version = build_request.get_version()
    # This should be something like 'http://cnx.org:80'.
    base_uri = build_request.transport.uri.rstrip('/')

    # Make a request to the repository to create the completezip.
    url = "{0}{1}/{2}/{3}/create_complete".format(base_uri, content_path,
                                                  id, version)
    try:
        resp = requests.get(url, auth=(username, password))
    except requests.exceptions.ConnectionError as exc:
        raise rbit.Failed("Issue connecting to the depend service at "
                          "{0}".format(url))

    if resp.status_code != 200:
        raise rbit.Failed(resp)

    # Write out the results to the filesystem.
    result_filename = "{0}-{1}.complete.zip".format(id, version)
    output_filepath = os.path.join(output_dir, result_filename)
    with open(output_filepath, 'wb') as f:
        f.write(resp.content)

    return [output_filepath]


def make_offlinezip(build_request, settings={}):
    """\
    Creates an offlinezip using the complete zip (dependency).

    Available settings:

    - **output-dir** - Directory where the produced file is stuck.
    - **oer.exports-dir** - Defines the location of the oer.exports package.
    - **cnx-buildout-dir** - Defines the location of cnx-buildout.
    - **python-env** - Defines a virtual-env directory to activate for this
      legacy stuff.

    Dependencies:

    - Requires an active virtual environment or that the python dependencies
      have been met by the system python.
    - Requires a copy of oer.exports and cnx-buildout, both of which have
      scripts in them that this will utilize.

    """
    output_dir = settings['output-dir']
    oerexports_dir = settings['oer.exports-dir']
    cnxbuildout_dir = settings['cnx-buildout-dir']
    python_env = settings.get('python-env', None)

    # Acquire the collection's data in a collection directory format.
    id = build_request.get_package()
    version = build_request.get_version()
    # This should be something like 'http://cnx.org:80'.
    base_uri = build_request.transport.uri.rstrip('/')

    # Create a temporary directory to work in...
    build_dir = tempfile.mkdtemp()
    logger.debug("Working in '{0}'.".format(build_dir))

    # Acquire the completezip file for use in the build. The
    #   completezip could be in the output directory. If it's not
    #   there we will need to download it from the host repository.
    completezip_filename = '{0}-{1}.complete.zip'.format(id, version)
    completezip_filepath = os.path.join(output_dir, completezip_filename)
    if not os.path.exists(completezip_filepath):
        # Looks like we will need to download the file...
        try:
            completezip_filepath = get_completezip(id, version,
                                                   base_uri, build_dir,
                                                   unpack=False)
        except Exception as exc:
            raise Blocked("Issues is probably that the complete zip "
                          "does not exist yet.")
    else:
        # The build script needs working directory access to the
        #   complete zip file.
        shutil.copy2(completezip_filepath, build_dir)

    # Run the oer.exports script against the collection data.
    build_script = os.path.join(cnxbuildout_dir, 'scripts',
                                'content2epub.bash')
    offlinezip_result_filename = '{0}-{1}.offline.zip'.format(id, version)
    # XXX The build script putting the file somewhere other other than where
    #     I told it to. *Grumbles*
    unpacked_collection_dir = "{0}_{1}_complete".format(id, version)
    offlinezip_result_filepath = os.path.join(build_dir,
                                              unpacked_collection_dir,
                                              offlinezip_result_filename)
    epub_result_filename = '{0}-{1}.epub'.format(id, version)
    epub_result_filepath = os.path.join(build_dir, epub_result_filename)

    command = []
    working_dir = build_dir
    if python_env is not None:
        activate = os.path.join(python_env, 'bin', 'activate')
        command.extend(['source', activate, '&&'])
        working_dir = python_env
    command.extend([build_script, "Connexions", id, version,
                    build_dir,  # maps to working directory
                    completezip_filename,
                    offlinezip_result_filename,
                    epub_result_filename,
                    oerexports_dir,
                    ])
    logger.debug("Running: " + ' '.join(command))
    process = subprocess.Popen(' '.join(command),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=oerexports_dir, shell=True,
                               executable='/bin/bash')
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        # Something went wrong...
        raise rbit.Failed(stderr)
    else:
        msg = "Offline zip created, moving contents to final destination..."
        logger.debug(msg)

    # Write out the results to the filesystem.
    offlinezip_output_filepath = os.path.join(output_dir,
                                              offlinezip_result_filename)
    epub_output_filepath = os.path.join(output_dir,
                                        epub_result_filename)

    shutil.copy2(offlinezip_result_filepath, output_dir)
    shutil.copy2(epub_result_filepath, output_dir)
    artifacts = [os.path.join(output_dir, offlinezip_result_filename),
                 os.path.join(output_dir, epub_result_filename),
                 ]

    # Remove the temporary build directory
    shutil.rmtree(build_dir)

    return artifacts
