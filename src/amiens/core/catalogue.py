#!/usr/bin/python3

# Copyright 2015 Nathan Ross
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import hashlib
from amiens.core.amiensdb import ArliDb
from amiens.core import util
from amiens.core.util import Log

class Catalogue:
    def __init__(self, rootdir, exists=True):
        self.rootdir = rootdir.rstrip('/')
        self.metadata_dir = self.rootdir+'/metadata'
        self.db_path = self.rootdir+'/amiens.sqlite'
        self.adb=None
        if exists:
            self.adb = ArliDb(self.db_path)
        else:
            os.makedirs(self.rootdir)
            self.adb = ArliDb.create_new(self.db_path)
    
    @staticmethod
    def get_metadata_path(parentdir, ident):
        ihash=hashlib.sha1(str.encode(ident)).hexdigest()
        division_dir=ihash[:2]
        fname=ihash[2:4]
        return parentdir.rstrip('/')+'/'+division_dir+'/'+fname+'.json'

    def get_metadata(self, ident):
        l_json = Catalogue.get_metadata_path(
            self.metadata_dir,
            ident
        )
        d_json=util.json_read(
            'reading metadata',
            l_json
        )
        return d_json[ident]
    
    def store_metadata(self, ident, xml):
        l_json = Catalogue.get_metadata_path(
            self.metadata_dir,
            ident
        )
        parent_dir=os.path.dirname(l_json)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        d_json={}
        if os.path.exists(l_json):
            d_json = util.json_read(
                'reading metadata',
                l_json
            )
        d_json[ident] = xml
        util.json_write(
            'writing metadata',
            l_json,
            d_json
        )
