#!/usr/bin/python3
# -*- coding: utf-8 -*-


"""
launcher core.py.

launcher library for retropie, based on original idea - Ironic
  and the retropie integration work by -krahs-

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


import os, sys, psutil, rpyc
import subprocess, time
import logging, re, shlex

from .screen import CRT
from .utils import HideScreen, check_process, show_info
from .core_paths import *
from .file_helpers import *
from .netplay import netplay

__VERSION__ = '0.1'
__DEBUG__ = logging.INFO # logging.ERROR
CLEAN_LOG_ONSTART = True

LOG_PATH = os.path.join(TMP_LAUNCHER_PATH, "CRT_Launcher.log")

CRT_RUNCOMMAND_FORMAT = "touch %s && sleep 1.5 && "

class launcher(object):
    """ virtual class for crt launcher """
    m_sFileName = ""
    m_sFileNameVar = '%ROM%'
    m_sCfgSystemPath = ""
    m_sSystemFreq = ""
    m_sSelCore = ""
    m_sNextValidBinary = ""
    m_lBinaryMasks = []
    m_lBinaries = []
    m_sCustomRACFG = "" #retroarch custom append config for CRT
    m_lProcesses = PROCESSES
    m_oBlackScreen = None
    m_oRunProcess = None
    m_oCRT = None
    m_sCleanLaunch = ""
    m_bFastBoot = False

    def __init__(self, p_sFilePath, p_sSystem, p_sCustom):
        os.system('tput civis') # hide cursor
        self.m_sSystem = p_sSystem
        self.m_sCustom = p_sCustom
        self.m_sFilePath = p_sFilePath
        self.m_sFileName = os.path.basename(self.m_sFilePath)
        self.m_sFileDir = os.path.dirname(self.m_sFilePath)
        self.m_sGameName = os.path.splitext(self.m_sFileName)[0]
        self.m_oBlackScreen = HideScreen()

        self.__temp()
        self.__clean()
        logging.info("INFO: arg 1 (rom_path) = %s, (system) = %s, (sin uso) = %s"
            % (self.m_sFilePath, self.m_sSystem, self.m_sCustom))

        if ini_get(CRT_UTILITY_FILE, "fast_boot").lower() == "true":
            logging.info("INFO: fast boot is enabled")
            self.m_bFastBoot = True
        self.oled_info()
        self.pre_configure() # user virtual method get init values
        self.configure() # rom name work
        self.post_configure() # user virtual method for post configure
        self.prepare() # check runcommand and screen
        self.run() # launch, wait and cleanup

    # called children pre_configure at start, called by __init__()
    def pre_configure(self):
        self.m_sCfgSystemPath = os.path.join(RETROPIE_CFG_PATH, self.m_sSystem, "emulators.cfg")

    # setup paths - called by __init__()
    def configure(self):
        self.m_sSystemFreq = self.m_sSystem

    # called children post_configure at start, called by __init__()
    def post_configure(self):
        pass

    def prepare(self):
        self.runcommand_prepare()
        self.screen_prepare()

    def run(self):
        self.start()
        self.wait()
        self.cleanup()

    def start(self):
        if not self.m_bFastBoot: 
            self.runcommand_start()
            self.screen_set()
        else: 
            self.screen_set()
            self.direct_start()

    def wait(self):
        time_start = time.time()
        self.m_oRunProcess.wait()
        os.system('tput civis') # hide cursor
        time_elapsed = int(time.time() - time_start)
        self.statistics(time_elapsed)
        if self.m_bFastBoot: self.change_cpu_governor("default")
        self.oled_info("end")
        logging.info("INFO: game time: %s" % time_elapsed)
        logging.info("INFO: process end")

    # generate command string
    # just called if need rebuild the CMD
    def runcommand_generate(self, p_sCMD):
        p_sCMD = p_sCMD.replace('"','').strip()
        new_cmd = self.m_sNextValidBinary + " = \""
        new_cmd += CRT_RUNCOMMAND_FORMAT % TMP_SLEEPER_FILE
        new_cmd += p_sCMD + "\""
        new_cmd = re.sub(r' +', " ", new_cmd)
        return new_cmd

    def runcommand_clean(self, p_sCMD):
        # first remove quotes
        p_sCMD = p_sCMD.replace('"', '')
        # check if %BASENAME% is used instead of %ROM%
        if '%BASENAME%' in p_sCMD:
            self.m_sFileNameVar = '%BASENAME%'
        elif '%ROM%' in p_sCMD:
            self.m_sFileNameVar = '%ROM%'
        else:
            self.m_sFileNameVar = None
        if self.m_sFileNameVar: p_sCMD = p_sCMD.replace(self.m_sFileNameVar, '')
        # "touch /path/lchtmp && sleep 1 && /path/retroarch ...
        # "/path/retroarch ...
        if "&&" in p_sCMD:
            p_sCMD = p_sCMD.split("&&")[-1]
        # ... --appendconfig /path/system.cfg %ROM%"'
        # ... %ROM%"'
        if "--appendconfig" in p_sCMD:
            p_sCMD = p_sCMD.split("--appendconfig")[0]
        # --apendconfig for retroach only. Custom cfg files
        # defined in plugins.
        if RA_BIN_FILE in p_sCMD:
            if self.m_sCustomRACFG:
                p_sCMD += " --appendconfig %s" % self.m_sCustomRACFG
        if self.m_sFileNameVar: p_sCMD += " " + self.m_sFileNameVar
        p_sCMD = self.runcommand_netplay(p_sCMD)
        return p_sCMD

    def runcommand_netplay(self, p_sCMD):
        if not RA_BIN_FILE in p_sCMD: return p_sCMD
        p_lNet = ['-C', '-H', '--port', '--nick']
        p_lCMD = p_sCMD.split(' ')
        count = 0
        # clean netplay config
        for item in p_lCMD:
            if item == '-C' or item == '-H':
                p_sCMD = p_sCMD.replace(item, '')
            elif item == '--port' or item == '--nick':
                text = p_lCMD[count] + " " + p_lCMD[count + 1]
                p_sCMD = p_sCMD.replace(text, '')
            count += 1
        p_sCMD = re.sub(r' +', " ", p_sCMD)
        p_oNetplay = netplay()

        # append netplay if enabled
        if p_oNetplay.status():
            logging.info("INFO: netplay enabled")
            # main netplay config
            if p_oNetplay.get_mode().lower() == 'client': 
                ip = p_oNetplay.get_host()
                mode = '-C ' + ip
            else: mode = '-H'
            port = '--port %s' % p_oNetplay.get_port()
            nick = "--nick \'%s\'" % p_oNetplay.get_nick()
            p_sCMD += " " + mode
            p_sCMD += " " + port
            p_sCMD += " " + nick
            ini = ini_get(CRT_UTILITY_FILE, 'netplay_stateless')
            if ini.lower() == "true": p_sCMD += " --stateless"
            # other options
            lframes = p_oNetplay.get_lframes()
            ini_set(self.m_sCustomRACFG, 
                    'netplay_input_latency_frames_min', lframes)
            spect = "true" if p_oNetplay.get_spectator() else "false"
            ini_set(self.m_sCustomRACFG, 
                    'netplay_start_as_spectator', spect)
            lobby = "true" if p_oNetplay.get_lobby() else "false"
            ini_set(self.m_sCustomRACFG, 
                    'netplay_public_announce', lobby)
            logging.info("INFO: netplay config: %s %s %s" % (mode, port, nick))
        return p_sCMD

    def runcommand_prepare(self):
        ''' check runcommand execution string on emulators cfg and integrates
            with retropie crt edition            
        '''
        f = open(self.m_sCfgSystemPath, "r")
        new_file = f.readlines()
        f.close()
        # only change file if is need it
        for Binary in self.m_lBinaries:
            for line in new_file:
                lValues = line.strip().split('=')
                sCMD = lValues[1].strip()
                if len(lValues) > 2:
                    sCMD = "=".join(lValues[1:]).strip()
                lValues = list(map(lambda s: s.strip(), lValues))
                if not self.m_bFastBoot:
                    if lValues[0] == Binary:
                        self.m_sNextValidBinary = lValues[0]
                        cmd_cleaned = self.runcommand_clean(sCMD)
                        cmd_current = self.runcommand_generate(cmd_cleaned)
                        if cmd_current != line.strip(): # atm just force our cmd
                            logging.info("changed command (%s)" % cmd_current)
                            modify_line(self.m_sCfgSystemPath, line, cmd_current)
                else:
                    if lValues[0].lower() == self.m_sSelCore:
                        self.m_sCleanLaunch = self.runcommand_clean(sCMD).strip()
                        logging.info("INFO: clean launching string on emulators.cfg: {%s}" \
                                     % self.m_sCleanLaunch)
                        return

    def runcommand_wait(self):
        """ wait_runcommand: wait for user launcher menu """
        logging.info("INFO: waiting runcommand ends and start")
        # TODO: better use a symple socket daemon
        while True:
            if os.path.exists(TMP_SLEEPER_FILE):
                logging.info("INFO: detected trigger file %s, wait finished..." % TMP_SLEEPER_FILE)
                # cleaning retroarch.cfg file generated by runcommand
                if os.path.exists(RETROPIE_CFGRAAPP_FILE):
                    touch_file(RETROPIE_CFGRAAPP_FILE)
                return False
            # try to detect if user exits from runcommand
            poll = self.m_oRunProcess.poll()
            if poll != None:
                logging.info("INFO: runcommand closed by user (poll = %s)" % poll)
                return True
            time.sleep(0.1)

    def runcommand_start(self):
        """ launch_core: run emulator with runcommand!"""
        commandline = "%s 0 _SYS_ %s \"%s\"" % (RETROPIE_RUNCOMMAND_FILE, self.m_sSystem, self.m_sFilePath)
        self.m_oRunProcess = subprocess.Popen(shlex.split(commandline), shell=False)
        logging.info("INFO: Subprocess running: %s", commandline)
        self.runcommand_wait()

    def direct_start(self):
        """ launch_core: run emulator without runcommand!"""
        if self.m_sFileNameVar and self.m_sFileNameVar in self.m_sCleanLaunch:
            if self.m_sFileNameVar == "%ROM%": p_sGame = self.m_sFilePath
            elif self.m_sFileNameVar == "%BASENAME%": p_sGame = self.m_sGameName
            self.m_sCleanLaunch = self.m_sCleanLaunch.replace(self.m_sFileNameVar,
                                  "\"%s\"" % p_sGame)
            self.m_sCleanLaunch += " >> %s 2>&1" % LOG_PATH
        commandline = self.m_sCleanLaunch
        if not os.path.exists("/tmp/retroarch"): os.system("mkdir /tmp/retroarch")
        self.change_cpu_governor()
        self.m_oRunProcess = subprocess.Popen(commandline, shell=True, executable='/bin/bash')
        logging.info("INFO: Subprocess running: %s", commandline)

    def change_cpu_governor(self, p_sMode = None):
        p_lCPUGov = ["schedutil", "conservative",
                     "ondemand", "userspace",
                     "powersave", "performance"]
        if p_sMode == "default": p_sGovernor = "ondemand"
        else:
            value = ini_get(RETROPIE_RUNCOMMAND_CFG_FILE, "governor").lower()
            if value and value in p_lCPUGov: p_sGovernor = value
            else: p_sGovernor = "ondemand"
        command = "echo \"%s\"" % p_sGovernor
        command += " | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
        command += " >> /dev/null 2>&1"
        os.system(command)
        logging.info("INFO: CPU scaling governor changed to {%s}" % p_sGovernor)

    def oled_info(self, p_sStatus = "init"):
        try:
            try: self.con.root
            except: self.con = rpyc.connect('localhost', CRT_OLED_PORT)
            if p_sStatus == "init":
                self.con.root.game_mode(self.m_sFileName, self.m_sSystem, 
                                        time.time(), "game_init")
            elif p_sStatus == "end":
                self.con.root.game_mode_off("game_over")
        except Exception as e: 
            logging.info("ERROR: %s" % e)
            logging.info("ERROR: Can't connect with OLED display service")

    def runcommand_kill(self, including_parent=False):
        """ kill runcommand and child processes if configuration is wrong"""
        p_iSelfPID = os.getpid()
        parent = psutil.Process(p_iSelfPID)
        children = parent.children(recursive=True)
        logging.info("INFO: killing all runcommand processes")
        for child in children:
            child.kill()
        gone, still_alive = psutil.wait_procs(children, timeout=5)
        if including_parent:
            parent.kill()
            parent.wait(5)

    def screen_prepare(self):
        pass

    def screen_set(self):
        self.m_oCRT = CRT(self.m_sSystemFreq)
        self.m_oCRT.screen_calculated(CRT_DB_SYSTEMS_FILE)
        self.m_oBlackScreen.fill()
        logging.info("INFO: clean: %s", TMP_SLEEPER_FILE)
        remove_file(TMP_SLEEPER_FILE)

    def panic(self, p_sErrorLine1, p_sErrorLine2 = None, p_bForceQuit = True):
        """ stop the program and show error to the user """
        sTitPanic = "SYSTEM LAUNCHING ERROR"
        lOptPanic = [(str(p_sErrorLine1).upper(), "OK")]
        if p_sErrorLine2:
            lOptPanic.append((str(p_sErrorLine2).upper(), "OK"))
        logging.error("PANIC: %s" % p_sErrorLine1)
        CRT().screen_restore()
        show_info(lOptPanic, sTitPanic, 7000)
        if p_bForceQuit:
            logging.error("EXIT: crt_launcher forced")
            self.__clean()
            sys.exit(1)

    def statistics(self, p_iTime):
        if not os.path.exists(CRT_STATS_FILE):
            touch_file(CRT_STATS_FILE)
            add_line(CRT_STATS_FILE, 'timer = "0"')
            
        value = ini_get(CRT_STATS_FILE, 'timer')
        if value:
            value = int(value) + p_iTime
            ini_set(CRT_STATS_FILE, 'timer', value)
        else: add_line(CRT_STATS_FILE, 'timer = "0"')

        value = ini_get(CRT_STATS_FILE, 'played_%s' % self.m_sSystem)
        if value:
            value = int(value) + 1
            ini_set(CRT_STATS_FILE, "played_%s" % self.m_sSystem, value)
        else: add_line(CRT_STATS_FILE, 'played_%s = "1"' % self.m_sSystem)

        value = ini_get(CRT_STATS_FILE, 'timer_%s' % self.m_sSystem)
        if value:
            value = int(value) + p_iTime
            ini_set(CRT_STATS_FILE, "timer_%s" % self.m_sSystem, value)
        else: add_line(CRT_STATS_FILE, 'timer_%s = "%s"' % (self.m_sSystem, p_iTime))

    # cleanup code
    def cleanup(self):
        self.m_oCRT.screen_restore()
        self.m_oBlackScreen.fill()
        logging.info("INFO: ES mode recover")
        os.system('clear')
        self.__clean()
        os.system('tput cnorm') # show cursor
        sys.exit()

    # clean system
    def __clean(self):
        self.clean_videomodes()
        remove_file(TMP_SLEEPER_FILE)
        os.system('rm -rf "/tmp/retroarch" >> /dev/null 2>&1')

    def clean_videomodes(self):
        try:
            os.remove(RETROPIE_VIDEOMODES_FILE)
        except OSError:
            return False
        return True

    def __temp(self):
        if CLEAN_LOG_ONSTART:
            remove_file(LOG_PATH)
        logging.basicConfig(filename=LOG_PATH, level=__DEBUG__, format='[%(asctime)s] %(levelname)s - %(filename)s:%(funcName)s - %(message)s')
