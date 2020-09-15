#!/usr/bin/python3
# -*- coding: utf-8 -*-


"""
USB automount main service code

USB Automount service code for Retropie by -krahs-

https://github.com/krahsdevil/crt-for-retropie/

Copyright (C)  2018/2020 -krahs- - https://github.com/krahsdevil/

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
import os, sys
import subprocess, re
import logging, traceback
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(SCRIPT_DIR + "/../"))
from main_paths import MODULES_PATH
sys.path.append(MODULES_PATH)

from launcher_module.core_paths import *
from launcher_module.utils import check_process, wait_process, set_procname

LOG_PATH = os.path.join(TMP_LAUNCHER_PATH,"CRT_External_Storage.log")
EXCEPTION_LOG = os.path.join(TMP_LAUNCHER_PATH, "backtrace.log")

CRT_OPT_FOLDER = "1CRT"
RETROPIE_OPT_FOLDER = "retropie"

__VERSION__ = '0.1'
__DEBUG__ = logging.INFO # logging.ERROR
CLEAN_LOG_ONSTART = False

set_procname(PNAME_EXTSTRG)

class USBAutoService(object):
    m_lProcesses = []
    m_bPRestart = False

    m_lMountUSBsPrev = []  # Previous scan: disk ID + mnt Path
    m_lMountPathsPrev = [] # Previous scan: only mnt Path
    m_lMountUSBs = []      # Current scan: disk ID + mnt Path
    m_lMountPaths = []     # Current scan: disk ID + mnt Path
    m_lMountCtrl = []      # For control the valid usb path
    m_bChanges = False
    m_bUSBMounted = False  # To avoid to mount a second device

    m_dWrongFolderName = { "fba_libretro": "fba", "mame": "mame-libretro",
                           "advmame": "mame-advmame", "sg1000": "sg-1000",
                           "wswan": "wonderswan", "wswanc": "wonderswancolor",
                           "colecovision": "coleco", "lynx": "atarilynx",
                          }

    m_dStartScripts = ({"script": "+Start ScummVM.sh", 
                        "binary": "/opt/retropie/emulators/scummvm/bin/scummvm"},
                       {"script": "+Start ScummVM-SDL1.sh", 
                        "binary": "/opt/retropie/emulators/scummvm-sdl1/bin/scummvm"},
                       {"script": "+Start Amiberry.sh", 
                        "binary": "/opt/retropie/emulators/amiberry/amiberry.sh"},
                       {"script": "+Start DOSBox.sh", 
                        "binary": "/opt/retropie/emulators/dosbox/bin/dosbox"},
                       {"script": "+Start Fuse.sh", 
                        "binary": "/opt/retropie/emulators/fuse/bin/fuse"})

    m_dRootFolders = [RETROPIE_ROMS_FOLDER, RETROPIE_BIOS_FOLDER, RETROPIE_GAMELIST_FOLDER]
    m_dGamelistFolders = [CRT_OPT_FOLDER, RETROPIE_OPT_FOLDER]
    m_iMntTime = 0
    m_iUMntTime = 0

    def __init__(self):
        self.__temp()
        self.__clean()
        self.m_lProcesses.append(PNAME_CONFIG)
        self.m_lProcesses.append(PNAME_LAUNCHER)
        logging.info("INFO: Initializating USB Automount Service")
        
    def run(self):
        self._loop()

    def _get_mounted_list(self):
        """ 
        Will take all connected disks on the system and make a filtered list with
        only usb devices. This also will create two lists, one with only usb mounted
        paths and other with mounted paths and disks system id (/dev/sda1 - /media/usb0)
        First access will replicate previous scan to variables 'Prev' to 
        compare and see if any new device was connected.
        """
        self.m_lMountUSBsPrev = self.m_lMountUSBs   #Save current scan as Prev to compare
        self.m_lMountPathsPrev = self.m_lMountPaths #Save current scan as Prev to compare
        self.m_lMountUSBs = []  #Reset variable with disk and paths info
        self.m_lMountPaths = [] #Reset variable with paths info
        
        try: self.prev_scan
        except: self.prev_scan = None

        command = "lsblk"
        try: scan = subprocess.check_output(command, shell=True).decode("utf-8")
        except: scan = None
        if scan != self.prev_scan:
            self.m_bChanges = True
            p_sCMDString = "find /dev/disk -ls | grep /%s"
            p_sOutputMNT = [(item.split()[0].replace("├─", "").replace("└─", ""),
                             item[item.find("/"):]) for item in subprocess.check_output(
                             ["lsblk"]).decode("utf-8").split("\n") if "/" in item]
            
            for item in p_sOutputMNT:
                try:
                    p_sOutputUSB = subprocess.check_output(["/bin/bash", "-c", p_sCMDString % item[0]]).decode("utf-8")
                except:
                    p_sOutputUSB = ""
                if 'usb' in p_sOutputUSB:
                    self.m_lMountUSBs.append(item)
                    self.m_lMountPaths.append(item[1])
        else:
            self.m_bChanges = False
        self.prev_scan = scan

    def _mount(self, p_sMount = None):
        for device in self.m_lMountUSBs:
            if device[1] == p_sMount:
                p_sDisk = device[0]
        os.system('sudo mount --bind "%s/%s" "%s" > /dev/null 2>&1' % (p_sMount, RETROPIE_ROMS_FOLDER, RETROPIE_ROMS_PATH))
        logging.info("INFO: Mounting %s/%s in %s" % (p_sMount, RETROPIE_ROMS_FOLDER, RETROPIE_ROMS_PATH))
        os.system('sudo mount --bind "%s/%s" "%s" > /dev/null 2>&1' % (p_sMount, RETROPIE_BIOS_FOLDER, RETROPIE_BIOS_PATH))
        logging.info("INFO: Mounting %s/%s in %s" % (p_sMount, RETROPIE_BIOS_FOLDER, RETROPIE_BIOS_PATH))
        os.system('sudo mount --bind "%s/%s" "%s" > /dev/null 2>&1' % (p_sMount, RETROPIE_GAMELIST_FOLDER, RETROPIE_GAMELIST_PATH))
        logging.info("INFO: Mounting %s/%s in %s" % (p_sMount, RETROPIE_GAMELIST_FOLDER, RETROPIE_GAMELIST_PATH))
        os.system('rm "%s" > /dev/null 2>&1' % CRT_EXTSTRG_TRIG_UMNT_PATH)
        os.system('echo "/dev/%s %s" > "%s"' % (p_sDisk, p_sMount, CRT_EXTSTRG_TRIG_MNT_PATH))
        logging.info("INFO: Created trigger file mount : \"/dev/%s %s\"" % (p_sDisk, p_sMount))
        self.m_iMntTime = time.time()

    def _check_mount(self):
        """ 
        Will check if any new USB external storage is connected and it´s a valid USB 
        for ROMs. If 'Prev' and current variable check for USB devices are different
        and also self.m_bUSBMounted is False (there is not a prev USB ROMs device
        connected) will try to mount.
        
        """
        p_bCheck01 = False
        p_bCheck02 = False
        if self.m_lMountPathsPrev != self.m_lMountPaths:
            p_bCheck01 = True
        
        if not self.m_bUSBMounted and p_bCheck01:
            for path in self.m_lMountPaths:
                if not path in self.m_lMountPathsPrev: #Means we have a new device
                    if self._valid_usb_storage(path): #Check if root '/roms' if found
                        self.m_bUSBMounted = True
                        logging.info("INFO: New VALID usb device plugged at \"%s\"" % (path))
                        #TODO: Prepare folder structure
                        self._get_folder_structure(path)
                        self.m_lMountCtrl.append(path)
                        self._mount(path)
                        p_bCheck02 = True
                        break
                    else:
                        logging.info("INFO: Found new NOT VALID usb device at \"%s\"" % (path))
        return p_bCheck02

    def _valid_usb_storage(self, p_sMount):
        for folder in os.listdir(p_sMount):
            #logging.info("INFO: Compare %s %s" % (folder.lower(), RETROPIE_ROMS_FOLDER.lower()))
            if folder.lower() == RETROPIE_ROMS_FOLDER.lower():
                logging.info('INFO: Found "/roms" folder in root at %s' % p_sMount)
                return True
        logging.info("INFO: No valid folder structure found at %s" % p_sMount)
        return False

    def _umount(self, p_sMount = None):
        """ Force umount of all mounted paths """
        try:
            os.system('sudo umount -l "%s" > /dev/null 2>&1' % RETROPIE_ROMS_PATH)
            logging.info("INFO: Umounting %s" % RETROPIE_ROMS_PATH)
            os.system('sudo umount -l "%s" > /dev/null 2>&1' % RETROPIE_BIOS_PATH)
            logging.info("INFO: Umounting %s" % RETROPIE_BIOS_PATH)
            os.system('sudo umount -l "%s" > /dev/null 2>&1' % RETROPIE_GAMELIST_PATH)
            logging.info("INFO: Umounting %s" % RETROPIE_GAMELIST_PATH)
            if p_sMount:
                os.system('sudo umount -l "%s" > /dev/null 2>&1' % p_sMount)
                logging.info("INFO: Umounting device %s" % p_sMount)
            os.system('rm "%s" > /dev/null 2>&1' % CRT_EXTSTRG_TRIG_MNT_PATH)
            os.system('touch "%s" > /dev/null 2>&1' % CRT_EXTSTRG_TRIG_UMNT_PATH)
            self.m_iUMntTime = time.time()
        except:
            pass

    def _check_umount(self):
        """ 
        Check if any previous devices identified as valid USB of ROMs is
        disconected. If list is empty will not do anything.
        """
        p_bCheck = False
        p_lTemp = self.m_lMountCtrl
        if p_lTemp:
            for path in p_lTemp:
                if not path in self.m_lMountPaths:
                    logging.info('INFO: Valid device at "%s" removed' % path)
                    p_bCheck = True
                    self.m_bUSBMounted = False
                    self.m_lMountCtrl.remove(path)
                    self._umount(path)
        return p_bCheck

    def _get_folder_structure(self, p_sMount):
        self._check_folder_names(p_sMount)
        self._check_missing_folders(p_sMount)
        self._sync_system_gamelist(p_sMount)
        self._sync_start_scripts(p_sMount)
    
    def _check_folder_names(self, p_sMount):
        """ Will fix wrong folder names, from some recalbox usb roms packs """
        p_sRootPath = p_sMount
        p_sGamelistsPath = (os.path.join(p_sRootPath, RETROPIE_GAMELIST_FOLDER))
        p_sROMsPath = (os.path.join(p_sRootPath, RETROPIE_ROMS_FOLDER))
        logging.info("INFO: Starting folder names check")
        # Fix main folders names on USB root
        self._fix_folder_names(self.m_dRootFolders, p_sRootPath)
        # Fix main folders names on USB gamelist folder
        self._fix_folder_names(self.m_dGamelistFolders, p_sGamelistsPath)
        # Fix wrong roms folder names
        self._fix_roms_folder_names(self.m_dWrongFolderName, p_sROMsPath)

    def _fix_roms_folder_names(self, p_lFolderLST, p_sPath):
        """ For fix some Recalbox roms packs, different folder names """
        if os.path.exists(p_sPath):
            for p_sFolderDST in p_lFolderLST:
                for p_sFolderSRC in os.listdir(p_sPath):
                    if p_sFolderDST.lower() == p_sFolderSRC.lower():
                        if not os.path.exists("%s/%s" % (p_sPath, p_lFolderLST[p_sFolderDST])):
                            os.rename("%s/%s" % (p_sPath, p_sFolderSRC),
                                      "%s/%s" % (p_sPath, p_lFolderLST[p_sFolderDST]))
                            logging.info("INFO: Changed folder name from %s/%s to %s/%s" % \
                                        (p_sPath, p_sFolderSRC, p_sPath, p_lFolderLST[p_sFolderDST]))

    def _fix_folder_names(self, p_lFolderLST, p_sPath):
        """ For CaSe SeNsItIvE folder names """
        if os.path.exists(p_sPath):
            for p_sFolderDST in p_lFolderLST:
                for p_sFolderSRC in os.listdir(p_sPath):
                    if p_sFolderDST.lower() == p_sFolderSRC.lower() and p_sFolderDST != p_sFolderSRC:
                        try:
                            os.rename("%s/%s" % (p_sPath, p_sFolderSRC),
                                      "%s/%s" % (p_sPath, p_sFolderDST))
                            logging.info("INFO: Changed folder name from %s/%s to %s/%s" % \
                                        (p_sPath, p_sFolderSRC, p_sPath, p_sFolderDST))
                        except:
                            pass

    def _check_missing_folders(self, p_sMount):
        """ Will fix and create base folders: roms, bios, gamelists... """
        p_sRootPath = p_sMount
        p_sGamelistsPath = (os.path.join(p_sRootPath, RETROPIE_GAMELIST_FOLDER))
        p_sROMsPath = (os.path.join(p_sRootPath, RETROPIE_ROMS_FOLDER))
        logging.info("INFO: Creating missing folders")
        # Create main folders
        self._create_miss_folders(self.m_dRootFolders, p_sRootPath)
        # Create system CRT and retropie 
        self._create_miss_folders(self.m_dGamelistFolders, p_sGamelistsPath)
        # Replicate roms/gamelist folders internal -> usb
        self._create_miss_folders(os.listdir(RETROPIE_ROMS_PATH), p_sROMsPath)
        self._create_miss_folders(os.listdir(RETROPIE_GAMELIST_PATH), p_sGamelistsPath)
        # Replicate roms/gamelist folders usb -> internal
        self._create_miss_folders(os.listdir(p_sROMsPath), RETROPIE_ROMS_PATH)
        self._create_miss_folders(os.listdir(p_sGamelistsPath), RETROPIE_GAMELIST_PATH)

    def _create_miss_folders(self, p_lFolderLST, p_sPath):
        for p_sFolderDST in p_lFolderLST:
            p_sPathDST = "%s/%s" % (p_sPath, p_sFolderDST)
            if not os.path.exists(p_sPathDST) and \
               not p_sFolderDST in self.m_dWrongFolderName:
                os.makedirs(p_sPathDST)
                logging.info("INFO: Create folder %s" % p_sPathDST)

    def _sync_system_gamelist(self, p_sMount):
        """ Will create and sync to usb CRT and retropie options for ES """
        p_sGamelistsPath = (os.path.join(p_sMount, RETROPIE_GAMELIST_FOLDER))
        for p_sFolder in self.m_dGamelistFolders:
            logging.info("INFO: Synchronizing folder %s/%s to %s/%s" % \
                        (RETROPIE_GAMELIST_PATH, p_sFolder, p_sGamelistsPath, p_sFolder))
            os.system('rsync -a --delete "%s/%s/" "%s/%s/"' % \
                       (RETROPIE_GAMELIST_PATH, p_sFolder, p_sGamelistsPath, p_sFolder))

    def _sync_start_scripts(self, p_sMount):
        p_sRootPath = p_sMount
        p_sROMsPath = (os.path.join(p_sRootPath, RETROPIE_ROMS_FOLDER))
        # Clean +Start_xxx scripts on internal storage
        self._clean_start_scripts(RETROPIE_ROMS_PATH, p_sROMsPath)
        # Clean +Start_xxx scripts on external usb device
        self._clean_start_scripts(p_sROMsPath, RETROPIE_ROMS_PATH)

    def _clean_start_scripts(self, p_sPathSRC, p_sPathDST):
        p_lFolderLST = os.listdir(p_sPathSRC)
        for item in self.m_dStartScripts:
            for p_sFolder in p_lFolderLST:
                p_sScriptSRC = "%s/%s/%s" % (p_sPathSRC, p_sFolder, item["script"])
                p_sScriptDST = "%s/%s/%s" % (p_sPathDST, p_sFolder, item["script"])
                if os.path.exists(p_sScriptSRC):
                    if not os.path.exists(item["binary"]):
                        logging.info("INFO: Binary %s doesn't exist" % item["binary"])
                        logging.info("INFO: Deleting %s" % p_sScriptSRC)
                        os.system('rm "%s" > /dev/null 2>&1' % p_sScriptSRC)
                        if os.path.exists(p_sScriptDST):
                            logging.info("INFO: Deleting %s" % p_sScriptDST)
                            os.system('rm "%s" > /dev/null 2>&1' % p_sScriptDST)
                    else:
                        if not os.path.exists(p_sScriptDST):
                            logging.info("INFO: Copying file %s to %s" % \
                                        (p_sScriptSRC, p_sScriptDST))
                            os.system('cp "%s" "%s" > /dev/null 2>&1' % \
                                     (p_sScriptSRC, p_sScriptDST))

    def _loop(self, p_iTime = 0.5):
        while True:
            if self.m_bPRestart: self._restart_ES()
            self._get_mounted_list()
            if self.m_bChanges:
                logging.info("INFO: Changes detected")
                if self._check_umount(): self._restart_ES()
                elif self._check_mount(): self._restart_ES()
            time.sleep(p_iTime)

    def _restart_ES(self):
        """ Restart ES if it's running """
        if check_process("emulationstatio"):
            self.m_bPRestart = True
            if check_process(self.m_lProcesses):
                time.sleep(0.5)
                #logging.info("INFO: Pending Reboot...")
                return
            if self.mounted_time():
                logging.info("INFO: Restarting EmulationStation...")
                commandline = "touch /tmp/es-restart "
                commandline += "&& pkill -f \"/opt/retropie"
                commandline += "/supplementary/.*/emulationstation([^.]|$)\""
                os.system(commandline)
                os.system('clear')
            self.m_bPRestart = False

    def mounted_time(self):
        if self.m_bUSBMounted:
            p_iTime = time.time() - self.m_iMntTime
        else:
            p_iTime = time.time() - self.m_iUMntTime
        uptime = self._get_es_uptime()
        logging.info("INFO: emulationstation uptime: %ssecs, " % uptime \
                     + "device mount/umounted since %ssecs" % p_iTime)
        if uptime > p_iTime: return True
        logging.info("INFO: canceling emulationstation restart")
        return False

    def _get_es_uptime(self):
        commandline = 'ps -Ao comm,etime | grep -i emulationstatio'
        try:
            output = subprocess.check_output(commandline, shell=True).decode("utf-8")
            output = re.sub(r' +', " ", output).split('\n')
        except: output = None
        uptime = []
        for line in output:
            if "emulationstatio" in line and ":" in line:
                uptime.append(self._get_seconds(line.strip().split(' ')[1]))
        return min(uptime)

    def _get_seconds(self, p_sTime):
        timer = p_sTime.split(':')
        if len(timer) == 2: h = 0
        elif len(timer) == 3: h = timer[0]
        m = timer[-2]
        s = timer[-1]
        secs = int(h) * 3600 + int(m) * 60 + int(s)
        return secs

    # clean trigger files
    def __clean(self):
        os.system('rm "%s" > /dev/null 2>&1' % CRT_EXTSTRG_TRIG_MNT_PATH)
        os.system('rm "%s" > /dev/null 2>&1' % CRT_EXTSTRG_TRIG_UMNT_PATH)
        os.system('touch "%s" > /dev/null 2>&1' % CRT_EXTSTRG_TRIG_UMNT_PATH)

    def __temp(self):
        if CLEAN_LOG_ONSTART:
            if os.path.exists (LOG_PATH):
                os.system('rm "%s"' % LOG_PATH)
        logging.basicConfig(filename=LOG_PATH, level=__DEBUG__,
        format='[%(asctime)s] %(levelname)s - %(filename)s:%(funcName)s - %(message)s')
        
try:
    oUSBAutoMount = USBAutoService()
    oUSBAutoMount.run()
except Exception as e:
    with open(EXCEPTION_LOG, 'a') as f:
        f.write(str(e))
        f.write(traceback.format_exc())