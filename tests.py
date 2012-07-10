#!/usr/bin/python
#-*- coding: UTF-8 -*-

"""
 (c) 2011, 2012 - Copyright Pierre-Yves Chibon

 Distributed under License GPLv3 or later
 You can find a copy of this license on the website
 http://www.gnu.org/licenses/gpl.html

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
 MA 02110-1301, USA.

Unit-test for the MQ2_Web.
"""

import os
import re
import shutil
import tempfile
import unittest

from mq2_web import APP, CONFIG

TEST_INPUT = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'static/Demoset.zip')

class MQ2_WebTestCase(unittest.TestCase):
    """ Test the web interface for MQ2. """

    def setUp(self):
        APP.config['TESTING'] = True
        APP.config['CSRF_ENABLED'] = False
        self.app = APP.test_client()

    def test_index_displays(self):
        """Checks that the index page displays correctly. """
        root = self.app.get('/')
        self.assertTrue('<form method="POST" action="." '\
        'enctype="multipart/form-data">' in root.data)
        self.assertTrue(root.status_code, 200)

    def test_wrong_session(self):
        """Checks that the form errors when it should. """
        post = self.app.post('/', data=dict(
                session_id='wrong identifier'),
                follow_redirects=True)
        self.assertTrue(post.status_code, 200)
        self.assertTrue('<li>This session does not exists</li>'
            in post.data)

    def test_sample_session(self):
        """Checks that the form works for an existing session. """
        session_id = CONFIG.get('mq2', 'sample_session')
        post = self.app.post('/', data=dict(
                session_id=session_id),
                follow_redirects=True)
        self.assertTrue(post.status_code, 200)
        self.assertTrue('<p> Session identifier: <span style="color:red">'
            in post.data)

    def test_sample_data(self):
        """Checks that the form works to upload the demo dataset. """
        stream = open(TEST_INPUT)
        post = self.app.post('/', data=dict(
                mapqtl_input=stream),
                follow_redirects=True)
        stream.close()

        self.assertTrue(post.status_code, 200)
        self.assertTrue('<p> Session identifier: <span style="color:red">'
            in post.data)

        motif = re.compile('\n(.*)</span></p>\n')
        output = motif.search(post.data)
        session_id = output.group(1).strip()

        post = self.app.post('/session/%s/' % session_id)
        self.assertTrue(post.status_code, 200)
        self.assertTrue('<p> Session identifier: <span style="color:red">'
            in post.data)
        self.assertTrue('%s</span></p>\n' % session_id)

        upload_folder = CONFIG.get('mq2', 'upload_folder')
        shutil.rmtree(os.path.join(upload_folder, session_id))

    def test_experiment(self):
        """Checks that the form works for an experiment. """
        stream = open(TEST_INPUT)
        post = self.app.post('/', data=dict(
                mapqtl_input=stream),
                follow_redirects=True)
        stream.close()
        self.assertTrue(post.status_code, 200)
        self.assertTrue('<p> Session identifier: <span style="color:red">'
            in post.data)

        motif = re.compile('\n(.*)</span></p>\n')
        output = motif.search(post.data)
        session_id = output.group(1).strip()

        post2 = self.app.post('/session/%s/' % session_id,
                data=dict(lod_threshold=3, mapqtl_session=2),
                follow_redirects=True)
        self.assertTrue(post2.status_code, 200)

        motif = re.compile('<li><a href="/session/.*>(.*)</a>')
        output = motif.search(post2.data)
        exp_id = output.group(1).strip()
        self.assertTrue('<p> Session identifier: <span style="color:red">'
            in post2.data)

        post3 = self.app.get('/session/%s/%s/' % (session_id, exp_id),
                follow_redirects=True)

        self.assertTrue(post3.status_code, 200)
        self.assertTrue('qtls_matrix.csv</a> -- Matrix giving for each'
            in post3.data)
        self.assertTrue('map.csv</a> -- The genetic map extracted'
            in post3.data)
        self.assertTrue('map_with_qtl.csv</a> -- Representation'
            in post3.data)
        self.assertTrue('<script type="text/javascript+protovis" >'
            in post3.data)

        post4 = self.app.post('/session/%s/' % session_id,
                data=dict(lod_threshold=3, mapqtl_session=2),
                follow_redirects=True)
        self.assertTrue(post4.status_code, 200)
        self.assertTrue('<li>Experiment already run in experiment: ' in
            post4.data)

        post5 = self.app.get('/session/%s/%s/marker/E36M48-330' % (session_id,
                exp_id),
                follow_redirects=True)

        self.assertTrue(post5.status_code, 200)
        self.assertTrue('MQ² results for marker E36M48-330' in post5.data)
        self.assertTrue('2 QTLs found' in post5.data)
        self.assertTrue('A_trait07' in post5.data)
        self.assertTrue('A_trait11' in post5.data)

        upload_folder = CONFIG.get('mq2', 'upload_folder')
        shutil.rmtree(os.path.join(upload_folder, session_id))


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(MQ2_WebTestCase)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
