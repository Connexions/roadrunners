# -*- coding: utf-8 -*-
"""\
rbit extensions for integration with oer.exports epub generation code.

Author: Michael Mulich
Copyright (c) 2012 Rice University

This software is subject to the provisions of the GNU Lesser General
Public License Version 2.1 (LGPL).  See LICENSE.txt for details.
"""
import os
import sys
import subprocess
##import shutil
import tempfile
import jsonpickle


def _get_completezip(build_request, settings, working_dir):
    """"Acquire the collection data from a (Plone based) Connexions
    repository in the completezip format.

    """
    # Download the completezip
    pkg = build_request.get_package()
    version = build_request.get_version()

    filename = "{0}-{1}.complete.zip".format(pkg, version)
    url = '{0}/content/{1}/{2}/complete'.format(build_request.transport.uri,
                                                pkg, version)
    process = subprocess.Popen(['wget', '-O', filename, url],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=working_dir)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise RuntimeError(stdout + "\n\n" + stderr)
    # Unpack the zip
    process = subprocess.Popen(['unzip', filename],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              cwd=working_dir)
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


def make_epub(message, set_status, settings={}):
    """rbit extension to interface with the oer.exports epub code.

    Available settings:

    - **output-dir** - Directory where the produced file is stuck.
    - **oer.exports-dir** - Defines the location of the oer.exports package.
    - **python** - Defines which python executable should be used.

    """
    python_executable = settings.get('python', sys.executable)
    oerexports_dir = settings['oer.exports-dir']
    output_dir = settings['output-dir']

    build_request = jsonpickle.decode(message)
    build_request.stamp_request()
    timestamp = build_request.get_buildstamp()
    status_message = "Starting job, timestamp: {0}".format(timestamp)
    set_status('Building', status_message)

    build_dir = tempfile.mkdtemp()
    print('-'*80 + '\n' + build_dir + '\n' + '-'*80)

    collection_dir = _get_completezip(build_request, settings, build_dir)

    build_script = os.path.join(oerexports_dir, 'content2epub.py')
    result_filename = '{0}-{1}.epub'.format(build_request.get_package(),
                                            build_request.get_version())
    result_filepath = os.path.join(build_dir, result_filename)
    command = [python_executable, build_script, collection_dir,
               # The follow are not optional, values must be supplied.
               '-t', 'collection',
               '-c', os.path.join(oerexports_dir, 'static', 'content.css'),
               '-e', os.path.join(oerexports_dir, 'xsl', 'dbk2epub.xsl'),
               '-o', result_filepath,
               ]

    print(' '.join(command))
    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=build_dir)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        # Something went wrong...
        set_status('Failed', stderr)
        return
    else:
        msg = "PDF created, moving contents to final destination..."
        set_status('Building', msg)

    # Move the file to it's final destination.
    shutil.copy2(result_filepath, output_dir)
    print(result_filepath)

    # Remove the temp directory.
    ##shutils.rmtree(build_dir)

    set_status('Done')
