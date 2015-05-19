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
from amiens.core import util
from amiens.core.util import Log
from amiens.core import enums
from amiens.core.stub import Stub

class Find(Subcmd):
    @staticmethod
    def find(catalogue, fq, mqs=[], result_limit=1000, test_limit=100000):
        adb = catalogue.adb
        sql_filter_str='WHERE blockDownload =? AND hasMetadata=? AND (rating is not ? AND rating is not ? AND rating is not ? AND rating is not ?) {} LIMIT ?'
        sql_filter_str=sql_filter_str.format(fq['sql'])
        Log.debug('sql:'+sql_filter_str)
        tmpresults=adb.one_off_select(
            ('tmpId', 'ident', 'rating', 'comment', 'totalAudioLength', 'totalAudioSize'),
            sql_filter_str,
            ( enums.DOWNLOADED.NONE.value,
              enums.METADATA_STATUS.STORED.value,
              enums.RATING.SKIPPED.value,
              enums.RATING.CONFIRM_SKIPPED.value,
              enums.RATING.MANUAL_SKIP.value,
              enums.RATING.TOSS.value,
              test_limit)
        )
        results = []
        i=0
        for r in tmpresults:
            r['metadata'] = catalogue.get_metadata(r['ident'])
            stub = Stub.FromDict(r)
            match=True
            for filt in mqs:
                if not filt['callback'](stub):
                    match=False
                    break
            if match:
                results.append(stub)
                i+=1
                if i==result_limit:
                    break
        return results

    @staticmethod
    def cmd(args):
        catalogue = args['catalogue_path']
        outdir = args['outdir']
        scratchdir = args['scratchdir']
        download = args['download']
        quality = args['quality']
        
        stublist = Find.find(catalogue,
                             args['filter_fq'][0],
                             args['mqs'],

                             args['result_limit'],
                             args['test_limit'])
        
        # we do a redundant write for each stub
        # so that a placeholder for each is present
        # when we begin downloading in earnest.
        for stub in stublist:
            stub.write(catalogue.adb,
                       args['filter_fq'][0],
                       scratchdir,
                       l_out=stub.path_from_rootdir(outdir))
            
        if download:
            for stub in stublist:
                stub.data['downloadLevel']=quality
                stub.write(catalogue.adb,
                           args['filter_fq'][0],
                           scratchdir,
                           l_out=stub.path_from_rootdir(outdir))
