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
from amiens.core import asserts
from amiens.core import util
from amiens.core.util import Log
from amiens.core.amiensdb import ArliDb

import subprocess
import time
import os

class AddIdents(Subcmd):
    
    @staticmethod
    def _from_identlist(adb, idents, is_new_db, media_type=enums.MTYPES.AUDIO):
        goal='merge in a list of identifiers'
        asserts.that(len(idents) > 0,
                'but the list of identifiers provided is empty.' \
                'This probably represents an error in retrieving or ' \
                'fetching the identifiers from the web')
        #UNTESTED    
        linectr=0
        c = adb.conn.cursor()
        for ident in idents:
            linectr+=1
            if (not is_new_db):
               res=ArliDb.quick_select(c, ('tmpid',), 'WHERE ident=?',
                                   (ident,), True)
               if len(res) > 0:
                    continue            
            instring="INSERT INTO items (ident, mediaType) VALUES (?,?)"
            util.Log.debug('I_sql: ' + instring)
            data=(ident, media_type.value)
            util.Log.debug('I_data: ' + repr(data))
            c.execute(instring, data)
            if linectr % 10000 == 0:
                print(str(linectr)+' added')
                #caching,writing much faster when lib handles it.
                adb.conn.commit()
                c = adb.conn.cursor()
        adb.conn.commit()
    
    @staticmethod
    def from_web(adb, is_new_db, media_type=enums.MTYPES.AUDIO):
        #UNTESTED
        goal='fetch a list of identifiers from the web'

        mtypestr=media_type.name
        outpath='/tmp/identList.'+str(int(time.time()))+'.csv'
        asserts.dne(goal, outpath)
        subprocess.call(['wget',
                         ('https://archive.org/advancedsearch.php?'
                          'q=mediatype%3A%28{}%29'
                          '&fl[]=identifier&sort[]=&sort[]=&sort[]='
                          '&rows=9999999&page=1'
                          '&output=csv'
                          '&callback=callback&save=yes').format(mtypestr),
                         '-O', outpath])
        AddIdents.from_file(adb, outpath, is_new_db, media_type)
        os.remove(outpath)
    
    @staticmethod
    def from_file(adb, l_ident, is_new_db, media_type=enums.MTYPES.AUDIO):
        #UNTESTED
        goal='asked to merge in identifier list at {}, '.format(l_ident)
        idents=[]
        #expect each line to be quoted.
        #TODO just rstrip and lstrip quotes in case some files are not?
        line_zero=True
        with util.debug_open(goal, l_ident, 'r') as f_idents:
            for line in f_idents:
                if line_zero:
                    line_zero=False
                    continue
                #rm trailing space and quotations
                idents.append(line.rstrip()[1:-1])
        AddIdents._from_identlist(adb, idents, is_new_db, media_type)
    
    @staticmethod
    def from_otherdb(adb, otherAdb, is_new_db, media_type=enums.MTYPES.AUDIO):
        #UNTESTED
        identlist=[x[0] for x in otherAdb.one_off_select(('ident',),
                                          'WHERE mediaType=?',
                                          (media_type,), True)]
        AddIdents._from_identlist(adb, identlist, is_new_db, media_type)

    @staticmethod
    def cmd(args):
        adb = args['catalogue_path'].adb
        is_new_db = args['is_new_db']
        media_type = args['media_type']
        data_src = args['data_src']
        #TODO confirm media type received here is same as needed.
        if data_src == None:
            AddIdents.from_web(adb, is_new_db, media_type)
        elif type(data_src) == str:
            AddIdents.from_file(adb, data_src, is_new_db, media_type)
        else:
            AddIdents.from_otherdb(adb, data_src, is_new_db, media_type)
