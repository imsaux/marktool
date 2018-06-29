# coding=utf-8

# 自动标定流程
# 1. 解析标定文件，按照车型在图片中的位置及高度占图片的比例进行分组 （analyzeCalibrationFile -> _frequency(_getKinds))
# 2. 标定当前车型，保存 (save)
# 3. 记录标定数据并计算各项偏移值
# 4. 获取同组车型 (get_current_group)
# 5. 遍历同组车型，同时更改标定文件中的数据 (calibration.carbody)

# 2.7.0.3
# 1. 支持对图片中的车轴信息进行操作
# 2. 支持对图片中的标定信息进行操作

import codecs
import datetime
from xml.etree import ElementTree as ET
import PIL.Image as pilImage
import PIL.ImageTk as pilImgTk
from tkinter.filedialog import *
import tkinter.ttk as ttk
import tkinter as tk
import ctypes
import re
import logging
import inspect
import json
import os
import copy

FEATURE_LIST = [
    "支持 操作图片中的车轴信息、标定信息",
    "支持 JSON",
    "支持 顶部图",
    "支持 走行部图片",
    "支持 侧面图"
]

class const:
    class Calibration:
        NONE_CALIBRATION = 0
        CAR_CALIBRATION = 1
        AXEL_OFFSET_CALIBRATION = 2
        RAIL_Y_CALIBRATION = 3
        AXEL_Y_CALIBRATION = 4
        OUTLINE_CALIBRATION = 5
        NEW_AXEL_CALIBRATION = 6

    CALIBRATION_MODE_FILE = 11
    CALIBRATION_MODE_PIC = 12

    CALC_SAVE_CALIBRATION = 41
    CALC_READ_CALIBRATION = 42
    CALC_SAVE_AUTO_CALIBRATION = 43


    if os.name == 'posix':
        KEY_CTRL = 37
        KEY_ESC = 9
    if os.name == 'nt':
        KEY_CTRL = 17
        KEY_ESC = 0

class util:
    @staticmethod
    def _gettime(_time=None, _type='socket'):
        """
        获取特定格式的日期时间字符串
        """
        t = None
        if _time is None:
            t = datetime.datetime.now()
        elif isinstance(_time, datetime.datetime):
            t = _time
        else:
            return None

        if _type == 'socket':
            return t.strftime("%Y-%m-%d %H:%M:%S")
        elif _type == 'file':
            return t.strftime("%Y%m%d")
        else:
            return None

class main():
    def __init__(self, _mainobj):
        # self.logger = self._getLogger()
        # self.logger.info('启动')
        self.win = _mainobj
        try:
            user32 = ctypes.windll.LoadLibrary('user32.dll')
            menu_height = user32.GetSystemMetrics(15)
            title_height = user32.GetSystemMetrics(4)
        except Exception as e:
            menu_height = 20
            title_height = 20
        self.win_size = (self.win.winfo_screenwidth(), self.win.winfo_screenheight()-menu_height-title_height-20)
        if os.name.upper() == 'NT':
            self.win.state('zoomed')
        self.data_init()
        self.ui_init()
        self.config()

    def _datetime_format(self, date=datetime.datetime.now(), mode=1):
        if mode == 1:
            return str(date.year) + '年' + str(date.month) + '月' + str(date.day) + '日'
        elif mode == 2:
            return date.strftime('%Y%m%d%H%M%S')
        elif mode == 3:
            return date.strftime('%m/%d/%Y')
        elif mode == 4:
            return str(date.year) + '年' + str(date.month) + '月' + str(date.day) + '日 ' + str(date.hour).zfill(2) + ':' + str(date.minute).zfill(2) + ':' + str(date.second).zfill(2)

    def _getLogger(self):
        logger = logging.getLogger('[biaoding]')

        this_file = inspect.getfile(inspect.currentframe())
        dirpath = os.path.abspath(os.path.dirname(this_file))
        if not os.path.exists(os.path.join(dirpath, 'log')):
            os.makedirs(os.path.join(dirpath, 'log'))
        handler = logging.FileHandler(os.path.join(dirpath, 'log', self._datetime_format(mode=2) + ".log"))

        formatter = logging.Formatter('%(asctime)s %(name)-12s [line:%(lineno)d] %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        return logger

    def data_init(self, init=True):
        if init:
            self.show_pics = list()
            self._calibration_dir = None
            self.currentPicIndex = 0
            self.currentPic = None
            self.currentPicInfo = list()
            self.current_actived_menu = None
            self.origin_img = None
            self.show_img = None
            self.showZoomRatio = 1
            self.group_imgs = dict()
            self.imgs_group = dict()
            self.picGroups = None
            self.calibrationFile = None
            self.auto_calibration_enable = True
            self.drawMode = const.Calibration.NONE_CALIBRATION
            self.showoffset = 0, 0
            self.drawObj = const.CALIBRATION_MODE_FILE
            self.open_dir = None
            self.dirname = None
            self.step_value = 0.0625  # 统计步长
            self.imgPosition = None
            self.calibrationHelper = None
            self.rail_y = 0
            self.outlines = [0, 0, 0]
            self.autoCalibrationParams = [0, 0, 1, 1]
            self.oldCalibrationInfo = list()
            self.groupByCalibration = dict()
            self.paint = {
                'CAR': [],
                'AXEL': [],   # 车轴
                'WHEEL': [],
                'RAIL': [],
                'OUTLINE': [],
                'POINT': [],
                'TEXT': [],
                'TEXT_COORDS': [],
                'IMG': [],
                'CONSULT': [],
                'PIC_CAR': [],
                'PIC_AXEL': [],
                'PIC_WHEEL': [],
                'PIC_RAIL': [],
                'PIC_OUTLINE': [],
                'PIC_NEW_AXEL': []

            }

            self.history = {
                'CAR': [],
                'AXEL': [],
                'WHEEL': [],
                'RAIL': [],
                'OUTLINE': [],
                'POINT': [],
                'TEXT': [],
                'TEXT_COORDS': [],
                'IMG': [],
                'CONSULT': [],
                'PIC_CAR': [],
                'PIC_AXEL': [],
                'PIC_WHEEL': [],
                'PIC_RAIL': [],
                'PIC_OUTLINE': [],
                'PIC_NEW_AXEL': []
            }
            self.source = {
                'G': [],
                'Z': [],
                'T': [],
            }
            self.searchByGroup = dict()
            self.coords_zoom = list()
            self.coords_full = list()
            self.CTRL = False
            self.isCalibrationFileReady = False
            self.FULL_SCREEN = False
            self.saved = list()
            self.current_pic_binary_data = None
            self.pic_calibration_value = []
            self.pic_wheel_value = []
            self.pic_origin_wheel_data = None
            self.pic_origin_calibration_data = None
            self.is_sartas = True
        else:
            self.clearAllCanvas()


    def remove_calibration(self):
        if self.pic_origin_calibration_data is not None:
            for k, v in self.pic_origin_calibration_data.items():
                self.current_pic_binary_data = self.current_pic_binary_data.replace(v.encode(), b"")
            self.save_pic_data()

    def remove_wheel(self):
        for l in self.pic_origin_wheel_data:
            self.current_pic_binary_data = self.current_pic_binary_data.replace(l.encode(), b"")
        self.save_pic_data()

    def check_data_type(self, _file_name):
        if '_ZL' in _file_name or '_ZR' in _file_name:
            self.source['Z'].append(_file_name)
        elif '_T' in _file_name:
            self.source['T'].append(_file_name)
        elif '_L' in _file_name or '_R' in _file_name:
            self.source['G'].append(_file_name)

    def ui_init(self):
        self.show_size = (self.win_size[0], self.win_size[1])

        self.canvas = tk.Canvas(self.win, bg='#C7EDCC', width=self.show_size[0], height=self.show_size[1]-60)
        self.canvas.place(x=0, y=0)

        self.rootMenu = tk.Menu(self.win)
        self.rootMenu.add_command(label='打开标定', command=self.openCalibrationFile)
        self.rootMenu.add_command(label='打开文件夹', command=self.openPictureFolder)


        operation_tool = tk.Menu(self.rootMenu, tearoff=0)
        pic_tool_menu = tk.Menu(operation_tool, tearoff=0)
        pic_tool_menu.add_command(label="清除车轴", command=self.remove_wheel)
        pic_tool_menu.add_command(label="清除标定", command=self.remove_calibration)
        pic_tool_menu.add_command(label="全部更新标定", command=self.check_all_null_data)
        operation_tool.add_cascade(label='图片操作', menu=pic_tool_menu)

        export_menu = tk.Menu(operation_tool, tearoff=0)
        export_menu.add_command(label="导出json", command=self.save2json)
        export_menu.add_command(label="导出config", command=self.save2config)
        operation_tool.add_cascade(label='导出', menu=export_menu)

        self.rootMenu.add_cascade(label='操作', menu=operation_tool)


        setting_menu = tk.Menu(self.rootMenu, tearoff=0)
        operate_obj_menu = tk.Menu(setting_menu, tearoff=0)
        self.operate_obj_menu_value = IntVar()
        self.operate_obj_menu_value.set(1)
        operate_obj_menu.add_radiobutton(label="图像", command=self.setCalibrationObjPic, variable=self.operate_obj_menu_value, value=2)
        operate_obj_menu.add_radiobutton(label="标定文件", command=self.setCalibrationObjFile, variable=self.operate_obj_menu_value, value=1)
        setting_menu.add_cascade(label='数据源', menu=operate_obj_menu)

        system_type_menu = tk.Menu(setting_menu, tearoff=0)
        self.system_type_menu_value = IntVar()
        self.system_type_menu_value.set(2)
        system_type_menu.add_radiobutton(label="接发列车系统", command=self.setSystemToSartas, variable=self.system_type_menu_value, value=2)
        system_type_menu.add_radiobutton(label="智能货检系统", command=self.setSystemToZhineng, variable=self.system_type_menu_value, value=1)
        setting_menu.add_cascade(label='目标系统', menu=system_type_menu)

        self.rootMenu.add_cascade(label='设置', menu=setting_menu)




        test_menu = tk.Menu(self.rootMenu, tearoff=0)
        test_menu.add_command(label='鼠标滚轮-向下：缩小')
        test_menu.add_command(label='鼠标滚轮-向上：放大')
        test_menu.add_command(label='鼠标右键：拖动')
        test_menu.add_command(label='鼠标左键：画点')
        test_menu.add_command(label='回退键（backspace）：删除最近一次绘制的车轴')
        self.rootMenu.add_cascade(label='帮助', menu=test_menu)

        about_menu = tk.Menu(self.rootMenu, tearoff=0)
        about_menu.add_command(label='开发标识：r20180629.1051')
        for fl in FEATURE_LIST:
            about_menu.add_command(label=fl)
        self.rootMenu.add_cascade(label='关于', menu=about_menu)

        self.win.config(menu=self.rootMenu)

        # Button(self.win, text="导出json", width=10, relief=GROOVE, bg="yellow", command=self.save2json).place(x=self.show_size[0]/2-415, y=self.show_size[1]-55)
        # Button(self.win, text="导出config", width=10, relief=GROOVE, bg="yellow", command=self.save2config).place(x=self.show_size[0]/2-295, y=self.show_size[1]-55)
        Button(self.win, text="上一张", width=10, relief=GROOVE, bg="yellow", command=self.showLastPic).place(x=self.show_size[0]/2-175, y=self.show_size[1]-55)
        Button(self.win, text="保  存", width=10, relief=GROOVE, bg="yellow", command=self.save_data).place(x=self.show_size[0]/2-50, y=self.show_size[1]-55)
        Button(self.win, text="下一张", width=10, relief=GROOVE, bg="yellow", command=self.showNextPic).place(x=self.show_size[0]/2+70, y=self.show_size[1]-55)
        Label(self.win, text="版本：2.7.0.4").place(x=0, y=self.show_size[1]-50)

        self.btn_calibration_type = Button(self.win, text="标定类型", width=10, relief=GROOVE, bg="yellow", command=self.pop_calibration_type)
        self.btn_calibration_type.place(x=self.show_size[0] / 2 + 195, y=self.show_size[1] - 55)

        # self.btn_calibration_obj = Button(self.win, text="  标   定 ", width=10, relief=GROOVE, bg="yellow", command=self.pop_calibration_obj)
        # self.btn_calibration_obj.place(x=self.show_size[0] / 2 + 315, y=self.show_size[1] - 55)


        self.setEventBinding()

    def create_group_menu(self):
        dct = self.imgs_group[self.group_imgs[self.currentPic]][0]
        carriage_menu = tk.Menu(self.rootMenu, tearoff=0)
        self.rootMenu.add_cascade(label='智能分组', menu=carriage_menu)

    def _zoom_to_point(self, x, y):
        if len(self.paint['IMG']) > 0:
            _bbox = self.canvas.bbox(self.paint['IMG'][0])
            pic_x = (x - _bbox[0]) / self.showZoomRatio
            pic_y = (y - _bbox[1]) / self.showZoomRatio
            move_x = pic_x - round(self.show_size[0]* (x / self.show_size[0]))
            move_y = pic_y - round(self.show_size[1]* (y / self.show_size[1]))
            return move_x, move_y
        else:
            return 0,0

    def _point_to_full(self):
        if len(self.coords_zoom) > 0:
            _bbox_img = self.canvas.bbox(self.paint['IMG'][0])
            tmp = [(round((p[0]-_bbox_img[0])/self.showZoomRatio), round((p[1]-_bbox_img[1])/self.showZoomRatio)) for p in self.coords_zoom]
            self.coords_full.clear()
            self.coords_full = tmp


    def _point_to_zoom(self):
        if len(self.coords_full) > 0:
            tmp = [(round(p[0]*self.showZoomRatio), round(p[1]*self.showZoomRatio)) for p in self.coords_zoom]
            self.coords_zoom.clear()
            self.coords_zoom = tmp

    def full_to_zoom(self, l_data):
        return [d*self.showZoomRatio for d in l_data]

    def zoom_to_full(self, l_data):
        return [round(d/self.showZoomRatio) for d in l_data]

    def eCanvasMouseWheel(self, event):
        if os.name == 'nt' and event.delta > 0 and not self.FULL_SCREEN:
            self.FULL_SCREEN = True
            _move = self._zoom_to_point(event.x, event.y)
            self.show()
            self.bbox_move(-_move[0], -_move[1])
            self.display_unsaved_shape()

        elif os.name == 'nt' and event.delta < 0 and self.FULL_SCREEN:
            self.FULL_SCREEN = False
            self.show()
            # self.bbox_move(-_move[0], -_move[1])
            self.display_unsaved_shape()
        if os.name == 'posix' and event.num == 5 and self.FULL_SCREEN:
            self.FULL_SCREEN = False
            self.show()
            # self.bbox_move(-_move[0], -_move[1])
            self.display_unsaved_shape()
        elif os.name == 'posix' and event.num == 4 and not self.FULL_SCREEN:
            self.FULL_SCREEN = True
            _move = self._zoom_to_point(event.x, event.y)
            self.show()
            self.bbox_move(-_move[0], -_move[1])
            self.display_unsaved_shape()

    def setEventBinding(self):
        self.canvas.bind('<Motion>', self.eCanvasMotion)
        self.canvas.bind('<Button-1>', self.eCanvasButton_1)
        self.canvas.bind('<ButtonRelease-1>', self.eCanvasButton_1_release)
        if os.name == 'nt':
            self.canvas.bind('<MouseWheel>', self.eCanvasMouseWheel)
        elif os.name == 'posix':
            self.canvas.bind('<Button-4>', self.eCanvasMouseWheel)
            self.canvas.bind('<Button-5>', self.eCanvasMouseWheel)
        self.canvas.bind('<B3-Motion>', self.drag)
        self.win.bind('<Key>', self.eKeyChanged)

    def eKeyChanged(self, event):
        if event.keycode == const.KEY_CTRL and self.CTRL:
            self.CTRL = False
        elif event.keycode == const.KEY_CTRL and not self.CTRL:
            self.CTRL = True
        
        # 支持开启/关闭 自动标定功能
        # True： 改动将影响同组车型
        # False： 改动不影响同组车型
        if event.keycode == 58 and self.auto_calibration_enable:
            self.auto_calibration_enable = False
        elif event.keycode == 58 and not self.auto_calibration_enable:
            self.auto_calibration_enable = True

        if event.keycode == 22 and os.name == 'posix' or event.keycode == 8 and os.name == 'nt':
            if len(self.paint['PIC_NEW_AXEL']) > 0:
                self.canvas.delete(self.paint['PIC_NEW_AXEL'][-1])
                self.paint['PIC_NEW_AXEL'].remove(self.paint['PIC_NEW_AXEL'][-1])
        #todo 待加入删除后加入的轴信息

    def drag(self, event):
        # print('%s %s -> %s' % (sys.platform, os.name, event.state))

        # if os.name == 'nt' and event.state != 1032:
        #     return
        # if os.name == 'posix' and event.state != 1024:
        #     return

        if not self.FULL_SCREEN:
            zoom_offset_x = event.x - self.zoom_last_x
            zoom_offset_y = event.y - self.zoom_last_y
            full_offset_x = round(event.x/self.showZoomRatio) - self.full_last_x
            full_offset_y = round(event.y/self.showZoomRatio) - self.full_last_y
        else:
            zoom_offset_x = round(event.x*self.showZoomRatio) - self.full_last_x
            zoom_offset_y = round(event.y*self.showZoomRatio) - self.full_last_y
            full_offset_x = event.x - self.full_last_x
            full_offset_y = event.y - self.full_last_y
        for obj in self.canvas.find_all():
            if not self.FULL_SCREEN:
                self.bbox_move(zoom_offset_x, zoom_offset_y, specify=obj)
            else:
                self.bbox_move(full_offset_x, full_offset_y, specify=obj)
        if not self.FULL_SCREEN:
            self.zoom_last_x = event.x
            self.zoom_last_y = event.y
            self.full_last_x = round(event.x / self.showZoomRatio)
            self.full_last_y = round(event.y / self.showZoomRatio)
        else:
            self.zoom_last_x = round(event.x * self.showZoomRatio)
            self.zoom_last_y = round(event.y * self.showZoomRatio)
            self.full_last_x = event.x
            self.full_last_y = event.y

    def setCurrnetPic(self, filename):
        if os.path.exists(filename):
            self.currentPic = filename
            self.currentPicInfo = self.getPicInfo(filename)
            self.dirname = os.path.dirname(filename)
            self.load_pic_binary()
            self.check_null_data(self.currentPic)

    def load_pic_binary(self):
        self.current_pic_binary_data = self.read_pic_data()
        self._getpicwheelinfo()
        self.get_pic_calibration_data(self.current_pic_binary_data)
        self.get_pic_calibration_value_data()

    def calc(self, mode, _bbox=None):
        if mode == const.CALC_SAVE_CALIBRATION:
            _img = self.canvas.bbox(self.paint['IMG'][0])  # 图片位置
            bbox_car = self.canvas.bbox(self.paint['CAR'][0] if self.drawObj == const.CALIBRATION_MODE_FILE else self.paint['PIC_CAR'][0])
            if not self.FULL_SCREEN:
                x = round((bbox_car[0] - _img[0]) / self.showZoomRatio)
                y = round((bbox_car[1] - _img[1]) / self.showZoomRatio)
                w = round((bbox_car[2] - _img[0]) / self.showZoomRatio) - x
                h = round((bbox_car[3] - _img[1]) / self.showZoomRatio) - y
            else:
                x = bbox_car[0] - _img[0]
                y = bbox_car[1] - _img[1]
                w = bbox_car[2] - _img[0] - x
                h = bbox_car[3] - _img[1] - y

            return x, y, w, h
        elif mode == const.CALC_READ_CALIBRATION:
            _img = self.canvas.bbox(self.paint['IMG'][0])  # 图片位置
            try:
                if _bbox is None:
                    x1 = int(self.oldCalibrationInfo['X_carbody'] * self.showZoomRatio) + _img[0]
                    y1 = int(self.oldCalibrationInfo['Y_carbody'] * self.showZoomRatio) + _img[1]
                    x2 = int((self.oldCalibrationInfo['width_carbody'] + self.oldCalibrationInfo[
                        'X_carbody']) * self.showZoomRatio) + _img[0]
                    y2 = int((self.oldCalibrationInfo['height_carbody'] + self.oldCalibrationInfo[
                        'Y_carbody']) * self.showZoomRatio) + _img[1]
                else:
                    x1 = int(_bbox[0] * self.showZoomRatio) + _img[0]
                    y1 = int(_bbox[1] * self.showZoomRatio) + _img[1]
                    x2 = int((_bbox[2]) * self.showZoomRatio) + _img[0]
                    y2 = int((_bbox[3]) * self.showZoomRatio) + _img[1]
                return x1, y1, x2, y2
            except:
                return 0, 0, 0, 0
        elif mode == const.CALC_SAVE_AUTO_CALIBRATION:
            if _bbox is not None and list(self.oldCalibrationInfo.values()).count(0) != 4:
                self.autoCalibrationParams[0] = _bbox[0] - self.oldCalibrationInfo['X_carbody']
                self.autoCalibrationParams[1] = _bbox[1] - self.oldCalibrationInfo['Y_carbody']
                self.autoCalibrationParams[2] = _bbox[2] / self.oldCalibrationInfo['width_carbody']
                self.autoCalibrationParams[3] = _bbox[3] / self.oldCalibrationInfo['height_carbody']
            else:
                self.autoCalibrationParams[3] = [0, 0, 1, 1]

    def _get_group_kinds(self):
        return list(self.imgs_group[self.group_imgs[self.currentPic]][0].keys())

    def save2json(self):
        self.save_data()
        self.calibrationHelper.export2JSON()

    def is_unsave(self, item):
        if item == const.Calibration.CAR_CALIBRATION:
            if self.drawObj == const.CALIBRATION_MODE_FILE:
                return self.currentPic in self.source['G'] and len(self.paint['CAR']) > 0 and self.paint['CAR'][0] not in self.history['CAR']
            else:
                return self.currentPic in self.source['G'] and len(self.paint['PIC_CAR']) > 0 and self.paint['PIC_CAR'][0] not in self.history['PIC_CAR']
        else:
            _Z = True if self.currentPic in self.source['Z'] else False
            if item == const.Calibration.RAIL_Y_CALIBRATION:
                if self.drawObj == const.CALIBRATION_MODE_FILE:
                    return self.currentPic not in self.source['T'] and len(self.paint['RAIL']) > 0 and self.paint['RAIL'][0] not in self.history['RAIL']
                else:
                    return self.currentPic not in self.source['T'] and len(self.paint['PIC_RAIL']) > 0 and self.paint['PIC_RAIL'][0] not in self.history['PIC_RAIL']
            elif item == const.Calibration.AXEL_OFFSET_CALIBRATION:
                if self.drawObj == const.CALIBRATION_MODE_FILE:
                    return self.currentPic not in self.source['T'] and len(self.paint['AXEL']) > 0 and self.paint['AXEL'][0] not in self.history['AXEL']
                else:
                    return self.currentPic not in self.source['T'] and len(self.paint['PIC_AXEL']) > 0 and self.paint['PIC_AXEL'][0] not in self.history['PIC_AXEL']
            elif item == const.Calibration.AXEL_Y_CALIBRATION:
                if self.drawObj == const.CALIBRATION_MODE_FILE:
                    return self.currentPic not in self.source['T'] and len(self.paint['WHEEL']) > 0 and self.paint['WHEEL'][0] not in self.history['WHEEL']
                else:
                    return self.currentPic not in self.source['T'] and len(self.paint['PIC_WHEEL']) > 0 and self.paint['PIC_WHEEL'][0] not in self.history['PIC_WHEEL']
            elif item == const.Calibration.NEW_AXEL_CALIBRATION:
                if self.drawObj == const.CALIBRATION_MODE_PIC:
                    return self.currentPic not in self.source['T'] and len(self.paint['PIC_NEW_AXEL']) > 0 and self.paint['PIC_NEW_AXEL'][0] not in self.history['PIC_NEW_AXEL']
            elif item == const.Calibration.OUTLINE_CALIBRATION:
                if self.drawObj == const.CALIBRATION_MODE_FILE:
                    return self.drawMode == const.Calibration.OUTLINE_CALIBRATION and len(self.paint['OUTLINE']) > 0 and self.paint['OUTLINE'][0] not in self.history['OUTLINE']
                else:
                    return self.drawMode == const.Calibration.OUTLINE_CALIBRATION and len(self.paint['PIC_OUTLINE']) > 0 and self.paint['PIC_OUTLINE'][0] not in self.history['PIC_OUTLINE']

    def save_data(self):
        if self.drawObj == const.CALIBRATION_MODE_FILE:
            if self.is_unsave(const.Calibration.CAR_CALIBRATION):
                _group_kinds = self.get_current_group()
                _new_bbox = self.calc(mode=const.CALC_SAVE_CALIBRATION)
                ret = dict()
                ret['X_carbody'] = _new_bbox[0]
                ret['Y_carbody'] = _new_bbox[1]
                ret['width_carbody'] = _new_bbox[2]
                ret['height_carbody'] = _new_bbox[3]

                self.calibrationHelper.carbody(
                    self.currentPicInfo[0],
                    self.currentPicInfo[1],
                    self.currentPicInfo[2],
                    _new=ret)
                self.saved.append('%s_%s_%s' % (self.currentPicInfo[1], self.currentPicInfo[2], self.currentPicInfo[0]))
                if self.oldCalibrationInfo is not None and list(self.oldCalibrationInfo.values()).count(-1) != 4 and self.auto_calibration_enable:
                    self.calc(mode=const.CALC_SAVE_AUTO_CALIBRATION, _bbox=_new_bbox)
                    _lst = [k.split('_')[2] for k in list(set(_group_kinds) & set(self.saved) ^ set(_group_kinds))]
                    if len(_lst) > 0:
                        self.calibrationHelper.oneclick(_lst, self.autoCalibrationParams, self.currentPicInfo[1], self.currentPicInfo[2])
                    self.autoCalibrationParams = [0, 0, 1, 1]
                    self.analyzeCalibrationFile()
            _Z = True if self.currentPic in self.source['Z'] else False
            if self.is_unsave(const.Calibration.AXEL_OFFSET_CALIBRATION):
                self.calibrationHelper.axel(
                    self.currentPicInfo[1],
                    self.currentPicInfo[2],
                    _new=self.axel_x_offset,
                    Z=_Z)
            if self.is_unsave(const.Calibration.AXEL_Y_CALIBRATION):
                self.calibrationHelper.wheel(
                    self.currentPicInfo[1],
                    self.currentPicInfo[2],
                    _new=self.axel_y,
                    Z=_Z)
            if self.is_unsave(const.Calibration.RAIL_Y_CALIBRATION):
                self.calibrationHelper.rail(
                    self.currentPicInfo[1],
                    self.currentPicInfo[2],
                    _new=self.rail_y,
                    Z=_Z)
            if self.is_unsave(const.Calibration.OUTLINE_CALIBRATION):
                self.calibrationHelper.outline(
                    self.currentPicInfo[1],
                    self.currentPicInfo[0],
                    _new=self.outlines)
            self.display(pic=self.currentPic)
            self.calibrationHelper.export()
        elif self.drawObj == const.CALIBRATION_MODE_PIC:
            dt_calibration_save = dict()
            if self.is_unsave(const.Calibration.CAR_CALIBRATION):
                _new_bbox = self.calc(mode=const.CALC_SAVE_CALIBRATION)
                dt_calibration_save["Cleft"] = _new_bbox[0]
                dt_calibration_save["Ctop"] = _new_bbox[1]
                dt_calibration_save["Cright"] = _new_bbox[0] + _new_bbox[2]
                dt_calibration_save["Cbottom"] = _new_bbox[1] + _new_bbox[3]
            if self.is_unsave(const.Calibration.AXEL_OFFSET_CALIBRATION):
                dt_calibration_save["Cwheeloffset"] = self.axel_x_offset
            if self.is_unsave(const.Calibration. AXEL_Y_CALIBRATION):
                dt_calibration_save["Cwheelcenter"] = self.axel_y
            if self.is_unsave(const.Calibration.RAIL_Y_CALIBRATION):
                dt_calibration_save["Crail"] = self.rail_y
            if self.is_unsave(const.Calibration.OUTLINE_CALIBRATION):
                _new = copy.deepcopy(self.outlines)
                if int(_new[0]) > int(_new[1]):
                    _new[0], _new[1] = _new[1], _new[0]
                _new[1] -= _new[0]

                dt_calibration_save["Ctop"] = _new[0]
                dt_calibration_save["Cbottom"] = _new[1]

            if self.is_unsave(const.Calibration.NEW_AXEL_CALIBRATION):
                lt_new_wheel = []
                for pl in self.paint["PIC_NEW_AXEL"]:
                    lt_new_wheel.append(round(self.canvas.bbox(pl)[0]/self.showZoomRatio))
                dt_calibration_save["Cwheeloffset"] = 0
                self.generate_pic_wheel_data(lt_new_wheel)


            self.generate_pic_calibration_data(dt_calibration_save)
            self.save_pic_data()


    def save2config(self):
        self.save_data()
        self.calibrationHelper.export2XML()

    def config(self, _new_file=None, _new_path=None, _new_index=None):
        if os.path.exists('biaoding.json'):
            if [_new_file, _new_path, _new_index].count(None) == 3:
                with open('biaoding.json', 'r') as _json:
                    v = json.load(_json)
                    self._file = v['file']
                    self._dir = v['path']
                    self._index = v['index']
            else:
                with open('biaoding.json', 'w') as _json:
                    v = dict()
                    v['file'] = _new_file if _new_file is not None else self._file
                    v['path'] = _new_path if _new_path is not None else self._dir
                    v['index'] = _new_index if _new_index is not None else self._index
                    json.dump(v, _json)
        else:
            v = {'file':'', 'path':'', 'index':0}
            with open('biaoding.json', 'w') as _json:
                json.dump(v, _json)
            self._file = v['file']
            self._dir = v['path']
            self._index = v['index']

    def _load_pics(self, dir):
        self.source['G'] = []
        self.source['T'] = []
        self.source['Z'] = []
        self.show_pics = []
        self.currentPicIndex = 0
        if dir != '' and os.path.exists(dir):
            for root, dirs, files in os.walk(dir, topdown=False):
                for f in files:
                    if os.path.splitext(f)[1].upper() == '.JPG':
                        _name = str(f).split('_')
                        if len(_name) != 5:
                            continue
                        # 2018-2-6 修改bug #623
                        if _name[0].isprintable() and \
                                re.match(r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$", _name[1]) and \
                            _name[2].isdigit() and \
                                len(_name[2]) == 14 and \
                                (_name[3][0] in ('L', 'R', 'T') or _name[3][:2] in ('ZL', 'ZR')):
                            self.check_data_type(os.path.join(root, f))

    def openPictureFolder(self):
        self.drawMode = const.Calibration.NONE_CALIBRATION
        self.config()

        try:
            dirpath = askdirectory(initialdir=self._dir, title='请选择图片文件夹')
        except:
            dirpath = askdirectory(title='请选择图片文件夹')
        if isinstance(dirpath, str) and os.path.exists(dirpath):
            self.config(_new_path=dirpath)
            self._load_pics(dirpath)
            if self.calibrationHelper is not None:
                self.display()
            else:
                self.setCalibrationObjPic()

    def display(self, pic=None):
        if self.calibrationHelper is None and self.drawObj != const.CALIBRATION_MODE_PIC:
            return
        if len(self.show_pics) == 0:
            if len(self.source['G']) > 0:
                self.show_pics.extend(self.source['G'])
            if len(self.source['Z']) > 0:
                self.show_pics.extend(self.source['Z'])
            if len(self.source['T']) > 0:
                self.show_pics.extend(self.source['T'])
        if len(self.show_pics) > 0:
            if pic is None:
                if 0 <= self.currentPicIndex <=len(self.show_pics) - 1:
                    self.setCurrnetPic(self.show_pics[self.currentPicIndex])
                else:
                    self.currentPicIndex = 0
                    self.setCurrnetPic(self.show_pics[self.currentPicIndex])
            else:
                self.setCurrnetPic(pic)
            self.show()
            self.update_title()

    def openCalibrationFile(self):
        self.isCalibrationFileReady = False
        self.config()
        try:
            _file_path = askopenfilename(initialdir=os.path.dirname(self._file), title='请选择标定文件')
        except:
            _file_path = askopenfilename(title='请选择标定文件')
        if len(_file_path) > 0 and os.path.exists(_file_path):
            self.config(_new_file=_file_path)
            if os.path.splitext(_file_path)[1] == '.config':
                self.calibrationHelper = json_handle()
                self.calibrationHelper.fromXML(_file_path)
            if os.path.splitext(_file_path)[1] == '.json':
                self.calibrationHelper = json_handle(_file_path)
            self.analyzeCalibrationFile()
            if self.calibrationHelper is not None:
                self.display()
        else:
            if self.calibrationHelper is not None:
                self.isCalibrationFileReady = True

    def get_current_group(self):
        _picInfo = self.getPicInfo(self.currentPic)
        _group_key = '%s_%s' % (str(_picInfo[1]), _picInfo[2])
        _algorGroup = self.algor_y_h(str(_picInfo[1]), str(_picInfo[2]), [_picInfo[0]])
        if _algorGroup[list(_algorGroup.keys())[0]][0][1] is not None:
            _key = self._getDictKey(
                list(_algorGroup.keys())[0],
                _algorGroup[list(_algorGroup.keys())[0]][0][1])
            try:
                _kinds_group =['%s_%s' % (_group_key, x) for x in self.groupByCalibration[_group_key][_key]]
            except KeyError:
                _kinds_group = []
            return _kinds_group
        else:
            return []

    def _getpicwheelinfo(self):
        self.pic_wheel_value = self.get_pic_wheel_data(self.current_pic_binary_data)

    def read_pic_data(self):
        with open(self.currentPic, 'rb') as fr:
            data = fr.read()
        return data

    def get_pic_wheel_data(self, b_data):
        # 获取图片车轮二进制数据
        s_wheel = "(\<Wheel\d{1,2}\s+\=\s+\-?\d+\>)+"
        s_wheel_value = "(\-?\d+)"
        try:
            l_wheels = [x for x in re.split(s_wheel, str(b_data)) if "Wheel" in x]
            self.pic_origin_wheel_data = l_wheels
            tmp = [re.split(s_wheel_value, y)[3] for y in l_wheels]
            l_wheels_value = [int(x) for x in tmp if x != "-1"]
            return l_wheels_value
        except:
            return None


    def check_all_null_data(self):
        for f in self.show_pics:
            self.setCurrnetPic(f)
        self.setCurrnetPic(self.show_pics[self.currentPicIndex])


    def check_null_data(self, file):
        with open(file, "ab") as fa:
            if self.pic_calibration_value is None and self.calibrationHelper is not None:
                xywh = self.calibrationHelper.carbody(self.currentPicInfo[0], self.currentPicInfo[1], self.currentPicInfo[2])
                if xywh is None:
                    xywh = dict()
                    xywh["X_carbody"] = 0
                    xywh["Y_carbody"] = 0
                    xywh["width_carbody"] = 0
                    xywh["height_carbody"] = 0
                if self.currentPic in self.source["T"]:
                    Cleft = "<Cleft = %s> " % (str(xywh["X_carbody"]))
                    Ctop = "<Ctop = %s> " % (str(xywh["Y_carbody"]))
                    Cright = "<Cright = %s> " % (str(xywh["X_carbody"]))
                    Cbottom = "<Cbottom = %s> " % (str(xywh["height_carbody"]))
                else:
                    Cleft = "<Cleft = %s> " % (str(xywh["X_carbody"]))
                    Ctop = "<Ctop = %s> " % (str(xywh["Y_carbody"]))
                    Cright = "<Cright = %s> " % (str(xywh["X_carbody"]+xywh["width_carbody"]))
                    Cbottom = "<Cbottom = %s> " % (str(xywh["Y_carbody"]+xywh["height_carbody"]))
                fa.write(Cleft.encode())
                fa.write(Ctop.encode())
                fa.write(Cright.encode())
                fa.write(Cbottom.encode())

                _side = self.currentPicInfo[2]
                _line = str(self.currentPicInfo[1])
                _Z = True if self.currentPic in self.source['Z'] else False
                try:
                    _offset = int(self.calibrationHelper.axel(_line, _side, Z=_Z))
                except:
                    _offset = 0
                try:
                    _wheel = int(self.calibrationHelper.wheel(_line, _side, Z=_Z))
                except:
                    _wheel = 0
                try:
                    _raily = int(self.calibrationHelper.rail(_line, _side, Z=_Z))
                except:
                    _raily = 0
                Cwheelcenter = "<Cwheelcenter = %s> " % (str(_wheel))
                Cwheeloffset = "<Cwheeloffset = %s> " % (str(_offset))
                Crail = "<Crail = %s> " % (str(_raily))
                fa.write(Cwheelcenter.encode())
                fa.write(Cwheeloffset.encode())
                fa.write(Crail.encode())
        self.load_pic_binary()


    def get_pic_calibration_data(self, b_data):
        # 获取图片标定二进制数据

        dt_calibration_regex = {
            "Cwheelcenter": "\<Cwheelcenter\s\=\s\-?\d+\>",
            "Cwheeloffset": "\<Cwheeloffset\s\=\s\-?\d+\>",
            "Ctop": "\<Ctop\s\=\s\-?\d+\>",
            "Cbottom": "\<Cbottom\s\=\s\-?\d+\>",
            "Cleft": "\<Cleft\s\=\s\-?\d+\>",
            "Cright": "\<Cright\s\=\s\-?\d+\>",
            "Crail": "\<Crail\s\=\s\-?\d+\>"
        }
        try:
            self.pic_origin_calibration_data = dict()
            for k, v in dt_calibration_regex.items():
                try:
                    self.pic_origin_calibration_data[k] = re.search(v, str(b_data)).group()
                except Exception as e:
                    pass
        except:
            self.pic_origin_calibration_data = None

    def get_pic_calibration_value_data(self):
        # 从二进制中获取十进制数据
        if self.pic_origin_calibration_data is None:
            self.pic_calibration_value = None
        else:
            dt_calibration_value_regex = "(\-?\d+)"
            calibration_value_data = {k: int(re.search(dt_calibration_value_regex, v).group()) for k, v in self.pic_origin_calibration_data.items()}
            if self.currentPic in self.source["T"]:
                self.pic_calibration_value = [
                    calibration_value_data["Cleft"] if "Cleft" in calibration_value_data.keys() else 0,
                    calibration_value_data["Ctop"] if "Ctop" in calibration_value_data.keys() else 0,
                    calibration_value_data["Cright"] if "Cright" in calibration_value_data.keys() else 0,
                    calibration_value_data["Cbottom"] if "Cbottom" in calibration_value_data.keys() else 0,
                    calibration_value_data["Cwheelcenter"] if "Cwheelcenter" in calibration_value_data.keys() else 0,
                    calibration_value_data["Cwheeloffset"] if "Cwheeloffset" in calibration_value_data.keys() else 0,
                    calibration_value_data["Crail"] if "Crail" in calibration_value_data.keys() else 0
                ]
            else:
                self.pic_calibration_value = [
                    calibration_value_data["Cleft"] if "Cleft" in calibration_value_data.keys() else 0,
                    calibration_value_data["Ctop"] if "Ctop" in calibration_value_data.keys() else 0,
                    calibration_value_data["Cright"] if "Cright" in calibration_value_data.keys() else 0 - calibration_value_data["Cleft"] if "Cleft" in calibration_value_data.keys() else 0,
                    calibration_value_data["Cbottom"] if "Cbottom" in calibration_value_data.keys() else 0 - calibration_value_data["Ctop"] if "Ctop" in calibration_value_data.keys() else 0,
                    calibration_value_data["Cwheelcenter"] if "Cwheelcenter" in calibration_value_data.keys() else 0,
                    calibration_value_data["Cwheeloffset"] if "Cwheeloffset" in calibration_value_data.keys() else 0,
                    calibration_value_data["Crail"] if "Crail" in calibration_value_data.keys() else 0
                ]

    def generate_pic_wheel_data(self, lt_new_value):
        tmp = "<Wheel%s = %s> "
        s_wheel_data = ""
        index = 1
        lt_new_value.sort()
        for x in lt_new_value:
            s_wheel_data += tmp % (str(index), x)
            index += 1
        self.current_pic_binary_data += s_wheel_data.encode()


    def generate_pic_calibration_data(self, dt_new_value):
        # 生成二进制标定修改数据
        dt_calibration_str = {
            "Cwheelcenter": "<Cwheelcenter = %s>",
            "Cwheeloffset": "<Cwheeloffset = %s>",
            "Ctop": "<Ctop = %s>",
            "Cbottom": "<Cbottom = %s>",
            "Cleft": "<Cleft = %s>",
            "Cright": "<Cright = %s>",
            "Crail": "<Crail = %s>",
        }
        if self.pic_origin_calibration_data is not None:
            r_old = {k: v for k, v in self.pic_origin_calibration_data.items()}
            r_new = {k: dt_calibration_str[k] % (v,) for k, v in dt_new_value.items()}
            for k, v in r_new.items():
                try:
                    self.current_pic_binary_data = self.current_pic_binary_data.replace(r_old[k].encode(), v.encode())
                except Exception as e:
                    self.current_pic_binary_data += r_new[k].encode()
        else:
            r_new = {k: dt_calibration_str[k] % (v,) for k, v in dt_new_value.items()}
            for k, v in r_new.items():
                self.current_pic_binary_data += v.encode()

    def save_pic_data(self):
        with open(self.currentPic, 'wb') as fw:
            fw.write(self.current_pic_binary_data)
        self.load_pic_binary()
        self.show()

    def getPicInfo(self, pic):
        try:
            _lst = os.path.basename(pic).split('_')
            _kind = _lst[0]
            _line = str(int(_lst[1].split('.')[3]))
            if self.is_sartas:
                _line = str(int(_line) - 1)
            if '#' in _lst[0]:
                _kind = _lst[0].replace('#', '*')
            if _lst[3][0] == 'Z':
                _side = _lst[3][1]
            else:
                _side = _lst[3][0]
        except:
            _kind = None
            _line = None
            _side = None
        finally:
            return _kind, _line, _side
    
    def clearAllCanvas(self):
        for key in self.paint.keys():
            self.cleanCanvasByType(self.paint[key], self.canvas)

    def show(self):
        self.clearAllCanvas()
        if self.FULL_SCREEN:
            self.displayImage2()
        else:
            self.displayImage()

        if self.currentPic in self.source['T']:
            if self.drawObj == const.CALIBRATION_MODE_FILE:
                self.displayOutline()
            elif self.drawObj == const.CALIBRATION_MODE_PIC:
                self.displayPicOutline()
        else:
            if self.drawObj is not None:
                if self.drawObj == const.CALIBRATION_MODE_FILE:
                    if self.currentPic in self.source['G']:
                        self.displayCarCalibration()
                    self.displayAxelCalibration()
                    self.displayWheelCalibration()
                    self.displayRailCalibration()
                elif self.drawObj == const.CALIBRATION_MODE_PIC:
                    if self.currentPic in self.source['G']:
                        self.displayPicCarCalibration()
                    self.displayPicAxelCalibration()
                    self.displayPicWheelCalibration()
                    self.displayPicRailCalibration()

    def display_unsaved_shape(self):
        _bbox = self.canvas.bbox(self.paint['IMG'][0])
        if self.drawObj == const.CALIBRATION_MODE_FILE:
            if self.drawMode == const.Calibration.CAR_CALIBRATION:
                self.cleanCanvasByType(self.paint['CAR'], self.canvas)
                self.cleanCanvasByType(self.paint['POINT'], self.canvas)
                if not self.FULL_SCREEN:
                    if len(self.coords_zoom) >= 2:
                        _new = self.canvas.create_rectangle(
                            self.coords_zoom[0][0] + _bbox[0], self.coords_zoom[0][1] + _bbox[1],
                            self.coords_zoom[1][0] + _bbox[0], self.coords_zoom[1][1] + _bbox[1],
                            width=2,
                            outline='red'
                        )
                        self.paint['CAR'].append(_new)
                else:
                    if len(self.coords_zoom) >= 2:
                        _new = self.canvas.create_rectangle(
                            self.coords_full[0][0] + _bbox[0], self.coords_full[0][1] + _bbox[1],
                            self.coords_full[1][0] + _bbox[0], self.coords_full[1][1] + _bbox[1],
                            width=2,
                            outline='red'
                        )
                        self.paint['CAR'].append(_new)
        elif self.drawObj == const.CALIBRATION_MODE_PIC:
            if self.drawMode == const.Calibration.NEW_AXEL_CALIBRATION:
                self.cleanCanvasByType(self.paint['PIC_NEW_AXEL'], self.canvas)
                self.cleanCanvasByType(self.paint['POINT'], self.canvas)
                if not self.FULL_SCREEN:
                    for p in self.coords_zoom:
                        self.paint['PIC_NEW_AXEL'].append(self.canvas.create_line(
                            (p[0] + _bbox[0],
                             self.show_img.size[1] + _bbox[1]),
                            (p[0] + _bbox[0],
                             _bbox[1]), width=2, fill='yellow'))

                else:
                    for p in self.coords_full:
                        self.paint['PIC_NEW_AXEL'].append(self.canvas.create_line(
                            (p[0] + _bbox[0],
                             self.show_img.size[1] + _bbox[1]),
                            (p[0] + _bbox[0],
                             _bbox[1]), width=2, fill='yellow'))


    def display_point(self):
        if not self.FULL_SCREEN:
            if len(self.coords_zoom) > 0:
                self._create_point(self.coords_zoom[0], self.coords_zoom[1], 2, fill='red')
        else:
            if len(self.coords_full) > 0:
                self._create_point(self.coords_full[0], self.coords_full[1], 2, fill='red')

    def displayImage(self):
        self.origin_img = pilImage.open(self.currentPic)
        self.show_img = self.resizeImage(self.origin_img)
        self._photo = pilImgTk.PhotoImage(self.show_img)
        _middle = self.win_size[0]/2, self.win_size[1]/2
        _img = self.canvas.create_image(_middle[0], _middle[1], image=self._photo)
        self.imgPosition = self.canvas.bbox(_img)
        self.paint['IMG'].append(_img)

    def displayImage2(self):
        self.origin_img = pilImage.open(self.currentPic)
        # self.showZoomRatio = 1
        self.show_img = self.origin_img
        self._photo = pilImgTk.PhotoImage(self.origin_img)
        _img = self.canvas.create_image(
            (
                self.origin_img.size[0] / 2,
                self.origin_img.size[1] / 2
                ),
            image=self._photo)
        self.imgPosition = self.canvas.bbox(_img)
        self.paint['IMG'].append(_img)

    def bbox_move(self, offX, offY, specify=None):
        if specify is None:
            _items = self.canvas.find_all()
            for item in _items:
                self.canvas.move(item, offX, offY)
        else:
            self.canvas.move(specify, offX, offY)

    def update_title(self):
        self.cleanCanvasByType(self.paint["TEXT"], self.canvas)
        self.paint["TEXT"].append(
            self.canvas.create_text(
                self.canvas.bbox(self.paint['IMG'])[2]/2,
                10,
                text=self.format_repr_wheel()  if len(self.pic_origin_wheel_data) > 0 else "无车轴信息",
                fill='blue'
            )
        )
        self.paint["TEXT"].append(
            self.canvas.create_text(
                self.canvas.bbox(self.paint['IMG'])[2]/2,
                30,
                text=self.format_repr_calibration() if self.pic_origin_calibration_data is not None else "无标定信息",
                fill='blue'
            )
        )
        try:
            if self.drawObj == const.CALIBRATION_MODE_FILE:
                _info = '(%s/%s) %s %s 线路：%s' % (
                    str(self.currentPicIndex + 1),
                    len(self.show_pics),
                    os.path.normpath(self.currentPic),
                    '【新增】' if list(self.oldCalibrationInfo.values()).count(-1) == 4 or list(self.oldCalibrationInfo.values()).count(0) == 4 else '',
                    self.currentPicInfo[1]
                )
            else:
                _info = '(%s/%s) %s %s 线路：%s' % (
                    str(self.currentPicIndex + 1),
                    len(self.show_pics),
                    os.path.normpath(self.currentPic),
                    '',
                    self.currentPicInfo[1]
                )
            self.win.title(_info)
        except:  # todo 没标定信息无法显示线路
            _info = '(%s/%s) %s %s' % (
                str(self.currentPicIndex + 1),
                len(self.show_pics),
                os.path.normpath(self.currentPic),
                '【新增】'
            )

            self.win.title(_info)


    def format_repr_wheel(self):
        r = ""
        i = 1
        for v in self.pic_wheel_value:
            r += "车轴" + str(i) + " : " + str(v) + "  "
            i += 1
        return r


    def format_repr_calibration(self):
        r = "位置 X：%s  Y：%s  车长：%s  车高：%s  车轴中心：%s  车轴偏移：%s  铁轨：%s" % (
            str(self.pic_calibration_value[0]),
            str(self.pic_calibration_value[1]),
            str(self.pic_calibration_value[2]),
            str(self.pic_calibration_value[3]),
            str(self.pic_calibration_value[4]),
            str(self.pic_calibration_value[5]),
            str(self.pic_calibration_value[6])
        )
        return r




    def displayPicCarCalibration(self):
        self.update_title()
        if self.pic_calibration_value is None:
            return
        if not self.FULL_SCREEN:
            _car = self.calc(mode=const.CALC_READ_CALIBRATION, _bbox=self.pic_calibration_value[:4])
            if _car.count(-1) != 4:  # 不为初始值
                x1, y1, x2, y2 = _car
                car_id = self.canvas.create_rectangle(x1, y1, x2, y2, width=2, outline='orange')
                self.paint['PIC_CAR'].append(car_id)
                self.history['PIC_CAR'].append(car_id)
        else:
            x1, y1, x2, y2 = self.pic_calibration_value[:4]
            car_id = self.canvas.create_rectangle(x1, y1, x2+x1, y2+y1, width=2, outline='orange')
            self.paint['PIC_CAR'].append(car_id)
            self.history['PIC_CAR'].append(car_id)

    def displayCarCalibration(self):
        self.oldCalibrationInfo = self.calibrationHelper.carbody(self.currentPicInfo[0], self.currentPicInfo[1], self.currentPicInfo[2])
        self.update_title()
        if not self.FULL_SCREEN:
            _car = self.calc(mode=const.CALC_READ_CALIBRATION)
            if _car.count(-1) != 4:  # 不为初始值
                x1, y1, x2, y2 = _car
                car_id = self.canvas.create_rectangle(x1, y1, x2, y2, width=2, outline='orange')
                self.paint['CAR'].append(car_id)
                self.history['CAR'].append(car_id)
        else:
            x1 = self.oldCalibrationInfo['X_carbody']
            y1 = self.oldCalibrationInfo['Y_carbody']
            x2 = self.oldCalibrationInfo['width_carbody'] + x1
            y2 = self.oldCalibrationInfo['height_carbody'] + y1
            car_id = self.canvas.create_rectangle(x1, y1, x2, y2, width=2, outline='orange')
            self.paint['CAR'].append(car_id)
            self.history['CAR'].append(car_id)

    def displayAxelCalibration(self):
        # 画各个车轴
        _side = self.currentPicInfo[2]
        _line = str(self.currentPicInfo[1])
        _w = self.origin_img.size[0]
        _bbox_img = self.canvas.bbox(self.paint['IMG'][0])
        _Z = True if self.currentPic in self.source['Z'] else False
        try:
            _offset = int(self.calibrationHelper.axel(_line, _side, Z=_Z))
        except:
            _offset = 0
        tmp = copy.deepcopy(self.pic_wheel_value)
        if _side == 'R':
            tmp.reverse()
            tmp = [_w - x for x in tmp]
        for _axel in tmp:
            if not self.FULL_SCREEN:
                axel_id = self.canvas.create_line(
                    (_axel-_offset)*self.showZoomRatio,
                    self.show_img.size[1] + _bbox_img[1],
                    (_axel-_offset)*self.showZoomRatio,
                    _bbox_img[1],
                    width=2,
                    fill='yellow', dash=(6,6))
                self.paint['AXEL'].append(axel_id)
                self.history['AXEL'].append(axel_id)
            else:
                axel_id = self.canvas.create_line(
                    (_axel-_offset),
                    self.show_img.size[1] + _bbox_img[1],
                    (_axel-_offset),
                    _bbox_img[1],
                    width=2,
                    fill='yellow', dash=(6,6))
                self.paint['AXEL'].append(axel_id)
                self.history['AXEL'].append(axel_id)

    def displayWheelCalibration(self):
        # 车轴y
        _side = self.currentPicInfo[2]
        _line = str(self.currentPicInfo[1])
        _bbox_img = self.canvas.bbox(self.paint['IMG'][0])
        _Z = True if self.currentPic in self.source['Z'] else False
        try:
            _y = int(self.calibrationHelper.wheel(_line, _side, Z=_Z))
        except:
            _y = 0
        if not self.FULL_SCREEN:
            wheel_id = self.canvas.create_line(
                0,
                _y * self.showZoomRatio + _bbox_img[1],
                _bbox_img[2],
                _y * self.showZoomRatio + _bbox_img[1],
                width=2,
                fill='green'
            )
            self.paint['WHEEL'].append(wheel_id)
            self.history['WHEEL'].append(wheel_id)
        else:
            wheel_id = self.canvas.create_line(
                0,
                _y + _bbox_img[1],
                _bbox_img[2],
                _y + _bbox_img[1],
                width=2,
                fill='green'
            )
            self.paint['WHEEL'].append(wheel_id)
            self.history['WHEEL'].append(wheel_id)

    def displayPicAxelCalibration(self):
        # 画各个车轴
        _side = self.currentPicInfo[2]
        _w = self.origin_img.size[0]
        _bbox_img = self.canvas.bbox(self.paint['IMG'][0])
        try:
            _offset = self.pic_calibration_value[5] if self.pic_calibration_value is not None else 0
        except:
            _offset = 0
        tmp = copy.deepcopy(self.pic_wheel_value)
        if _side == 'R':
            tmp.reverse()
            tmp = [_w - x for x in tmp]
        for _axel in tmp:
            if not self.FULL_SCREEN:
                axel_id = self.canvas.create_line(
                    (_axel-_offset)*self.showZoomRatio,
                    self.show_img.size[1] + _bbox_img[1],
                    (_axel-_offset)*self.showZoomRatio,
                    _bbox_img[1],
                    width=2,
                    fill='yellow', dash=(6,6))
                self.paint['PIC_AXEL'].append(axel_id)
                self.history['PIC_AXEL'].append(axel_id)
            else:
                axel_id = self.canvas.create_line(
                    (_axel-_offset),
                    self.show_img.size[1] + _bbox_img[1],
                    (_axel-_offset),
                    _bbox_img[1],
                    width=2,
                    fill='yellow', dash=(6,6))
                self.paint['PIC_AXEL'].append(axel_id)
                self.history['PIC_AXEL'].append(axel_id)

    def displayPicWheelCalibration(self):
        # 车轴y
        _bbox_img = self.canvas.bbox(self.paint['IMG'][0])
        try:
            _y = self.pic_calibration_value[4] if self.pic_calibration_value is not None else 0
        except:
            _y = 0
        if not self.FULL_SCREEN:
            wheel_id = self.canvas.create_line(
                0,
                _y * self.showZoomRatio + _bbox_img[1],
                _bbox_img[2],
                _y * self.showZoomRatio + _bbox_img[1],
                width=2,
                fill='green'
            )
            self.paint['PIC_WHEEL'].append(wheel_id)
            self.history['PIC_WHEEL'].append(wheel_id)
        else:
            wheel_id = self.canvas.create_line(
                0,
                _y + _bbox_img[1],
                _bbox_img[2],
                _y + _bbox_img[1],
                width=2,
                fill='green'
            )
            self.paint['PIC_WHEEL'].append(wheel_id)
            self.history['PIC_WHEEL'].append(wheel_id)

    def displayOutline(self):
        self.cleanCanvasByType(self.paint['OUTLINE'], self.canvas)
        _line = str(self.currentPicInfo[1])
        _kind = str(self.currentPicInfo[0])
        try:
            _outlines = self.calibrationHelper.outline(_line, _kind)
        except:
            _outlines = [0, 0]
        for _outline in _outlines:
            if not self.FULL_SCREEN:
                outline_id = self.canvas.create_line(
                    0,
                    _outline *self.showZoomRatio + self.imgPosition[1],
                    self.imgPosition[2],
                    _outline *self.showZoomRatio + self.imgPosition[1],
                    width=2,
                    fill='yellow')
                self.paint['OUTLINE'].append(outline_id)
                self.history['OUTLINE'].append(outline_id)
            else:
                outline_id = self.canvas.create_line(
                    0,
                    _outline + self.imgPosition[1],
                    self.imgPosition[2],
                    _outline + self.imgPosition[1],
                    width=2,
                    fill='yellow')
                self.paint['OUTLINE'].append(outline_id)
                self.history['OUTLINE'].append(outline_id)


    def displayPicOutline(self):
        self.cleanCanvasByType(self.paint['PIC_OUTLINE'], self.canvas)
        try:
            _outlines = [self.pic_calibration_value[1], self.pic_calibration_value[3]]
            _outlines[1] = _outlines[0] + _outlines[1]
        except:
            _outlines = [0, 0]
        for _outline in _outlines:
            if not self.FULL_SCREEN:
                outline_id = self.canvas.create_line(
                    0,
                    _outline *self.showZoomRatio + self.imgPosition[1],
                    self.imgPosition[2],
                    _outline *self.showZoomRatio + self.imgPosition[1],
                    width=2,
                    fill='yellow')
                self.paint['PIC_OUTLINE'].append(outline_id)
                self.history['PIC_OUTLINE'].append(outline_id)
            else:
                outline_id = self.canvas.create_line(
                    0,
                    _outline + self.imgPosition[1],
                    self.imgPosition[2],
                    _outline + self.imgPosition[1],
                    width=2,
                    fill='yellow')
                self.paint['PIC_OUTLINE'].append(outline_id)
                self.history['PIC_OUTLINE'].append(outline_id)

    def displayRailCalibration(self):
        _side = self.currentPicInfo[2]
        _line = str(self.currentPicInfo[1])
        _Z = True if self.currentPic in self.source['Z'] else False
        _bbox_img = self.canvas.bbox(self.paint['IMG'][0])
        try:
            _raily = int(self.calibrationHelper.rail(_line, _side, Z=_Z))
        except:
            _raily = 0
        if _raily != -1:
            if not self.FULL_SCREEN:
                rail_id = self.canvas.create_line(
                    0,
                    _raily * self.showZoomRatio + _bbox_img[1],
                    _bbox_img[2],
                    _raily * self.showZoomRatio + _bbox_img[1],
                    width=2,
                    fill='blue'
                )
                self.paint['RAIL'].append(rail_id)
                self.history['RAIL'].append(rail_id)
            else:
                rail_id = self.canvas.create_line(
                    0,
                    _raily + _bbox_img[1],
                    _bbox_img[2],
                    _raily + _bbox_img[1],
                    width = 2,
                    fill = 'blue'
                )
                self.paint['RAIL'].append(rail_id)
                self.history['RAIL'].append(rail_id)

    def displayPicRailCalibration(self):
        _bbox_img = self.canvas.bbox(self.paint['IMG'][0])
        _raily = self.pic_calibration_value[6] if self.pic_calibration_value is not None else 0
        if _raily != -1:
            if not self.FULL_SCREEN:
                rail_id = self.canvas.create_line(
                    0,
                    _raily * self.showZoomRatio + _bbox_img[1],
                    _bbox_img[2],
                    _raily * self.showZoomRatio + _bbox_img[1],
                    width=2,
                    fill='blue'
                )
                self.paint['PIC_RAIL'].append(rail_id)
                self.history['PIC_RAIL'].append(rail_id)
            else:
                rail_id = self.canvas.create_line(
                    0,
                    _raily + _bbox_img[1],
                    _bbox_img[2],
                    _raily + _bbox_img[1],
                    width=2,
                    fill='blue'
                )
                self.paint['PIC_RAIL'].append(rail_id)
                self.history['PIC_RAIL'].append(rail_id)

    def cleanCanvasByType(self, lst, _from):
        for id in lst:
            _from.delete(id)
        lst.clear()

    def resizeImage(self, im):
        wratio = 1.0 * self.show_size[0] / im.size[0]  # 计算width缩放倍数
        hratio = 1.0 * self.show_size[1] / im.size[1]  # 计算height缩放倍数
        self.showZoomRatio = min([wratio, hratio])
        width = int(im.size[0] * self.showZoomRatio)
        height = int(im.size[1] * self.showZoomRatio)
        return im.resize((width, height), pilImage.ANTIALIAS)

    def showNextPic(self):
        if -1 < self.currentPicIndex + 1 < len(self.show_pics):
            self.currentPicIndex += 1
            self.setCurrnetPic(self.show_pics[self.currentPicIndex])
            self.show()
            self.update_title()
            self.setNoneCalibration()

    def showLastPic(self):
        if -1 < self.currentPicIndex - 1 < len(self.show_pics):
            self.currentPicIndex -= 1
            self.setCurrnetPic(self.show_pics[self.currentPicIndex])
            self.show()
            self.update_title()
            self.setNoneCalibration()
            
    def setCarCalibration(self):
        self.drawMode = const.Calibration.CAR_CALIBRATION
        if self.btn_calibration_type is not None:
            self.btn_calibration_type.config(text='车厢标定')
        self.current_actived_menu = None
        self.coords_full.clear()
        self.coords_zoom.clear()

    def setPicCarCalibration(self):
        self.drawMode = const.Calibration.PIC_CAR_CALIBRATION
        if self.btn_calibration_type is not None:
            self.btn_calibration_type.config(text='车厢标定')
        self.current_actived_menu = None
        self.coords_full.clear()
        self.coords_zoom.clear()

    def setOutlineCalibration(self):
        self.drawMode = const.Calibration.OUTLINE_CALIBRATION
        if self.btn_calibration_type is not None:
            self.btn_calibration_type.config(text='轮廓标定')
        self.current_actived_menu = None
        self.coords_full.clear()
        self.coords_zoom.clear()

    def setAxelCalibration(self):
        self.drawMode = const.Calibration.AXEL_Y_CALIBRATION
        if self.btn_calibration_type is not None:
            self.btn_calibration_type.config(text='车轴标定')
        self.current_actived_menu = None
        self.coords_full.clear()
        self.coords_zoom.clear()

    def setRailCalibration(self):
        self.drawMode = const.Calibration.RAIL_Y_CALIBRATION
        if self.btn_calibration_type is not None:
            self.btn_calibration_type.config(text='铁轨标定')
        self.current_actived_menu = None
        self.coords_full.clear()
        self.coords_zoom.clear()


    def setNewWheelCalibration(self):
        self.drawMode = const.Calibration.NEW_AXEL_CALIBRATION
        if self.btn_calibration_type is not None:
            self.btn_calibration_type.config(text='添加车轴')
        self.current_actived_menu = None
        self.coords_full.clear()
        self.coords_zoom.clear()


    def setModifyWheelCalibration(self):
        self.drawMode = const.Calibration.AXEL_OFFSET_CALIBRATION
        if self.btn_calibration_type is not None:
            self.btn_calibration_type.config(text='调整车轴')
        self.current_actived_menu = None
        self.coords_full.clear()
        self.coords_zoom.clear()

    def setNoneCalibration(self):
        self.drawMode = const.Calibration.NONE_CALIBRATION
        if self.btn_calibration_type is not None:
            self.btn_calibration_type.config(text='标定类型')
        self.current_actived_menu = None
        self.coords_full.clear()
        self.coords_zoom.clear()

    def setCalibrationObjPic(self):
        self.drawObj = const.CALIBRATION_MODE_PIC
        self.operate_obj_menu_value.set(2)
        self.coords_full.clear()
        self.coords_zoom.clear()
        self.display()

    def setCalibrationObjFile(self):
        if self.calibrationHelper is not None:
            self.drawObj = const.CALIBRATION_MODE_FILE
            self.operate_obj_menu_value.set(1)
            self.coords_full.clear()
            self.coords_zoom.clear()
            self.display()
        else:
            self.operate_obj_menu_value.set(2)

    def setSystemToSartas(self):
        self.is_sartas = True
        self.display()

    def setSystemToZhineng(self):
        self.is_sartas = False
        self.display()

    def eCanvasMotion(self, event):
        if len(self.paint['IMG']) == 0: return
        bbox = self.canvas.bbox(self.paint['IMG'][0])
        if not self.FULL_SCREEN:
            self.zoom_last_x = event.x
            self.zoom_last_y = event.y
            self.full_last_x = round(event.x / self.showZoomRatio)
            self.full_last_y = round(event.y / self.showZoomRatio)
        else:
            self.zoom_last_x = round(event.x * self.showZoomRatio)
            self.zoom_last_y = round(event.y * self.showZoomRatio)
            self.full_last_x = event.x
            self.full_last_y = event.y
        # print(self.zoom_last_x, self.zoom_last_y)
        # print(self.full_last_x, self.full_last_y)
        self.cleanCanvasByType(self.paint['CONSULT'], self.canvas)
        if bbox[0] <= event.x <= bbox[2] and bbox[1] <= event.y <= bbox[3]:
            self.paint['CONSULT'].append(
                self.canvas.create_line(
                    bbox[0], event.y, bbox[2], event.y, width=2, fill='yellow', dash=(6,6)
                )
            )
            self.paint['CONSULT'].append(
                self.canvas.create_line(
                    event.x, bbox[1], event.x, bbox[3], width=2, fill='yellow', dash=(6,6)
                )
            )
            self.cleanCanvasByType(self.paint['TEXT_COORDS'], self.canvas)
            if not self.FULL_SCREEN:
                self.paint["TEXT_COORDS"].append(
                    self.canvas.create_text(
                        event.x + 40,
                        event.y + 30,
                        text='%s,%s\n(%s,%s)' % (
                            str(round((event.x - self.canvas.bbox(self.paint['IMG'][0])[0]) /self.showZoomRatio)),
                            str(round((event.y - self.canvas.bbox(self.paint['IMG'][0])[1]) /self.showZoomRatio)),
                            str(event.x),
                            str(event.y)
                        ),
                        fill='red'
                    )
                )
            else:
                self.paint["TEXT_COORDS"].append(
                    self.canvas.create_text(
                        event.x + 100,
                        event.y + 100,
                        text='%s,%s\n(%s,%s)' % (
                            str(event.x - self.canvas.bbox(self.paint['IMG'][0])[0]),
                            str(event.y - self.canvas.bbox(self.paint['IMG'][0])[1]),
                            str(event.x),
                            str(event.y)
                        ),
                        fill='red'
                    )
                )
            self.update_title()

    def pop_calibration_type(self):
        if self.current_actived_menu is not None:
            self.current_actived_menu.unpost()
            self.current_actived_menu = None
        else:
            popmenu = Menu(self.canvas, tearoff=0)
            self.current_actived_menu = popmenu

            if self.currentPic in self.source['G']:
                popmenu.add_command(label='  车 厢 标 定 ', command=self.setCarCalibration)
                popmenu.add_command(label='  车 轴 标 定 ', command=self.setAxelCalibration)
                popmenu.add_command(label='  铁 轨 标 定 ', command=self.setRailCalibration)
                if self.drawObj == const.CALIBRATION_MODE_PIC:
                    if self.pic_wheel_value == []:
                        popmenu.add_command(label='  添 加 车 轴 ', command=self.setNewWheelCalibration)
                    else:
                        popmenu.add_command(label='  调 整 车 轴 ', command=self.setModifyWheelCalibration)
                else:
                    popmenu.add_command(label='  调 整 车 轴 ', command=self.setModifyWheelCalibration)
                popmenu.post(round(self.show_size[0] / 2 + 195), round(self.show_size[1] - 100))
            if self.currentPic in self.source['Z']:
                popmenu.add_command(label='  车 轴 标 定 ', command=self.setAxelCalibration)
                popmenu.add_command(label='  铁 轨 标 定 ', command=self.setRailCalibration)
                if self.drawObj == const.CALIBRATION_MODE_PIC:
                    if self.pic_wheel_value == []:
                        popmenu.add_command(label='  添 加 车 轴 ', command=self.setNewWheelCalibration)
                    else:
                        popmenu.add_command(label='  调 整 车 轴 ', command=self.setModifyWheelCalibration)
                else:
                    popmenu.add_command(label='  调 整 车 轴 ', command=self.setModifyWheelCalibration)
                popmenu.post(round(self.show_size[0] / 2 + 195), round(self.show_size[1] - 80))
            if self.currentPic in self.source['T']:
                popmenu.add_command(label='  轮 廓 标 定 ', command=self.setOutlineCalibration)
                popmenu.post(round(self.show_size[0] / 2 + 195), round(self.show_size[1] - 40))

    def pop_calibration_obj(self):
        if self.current_actived_menu is not None:
            self.current_actived_menu.unpost()
            self.current_actived_menu = None
        else:
            popmenu = Menu(self.canvas, tearoff=0)
            self.current_actived_menu = popmenu
            popmenu.add_command(label='  标   定 ', command=self.setCalibrationObjFile)
            popmenu.add_command(label='  图   片 ', command=self.setCalibrationObjPic)
            popmenu.post(round(self.show_size[0] / 2 + 215), round(self.show_size[1] - 80))

    def eCanvasButton_1(self, event):
        if len(self.paint['IMG']) == 0:
            return
        _bbox = self.canvas.bbox(self.paint['IMG'][0])

        if self.drawObj == const.CALIBRATION_MODE_FILE and self.drawMode == const.Calibration.CAR_CALIBRATION:
            if len(self.coords_zoom) > 1:
                self.coords_zoom.clear()
            if len(self.coords_full) > 1:
                self.coords_full.clear()

            if not self.FULL_SCREEN:
                self.coords_zoom.append(
                    (
                        event.x - _bbox[0],
                        event.y - _bbox[1]
                    )
                )
                self.coords_full.append(
                    (
                        round((event.x - _bbox[0])/self.showZoomRatio),
                        round((event.y - _bbox[1])/self.showZoomRatio)
                    )
                )
            else:
                self.coords_zoom.append(
                    (
                        round((event.x - _bbox[0]) * self.showZoomRatio),
                        round((event.y - _bbox[1]) * self.showZoomRatio)
                    )
                )
                self.coords_full.append(
                    (
                        event.x - _bbox[0],
                        event.y - _bbox[1]
                    )
                )
            self._create_point(event.x, event.y, 2, fill='red')
            if not self.FULL_SCREEN and len(self.coords_zoom) >= 2:
                self.cleanCanvasByType(self.paint['CAR'], self.canvas)
                self.cleanCanvasByType(self.paint['POINT'], self.canvas)
                _new = self.canvas.create_rectangle(
                    # self.coords[0][0] + bbox[0], self.coords[0][1] + bbox[1],
                    self.coords_zoom[0][0] + _bbox[0], self.coords_zoom[0][1] + _bbox[1],
                    self.coords_zoom[1][0] + _bbox[0], self.coords_zoom[1][1] + _bbox[1],
                    width=2,
                    outline='red'
                )
                self.paint['CAR'].append(_new)
            if self.FULL_SCREEN and len(self.coords_full) >= 2:
                self.cleanCanvasByType(self.paint['CAR'], self.canvas)
                self.cleanCanvasByType(self.paint['POINT'], self.canvas)

                _new = self.canvas.create_rectangle(
                    self.coords_full[0][0] + _bbox[0], self.coords_full[0][1] + _bbox[1],
                    self.coords_full[1][0] + _bbox[0], self.coords_full[1][1] + _bbox[1],
                    width=2,
                    outline='red'
                )
                self.paint['CAR'].append(_new)
        elif self.drawObj == const.CALIBRATION_MODE_PIC and self.drawMode == const.Calibration.CAR_CALIBRATION:
            if len(self.coords_zoom) > 1:
                self.coords_zoom.clear()
            if len(self.coords_full) > 1:
                self.coords_full.clear()

            if not self.FULL_SCREEN:
                self.coords_zoom.append(
                    (
                        event.x - _bbox[0],
                        event.y - _bbox[1]
                    )
                )
                self.coords_full.append(
                    (
                        round((event.x - _bbox[0])/self.showZoomRatio),
                        round((event.y - _bbox[1])/self.showZoomRatio)
                    )
                )
            else:
                self.coords_zoom.append(
                    (
                        round((event.x - _bbox[0]) * self.showZoomRatio),
                        round((event.y - _bbox[1]) * self.showZoomRatio)
                    )
                )
                self.coords_full.append(
                    (
                        event.x - _bbox[0],
                        event.y - _bbox[1]
                    )
                )
            self._create_point(event.x, event.y, 2, fill='red')
            if not self.FULL_SCREEN and len(self.coords_zoom) >= 2:
                self.cleanCanvasByType(self.paint['PIC_CAR'], self.canvas)
                self.cleanCanvasByType(self.paint['POINT'], self.canvas)
                _new = self.canvas.create_rectangle(
                    # self.coords[0][0] + bbox[0], self.coords[0][1] + bbox[1],
                    self.coords_zoom[0][0] + _bbox[0], self.coords_zoom[0][1] + _bbox[1],
                    self.coords_zoom[1][0] + _bbox[0], self.coords_zoom[1][1] + _bbox[1],
                    width=2,
                    outline='red'
                )
                self.paint['PIC_CAR'].append(_new)
            if self.FULL_SCREEN and len(self.coords_full) >= 2:
                self.cleanCanvasByType(self.paint['PIC_CAR'], self.canvas)
                self.cleanCanvasByType(self.paint['POINT'], self.canvas)

                _new = self.canvas.create_rectangle(
                    self.coords_full[0][0] + _bbox[0], self.coords_full[0][1] + _bbox[1],
                    self.coords_full[1][0] + _bbox[0], self.coords_full[1][1] + _bbox[1],
                    width=2,
                    outline='red'
                )
                self.paint['PIC_CAR'].append(_new)

        elif self.drawObj == const.CALIBRATION_MODE_FILE and self.drawMode == const.Calibration.AXEL_Y_CALIBRATION:
            self.cleanCanvasByType(self.paint['WHEEL'], self.canvas)
            self.paint['WHEEL'].append(
                self.canvas.create_line(_bbox[0], event.y, _bbox[2], event.y, width=2, fill='yellow')
            )
            if not self.FULL_SCREEN:
                self.axel_y = round((event.y - self.canvas.bbox(self.paint['IMG'][0])[1]) / self.showZoomRatio)
            else:
                self.axel_y = event.y - self.canvas.bbox(self.paint['IMG'][0])[1]


        elif self.drawObj == const.CALIBRATION_MODE_PIC and self.drawMode == const.Calibration.AXEL_Y_CALIBRATION:
            self.cleanCanvasByType(self.paint['PIC_WHEEL'], self.canvas)
            self.paint['PIC_WHEEL'].append(
                self.canvas.create_line(_bbox[0], event.y, _bbox[2], event.y, width=2, fill='yellow')
            )
            if not self.FULL_SCREEN:
                self.axel_y = round((event.y - self.canvas.bbox(self.paint['IMG'][0])[1]) / self.showZoomRatio)
            else:
                self.axel_y = event.y - self.canvas.bbox(self.paint['IMG'][0])[1]

        elif self.drawObj == const.CALIBRATION_MODE_FILE and self.drawMode == const.Calibration.AXEL_OFFSET_CALIBRATION:
            self.cleanCanvasByType(self.paint['AXEL'], self.canvas)
            _side = self.currentPicInfo[2]
            _w = self.origin_img.size[0]
            tmp = copy.deepcopy(self.pic_wheel_value)
            if len(tmp) > 0:
                _x_offset = 0
                if _side == 'R':
                    tmp.reverse()
                    tmp = [_w - x for x in tmp]
                    if not self.FULL_SCREEN:
                        _x_offset = round(tmp[0]*self.showZoomRatio) - event.x
                    else:
                        _x_offset = tmp[0] - event.x
                if _side == 'L':
                    if not self.FULL_SCREEN:
                        _x_offset = round(tmp[2]*self.showZoomRatio) - event.x
                    else:
                        _x_offset = tmp[2] - event.x
                if not self.FULL_SCREEN:
                    self.axel_x_offset = round((_x_offset + _bbox[0])/self.showZoomRatio)
                else:
                    self.axel_x_offset = _x_offset + _bbox[0]
                for _axel in tmp:
                    if not self.FULL_SCREEN:
                        self.paint['AXEL'].append(self.canvas.create_line(
                            (round(_axel*self.showZoomRatio) - _x_offset,
                            self.show_img.size[1] + _bbox[1]),
                            (round(_axel*self.showZoomRatio) - _x_offset,
                             _bbox[1]), width=2, fill='yellow'))
                    else:
                        self.paint['AXEL'].append(self.canvas.create_line(
                            (_axel - _x_offset,
                            self.show_img.size[1] + _bbox[1]),
                            (_axel - _x_offset,
                             _bbox[1]), width=2, fill='yellow'))


        elif self.drawObj == const.CALIBRATION_MODE_PIC and self.drawMode == const.Calibration.AXEL_OFFSET_CALIBRATION:
            self.cleanCanvasByType(self.paint['PIC_AXEL'], self.canvas)
            _side = self.currentPicInfo[2]
            _w = self.origin_img.size[0]
            tmp = copy.deepcopy(self.pic_wheel_value)
            if len(tmp) > 0:
                _x_offset = 0
                if _side == 'R':
                    tmp.reverse()
                    tmp = [_w - x for x in tmp]
                    if not self.FULL_SCREEN:
                        _x_offset = round(tmp[0]*self.showZoomRatio) - event.x
                    else:
                        _x_offset = tmp[0] - event.x
                if _side == 'L':
                    if not self.FULL_SCREEN:
                        _x_offset = round(tmp[2]*self.showZoomRatio) - event.x
                    else:
                        _x_offset = tmp[2] - event.x
                if not self.FULL_SCREEN:
                    self.axel_x_offset = round((_x_offset + _bbox[0])/self.showZoomRatio)
                else:
                    self.axel_x_offset = _x_offset + _bbox[0]
                for _axel in tmp:
                    if not self.FULL_SCREEN:
                        self.paint['PIC_AXEL'].append(self.canvas.create_line(
                            (round(_axel*self.showZoomRatio) - _x_offset,
                            self.show_img.size[1] + _bbox[1]),
                            (round(_axel*self.showZoomRatio) - _x_offset,
                             _bbox[1]), width=2, fill='yellow'))
                    else:
                        self.paint['PIC_AXEL'].append(self.canvas.create_line(
                            (_axel - _x_offset,
                            self.show_img.size[1] + _bbox[1]),
                            (_axel - _x_offset,
                             _bbox[1]), width=2, fill='yellow'))


        elif self.drawObj == const.CALIBRATION_MODE_FILE and self.drawMode == const.Calibration.RAIL_Y_CALIBRATION:
            self.cleanCanvasByType(self.paint['RAIL'], self.canvas)
            if not self.FULL_SCREEN:
                self.rail_y = round((event.y - self.canvas.bbox(self.paint['IMG'][0])[1]) / self.showZoomRatio)
            else:
                self.rail_y = event.y - self.canvas.bbox(self.paint['IMG'][0])[1]
            self.paint['RAIL'].append(
                self.canvas.create_line(0, event.y, self.show_img.size[0], event.y, width=2, fill='blue')
            )
        elif self.drawObj == const.CALIBRATION_MODE_PIC and self.drawMode == const.Calibration.RAIL_Y_CALIBRATION:
            self.cleanCanvasByType(self.paint['PIC_RAIL'], self.canvas)
            if not self.FULL_SCREEN:
                self.rail_y = round((event.y - self.canvas.bbox(self.paint['IMG'][0])[1]) / self.showZoomRatio)
            else:
                self.rail_y = event.y - self.canvas.bbox(self.paint['IMG'][0])[1]
            self.paint['PIC_RAIL'].append(
                self.canvas.create_line(0, event.y, self.show_img.size[0], event.y, width=2, fill='blue')
            )
        elif self.drawObj == const.CALIBRATION_MODE_FILE and self.drawMode == const.Calibration.OUTLINE_CALIBRATION:
            if self.outlines[0] != 0 and self.outlines[1] != 0 or len(self.paint['OUTLINE']) > 1:
                self.outlines[0] = 0
                self.outlines[1] = 0
                self.cleanCanvasByType(self.paint['OUTLINE'], self.canvas)
            if self.outlines[0] == 0:
                if not self.FULL_SCREEN:
                    self.outlines[0] = round((event.y - _bbox[1]) / self.showZoomRatio)
                else:
                    self.outlines[0] = event.y - _bbox[1]
            elif self.outlines[1] == 0:
                if not self.FULL_SCREEN:
                    self.outlines[1] = round((event.y - _bbox[1]) / self.showZoomRatio)
                else:
                    self.outlines[1] = event.y - _bbox[1]
            # print(self.outlines)
            self.paint['OUTLINE'].append(
                self.canvas.create_line(0, event.y, self.show_img.size[0], event.y, width=2, fill='blue')
            )
        elif self.drawObj == const.CALIBRATION_MODE_PIC and self.drawMode == const.Calibration.OUTLINE_CALIBRATION:
            if self.outlines[0] != 0 and self.outlines[1] != 0 or len(self.paint['PIC_OUTLINE']) > 1:
                self.outlines[0] = 0
                self.outlines[1] = 0
                self.cleanCanvasByType(self.paint['PIC_OUTLINE'], self.canvas)
            if self.outlines[0] == 0:
                if not self.FULL_SCREEN:
                    self.outlines[0] = round((event.y - _bbox[1]) / self.showZoomRatio)
                else:
                    self.outlines[0] = event.y - _bbox[1]
            elif self.outlines[1] == 0:
                if not self.FULL_SCREEN:
                    self.outlines[1] = round((event.y - _bbox[1]) / self.showZoomRatio)
                else:
                    self.outlines[1] = event.y - _bbox[1]
            # print(self.outlines)
            self.paint['PIC_OUTLINE'].append(
                self.canvas.create_line(0, event.y, self.show_img.size[0], event.y, width=2, fill='blue')
            )
        elif self.drawObj == const.CALIBRATION_MODE_PIC and self.drawMode == const.Calibration.NEW_AXEL_CALIBRATION:
            if not self.FULL_SCREEN:
                self.coords_zoom.append(
                    (
                        event.x - _bbox[0],
                        event.y - _bbox[1]
                    )
                )
                self.coords_full.append(
                    (
                        round((event.x - _bbox[0])/self.showZoomRatio),
                        round((event.y - _bbox[1])/self.showZoomRatio)
                    )
                )
            else:
                self.coords_zoom.append(
                    (
                        round((event.x - _bbox[0]) * self.showZoomRatio),
                        round((event.y - _bbox[1]) * self.showZoomRatio)
                    )
                )
                self.coords_full.append(
                    (
                        event.x - _bbox[0],
                        event.y - _bbox[1]
                    )
                )
            if not self.FULL_SCREEN:
                self.paint['PIC_NEW_AXEL'].append(self.canvas.create_line(
                    (event.x,
                     self.show_img.size[1] + _bbox[1]),
                    (event.x,
                     _bbox[1]), width=2, fill='yellow'))
            else:
                self.paint['PIC_NEW_AXEL'].append(self.canvas.create_line(
                    (event.x,
                     self.show_img.size[1] + _bbox[1]),
                    (event.x,
                     _bbox[1]), width=2, fill='yellow'))

    def eCanvasButton_1_release(self, event):

        if self.CTRL and len(self.paint['POINT']) > 0:
            _bbox_point = self.canvas.bbox(self.paint['POINT'][0])
            _bbox_img = self.canvas.bbox(self.paint['IMG'][0])
          #print('point bbox-> ', _bbox_point)
          #print('img bbox-> ', _bbox_img)
            if not self.FULL_SCREEN:
                if len(self.coords_zoom) > 0:

                    self.coords_zoom = [(_bbox_point[0] - _bbox_img[0], _bbox_point[1] - _bbox_img[1])]
                    self.coords_full = [
                        (round((_bbox_point[0] - _bbox_img[0]) / self.showZoomRatio), round((_bbox_point[1] - _bbox_img[1]) / self.showZoomRatio))]
            else:
                if len(self.coords_full) > 0:
                    self.coords_zoom = [
                        (round((_bbox_point[0] - _bbox_img[0])  * self.showZoomRatio), round((_bbox_point[1] - _bbox_img[1]) * self.showZoomRatio))]
                    self.coords_full = [(_bbox_point[0] - _bbox_img[0], _bbox_point[1] - _bbox_img[1])]

    def eCanvasButton_1_move(self, event):
        if self.drawMode == 1:
            self.cleanCanvasByType(self.paint['CAR'], self.canvas)
            self.paint['CAR'].append(
                self.canvas.create_rectangle(
                    (self.coords_zoom[0][0], self.coords_zoom[0][1]),
                    (event.x, event.y),
                    width=2,
                    outline='red'
                )
            )
        self.cleanCanvasByType(self.paint['CONSULT'], self.canvas)
        bbox = self.canvas.bbox(self.paint['IMG'][0])
        self.paint['CONSULT'].append(
            self.canvas.create_line(
                bbox[0], event.y, bbox[2], event.y, width=2, fill='yellow', dash=(6,6)
            )
        )
        self.paint['CONSULT'].append(
            self.canvas.create_line(
                event.x, bbox[1], event.x, bbox[3], width=2, fill='yellow', dash=(6,6)
            )
        )

    def _create_point(self, x, y, r, **kwargs):
        #   画圆 point
        # self._create_point(500,300,2,fill='red')
        self.paint['POINT'].append(self.canvas.create_oval(x - r, y - r, x + r, y + r, **kwargs))

    def _fetch_obj(self, event):
        c = event.widget
        x = c.canvasx(event.x)
        y = c.canvasy(event.y)
        self.fetchobjs = None
        objs = []
        xyxy = None
        item = c.find_withtag('current')
        # print('_ self.showoffset >>> (%d,%d)' % (self.showoffset))
        # if c.type(item) == 'image':
        for i in c.find_all():
            xyxy = c.bbox(i)
            if x >= xyxy[0] and x <= xyxy[2] and y >= xyxy[1] and y <= xyxy[3]:
                objs.append(i)
            # print('all >>>(%d), fetch >>>(%d)' % (len(c.find_all()), len(objs)))
        self.fetchobjs = objs

    def _clear_menu(self):
        # 清空menu
        if self.currentMenu is not None:
            self.currentMenu.unpost()

    def _find_new_car(self):
        _dt = dict()
        for _key in self.showPics.keys():
            _info = self.getPicInfo(_key)
            r = self.calibrationHelper.carbody(_info[0], _info[1], _info[2])
            if r.count(-1) == 4:
                _dt[_key] = dict()
                _sym = '%s_%s' % (str(_info[1]), _info[2])
                _dt[_key][_sym] = list()
        # print(_dt)
        return _dt

    def _frequency(self, dct_group):
        """
        计算分布
        """
        dict_frequency = dict()
        for _k in dct_group.keys():
            for k, v in dct_group[_k]:
                _id = self._getDictKey(_k, v)
                try:
                    if k in dict_frequency[_id] or v is None: continue
                    dict_frequency[_id].append(k)
                except KeyError:
                    dict_frequency[_id] = [k, ]
        return dict_frequency

    def _getDictKey(self, _k, v):
        if v is None:
            _id = _k + '_None'
        else:
            _id = _k + '_' + '_'.join(v)
        return _id

    # 统计分组
    def analyzeCalibrationFile(self):
        for line in self.calibrationHelper.Data:
            for side in self.calibrationHelper.Data[line]:
                _group = self._getKinds(line, side, self.algor_y_h)
                self.groupByCalibration[line+'_'+side] = self._frequency(_group)

    # 统计分组
    def _getKinds(self, line, side, func):
        kinds = []
        for items in self.calibrationHelper.Data[line][side]:
            if isinstance(self.calibrationHelper.Data[line][side][items], int):
                continue
            elif isinstance(self.calibrationHelper.Data[line][side][items], dict):
                kinds.append(items)
        return func(line, side, kinds)

    # 统计分组
    def algor_y_h(self, line, side, kinds):
        vals = dict()
        for kind in kinds:
            if '#' in kind:
                _curkind = kind.replace('#', '*')
            else:
                _curkind = kind
            carbody = self.calibrationHelper.carbody(_curkind, line, side)
            if carbody is None or list(carbody.values()).count(-1) == 4:
                try:
                    vals[_curkind[0]].append((_curkind, None))
                except KeyError:
                    vals[_curkind[0]] = [(_curkind, None),]
            else:
                y = int(carbody['Y_carbody']) / 2048
                h = int(carbody['height_carbody']) / 2048
                v1 = str(round(y / self.step_value))
                v2 = str(round(h / self.step_value))
                try:
                    vals[_curkind[0]].append((_curkind, [v1, v2]))
                except KeyError:
                    vals[_curkind[0]] = [(_curkind, [v1, v2]),]
                except:
                    pass
        return vals

    def algor_y(self, _line, kinds):
        vals = dict()
        _l = _line.split('_')[0]
        _s = _line.split('_')[1]
        for kind in kinds:
            if '#' in kind:
                _curkind = kind.replace('#', '*')
            else:
                _curkind = kind
            carbody = self.calibrationHelper.carbody(_curkind, _l, _s)
            if carbody.count(-1) == 4: 
                try:
                    vals[_curkind[0]].append((_curkind, None))
                except KeyError:
                    vals[_curkind[0]] = [(_curkind, None),]
            y = int(carbody[1]) / 2048
            v = str(round(y / self.step_value))
            try:
                vals[_curkind[0]].append((_curkind, [v]))
            except KeyError:
                vals[_curkind[0]] = [(_curkind, [v]),]
        return vals


class json_handle():
    def __init__(self, calibrationFile=None):
        self.data = None
        self.data_source_is_json = False
        self.readJSON(calibrationFile)

    def export(self):
        if self.data_source_is_json:
            self.export2JSON()
        else:
            self.export2XML()

    def readJSON(self, calibrationFile):
        if calibrationFile is not None and os.path.exists(calibrationFile):
            with open(calibrationFile, 'r') as fpRead:
                self.data = json.load(fpRead)
                self.data_source_is_json = True
                self._baseName = os.path.splitext(calibrationFile)[0]

    def export2JSON(self):
        with open(self._baseName + '.json', 'w') as fpWrite:
            json.dump(self.data, fpWrite, indent=4)

    @property
    def Data(self):
        return self.data

    def export2XML(self, xmlFile=None):
        _ImagingProperties = ET.Element('ImagingProperties')
        for line in self.data.keys():
            _CameraPosition = ET.SubElement(_ImagingProperties, 'CameraPosition')
            _CameraPosition.set('line', line)
            for side in self.data[line]:
                _lphototype = ET.SubElement(_CameraPosition, 'phototype')
                _lphototype.set('imgtype', side)
                for items in self.data[line][side]:
                    if isinstance(self.data[line][side][items], dict):
                        kind = ET.SubElement(_lphototype, 'carcz')
                        kind.set('cztype', items)
                        _x = ET.SubElement(kind, 'X_carbody')
                        _x.text = str(self.data[line][side][items]['X_carbody'])
                        _y = ET.SubElement(kind, 'Y_carbody')
                        _y.text = str(self.data[line][side][items]['Y_carbody'])
                        _w = ET.SubElement(kind, 'width_carbody')
                        _w.text = str(self.data[line][side][items]['width_carbody'])
                        _h = ET.SubElement(kind, 'height_carbody')
                        _h.text = str(self.data[line][side][items]['height_carbody'])
                    elif isinstance(self.data[line][side][items], int):
                        _newOffsetX = ET.Element(items)
                        _newOffsetX.text = str(self.data[line][side][items])
                        _lphototype.insert(0, _newOffsetX)
        tree = ET.ElementTree(element=_ImagingProperties)
        if xmlFile is not None:
            tree.write(xmlFile)
        else:
            tree.write(self._baseName + '.config')

    def _readXML(self, xmlFile):
        import re
        tree = None
        self._baseName = os.path.splitext(xmlFile)[0]
        try:
            with codecs.open(xmlFile, 'r', 'gbk') as f:
                text = re.sub(u"[\x00-\x08\x0b-\x0c\x0e-\x1f]+", u"", f.read())
                tree = ET.ElementTree(ET.fromstring(text))
        except ET.ParseError:
            pass
        finally:
            return tree

    def fromXML(self, xmlFile):
        _data = dict()
        tree = self._readXML(xmlFile)
        for line in tree.getroot():
            _data[line.get('line')] = dict()
            for side in line:
                _data[line.get('line')][side.get('imgtype')] = dict()
                for items in side:
                    if len(items.getchildren()) > 0:
                        _new_cztype = dict()
                        for item in items:
                            _new_cztype[item.tag] = round(int(item.text))
                        _data[line.get('line')][side.get('imgtype')][items.get('cztype')] = _new_cztype
                    else:
                        _data[line.get('line')][side.get('imgtype')][items.tag] = round(int(items.text))
        self.data_source_is_json = False
        self.data = _data

    def carbody(self, kind, line, side, _new=None):
        if _new is None:
            if line in self.data and side in self.data[line] and kind in self.data[line][side]:
                return self.data[line][side][kind]
            else:
                return None
        else:
            if line not in self.data:
                self.data[line] = dict()
            if side not in self.data[line]:
                self.data[line][side] = dict()
            if kind not in self.data[line][side]:
                self.data[line][side][kind] = dict()

            self.data[line][side][kind] = _new

    def axel(self, line, side, _new=None, Z=False):
        _item = 'train_axle_xoffset'
        if Z:
            _item = 'zx_train_axle_xoffset'
        if _new is None:
            if line in self.data \
                    and side in self.data[line] \
                    and _item in self.data[line][side]:
                return self.data[line][side][_item]
            else:
                return None
        else:
            if line not in self.data:
                self.data[line] = dict()
            if side not in self.data[line]:
                self.data[line][side] = dict()
            self.data[line][side][_item] = _new

    def wheel(self, line, side, _new=None, Z=False):
        _item = 'train_axle_y'
        if Z:
            _item = 'zx_train_axle_y'
        if _new is None:
            if line in self.data and side in self.data[line] and _item in self.data[line][side]:
                return self.data[line][side][_item]
            else:
                return None
        else:
            if line not in self.data:
                self.data[line] = dict()
            if side not in self.data[line]:
                self.data[line][side] = dict()
            self.data[line][side][_item] = _new

    def rail(self, line, side, _new=None, Z=False):
        _item = 'rail_y'
        if Z:
            _item = 'zx_rail_y'
        if _new is None:
            if line in self.data and side in self.data[line] and _item in self.data[line][side]:
                return self.data[line][side][_item]
            else:
                return None
        else:
            if line not in self.data:
                self.data[line] = dict()
            if side not in self.data[line]:
                self.data[line][side] = dict()
            self.data[line][side][_item] = _new

    def outline(self, line, kind, _new=None):
        _item_top = 'Y_carbody'
        _item_bottom = 'height_carbody'
        _item_w = 'width_carbody'
        _item_h = 'X_carbody'

        if _new is not None and hasattr(_new, '__len__'):
            if len(_new) >= 2:
                if int(_new[0]) > int(_new[1]):
                    _new[0], _new[1] = _new[1], _new[0]
                _new[1] -= _new[0]
                if line not in self.data:
                    self.data[line] = dict()
                if 'T' not in self.data[line]:
                    self.data[line]['T'] = dict()
                if kind not in self.data[line]['T']:
                    self.data[line]['T'][kind] = dict()
                self.data[line]['T'][kind][_item_top] = _new[0]
                self.data[line]['T'][kind][_item_bottom] = _new[1]
                self.data[line]['T'][kind][_item_w] = -1
                self.data[line]['T'][kind][_item_h] = -1
        else:
            if line in self.data \
                    and 'T' in self.data[line] \
                    and kind in self.data[line]['T']:
                return self.data[line]['T'][kind][_item_top], self.data[line]['T'][kind][_item_bottom] + self.data[line]['T'][kind][_item_top]
            else:
                return 0, 0

    def oneclick(self, lst_cztype, autoCalibrationParams, line, side):
        for carz in lst_cztype:
            self.data[line][side][carz]['X_carbody'] += autoCalibrationParams[0]
            self.data[line][side][carz]['Y_carbody'] += autoCalibrationParams[1]
            self.data[line][side][carz]['width_carbody'] = round(
                self.data[line][side][carz]['width_carbody'] * autoCalibrationParams[2])
            self.data[line][side][carz]['height_carbody'] = round(
                self.data[line][side][carz]['height_carbody'] * autoCalibrationParams[3])


def start():
    m = Tk()
    m.title('车型标定工具')
    main(m)
    m.mainloop()

def repaire_config():
    # 修复之前几个版本标定顶部图时的数据错误
    _calibration_file = "E:\\data\\work\\test\\CarPositionInformation_南仓_20180612_maying.config"
    a = json_handle()
    a.fromXML(_calibration_file)
    for l in a.Data.keys():
        if "T" in a.Data[l].keys():
            for ctype in a.Data[l]["T"].keys():
                o = a.Data[l]["T"][ctype]
                if o["X_carbody"] == -1 and o["width_carbody"] == -1:
                    o["height_carbody"] -= o["Y_carbody"]
                if o["X_carbody"] != -1 and o["Y_carbody"] != -1 and o["height_carbody"] == -1 and o["width_carbody"] == -1:
                    o["height_carbody"] = o["X_carbody"] - o["Y_carbody"]
                    o["X_carbody"] = -1

    a.export()


if __name__ == '__main__':
    start()
    # repaire_config()