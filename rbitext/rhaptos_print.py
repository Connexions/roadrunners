# -*- coding: utf-8 -*-
"""\
rbit extensions for integration with Products.RhaptosPrint.

Author: Michael Mulich
Copyright (c) 2012 Rice University

Parts of the client code are derived from the PyBit client implementation at
https://github.com/nicholasdavidson/pybit licensed under GPL2.1.

This software is subject to the provisions of the GNU Lesser General
Public License Version 2.1 (LGPL).  See LICENSE.txt for details.
"""
import os
import subprocess
import jsonpickle


def make_print(message, set_status, settings={}):
    """rbit extension to interface with the Products.RhaptosPrint.printing
    Makefile.

    Available settings:

    - **python** - Maps to the make file's PYTHON variable
    - **print-dir** - Maps to the make file's PRINT_DIR variable
    - **host** - Maps to the make file's HOST variable

    """
    build_request = jsonpickle.decode(message)
    build_request.stamp_request()
    timestamp = build_request.get_buildstamp()
    status_message = "Starting job, timestamp: {0}".format(timestamp)
    set_status('Building', status_message)

    content_id = build_request.get_package()
    command = ['make', '{0}.pdf'.format(content_id)]
    # Override various make variables.
    overrides = [
        settings.get('python') and "PYTHON=" + settings['python'] or None,
        settings.get('print-dir') and "PRINT_DIR=" + settings['print-dir'] or None,
        settings.get('host') and "HOST=" + settings['host'] or None,
        "COLLECTION_VERSION=" + build_request.job.packageinstance.package.version,
        ]
    overrides = [c for c in overrides if c]  # Remove the None values.
    command.extend(overrides)

    cwd = os.path.abspath(settings.get('print-dir', os.curdir))
    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=cwd)
    stdout, stderr = process.communicate()
    if process.returncode < 0:
        # Something went wrong...
        set_status('Failed', stderr)
    return ""
