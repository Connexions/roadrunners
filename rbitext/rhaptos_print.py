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
import shutil
import jsonpickle


def make_print(message, set_status, settings={}):
    """rbit extension to interface with the Products.RhaptosPrint.printing
    Makefile.

    Available settings:

    - **output-dir** - Directory where the produced file is stuck.
    - **python** - Maps to the make file's PYTHON variable
    - **print-dir** - Maps to the make file's PRINT_DIR variable
    - **host** - Maps to the make file's HOST variable

    """
    output_dir = settings['output-dir']
    python_executable = settings.get('python', None)
    print_dir = settings.get('print-dir', None)
    host = settings.get('host', None)

    build_request = jsonpickle.decode(message)
    build_request.stamp_request()
    timestamp = build_request.get_buildstamp()
    status_message = "Starting job, timestamp: {0}".format(timestamp)
    set_status('Building', status_message)

    content_id = build_request.get_package()
    pdf_filename = '{0}.pdf'.format(content_id)
    command = ['make', pdf_filename]
    # Override various make variables.
    overrides = [
        python_executable and "PYTHON=" + python_executable or None,
        print_dir and "PRINT_DIR=" + print_dir or None,
        host and "HOST=" + host or None,
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
        return
    else:
        msg = "PDF created, moving contents to final destination..."
        set_status('Building', msg)

    # Move the resulting document to the defined location.
    shutil.copy2(os.path.join(cwd, pdf_filename), output_dir)

    set_status('Done')
