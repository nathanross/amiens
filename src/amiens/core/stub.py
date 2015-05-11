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

from amiens.core import util
from amiens.core.enums import DOWNLOADED

import subprocess
import shutil
import glob
import re

class Stub:
    def __init__(self, tmp_id, ident, metadata,
                 length=None,
                 download_level=DOWNLOADED.NONE.value,
                 download_lock=0, rating=None, comment=None):
        self.data={
            tmpId: tmp_id,
            ident: ident,
            length: length,
            metadata: metadata,
            downloadLevel: download_level,
            downloadLock : download_lock,
            rating: rating,
            comment: comment
        }
        self.l_src=None

    #you're going to want to install unrar, p7zip, unzip
    @staticmethod
    def _extractArchives(l_d_out, fnames):
        archives=[]
        ext_match=lambda x,y:re.match('.*\.('+'|'.join(x)+')$', y)
        for fname in fnames:            
            if ext_match(['7z','tar\.gz','tgz','tar','zip','rar'],
                         fname):
                archives.append(fname)
        extract_dir=l_d_out
        for fname in archives:
            l_arch=l_d_out+'/'+fname
            if len(archives) > 1:
                #don't truncate filename as may have multiple archives
                # of same name but different ext
                extract_dir=l_d_out+'/d_'+fname                
            if ext_match(['tgz','tar', 'tar\.gz'], fname):
                subprocess.call(['tar', '-xf', fname, '-C', extract_dir])
            elif ext_match(['7z'], fname):
                subprocess.call(['7zr', 'x', '-o', extract_dir, fname])
            elif ext_match(['zip'], fname):
                subprocess.call(['unzip', fname, '-d', extract_dir])
            elif ext_match(['rar'], fname):
                subprocess.call(['unrar', 'x', fname, extract_dir])

    # you're going to want to install
    #    sox libsox-fmt-mp3 mac flac avconv
    # only sets length value if it is SURE that we have the complete
    # length. returns length value in db (e.g. None if not have complete val).
    # Example, if one of the files is a large .xyz file
    # and we don't know how to read .xyz files (but are not sure
    # that they are not audio or video), we return a length of None
    # and make no change to the db
    def _getLength(adb, ident, l_d_out):
        if self.data['length'] != None:
            return (True, self.data['length'])
        read_soxi=['soxi', '-D']
        ext_match=lambda x,y:re.match('.*\.('+'|'.join(x)+')$', y)
        exts_readable=((['mp3','ogg','flac','wav'], soxi),)
        #to ignore even if above 30kb
        exts_ignore=['jpg', 'png', 'bmp', 'gif', 'pdf']
        length=0
        KILOBYTES=1024
        SKIP_SIZE=30*KILOBYTES
        has_unknowns=False
        for f in os.walk(l_d_out):
            fpath=f[0]
            length_success=False
            for read_method in exts_readable:
                if ext_match(read_method[0], fpath):
                    length_get=deepcopy(read_method[0])
                    length_get.append(fpath)
                    length += float(
                        subprocess.check_output(length_get)
                    )
                    length_success=True
                    break
            
            if length_success or \
               ext_match(exts_ignore, fpath) or \
               os.path.getsize(fpath) < SKIP_SIZE:
                continue
            length=None
            Log.warn('couldnt get length of file: '+fpath+\
                     ' skipping evaluation of this directory'+\
                     ' based on length')
            break
        if length != None:
           adb.one_off_update(
               ('length', length),
               'WHERE tmpId=?',
               (self.data['tmpId'],)
           )
        self.data['length']=length
        return length
        
    def _downloadFnames(self, adb, l_d_out, fnames):
        urls = []
        for fname in fnames:
            # we can use https in the below url,
            # but it makes most files go about 1/4 speed.        
            f_url='http://archive.org/download/{0}/{1}'
            f_url=f_url.format(self.data['ident'], fname)
            urls.append(f_url)
        if len(urls) == 0:
            return True
        wget_call=['wget', '-P ', l_d_out]
        wget_call.extend(urls)
        err_code=subprocess.call(wget_call)
        if err_code != 0:
            util.Log.fatal('download error')
            #return False
        
        # sox, libsox-fmt-mp3
        Stub._extractArchives(l_d_out, fnames)        
        
        return True
        
    def _downloadTo(self, adb, fq, scratchdir, l_d_out, quality):        
        filedata_etree = _FetchInfo.as_etree(self.data['ident'],
                                             _FetchInfo.METADATA)
        fnames=[]
        if quality == DOWNLOADED.ORIGINAL.value:
            for f in filedata_etree:
                if f.get('source') == 'original':
                    fnames.append(f.get('name'))
                orig_dir=scratchdir+'/original'
                os.makedirs(orig_dir)
                self._downloadFnames(adb, self.data['ident'],
                                     orig_dir, fnames)
                length=self._getLength(adb, orig_dir)
                if not fq(self.data['size'], length):
                    shutil.rmtree(orig_dir)
                    return True
                
        shutil.move(
            glob.glob(scratchdir+'/*'),
            l_d_out
        )
        
    def write(self, adb, fq, arg_scratchdir, l_out=None):
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
        scratchdir=arg_scratchdir.rstrip('/')
        
        l=''        
        if l_out == None:
            l=self.l_src
            if self.l_src == None:
                raise 'no idea where to write this stub to...'  
        else:
            l=l_out.rstrip('/')
            if self.l_src == None:
                self.l_src=l_out
                
        goal = "write item stub {}".format(l)

        towrite = deepcopy(self.data)

        now=time.time()

        towrite['downloadLock'] = now
        if (os.path.exists(l)):
            old_stub=util.json_read(goal, l)            
            towrite['downloadLevel'] = old_stub['downloadLevel']
            if old_stub['downloadLevel'] >= self.data['downloadLevel'] or \
            ((old_stub['downloadLock'] + 60*60*24) > now) :
                towrite['downloadLock'] = old_stub['downloadLock']
        else:
            towrite['downloadLevel'] = 0

        util.json_write(goal, l, towrite)
        
        if self.data['downloadLevel'] > towrite['downloadLevel']:
            try:
                towrite['downloadLevel'] = Stub._downloadTo(
                    adb,
                    fq,
                    scratchdir,
                    l,
                    self.data['downloadLevel']
                )
            except:
                pass
        
        towrite['downloadLock'] = 0
        util.json_write(goal, l, towrite)
    
            
    @classmethod
    def FromDict(cls, d):
        if not ('downloadLevel' in d):
            d['downloadLevel']=0
        if not ('downloadLock' in d):
            d['downloadLock']=False
        return cls(d.tmpId, d.ident,
                   d.metadata, d.downloadLevel, d.downloadLock,
                   d.rating, d.comment)
    @classmethod
    def FromFile(cls, l_in):
        goal = "read item stub {}".format(l_in)
        return Stub.FromDict(cls, json.loads(full_read(goal, l_in)))
    
    def path_from_rootdir(self, outdir):
        #creates directory for stubfile and returns stub path
        dest=outdir+'/'+self.data.ident
        if not (os.access(dest, 0)):
            os.makedirs(dest)
        return dest+'/.amiens.json'
