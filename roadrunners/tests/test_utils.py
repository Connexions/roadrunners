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

from .. import utils
from . import test_data
try:
    from unittest import mock
except ImportError:
    import mock

class RoadrunnerUtilTests(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory to work in
        self.test_dir = tempfile.mkdtemp()
        # Overwrite requests.get in utils for the tests
        def mocked_get(url, auth=None):
            self.assertTrue('http://cnx.org/content/col10642/1.2/' in url)
            mock_response = mock.Mock()
            mock_response.status_code = 200
            with open(test_data("test_zip.zip"), 'rb') as file_object:
                mock_response.content = file_object.read()
            return mock_response
        get_patcher = mock.patch('roadrunners.legacy.requests.get', mocked_get)
        get_patcher.start()
        self.addCleanup(get_patcher.stop)
    
    def tearDown(self):
        # Destroy the temporary testing directory even if tests fail
        shutil.rmtree(self.test_dir)
    
    def verify_unpack(self, unpacked_file):
        test_dir = self.test_dir
        
        # Returns only the name of what was unpacked
        self.assertEquals(len(unpacked_file), 1)
        self.assertTrue("test_zip" in unpacked_file)
        
        # Unpacked file contains what it is supposed to
        directory_listing = os.listdir(os.path.join(test_dir, "test_zip"))
        self.assertEqual(len(directory_listing), 2)
        self.assertTrue("col10642-1.2.pdf" in directory_listing)
        self.assertTrue("file.txt" in directory_listing)
        
    def test_unpack_zip_workingdir(self): 
        unpacked_file = utils.unpack_zip(test_data("test_zip.zip"), self.test_dir)
        self.verify_unpack(unpacked_file)

    def test_unpack_zip_other_files(self):
        # put another file in the test directory
        tempfile.mkstemp(dir=self.test_dir)
        unpacked_file = utils.unpack_zip(test_data("test_zip.zip"), self.test_dir)
        self.verify_unpack(unpacked_file)
    
    def test_get_zip_dont_unpack(self):   
        zip = utils.get_zip('col10642', '1.2', 'http://cnx.org', self.test_dir, False)
        self.assertEqual(zip, os.path.join(self.test_dir, 'col10642-1.2.complete.zip'))
        self.assertTrue('col10642-1.2.complete.zip' in os.listdir(self.test_dir))
    
    def test_get_zip_unpack(self):
        
        # Check correct file was unpacked
        zip = utils.get_zip('col10642', '1.2', 'http://cnx.org', self.test_dir)
        self.assertEqual(zip, 'test_zip')
        self.assertTrue('test_zip' in os.listdir(self.test_dir))

        # Check correct contents were unpacked
        contents = os.listdir(os.path.join(self.test_dir, 'test_zip'))
        self.assertEqual(len(contents), 2)
        self.assertTrue('file.txt' in contents)
        self.assertTrue('col10642-1.2.pdf' in contents)

