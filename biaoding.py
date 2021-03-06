# coding=utf-8

# 自动标定流程
# 1. 解析标定文件，按照车型在图片中的位置及高度占图片的比例进行分组 （analyzeCalibrationFile -> _frequency(_getKinds))
# 2. 标定当前车型，保存 (save)
# 3. 记录标定数据并计算各项偏移值
# 4. 获取同组车型 (get_current_group)
# 5. 遍历同组车型，同时更改标定文件中的数据 (calibration.carbody)


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

class const:
    class Calibration:
        NONE_CALIBRATION = 0
        CAR_CALIBRATION = 1
        AXEL_CALIBRATION = 2
        RAIL_CALIBRATION = 3
        WHEEL_CALIBRATION = 4
        OUTLINE_CALIBRATION = 5


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
            self.drawObj = None
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
                'AXEL': [],
                'WHEEL': [],
                'RAIL': [],
                'OUTLINE': [],
                'POINT': [],
                'TEXT': [],
                'IMG': [],
                'CONSULT': [],
            }

            self.history = {
                'CAR': [],
                'AXEL': [],
                'WHEEL': [],
                'RAIL': [],
                'OUTLINE': [],
                'POINT': [],
                'TEXT': [],
                'IMG': [],
                'CONSULT': [],
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

        else:
            self.clearAllCanvas()



    def check_data_type(self, _file_name):
        if '_ZL' in _file_name or '_ZR' in _file_name:
            self.source['Z'].append(_file_name)
        elif '_T' in _file_name:
            self.source['T'].append(_file_name)
        else:
            self.source['G'].append(_file_name)

    def ui_init(self):
        self.show_size = (self.win_size[0], self.win_size[1])

        # self.canvas = tk.Canvas(self.win, bg='#C7EDCC', width=self.show_size[0], height=self.show_size[1])
        self.canvas = tk.Canvas(self.win, bg='#C7EDCC', width=self.show_size[0], height=self.show_size[1]-60)
        self.canvas.place(x=0, y=0)

        self.rootMenu = tk.Menu(self.win)
        self.rootMenu.add_command(label='加载标定', command=self.openCalibrationFile)
        self.rootMenu.add_command(label='加载图片', command=self.openPictureFolder)

        test_menu = tk.Menu(self.rootMenu, tearoff=0)
        test_menu.add_command(label='鼠标滚轮-向下：缩小')
        test_menu.add_command(label='鼠标滚轮-向上：放大')
        test_menu.add_command(label='鼠标右键：拖动')
        test_menu.add_command(label='鼠标左键：画点')
        self.rootMenu.add_cascade(label='帮助', menu=test_menu)

        about_menu = tk.Menu(self.rootMenu, tearoff=0)
        about_menu.add_command(label='开发标识：r20180521.1430')
        self.rootMenu.add_cascade(label='关于', menu=about_menu)

        self.win.config(menu=self.rootMenu)

        # Button(self.win, text="智能分组", width=10, relief=GROOVE, bg="yellow").place(x=self.show_size[0] / 2 - 415, y=self.show_size[1] - 55)
        # Button(self.win, text="定位", width=10, relief=GROOVE, bg="yellow").place(x=self.show_size[0] / 2 - 295, y=self.show_size[1] - 55)

        Button(self.win, text="导出json", width=10, relief=GROOVE, bg="yellow", command=self.save2json).place(x=self.show_size[0]/2-415, y=self.show_size[1]-55)
        Button(self.win, text="导出config", width=10, relief=GROOVE, bg="yellow", command=self.save2config).place(x=self.show_size[0]/2-295, y=self.show_size[1]-55)
        Button(self.win, text="上一张", width=10, relief=GROOVE, bg="yellow", command=self.showLastPic).place(x=self.show_size[0]/2-175, y=self.show_size[1]-55)
        Button(self.win, text="保  存", width=10, relief=GROOVE, bg="yellow", command=self.save_data).place(x=self.show_size[0]/2-50, y=self.show_size[1]-55)
        Button(self.win, text="下一张", width=10, relief=GROOVE, bg="yellow", command=self.showNextPic).place(x=self.show_size[0]/2+75, y=self.show_size[1]-55)
        Label(self.win, text="版本：2.7.0.2").place(x=0, y=self.show_size[1]-50)

        self.btn_calibration_type = Button(self.win, text="标定类型", width=10, relief=GROOVE, bg="yellow", command=self.pop_calibration_type)
        self.btn_calibration_type.place(x=self.show_size[0] / 2 + 195, y=self.show_size[1] - 55)


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
            _point = self.coords_zoom[0]
            _bbox_img = self.canvas.bbox(self.paint['IMG'][0])
            _p1 = round((_point[0] - _bbox_img[0])/self.showZoomRatio)
            _p2 = round((_point[1] - _bbox_img[1])/self.showZoomRatio)
            self.coords_zoom.clear()
            self.coords_zoom.append((_p1, _p2))


    def _point_to_zoom(self):
        if len(self.coords_zoom) > 0:
            _point = self.coords_zoom[0]
            _p1 = _point[0] * self.showZoomRatio
            _p2 = _point[1] * self.showZoomRatio
            self.coords_zoom.clear()
            self.coords_zoom.append((_p1, _p2))

    def full_to_zoom(self, l_data):
        return [d*self.showZoomRatio for d in l_data]

    def zoom_to_full(self, l_data):
        return [round(d/self.showZoomRatio) for d in l_data]

    def eCanvasMouseWheel(self, event):
        _move = [0, 0]
        if os.name == 'nt' and event.delta > 0 and not self.FULL_SCREEN:
            self.FULL_SCREEN = True
            _move = self._zoom_to_point(event.x, event.y)
            self.show()
            self.bbox_move(-_move[0], -_move[1])
            self.display_unsaved_rectangle()

        elif  os.name == 'nt' and event.delta < 0 and self.FULL_SCREEN:
            self.FULL_SCREEN = False
            self.show()
            # self.bbox_move(-_move[0], -_move[1])
            self.display_unsaved_rectangle()
        if os.name == 'posix' and event.num == 5 and self.FULL_SCREEN:
            self.FULL_SCREEN = False
            self.show()
            # self.bbox_move(-_move[0], -_move[1])
            self.display_unsaved_rectangle()
        elif  os.name == 'posix' and event.num == 4 and not self.FULL_SCREEN:
            self.FULL_SCREEN = True
            _move = self._zoom_to_point(event.x, event.y)
            self.show()
            self.bbox_move(-_move[0], -_move[1])
            self.display_unsaved_rectangle()

    def setEventBinding(self):
        self.canvas.bind('<Motion>', self.eCanvasMotion)
        # self.canvas.bind('<Button-3>', self.drag)
        self.canvas.bind('<Button-1>', self.eCanvasButton_1)
        self.canvas.bind('<ButtonRelease-1>', self.eCanvasButton_1_release)
        if os.name == 'nt':
            self.canvas.bind('<MouseWheel>', self.eCanvasMouseWheel)
        elif os.name == 'posix':
            self.canvas.bind('<Button-4>', self.eCanvasMouseWheel)
            self.canvas.bind('<Button-5>', self.eCanvasMouseWheel)
        self.canvas.bind('<B3-Motion>', self.drag)

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

    def showInfo(self):
        if self.calibrationHelper is None: return
        def getLineName(name):
            return '202.202.202.%s' % (str(int(name)+1),)
        
        top = tk.Toplevel(self.win, width=420, height=500)
        top.title('标定信息')
        _side_frame = tk.Frame(top, width=420, height=30)
        _info_frame = tk.Frame(top, width=420, height=570)
        _side_frame.place(x=0, y=0)
        _info_frame.place(x=0, y=31)
        
        lb_side = tk.Label(_side_frame, text='站点：')
        lb_side.place(x=10, y=0)
        ery_side = tk.Entry(_side_frame, width=10)
        ery_side.place(x=50, y=0)
        lb_side_info = Label(_side_frame)
        lb_side_info.place(x=100, y=0)
        infos = self.calibrationHelper.sideinfo()
        ery_side.insert(0, infos[2])
        lb_side_info.config(text='  创建日期：%s  最近修改日期：%s' % (infos[0], infos[1]))
        
        stats = self.stats(mode='info')
        tree = ttk.Treeview(_info_frame, height=20)
        tree["columns"]=("left","right")
        tree.column("left", width=100 )
        tree.column("right", width=100)
        tree.heading("left", text="左侧")
        tree.heading("right", text="右侧")
        for _keys in stats.keys():
            root = tree.insert('', 0, text=getLineName(_keys))
            for _kind in stats[_keys]:
                if '×' == _kind[1] or '×' == _kind[2]:
                    tree.insert(root, 'end', text=_kind[0], values=(_kind[1],_kind[2]), tags='warning')
                else:
                    tree.insert(root, 'end', text=_kind[0], values=(_kind[1],_kind[2]))
            iKind = len(tree.get_children(item=root))
            iLeft = [tree.item(x)['values'][0] for x in tree.get_children(item=root)].count('√')
            iRight = [tree.item(x)['values'][1] for x in tree.get_children(item=root)].count('√')
            tree.insert(root, 'end', text='总计： '+str(iKind), values=(str(iLeft),str(iRight)))
        tree.tag_configure('warning', background='orange')
        tree.pack(side=LEFT)
        trinfo = Scrollbar(_info_frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=trinfo.set)
        trinfo.pack(side=RIGHT, fill=Y)
        def _close():
            self.calibrationHelper.sideinfo(sideName=ery_side.get(), modifyDate=util._gettime(_type='file'))
            top.destroy()
        btnClose = Button(top, text='确定', command=_close, width=10)
        btnClose.place(x=230, y=465)

    def showStatus(self):
        if self.calibrationHelper is None: return
        def _getLineName(name):
            return '202.202.202.%s' % (str(int(name)+1),)
        
        top = Toplevel(self.win, width=420, height=500)
        top.title('车型状态')
        _side_frame = Frame(top, width=420, height=30)
        _info_frame = Frame(top, width=420, height=570)
        _side_frame.place(x=0, y=0)
        _info_frame.place(x=0, y=31)
        
        lb_side = Label(_side_frame, text='站点：')
        lb_side.place(x=10, y=0)
        ery_side = Entry(_side_frame, width=10)
        ery_side.place(x=50, y=0)
        lb_side_info = Label(_side_frame)
        lb_side_info.place(x=100, y=0)
        infos = self.calibrationHelper.sideinfo()
        ery_side.insert(0, infos[2])
        lb_side_info.config(text='  创建日期：%s  最近修改日期：%s' % (infos[0], infos[1]))
        
        
        stats = self.stats(mode='status')
        tree = ttk.Treeview(_info_frame, height=20)
        tree["columns"]=("left","right")
        tree.column("left", width=100 )
        tree.column("right", width=100)
        tree.heading("left", text="左侧")
        tree.heading("right", text="右侧")

        for _keys in stats.keys():
            root = tree.insert('', 0, text=_getLineName(_keys))
            for _kind in stats[_keys]:
                if '缺' in _kind[1] or '缺' in _kind[2]:
                    tree.insert(root, 'end', text=_kind[0], values=(_kind[1],_kind[2]), tags='warning')
                else:
                    tree.insert(root, 'end', text=_kind[0], values=(_kind[1],_kind[2]))
            iKind = len(tree.get_children(item=root))
            iLeft = [tree.item(x)['values'][0] for x in tree.get_children(item=root)].count('缺[缺]')
            iRight = [tree.item(x)['values'][1] for x in tree.get_children(item=root)].count('缺[缺]')
            tree.insert(root, 'end', text='总计： '+str(iKind), values=(str(iLeft),str(iRight)))
        tree.tag_configure('warning', background='orange')
        tree.pack(side=LEFT)
        trinfo = Scrollbar(_info_frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=trinfo.set)
        trinfo.pack(side=RIGHT, fill=Y)
        def _close():
            self.calibrationHelper.sideinfo(sideName=ery_side.get(), modifyDate=util._gettime(_type='file'))
            top.destroy()
        btnClose = Button(top, text='确定', command=_close, width=10)
        btnClose.place(x=230, y=465)

    def stats(self, mode='status'):
        def _filter(x):
            return x is not None
        # _stats = dict()
        # today_date = util._gettime(_type='file')
        if self.calibrationHelper is None: return
        _keys = set([x.split('_')[0] for x in self.calibrationHelper.dictPhototype.keys()])
        kinds = dict()
        for line in _keys:
            _L = sorted(filter(_filter, [x.get('cztype') for x in self.calibrationHelper.dictPhototype[line + '_L']]) ,key=lambda s:s[0])
            _R = sorted(filter(_filter, [x.get('cztype') for x in self.calibrationHelper.dictPhototype[line + '_R']]) ,key=lambda s:s[0])
            kinds[line] = sorted(set(_L) | set(_R), key=lambda s:s[0])
        if len(kinds) == 0: return ['空', '', '']
        _return = dict()
        if mode == 'info':
            for line in kinds.keys():
                _return[line] = list()
                for kind in kinds[line]:
                    _tmp = list()
                    _tmp.append(kind)
                    if self.calibrationHelper.carbody(kind, line, 'L').count(-1) != 4:
                        _tmp.append('√')
                    else:
                        _tmp.append('×')
                    if self.calibrationHelper.carbody(kind, line, 'R').count(-1) != 4:
                        _tmp.append('√')
                    else:
                        _tmp.append('×')
                    _return[line].append(_tmp)
            # print(_return)
        elif mode == 'status':
            for line in kinds.keys():
                _return[line] = list()
                for kind in kinds[line]:
                    _tmp = list()
                    _tmp.append(kind)
                    _l = self.calibrationHelper.carinfo(kind, line, 'L')
                    if _l != [None, None, None]:
                        _tmp.append('%s[%s]' % (
                            '自动' if _l[2] == 'Auto' else ('缺' if _l[2] is None else '手动'),
                             _l[1] if _l[1] is not None else '缺'))
                    _r = self.calibrationHelper.carinfo(kind, line, 'R')
                    if _r != [None, None, None]:
                        _tmp.append('%s[%s]' % (
                            '自动' if _r[2] == 'Auto' else ('缺' if _r[2] is None else '手动'),
                             _r[1] if _r[1] is not None else '缺'))
                    _return[line].append(_tmp)
            # print(_return)
        return _return


    def setCurrnetPic(self, filename):
        if os.path.exists(filename):
            self.currentPic = filename
            self.currentPicInfo = self.getPicInfo(filename)
            self.dirname = os.path.dirname(filename)

    def calc(self, mode, _bbox=None):
        if mode == const.CALC_SAVE_CALIBRATION:
            _img = self.canvas.bbox(self.paint['IMG'][0])  # 图片位置
            bbox_car = self.canvas.bbox(self.paint['CAR'][0])
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
            ret = dict()
            ret['X_carbody'] = x
            ret['Y_carbody'] = y
            ret['width_carbody'] = w
            ret['height_carbody'] = h

            return ret
        elif mode == const.CALC_READ_CALIBRATION:
            _img = self.canvas.bbox(self.paint['IMG'][0])  # 图片位置

            x1 = int(self.oldCalibrationInfo['X_carbody'] * self.showZoomRatio) + _img[0]
            y1 = int(self.oldCalibrationInfo['Y_carbody'] * self.showZoomRatio) + _img[1]
            x2 = int((self.oldCalibrationInfo['width_carbody'] + self.oldCalibrationInfo[
                'X_carbody']) * self.showZoomRatio) + _img[0]
            y2 = int((self.oldCalibrationInfo['height_carbody'] + self.oldCalibrationInfo[
                'Y_carbody']) * self.showZoomRatio) + _img[1]
            return x1, y1, x2, y2
        elif mode == const.CALC_SAVE_AUTO_CALIBRATION:
            if _bbox is not None and list(self.oldCalibrationInfo.values()).count(0) != 4:
                self.autoCalibrationParams[0] = _bbox['X_carbody'] - self.oldCalibrationInfo['X_carbody']
                self.autoCalibrationParams[1] = _bbox['Y_carbody'] - self.oldCalibrationInfo['Y_carbody']
                self.autoCalibrationParams[2] = _bbox['width_carbody'] / self.oldCalibrationInfo['width_carbody']
                self.autoCalibrationParams[3] = _bbox['height_carbody'] / self.oldCalibrationInfo['height_carbody']
            else:
                self.autoCalibrationParams[3] = [0, 0, 1, 1]

    def _get_group_kinds(self):
        return list(self.imgs_group[self.group_imgs[self.currentPic]][0].keys())



    def save2json(self):
        self.save_data()
        self.calibrationHelper.export2JSON()


    def is_unsave(self, item):
        if item==const.Calibration.CAR_CALIBRATION:
            return self.currentPic in self.source['G'] and len(self.paint['CAR']) > 0 and self.paint['CAR'][0] not in self.history['CAR']
        else:
            _Z = True if self.currentPic in self.source['Z'] else False
            if item == const.Calibration.RAIL_CALIBRATION:
                return self.currentPic not in self.source['T'] and len(self.paint['RAIL']) > 0 and self.paint['RAIL'][0] not in self.history['RAIL']
            elif item == const.Calibration.AXEL_CALIBRATION:
                return self.currentPic not in self.source['T'] and len(self.paint['AXEL']) > 0 and self.paint['AXEL'][0] not in self.history['AXEL']
            elif item == const.Calibration.WHEEL_CALIBRATION:
                return self.currentPic not in self.source['T'] and len(self.paint['WHEEL']) > 0 and self.paint['WHEEL'][0] not in self.history['WHEEL']
            elif item == const.Calibration.OUTLINE_CALIBRATION:
                return self.drawMode == const.Calibration.OUTLINE_CALIBRATION and len(self.paint['OUTLINE']) > 0 and self.paint['OUTLINE'][0] not in self.history['OUTLINE']




    def save_data(self):
        if self.is_unsave(const.Calibration.CAR_CALIBRATION):
            _group_kinds = self.get_current_group()
            _new_bbox = self.calc(mode=const.CALC_SAVE_CALIBRATION)
            self.calibrationHelper.carbody(
                self.currentPicInfo[0],
                self.currentPicInfo[1],
                self.currentPicInfo[2],
                _new=_new_bbox)
            self.saved.append('%s_%s_%s' % (self.currentPicInfo[1], self.currentPicInfo[2], self.currentPicInfo[0]))
            if list(self.oldCalibrationInfo.values()).count(-1) != 4 and self.auto_calibration_enable:
                self.calc(mode=const.CALC_SAVE_AUTO_CALIBRATION, _bbox=_new_bbox)
                _lst = [k.split('_')[2] for k in list(set(_group_kinds) & set(self.saved) ^ set(_group_kinds))]
                if len(_lst) > 0:
                    self.calibrationHelper.oneclick(_lst, self.autoCalibrationParams, self.currentPicInfo[1], self.currentPicInfo[2])
                self.autoCalibrationParams = [0, 0, 1, 1]
                self.analyzeCalibrationFile()
        _Z = True if self.currentPic in self.source['Z'] else False
        if self.is_unsave(const.Calibration.AXEL_CALIBRATION):
            self.calibrationHelper.axel(
                self.currentPicInfo[1],
                self.currentPicInfo[2],
                _new=self.axel_x_offset,
                Z=_Z)
        if self.is_unsave(const.Calibration.WHEEL_CALIBRATION):
            self.calibrationHelper.wheel(
                self.currentPicInfo[1],
                self.currentPicInfo[2],
                _new=self.axel_y,
                Z=_Z)
        if self.is_unsave(const.Calibration.RAIL_CALIBRATION):
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

    def save2config(self):
        self.save_data()
        self.calibrationHelper.export2XML()



    # def config(self, new=None):
    #     c = configparser.ConfigParser()
    #     try:
    #         # 没有配置文件则生成一个
    #         if not os.path.exists('biaoding.ini'):
    #             c.add_section('source')
    #             c.add_section('temp')
    #             c.set('source', 'calibration_file', '')
    #             c.set('source', 'pic_dir', '')
    #             c.set('temp', 'index', '0')
    #             with open('biaoding.ini', 'w') as f:
    #                 c.write(f)
    #
    #         c.read('biaoding.ini')
    #         if new is not None:
    #             c.set(new[0], new[1], new[2].encode().decode())
    #             c.write(open("biaoding.ini", "w"))
    #
    #         if os.path.exists(c.get('source', 'calibration_file')):
    #             self._file = c.get('source', 'calibration_file')
    #             self.calibrationHelper = calibration(self._file)
    #         if os.path.exists(c.get('source', 'pic_dir')):
    #             self._dir = c.get('source', 'pic_dir')
    #             self._load_pics(self._dir)
    #         if c.get('temp', 'index') != '':
    #             self.currentPicIndex = int(c.get('temp', 'index'))
    #         if new is None and self.calibrationHelper is not None:
    #             self.analyzeCalibrationFile()
    #             self.display()
    #     except Exception as e:
    #         pass


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
                        if _name[0].isprintable() and re.match(r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$", _name[1]) and \
                            _name[2].isdigit() and len(_name[2]) == 14 and (_name[3][0] in ('L', 'R', 'T') or _name[3][:2] in ('ZL', 'ZR')):
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

    def display(self, pic=None):
        if self.calibrationHelper is None:
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
        nm = list()
        with open(self.currentPic, 'rb') as f:
            for _l in f:
                if b'<Wheel1 = ' in _l:
                    tmp = _l.split(b'<Error =')
                    for k in tmp[1].split(b'<'):
                        if b'Wheel' in k:
                            nm.append(int(k[9:k.index(ord('>'))]))
                    break
        # print(nm)
        return nm

    def getExtName(self, _filepath, toget='ex'):
        import os
        _filename = _filepath  # 纯文件名，不带路径
        if os.name == 'posix':
            _filename = _filepath.split('/')[len(_filepath.split('/')) - 1]
        elif os.name == 'nt':
            if _filepath.find('\\') != 0:
                _tmp = _filepath.split('\\')
                _filename = _tmp[len(_tmp) - 1]  # 含扩展名
        if toget == 'jpginfo':
            _file = _filename.split('_')
            _line = 0
            if _file[1] == '202.202.202.2':
                _line = 1
            elif _file[1] == '202.202.202.3':
                _line = 2
            return (_file[0], _line, _file[3][0])
        elif toget == 'ex':
            _file = _filename.split('.')
            return _file[len(_file) - 1].upper()

    def getPicInfo(self, pic):
        try:
            _lst = os.path.basename(pic).split('_')
            _kind = _lst[0]
            _line = str(int(_lst[1].split('.')[3])-1)
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
            self.displayOutline()
        else:
            if self.currentPic in self.source['G']:
                self.displayCarCalibration()
            self.displayAxelCalibration()
            self.displayRailCalibration()

    def display_unsaved_rectangle(self):
        _bbox = self.canvas.bbox(self.paint['IMG'][0])
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
        _info = '(%s/%s) %s %s' % (
            str(self.currentPicIndex + 1),
            len(self.show_pics),
            self.currentPic,
            '【新增】' if list(self.oldCalibrationInfo.values()).count(-1) == 4 or list(self.oldCalibrationInfo.values()).count(0) == 4 else ''
        )
        self.win.title(_info)

    def displayCarCalibration(self):
        self.oldCalibrationInfo = self.calibrationHelper.carbody(self.currentPicInfo[0], self.currentPicInfo[1], self.currentPicInfo[2])
        self.update_title()
        #print('exists carbody >>> ',self.oldCalibrationInfo)
        if not self.FULL_SCREEN:
            _car = self.calc(mode=const.CALC_READ_CALIBRATION)
            # _car = self.handleCoords(const.CAR_CALIBRATION_READ, self.canvas.bbox(self.paint['IMG'][0]))
            if _car.count(-1) != 4:  # 不为初始值
                x1, y1, x2, y2 = _car
                _x1 = self.show_size[0]/2 - round(self.oldCalibrationInfo['width_carbody'] * self.showZoomRatio /2)
                _x2 = x2 - x1
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

    def displayAxelCalibration(self):
        _side = self.currentPicInfo[2]
        _line = str(self.currentPicInfo[1])
        _w = self.origin_img.size[0]
        _bbox_img = self.canvas.bbox(self.paint['IMG'][0])
        _wheelInfo = self._getpicwheelinfo()
        _Z = True if self.currentPic in self.source['Z'] else False
        _offset = int(self.calibrationHelper.axel(_line, _side, Z=_Z))
        _wheel = int(self.calibrationHelper.wheel(_line, _side, Z=_Z))
        _lst_axel = _wheelInfo[:len(_wheelInfo) - _wheelInfo.count(-1)]
        if _side == 'R':
            _lst_axel.reverse()
            _lst_axel = [_w - x for x in _lst_axel]
        for _axel in _lst_axel:
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
        if not self.FULL_SCREEN:
            wheel_id = self.canvas.create_line(
                0,
                _wheel * self.showZoomRatio + _bbox_img[1],
                _bbox_img[2],
                _wheel * self.showZoomRatio + _bbox_img[1],
                width=2,
                fill='green'
            )
            self.paint['WHEEL'].append(wheel_id)
            self.history['WHEEL'].append(wheel_id)
        else:
            wheel_id = self.canvas.create_line(
                0,
                _wheel + _bbox_img[1],
                _bbox_img[2],
                _wheel + _bbox_img[1],
                width=2,
                fill='green'
            )
            self.paint['WHEEL'].append(wheel_id)
            self.history['WHEEL'].append(wheel_id)

    def displayOutline(self):
        self.cleanCanvasByType(self.paint['OUTLINE'], self.canvas)
        _line = str(self.currentPicInfo[1])
        _kind = str(self.currentPicInfo[0])
        _outlines = self.calibrationHelper.outline(_line, _kind)
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
                    _outline *self.showZoomRatio + self.imgPosition[1],
                    self.imgPosition[2],
                    _outline *self.showZoomRatio + self.imgPosition[1],
                    width=2,
                    fill='yellow')
                self.paint['OUTLINE'].append(outline_id)
                self.history['OUTLINE'].append(outline_id)

    def displayRailCalibration(self):
        _side = self.currentPicInfo[2]
        _line = str(self.currentPicInfo[1])
        _Z = True if self.currentPic in self.source['Z'] else False
        _bbox_img = self.canvas.bbox(self.paint['IMG'][0])
        _raily = int(self.calibrationHelper.rail(_line, _side, Z=_Z))
        #print('getrail() = %d' % (_raily,))
        if _raily != -1:
            if not self.FULL_SCREEN:
                rail_id = self.canvas.create_line(
                    0,
                    _raily * self.showZoomRatio + _bbox_img[1],
                    _bbox_img[2],
                    _raily * self.showZoomRatio + _bbox_img[1],
                    width = 2,
                    fill = 'blue'
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

    def showLastPic(self):
        if -1 < self.currentPicIndex - 1 < len(self.show_pics):
            self.currentPicIndex -= 1
            self.setCurrnetPic(self.show_pics[self.currentPicIndex])
            self.show()
            self.update_title()
            
    def setCarCalibration(self):
        self.drawMode = const.Calibration.CAR_CALIBRATION
        if self.btn_calibration_type is not None:
            self.btn_calibration_type.config(text='车厢标定')
        self.current_actived_menu = None

    def setOutlineCalibration(self):
        self.drawMode = const.Calibration.OUTLINE_CALIBRATION
        if self.btn_calibration_type is not None:
            self.btn_calibration_type.config(text='轮廓标定')
        self.current_actived_menu = None

    def setAxelCalibration(self):
        self.drawMode = const.Calibration.AXEL_CALIBRATION
        if self.btn_calibration_type is not None:
            self.btn_calibration_type.config(text='车轴标定')
        self.current_actived_menu = None


    def setRailCalibration(self):
        self.drawMode = const.Calibration.RAIL_CALIBRATION
        if self.btn_calibration_type is not None:
            self.btn_calibration_type.config(text='铁轨标定')
        self.current_actived_menu = None

    def setWheelCalibration(self):
        self.drawMode = const.Calibration.WHEEL_CALIBRATION

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

    # def eCanvasButton_3(self, event):


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
                popmenu.post(round(self.show_size[0] / 2 + 195), round(self.show_size[1] - 80))
            if self.currentPic in self.source['Z']:
                popmenu.add_command(label='  车 轴 标 定 ', command=self.setAxelCalibration)
                popmenu.add_command(label='  铁 轨 标 定 ', command=self.setRailCalibration)
                popmenu.post(round(self.show_size[0] / 2 + 195), round(self.show_size[1] - 60))
            if self.currentPic in self.source['T']:
                popmenu.add_command(label='  轮 廓 标 定 ', command=self.setOutlineCalibration)
                popmenu.post(round(self.show_size[0] / 2 + 195), round(self.show_size[1] - 40))

    def eCanvasButton_1(self, event):
      #print('click -> ', event.x, event.y)
        # print('%s %s -> %s' % (sys.platform, os.name, event.state))

        # if os.name == 'nt' and event.state != 8:
        #     return
        # if os.name == 'posix' and event.state != 0:
        #     return
        _bbox = self.canvas.bbox(self.paint['IMG'][0])

        if self.drawMode == const.Calibration.CAR_CALIBRATION:
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
        elif self.drawMode == const.Calibration.AXEL_CALIBRATION:
            self.cleanCanvasByType(self.paint['AXEL'], self.canvas)
            self.cleanCanvasByType(self.paint['WHEEL'], self.canvas)
            _side = self.currentPicInfo[2]
            _w = self.origin_img.size[0]
            self.paint['WHEEL'].append(
                self.canvas.create_line(_bbox[0], event.y, _bbox[2], event.y, width=2, fill='yellow')
            )
            if not self.FULL_SCREEN:
                self.axel_y = round((event.y - self.canvas.bbox(self.paint['IMG'][0])[1]) / self.showZoomRatio)
            else:
                self.axel_y = event.y - self.canvas.bbox(self.paint['IMG'][0])[1]

            _wheel = self._getpicwheelinfo()
            _lst_axel = _wheel[:len(_wheel)-_wheel.count(-1)]

            if len(_lst_axel) > 0:
                if _side == 'R':
                    _lst_axel.reverse()
                    _lst_axel = [_w - x for x in _lst_axel]
                    if not self.FULL_SCREEN:
                        _x_offset = round(_lst_axel[0]*self.showZoomRatio) - event.x
                    else:
                        _x_offset = _lst_axel[0] - event.x
                if _side == 'L':
                    if not self.FULL_SCREEN:
                        _x_offset = round(_lst_axel[2]*self.showZoomRatio) - event.x
                    else:
                        _x_offset = _lst_axel[2] - event.x
                if not self.FULL_SCREEN:
                    self.axel_x_offset = round((_x_offset + _bbox[0])/self.showZoomRatio)
                else:
                    self.axel_x_offset = _x_offset + _bbox[0]
                for _axel in _lst_axel:
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
        elif self.drawMode == const.Calibration.RAIL_CALIBRATION:
            self.cleanCanvasByType(self.paint['RAIL'], self.canvas)
            if not self.FULL_SCREEN:
                self.rail_y = round((event.y - self.canvas.bbox(self.paint['IMG'][0])[1]) / self.showZoomRatio)
            else:
                self.rail_y = event.y - self.canvas.bbox(self.paint['IMG'][0])[1]
            self.paint['RAIL'].append(
                self.canvas.create_line(0, event.y, self.show_img.size[0], event.y, width=2, fill='blue')
            )
        elif self.drawMode == const.Calibration.OUTLINE_CALIBRATION:
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


  
        # if self.display_mode == DISPLAY_MODE_ZOOM:
        #     if self.drawMode == CAR_CALIBRATION:
        #         if len(self.coords) == 0:
        #             self.coords.append((event.x, event.y))
        #         else:
        #             self.coords.clear()
        #             self.coords.append((event.x, event.y))
        #     elif self.drawMode == AXEL_CALIBRATION:
        #         self.cleanCanvasByType(self.paint['AXEL'], self.canvas)
        #         self.cleanCanvasByType(self.paint['WHEEL'], self.canvas)
        #         _side = self.currentPicInfo[2]
        #         _line = str(self.currentPicInfo[1])
        #         _kind = self.currentPicInfo[0]
        #         _w = self.origin_img.size[0]
        #         self.paint['WHEEL'].append(
        #             self.canvas.create_line(0, event.y, self.imgPosition[2], event.y, width=2, fill='yellow')
        #         )
        #         self.axel_y = round((event.y - self.imgPosition[1]) / self.showZoomRatio)
                
        #         _wheel = self._getpicwheelinfo()
        #         _lst_axel = _wheel[:len(_wheel)-_wheel.count(-1)]
        #         if _side == 'R':
        #             _lst_axel.reverse()
        #             _lst_axel = [_w - x for x in _lst_axel]
        #             _x_offset = round(_lst_axel[0]*self.showZoomRatio) - event.x
        #         if _side == 'L':
        #             _x_offset = round(_lst_axel[2]*self.showZoomRatio) - event.x
        #         self.axel_x_offset = round(_x_offset/self.showZoomRatio)
        #         for _axel in _lst_axel:
        #             self.paint['AXEL'].append(self.canvas.create_line(
        #                 (round(_axel*self.showZoomRatio) - _x_offset,
        #                 self.show_img.size[1] + self.imgPosition[1]),
        #                 (round(_axel*self.showZoomRatio) - _x_offset,
        #                 self.imgPosition[1]), width=2, fill='yellow'))
        #     elif self.drawMode == RAIL_CALIBRATION:
        #         self.cleanCanvasByType(self.paint['RAIL'], self.canvas)
        #         self.rail_y = round((event.y - self.imgPosition[1]) / self.showZoomRatio)
        #         self.paint['RAIL'].append(
        #             self.canvas.create_line(0, event.y, self.show_img.size[0], event.y, width=2, fill='blue')
        #         )
        #     elif self.drawMode == OUTLINE_CALIBRATION:
        #         if self.outlines[0] != 0 and self.outlines[1] != 0 or len(self.paint['OUTLINE']) > 1:
        #             self.outlines[0] = 0
        #             self.outlines[1] = 0
        #             self.cleanCanvasByType(self.paint['OUTLINE'], self.canvas)
        #         if self.outlines[0] == 0:
        #             self.outlines[0] = round((event.y - self.imgPosition[1]) / self.showZoomRatio)
        #         elif self.outlines[1] == 0:
        #             self.outlines[1] = round((event.y - self.imgPosition[1]) / self.showZoomRatio)
        #         # print(self.outlines)
        #         self.paint['OUTLINE'].append(
        #             self.canvas.create_line(0, event.y, self.show_img.size[0], event.y, width=2, fill='blue')
        #         )
        #     elif self.drawMode == OUTLINE_CALIBRATION2:
        #         if self.outlines[2] != 0 or len(self.OUTLINE_MIDDLE_ID) > 0:
        #             self.outlines[2] = 0
        #             self.cleanCanvasByType(self.OUTLINE_MIDDLE_ID, self.canvas)
        #         if self.outlines[2] == 0:
        #             self.outlines[2] = round((event.y - self.imgPosition[1]) / self.showZoomRatio)
        #         # print(self.outlines)
        #         self.OUTLINE_MIDDLE_ID.append(
        #             self.canvas.create_line(0, event.y, self.show_img.size[0], event.y, width=2, fill='blue')
        #         )

        # elif self.display_mode == DISPLAY_MODE_ORIGIN:
        #     if self.drawMode == 1:
        #         if self.CTRL_ENABLE: return
        #         self.coords.append((event.x, event.y))
        #         if len(self.coords) >= 2:
        #             self.cleanCanvasByType(self.paint['CAR'], self.canvas)
        #             _new = self.canvas.create_rectangle(
        #                 # self.coords[0][0] + bbox[0], self.coords[0][1] + bbox[1],
        #                 self.coords[0][0], self.coords[0][1],
        #                 event.x, event.y,
        #                 width=2,
        #                 outline='red'
        #             )
        #             self.paint['CAR'].append(_new)
        #             # print('img > ', self.canvas.bbox(self.paint['IMG'][0]))
        #             # print('add > ', self.canvas.bbox(_new))
        #             self.coords.clear()

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
            json.dump(self.data, fpWrite)

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
            _item = 'ztrain_axle_xoffset'
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
            _item = 'ztrain_axle_y'
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
            _item = 'zrail_y'
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
        _item_bottom = 'X_carbody'
        _item_w = 'width_carbody'
        _item_h = 'height_carbody'

        if _new is not None and hasattr(_new, '__len__'):
            if len(_new) >= 2:
                if int(_new[0]) > int(_new[1]):
                    _new[0], _new[1] = _new[1], _new[0]
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
                return self.data[line]['T'][kind][_item_top], self.data[line]['T'][kind][_item_bottom]
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


if __name__ == '__main__':
    start()
    # test()