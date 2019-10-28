#!/usr/bin/python
# coding: utf-8

"""
pattern_datas.py.

Centering Pattern Utility for CRT image adjusting by Krahs

https://github.com/krahsdevil/crt-for-retropie/

Copyright (C)  2018/2019 -krahs- - https://github.com/krahsdevil/
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

import os, pygame
import logging

CRT_PATH = "/opt/retropie/configs/all/CRT"

TEST_IMGPATTERN_PATH = "" #Assign Pattern to draw
TEST_MEDIA_PATH = os.path.join(CRT_PATH,"bin/ScreenUtilityFiles/resources/assets/screen_center_utility")
PATTERN_INGAME_PATH = os.path.join(TEST_MEDIA_PATH,
                      "screen_center_utility_su_crosshatch.png")
PATTERN_SYSTEM_PATH = os.path.join(TEST_MEDIA_PATH,
                      "screen_center_utility_su_pattern.png")

RED = pygame.Color(255, 0, 0)
BLACK = pygame.Color(0, 0, 0)
GREY = pygame.Color(50, 50, 50)
WHITE = pygame.Color(255,255,255)
YELLOW = pygame.Color(255,255,0)
BLUE = pygame.Color(0,0,153)
BLUEDARK = pygame.Color(66,66,231)
BLUELIGHT = pygame.Color(165,165,255)
BLUEUNSELECT = pygame.Color(110,110,255)

class datas(object):
    """ virtual class for return info box coordinates and text """
    m_dPatternAdj = {}
    m_dConfigFile = {}
    m_sEnv = ""

    m_iMaxOffSetX = 0
    m_iMaxOffSetY = 0

    m_lInfo = [] #Full information for info text
    m_lBox = [] #Full information for the box

    m_lInfo_Idx = {}
    m_lInfo_Var = {}
    m_lInfo_Text = ()
    m_lInfo_Pos = ()
    m_lInfo_Rnd = ()
    m_lBox_Idx = {}
    m_lBox_Var = {}
    m_lBox_Pos = ()
    m_lBox_Rnd = ()

    m_iTCentX = 0
    m_iTCentY = 0
    m_iBCentX = 0
    m_iBCentY = 0

    m_lPattern = {"posx": 0, "posy": 0, "width": 0, "height": 0}
    m_iCurrent = 0
    m_iCurrentSub = 0

    def __init__(self, p_iPatternAdj, p_dConfigFile, p_sEnv):
        self.m_dPatternAdj = p_iPatternAdj
        self.m_dConfigFile = p_dConfigFile
        self.m_sEnv = p_sEnv
        self.prepare()

    def prepare(self):
        self.prepare_datas()
        self.prepare_pattern()

    def get_info_datas(self):
        return self.m_lInfo, self.m_lBox

    def get_pattern_datas(self):
        self.prepare_pattern()
        return self.m_lPattern, TEST_IMGPATTERN_PATH

    def update(self, p_iMaxOffsetX, p_iMaxOffsetY):
        self.m_iMaxOffSetX = p_iMaxOffsetX
        self.m_iMaxOffSetY = p_iMaxOffsetY
        self.update_menu_colors()
        self.update_menu_text()
        return self.get_info_datas()

    def pass_menu_options(self, p_iCurrent, p_iCurrentSub):
        self.m_iCurrent = p_iCurrent
        self.m_iCurrentSub = p_iCurrentSub

    def prepare_datas(self):
        """ This function will prepare all the needed datas to create the whole
            test pattern on screen. Box for showing differents options and the
            options itself, coordinates for drawing or colours.Custom datas for
            the different tests: system60, system50, test60 or test50. Datas are
            separated on different variables for better comprenhension and join
            all together trough a dedicated function for main program. """

        """Global Centering"""
        self.m_iTCentX = (self.m_dPatternAdj["ScreenHSize"]/2)
        self.m_iTCentY = (self.m_dPatternAdj["ScreenVSize"])
        self.m_iBCentX = (self.m_dPatternAdj["ScreenHSize"]/2)
        self.m_iBCentY = (self.m_dPatternAdj["ScreenVSize"])

        self.m_lInfo_Text = ({"label": "info1", "text" : "Offset X:%s" %
                              self.m_dConfigFile["offsetX"]},
                             {"label": "info2", "text" : "Offset Y:%s" %
                              self.m_dConfigFile["offsetY"]},
                             {"label": "info3", "text" : "H:%s|V:%s" %
                              (self.m_dConfigFile["width"],
                               self.m_dConfigFile["height"])},
                             {"label": "line1",
                              "text" : "PRESS ANY DIRECTION"},
                             {"label": "line2",
                              "text" : "TO CENTER THE SCREEN"},
                             {"label": "line3",
                              "text" : "<Press any button to set>"}
                             )

        self.m_lInfo_Rnd = ({"label": "info1", "rndimg": None,
                             "rndpos": None, "rndcolor": WHITE},
                            {"label": "info2", "rndimg": None,
                             "rndpos": None, "rndcolor": WHITE},
                            {"label": "info3", "rndimg": None,
                             "rndpos": None, "rndcolor": WHITE},
                            {"label": "line1", "rndimg": None,
                             "rndpos": None, "rndcolor": WHITE},
                            {"label": "line2", "rndimg": None,
                             "rndpos": None, "rndcolor": WHITE},
                            {"label": "line3", "rndimg": None,
                             "rndpos": None, "rndcolor": WHITE}
                            )

        if self.m_sEnv == "system50":
            """TEXT DESIGN"""
            #'self.m_lInfo_Var': Index of text lines to complete the library
            self.m_lInfo_Idx = ["info1", "info2", "info3",
                                "line1", "line2", "line3"]

            #'self.m_lInfo_Var': Libraries for text info,
            # separated for better comprenhension
            self.m_lInfo_Var = {"self.m_lInfo_Text", "self.m_lInfo_Pos",
                                "self.m_lInfo_Rnd"}

            self.m_lInfo_Pos = ({"label": "info1", "posx": self.m_iTCentX-135,
                                 "posy": self.m_iTCentY-82, "center": "midleft"},
                                {"label": "info2", "posx": self.m_iTCentX-31,
                                 "posy": self.m_iTCentY-82, "center": "midleft"},
                                {"label": "info3", "posx": self.m_iTCentX+71,
                                 "posy": self.m_iTCentY-82, "center": "midleft"},
                                {"label": "line1", "posx": self.m_iTCentX,
                                 "posy": self.m_iTCentY-64, "center": "center"},
                                {"label": "line2", "posx": self.m_iTCentX,
                                 "posy": self.m_iTCentY-54, "center": "center"},
                                {"label": "line3", "posx": self.m_iTCentX,
                                 "posy": self.m_iTCentY-43, "center": "center"}
                                )

            """BOX DESIGN"""
            #'self.m_lBox_Idx': Index of rectangles to complete the library
            self.m_lBox_Idx = ["rect1", "rect2", "rect3", "rect4", "rect5"]

            #'self.m_lBox_Var': Libraries for Box,
            # separated for better comprenhension
            self.m_lBox_Var = {"self.m_lBox_Pos", "self.m_lBox_Rnd"}

            self.m_lBox_Pos = ({"label": "rect1", "posx": self.m_iBCentX-148,
                                "posy": self.m_iBCentY-90},
                               {"label": "rect2", "posx": self.m_iBCentX-152,
                                "posy": self.m_iBCentY-93},
                               {"label": "rect3", "posx": self.m_iBCentX-150,
                                "posy": self.m_iBCentY-91},
                               {"label": "rect4", "posx": self.m_iBCentX-150,
                                "posy": self.m_iBCentY-91},
                               {"label": "rect5", "posx": self.m_iBCentX-150,
                                "posy": self.m_iBCentY-91}
                               )

            self.m_lBox_Rnd = ({"label": "rect1", "width": 304, "height" : 61,
                                "fill" : 0, "rndcolor": GREY},
                               {"label": "rect2", "width": 304, "height" : 61,
                                "fill" : 0, "rndcolor": WHITE},
                               {"label": "rect3", "width": 300, "height" : 57,
                                "fill" : 0, "rndcolor": BLUE},
                               {"label": "rect4", "width": 300, "height" : 57,
                                "fill" : 1, "rndcolor": WHITE},
                               {"label": "rect5", "width": 300, "height" : 17,
                                "fill" : 1, "rndcolor": WHITE}
                               )

        elif self.m_sEnv == "system60":
            """TEXT DESIGN"""
            #'self.m_lInfo_Var': Index of text lines to complete the library
            self.m_lInfo_Idx = ["info1", "info2", "info3",
                                "line1", "line2", "line3"]

            #'self.m_lInfo_Var': Libraries for text info,
            # separated for better comprenhension
            self.m_lInfo_Var = {"self.m_lInfo_Text", "self.m_lInfo_Pos",
                                "self.m_lInfo_Rnd"}

            self.m_lInfo_Pos = ({"label": "info1", "posx": self.m_iTCentX-109,
                                 "posy": self.m_iTCentY-84, "center": "midleft"},
                                {"label": "info2", "posx": self.m_iTCentX-109,
                                 "posy": self.m_iTCentY-73, "center": "midleft"},
                                {"label": "info3", "posx": self.m_iTCentX+39,
                                 "posy": self.m_iTCentY-84, "center": "midleft"},
                                {"label": "line1", "posx": self.m_iTCentX,
                                 "posy": self.m_iTCentY-55, "center": "center"},
                                {"label": "line2", "posx": self.m_iTCentX,
                                 "posy": self.m_iTCentY-45, "center": "center"},
                                {"label": "line3", "posx": self.m_iTCentX,
                                 "posy": self.m_iTCentY-34, "center": "center"}
                                )

            """BOX DESIGN"""
            #'self.m_lBox_Idx': Index of rectangles to complete the library
            self.m_lBox_Idx = ["rect1", "rect2", "rect3", "rect4", "rect5"]

            #'self.m_lBox_Var': Libraries for Box, separated for better comprenhension
            self.m_lBox_Var = {"self.m_lBox_Pos", "self.m_lBox_Rnd"}

            self.m_lBox_Pos = ({"label": "rect1", "posx": self.m_iBCentX-113,
                                "posy": self.m_iBCentY-92},
                               {"label": "rect2", "posx": self.m_iBCentX-117,
                                "posy": self.m_iBCentY-95},
                               {"label": "rect3", "posx": self.m_iBCentX-115,
                                "posy": self.m_iBCentY-93},
                               {"label": "rect4", "posx": self.m_iBCentX-115,
                                "posy": self.m_iBCentY-93},
                               {"label": "rect5", "posx": self.m_iBCentX-115,
                                "posy": self.m_iBCentY-93}
                               )

            self.m_lBox_Rnd = ({"label": "rect1", "width": 234, "height" : 72,
                                "fill" : 0, "rndcolor": GREY},
                               {"label": "rect2", "width": 234, "height" : 72,
                                "fill" : 0, "rndcolor": WHITE},
                               {"label": "rect3", "width": 230, "height" : 68,
                                "fill" : 0, "rndcolor": BLUE},
                               {"label": "rect4", "width": 230, "height" : 68,
                                "fill" : 1, "rndcolor": WHITE},
                               {"label": "rect5", "width": 230, "height" : 28,
                                "fill" : 1, "rndcolor": WHITE}
                               )

        elif self.m_sEnv == "test60" or self.m_sEnv == "test50":
            """TEXT DESIGN"""
            #'self.m_lInfo_Var': Index of text lines to complete the library
            self.m_lInfo_Idx = ["info1", "info2", "info3",
                                "line1", "line2", "line3"]

            #'self.m_lInfo_Var': Libraries for text info,
            # separated for better comprenhension
            self.m_lInfo_Var = {"self.m_lInfo_Text", "self.m_lInfo_Pos",
                                "self.m_lInfo_Rnd"}

            self.m_lInfo_Pos = ({"label": "info1", "posx": self.m_iTCentX-475,
                                 "posy": self.m_iTCentY-80, "center": "midleft"},
                                {"label": "info2", "posx": self.m_iTCentX-114,
                                 "posy": self.m_iTCentY-80, "center": "midleft"},
                                {"label": "info3", "posx": self.m_iTCentX+225,
                                 "posy": self.m_iTCentY-80, "center": "midleft"},
                                {"label": "line1", "posx": self.m_iTCentX,
                                 "posy": self.m_iTCentY-60, "center": "center"},
                                {"label": "line2", "posx": self.m_iTCentX,
                                 "posy": self.m_iTCentY-50, "center": "center"},
                                {"label": "line3", "posx": self.m_iTCentX,
                                 "posy": self.m_iTCentY-41, "center": "center"}
                                )

            """BOX DESIGN"""
            #'self.m_lBox_Idx': Index of rectangles to complete the library
            self.m_lBox_Idx = ["rect1", "rect2", "rect3", "rect4", "rect5"]

            #'self.m_lBox_Var': Libraries for Box,
            # separated for better comprenhension
            self.m_lBox_Var = {"self.m_lBox_Pos", "self.m_lBox_Rnd"}

            self.m_lBox_Pos = ({"label": "rect1", "posx": self.m_iBCentX-498,
                                "posy": self.m_iBCentY-89},
                               {"label": "rect2", "posx": self.m_iBCentX-513,
                                "posy": self.m_iBCentY-91},
                               {"label": "rect3", "posx": self.m_iBCentX-500,
                                "posy": self.m_iBCentY-89},
                               {"label": "rect4", "posx": self.m_iBCentX-500,
                                "posy": self.m_iBCentY-89},
                               {"label": "rect5", "posx": self.m_iBCentX-500,
                                "posy": self.m_iBCentY-89}
                               )

            self.m_lBox_Rnd = ({"label": "rect1", "width": 1026, "height" : 61,
                                "fill" : 0, "rndcolor": GREY},
                               {"label": "rect2", "width": 1026, "height" : 61,
                                "fill" : 0, "rndcolor": WHITE},
                               {"label": "rect3", "width": 1000, "height" : 57,
                                "fill" : 0, "rndcolor": BLUE},
                               {"label": "rect4", "width": 1000, "height" : 57,
                                "fill" : 1, "rndcolor": WHITE},
                               {"label": "rect5", "width": 1000, "height" : 17,
                                "fill" : 1, "rndcolor": WHITE}
                               )

        self._generate_info(self.m_lInfo_Idx, self.m_lInfo_Var, "self.m_lInfo")
        self._generate_info(self.m_lBox_Idx, self.m_lBox_Var, "self.m_lBox")

    def prepare_pattern(self):
        global TEST_IMGPATTERN_PATH
        VOverscan = 0
        HOverscan = 0
        """ Init and refresh pattern size and position data during centering """
        if self.m_sEnv == "test60":
            TEST_IMGPATTERN_PATH = PATTERN_INGAME_PATH #Select pattern for ingame 60hz
            PatternResizeX = (self.m_dPatternAdj["PatternHSize"]+
                             (6*self.m_dConfigFile["width"]))
            PatternResizeY = (self.m_dPatternAdj["PatternVSize"]+
                             (2*self.m_dConfigFile["height"]))
            PatternCentX = ((self.m_dPatternAdj["ScreenHSize"]/2)+
                            (self.m_dConfigFile["offsetX"]*4)-
                            (8-(self.m_dConfigFile["width"]/2)))
            PatternCentY = ((self.m_dPatternAdj["ScreenVSize"]/2)+
                             self.m_dConfigFile["offsetY"])

        elif self.m_sEnv == "system50" or self.m_sEnv == "system60":
            #Select pattern for system (EmulationStation)
            TEST_IMGPATTERN_PATH = PATTERN_SYSTEM_PATH

            """Apply overscan if 320x240"""
            if self.m_dPatternAdj["PatternHSize"] == 320 and \
               self.m_dPatternAdj["PatternVSize"] == 240:
                VOverscan = 16
                HOverscan = 18
            PatternResizeX = (self.m_dPatternAdj["PatternHSize"]-
                              HOverscan+(2*self.m_dConfigFile["width"]))
            PatternResizeY = (self.m_dPatternAdj["PatternVSize"]-VOverscan+
                             (2*self.m_dConfigFile["height"]))
            PatternCentX = ((self.m_dPatternAdj["ScreenHSize"]/2)+
                            (self.m_dConfigFile["offsetX"]))
            PatternCentY = ((self.m_dPatternAdj["ScreenVSize"]/2)+
                            (self.m_dConfigFile["offsetY"]))

        self.m_lPattern["posx"] = PatternCentX
        self.m_lPattern["posy"] = PatternCentY
        self.m_lPattern["width"] = PatternResizeX
        self.m_lPattern["height"] = PatternResizeY

    def update_menu_colors(self):
        """Set info text color"""
        #Initialize color to WHITE
        self._change_box_info_text("info1", "rndcolor", WHITE, "self.m_lInfo")
        self._change_box_info_text("info2", "rndcolor", WHITE, "self.m_lInfo")
        self._change_box_info_text("info3", "rndcolor", WHITE, "self.m_lInfo")
        self._change_box_info_text("line1", "rndcolor", WHITE, "self.m_lInfo")
        self._change_box_info_text("line2", "rndcolor", WHITE, "self.m_lInfo")
        self._change_box_info_text("line3", "rndcolor", WHITE, "self.m_lInfo")

        #Set custom color per option
        if self.m_iCurrent == 0:
            pass
        elif self.m_iCurrent == 1:
            if abs(self.m_dConfigFile["width"]) == self.m_iMaxOffSetX:
                self._change_box_info_text("info3",
                                           "rndcolor", RED, "self.m_lInfo")
        elif self.m_iCurrent == 2:
            if self.m_sEnv == "system50" or self.m_sEnv == "system60":
                if abs(self.m_dConfigFile["height"]) == self.m_iMaxOffSetY:
                    self._change_box_info_text("info3",
                                               "rndcolor", RED, "self.m_lInfo")
            #RED info: vertical size locked
            elif self.m_sEnv == "test50" or self.m_sEnv == "test60":
                self._change_box_info_text("line1",
                                           "rndcolor", RED, "self.m_lInfo")
                self._change_box_info_text("line2",
                                           "rndcolor", RED, "self.m_lInfo")
        elif self.m_iCurrent == 3:
            self._change_box_info_text("info3",
                                       "rndcolor", YELLOW, "self.m_lInfo")
            self._change_box_info_text("line2",
                                       "rndcolor", YELLOW, "self.m_lInfo")

        #Set always these colors
        if self.m_sEnv == "system50" or self.m_sEnv == "system60":
            if abs(self.m_dConfigFile["offsetX"]) == \
               abs(self.m_iMaxOffSetX - self.m_dConfigFile["width"]):
                self._change_box_info_text("info1",
                                           "rndcolor", RED, "self.m_lInfo")
            if abs(self.m_dConfigFile["offsetY"]) == \
               abs(self.m_iMaxOffSetY - self.m_dConfigFile["height"]):
                self._change_box_info_text("info2",
                                           "rndcolor", RED, "self.m_lInfo")
        elif self.m_sEnv == "test50" or self.m_sEnv == "test60":
            if abs(self.m_dConfigFile["offsetX"]) == \
               abs(self.m_iMaxOffSetX):
                self._change_box_info_text("info1",
                                           "rndcolor", RED, "self.m_lInfo")
            if abs(self.m_dConfigFile["offsetY"]) == abs(self.m_iMaxOffSetY):
                self._change_box_info_text("info2",
                                           "rndcolor", RED, "self.m_lInfo")

    def update_menu_text(self):
        """Set info lines in box per option"""
        if self.m_iCurrent == 0:
            self._change_box_info_text("info3", "text", "H:%s|V:%s" %
            (self.m_dConfigFile["width"], self.m_dConfigFile["height"]),
             "self.m_lInfo")
            self._change_box_info_text("line1", "text",
                                       "PRESS ANY DIRECTION", "self.m_lInfo")
            self._change_box_info_text("line2", "text",
                                       "TO CENTER THE SCREEN", "self.m_lInfo")
            self._change_box_info_text("line3", "text",
                                       "<Press any button to set>",
                                       "self.m_lInfo")
        elif self.m_iCurrent == 1:
            self._change_box_info_text("info3", "text", "Width:%s" %
                                       (self.m_dConfigFile["width"]),
                                        "self.m_lInfo")
            self._change_box_info_text("line1", "text",
                                       "PRESS LEFTH/RIGHT", "self.m_lInfo")
            self._change_box_info_text("line2", "text",
                                       "TO CHANGE HORIZONTAL WIDTH",
                                       "self.m_lInfo")
            self._change_box_info_text("line3", "text",
                                       "<Press any button to set>",
                                       "self.m_lInfo")
        elif self.m_iCurrent == 2:
            if self.m_sEnv == "system50" or self.m_sEnv == "system60":
                self._change_box_info_text("info3", "text", "Height:%s" %
                                          (self.m_dConfigFile["height"]),
                                           "self.m_lInfo")
                self._change_box_info_text("line1", "text",
                                           "PRESS UP/DOWN", "self.m_lInfo")
                self._change_box_info_text("line2", "text",
                                           "TO CHANGE VERTICAL HEIGHT",
                                           "self.m_lInfo")
                self._change_box_info_text("line3", "text",
                                           "<Press any button to set>",
                                           "self.m_lInfo")
            elif self.m_sEnv == "test50" or self.m_sEnv == "test60":
                self._change_box_info_text("info3", "text",
                                           "Blocked!", "self.m_lInfo")
                self._change_box_info_text("line1", "text",
                                           "FORCED VERTICAL SIZE",
                                           "self.m_lInfo")
                self._change_box_info_text("line2", "text",
                                           "ONLY PIXEL PERFECT!",
                                           "self.m_lInfo")
                self._change_box_info_text("line3", "text",
                                           "<Press any button to continue>",
                                           "self.m_lInfo")
        elif self.m_iCurrent == 3:
            if self.m_iCurrentSub == 0:
                self._change_box_info_text("line1", "text",
                                           ">TRY AGAIN", "self.m_lInfo")
                self._change_box_info_text("line2", "text",
                                           " QUIT TEST", "self.m_lInfo")
            elif self.m_iCurrentSub == 1:
                self._change_box_info_text("line1", "text",
                                           " TRY AGAIN", "self.m_lInfo")
                self._change_box_info_text("line2", "text",
                                           ">QUIT TEST", "self.m_lInfo")

            self._change_box_info_text("line3", "text",
                                       "<Select your option>", "self.m_lInfo")
            self._change_box_info_text("info3", "text",
                                       "   EXIT?", "self.m_lInfo")
        #Set always these options:
        self._change_box_info_text("info1", "text", "Offset X:%s" %
                                  (self.m_dConfigFile["offsetX"]),
                                   "self.m_lInfo")
        self._change_box_info_text("info2", "text", "Offset Y:%s" %
                                  (self.m_dConfigFile["offsetY"]),
                                   "self.m_lInfo")

    def _change_box_info_text(self, p_sLabel, p_sField, p_sData, p_lLibrary):
        for gopt in eval(p_lLibrary):
            if gopt["label"] == p_sLabel:
                gopt[p_sField] = p_sData

    def _generate_info(self, p_lIndex, p_lVar, p_lLibrary):
        #Generate complete library for info text and box from separated parts
        Info_Text_Temp = {}
        TXTLineTemp = {}
        found = False

        #Check in a row all labels (info1, info2 ... line2, line3)
        for lab in p_lIndex:
            #Check all involved separated libraries to complete each label
            for varname in p_lVar:
                vartemp = eval(varname)
                for txtline in vartemp:
                    TXTLineTemp = {}
                    #Prepare part of a label datas
                    for item in txtline:
                        if txtline[item] != None:
                            TXTLineTemp[item] = txtline[item]
                        #If same label of first step, datas will be taken
                        if txtline[item] == lab:
                            found = True
                    #If datas are for the same label append to temp variable
                    if found:
                        for option in TXTLineTemp:
                            Info_Text_Temp[option] = TXTLineTemp[option]
                        found = False
            eval(p_lLibrary).append(Info_Text_Temp)
            Info_Text_Temp = {}
