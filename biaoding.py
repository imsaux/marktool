# coding=utf-8
import codecs
import datetime
from xml.etree import ElementTree as ET
import PIL.Image as pilImage
# import PIL.ImageDraw as pilImgDraw
import PIL.ImageTk as pilImgTk
from tkinter.filedialog import *
import tkinter.ttk as ttk
import tkinter as tk
import ctypes
import configparser
import logging
import inspect

class const:
    NONE_CALIBRATION = 0
    CAR_CALIBRATION = 1
    AXEL_CALIBRATION = 2
    RAIL_CALIBRATION = 3
    WHEEL_CALIBRATION = 4
    OUTLINE_CALIBRATION = 5
    OUTLINE_CALIBRATION2 = 6

    DATA_TYPE_Z = 31
    DATA_TYPE_G = 32
    DATA_TYPE_T = 33

    CALC_SAVE_CALIBRATION = 41
    CALC_READ_CALIBRATION = 42

    SHOW_MODE_ORIGIN = 51
    SHOW_MODE_ZOOM = 52

    DRAW_MODE_NONE = 61
    DRAW_MODE_CALIBRATION = 62
    DRAW_MODE_AXEL = 63
    DRAW_MODE_WHEEL = 64
    DRAW_MODE_RAIL = 65
    DRAW_MODE_OUTLINE = 66

    MARK_MODE_ALL = 71
    MARK_MODE_AUTO = 72

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
        self.currentPic = None
        self.currentPicInfo = list()
        self.currentMenu = None
        self.currentPicIndex = 0
        self.origin_img = None
        self.show_img = None
        self.showZoomRatio = 1
        self.group_imgs = dict()
        self.imgs_group = dict()
        self.picGroups = None
        self.calibrationFile = None
        self.auto_calibration_enable = True
        self.drawMode = 0
        self.showoffset = 0, 0
        self.drawObj = None
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
            'POINT':[],
            'TEXT': [],
            'IMG': [],
            'CONSULT': [],
        }

        self.history= {
            'CAR': [],
            'AXEL': [],
            'WHEEL': [],
            'RAIL': [],
            'OUTLINE': [],
            'POINT':[],
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
        self._file = sys.path[0]
        self._dir = sys.path[0]
        self._index = 0
        self.saved = list()

        if init:
            self.show_pics = list()
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

        self.canvas = tk.Canvas(self.win, bg='#C7EDCC', width=self.show_size[0], height=self.show_size[1])
        self.canvas.place(x=0, y=0)

        self.rootMenu = tk.Menu(self.win)
        self.rootMenu.add_command(label='读取标定', command=self.openCalibrationFile)
        self.rootMenu.add_command(label='读取图片', command=self.openPictureFolder)
        self.rootMenu.add_command(label='上一张', command=self.showLastPic)
        self.rootMenu.add_command(label='下一张', command=self.showNextPic)
        self.rootMenu.add_command(label='保存', command=self.save)

        test_menu = tk.Menu(self.rootMenu, tearoff=0)
        test_menu.add_command(label='鼠标滚轮-向下：缩小')
        test_menu.add_command(label='鼠标滚轮-向上：放大')
        test_menu.add_command(label='鼠标右键：选择标定类型',)
        test_menu.add_command(label='鼠标左键：画点',)
        test_menu.add_command(label='Ctrl + 鼠标左键：拖动',)
        self.rootMenu.add_cascade(label='帮助', menu=test_menu)
        self.rootMenu.add_command(label='版本：r20180130.1721')

        self.win.config(menu=self.rootMenu)

        self.setEventBinding()

    def create_group_menu(self):
        dct = self.imgs_group[self.group_imgs[self.currentPic]][0]
        carriage_menu = tk.Menu(self.rootMenu, tearoff=0)
        self.rootMenu.add_cascade(label='智能分组', menu=carriage_menu)


    def _zoom_to_point(self, x, y):
        # (0, 0, w, h)
        _bbox = self.canvas.bbox(self.paint['IMG'][0])
        pic_x = (x - _bbox[0]) / self.showZoomRatio
        pic_y = (y - _bbox[1]) / self.showZoomRatio
        move_x = pic_x - round(self.show_size[0]* (x / self.show_size[0]))
        move_y = pic_y - round(self.show_size[1]* (y / self.show_size[1]))
        return move_x, move_y

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
            _bbox_img = self.canvas.bbox(self.paint['IMG'][0])
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
        if os.name == 'posix' and event.num == 4 and self.FULL_SCREEN:
            self.FULL_SCREEN = False
            self.show()
            # self.bbox_move(-_move[0], -_move[1])
            self.display_unsaved_rectangle()
        elif  os.name == 'posix' and event.num == 5 and not self.FULL_SCREEN:
            self.FULL_SCREEN = True
            _move = self._zoom_to_point(event.x, event.y)
            self.show()
            self.bbox_move(-_move[0], -_move[1])
            self.display_unsaved_rectangle()


    # todo 分车型标定（使用该功能后，将每种车型仅显示一张）
    # todo 定位至最近的新增车型



    def setEventBinding(self):
        self.canvas.bind('<Motion>', self.eCanvasMotion)
        self.canvas.bind('<Button-3>', self.eCanvasButton_3)
        self.canvas.bind('<Button-1>', self.eCanvasButton_1)
        self.canvas.bind('<ButtonRelease-1>', self.eCanvasButton_1_release)
        if os.name == 'nt':
            self.canvas.bind('<MouseWheel>', self.eCanvasMouseWheel)
        elif os.name == 'posix':
            self.canvas.bind('<Button-4>', self.eCanvasMouseWheel)
            self.canvas.bind('<Button-5>', self.eCanvasMouseWheel)
        # self.win.bind('<KeyRelease>', self.eKeyChanged)
        # self.win.bind('<Key>', self.eKeyChanged)
        self.canvas.bind('<Control-B1-Motion>', self.drag)

    def eKeyChanged(self, event):
        print(event.keycode)
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
        if event.state != 268:
            return

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

    def calc(self, mode, x=0, y=0, w=0, h=0, algo=None):
        if  mode == const.CALC_SAVE_CALIBRATION:
            _img = self.canvas.bbox(self.paint['IMG'][0])  # 图片位置
            bbox_car = self.canvas.bbox(self.paint['CAR'][0])
            x = round((bbox_car[0] - _img[0]) / self.showZoomRatio)
            y = round((bbox_car[1] - _img[1]) / self.showZoomRatio)
            w = round((bbox_car[2] - _img[0]) / self.showZoomRatio - x)
            h = round((bbox_car[3] - _img[1]) / self.showZoomRatio - y)
            return x, y, w, h
        elif mode == const.CALC_READ_CALIBRATION:
            x1 = int(self.oldCalibrationInfo[0] * self.showZoomRatio) + x
            y1 = int(self.oldCalibrationInfo[1] * self.showZoomRatio) + y
            x2 = int((self.oldCalibrationInfo[2] + self.oldCalibrationInfo[0]) * self.showZoomRatio) + x
            y2 = int((self.oldCalibrationInfo[3] + self.oldCalibrationInfo[1]) * self.showZoomRatio) + y
            return x1, y1, x2, y2
        else:
            return x, y, w, h

    def _get_group_kinds(self):
        return list(self.imgs_group[self.group_imgs[self.currentPic]][0].keys())


    def save(self):

        # todo 自动标定如何过滤影响车型
        _Z = True if self.currentPic in self.source['Z'] else False
        if self.currentPic in self.source['G'] and len(self.paint['CAR']) > 0 and self.paint['CAR'][0] not in self.history['CAR']:
            # x, y, w, h = self.calc(const.CALC_SAVE_CALIBRATION)
            bbox_car = self.canvas.bbox(self.paint['CAR'][0])
            _img = self.canvas.bbox(self.paint['IMG'][0])
            _group_kinds = self.get_current_group()

            if not self.FULL_SCREEN:
                x = round((bbox_car[0] - _img[0])/self.showZoomRatio)
                y = round((bbox_car[1] - _img[1])/self.showZoomRatio)
                w = round((bbox_car[2] - _img[0])/self.showZoomRatio) - x
                h = round((bbox_car[3] - _img[1])/self.showZoomRatio) - y
            else:
                x = bbox_car[0] - _img[0]
                y = bbox_car[1] - _img[1]
                w = bbox_car[2] - _img[0] - x
                h = bbox_car[3] - _img[1] - y
            self.calibrationHelper.carbody(
                self.currentPicInfo[0],
                self.currentPicInfo[1],
                self.currentPicInfo[2],
                _new=(x, y, w, h))

            self.saved.append('%s_%s_%s' % (self.currentPicInfo[1], self.currentPicInfo[2], self.currentPicInfo[0]))
            if self.oldCalibrationInfo.count(-1) != 4 and self.auto_calibration_enable:
                self.autoCalibrationParams[0] = x - self.oldCalibrationInfo[0]
                self.autoCalibrationParams[1] = y - self.oldCalibrationInfo[1]
                self.autoCalibrationParams[2] = w / self.oldCalibrationInfo[2]
                self.autoCalibrationParams[3] = h / self.oldCalibrationInfo[3]
                _lst = [k.split('_')[2] for k in list(set(_group_kinds) & set(self.saved) ^ set(_group_kinds))]
                if len(_lst) > 0:
                    self.calibrationHelper.oneclick(_lst, self.autoCalibrationParams, self.currentPicInfo[1], self.currentPicInfo[2])
                self.autoCalibrationParams = [0, 0, 1, 1]
                self.analyzeCalibrationFile()
        if self.currentPic not in self.source['T'] and len(self.paint['AXEL']) > 0 and self.paint['AXEL'][0] not in self.history['AXEL']:
            self.calibrationHelper.axel(
                self.currentPicInfo[1], 
                self.currentPicInfo[2], 
                _new=self.axel_x_offset,
                Z=_Z)
        if self.currentPic not in self.source['T'] and len(self.paint['WHEEL']) > 0 and self.paint['WHEEL'][0] not in self.history['WHEEL']:
            self.calibrationHelper.wheel(
                self.currentPicInfo[1], 
                self.currentPicInfo[2], 
                _new=self.axel_y,
                Z=_Z)
        if self.currentPic not in self.source['T'] and len(self.paint['RAIL']) > 0 and self.paint['RAIL'][0] not in self.history['RAIL']:
            self.calibrationHelper.rail(
                self.currentPicInfo[1], 
                self.currentPicInfo[2], 
                _new=self.rail_y,
                Z=_Z)
        if self.drawMode == const.OUTLINE_CALIBRATION and len(self.paint['OUTLINE']) > 0 and self.paint['OUTLINE'][0] not in self.history['OUTLINE']:
            self.calibrationHelper.outline(
                self.currentPicInfo[1],
                self.currentPicInfo[0],
                _new=self.outlines)
        self.display(pic=self.currentPic)

    def config(self, new=None):
        c = configparser.ConfigParser()
        try:
            c.read('biaoding.ini')
            if new is not None:
                c.set(new[0], new[1], new[2].encode().decode())
                c.write(open("biaoding.ini", "w"))

            if os.path.exists(c.get('source', 'calibration_file')):
                self._file = c.get('source', 'calibration_file')
                self.calibrationHelper = calibration(self._file)
            if os.path.exists(c.get('source', 'pic_dir')):
                self._dir = c.get('source', 'pic_dir')
                self._load_pics(self._dir)
            if c.get('temp', 'index') != '':
                self.currentPicIndex = int(c.get('temp', 'index'))
            if new is None and self.calibrationHelper is not None:
                self.analyzeCalibrationFile()
                self.display()
        except Exception as e:
            pass

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
                        self.check_data_type(os.path.join(root, f))

    def openPictureFolder(self):
        self.drawMode = const.NONE_CALIBRATION
        dirpath = askdirectory(initialdir=self._dir, title='请选择图片文件夹')
        if dirpath not in ['', '.'] and os.path.exists(dirpath):
            self.config(new=('source', 'pic_dir', dirpath))
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
            if pic is None and 0 <= self.currentPicIndex <=len(self.show_pics) - 1:
                self.setCurrnetPic(self.show_pics[self.currentPicIndex])
            else:
                self.setCurrnetPic(pic)
            self.show()

    def openCalibrationFile(self):
        self.isCalibrationFileReady = False
        self.data_init(init=False)
        _file_path = os.path.normpath(askopenfilename(initialdir=self._file, title='请选择标定文件'))
        if _file_path.split('.')[-1] == 'config' and os.path.exists(_file_path):
            self.config(new=('source', 'calibration_file', _file_path))
            self.calibrationHelper = calibration(_file_path)
            self.handleCarPositionfile()
            if self.calibrationHelper is not None:
                self.display()

    def handleCarPositionfile(self):
        self.analyzeCalibrationFile()

    def get_current_group(self):
        _picInfo = self.getPicInfo(self.currentPic)
        _group_key = '%s_%s' % (str(_picInfo[1]), _picInfo[2])
        _algorGroup = self.algor_y_h(_group_key, [_picInfo[0]])
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
            # print(_file[0], _line, _file[3][0])
            return (_file[0], _line, _file[3][0])
        elif toget == 'ex':
            _file = _filename.split('.')
            return _file[len(_file) - 1].upper()

    def getPicInfo(self, pic):
        # print(pic)
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
            # print('exception')
            # print(pic)
            # print(_lst)
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
            '【新增】' if self.oldCalibrationInfo.count(-1) == 4 else ''
        )
        self.win.title(_info)

    def displayCarCalibration(self):
        self.oldCalibrationInfo = self.calibrationHelper.carbody(self.currentPicInfo[0], self.currentPicInfo[1], self.currentPicInfo[2])
        self.update_title()
        #print('exists carbody >>> ',self.oldCalibrationInfo)
        if not self.FULL_SCREEN:
            _car = self.calc(
                const.CALC_READ_CALIBRATION,
                x=self.canvas.bbox(self.paint['IMG'][0])[0],
                y=self.canvas.bbox(self.paint['IMG'][0])[1],
            )
            # _car = self.handleCoords(const.CAR_CALIBRATION_READ, self.canvas.bbox(self.paint['IMG'][0]))
            if _car.count(-1) != 4:  # 不为初始值
                x1, y1, x2, y2 = _car
                _x1 = self.show_size[0]/2 - round(self.oldCalibrationInfo[2] * self.showZoomRatio /2)
                _x2 = x2 - x1
                car_id = self.canvas.create_rectangle(x1, y1, x2, y2, width=2, outline='orange')
                self.paint['CAR'].append(car_id)
                self.history['CAR'].append(car_id)
        else:
            x1 = self.oldCalibrationInfo[0]
            y1 = self.oldCalibrationInfo[1]
            x2 = self.oldCalibrationInfo[2] + x1
            y2 = self.oldCalibrationInfo[3] + y1
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
            self.config(new=('temp', 'index', str(self.currentPicIndex)))
            self.coords_zoom.clear()
            self.coords_full.clear()
            self.display()
            self.update_title()

    def showLastPic(self):
        if -1 < self.currentPicIndex - 1 < len(self.show_pics):
            self.currentPicIndex -= 1
            self.config(new=('temp', 'index', str(self.currentPicIndex)))
            self.coords_zoom.clear()
            self.coords_full.clear()
            self.display()
            self.update_title()
            
    def setCarCalibration(self):
        self.drawMode = const.CAR_CALIBRATION

    def setOutlineCalibration(self):
        self.drawMode = const.OUTLINE_CALIBRATION

    def setOutlineCalibration2(self):
        self.drawMode = const.OUTLINE_CALIBRATION2

    def setAxelCalibration(self):
        self.drawMode = const.AXEL_CALIBRATION

    def setRailCalibration(self):
        self.drawMode = const.RAIL_CALIBRATION

    def setWheelCalibration(self):
        self.drawMode = const.WHEEL_CALIBRATION

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

    def eCanvasButton_3(self, event):
        self._clear_menu()
        popmenu = Menu(self.canvas, tearoff=0)
        self.current_actived_menu = popmenu
        
        if self.currentPic in self.source['G']:
            popmenu.add_command(label='车厢标定', command=self.setCarCalibration)
            popmenu.add_command(label='车轴标定', command=self.setAxelCalibration)
            popmenu.add_command(label='铁轨标定', command=self.setRailCalibration)
        if self.currentPic in self.source['Z']:
            popmenu.add_command(label='车轴标定', command=self.setAxelCalibration)
            popmenu.add_command(label='铁轨标定', command=self.setRailCalibration)
        if self.currentPic in self.source['T']:
            popmenu.add_command(label='轮廓标定', command=self.setOutlineCalibration)
            popmenu.add_command(label='中线标定', command=self.setOutlineCalibration2)
        popmenu.post(event.x_root, event.y_root)

    def eCanvasButton_1(self, event):
      #print('click -> ', event.x, event.y)
        if event.state != 8:
            return
        _bbox = self.canvas.bbox(self.paint['IMG'][0])

        if self.drawMode == const.CAR_CALIBRATION:
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
        elif self.drawMode == const.AXEL_CALIBRATION:
            self.cleanCanvasByType(self.paint['AXEL'], self.canvas)
            self.cleanCanvasByType(self.paint['WHEEL'], self.canvas)
            _side = self.currentPicInfo[2]
            _w = self.origin_img.size[0]
            self.paint['WHEEL'].append(
                self.canvas.create_line(0, event.y, self.canvas.bbox(self.paint['IMG'][0])[2], event.y, width=2, fill='yellow')
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
        elif self.drawMode == const.RAIL_CALIBRATION:
            self.cleanCanvasByType(self.paint['RAIL'], self.canvas)
            if not self.FULL_SCREEN:
                self.rail_y = round((event.y - self.canvas.bbox(self.paint['IMG'][0])[1]) / self.showZoomRatio)
            else:
                self.rail_y = event.y - self.canvas.bbox(self.paint['IMG'][0])[1]
            self.paint['RAIL'].append(
                self.canvas.create_line(0, event.y, self.show_img.size[0], event.y, width=2, fill='blue')
            )
        elif self.drawMode == const.OUTLINE_CALIBRATION:
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
        计算频率分布
        :param lst_value: 
        :return: 
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

    def analyzeCalibrationFile(self):
        for _line in self.calibrationHelper.dictPhototype.keys():
            if '_' not in _line:
                continue
            _group = self._getKinds(_line, self.algor_y_h)
            self.groupByCalibration[_line] = self._frequency(_group)

    def _getKinds(self, _line, func):
        _kinds = list()
        for kind in self.calibrationHelper.dictPhototype[_line]:
            if kind.tag != 'carcz' or kind.get('cztype') == '': continue
            _kinds.append(str(kind.get('cztype')))
        return func(_line, _kinds)
    
    def algor_y_h(self, _line, kinds):
        vals = dict()
        _l = _line.split('_')[0]
        _s = _line.split('_')[1]
        for kind in kinds:
            if '#' in kind:
                _curkind = kind.replace('#', '*')
            else:
                _curkind = kind
            carbody = self.calibrationHelper.carbody(_curkind, _l, _s)
            if carbody is None or carbody.count(-1) == 4: 
                try:
                    vals[_curkind[0]].append((_curkind, None))
                except KeyError:
                    vals[_curkind[0]] = [(_curkind, None),]
            else:
                y = int(carbody[1]) / 2048
                h = int(carbody[3]) / 2048
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


class calibration():
    def __init__(self, calibrationFile):
        self.calibrationFile = calibrationFile
        self.tree = None
        self.dictPhototype = dict()
        self.init()
        
    def init(self):
        try:
            with codecs.open(self.calibrationFile, 'r', 'gbk') as f:
                text = re.sub(u"[\x00-\x08\x0b-\x0c\x0e-\x1f]+", u"", f.read())
                self.tree = ET.ElementTree(ET.fromstring(text))
        except ET.ParseError:
            self.build(0, lineTag='1', lTag='L', rTag='R', tTag='T')
        finally:
            self.readxml()
            # self.sideinfo()

    def build(self, level, lineTag=None, lTag=None, rTag=None, tTag=None):
        if level == 0:
            _ImagingProperties = ET.Element('ImagingProperties')
            if lineTag is not None:
                _CameraPosition = ET.SubElement(_ImagingProperties, 'CameraPosition')
                _CameraPosition.set('line', lineTag)
                if lTag is not None:
                    _lphototype = ET.SubElement(_CameraPosition, 'phototype')
                    _lphototype.set('imgtype', lTag)
                if tTag is not None:
                    _lphototype = ET.SubElement(_CameraPosition, 'phototype')
                    _lphototype.set('imgtype', tTag)
                if rTag is not None:
                    _rphototype = ET.SubElement(_CameraPosition, 'phototype')
                    _rphototype.set('imgtype', rTag)
            # self.calibrationFile = 'e:/tmp_calibrationfile.config'
            self.tree = ET.ElementTree(element=_ImagingProperties)
        elif level == 1:
            root = self.tree.getroot()
            if lineTag is not None:
                _CameraPosition = ET.SubElement(root, 'CameraPosition')
                _CameraPosition.set('line', lineTag)
                if lTag is not None:
                    _lphototype = ET.SubElement(_CameraPosition, 'phototype')
                    _lphototype.set('imgtype', lTag)
                if tTag is not None:
                    _lphototype = ET.SubElement(_CameraPosition, 'phototype')
                    _lphototype.set('imgtype', tTag)
                if rTag is not None:
                    _rphototype = ET.SubElement(_CameraPosition, 'phototype')
                    _rphototype.set('imgtype', rTag)
        self.tree.write(self.calibrationFile)

    
    def sideinfo(self, createDate=None, modifyDate=None, sideName=None):
        root = self.tree.getroot()
        _now = util._gettime(_type='file')

        if root.get('side') is None:
            root.set('side', '无')
        if root.get('create_date') is None:
            root.set('create_date', _now)
        if root.get('modify_date') is None:
            root.set('modify_date', _now)
        
        if createDate is None and modifyDate is None and sideName is None:
            return root.get('create_date'), root.get('modify_date'), root.get('side')
        else:
            if createDate is not None:
                root.set('create_date', str(createDate))
            if modifyDate is not None:
                root.set('modify_date', str(modifyDate))
            if sideName is not None:
                root.set('side', str(sideName))
            self.tree.write(self.calibrationFile)
            
    def carinfo(self, kind, line, side, createDate=None, modifyDate=None, modifyMode=None):
        xCarcz = '.carcz[@cztype="' + str(kind) + '"]'
        try:
            _parent = self.dictPhototype['%s_%s' % (line, side)]
        except KeyError:
            return None, None, None
        node = _parent.find(xCarcz)
        if node is None: return None, None, None
        if createDate is None and modifyDate is None and modifyMode is None:
            return node.get('create_date'), node.get('modify_date'), node.get('modify_mode')
        else:
            if createDate is not None:
                node.set('create_date', str(createDate))
            if modifyDate is not None:
                node.set('modify_date', str(modifyDate))
            if modifyMode is not None:
                node.set('modify_mode', str(modifyMode))
            self.tree.write(self.calibrationFile)
    
    def _getNewCode(self, kind):
        """
        货车+'T'
        """
        _kind = kind
        if kind[0] != 'K' and (kind[0] == 'J' and 'JSQ' in kind):
            _kind = 'T' + kind
        return _kind

    def carbody(self, kind, line, side, _new=None):
        _kind = self._getNewCode(kind)
        xCarcz = '.carcz[@cztype="' + str(_kind) + '"]'
        xCarcz_old = '.carcz[@cztype="' + str(kind) + '"]'
        try:
            _parent = self.dictPhototype['%s_%s' % (line, side)]
        except KeyError:
            if _new is None:
                return -1, -1, -1, -1
            else:
                self.build(1, lineTag=line, lTag='L', rTag='R')
                self.readxml()
                _parent = self.dictPhototype['%s_%s' % (line, side)]
        node = _parent.find(xCarcz)
        node_old = _parent.find(xCarcz_old)
        if _new is None:
            if node is not None: 
                x = int(node.find('X_carbody').text)
                y = int(node.find('Y_carbody').text)
                width = int(node.find('width_carbody').text)
                height = int(node.find('height_carbody').text)
                return x, y, width, height
            elif node_old is not None:
                x = int(node_old.find('X_carbody').text)
                y = int(node_old.find('Y_carbody').text)
                width = int(node_old.find('width_carbody').text)
                height = int(node_old.find('height_carbody').text)
                return x, y, width, height
            else:
                return -1, -1, -1, -1   # 标定中无该车型

        else:
            if node is None:
                _new_kind = ET.SubElement(_parent, 'carcz')
                _new_kind.set('cztype', str(_kind))
                _new_kind.set('create_date', util._gettime(_type='file'))
                _new_kind.set('modify_date', util._gettime(_type='file'))
                _new_kind.set('modify_mode', 'Manual')
                _x = ET.SubElement(_new_kind, 'X_carbody')
                _x.text = str(_new[0])
                _y = ET.SubElement(_new_kind, 'Y_carbody')
                _y.text = str(_new[1])
                #_y.set('ratio', str(self.yratio))
                _w = ET.SubElement(_new_kind, 'width_carbody')
                _w.text = str(_new[2])
                _h = ET.SubElement(_new_kind, 'height_carbody')
                _h.text = str(_new[3])
            else:
                node.find('X_carbody').text = str(_new[0])
                node.find('Y_carbody').text = str(_new[1])
                node.find('width_carbody').text = str(_new[2])
                node.find('height_carbody').text = str(_new[3])
                node.set('modify_mode', 'Manual')
                node.set('modify_date', util._gettime(_type='file'))
            self.tree.write(self.calibrationFile)

    def axel(self, line, side, _new=None, Z=False):
        if Z:
            xOffsetX = ".zx_train_axle_xoffset"
        else:
            xOffsetX = ".train_axle_xoffset"
        try:
            _line = int(line) % 2 + 1
            _parent = self.dictPhototype['%s_%s' % (_line, side)]
        except KeyError:
            return 0
        nodeOffsetX = _parent.find(xOffsetX)
        if _new is None:
            if nodeOffsetX is None: return 0
            return nodeOffsetX.text
        else:
            if nodeOffsetX is None:
                _newOffsetX = ET.Element(xOffsetX[1:])
                _newOffsetX.text = str(_new)
                _parent.insert(0, _newOffsetX)
            else:
                nodeOffsetX.text = str(_new)
            self.tree.write(self.calibrationFile)
            
    def wheel(self, line, side, _new=None, Z=False):
        if Z:
            xOffsetY = ".zx_train_axle_y"
        else:
            xOffsetY = ".train_axle_y"
        try:
            _line = int(line) % 2 + 1
            _parent = self.dictPhototype['%s_%s' % (_line, side)]
        except KeyError:
            return 0
        nodeOffsetY = _parent.find(xOffsetY)
        if _new is None:
            if nodeOffsetY is None: return 0
            return nodeOffsetY.text
        else:
            if nodeOffsetY is None:
                _newOffsetY = ET.Element(xOffsetY[1:])
                _newOffsetY.text = str(_new)
                _parent.insert(0, _newOffsetY)
            else:
                nodeOffsetY.text = str(_new)
            self.tree.write(self.calibrationFile)
            
    def rail(self, line, side, _new=None, Z=False):
        if Z:
            xRail = ".zx_rail_y"
        else:
            xRail = ".rail_y"
        try:
            _line = int(line) % 2 + 1
            _parent = self.dictPhototype['%s_%s' % (_line, side)]
        except KeyError:
            return 0
        nodeRail = _parent.find(xRail)
        if _new is None:
            if nodeRail is None: return 0
            return nodeRail.text
        else:
            if nodeRail is None:
                _newRail = ET.Element(xRail[1:])
                _newRail.text = str(_new)
                _parent.insert(0, _newRail)
            else:
                nodeRail.text = str(_new)
            self.tree.write(self.calibrationFile)

    def outline(self, line, kind, _new=None):
        # new = [top.y, bottom.y, pic.width]
        xOutlineTop = ".Y_carbody"
        xOutlineBottom = ".height_carbody"
        xOutlineWidth = ".width_carbody"
        _kind = self._getNewCode(kind)
        xCarcz = '.carcz[@cztype="' + str(_kind) + '"]'
        if _new is not None and int(_new[0]) > int(_new[1]):
            _new[0], _new[1] = _new[1], _new[0]

        _line = int(line)
        try:
            _parent = self.dictPhototype['%s_%s' % (_line, 'T')]
        except KeyError:
            _p = self.dictPhototype['%s' % (_line)]
            _lphototype = ET.SubElement(_p, 'phototype')
            _lphototype.set('imgtype', 'T')
            self.tree.write(self.calibrationFile)
            self.readxml()
            _parent = self.dictPhototype['%s_%s' % (_line, 'T')]
        node = _parent.find(xCarcz)
        if _new is None:
            if node is not None:
                _top = int(node.find(xOutlineTop[1:]).text)
                _bottom = int(node.find(xOutlineBottom[1:]).text)
                return _top, _bottom - 1 + _top
            else:
                return 0,0
        else:
            if node is None:
                _new_kind = ET.SubElement(_parent, 'carcz')
                _new_kind.set('cztype', str(_kind))
                _top = int(_new[0])
                _bottom = int(_new[1]) - _top + 1
                eleH = ET.SubElement(_new_kind, 'X_carbody')
                eleH.text = '-1'
                eletop = ET.SubElement(_new_kind, xOutlineTop[1:])
                eletop.text = str(_top)
                eleW = ET.SubElement(_new_kind, xOutlineWidth[1:])
                eleW.text = '-1'
                elebottom = ET.SubElement(_new_kind, xOutlineBottom[1:])
                elebottom.text = str(_bottom)
            else:
                _top = int(_new[0])
                _bottom = int(_new[1]) - _top + 1
                node.find(xOutlineTop[1:]).text = str(_top)
                node.find(xOutlineBottom[1:]).text = str(_bottom)

            self.tree.write(self.calibrationFile)

    def outline2(self, line, _new=None):
        # xOutlineTop = ".t_top"
        # xOutlineBottom = ".t_bottom"
        xOutlineMiddle = ".t_middle"
        _line = int(line)
        try:
            _parent = self.dictPhototype['%s_%s' % (_line, 'T')]
        except KeyError:
            _p = self.dictPhototype['%s' % (_line)]
            _lphototype = ET.SubElement(_p, 'phototype')
            _lphototype.set('imgtype', 'T')
            self.tree.write(self.calibrationFile)
            self.readxml()
            _parent = self.dictPhototype['%s_%s' % (_line, 'T')]
        # nodeTop = _parent.find(xOutlineTop)
        # nodeBottom = _parent.find(xOutlineBottom)
        nodeMiddle = _parent.find(xOutlineMiddle)
        if _new is None:
            return int(nodeMiddle.text) if nodeMiddle is not None else 0
        else:
            if _parent.find(xOutlineMiddle) is None:
                _newObj = ET.Element(xOutlineMiddle[1:])
                _newObj.text = str(_new[2])
                _parent.insert(0, _newObj)
            else:
                _parent.find(xOutlineMiddle).text = str(_new[2])
            self.tree.write(self.calibrationFile)

    def oneclick(self, lst_cztype, autoCalibrationParams, line, side):
        #print('[oneclick] params >>> ', lst_cztype, autoCalibrationParams)
        _key = '%s_%s' % (line, side)
        for _nCar in self.dictPhototype[_key]:
            if _nCar.get('cztype') in lst_cztype:
                old_x = int(_nCar.find('X_carbody').text)
                old_y = int(_nCar.find('Y_carbody').text)
                _nCar.find('X_carbody').text = str(old_x + autoCalibrationParams[0])
                _nCar.find('Y_carbody').text = str(old_y + autoCalibrationParams[1])
                _height = float(_nCar.find('height_carbody').text)
                _width = float(_nCar.find('width_carbody').text)
                _nCar.find('height_carbody').text = str(round(_height * autoCalibrationParams[3]))
                _nCar.find('width_carbody').text = str(round(_width * autoCalibrationParams[2]))
                _nCar.set('modify_mode', 'Auto')
                _nCar.set('modify_date', util._gettime(_type='file'))
        self.tree.write(self.calibrationFile)

    def readxml(self):
        root = self.tree.getroot()
        for _line in root:
            self.dictPhototype[_line.get('line')] = _line
            for _side in _line:
                self.dictPhototype[_line.get('line') + '_' + _side.get('imgtype')] = _side

        self.rebuilt_TOP()

    def rebuilt_TOP(self):
        for key in self.dictPhototype.keys():
            if 'T' in key:
                _parent = self.dictPhototype[key]
                xpath = ['t_top', 't_bottom']
                for carz in _parent:
                    try:
                        v = [int(carz.find(x).text) for x in xpath]
                        for node in xpath:
                            carz.remove(carz.find(node))

                        elebottom = ET.SubElement(carz, 'X_carbody')
                        elebottom.text = '-1'
                        eletop = ET.SubElement(carz, 'Y_carbody')
                        eletop.text = str(v[0])
                        eleW = ET.SubElement(carz, 'width_carbody')
                        eleW.text = '-1'
                        eleH = ET.SubElement(carz, 'height_carbody')
                        eleH.text = str(v[1] - v[0] + 1)
                        self.tree.write(self.calibrationFile)
                    except Exception as e:
                        continue



def start():
    m = Tk()
    m.title('车型标定工具')
    main(m)
    m.mainloop()

def test():
    f = '/home/sunyue/data/cpi  (复件).config'
    if os.path.exists(f):
        c = calibration(f)
        c.rebuilt_TOP()
    # c.build(1, '3', lTag='L')

if __name__ == '__main__':
    start()
    # test()