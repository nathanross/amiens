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
from amiens.core.util import Log, LogSeverity
from amiens.core.amiensdb import ArliDb

import defusedxml.ElementTree as etree
import time
from math import ceil
import re
import random
import threading

#note this also means max simultaneous HTTP requests to archive.org
MAX_THREADS=1
_tn = lambda : time.time()
_tdiff = lambda z: (time.time()) - z
        
def _StubBuilder():
    return { 'tmpId':None,
             'ident':None,
             'totalAudioLength':None,
             'totalAudioSize':None,
             'metadata':None,
             'rating':0,
             'comment':'',
             'existsStatus':None,
             'checkedOnUnixDate': None,
             'hasMetadata':None,
             # special key value only for learn.
             # no reason for a persistent enum val for hasMetadata
             # regarding whether fq has passed if its information
             # that is generated and only needed within the course
             # of a single learn call.
             # IS redundant with stats['passed_fq'] but don't want
             # to use that, better to keep everything in stats strictly
             # for debugging, rather than pollute it with sidechannel usage.

             'seekingMetadata':False,
             'stats': {
                 'passed fq':False,
             }
         }

class Learn(Subcmd):
    RE_FLOAT=re.compile('^\d+(\.\d+)?$')
    RE_M_S=re.compile('^(\d+):(\d\d?)$')
    RE_H_M_S=re.compile('^(\d+):(\d\d?):(\d\d?)$')

    @staticmethod
    def getLearningTargets(c, offset, step_size):
        filter_sql=('WHERE ((tmpId+{}) % {} = 0) '
             'AND ((checkedOnUnixDate < 0) OR (checkedOnUnixDate IS NULL)) '
             'AND ((existsStatus IS NULL) OR (existsStatus < ?)) '
             'AND (rating = ? OR rating = ?) LIMIT 1000').format(offset,
                                                                 step_size)
        return ArliDb.quick_select(
            c,
            ('tmpId', 'ident', 'hasMetadata', 'rating', 'comment'),
            filter_sql,
            # we don't filter by has metadata, because we reserve
            # the right for the learn process to not necessarily update
            # metadata, so not having metadata isn't an indicator
            # of priority to be checked.
            (enums.EXISTS_STATUS.DELETED.value,
             enums.RATING.UNRATED.value,
             enums.RATING.CONFIRM_UNRATED.value))
    
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
                    length_el=f.find('length')
                    if not (length_el == None) and \
                       not (length_el.text == None) and \
                       not (length_el.text == ''):
                        if totals['length'] == None:
                            totals['length'] = 0
                        lengthval=f.find('length').text
                        if re.match(Learn.RE_FLOAT, lengthval):
                            # seconds
                            totals['length'] += int(round(float(lengthval)))
                        elif re.match(Learn.RE_M_S, lengthval):
                            # minutes:seconds
                            m, s = \
                            [ int(x) for x in re.match(Learn.RE_M_S,
                                                       lengthval).groups() ]
                            totals['length'] += m*60 + s
                        elif re.match(Learn.RE_H_M_S, lengthval):
                            # hours:minutes:seconds
                            h, m, s = \
                             [ int(x) for x in re.match(Learn.RE_H_M_S,
                                                        lengthval).groups() ]
                            totals['length'] += h*3600 + m*60 + s
                        else:
                            Log.warning(('couldnt successfully interpret'
                                        'length value <{}>').format(val))
                            unknowable_length = True
                            totals['length'] = None
                    else:
                        unknowable_length = True
                        totals['length'] = None                    

        return totals
    
    @staticmethod
    def get_xmls(item, fq, threadsafe_list, msg_log):
        
        result = _StubBuilder()
        for field in ('tmpId', 'ident', 'hasMetadata', 'rating', 'comment'):
            result[field] = item[field]
            
        msg_log.append((LogSeverity.DATA,
                       'updating item {}'.format(item['tmpId'])))

        #parse file data
        #filedata_etree = FetchInfo.as_etree(
        #    item['ident'], FetchInfo.FILEDATA)
        filedata_xml = FetchInfo.as_str(item['ident'],
                                        FetchInfo.FILEDATA)
        filedata_etree = etree.fromstring(filedata_xml)
        
        msg_log.append((LogSeverity.DEBUG,
                        etree.tostring(filedata_etree).decode()))
        if not filedata_etree:
            #if none found, mark it as nonexistent in the database.
            result['existsStatus'] = enums.EXISTS_STATUS.DELETED.value
        else:
            result['existsStatus'] = enums.EXISTS_STATUS.EXISTS.value
            #otherwise get aggregate media data only available
            #in filedata.
            totals = Learn._sum_filedata_totals(filedata_etree)
            msg_log.append((LogSeverity.DEBUG,
                            'totals are:'+repr(totals)))
            result['totalAudioLength'] = totals['length']
            result['totalAudioSize'] = totals['size']
            rprev=result['rating']
            RATING=enums.RATING
            #for now we assume only one fq otherwise there are
            # complications with sql filter chaining.
            if (rprev == RATING.UNRATED.value or \
               rprev == RATING.CONFIRM_UNRATED.value) and \
               fq['callback'](totals['size'], totals['length']):
                msg_log.append((LogSeverity.DEBUG, 'passed FQ'))
                result['stats']['passed fq'] = True
                result['seekingMetadata'] = True
            if result['seekingMetadata'] or \
               rprev >= RATING.BAD.value:
                msg_log.append((LogSeverity.DEBUG, 'downloading metadata'))
                result['metadata'] = FetchInfo.as_str(item['ident'],
                                               FetchInfo.METADATA)
        threadsafe_list.append(result)
        
    @staticmethod
    def filter_new_metadata(return_queue, mqs, debug_stats):
        metadata_storage_queue=[]
        for result in return_queue:
            # even if updating an item, metadata is
            # set to None unless the fq was passed.
            Log.debug('in regard to result '+result['ident'])
            if result['seekingMetadata'] == False:
                Log.force('not seeking metadata')
                if result['metadata']:
                    debug_stats['updated (no fq,mq)'] +=1
                continue
            st=_tn()
            Log.debug(result['metadata'])
            metadata_etree = etree.fromstring(result['metadata'])
            debug_stats['t_parse_mxml']+=_tdiff(st)
            matches = True
            stub=Stub.FromDict(result)
            st=_tn()
            #if it matches callbacks to keep it...
            for i_mq in range(0, len(mqs)):
                mq = mqs[i_mq]['callback']
                if not mq(stub):
                    Log.debug("NO MATCH on mq {}".format(i_mq))
                    matches = False
                    break
            debug_stats['t_mq']+=_tdiff(st)
            if matches:
                debug_stats['passed mqs'] += 1
                Log.debug('keep_m_mqs all matched. writing xml to disk')
                #store it so its usable by find()
                #we can handle the amount of ram, given that we won't
                # be storing more than 1k at a time at any point.
                metadata_storage_queue.append(
                    (result['ident'], result['metadata']))
                result['hasMetadata'] = enums.METADATA_STATUS.STORED.value
                #else if block_non_match:
                #    has_metadata = METADATA_STATUS.BLOCKED
                return metadata_storage_queue
            else:
                result['rating'] = enums.RATING.SKIPPED.value
        return metadata_storage_queue
    
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
        debug_counters=(
            'checked',
            'still exist',
            'passed fq',
            'updated (no fq,mq)',
            'passed mqs',
            't_select',
            't_fetch_xmls',
            't_parse_mxml',
            't_mq',
            't_update_exists',
        )
        debug_stats = {}
        for counter in debug_counters:
            debug_stats[counter] = 0
            
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
        
        while (now - start_unixtime) < minutes*60 :
            now = int(time.time())
            offset=random.randint(0, step_size-1)
            #randint is inclusive on both ends.
            c = adb.conn.cursor()            
            # for now, just only look at idents
            # we've never looked at before.
            # if we ever run out of those,
            # not likely, we can change this code.
            # todo (AND NOT = exists_status enumval)
            # instead of (AND < enum val)
            st=_tn()
            items=Learn.getLearningTargets(c, offset, step_size)
            debug_stats['t_select']+=_tdiff(st)
            if len(items) == 0:
                Log.fatal('couldnt find any candidates for learning,'
                          'please get some idents.')
            
            st=_tn()
            threads = []
            ident_index=0            
            
            return_queue=[]
            wait_interval=0.5/MAX_THREADS
            past_time_limit=False
            while (ident_index < len(items) and not past_time_limit) or \
                  len(threads) > 0:
                past_time_limit=(_tn() - start_unixtime) > minutes*60
                # if we have items available, and are tracking less threads
                # than the maximum, create a new therad.
                if not past_time_limit and \
                   len(threads) < MAX_THREADS and \
                   ident_index < len(items):
                    Log.force('creating new thread')
                    message_log=[]
                    newthread=threading.Thread(
                            target=Learn.get_xmls,
                            args=(
                                items[ident_index],
                                fetch_m_fq[0],
                                return_queue,
                                message_log
                            )
                        )
                    threads.append((newthread, message_log))
                    newthread.start()
                    debug_stats['checked'] += 1
                    ident_index += 1
                time.sleep(wait_interval)
                i=0
                # go through threads and stop keeping track of
                # completed ones
                while i < len(threads):
                    Log.force('checking thread at position {}'.format(repr(i)))
                    if threads[i][0].is_alive():
                        Log.force('thread still alive')
                        i+=1
                        continue
                    Log.force('thread complete, printing logs '
                              'then clearing position')
                    for msg in message_log:
                        Log.log(msg[0], msg[1])
                    threads.__delitem__(i)            
            debug_stats['t_fetch_xmls']+=_tdiff(st)
            # updates
            # never happen in the first place, (as its not a good
            # ROI when most items dont change and there are a
            # for practical purposes infinite number of unchecked
            # items where bandwidth, processor, and time of fetching
            # their XML will be worth it) 
            
            # rather than dealing with thread-safe writes to 4-5
            # different objects for multiple conditions, just
            # deal with threadsafe (though out-of-order is fine)
            # additions to one queue and process those. Remember,
            # we're network-IO-bound, not processing or db-io bound
            # (also GIL prevents threads from helping with processing time)
            # so its find to keep processing and db-io stuff
            # singlethreaded

            Log.force('done fetching xmls')
            metadata_storage_queue=Learn.filter_new_metadata(
                return_queue,
                keep_m_mqs,
                debug_stats
            )
            
            for result in return_queue:
                if result['existsStatus'] == \
                   enums.EXISTS_STATUS.EXISTS.value:
                    debug_stats['still exist'] += 1
                    if result['stats']['passed fq']:
                        debug_stats['passed fq'] +=1
                    update_fields=('totalAudioLength',
                                   'totalAudioSize',
                                   'rating',
                                   'existsStatus',
                                   'checkedOnUnixDate',
                                   'hasMetadata')
                else:
                    update_fields =('existsStatus', 'checkedOnUnixDate')
                update_keyvals = [ (x, result[x]) for x in update_fields]
                st=_tn()
                ArliDb.quick_update(c,
                                    update_keyvals,
                                    'WHERE tmpId=?', (result['tmpId'],))
                
                debug_stats['t_update_exists']+=_tdiff(st)
            adb.conn.commit()
            for metadata_pair in metadata_storage_queue:
                catalogue.store_metadata(*metadata_pair)

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
            
