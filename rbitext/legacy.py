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

from rbit import Blocked
from .utils import logger, get_completezip, unpack_zip


def make_completezip(message, set_status, settings={}):
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

    # Start the building sequence by updating the build's status.
    build_request = jsonpickle.decode(message)
    build_request.stamp_request()
    timestamp = build_request.get_buildstamp()
    status_message = "Starting job, timestamp: {0}".format(timestamp)
    set_status('Building', status_message)

    # Acquire the collection's data in a collection directory format.
    id = build_request.get_package()
    version = build_request.get_version()
    # This should be something like 'http://cnx.org:80'.
    base_uri = build_request.transport.uri.rstrip('/')

    # Make a request to the repository to create the completezip.
    url = "{0}{1}/{2}/{3}/create_complete".format(base_uri, content_path,
                                                  id, version)
    resp = requests.get(url, auth=(username, password))

    if resp.status_code != 200:
        set_status('Failed', resp)
        return

    # Write out the results to the filesystem.
    result_filename = "{0}-{1}.complete.zip".format(id, version)
    output_filepath = os.path.join(output_dir, result_filename)
    set_status('Building', "Placing file a location: " + output_filepath)
    with open(output_filepath, 'wb') as f:
        f.write(resp.content)

    set_status('Done')


def make_offlinezip(message, set_status, settings={}):
    """\
    Creates an offlinezip using the complete zip (dependency).

    Available settings:

    - **output-dir** - Directory where the produced file is stuck.
    - **oer.exports-dir** - Defines the location of the oer.exports package.
    - **python** - Defines which python executable should be used.

    """
    output_dir = settings['output-dir']
    python_executable = settings.get('python', sys.executable)
    oerexports_dir = settings['oer.exports-dir']

    # Start the building sequence by updating the build's status.
    build_request = jsonpickle.decode(message)
    build_request.stamp_request()
    timestamp = build_request.get_buildstamp()
    status_message = "Starting job, timestamp: {0}".format(timestamp)
    set_status('Building', status_message)

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
    if os.path.exists(completezip_filepath):
        content_dir = unpack_zip(completezip_filepath, build_dir)[0]
    else:
        # Looks like we will need to download the file...
        try:
            content_dir = get_completezip(id, version, base_uri, build_dir)
        except Exception as exc:
            traceback.print_exc(exc)
            raise Blocked("Issues is probably that the complete zip "
                          "does not exist yet.")

    # Run the oer.exports script against the collection data.
    build_script = os.path.join(oerexports_dir, 'content2epub.py')
    result_filename = '{0}-{1}.offline.zip'.format(id, version)
    result_filepath = os.path.join(build_dir, result_filename)
    command = [python_executable, build_script, content_dir,
               # The follow are not optional, values must be supplied.
               '-t', 'collection',
               '-c', os.path.join(oerexports_dir, 'static',
                                  'offline-zip-overrides.css'),
               '-e', os.path.join(oerexports_dir, 'xsl', 'dbk2html.xsl'),
               '-o', result_filepath,
               ]
    set_status('Building', "Running: " + ' '.join(command))
    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=build_dir)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        # Something went wrong...
        set_status('Failed', stderr)
        return
    else:
        msg = "Offline zip created, moving contents to final destination..."
        set_status('Building', msg)

    # TODO Add a readme file to the zip Also, remove epub metadata files.

    # Write out the results to the filesystem.
    shutil.copy2(result_filepath, output_dir)
    output_filepath = os.path.join(output_dir, result_filename)
    set_status('Building', "Placing file a location: " + output_filepath)

    # Remove the temporary build directory
    shutil.rmtree(build_dir)

    set_status('Done')
