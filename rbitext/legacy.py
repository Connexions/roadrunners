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
import jsonpickle
import requests

from .utils import logger


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
