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

from amiens.core import enums
from amiens.core import util
from amiens.core.fetchinfo import FetchInfo
from amiens.core.util import Log
from amiens.core.enums import DOWNLOADED

import subprocess
import shutil
import glob
from copy import deepcopy
import time
import re
import os
from os import path

class Stub:
    def __init__(self, tmp_id, ident, metadata,
                 length=None, size=None,
                 download_level=DOWNLOADED.NONE.value,
                 download_lock=0, rating=None, comment=None):
        self.data={
            'tmpId': tmp_id,
            'ident': ident,
            'totalAudioLength': length,
            'totalAudioSize': size,
            'metadata': metadata,
            'downloadLevel': download_level,
            'downloadLock' : download_lock,
            'rating': rating,
            'comment': comment
        }
        self.l_src=None

    @staticmethod
    def irrelevant_to_length(fname, fsize):
        ext_match=lambda x,y:re.match('.*\.('+'|'.join(x)+')$', y)
        # files that are definitely not audio or video,
        # but may commonly be of > ~30kb size and accompany
        # music items. It is important to know to ignore these,
        # because otherwise an item where all the music files
        # have known lengths could become an item with total
        # length not-automatically-knowable if it didn't know
        # this jpg, doc, etc was not an audio or video file.
        exts_ignore=['jpg', 'png', 'bmp', 'gif', 'pdf', 'xml', 'txt', 'doc', 'odt', 'sqlite']
        KILOBYTES=1024
        SKIP_SIZE=30*KILOBYTES
        return (ext_match(exts_ignore, fname) or \
               fsize < SKIP_SIZE)


        
    #you're going to want to install unrar, p7zip, unzip
    @staticmethod
    def _extractArchives(l_d_out, fnames):
        archives=[]
        Log.outline('called with l_d_out {}, fnames {}'.format(
            l_d_out, repr(fnames)            
        ))
        ext_match=lambda x,y:re.match('.*\.('+'|'.join(x)+')$', y)
        for fname in fnames:
            Log.force('testing if is archive:<'+fname+'>')
            if ext_match(['7z','tar\.gz','tgz','tar','zip','rar'],
                         fname):
                Log.force('-- matches as archive --')
                archives.append(fname)
        extract_dir=l_d_out
        for fname in archives:
            l_arch=l_d_out+'/'+fname
            Log.force('what kind of archive is <'+fname+'>')
            if len(archives) > 1:
                #don't truncate filename as may have multiple archives
                # of same name but different ext
                extract_dir=l_d_out+'/d_'+fname                
            if ext_match(['tgz','tar', 'tar\.gz'], fname):
                cmd=['tar', '-xf', l_arch, '-C', extract_dir]
            elif ext_match(['7z'], fname):
                Log.force('its 7zip')
                cmd=['7zr', 'x', '-o'+extract_dir, l_arch] 
            elif ext_match(['zip'], fname):
                cmd=['unzip', l_arch, '-d', extract_dir] #tested.
            elif ext_match(['rar'], fname):
                cmd=['unrar', 'x', l_arch, extract_dir]
            Log.data('unarchive cmd is...<{}>'.format(' '.join(cmd)))
            subprocess.call(cmd)
            if path.exists(l_arch):
                os.remove(l_arch)

    # you're going to want to install
    #    sox libsox-fmt-mp3 mac flac avconv
    # only sets length value if it is SURE that we have the complete
    # length. returns length value in db (e.g. None if not have complete val).
    # Example, if one of the files is a large .xyz file
    # and we don't know how to read .xyz files (but are not sure
    # that they are not audio or video), we return a length of None
    # and make no change to the db
    def _getLength(self, adb, l_d_out):
        Log.outline('called with l_d_out of {}, also self.data.totalAudiolength is {}'.format(
            l_d_out, repr(self.data['totalAudioLength'])
        ))
        if self.data['totalAudioLength'] != None:
            return self.data['totalAudioLength']
        read_soxi=['soxi', '-D']
        ext_match=lambda x,y:re.match('.*\.('+'|'.join(x)+')$', y)
        exts_readable=((['mp3','ogg','flac','wav'], read_soxi),)
        #to ignore even if above 30kb
        length=0
        has_unknowns=False

        for d in os.walk(l_d_out):
            path_d=d[0]
            for f in d[2]:
                fpath=path_d + '/' + f
                Log.data('checking length of file {}'.format(fpath))
                length_success=False
                if Stub.irrelevant_to_length(fpath, path.getsize(fpath)):
                    continue

                for read_method in exts_readable:
                    if ext_match(read_method[0], fpath):
                        length_get=deepcopy(read_method[1])
                        length_get.append(fpath)
                        Log.force('total length before calling read method:'+repr(length))
                        length += float(
                            subprocess.check_output(length_get)
                        )
                        Log.force('total length AFTER calling read method:'+repr(length))
                        length_success=True
                        break

                if not (length_success):
                    length=None
                    Log.warning('couldnt get length of file: '+fpath+\
                         ' skipping evaluation of this directory'+\
                         ' based on length')
                    break
            if not length_success:
                break        
        if length != None:
            length = int(round(length))
            adb.one_off_update(
                (('totalAudioLength', length),),
                'WHERE tmpId=?',
                (self.data['tmpId'],)
            )           
        Log.force(str(length))
        self.data['totalAudioLength']=length
        return length
        
    def _downloadFnames(self, adb, l_d_out, fnames):
        Log.outline('called with l_d_out {}, fnames {}'.format(
            l_d_out, repr(fnames)
        ))
        urls = []
        for fname in fnames:
            # we can use https in the below url,
            # but it makes most files go about 1/4 speed.        
            f_url='http://archive.org/download/{0}/{1}'
            f_url=f_url.format(self.data['ident'], fname)
            urls.append(f_url)
        if len(urls) == 0:
            return True
        wget_call=['wget', '-P', l_d_out]
        wget_call.extend(urls)
        Log.data(' '.join(wget_call))
        err_code=subprocess.call(wget_call)
        if err_code != 0:
            Log.warning('err_code:{}'.format(str(err_code)))
            #return False
        
        # sox, libsox-fmt-mp3
        Stub._extractArchives(l_d_out, fnames)        
        
        return True
        
    def _downloadOrchestrator(self, adb, fq, scratchdir, l_d_out, quality):        
        filedata_etree = FetchInfo.as_etree(self.data['ident'],
                                             FetchInfo.FILEDATA)        
        fnames=[]
        
        Log.outline(
            'called w/ scratchdir: {}, l_d_out: {}, quality: {}'.format(
            scratchdir, l_d_out, repr(quality)
        ))
        if quality == DOWNLOADED.ORIGINAL.value:
            for f in filedata_etree:
                Log.force(repr(f))
                if f.get('source') == 'original':
                    fnames.append(f.get('name'))
            orig_dir=scratchdir+'/original'                
            os.makedirs(orig_dir)
            self._downloadFnames(adb,
                                 orig_dir, fnames)
            length=self._getLength(adb, orig_dir)
            Log.force('length_final:'+repr(length))
            if not fq['callback'](self.data['totalAudioSize'], length):
                shutil.rmtree(orig_dir)
                return True

        for subdir in glob.glob(scratchdir+'/*'):
            shutil.move(
                subdir,
                l_d_out
            )
        adb.one_off_update(
            (('blockDownload', enums.BLOCKDOWNLOAD.DOWNLOADED.value),),
            'WHERE tmpId=?',
            (self.data['tmpId'],)
        )           
        
    def write(self, adb, fq, arg_scratchdir, l_out=None):
        Log.outline('ident:'+self.data['ident'])
        #this system has FILESYSTEM lock,
        # but not OBJECT lock.

        # The way this deals with resource contention for filesystem lock is:
        #  - if there's currently files downloaded that are same or higher qual.
        #     level
        #     than that requested, no action is taken, and the stub file's
        #     download level is not altered.
        #  - if the files downloaded are of lower quality, the first write
        #     of higher quality (incl. the initial download) places a LOCK
        #     in the stub of the timestamp to begin download, without changing
        #     the level in the stub.
        #  - once a download completes the LOCK is set to 0, and the download
        #    level is updated to reflect the current quality level completely
        #    downloaded.
        #  - for 24 hours after a lock's placement in a file,
        #    additional write requests
        #    higher the current completely downloaded quality level are
        #    simply ignored.

        #    This means NO PRE-EMPTION or QUEUEING.
        #     So if you are downloading SD in one process,
        #     and then (optionally canceling the first) begin downloading HD
        #     in another, the HD request will be cancelled and you will be
        #     informed of this. to switch quality you have to cancel
        #     the first process and set the lock to 0 in the stub, or wait until
        #     the process completes then re-request.

        #   IN THE FUTURE THIS MAY BE OVERWRITTEN
        #     e.g. add a queuedDownload level, have the download functions
        #        run a callback which polls the stub at a regular interval
        #        to see if the queuedDownload level has increased,
        #        if so, cancels download.
        #        alternatively, each download folder could have a .lock
        #        file which is checked, so that behavior where download q2, then
        #        download q3 a minute later leads to the same behavior whether
        #        q2 finishes rdownloading before the 2nd request or not. we could
        #        also use an array of locks in the stub instead of lock files.
        #
        #     the second option is probably the best, but a bit complicated.
        #     i think if we are not going to do it right, let's just keep
        #     it simple until we do.

        
        l=''        
        if l_out == None:
            l=self.l_src
            if self.l_src == None:
                raise 'no idea where to write this stub to...'  
        else:
            l=l_out.rstrip('/')
            if self.l_src == None:
                self.l_src=l_out
                

        towrite = deepcopy(self.data)

        now=time.time()
        
        l_json=l+'/.amiens.json'
        goal = "write item stub {}".format(l_json)
        towrite['downloadLock'] = now
        still_locked=False
        if (path.exists(l_json)):
            old_stub=util.json_read(goal, l_json)            
            towrite['downloadLevel'] = old_stub['downloadLevel']

            lower_quality=old_stub['downloadLevel'] >= self.data['downloadLevel']
            still_locked=((old_stub['downloadLock'] + 60*60*24) > now)
            if lower_quality or still_locked:
                towrite['downloadLock'] = old_stub['downloadLock']
        else:
            # downloadLevel in the stub file should only be the COMPLETED
            # downloadfile, and not reflect any download in progress
            # that a download is in progress is conveyed by the download
            # lock.
            towrite['downloadLevel'] = 0
        
        util.json_write(goal, l_json, towrite)

        Log.force(repr(self.data['downloadLevel']))
        Log.force(repr(towrite['downloadLevel']))
        if self.data['downloadLevel'] > towrite['downloadLevel'] and \
           not still_locked:
            scratchdir=arg_scratchdir.rstrip('/')
            Log.outline('trying to download')
            towrite['downloadLevel'] = self._downloadOrchestrator(
                adb=adb,
                fq=fq,
                scratchdir=scratchdir,
                l_d_out=l,
                quality=self.data['downloadLevel']
            )
        
        towrite['downloadLock'] = 0
        util.json_write(goal, l_json, towrite)
    
            
    @classmethod
    def FromDict(cls, d):
        if not ('downloadLevel' in d):
            d['downloadLevel']=0
        if not ('downloadLock' in d):
            d['downloadLock']=False
        return cls(d['tmpId'], d['ident'],
                   d['metadata'],
                   d['totalAudioLength'],
                   d['totalAudioSize'],
                   d['downloadLevel'],
                   d['downloadLock'],
                   d['rating'], d['comment'])
    
    @classmethod
    def FromPath(cls, l_in):        
        f_src=l_in
        if (path.exists(l_in) and path.isdir(l_in)):
            f_src=l_in.rstrip('/') + '/.amiens.json'
        goal = "read item stub {}".format(f_src)
        return Stub.FromDict(util.json_read(goal, f_src))
        
        
    def path_from_rootdir(self, outdir):
        #creates directory for stubfile and returns stub path
        dest=outdir+'/'+self.data['ident']
        if not (path.exists(dest)):
            os.makedirs(dest)
        return dest
