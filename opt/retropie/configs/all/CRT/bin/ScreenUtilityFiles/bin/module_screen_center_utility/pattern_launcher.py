#!/usr/bin/python
# -*- coding: utf-8 -*-


"""
centering pattern.py.

Centering Pattern Utility for CRT image adjusting by Krahs

https://github.com/krahsdevil/crt-for-retropie/

Copyright (C)  2018/2020 -krahs- - https://github.com/krahsdevil/
Copyright (C)  2019 dskywalk - http://david.dantoine.org

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Lesser General Public License as published by the Free
Software Foundation, either version 2 of the License, or (at your option) any
later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details.
You should have received a copy of the GNU Lesser General Public License along
with this program.  If not, see <http://www.gnu.org/licenses/>.

"""


import os, sys, traceback, time
import subprocess, commands
import logging

sys.dont_write_bytecode = True

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(SCRIPT_DIR + "/../"))
from main_paths import MODULES_PATH
sys.path.append(MODULES_PATH)

from launcher_module.utils import check_process, show_info, menu_options
from launcher_module.core_paths import TMP_LAUNCHER_PATH, CRT_UTILITY_FILE
from launcher_module.screen import CRT
from launcher_module.file_helpers import *
from pattern_generator import *

__VERSION__ = '0.1'
__DEBUG__ = logging.INFO # logging.ERROR
CLEAN_LOG_ONSTART = True

LOG_PATH = os.path.join(TMP_LAUNCHER_PATH, "CRT_Screen_Center.log")
EXCEPTION_LOG = os.path.join(TMP_LAUNCHER_PATH, "backtrace.log")

tests = ["current", "system", "system50", "system60", "test60", "force"]
Arg = []

class center(object):
    """ virtual class for centering pattern """
    m_dVideo = {}
    m_oCRT = None
    m_oPatternHandle = None
    m_sEnv = ""
    m_bRestart = True

    m_dPatternAdj = {}

    def __init__(self):
        self.__temp()
        self.__clean()
        self.m_oPatternHandle = generate()

    def launch(self, p_sArgv = "current", p_sRestart = True): 
        logging.info("INFO: arg 1 (test) = %s" %p_sArgv)
        self.m_sEnv = p_sArgv
        self.m_bRestart = p_sRestart
        if self.m_sEnv == "force":
            logging.info("INFO: Force mode, only apply sys resolution")
            self._force_system_res()
        else:
            self.configure() # rom name work
            self.prepare() # screen and pattern generator
            self.run() # launch, wait and cleanup

    # called at start, called by __init__()
    def configure(self):
        """Get from utility.cfg system resolution"""
        if self.m_sEnv == "current":
            self.m_sEnv = ini_get(CRT_UTILITY_FILE, "default")

    def prepare(self):
        self.screen_prepare()
        self.m_oPatternHandle.initialize(self.m_sEnv, self.m_dVideo)

    def run(self):
        self.start()
        self.cleanup()

    def start(self):
        self.apply_diff_timings()
        self.screen_set()
        self.m_oPatternHandle.launch()

    def apply_diff_timings(self):
        DiffTimings = self.m_oPatternHandle.get_diff_timings()
        logging.info("INFO: timing_data_set PRE-CALCULATED Diff - %s" %
                     self.m_dVideo)
        for timing in DiffTimings:
            self.m_oCRT.timing_add(timing, int(DiffTimings[timing]))
        logging.info("INFO: timing_data_set POST-CALCULATED Diff - %s" %
                      self.m_dVideo)

    def _force_system_res(self):
        p_oSaveBoot = saveboot()
        p_oSaveBoot.save()
        self.m_oCRT = CRT()
        self.cleanup()
        self._restart_es()

    def screen_prepare(self):
        self.m_oCRT = CRT(self.m_sEnv + "_timings")
        self.m_dVideo = self.m_oCRT.pattern_data(CRT_UTILITY_FILE)

    def screen_set(self):
        self.m_oCRT.resolution_set()

    def panic(self, p_sErrorLine1, p_sErrorLine2 = "-", p_bForceQuit = True):
        """ stop the program and show error to the user """
        logging.error("PANIC: %s" % p_sErrorLine1)
        CRT().screen_restore()
        something_is_bad(p_sErrorLine1, p_sErrorLine2)
        if p_bForceQuit:
            logging.error("EXIT: crt_launcher forced")
            self.__clean()
            sys.exit(1)

    def _restart_es(self):
        commandline = None
        if self.m_bRestart:
            if check_process("emulationstatio"):
                commandline = "touch /tmp/es-restart "
                commandline += "&& pkill -f \"/opt/retropie"
                commandline += "/supplementary/.*/emulationstation([^.]|$)\""
                show_info("RESTARTING EMULATIONSTATION")
                os.system(commandline)
                time.sleep(2)
                sys.exit(1)

    # cleanup code
    def cleanup(self):
        self.m_oCRT.screen_restore()
        logging.info("ES mode recover")
        os.system('clear')
        self.__clean()

    # clean system
    def __clean(self):
        pass

    def __temp(self):
        if CLEAN_LOG_ONSTART:
            remove_file(LOG_PATH)
        logging.basicConfig(filename=LOG_PATH, level=__DEBUG__,
        format='[%(asctime)s] %(levelname)s - %(filename)s:%(funcName)s - %(message)s')

if __name__ == '__main__':
    def get_argument():
        sTitRot = "SCREEN CENTER UTILITY"
        lOptRot = [("FRONTEND CENTERING", "FRONTEND"),
                   ("IN-GAME CENTERING", "INGAME"),
                   ("CANCEL", "CANCEL")]

        sChoice = menu_options(lOptRot, sTitRot)
        if sChoice == "FRONTEND":
            sChoice = "system"
        elif sChoice == "INGAME":
            sChoice = "test60"
        else:
            sys.exit()
        return sChoice
        
    try:
        opt = sys.argv[1]
    except:
        opt = get_argument()

    try:
        if not opt in tests:
            print ('ERROR: some of these arguments expected:\n %s' % tests)
            raise Exception('incorrect argument')

        if opt == "system":
            Arg.append("system60")
            Arg.append("system50")
        else:
            Arg.append(opt)
        for item in Arg:
            oLaunch = center()
            oLaunch.launch(item)
            oLaunch = None
            CLEAN_LOG_ONSTART = False
        
    except Exception as e:
        ErrMsg = ""
        if "list index out of range" in e:
            ErrMsg += 'ERROR: at least one argument expected \n'
        elif 'incorrect argument' in e:
            ErrMsg += 'ERROR: some of these arguments expected: %s \n' % tests
        else:
            ErrMsg += str(e) + '\n'
            ErrMsg += traceback.format_exc()
        with open(EXCEPTION_LOG, 'a') as f:
            f.write(str(ErrMsg))

    sys.exit()