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
from amiens.core import enums
from amiens.core import util
from amiens.core.stub import Stub
from amiens.core.fetchinfo import FetchInfo
from amiens.core.util import Log
from amiens.core.amiensdb import ArliDb

import defusedxml.ElementTree as etree
import time
from math import ceil
import re
import random

class Learn(Subcmd):
    RE_FLOAT=re.compile('^\d+(\.\d+)?$')
    RE_M_S=re.compile('^(\d+):(\d\d?)$')
    RE_H_M_S=re.compile('^(\d+):(\d\d?):(\d\d?)$')
    
    @staticmethod
    def _sum_filedata_totals(filedata_etree):
        totals = {
            'length' : None, #seconds
            'size' : None #bytes
        }
        unknowable_length=False
        for f in filedata_etree:
            if f.get('source') == 'original':
                fsize=0
                #far as I know, every file but the file xml has a size entry.
                if totals['size'] == None:
                    totals['size'] = 0
                if (f.find('size') == None):
                        continue
                fsize=int(float(f.find('size').text))                
                if Stub.irrelevant_to_length(
                        f.get('name'), fsize):
                    continue
                totals['size'] += fsize
                
                if not unknowable_length:
                    if not (f.find('length') == None) and \
                       not (f.find('length').text == ''):
                        if totals['length'] == None:
                            totals['length'] = 0
                        lengthval=f.find('length').text
                        if re.match(Learn.RE_FLOAT, lengthval):
                            # seconds
                            totals['length'] += int(round(float(lengthval)))
                        elif re.match(Learn.RE_M_S, lengthval):
                            # minutes:seconds
                            m, s = \
                            [ int(x) for x in re.match(Learn.RE_M_S, lengthval).groups() ]
                            totals['length'] += m*60 + s
                        elif re.match(Learn.RE_H_M_S, lengthval):
                            # hours:minutes:seconds
                            h, m, s = \
                             [ int(x) for x in re.match(Learn.RE_H_M_S, lengthval).groups() ]
                            totals['length'] += h*3600 + m*60 + s
                        else:
                            Log.warning('couldnt successfully interpret length value <{}>'.format(val))
                            unknowable_length = True
                            totals['length'] = None
                    else:
                        unknowable_length = True
                        totals['length'] = None                    

        return totals
        
    
    # filefilters here aren't meant so much for you know
    # "am i in the mood for something really long"
    # but rather to filter out items which the consideration
    # of them is almost always going to be a waste
    # of time relative to any nice listening music gained
    # (e.g. 10 seconds of audio.)
    @staticmethod
    def from_web(catalogue, media_type, minutes, fetch_m_fq, keep_m_mqs):
        adb = catalogue.adb
        now = start_unixtime = int(time.time())
        count=0
        debug_counters=[
            'checked',
            'still exist',
            'passed fq',
            'passed mqs',
            't_fetch_fxml',
            't_parse_fxml',
            't_fetch_mxml',
            't_parse_mxml',
            't_get_totals',
            't_fq',
            't_mq',
            't_update_exists',
            't_select'
        ]
        tn = lambda : time.time()
        tdiff = lambda z: (time.time()) - z
        debug_stats = {}

        c = adb.conn.cursor()
        c.execute('select count(*) from items')
        total_idents=c.fetchall()[0][0]
        c.close()
        # the goal is to draw a sample that is relatively equally
        # spaced over the age of idents within a single learn session,
        # and over hundreds of learn sessions eventually forms a uniform
        # distribution.
        # the spacing is important so that we're searching over a variety
        # of items from different times. The random initial offset is
        # important so that the spacing-restricted select (rather than
        # selecting over all idents) does not lead us to end up
        # checking the same restricted set of 2000 idents over and over again.
        step_size=int(total_idents/1000) #truncates
        
        for counter in debug_counters:
            debug_stats[counter] = 0
        while (now - start_unixtime) < minutes*60 :
            now = int(time.time())
            offset=random.randint(0, step_size-1) #randint is inclusive on both ends.
            c = adb.conn.cursor()            
            # for now, just only look at idents
            # we've never looked at before.
            # if we ever run out of those,
            # not likely, we can change this code.
            # todo (AND NOT = exists_status enumval)
            # instead of (AND < enum val)
            st=tn()
            items=ArliDb.quick_select(
                c,
                ('tmpId', 'ident', 'hasMetadata', 'rating', 'comment'),
                ('WHERE ((tmpId+{}) % {} = 0) '
                 'AND ((checkedOnUnixDate < 0) OR (checkedOnUnixDate IS NULL)) '
                 'AND ((existsStatus IS NULL) OR (existsStatus < ?)) '
                 'AND (rating = ? OR rating = ?) LIMIT 1000').format(offset, step_size),
                # we don't filter by has metadata, because we reserve
                # the right for the learn process to not necessarily update
                # metadata, so not having metadata isn't an indicator
                # of priority to be checked.
                (enums.EXISTS_STATUS.DELETED.value,
                enums.RATING.UNRATED.value,
                enums.RATING.CONFIRM_UNRATED.value))
            debug_stats['t_select']+=tdiff(st)
            if len(items) == 0:
                Log.fatal('couldnt find any candidates for learning, please get some idents.')
            metadata_storage_queue=[]
            for item in items:
                Log.data('updating item {}'.format(item['tmpId']))
                now = int(time.time())
                debug_stats['checked'] += 1
                if not ((now - start_unixtime) < minutes*60):
                    break
                
                #parse file data
                #filedata_etree = FetchInfo.as_etree(
                #    item['ident'], FetchInfo.FILEDATA)
                st=tn()
                filedata_xml = FetchInfo.as_str(item['ident'],
                                                FetchInfo.FILEDATA)
                debug_stats['t_fetch_fxml']+=tdiff(st)
                st=tn()
                filedata_etree = etree.fromstring(filedata_xml)
                debug_stats['t_parse_fxml']+=tdiff(st)

                
                Log.debug(etree.tostring(filedata_etree).decode())
                #if none found, mark it as nonexistent in the database.
                if not filedata_etree:
                    ArliDb.quick_update(
                        c,
                        (
                            ('existsStatus',
                             enums.EXISTS_STATUS.DELETED.value),
                        ),
                        'WHERE tmpId=?', (item['tmpId'],))
                    continue
                
                debug_stats['still exist'] += 1
                
                #otherwise get aggregate media data only available
                #in filedata.
                st=tn()
                totals = Learn._sum_filedata_totals(filedata_etree)
                debug_stats['t_get_totals']+=tdiff(st)
                            
                has_metadata = item['hasMetadata']
                if has_metadata == None:
                    has_metadata=enums.METADATA_STATUS.NONE.value
                
                rating = enums.RATING.UNRATED.value
                #if we don't have the metadata, and aggregate media data
                # indicates to keep it...
                st=tn()
                if (has_metadata == \
                   enums.METADATA_STATUS.NONE.value) and \
                   fetch_m_fq[0]['callback'](totals['size'], totals['length']):
                    debug_stats['passed fq'] += 1
                    debug_stats['t_fq']+=tdiff(st)
                    Log.debug('passed fq, retrieving metadata')
                    #download the metadata
                    st=tn()
                    metadata_xml = FetchInfo.as_str(item['ident'],
                                                    FetchInfo.METADATA)
                    debug_stats['t_fetch_mxml']+=tdiff(st)
                    st=tn()
                    metadata_etree = etree.fromstring(metadata_xml)
                    debug_stats['t_parse_mxml']+=tdiff(st)
                    Log.debug('metadata_etree')
                    Log.debug(etree.tostring(metadata_etree).decode())
                    matches = True
                    
                    #if it matches callbacks to keep it...
                    for i_mq in range(0, len(keep_m_mqs)):
                        mq = keep_m_mqs[i_mq]['callback']
                        item['metadata']=metadata_xml
                        item['totalAudioSize']=totals['size']
                        item['totalAudioLength']=totals['length']
                        stub=Stub.FromDict(item)
                        st=tn()
                        if not mq(stub):
                            debug_stats['t_mq']+=tdiff(st)
                            print("NO MATCH on mq {}".format(i_mq))
                            matches = False
                            break                    
                    if matches:
                        debug_stats['passed mqs'] +=1
                        Log.debug('keep_m_mqs all matched. writing xml to disk')
                        #store it so its usable by find()
                        #we can handle the amount of ram, given that we won't
                        # be storing more than 1k at a time at any point.
                        metadata_storage_queue.append((item['ident'], metadata_xml))
                        has_metadata = enums.METADATA_STATUS.STORED.value
                    #else if block_non_match:
                    #    has_metadata = METADATA_STATUS.BLOCKED
                    else:

                        rating = enums.RATING.SKIPPED.value
                        
                
                # update aggregate data, last checked date,
                # and status of existence and status of
                # metadata storage in db.
                st=tn()
                updates = (('totalAudioLength', totals['length']),
                           ('totalAudioSize', totals['size']),
                           ('checkedOnUnixDate', now),
                           ('rating', rating),
                           ('hasMetadata', has_metadata),
                           ('existsStatus',
                            enums.EXISTS_STATUS.EXISTS.value))
                ArliDb.quick_update(c,
                                    updates,
                                    'WHERE tmpId=?', (item['tmpId'],))
                debug_stats['t_update_exists']+=tdiff(st)

            adb.conn.commit()
            for metadata_pair in metadata_storage_queue:
                catalogue.store_metadata(*metadata_pair)
            metadata_storage_queue=[]
        for counter in debug_counters:
            Log.outline(counter + ':' + str(debug_stats[counter]))
    @staticmethod
    def cmd(args):
        catalogue=args['catalogue_path']
        media_type=args['media_type']
        minutes=args['wait']
        fetch_m_fq=args['fetch_m_fq']
        keep_m_mqs=args['keep_m_mqs']
        data_src=args['data_src']
        if data_src == None:
            Learn.from_web(
                catalogue=catalogue,
                media_type=media_type,
                minutes=minutes,
                fetch_m_fq=fetch_m_fq,
                keep_m_mqs=keep_m_mqs
            )
        else:
            Log.fatal('learn from other db not supported yet.')
            #really learn from other db should probably be a separate
            #subcommand with the option for sql filters instead of fqs, etc.
            
