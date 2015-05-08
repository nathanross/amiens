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
from amiens.core import asserts
from amiens.core import util
from amiens.core.catalogue import Catalogue
from os import path
from amiens.core.util import Log

# normalizes strings input from argument into valid inputs.
# probably better way to do it would be to create args
# by extending an Arg class and overriding a dummy 'transform'
# method.

class Transforms(object):
    @staticmethod
    def useCatalogue(path_posix):
        if path_posix:
            return Catalogue(path.expanduser(path_posix), exists=True)
        return path_posix

    @staticmethod
    def data_src(path_posix):
        goal='received data_src argument'
        if path_posix == None:
            return None
        abspath=path.expanduser(path_posix)
        asserts.exists(goal, abspath)
        if abspath[-3:] == 'csv':
            return abspath
        else:
            return Transforms.useCatalogue(abspath)
    
    @staticmethod
    def dummy(arg):
        return arg

    @staticmethod
    def boolean(arg):
        goal='received boolean argument'
        asserts.that(arg <= 1,
                     goal+' but it is higher than the maximum 1')
        asserts.that(arg >= 0,
                     goal+' but it is lower than the minimum 0')
        return arg

    @staticmethod
    def mediaType(arg):
        asserts.that(arg.upper() in enums.MTYPES.__members__,
                'received mediaType argument, but is not valid')
        return enums.MTYPES.__members__[arg.upper()]

    @staticmethod
    def posix_generic(path_posix):
        return path.expanduser(path_posix)
    
    @staticmethod
    def mqs_fqs(arg):
        callbacks=[]
        goal='received mq argument '
        arglist=arg
        if type(arg) == str:
            arglist=[arg]
        for l_mq in arglist:
            receiver={'callback':None}
            mq_text=util.full_read(goal, path.expanduser(l_mq))
            exec(mq_text, {}, receiver)
            asserts.that(receiver['callback'],
                    'no callback assigned for mq:' + l_mq)
            tq={'callback':receiver['callback'], 'sql':None}
            if 'sql' in receiver:
                tq['sql'] = receiver['sql']
            callbacks.append(tq)
        return callbacks

    @staticmethod
    def item(path_posix):
        goal='received item argument'
        arg=path.expanduser(path_posix)
        asserts.exists(goal, arg)
        l=arg
        if path.isdir(goal):
            l+='/.amiens.json'
        stub = _Stub.FromFile(l)
        stub.l_src=l
        return stub
    
    @staticmethod
    def outdir(path_posix):
        goal='received outdir argument'
        arg=path.expanduser(path_posix).rstrip('/')
        if not os.path.exists(arg):
            os.makedirs(arg)
        else:
            asserts.isdir(goal, arg)
            asserts.canwrite(goal, arg)
        return arg

    @staticmethod
    def quality(arg):
        goal='received quality argument'
        asserts.that(arg > 4, goal+' but it is higher than the maximum 4')
        asserts.that(arg < 0, goal+' but it is lower than the minimum 1')
        return arg
    
    @staticmethod
    def rating(arg):
        goal='received rating argument'
        asserts.that(arg > 5, goal+' but it is higher than the maximum 5')
        asserts.that(arg < 0, goal+' but it is lower than the minimum 0')
        return arg
