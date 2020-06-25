#!/usr/bin/python
# -*- coding: utf-8 -*-


"""
RGB cable selector for Retropie CRT Edition

Module to change configuration in config.txt for different RGB cables by -krahs-
CRT Daemon for jamma controls (third party software activator)

https://github.com/krahsdevil/crt-for-retropie/

Copyright (C)  2018/2020 -krahs- - https://github.com/krahsdevil/
Copyright (C)  2020 dskywalk - http://david.dantoine.org

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
import os, sys, traceback
import commands, time
import logging

sys.dont_write_bytecode = True

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(SCRIPT_DIR + "/../"))
from main_paths import MODULES_PATH
sys.path.append(MODULES_PATH)

from controls_mapping import CTRLSMgmt
from launcher_module.core_paths import *
from launcher_module.file_helpers import *
from launcher_module.utils import check_process, wait_process, \
                                  show_info, menu_options

LOG_PATH = os.path.join(TMP_LAUNCHER_PATH, "CRT_RGB_Cable_Selector.log")
EXCEPTION_LOG = os.path.join(TMP_LAUNCHER_PATH, "backtrace.log")

__VERSION__ = '0.1'
__DEBUG__ = logging.INFO # logging.ERROR
CLEAN_LOG_ONSTART = True

class CableSelector(object):
    """ virtual class for USB Automount enable/disable/eject """

    m_lCfgLines = ({'line': 'jamma_cable=',
                    'value': -1, 'label': 'jamma'},
                   {'line': 'dtparam=i2c_vc=on',
                    'value': 0, 'label': 'i2c1'},
                   {'line': 'dtoverlay=i2c-gpio,i2c_gpio_sda=10,i2c_gpio_scl=11',
                    'value': 0, 'label': 'i2c2'},
                   {'line': 'dpi_output_format=6',
                    'value': 0, 'label': 'opt1'},
                   {'line': 'dtoverlay=pwm-2chan,pin=18,func=2,pin2=19,func2=2',
                    'value': 0, 'label': 'opt2'},
                   {'line': 'disable_audio_dither=1',
                    'value': 0, 'label': 'audio1'},
                   {'line': 'dtparam=audio=on',
                    'value': 0, 'label': 'audio2'})

    m_lCables = ["rgb-pi", "vga666", "pi2scart", "jamma-rgb-pi", "pi2jamma"]

    m_bUploadCFG = False  # If True config.txt was changed
    m_bRebootES = False

    m_iCableOverlay = ""  # Overlay can be vga666 or rgb-pi
    m_iCableJamma = -1    # Cable Jamma 0 = none; 1 = pi2jamma; 2 = jamma-rgb-pi
    m_sCableName = ""     # Identify exact cable model regular-jamma

    m_bFix = False        # True if current configuration has some issue

    m_bDaemonExist = False
    m_bDaemonLoad = False

    m_sBootTempFile = ""
    m_sFstBootApp = 'resize2fs' # For first boot, resize2fs will be working

    m_sTitle = ""
    m_lChoices = []             #Choices for selector
    m_lToFix = []               #Options wrong configured
    m_lInfoReboot = [("SYSTEM WILL REBOOT NOW...", "OK")]
    
    m_oControls = None

    def __init__(self):
        self.__temp()
        logging.info("INFO: Launching CRT cable selector")

    def prepare(self):
        #self.__clean()
        self.m_sBootTempFile = generate_random_temp_filename(RASP_BOOTCFG_FILE)
        self._clone_boot_cfg()
        self._check_crtdaemon() # Check service
        self._check_base_config()
        self.m_oControls = CTRLSMgmt()

    def change_cable(self, p_sCableName = None):
        if p_sCableName not in self.m_lCables: return False
        self.prepare()
        self._cable_config(p_sCableName, True)
        self._ctrls_configuration(p_sCableName)
        self._upload_boot_cfg()
        return self.get_cable()
        
    def get_cable(self):
        self.prepare()
        self.__clean()
        if self.m_bFix: return False
        return self.m_sCableName

    def get_cable_list(self):
        return self.m_lCables
        
    def run(self):
        self.prepare()
        show_info('PLEASE WAIT...')
        self._check_if_first_boot()
        self._loop()

    def _check_base_config(self):
        self._check_boot_config_file()
        self._create_missing_config()
        self.m_bFix = self._check_current_cable()

    def _loop(self):
        p_sOption = ""
        self._generate_cable_list()
        while True:
            p_sOption = menu_options(self.m_lChoices, self.m_sTitle)
            if p_sOption != 'EXIT':
                self._cable_config(p_sOption, True)
            break
        self._ctrls_configuration(p_sOption)
        self._upload_boot_cfg()
        self._restart()

    def _generate_cable_list(self):
        self.m_sTitle = ""
        self.m_lChoices = []
        self.m_sTitle = "CHOOSE RGB CABLE"
        for cable in self.m_lCables:
            if self.m_sCableName == cable and self.m_bFix:
                self.m_lChoices.append(('[*] ' + cable.upper() + \
                                        ' (Current, need FIX)', cable))
            elif self.m_sCableName == cable:
                self.m_lChoices.append(('[*] ' + cable.upper() + \
                                        ' (No change)', 'EXIT'))
            else:
                self.m_lChoices.append(('[ ] ' + cable.upper(), cable))

    def _check_boot_config_file(self):
        # Look for options
        logging.info('INFO: Checking configured options in config.txt:')
        with open(self.m_sBootTempFile, 'r') as file:
            for line in file:
                if 'dtoverlay=rgb-pi' in line:
                    self.m_iCableOverlay = 2
                    logging.info('INFO: detected dtoverlay=rgb-pi')
                elif 'dtoverlay=vga666' in line:
                    self.m_iCableOverlay = 1
                    logging.info('INFO: Detected dtoverlay=vga666')
                else:
                    for item in self.m_lCfgLines:
                        if item['label'] == 'jamma':
                            if item['line'] in line:
                                lValues = line.strip().replace('=',' ').split(' ')
                                item['value'] = int(lValues[1].strip())
                                logging.info('INFO: detected %s%s' \
                                             % (item['line'], item['value']))
                                if line[:1] == '#':
                                    modify_line(self.m_sBootTempFile, item['line'],
                                                item['line']+str(item['value']))
                                    logging.info('WARNING: \'jamma_cable=\' ' + \
                                                 'fixed {was commented line}')
                                if item['value'] not in {0, 1, 2}:
                                    item['value'] = 0
                                    modify_line(self.m_sBootTempFile, item['line'],
                                                item['line']+str(item['value']))
                                    logging.info('WARNING: \'jamma_cable=\' ' + \
                                                 ' fixed {wrong value}')
                        else:
                            if item['line'] in line:
                                if line[:1] == '#':
                                    item['value'] =  1
                                    state = 'commented line'
                                else:
                                    item['value'] =  2
                                    state = 'no-commented line'
                                logging.info('INFO: detected %s {%s}' \
                                             % (item['line'], state))

    def _create_missing_config(self):
        p_bConfigs = False
        for item in self.m_lCfgLines:
            if item['label'] == 'jamma':
                if item['value'] < 0:
                    p_bConfigs = True
                    os.system('echo \"\n# Set if you have a jamma cable; ' + \
                              '0=none; 1=pi2jamma; 2=jamma-rgb-pi\" >> %s' \
                              % self.m_sBootTempFile)
                    os.system('echo \"%s0\" >> %s' % (item['line'],
                                                      self.m_sBootTempFile))
                    logging.info('MISSING: created missing config ' + \
                                 'line: {%s0}' % item['line'])
            else:
                if item['value'] == 0:
                    p_bConfigs = True
                    os.system('echo \"\n#%s\" >> %s' % (item['line'],
                                                        self.m_sBootTempFile))
                    logging.info('MISSING: created missing config ' + \
                                 ' line: {#%s}' % item['line'])
        if p_bConfigs:
            # Re-check again config options in boot.txt because of
            # new config lines in /boot/config.txt
            logging.info("INFO: checking a second time config.txt")
            self._check_boot_config_file()

        self.m_bUploadCFG = p_bConfigs

    def _check_current_cable(self):
        #Check if current RGB output is well configured
        #Return True if current config seems to be wrong for identified cable
        p_bCheck = False
        self._detect_cable_model()
        logging.info("INFO: checking configuration for %s" \
                     % self.m_sCableName.upper())
        p_bCheck = self._cable_config(self.m_sCableName, False)
        if not p_bCheck:
            logging.info("INFO: config for current cable seems OK")
        return p_bCheck

    def _cable_config(self, p_sCableName, write = False):
        """ Check _check_config_lines(self) function for info """
        p_bCheck = False
        if p_sCableName == 'rgb-pi':
            p_bCheck = self._check_config_lines(2, 2, 1, 2, 2, 0, 1, 1, write)
        elif p_sCableName == 'jamma-rgb-pi':
            p_bCheck = self._check_config_lines(2, 2, 1, 2, 2, 2, 2, 2, write)
        elif p_sCableName == 'vga666':
            p_bCheck = self._check_config_lines(1, 1, 1, 2, 1, 0, 1, 1, write)
        elif p_sCableName == 'pi2scart':
            p_bCheck = self._check_config_lines(1, 1, 2, 2, 1, 0, 1, 1, write)
        elif p_sCableName == 'pi2jamma':
            p_bCheck = self._check_config_lines(1, 1, 2, 2, 1, 1, 1, 1, write)
        return p_bCheck

    def _ctrls_configuration(self, p_sCableName):
        """
        Will apply all default keyboard controls for pi2jamma.
        If current cable is pi2jamma and exit withouth change,
        function will re-apply controls on EmulationStation and 
        Retroarch and restart EmulationStation.
        If any other cable is selected and no change, no controls
        reconfiguration.
        If change from pi2jamma to other then controls config
        will be cleaned.        
        """
        # pi2jamma controls
        if p_sCableName.lower() == 'exit' and \
           self.m_sCableName == 'pi2jamma':
            self.m_bRebootES = self.m_oControls.pi2jamma_enable_controls()
        elif p_sCableName == 'pi2jamma':
            self.m_bRebootES = self.m_oControls.pi2jamma_enable_controls()
        else:
            self.m_bRebootES = self.m_oControls.pi2jamma_disable_controls()

    def _detect_cable_model(self):
        p_iJamma = self.get_config_line_value('jamma')
        p_iAudio1 = self.get_config_line_value('audio1')
        p_iAudio2 = self.get_config_line_value('audio2')

        if p_iJamma == 0:
            if self.m_iCableOverlay == 1:
                self.m_sCableName = 'vga666'
                if p_iAudio1 == 2 and p_iAudio2 == 2:
                    self.m_sCableName = 'pi2scart'
            elif self.m_iCableOverlay == 2:
                self.m_sCableName = 'rgb-pi'
        else:
            if p_iJamma == 1:
                self.m_sCableName = 'pi2jamma'
                if self.m_iCableOverlay == 2:
                    logging.info("WARNING: current jamma_cable mode is not " + \
                                 " compatible with rgb-pi DTO, disabling " + \
                                 "jamma {jamma_cable=0}")
                    modify_line(self.m_sBootTempFile, 'jamma_cable=',
                                'jamma_cable=0')
                    self.m_sCableName = 'rgb-pi'
                    p_iJamma = 0
            elif p_iJamma == 2:
                self.m_sCableName = 'jamma-rgb-pi'
                if self.m_iCableOverlay == 1:
                    logging.info("WARNING: current jamma_cable mode is not " + \
                                 "compatible with vga666 DTO, disabling " + \
                                 "jamma {jamma_cable=0}")
                    modify_line(self.m_sBootTempFile, 'jamma_cable=',
                                'jamma_cable=0')
                    self.m_sCableName = 'vga666'
                    if p_iAudio1 == 2 and p_iAudio2 == 2:
                        self.m_sCableName = 'pi2scart'
                    p_iJamma = 0
            else:
                pass
        logging.info("INFO: RGB CABLE IDENTIFIED: [%s]" \
                     % self.m_sCableName.upper())

    def get_config_line_value(self, p_sLabel, p_sData = 'value'):
        for item in self.m_lCfgLines:
            if item['label'] == p_sLabel:
                return item[p_sData]
        return False

    def _check_config_lines(self, opt1, opt2, audio1, audio2, dto,
                            jamma, i2c1, i2c2, write = False):
        """
        This function will check the config lines in config.txt defined
        in p_bCheck variable for RGB cable identification.

        opt1/opt2/audio1/audio2 can be 1/2:
            1 = option disabled, commented line with '#' at the begining
            2 = option enabled, not commented line

        jamma can be 0/1/2:
            0 = jamma cable disabled        (jamma_cable=0)
            1 = jamma cable is pi2jamma     (jamma_cable=1)
            2 = jamma cable is jamma-rgb-pi (jamma_cable=2)

        dto can be 1/2
            1 = vga666 'dtoverlay=vga666'
            2 = rgb-pi 'dtoverlay=rgb-pi'

        i2c1/i2c2 can be 1/2
            1 = option disabled, commented line with '#' at the begining
            2 = option enabled, not commented line

        jamma:  refers to 'jamma_cable='
        opt1:   refers to 'dpi_output_format=6'
        opt2:   refers to 'dtoverlay=pwm-2chan,pin=18,func=2,pin2=19,func2=2'
        audio1: refers to 'disable_audio_dither=1'
        audio2: refers to 'dtparam=audio=on'
        dto:    refers to 'dtoverlay=vga666' or 'dtoverlay=rgb-pi'
        i2c1:   refers to 'dtparam=i2c_vc=on'
        i2c2:   refers to 'dtoverlay=i2c-gpio,i2c_gpio_sda=10,i2c_gpio_scl=11'
        """
        p_bCheck = False
        self.m_lToFix = []

        if write:
            if dto != self.m_iCableOverlay:
                if dto == 1:
                    p_sDTONew = 'dtoverlay=vga666'
                    p_sDTOOld = 'dtoverlay=rgb-pi'
                elif dto == 2:
                    p_sDTONew = 'dtoverlay=rgb-pi'
                    p_sDTOOld = 'dtoverlay=vga666'
                modify_line(self.m_sBootTempFile, p_sDTOOld, p_sDTONew)
                self.m_bUploadCFG = True
                logging.info("WARNING: DTO WAS CHANGED to %s" % p_sDTONew)

        for item in self.m_lCfgLines:
            if item['value'] != eval(item['label']):
                p_bCheck = True
                if item['label'] == 'jamma':
                    state = "disabled" if eval(item['label']) == 0 else jamma
                    line = '%s%s' % (item['line'], eval(item['label']))
                else:
                    state = "un-commented" if eval(item['label']) == 2 \
                            else "commented"
                    line = str(item['line']) if eval(item['label']) == 2 \
                           else '#'+str(item['line'])
                self.m_lToFix.append((item['line'], 'opt'))
                if write:
                    modify_line(self.m_sBootTempFile, item['line'], line)
                    self.m_bUploadCFG = True
                    logging.info("WARNING: %s (WAS CHANGED to be %s)" \
                                 % (item['line'], state))
                else:
                    logging.info("WARNING: %s (must be %s)" \
                                 % (item['line'], state))
        return p_bCheck

    def _check_if_first_boot(self):
        """ Check if resize2fs is working on expanding SD partition """
        if check_process(self.m_sFstBootApp):
            logging.info("WARNING: Wait until resize2fs finish")
            wait_process(self.m_sFstBootApp, 'stop', 1, 5)

    def _check_crtdaemon(self):
        if not self._check_service(CRT_RGB_SRV_FILE, 'load'):
            self._remove_crtdaemon()
            self._install_crtdaemon()

    def _check_crtdaemon_files(self):
        """ Check if needed service files exists """
        bCheck01 = os.path.exists(CRT_RGB_SRV_PATH)
        bCheck02 = os.path.exists(CRT_RGB_CORE_PATH)
        if bCheck01 and bCheck02:
            logging.info("INFO: Found daemon files %s and %s" \
                         % (CRT_RGB_SRV_FILE, CRT_RGB_CORE_FILE))
            return True
        logging.info("ERROR: NOT found daemon files %s and %s" \
                     % (CRT_RGB_SRV_FILE, CRT_RGB_CORE_FILE))
        return False

    def _install_crtdaemon(self):
        if self._check_crtdaemon_files:
            #show_info('REINSTALLING CRT DAEMON...')
            os.system('sudo cp %s /etc/systemd/system/%s > /dev/null 2>&1' \
                      % (CRT_RGB_SRV_PATH, CRT_RGB_SRV_FILE))
            os.system('sudo chmod +x /etc/systemd/system/%s > /dev/null 2>&1' \
                      % CRT_RGB_SRV_FILE)
            os.system('sudo systemctl enable %s > /dev/null 2>&1' \
                      % CRT_RGB_SRV_FILE)
            #os.system('sudo systemctl start %s > /dev/null 2>&1' \
            #          % CRT_RGB_SRV_FILE)

    def _remove_crtdaemon(self):
        if self._check_crtdaemon_files:
            #show_info('CLEANING CRT DAEMON...')
            os.system('sudo systemctl disable %s > /dev/null 2>&1' \
                      % CRT_RGB_SRV_FILE)
            os.system('sudo systemctl stop %s > /dev/null 2>&1' \
                      % CRT_RGB_SRV_FILE)
            os.system('sudo rm /etc/systemd/system/%s > /dev/null 2>&1' \
                      % CRT_RGB_SRV_FILE)

    def _check_service(self, p_sService, p_sState):
        """
        This function will return true or false for this options:
        p_sState = 'load' Will return if service is loaded
        p_sState = 'run'  Will return if service is loaded
        """
        p_bLoaded = False
        p_bRunning = False
        p_sCommand = 'systemctl list-units --all | grep \"%s\"' % p_sService
        p_sOutput = commands.getoutput(p_sCommand)
        if p_sService in p_sOutput:
            p_bLoaded = True
            if 'running' in p_sOutput:
                p_bRunning = True
        if p_sState == 'load': return p_bLoaded
        elif p_sState == 'run': return p_bRunning

    def _restart(self):
        """ Restart system or reboot ES if needed """
        commandline = ""
        if not self.m_bUploadCFG:
            logging.info('INFO: NO changes in /boot/config.txt; ' + \
                         'no reboot needed')
            # check if ES must reboot
            if self.m_bRebootES and check_process("emulationstatio"):
                show_info('CLEANING KEYBOARD CONFIG', 2000)
                show_info('EMULATIONSTATION WILL RESTART NOW')
                commandline = "touch /tmp/es-restart "
                commandline += "&& pkill -f \"/opt/retropie"
                commandline += "/supplementary/.*/emulationstation([^.]|$)\""
                os.system(commandline)
                time.sleep(1)
        else:
            commandline = 'sudo reboot now'
            show_info(self.m_lInfoReboot)
            os.system(commandline)
        sys.exit(0)

    def _clone_boot_cfg(self):
        os.system('cp %s %s' %(RASP_BOOTCFG_FILE, self.m_sBootTempFile))
        logging.info('INFO: preparing a temp copy of config.txt at %s' \
                     % self.m_sBootTempFile)

    def _upload_boot_cfg(self):
        if self.m_bUploadCFG:
            os.system('sudo cp %s %s' % (self.m_sBootTempFile, RASP_BOOTCFG_FILE))
            logging.info('INFO: uploading modified config.txt to /boot')
        self.__clean()

    # clean system
    def __clean(self):
        remove_file(self.m_sBootTempFile)

    def __temp(self):
        if CLEAN_LOG_ONSTART:
            remove_file(LOG_PATH)
        logging.basicConfig(filename=LOG_PATH, level=__DEBUG__,
        format='[%(asctime)s] %(levelname)s - %(filename)s:%(funcName)s - %(message)s')

if __name__ == '__main__':
    try:
        oLaunch = CableSelector()
        oLaunch.run()
    except Exception as e:
        with open(EXCEPTION_LOG, 'a') as f:
            f.write(str(e))
            f.write(traceback.format_exc())