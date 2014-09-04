# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""\
Tests for the pdf roadrunner.

"""
import os
import re
import tempfile
import shutil
import subprocess
import unittest

from ConfigParser import RawConfigParser
try:
    from unittest import mock
except ImportError:
    import mock

from . import test_data
from .. import pdf
from . import pdfiinfo

# Get settings from the ini file
config = RawConfigParser()
if hasattr('test.ini', 'read'):
    config.readfp('test.ini')
else:
    with open('test.ini', 'r') as f:
        config.readfp(f)

def config_to_dict(c):
    result = {}
    for section in c.sections():
        result[section] = dict(c.items(section))
    return result

settings = config_to_dict(config)['runner:pdf']

class PdfTests(unittest.TestCase):
    
    def mocked_get_offlinezip(self, url, auth=None):
        # Make sure the url and authorization are good
        url1 = 'http://cnx.org/content/col10642/1.2/'
        url2 = 'http://cnx.org/content/col10642/latest/'
        self.assertTrue(url1 in url or url2 in url)
        if auth:
            username = settings['runner:completezip']['username']
            password = settings['runner:completezip']['password']
            self.assertEquals(auth, (username, password))
        # Create the mock response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        with open(test_data('col10642-1.2.offline.zip'), 'rb') as zip_object:
            mock_response.content = zip_object.read()
        return mock_response
        
        
    def setUp(self):
    
        # make a temp directory with no underscores
        self.test_output = tempfile.mkdtemp()
        new_name = re.sub('_', 'g', self.test_output)
        os.rename(self.test_output, new_name)
        self.test_output = new_name
        settings['output-dir'] = self.test_output

        # Mock the build request
        self.mock_request = mock.Mock()
        self.mock_request.get_package.return_value = "col10642"
        self.mock_request.get_version.return_value = "1.2"
        self.mock_request.transport.uri = "http://cnx.org"
        self.mock_request.job.packageinstance.package.version = "1.2"
        
        def mock_popen(command, stdout, stderr, cwd):
            # don't want to do anything with the uzip command
            if (command[0] == 'unzip'):
                PdfTests.patcher.stop()
                process = subprocess.Popen(command, stdout=stdout, stderr=stderr, cwd=cwd)
                PdfTests.patcher.start()
                return process
            # the pdf building command
            result_filepath = command[-1]
            command.insert(8, '-t')
            command.insert(9, self.test_output)
            PdfTests.patcher.stop()
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, cwd=cwd)
            PdfTests.patcher.start()
            return process
            
        PdfTests.patcher = mock.patch('roadrunners.pdf.subprocess.Popen', mock_popen)
        PdfTests.patcher.start()
        self.addCleanup(PdfTests.patcher.stop)
    
    def tearDown(self):
        shutil.rmtree(self.test_output)
            
    def verify_pdf(self, expect_pdf, test_pdf, expect_html, test_html, title):
    
        # check the pdf metadata
        info = pdfiinfo.pdfinfo(test_pdf)
        self.assertEquals(info['Title'], title)
        self.assertTrue(int(info['File size'].split(' ')[0]) > 0)
        
        with open(test_html) as got_file:
            got_string = got_file.read()
        with open(expect_html) as wanted_file:
            wanted_string = wanted_file.read()

        # replace the unique id numbers in the files
        replace_string = re.sub(r'Link: #m[1-9]*-autoid-cnx2dbk-idm[0-9]*', 'Link: #m12345-autoid-cnx2dbk-idm1', got_string)
        replace_string = re.sub(r'Link: #m[1-9]*-autoid-cnx2dbk-idm[0-9]*', 'Link: #m12345-autoid-cnx2dbk-idm1', wanted_string)
        replace_string2 = re.sub(r'Link: #idm[0-9]*', 'Link: #idm1', got_string)
        replace_string2 = re.sub(r'Link: #idm[0-9]*', 'Link: #idm1', wanted_string)

        # see if the strings are equal
        self.assertEquals(replace_string, replace_string2)
    
    @unittest.skipIf(not os.path.exists(settings['oer.exports-dir']), 'need oer.exports')
    def test_make_pdf(self):
        
        with mock.patch('roadrunners.utils.requests.get', self.mocked_get_offlinezip):
            output_path = pdf.make_pdf(self.mock_request, settings)
        self.assertEquals(os.path.join(self.test_output, 'col10642-1.2.pdf'), output_path[0])
        self.assertEquals(len(output_path), 1)
        
        # get the expected and test files and verify them
        got_html = os.path.join(self.test_output, 'collection.xhtml')
        wanted_html = test_data('collection.xhtml')
        test_pdf = output_path[0]
        expect_pdf = test_data('col10642-1.2.pdf')
        title = 'XML og XSLT - en introduktion'
        
        PdfTests.patcher.stop()
        self.verify_pdf(expect_pdf, test_pdf, wanted_html, got_html, title)
        PdfTests.patcher.start()
    
    @unittest.skipIf(not os.path.exists(settings['oer.exports-dir']), 'need oer.exports')
    def test_pdf_latest_version(self):
        self.mock_request.get_version.return_value = "latest"
        self.mock_request.job.packageinstance.package.version = "latest"

        with mock.patch('roadrunners.utils.requests.get', self.mocked_get_offlinezip):
            output_path = pdf.make_pdf(self.mock_request, settings)
        self.assertEquals(os.path.join(self.test_output, 'col10642-1.2.pdf'), output_path[0])
        self.assertEquals(len(output_path), 1)
        
        # get the expected and test files and verify them
        got_html = os.path.join(self.test_output, 'collection.xhtml')
        wanted_html = test_data('collection.xhtml')
        test_pdf = output_path[0]
        expect_pdf = test_data('col10642-1.2.pdf')
        title = 'XML og XSLT - en introduktion'
        
        PdfTests.patcher.stop()
        self.verify_pdf(expect_pdf, test_pdf, wanted_html, got_html, title)
        PdfTests.patcher.start()
        
        
        