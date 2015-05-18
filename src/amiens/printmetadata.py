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

from amiens.core.subcmd import Subcmd
import defusedxml.ElementTree as etree

class PrintMetadata(Subcmd):

    @staticmethod
    def add_if_present(lines, m_etree, tag, arg_displayname=None):        
        displayname=tag.lower()
        if arg_displayname != None:
            displayname = arg_displayname
        spacelen=max(0, 10-len(displayname))
        spaces=' '.join('' for x in range(0, spacelen))
        el=m_etree.find(tag)
        if el != None and el.text != None:
            text=el.text
            if type(el.text) != str:
                text = repr(el.text)
            
            lines.append(displayname+': '+spaces+ text)

    
    @staticmethod
    def cmd(args):
        item=args['item']
        t='\t'
        lines=['' '--------------------------------------', '']
        
        lines.append('Ident:    '+item.data['ident'])
        lines.append('Rating:   '+repr(item.data['rating']))
        lines.append('Comment:  '+repr(item.data['comment']))
        lines.append(' ')
        m_etree = etree.fromstring(item.data['metadata'])
        prioritized_tags = ({'tag':'title', 'display':'Title'},
                            {'tag':'subject','display':'Tags'},
                            {'tag':'description','display':'Descript.'})

        low_priority_tags=({'tag':'addeddate', 'display': 'Added on'},
                           {'tag':'publicdate', 'display': 'Published'},
                           {'tag': 'uploader', 'display': None},
                           {'tag': 'mediatype', 'display': None})
        skipped_tags=['identifier', 'curation']

        for keyword in prioritized_tags:
            PrintMetadata.add_if_present(lines, m_etree, keyword['tag'],
                                         keyword['display'])
        
        lines.append('')
        lines.append('--other tags--')

        standout_tags = [ x['tag'] for x in prioritized_tags ]
        standout_tags.extend([ x['tag'] for x in low_priority_tags ])
        standout_tags.extend(skipped_tags)

        for m_keyval in m_etree:
            if m_keyval.tag in standout_tags:
                continue
            if m_keyval.text == None or m_keyval.text == '':
                continue    
            lines.append(m_keyval.tag + ' : ' + repr(m_keyval.text))
        
        lines.append(' ')
        
        for keyword in low_priority_tags:
            PrintMetadata.add_if_present(lines, m_etree, keyword['tag'],
                                         keyword['display'])

        lines.append(' ')
                        
        print('\n  '.join(lines))
        
