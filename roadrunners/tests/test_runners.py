# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""\
Tests for common utilities used in the roadrunners.

"""
import os
import tempfile
import shutil
import unittest

from ConfigParser import RawConfigParser
try:
    from unittest import mock
except ImportError:
    import mock
from zipfile import ZipFile

from . import test_data
from .. import epub
from .. import legacy
from .. import utils



class RoadrunnerTests(unittest.TestCase):
    # Mock utils get_completezip so that necessary files are returned
    def mocked_get_completezip(self, url, auth=None):
        # Make sure the url and authorization are good
        url1 = 'http://cnx.org/content/col10642/1.2/'
        url2 = 'http://cnx.org/content/col10642/latest/'
        self.assertTrue(url1 in url or url2 in url)
        if auth:
            username = self.settings['runner:completezip']['username']
            password = self.settings['runner:completezip']['password']
            self.assertEquals(auth, (username, password))
        # Create the mock response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        with open(test_data('col10642-1.2.complete.zip'), 'rb') as zip_object:
            mock_response.content = zip_object.read()
        return mock_response
    
    def setUp(self):
        # Create a temporary directory to work in
        self.test_output = tempfile.mkdtemp()
        
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

        self.settings = config_to_dict(config)
        
        # Mock the build request
        self.mock_request = mock.Mock()
        self.mock_request.get_package.return_value = "col10642"
        self.mock_request.get_version.return_value = "1.2"
        self.mock_request.transport.uri = "http://cnx.org"
        self.mock_request.job.packageinstance.package.version = "1.2"
        
        def mocked_get(url, auth=None):
            # Make sure the url and authorization are good
            self.assertTrue('http://cnx.org/content/col10642/1.2/' in url)
            if auth:
                username = self.settings['runner:completezip']['username']
                password = self.settings['runner:completezip']['password']
                self.assertEquals(auth, (username, password))
            # Create the mock response
            mock_response = mock.Mock()
            mock_response.status_code = 200
            # If the request is for xml
            if 'source_create' in url:
                with open(test_data('col10642-1.2.xml'), 'rb') as file_object:
                    mock_response.content = file_object.read()
            # otherwise its for a completezip
            else:
                with open(test_data('test_zip.zip'), 'rb') as zip_object:
                    mock_response.content = zip_object.read()
            return mock_response
        get_patcher = mock.patch('roadrunners.legacy.requests.get', mocked_get)
        get_patcher.start()
        self.addCleanup(get_patcher.stop)
    
    def tearDown(self):
        # Destroy the temporary testing directory even if tests fail
        shutil.rmtree(self.test_output)
        
    def test_make_collxml(self):
        settings = self.settings['runner:xml']
        settings['output-dir'] = self.test_output
        
        output_path = legacy.make_collxml(self.mock_request, settings)
        self.assertEquals(os.path.join(self.test_output, 'col10642-1.2.xml'), output_path[0])
        self.assertEquals(len(output_path), 1)
        
    def test_completezip(self):
        settings = self.settings['runner:completezip']
        settings['output-dir'] = self.test_output
        
        output_path = legacy.make_completezip(self.mock_request, settings)
        
        # Check that correct thing was returned
        self.assertEquals(len(output_path), 1)
        self.assertEquals(output_path[0], os.path.join(self.test_output, "col10642-1.2.complete.zip"))
        
        # Check that file is where it is supposed to be
        self.assertTrue("col10642-1.2.complete.zip" in os.listdir(self.test_output))
        # And that it is the only one there as expected
        self.assertEquals(len(os.listdir(self.test_output)), 1)
        
        # Check that it contains the right files
        zip_obj = ZipFile(os.path.join(self.test_output, "col10642-1.2.complete.zip"))
        zip_obj.extractall(self.test_output)
        contents = os.listdir(os.path.join(self.test_output,'test_zip'))
        self.assertTrue('file.txt' in contents)
        self.assertTrue('col10642-1.2.pdf' in contents)
        self.assertEquals(len(contents), 2)
    
    def test_legacy_print(self):        
        settings = self.settings['runner:legacy-print']
        settings['output-dir'] = self.test_output
        
        output_path = legacy.make_print(self.mock_request, settings)
        
        # Check that correct thing was returned
        self.assertEquals(len(output_path), 1)
        self.assertEquals(output_path[0], os.path.join(self.test_output, 'col10642-1.2.pdf'))
        
        # Check that file is where it is supposed to be
        self.assertTrue('col10642-1.2.pdf' in os.listdir(self.test_output))
    
    def test_offlinezip_existing_completezip(self):
        # get the settings dictionary
        settings = self.settings['runner:offlinezip']
        settings['output-dir'] = self.test_output
        
        # get the completezip and put it where its supposed to be
        with mock.patch('roadrunners.utils.requests.get', self.mocked_get_completezip):
            utils.get_completezip("col10642", "1.2", "http://cnx.org", self.test_output, unpack=False)
        
        path_list = legacy.make_offlinezip(self.mock_request, settings)
        self.assertEquals(len(path_list), 2)
        self.assertTrue(os.path.join(self.test_output, 'col10642-1.2.epub') in path_list)
        self.assertTrue(os.path.join(self.test_output, 'col10642-1.2.offline.zip') in path_list)
        
    def test_offlinezip_no_completezip(self):

        # get the settings dictionary
        settings = self.settings['runner:offlinezip']
        settings['output-dir'] = self.test_output
        
        with mock.patch('roadrunners.utils.requests.get', self.mocked_get_completezip):
            path_list = legacy.make_offlinezip(self.mock_request, settings)
        self.assertEquals(len(path_list), 2)
        self.assertTrue(os.path.join(self.test_output, 'col10642-1.2.epub') in path_list)
        self.assertTrue(os.path.join(self.test_output, 'col10642-1.2.offline.zip') in path_list)
    
    def test_make_epub(self):
        
        # get the settings dictionary
        settings = self.settings['runner:epub']
        settings['output-dir'] = self.test_output
        
        with mock.patch('roadrunners.utils.requests.get', self.mocked_get_completezip):
            output_path = epub.make_epub(self.mock_request, settings)
        self.assertEquals(os.path.join(self.test_output, 'col10642-1.2.epub'), output_path[0])
        self.assertEquals(len(output_path), 1)
        
    def test_make_epub_latest(self):
    
        # get the settings dictionary
        settings = self.settings['runner:epub']
        settings['output-dir'] = self.test_output
        
        # change the build request to use 'latest' version
        self.mock_request.get_version.return_value = "latest"
        self.mock_request.job.packageinstance.package.version = "latest"
        
        with mock.patch('roadrunners.utils.requests.get', self.mocked_get_completezip):
            output_path = epub.make_epub(self.mock_request, settings)
        self.assertEquals(os.path.join(self.test_output, 'col10642-1.2.epub'), output_path[0])
        self.assertEquals(len(output_path), 1)