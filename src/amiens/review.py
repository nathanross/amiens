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
from amiens.core.util import Log
from amiens.core import enums

class Review(Subcmd):

    @staticmethod
    def cmd(args):
        adb = args['catalogue_path'].adb
        item = args['item']
        for key in ('rating', 'comment'):
            if args[key] == None:
                continue
            val=args[key]
            if val == item.data[key]:
                continue
            item.data[key] = val
            adb.one_off_update(((key, val),),
                               'WHERE tmpId=?',
                               (item.data['tmpId'],))            
            item.write(adb, None, None)
        tmpresult=adb.one_off_select(
            ('comment', 'rating'),
            'WHERE tmpId=?',
            (item.data['tmpId'],))[0]
        Log.writes('comment:'+repr(tmpresult['comment']))
        Log.writes('rating:'+\
                   list(enums.RATING.__members__)[tmpresult['rating']])
