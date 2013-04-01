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
import sys
import subprocess
import shutil

import rbit
from .utils import logger


def make_print(build_request, settings={}):
    """rbit extension to interface with the Products.RhaptosPrint.printing
    Makefile.

    Available settings:

    - **output-dir** - Directory where the produced file is stuck.
    - **python** - Maps to the make file's PYTHON variable
    - **print-dir** - Maps to the make file's PRINT_DIR variable

    """
    output_dir = settings['output-dir']
    python_executable = settings.get('python', sys.executable)
    print_dir = settings.get('print-dir', None)
    cwd = os.path.abspath(settings.get('print-dir', os.curdir))

    build_request.stamp_request()
    timestamp = build_request.get_buildstamp()
    status_message = "Starting job, timestamp: {0}".format(timestamp)
    logger.debug(status_message)

    # Clean up the 'shared' environment before trying to build.
    # FIXME This is a 'shared' environment, which means we can't run
    #       more than one job at a time.
    process = subprocess.Popen(['make', 'clear'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=cwd)
    stdout, stderr = process.communicate()
    # At this time we don't really care if cleanup worked or not.
    # if process.returncode != 0:
    #     # Something went wrong...
    #     message = '\n\n'.join(["Cleanup failed:", stderr, stdout])
    #     set_status('Failed', message)
    #     return

    # Run the makefile from RhaptosPrint that will create the PDF
    id = build_request.get_package()
    version = build_request.get_version()
    pdf_filename = "{}.pdf".format(id)
    is_module = id.startswith('m')
    make_file = is_module and 'module_print.mak' or 'course_print.mak'
    command = ['make', '-f', make_file, pdf_filename]
    # Override various make variables.
    host = build_request.transport.uri
    host = '/'.join(host.split('/')[:3])  # just the {protocol}://{hostname}
    overrides = [
        python_executable and "PYTHON=" + python_executable or None,
        print_dir and "PRINT_DIR=" + print_dir or None,
        host and "HOST=" + host or None,
        "VERSION=" + build_request.job.packageinstance.package.version,
        ]
    overrides = [c for c in overrides if c]  # Remove the None values.
    command.extend(overrides)

    logger.debug("Running command: " + ' '.join(command))
    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=cwd)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise rbit.Failed(stderr)
    else:
        msg = "PDF created, moving contents to final destination..."
        logger.debug(msg)


    # Rename and move the resulting document to the defined location.
    new_pdf_filename = "{}-{}.pdf".format(id, version)
    os.rename(os.path.join(cwd, pdf_filename),
              os.path.join(cwd, new_pdf_filename))
    pdf_filename = new_pdf_filename
    shutil.copy2(os.path.join(cwd, pdf_filename), output_dir)

    return [os.path.join(output_dir, pdf_filename)]
