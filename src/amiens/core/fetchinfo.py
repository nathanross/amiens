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

from amiens.core.util import Log

import urllib.request
import defusedxml.ElementTree as etree

class FetchInfo(object):
    METADATA=True
    FILEDATA=False
    
    @staticmethod
    def as_str(ident, meta):
        keyword = 'meta' if (meta == FetchInfo.METADATA) else 'files'
        url ='https://archive.org/download/{0}/{0}_{1}.xml'.format(ident, keyword)
        try:
            res= urllib.request.urlopen(url).read()
        except:
            return None
        Log.data('url:'+url)
        return res.decode()
    
    @staticmethod
    def as_etree(ident, meta):
        res = FetchInfo.as_str(ident, meta)
        if res == None:
            return res
        return etree.fromstring(res)

