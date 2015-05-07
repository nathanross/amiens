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

from arli.core import asserts
from arli.core import util
from arli.core.util import Log

import sqlite3

class ArliDb():
    
    def __init__(self, l_db):
        #UNTESTED
        goal='asked to connect to db at {}, '.format(l_db)
        util.Log.debug('opening database at ' + l_db)
        asserts.exists(goal, l_db)
        self.conn = sqlite3.connect(l_db)

    def one_off_update(self, colvalpairs, query_filter, data):
        ArliDb.quick_update(self.conn.cursor(),
                              colvalpairs, query_filter, data)
        self.conn.commit()

    def one_off_select(self, cols, query_filter='', data=[], return_raw=False):
        return ArliDb.quick_select(self.conn.cursor(),
                                   cols, query_filter, data, return_raw)

    @staticmethod
    def quick_update(cursor, colvalpairs, query_filter, data):
        cols, vals = zip(*colvalpairs)
        vals = list(vals)
        vals.extend(data)

        
        q=''.join(['UPDATE items SET ',
                   '=?, '.join(cols),
                   '=? ', 
#        postgres
#        q=''.join(['UPDATE items SET (',
#                   '=?, '.join(cols),
#                   ') = (',
#                   ''.join(['?' for c in cols]),
#                   ') ',
                   query_filter])
        Log.debug('U_sql:'+q)
        Log.debug('U_data:'+repr(vals))
        cursor.execute(q, vals)

        
    @staticmethod
    def quick_select(cursor,
                     cols, query_filter='', data=[],
                     return_raw=False):
        c = cursor
        sqlstr=''.join(['SELECT ',
                           ', '.join(cols),
                           ' FROM items ',
                           query_filter])
        Log.debug('Q_sql: ' + sqlstr)
        Log.debug('Q_data: ' + repr(data))
        c.execute(sqlstr, data)
        if return_raw:
            return c.fetchall()
        tmpresults= c.fetchall()
        results = [ ]
        for x in tmpresults:
            row={}
            for i in range(0, len(cols)):
                row[cols[i]] = x[i]
            results.append(row)
        return results
    
    @classmethod
    def create_new(cls, l_db):
        #UNTESTED
        goal='asked to create db at {}, '.format(l_db)
        asserts.dne(goal, l_db)
        
        conn = sqlite3.connect(l_db)
        c = conn.cursor()
        c.execute('''CREATE TABLE items
        (tmpId INTEGER PRIMARY KEY AUTOINCREMENT, ident TEXT, mediaType INTEGER, existsStatus INTEGER, totalAudioLength INTEGER, totalAudioSize INTEGER, checkedOnUnixDate INTEGER, hasMetadata INTEGER, metadata TEXT, blockDownload INTEGER, rating INTEGER, comment TEXT)''')
        conn.commit()
        conn.close()
        return cls(l_db)
