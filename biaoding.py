# coding=utf-8
import codecs
import datetime
from xml.etree import ElementTree as ET
import PIL.Image as pilImage
import PIL.ImageDraw as pilImgDraw
import PIL.ImageTk as pilImgTk
from tkinter.filedialog import *
import tkinter.ttk as ttk
import tkinter as tk
import ctypes

class const:
    CAR_CALIBRATION = 1
    AXEL_CALIBRATION = 2
    RAIL_CALIBRATION = 3
    WHEEL_CALIBRATION = 4
    OUTLINE_CALIBRATION = 5
    OUTLINE_CALIBRATION2 = 6

    CAR_CALIBRATION_READ = 11
    CAR_CALIBRATION_WRITE = 12

    HANDLECOORDS_MODE_CALIBRATION_READ = 11
    HANDLECOORDS_MODE_CALIBRATION_WRITE = 12
    HANDLECOORDS_MODE_ORIGIN_IMAGE_OFFSET = 13
    HANDLECOORDS_MODE_ORIGIN_IMAGE_SAVE = 14
    HANDLECOORDS_MODE_ORIGIN_IMAGE_SHOW = 15

    DISPLAY_MODE_ZOOM = 21
    DISPLAY_MODE_ORIGIN = 22

    DATA_TYPE_Z = 31
    DATA_TYPE_G = 32
    DATA_TYPE_T = 33
class util:
    @staticmethod
    def _expand_tree(tr, root=None):
        iids = tr.get_children(root)
        for iid in iids:
            tr.item(iid, open=True)
            _expand_tree(tr, root=iid)
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
        self.win = _mainobj
        try:
            user32 = ctypes.windll.LoadLibrary('user32.dll')
            menu_height = user32.GetSystemMetrics(15)
            title_height = user32.GetSystemMetrics(4)
        except Exception as e:
            menu_height = 20 ## todo 怎么处理跨平台获取bar高度
            title_height = 20
        self.win_size = (self.win.winfo_screenwidth(), self.win.winfo_screenheight()-menu_height-title_height-20)
        if os.name.upper() == 'NT':
            self.win.state('zoomed')
        self.data_init()
        self.ui_init()
    def data_init(self, init=True):
        self.currentPic = None
        self.currentPicInfo = list()
        self.currentMenu = None
        self.currentPopMenu = None
        self.currentPicIndex = 0
        self.origin_img = None
        self.show_img = None
        self.showZoomRatio = 1
        self.showPics = list()
        self.picGroups = None
        self.calibrationFile = None
        self.drawMode = const.CAR_CALIBRATION
        self.showoffset = 0, 0
        self.drawObj = None
        self.dirname = None
        self.step_value = 0.125
        self.imgPosition = None
        # self.y_offset = 0
        self.calibrationHelper = None
        self.rail_y = 0
        self.outlines = [0, 0, 0]
        self.autoCalibrationParams = [0, 0, 1, 1]
        self.currentCalibrationParams = list()
        self.oldCalibrationInfo = list()
        self.groupByCalibration = dict()
        # self.fetchobjs = list()
        self.history = {'CAR': [], 'AXEL': [], 'WHEEL': [], 'RAIL': [], 'OUTLINE': [], 'OUTLINE_MIDDLE': [], 'POINT':[]}
        self.searchByGroup = dict()
        self.coords = list()
        self.CAR_ID = list()
        self.WHEEL_ID = list()
        self.RAIL_ID = list()
        self.AXEL_ID = list()
        self.IMG_ID = list()
        self.TEXT_ID = list()
        self.OUTLINE_ID = list()
        self.OUTLINE_MIDDLE_ID = list()
        self.POINT_ID = list()
        self.backupShowPics = None
        self.display_mode = const.DISPLAY_MODE_ZOOM
        self.CONSULT_ID = list()
        self.CTRL = False
        self.isAutoCalibration = True
        self.isPicsReady = False
        self.isCalibrationFileReady = False
        self.current_zoom_ratio = 1
        self.FULL_SCREEN = False

        if init:
            self.allPics = list()
        else:
            self.clearAllCanvas()


    def check_data_type(self, _file_name):
        self.isG = self.isZ = self.isT = False
        if '_ZL' in _file_name or '_ZR' in _file_name:
            self.isZ = True
        elif '_T' in _file_name:
            self.isT = True
        else:
            self.isG = True

    def ui_init(self):
        self.show_size = (self.win_size[0], self.win_size[1]*0.9)
        self.ctrl_size = (self.win_size[0], self.win_size[1]*0.1)

        self.canvas = tk.Canvas(self.win, bg='#C7EDCC', width=self.show_size[0], height=self.show_size[1])
        self.canvas.place(x=0, y=0)

        self.control_frame = tk.Frame(self.win, width=self.ctrl_size[0], height=self.ctrl_size[1], bg='#C7EDCC')
        self.control_frame.place(x=0, y=self.show_size[1])

        self.btLastPic = tk.Button(self.control_frame, text='上一张', command=self.showLastPic)
        self.btLastPic.config(width=10, height=1)
        self.btLastPic.pack(side='left')

        self.btNextPic = tk.Button(self.control_frame, text='下一张', command=self.showNextPic)
        self.btNextPic.config(width=10, height=1)
        self.btNextPic.pack(side='left')

        self.btMainPic = tk.Button(self.control_frame, text='保存', command=self.save)
        self.btMainPic.config(width=10, height=1)
        self.btMainPic.pack(side='left')

        # self.check_group_v = IntVar()
        # c = Checkbutton(self.control_frame, text="开启智能分组", variable=self.check_group_v)
        # c.var = self.check_group_v
        # c.pack(side=LEFT)
        
        self.lbPicInfo = tk.Label(self.control_frame)
        self.lbPicInfo.pack(side=LEFT)

        rootMenu = tk.Menu(self.win)
        sourceMenu = tk.Menu(rootMenu, tearoff=0)
        sourceMenu.add_command(label='标定文件', command=self.openCalibrationFile)
        sourceMenu.add_command(label='图片', command=self.openPictureFolder)
        # sourceMenu.add_command(label='ZXGQpics', command=self.openZPictureFolder)
        # sourceMenu.add_command(label='Tpics', command=self.openTPictureFolder)
        rootMenu.add_cascade(label='加载', menu=sourceMenu)

        # toolMenu = tk.Menu(rootMenu, tearoff=0)
        # toolMenu.add_command(label='标定信息', command=self.showInfo)
        # toolMenu.add_command(label='标定状态', command=self.showStatus)
        # rootMenu.add_cascade(label='查看', menu=toolMenu)

        self.win.config(menu=rootMenu)
        
        # _group_frame = tk.Frame(self.control_frame, width=250, height=300, bg='#C7EDCC')
        # self.trGroup = ttk.Treeview(_group_frame, show='tree', height=25)
        # self.trGroup.pack(side=LEFT)
        # self.trGroup.bind('<<TreeviewSelect>>', self.eTreeButton_1)
        # trGroup_vbar = tk.Scrollbar(_group_frame, orient=VERTICAL, command=self.trGroup.yview)
        # self.trGroup.configure(yscrollcommand=trGroup_vbar.set)
        # trGroup_vbar.pack(side=RIGHT, fill=Y)
        # _group_frame.place(x=40, y=25)
        
        self.setEventBinding(mode=self.display_mode)
        # self.updateStatusInfo()
    
    def updateStatusInfo(self):
        _picReady = '已加载' if self.isPicsReady is True else '未加载'
        _calibrationReady = '已加载' if self.isCalibrationFileReady is True else '未加载'
        _autoCalibration = '开' if self.isAutoCalibration is True else '关'
        _info = '标定文件：%s 图片目录：%s 自动标定：%s' % (_calibrationReady, _picReady, _autoCalibration)
        # self.lbInfo.config(text=_info)

    def eCanvasMouseWheel(self, event):
        if event.delta > 0:
            self.FULL_SCREEN = True
        else:
            self.FULL_SCREEN = False
        self.show()

    def setEventBinding(self, mode=const.DISPLAY_MODE_ORIGIN):
        self.canvas.bind('<Motion>', self.eCanvasMotion)
        self.canvas.bind('<Button-3>', self.eCanvasButton_3)
        self.canvas.bind('<Button-1>', self.eCanvasButton_1)
        self.canvas.bind('<ButtonRelease-1>', self.eCanvasButton_1_release)
        self.canvas.bind('<MouseWheel>', self.eCanvasMouseWheel)
        self.win.bind('<KeyRelease>', self.eKeyRelease)
        self.win.bind('<Key>', self.eKeyChanged)
        self.canvas.bind('<B1-Motion>', self.drag)
        # if mode == DISPLAY_MODE_ZOOM:
        #     # pass
        #     self.canvas.bind('<B1-Motion>', self.eCanvasButton_1_move)
        # elif mode == DISPLAY_MODE_ORIGIN:
        #     pass
        #     # self.canvas.bind('<Control-B1-Motion>', self.drag)

    def eKeyRelease(self, event):
        if event.keycode == 17:
            self.CTRL = False
        print(event.keycode)

    def eKeyChanged(self, event):
        # if event.keysym == 'm':
        #     if self.isAutoCalibration == False:
        #         self.isAutoCalibration = True
        #     else:
        #         self.isAutoCalibration = False
        #     self.updateStatusInfo()
        if event.keycode == 17:
            self.CTRL = True
        print(event.keycode)

    def drag(self, event):
        """
        操作针对全部canvas对象
        """
        if self.CTRL:
            offx = event.x - self.startX
            offy = event.y - self.startY
            for obj in self.canvas.find_all():
                # if self.canvas.type(obj) != 'image':
                self.bbox_move(offx, offy, specify=obj)
            self.coords = [(x+offx,y+offy) for x,y in self.coords]
        self.startX = event.x
        self.startY = event.y

    def drag2(self, event):
        """
        操作仅针对车厢标定区域
        """
        offx = event.x - self.startX
        offy = event.y - self.startY
        for obj in self.CAR_ID:
            if self.canvas.type(obj) != 'rectangle':
                self.bbox_move(offx, offy, specify=obj)
        self.coords = [(x+offx,y+offy) for x,y in self.coords]
        self.startX = event.x
        self.startY = event.y
    
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
    def eKey(self, event):
        pass
        # print(event.keycode)
        
        # if event.keycode == 27:
        #     self.recovery()
        #     self.setToMainPic()
            
        # if event.keycode == 66:
        #     self.backupShowPics = self.showPics
        #     _dt = self._find_new_car()
        #     self.showPics = _dt
        #     self.currentPicIndex = 0
        #     self.setCurrnetPic(list(self.showPics.keys())[self.currentPicIndex])
        #     self.show()
        #     self.updateInfo()
        #     self.setToMainPic()
        
        # if event.keycode == 65:
        #     if self.backupShowPics is not None:
        #         self.showPics = self.backupShowPics
        #         self.currentPicIndex = 0
        #         self.setCurrnetPic(list(self.showPics.keys())[self.currentPicIndex])
        #         self.show()
        #         self.updateInfo()
        #         self.setToMainPic()
    def stats(self, mode='status'):
        def _filter(x):
            return x is not None
        _stats = dict()
        today_date = util._gettime(_type='file')
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
    def eTreeButton_1(self, event):
        _widget = event.widget
        if self.trGroup.item(_widget.focus())['tags'][0] == 'file':
            _basename = '_'.join([str(x) for x in self.trGroup.item(_widget.focus())['values']])
            _pic = _basename.replace('$$', '\\')
            self.setCurrnetPic(_pic)
            try:
                self.show()
            except:
                pass
    def getTreeData(self, _pic):
        if self.isZ: return
        self.cleanTreeNode()
        today_date = util._gettime(_type='file')
        _info = self.getPicInfo(_pic)
        if _pic not in list(self.showPics.keys()):
            _group_key = '%s_%s' % (str(_info[1]), _info[2])
            # _algorGroup = self.algor_y(_group_key, [_info[0]])
            _algorGroup = self.algor_y_h(_group_key, [_info[0]])
            if _algorGroup[list(_algorGroup.keys())[0]][0][1] is not None:
                _key = self._getDictKey(
                    list(_algorGroup.keys())[0], 
                    _algorGroup[list(_algorGroup.keys())[0]][0][1])
                _existsGroup = _group_key + '_' + _key
                _picGroup = self.picGroups[_existsGroup]
        else:
            _groupCode = self.showPics[_pic]
            if _groupCode is None: return
            _picGroup = self.picGroups[_groupCode]
        root = self.trGroup.insert(
            '',
            0,
            text='车型分组',
            tags='root'
            )
        for x in _picGroup[0].keys():
            _kind = self.trGroup.insert(
                root,
                0,
                text=x,
                tags='root'
            )

            for _car in _picGroup[0][x]:
                _file = _car.split('_')[3] + '_' + _car.split('_')[4]
                encode_car = _car.replace('\\', '$$')
                self.trGroup.insert(
                    _kind,
                    0,
                    text=_file,
                    values=(str(encode_car).split('_')),
                    tags='file'
                )
        _expand_tree(self.trGroup)

    def setCurrnetPic(self, filename):
        """
        设置当前图片参数
        :param filename:完整路径 
        :return: 
        """
        if os.path.exists(filename):
            self.currentPic = filename
            self.currentPicInfo = self.getPicInfo(filename)
            self.dirname = os.path.dirname(filename)

    def save(self):
        if self.isG and len(self.CAR_ID) > 0 and self.CAR_ID[0] not in self.history['CAR']:
            bbox_car = self.canvas.bbox(self.CAR_ID[0])
            _para = self.canvas.bbox(self.IMG_ID[0])
            x = round((bbox_car[0] - _para[0]) / self.showZoomRatio)
            y = round((bbox_car[1] - _para[1]) / self.showZoomRatio)
            w = round((bbox_car[2] - bbox_car[0]) / self.showZoomRatio)
            h = round((bbox_car[3] - bbox_car[1]) / self.showZoomRatio)
            newCalibration = (x,y,w,h)
            # self.calibrationHelper.setcarbody(newCalibration)
            self.calibrationHelper.carbody(
                self.currentPicInfo[0],
                self.currentPicInfo[1], 
                self.currentPicInfo[2], 
                _new=newCalibration)
            # if self.oldCalibrationInfo.count(-1) != 4 and self.isAutoCalibration is True:
            #     # print('准备自动标定')
            #     self.autoCalibrationParams[0] = x - self.oldCalibrationInfo[0]
            #     self.autoCalibrationParams[1] = y - self.oldCalibrationInfo[1]
            #     self.autoCalibrationParams[2] = w / self.oldCalibrationInfo[2]
            #     self.autoCalibrationParams[3] = h / self.oldCalibrationInfo[3]
            #     _lst = self._getElementsFromTree()
            #     _lst.remove(self.currentPicInfo[0])
            #     self.calibrationHelper.oneclick(_lst, self.autoCalibrationParams, self.currentPicInfo[1], self.currentPicInfo[2])
            #     self.autoCalibrationParams = [0, 0, 1, 1]

        # else:
        #     print('车厢标定无改动！')
        if not self.isT and len(self.AXEL_ID) > 0 and self.AXEL_ID[0] not in self.history['AXEL']:
            self.calibrationHelper.axel(
                self.currentPicInfo[1], 
                self.currentPicInfo[2], 
                _new=self.axel_x_offset,
                Z=self.isZ)
        # else:
        #     print('车轴标定无改动！')
        if not self.isT and len(self.WHEEL_ID) > 0 and self.WHEEL_ID[0] not in self.history['WHEEL']:
            self.calibrationHelper.wheel(
                self.currentPicInfo[1], 
                self.currentPicInfo[2], 
                _new=self.axel_y,
                Z=self.isZ)
        # else:
        #     print('车轮标定无改动！')
        if not self.isT and len(self.RAIL_ID) > 0 and self.RAIL_ID[0] not in self.history['RAIL']:
            self.calibrationHelper.rail(
                self.currentPicInfo[1], 
                self.currentPicInfo[2], 
                _new=self.rail_y,
                Z=self.isZ)
        # else:
        #     print('铁轨标定无改动！')
        if self.drawMode == const.OUTLINE_CALIBRATION and len(self.OUTLINE_ID) > 0 and self.OUTLINE_ID[0] not in self.history['OUTLINE']:
            self.calibrationHelper.outline(
                self.currentPicInfo[1],
                kind=self.currentPicInfo[0],
                _new=self.outlines)
        # else:
        #     print('铁轨标定无改动！')
        if self.drawMode == const.OUTLINE_CALIBRATION2 and len(self.OUTLINE_MIDDLE_ID) > 0 and self.OUTLINE_MIDDLE_ID[0] not in self.history['OUTLINE_MIDDLE']:
            self.calibrationHelper.outline2(
                self.currentPicInfo[1],
                _new=self.outlines)
        # else:
        #     print('铁轨标定无改动！')
        self.display(_pics=self.currentPic)
        

    def _getElementsFromTree(self, level=1):
        _Root = self.trGroup.get_children()
        _kinds = []
        for x in range(level):
            iids = self.trGroup.get_children(_Root)
            for iid in iids:
                _kinds.append(self.trGroup.item(iid)['text'])
        return _kinds

    def openPictureFolder(self):
        self.allPics = []
        dirpath = askdirectory(initialdir=os.path.join(sys.path[0]), title='请选择图片文件夹')
        self.currentPicIndex = 0
        if os.path.exists(dirpath) is True:
            for root, dirs, files in os.walk(dirpath, topdown=False):
                self.allPics = [os.path.normpath(os.path.join(root, name)) for name in files]
            self.isPicsReady = True
            if self.calibrationFile is not None and self.calibrationHelper is not None:
                self.display()
        # self.updateStatusInfo()


    def openTPictureFolder(self):
        self.isPicsReady = False
        self.isZ = False
        self.isT = True
        self.allPics = []
        self.showPics = []
        self.cleanTreeNode()
        dirpath = askdirectory(initialdir=os.path.join(sys.path[0]), title='请选择超限图片文件夹')
        self.currentPicIndex = 0
        if os.path.exists(dirpath) is True:
            for root, dirs, files in os.walk(dirpath, topdown=False):
                self.allPics = [os.path.normpath(os.path.join(root, name)) for name in files]
            self.isPicsReady = True
            if self.calibrationFile is not None and self.calibrationHelper is not None:
                self.display()
        # self.updateStatusInfo()
    def openZPictureFolder(self):
        self.isPicsReady = False
        self.isZ = True
        self.isG = False
        self.isT = False
        self.allPics = []
        self.showPics = []
        self.cleanTreeNode()
        dirpath = askdirectory(initialdir=os.path.join(sys.path[0]), title='请选择走行部图片文件夹')
        self.currentPicIndex = 0
        if os.path.exists(dirpath) is True:
            for root, dirs, files in os.walk(dirpath, topdown=False):
                self.allPics = [os.path.normpath(os.path.join(root, name)) for name in files]
            self.isPicsReady = True
            if self.calibrationFile is not None and self.calibrationHelper is not None:
                self.display()
        # self.updateStatusInfo()
    def refreshData(self, handleCalibration=False, handlePics=False, _handlePics_param=None):
        if handleCalibration:
            self.handleCarPositionfile()
        if handlePics:
            self.getPicGroups(_pic=_handlePics_param)
            self.getShowPics()
            if _handlePics_param is not None:
                self.setCurrnetPic(_handlePics_param)

    def display(self, _pics=None, _index=0):
        # if self.isZ:
        #     self.refreshData(handleCalibration=True, handlePics=True)
        #     self.setCurrnetPic(list(self.showPics.keys())[0])
        # if self.isG:
        #     if _pics is None:
        #         self.refreshData(handlePics=True)
        #         self.setCurrnetPic(list(self.showPics.keys())[0])
        #     if _pics is not None:
        #         self.refreshData(handleCalibration=True, handlePics=True, _handlePics_param=_pics[_index])
        # if self.isT:
        #     self.refreshData(handleCalibration=True, handlePics=True)
        #     self.setCurrnetPic(list(self.showPics.keys())[0])
        self.setCurrnetPic(self.allPics[self.currentPicIndex])
        self.show()

    def getShowPics(self):
        _return = dict()
        if self.isT:
            for _key in self.picGroups.keys():
                _return[_key] = None
        if self.isG:
            for _key in self.picGroups.keys():
                if _key.split('_')[2] != 'NEW':
                    _return[self.picGroups[_key][1]] = _key
                else:
                    for _new in list(self.picGroups[_key][0].values()):
                        for pic in _new:
                            _return[pic] = None
        if self.isZ:
            for _key in self.picGroups.keys():
                _return[_key] = None
        self.showPics = _return
    
    def openCalibrationFile(self):
        self.isCalibrationFileReady = False
        self.data_init(init=False)
        self.calibrationFile = os.path.normpath(askopenfilename(initialdir=os.path.join(sys.path[0]), title='请选择标定文件'))
        self.calibrationHelper = calibration(self.calibrationFile)
        if os.path.exists(self.calibrationFile) is True:
            self.handleCarPositionfile()
            if len(self.allPics) != 0 and self.calibrationFile is not None:
                self.display()
        # self.updateStatusInfo()
            
    def handleCarPositionfile(self):
        self.analyzeCalibrationFile()

    def getPicGroups(self, _pic=None):
        _return = dict()
        _count1 = 0
        self.cleanPics()
        if self.isG:
            for pic in self.allPics:
                _picInfo = self.getPicInfo(pic)
                _group_key = '%s_%s' % (str(_picInfo[1]), _picInfo[2])
                _algorGroup = self.algor_y_h(_group_key, [_picInfo[0]])
                _newGroup = _group_key + '_NEW'
                if _algorGroup[list(_algorGroup.keys())[0]][0][1] is not None:
                    _key = self._getDictKey(
                        list(_algorGroup.keys())[0], 
                        _algorGroup[list(_algorGroup.keys())[0]][0][1])
                    _existsGroup = _group_key + '_' + _key
                    try:
                        _tmp =  self.groupByCalibration[_group_key]
                    except KeyError:
                        self.calibrationHelper.build(1, lineTag=_picInfo[1], lTag='L', rTag='R')
                        # self.calibrationHelper.readxml()
                        self.handleCarPositionfile()

                    try:
                        _kinds_group = self.groupByCalibration[_group_key][_key]
                    except KeyError:
                        _kinds_group = []
                    if _existsGroup not in _return.keys():
                        _return[_existsGroup] = list()
                        _tmp = dict()
                        for kind in _kinds_group:
                            _tmp[kind] = list()
                        _return[_existsGroup].insert(1, '')
                        _return[_existsGroup].insert(0, _tmp)
                    if '#' in _picInfo[0]:
                        _curKind = _picInfo[0].replace('#', '*')
                    else:
                        _curKind = _picInfo[0]
                    _return[_existsGroup][0][_curKind].append(pic)
                    _count1 += 1
                    _return[_existsGroup][1] = pic
                    if _pic is not None:
                        _tmp_info = self.getPicInfo(_pic)
                        _tmp_group_key = '%s_%s' % (str(_tmp_info[1]), _tmp_info[2])
                        if _tmp_group_key == _group_key and \
                            _tmp_info[0] in _return[_existsGroup][0][_curKind] and \
                            _return[_existsGroup][1] != _pic:
                            _return[_existsGroup][1] = _pic
                else:
                    if _newGroup not in _return.keys():
                        _return[_newGroup] = list()
                        _tmp = dict()
                        _return[_newGroup].insert(0, _tmp)
                    
                    if _picInfo[0] in _return[_newGroup][0]:
                        _return[_newGroup][0][_picInfo[0]].append(pic)
                    else:
                        _return[_newGroup][0][_picInfo[0]] = [pic]
                    _count1 += 1
        else:
            for pic in self.allPics:
                _return[pic] = list()
        self.picGroups = _return
            
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
            
    def updateInfo(self):
        _info = '(%d/%d) %s' % (self.currentPicIndex + 1, len(self.allPics), self.currentPic)
        self.lbPicInfo.config(text=_info)

    def getExtName(self, _filepath, toget='ex'):
        # _filepath：文件名（含路径）
        # toget = 'ex':获取该文件扩展名
        # toget = 'jpginfo'：获取车型、线路、左右侧信息
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

    def cleanPics(self):
        _nopics = list()
        for _file in self.allPics:
            exname = self.getExtName(_file)
            if exname == 'JPG':
                _nopics.append(_file)
        self.allPics = _nopics

    def handleCoords(self, mode, params):
        if len(self.IMG_ID) != 0:
            bbox = self.canvas.bbox(self.IMG_ID[0])
        if self.oldCalibrationInfo is None or len(self.oldCalibrationInfo) == 0 or self.oldCalibrationInfo.count(
            -1) == 4: return [0, 0, 0, 0]
        if mode == const.CAR_CALIBRATION_READ:   # 车厢标定 origin >> pic
            x1 = int(self.oldCalibrationInfo[0] * self.showZoomRatio) + params[0]
            y1 = int(self.oldCalibrationInfo[1] * self.showZoomRatio) + params[1]
            x2 = int((self.oldCalibrationInfo[2] + self.oldCalibrationInfo[0]) * self.showZoomRatio) + params[0]
            y2 = int((self.oldCalibrationInfo[3] + self.oldCalibrationInfo[1]) * self.showZoomRatio) + params[1]
            return x1, y1, x2, y2
        elif mode == const.CAR_CALIBRATION_WRITE: #车厢标定 pic >> origin
            oStartX = int(params[0] / self.showZoomRatio)
            oStartY = int(params[1] / self.showZoomRatio)
            oEndX = int(params[2] / self.showZoomRatio)
            oEndY = int(params[3] / self.showZoomRatio)
            oWidth = oEndX - oStartX
            oHeight = oEndY - oStartY
            return (oStartX, oStartY, oWidth, oHeight)
        elif mode == const.HANDLECOORDS_MODE_ORIGIN_IMAGE_SHOW:
            if len(self.IMG_ID) != 0:
                X = params[0]
                Y = params[1]
                if bbox[0] < 0:
                    X += abs(bbox[0])
                elif bbox[0] > 0:
                    X -= bbox[0]

                if bbox[1] < 0:
                    Y += abs(bbox[1])
                elif bbox[1] > 0:
                    Y -= bbox[1]
                return X, Y
        elif mode == const.HANDLECOORDS_MODE_ORIGIN_IMAGE_SAVE:
            img_bbox = self.canvas.bbox(self.IMG_ID[0])
            car_bbox = self.canvas.bbox(self.CAR_ID[0])
            if img_bbox[0] > 0:
                _x = car_bbox[0] - img_bbox[0]
            elif img_bbox[0] < 0:
                _x = car_bbox[0] + abs(img_bbox[0])
            else:
                _x = car_bbox[0]

            if img_bbox[1] > 0:
                _y = car_bbox[1] - img_bbox[1]
            elif img_bbox[1] < 0:
                _y = car_bbox[1] + abs(img_bbox[1])
            else:
                _y = car_bbox[1]

            _w = car_bbox[2] - car_bbox[0]
            _h = car_bbox[3] - car_bbox[1]
            return _x, _y, _w, _h

    def getPicInfo(self, pic):
        # print(pic)
        try:
            _lst = os.path.basename(pic).split('_')
            _kind = _lst[0]
            _line = str(int(_lst[1].split('.')[3])-1)
            if '#' in _lst[0]:
                _kind = _lst[0].replace('#', '*')
            if 'T' == _lst[0][0] or 'Q' == _lst[0][0]:
                _kind = _kind[1:] ## todo T和Q要不要保存在标定文件中
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
            return (_kind, _line, _side)
    
    def clearAllCanvas(self):
        self.cleanCanvasByType(self.IMG_ID, self.canvas)
        self.cleanCanvasByType(self.CAR_ID, self.canvas)
        self.cleanCanvasByType(self.WHEEL_ID, self.canvas)
        self.cleanCanvasByType(self.AXEL_ID, self.canvas)
        self.cleanCanvasByType(self.RAIL_ID, self.canvas)
        self.cleanCanvasByType(self.TEXT_ID, self.canvas)
        self.cleanCanvasByType(self.OUTLINE_ID, self.canvas)


    def show(self):
        # 清理对象
        self.clearAllCanvas()
        if self.FULL_SCREEN:
            self.displayImage2()
        else:
            self.displayImage()
        # if self.display_mode == DISPLAY_MODE_ORIGIN:
        #     self.displayImage2()    
        # elif self.display_mode == DISPLAY_MODE_ZOOM:
        #     self.displayImage()
        self.check_data_type(self.allPics[self.currentPicIndex])
        if self.isT:
            self.displayOutline()
            self.displayOutline2()
        else:
            if self.isG:
                self.displayCarCalibration()
            self.displayAxelCalibration()
            self.displayRailCalibration()
        # self.getTreeData(self.currentPic)
        self.updateInfo()

    def displayImage(self):
        self.origin_img = pilImage.open(self.currentPic)
        self.show_img = self.resizeImage(self.origin_img)
        self._photo = pilImgTk.PhotoImage(self.show_img)
        _middle = self.win_size[0]/2, self.win_size[1]/2
        _img = self.canvas.create_image(_middle[0], _middle[1], image=self._photo)
        self.imgPosition = self.canvas.bbox(_img)
        self.IMG_ID.append(_img)

    def displayImage2(self):
        self.origin_img = pilImage.open(self.currentPic)
        self.showZoomRatio = 1
        self.show_img = self.origin_img
        self._photo = pilImgTk.PhotoImage(self.origin_img)
        _img = self.canvas.create_image(
            (
                self.origin_img.size[0] / 2, 
                self.origin_img.size[1] / 2
                ), 
            image=self._photo)
        self.imgPosition = self.canvas.bbox(_img)
        self.IMG_ID.append(_img)

    def bbox_scale(self, xy_scale, specify=None):
        # 全图 > 清空canvas > 按原始大小重绘全部元素

        if specify is None:
            _items = self.canvas.find_all()
            # self.clearAllCanvas()
            for item in _items:
                self.canvas.scale(item,self.canvas.bbox(self.IMG_ID[0])[0],self.canvas.bbox(self.IMG_ID[0])[1],xy_scale,xy_scale)
        else:
            self.canvas.move(specify, offX, offY)


    def bbox_move(self, offX, offY, specify=None):
        if specify is None:
            _items = self.canvas.find_all()
            for item in _items:
                self.canvas.move(item, offX, offY)
        else:
            self.canvas.move(specify, offX, offY)

    def displayCarCalibration(self):
        self.oldCalibrationInfo = self.calibrationHelper.carbody(self.currentPicInfo[0], self.currentPicInfo[1], self.currentPicInfo[2])
        _info = '%s %s %s %s' % (
            '202.202.202.%s' % (str(int(self.currentPicInfo[1])+1)),
            '左侧' if self.currentPicInfo[2] == 'L' else '右侧',
            self.currentPicInfo[0],
            '【新增】' if self.oldCalibrationInfo.count(-1) == 4 else ''
        )
        self.TEXT_ID.append(
            self.canvas.create_text((350, 100), text=_info, anchor='w', font=60)
        )
    
        #print('exists carbody >>> ',self.oldCalibrationInfo)
        if self.display_mode == const.DISPLAY_MODE_ZOOM:
            _car = self.handleCoords(const.CAR_CALIBRATION_READ, self.canvas.bbox(self.IMG_ID[0]))
            if _car.count(-1) != 4:  # 不为初始值
                x1, y1, x2, y2 = _car
                _x1 = self.show_size[0]/2 - round(self.oldCalibrationInfo[2] * self.showZoomRatio /2)
                _x2 = x2 - x1
                car_id = self.canvas.create_rectangle(x1, y1, x2, y2, width=2, outline='orange')
                self.CAR_ID.append(car_id)
                self.history['CAR'].append(car_id)
        elif self.display_mode == const.DISPLAY_MODE_ORIGIN:
            x1 = self.oldCalibrationInfo[0]
            y1 = self.oldCalibrationInfo[1]
            x2 = self.oldCalibrationInfo[2] + x1
            y2 = self.oldCalibrationInfo[3] + y1
            car_id = self.canvas.create_rectangle(x1, y1, x2, y2, width=2, outline='orange')
            self.CAR_ID.append(car_id)

    def displayAxelCalibration(self):
        _side = self.currentPicInfo[2]
        _line = str(self.currentPicInfo[1])
        _kind = self.currentPicInfo[0]
        _w = self.origin_img.size[0]        
        _wheelInfo = self._getpicwheelinfo()
        _offset = int(self.calibrationHelper.axel(_line, _side, Z=self.isZ))
        _wheel = int(self.calibrationHelper.wheel(_line, _side, Z=self.isZ))
        _lst_axel = _wheelInfo[:len(_wheelInfo) - _wheelInfo.count(-1)]
        if _side == 'R':
            _lst_axel.reverse()
            _lst_axel = [_w - x for x in _lst_axel]
        for _axel in _lst_axel:
            axel_id = self.canvas.create_line(
                (_axel-_offset)*self.showZoomRatio,
                self.show_img.size[1] + self.imgPosition[1],
                (_axel-_offset)*self.showZoomRatio,
                self.imgPosition[1],
                width=2,
                fill='yellow', dash=(6,6))
            self.AXEL_ID.append(axel_id)
            self.history['AXEL'].append(axel_id)
        wheel_id = self.canvas.create_line(
            0,
            _wheel * self.showZoomRatio + self.imgPosition[1],
            self.imgPosition[2],
            _wheel * self.showZoomRatio + self.imgPosition[1],
            width=2,
            fill='green'
        )
        self.WHEEL_ID.append(wheel_id)
        self.history['WHEEL'].append(wheel_id)


    def displayOutline(self):
        self.cleanCanvasByType(self.OUTLINE_ID, self.canvas)
        _line = str(self.currentPicInfo[1])
        _kind = str(self.currentPicInfo[0])
        _outlines = self.calibrationHelper.outline(_line, kind=_kind)
        for _outline in _outlines:
            outline_id = self.canvas.create_line(
                0,
                _outline *self.showZoomRatio + self.imgPosition[1],
                self.imgPosition[2],
                _outline *self.showZoomRatio + self.imgPosition[1],
                width=2,
                fill='yellow')
            self.OUTLINE_ID.append(outline_id)
            self.history['OUTLINE'].append(outline_id)

    def displayOutline2(self):
        pass
        # _line = str(self.currentPicInfo[1])
        # _outline_middle = self.calibrationHelper.outline2(_line)
        # outline_id = self.canvas.create_line(
        #     0,
        #     _outline_middle *self.showZoomRatio + self.imgPosition[1],
        #     self.imgPosition[2],
        #     _outline_middle *self.showZoomRatio + self.imgPosition[1],
        #     width=2,
        #     fill='yellow')
        # self.OUTLINE_MIDDLE_ID.append(outline_id)
        # self.history['OUTLINE_MIDDLE'].append(outline_id)

    def displayRailCalibration(self):
        _side = self.currentPicInfo[2]
        _line = str(self.currentPicInfo[1])
        _raily = int(self.calibrationHelper.rail(_line, _side, Z=self.isZ))
        #print('getrail() = %d' % (_raily,))
        if _raily != -1:
            rail_id = self.canvas.create_line(
                0,
                _raily * self.showZoomRatio + self.imgPosition[1],
                self.imgPosition[2],
                _raily * self.showZoomRatio + self.imgPosition[1],
                width = 2,
                fill = 'blue'
            )
            self.RAIL_ID.append(rail_id)
            self.history['RAIL'].append(rail_id)


    def cleanTreeNode(self):
        for node in self.trGroup.get_children():
            self.trGroup.delete(node)

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
        if -1 < self.currentPicIndex + 1 < len(self.allPics):
            self.currentPicIndex += 1
            self.setCurrnetPic(self.allPics[self.currentPicIndex])
            self.show()
            self.updateInfo()

    def showLastPic(self):
        if -1 < self.currentPicIndex - 1 < len(self.allPics):
            self.currentPicIndex -= 1
            self.setCurrnetPic(self.allPics[self.currentPicIndex])
            self.show()
            self.updateInfo()
            
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
        if len(self.IMG_ID) == 0: return
        bbox = self.canvas.bbox(self.IMG_ID[0])

        self.cleanCanvasByType(self.CONSULT_ID, self.canvas)
        self.CONSULT_ID.append(
            self.canvas.create_line(
                bbox[0], event.y, bbox[2], event.y, width=2, fill='yellow', dash=(6,6)
            )
        )
        self.CONSULT_ID.append(
            self.canvas.create_line(
                event.x, bbox[1], event.x, bbox[3], width=2, fill='yellow', dash=(6,6)
            )
        )
    

    def eCanvasButton_3(self, event):
        self._clear_menu()
        popmenu = Menu(self.canvas, tearoff=0)
        self.current_actived_menu = popmenu
        
        if self.isG:
            popmenu.add_command(label='车厢标定', command=self.setCarCalibration)
            popmenu.add_command(label='车轴标定', command=self.setAxelCalibration)
            popmenu.add_command(label='铁轨标定', command=self.setRailCalibration)
        if self.isZ:
            popmenu.add_command(label='车轴标定', command=self.setAxelCalibration)
            popmenu.add_command(label='铁轨标定', command=self.setRailCalibration)
        if self.isT:
            popmenu.add_command(label='轮廓标定', command=self.setOutlineCalibration)
            popmenu.add_command(label='中线标定', command=self.setOutlineCalibration2)
        popmenu.post(event.x_root, event.y_root)

    def eCanvasButton_1(self, event):
        self.startX = event.x
        self.startY = event.y
        if self.CTRL: return
        if self.drawMode == const.CAR_CALIBRATION:
            self.coords.append((event.x, event.y))
            self._create_point(event.x,event.y,2,fill='red')
            if len(self.coords) >= 2:
                self.cleanCanvasByType(self.CAR_ID, self.canvas)
                self.cleanCanvasByType(self.POINT_ID, self.canvas)
                _new = self.canvas.create_rectangle(
                    # self.coords[0][0] + bbox[0], self.coords[0][1] + bbox[1],
                    self.coords[0][0], self.coords[0][1],
                    event.x, event.y,
                    width=2,
                    outline='red'
                )
                self.CAR_ID.append(_new)
                # print('img > ', self.canvas.bbox(self.IMG_ID[0]))
                # print('add > ', self.canvas.bbox(_new))
                self.coords.clear()

        elif self.drawMode == const.AXEL_CALIBRATION:
            self.cleanCanvasByType(self.AXEL_ID, self.canvas)
            self.cleanCanvasByType(self.WHEEL_ID, self.canvas)
            _side = self.currentPicInfo[2]
            _line = str(self.currentPicInfo[1])
            _kind = self.currentPicInfo[0]
            _w = self.origin_img.size[0]
            self.WHEEL_ID.append(
                self.canvas.create_line(0, event.y, self.canvas.bbox(self.IMG_ID[0])[2], event.y, width=2, fill='yellow')
            )
            self.axel_y = round((event.y - self.canvas.bbox(self.IMG_ID[0])[1]) / self.showZoomRatio)
            
            _wheel = self._getpicwheelinfo()
            _lst_axel = _wheel[:len(_wheel)-_wheel.count(-1)]
            if len(_lst_axel) > 0:
                if _side == 'R':
                    _lst_axel.reverse()
                    _lst_axel = [_w - x for x in _lst_axel]
                    _x_offset = round(_lst_axel[0]*self.showZoomRatio) - event.x
                if _side == 'L':
                    _x_offset = round(_lst_axel[2]*self.showZoomRatio) - event.x
                self.axel_x_offset = round(_x_offset/self.showZoomRatio)
                for _axel in _lst_axel:
                    self.AXEL_ID.append(self.canvas.create_line(
                        (round(_axel*self.showZoomRatio) - _x_offset,
                        self.show_img.size[1] + self.imgPosition[1]),
                        (round(_axel*self.showZoomRatio) - _x_offset,
                        self.imgPosition[1]), width=2, fill='yellow'))
        elif self.drawMode == const.RAIL_CALIBRATION:
            self.cleanCanvasByType(self.RAIL_ID, self.canvas)
            self.rail_y = round((event.y - self.canvas.bbox(self.IMG_ID[0])[1]) / self.showZoomRatio)
            self.RAIL_ID.append(
                self.canvas.create_line(0, event.y, self.show_img.size[0], event.y, width=2, fill='blue')
            )
        elif self.drawMode == const.OUTLINE_CALIBRATION:
            if self.outlines[0] != 0 and self.outlines[1] != 0 or len(self.OUTLINE_ID) > 1:
                self.outlines[0] = 0
                self.outlines[1] = 0
                self.cleanCanvasByType(self.OUTLINE_ID, self.canvas)
            if self.outlines[0] == 0:
                self.outlines[0] = round((event.y - self.imgPosition[1]) / self.showZoomRatio)
            elif self.outlines[1] == 0:
                self.outlines[1] = round((event.y - self.imgPosition[1]) / self.showZoomRatio)
            # print(self.outlines)
            self.OUTLINE_ID.append(
                self.canvas.create_line(0, event.y, self.show_img.size[0], event.y, width=2, fill='blue')
            )
        elif self.drawMode == const.OUTLINE_CALIBRATION2:
            if self.outlines[2] != 0 or len(self.OUTLINE_MIDDLE_ID) > 0:
                self.outlines[2] = 0
                self.cleanCanvasByType(self.OUTLINE_MIDDLE_ID, self.canvas)
            if self.outlines[2] == 0:
                self.outlines[2] = round((event.y - self.imgPosition[1]) / self.showZoomRatio)
            # print(self.outlines)
            self.OUTLINE_MIDDLE_ID.append(
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
        #         self.cleanCanvasByType(self.AXEL_ID, self.canvas)
        #         self.cleanCanvasByType(self.WHEEL_ID, self.canvas)
        #         _side = self.currentPicInfo[2]
        #         _line = str(self.currentPicInfo[1])
        #         _kind = self.currentPicInfo[0]
        #         _w = self.origin_img.size[0]
        #         self.WHEEL_ID.append(
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
        #             self.AXEL_ID.append(self.canvas.create_line(
        #                 (round(_axel*self.showZoomRatio) - _x_offset,
        #                 self.show_img.size[1] + self.imgPosition[1]),
        #                 (round(_axel*self.showZoomRatio) - _x_offset,
        #                 self.imgPosition[1]), width=2, fill='yellow'))
        #     elif self.drawMode == RAIL_CALIBRATION:
        #         self.cleanCanvasByType(self.RAIL_ID, self.canvas)
        #         self.rail_y = round((event.y - self.imgPosition[1]) / self.showZoomRatio)
        #         self.RAIL_ID.append(
        #             self.canvas.create_line(0, event.y, self.show_img.size[0], event.y, width=2, fill='blue')
        #         )
        #     elif self.drawMode == OUTLINE_CALIBRATION:
        #         if self.outlines[0] != 0 and self.outlines[1] != 0 or len(self.OUTLINE_ID) > 1:
        #             self.outlines[0] = 0
        #             self.outlines[1] = 0
        #             self.cleanCanvasByType(self.OUTLINE_ID, self.canvas)
        #         if self.outlines[0] == 0:
        #             self.outlines[0] = round((event.y - self.imgPosition[1]) / self.showZoomRatio)
        #         elif self.outlines[1] == 0:
        #             self.outlines[1] = round((event.y - self.imgPosition[1]) / self.showZoomRatio)
        #         # print(self.outlines)
        #         self.OUTLINE_ID.append(
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
        #             self.cleanCanvasByType(self.CAR_ID, self.canvas)
        #             _new = self.canvas.create_rectangle(
        #                 # self.coords[0][0] + bbox[0], self.coords[0][1] + bbox[1],
        #                 self.coords[0][0], self.coords[0][1],
        #                 event.x, event.y,
        #                 width=2,
        #                 outline='red'
        #             )
        #             self.CAR_ID.append(_new)
        #             # print('img > ', self.canvas.bbox(self.IMG_ID[0]))
        #             # print('add > ', self.canvas.bbox(_new))
        #             self.coords.clear()

    def eCanvasButton_1_release(self, event):
        if len(self.coords) > 1:
            self.coords.clear()

    def eCanvasButton_1_move(self, event):
        if self.drawMode == 1:
            self.cleanCanvasByType(self.CAR_ID, self.canvas)
            self.CAR_ID.append(
                self.canvas.create_rectangle(
                    (self.coords[0][0], self.coords[0][1]),
                    (event.x, event.y),
                    width=2,
                    outline='red'
                )
            )
        self.cleanCanvasByType(self.CONSULT_ID, self.canvas)
        bbox = self.canvas.bbox(self.IMG_ID[0])
        self.CONSULT_ID.append(
            self.canvas.create_line(
                bbox[0], event.y, bbox[2], event.y, width=2, fill='yellow', dash=(6,6)
            )
        )
        self.CONSULT_ID.append(
            self.canvas.create_line(
                event.x, bbox[1], event.x, bbox[3], width=2, fill='yellow', dash=(6,6)
            )
        )

    def _create_point(self, x, y, r, **kwargs):
        #   画圆 point
        # self._create_point(500,300,2,fill='red')
        self.POINT_ID.append(self.canvas.create_oval(x - r, y - r, x + r, y + r, **kwargs))


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
        _id = _k + '_' + '_'.join(v)
        return _id

    def analyzeCalibrationFile(self):
        for _line in self.calibrationHelper.dictPhototype.keys():
            # _group = self._getKinds(_line, self.algor_y)
            if '_' not in _line:
                continue
            _group = self._getKinds(_line, self.algor_y_h)
            self.groupByCalibration[_line] = self._frequency(_group)
        self.isCalibrationFileReady = True

    def _getKinds(self, _line, func):
        _kinds = list()
        for kind in self.calibrationHelper.dictPhototype[_line]:
            if kind.tag != 'carcz' or kind.get('cztype') == '': continue
            _kinds.append(str(kind.get('cztype')))
        return func(_line, _kinds)
    
    def algor_y_h(self, _line, kinds):
        self.step_value = 0.0625
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
        self.step_value = 0.03125
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
            self.sideinfo()

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

    def outline(self, line, kind=None, _new=None):
        xOutlineTop = ".t_top"
        xOutlineBottom = ".t_bottom"
        if kind is not None:
            _kind = self._getNewCode(kind)
            xCarcz = '.carcz[@cztype="' + str(_kind) + '"]'
        # xOutlineMiddle = ".t_middle"
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
        # nodeTop = _parent.find(xOutlineTop)
        # nodeBottom = _parent.find(xOutlineBottom)
        # nodeMiddle = _parent.find(xOutlineMiddle)
        if _new is None:
            if node is not None:
                _top = int(node.find(xOutlineTop[1:]).text)
                _bottom = int(node.find(xOutlineBottom[1:]).text)
                return _top, _bottom
            # _r = list()
            # _r.append(int(nodeTop.text) if nodeTop is not None else 0)
            # _r.append(int(nodeBottom.text) if nodeBottom is not None else 0)
            # # _r.append(int(nodeMiddle.text) if nodeMiddle is not None else 0)
            # return _r
            else:
                return 0,0
        else:
            if node is None:
                _new_kind = ET.SubElement(_parent, 'carcz')
                _new_kind.set('cztype', str(_kind))
                _new_kind.set('create_date', util._gettime(_type='file'))
                _new_kind.set('modify_date', util._gettime(_type='file'))
                _new_kind.set('modify_mode', 'Manual')
                eletop = ET.SubElement(_new_kind, xOutlineTop[1:])
                eletop.text = str(_new[0])
                elebottom = ET.SubElement(_new_kind, xOutlineBottom[1:])
                elebottom.text = str(_new[1])
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
def start():
    m = Tk()
    m.title('车型自动标定工具')
    _main = main(m)
    m.mainloop()
def test():
    c = calibration('F:/data/05车型标定文件/唐官屯/CarPositionInformation_唐官屯 - 副本.config')
    c.build(1, '3', lTag='L')
if __name__ == '__main__':
    start()
    # test()