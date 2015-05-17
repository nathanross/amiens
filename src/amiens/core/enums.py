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

from enum import Enum, IntEnum

class MTYPES(Enum):
    PROBLEM=0
    AUDIO=1
    VIDEO=2

MTYPE_TO_STR = [ None, 'audio', 'video']

class EXISTS_STATUS(Enum):
    UNKNOWN=0
    EXISTS=1
    DELETED=2
    
class METADATA_STATUS(Enum):
    NONE=0
    STORED=1
    BLOCKED=2

class DOWNLOADED(IntEnum):
    NONE=0
    LOW=1
    MEDIUM=2
    ORIGINAL=3
    ALL=4

class BLOCKDOWNLOAD(IntEnum):
    NO=0
    DOWNLOADED=1
    NO_FILES=2
    PREFERENCE=3

class RATING(IntEnum):
    UNRATED=0
    SKIPPED=1
    CONFIRM_UNRATED=2
    CONFIRM_SKIPPED=3
    MANUAL_SKIP=4
    #is it really necessary to define the number of stars
    # maybe just have 4 as a baseline and leave the semantics
    # up to the user.
    TOSS=5
    BAD=6
    DEF_OKAY=7
    OKAY=8
    GOOD=9 
    
