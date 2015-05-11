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

#!/bin/python3
import defusedxml.ElementTree as etree

def do_blacklist(stub):
    blacklist=['polka','ska', 'talk', 'podcast']
    corpus=stub.data['metadata']
    #m_etree = etree.fromstring(stub.data['metadata'])
    #corpus=''
    #for keyword in ['title', 'subject', 'description']:
    #    el = m_etree.find(keyword)
    #    if el:
    #        corpus += ' ' + el.text
    if corpus:
        for term in blacklist:
            if term in corpus:
                return False
    return True

callback=do_blacklist
