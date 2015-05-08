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

class PrintMetadata(Subcmd):
    
    @staticmethod
    def cmd(args):
        item=args['item']
        t='\t'
        lines=['']
        lines.append('Ident:\t'+item.ident)
        lines.append('Rating:\t'+str(item.rating))
        lines.append('Comment:\t'+item.comment)
        
        m_etree = etree.fromstring(item.data.metadata)
        for keyword in ({tag:'title', display:'Title'},
                        {tag:'subject',display:'Tags'},
                        {tag:'description',display:'Description'}):
            el=m_etree.find(keyword['tag'])
            if el:
                lines.append(keyword['display']+': '+ el.text)
        print('\n'.join(lines))
