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

#!/bin/python3

def audio_strict_long_hq(s, l):
    # strict means if we don't have
    # requisite information about the file,
    # skip it.
    # (e.g. for files that means m4as which we can't get length for.)
    #print('length:'+repr(l))    
        #print('skipping')
        #return False
    #if length < 20 min. skip.
    min_minutes = 20
    if l == None:
        print('using default length')
        l = (1+min_minutes) * 60
    print('length:'+repr(l))    
    if l < (min_minutes * 60):
        #print('less than {}, skipping'.format(min_minutes*60))
        return False

    print('size:'+repr(s))    
    bytes_per_second=(s/l)
    kbps=bytes_per_second*(8/1024.)
    print('kbps:'+repr(kbps))    
    
    target_min_kbps=192
    # note that even when set to a cbr, there's going
    # to sometimes be size variance /below/ that cbr
    # 0.96x-4 is an initial wild guess of a
    # generous lower bound.
    if kbps < ((target_min_kbps*0.96)-4):
        print('skipping as is less than target {}'.format(((target_min_kbps*0.96)-4)))
        return False
    return True

callback=audio_strict_long_hq

#chaneg these constants.
GOAL_TARGET_KBPS=192.
MIN_MINUTES=20

TARGET_KBPS=((GOAL_TARGET_KBPS*0.96)-4)
BYTE_PS_TO_KBPS=(8/1024.)

sql='AND totalAudioSize > ' + \
    str((TARGET_KBPS/BYTE_PS_TO_KBPS)*(MIN_MINUTES*60)) + \
    ' AND ((totalAudioLength IS NULL) OR ((totalAudioLength > '+ \
    str(MIN_MINUTES*60) + \
    ') AND ((totalAudioSize/totalAudioLength)*' + \
    str(BYTE_PS_TO_KBPS) + ' >= ' + str(TARGET_KBPS) + '))'
