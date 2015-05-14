import sys
from os import listdir
from collections import OrderedDict
from os.path import isfile, join, dirname, splitext
import operator
import re
from PyQt4 import QtGui, QtCore

from converter import Shot, Diagram
import precessing as proc
from lists import ThumbListWidget, OrderedSet
# from plotter import PointBrowser

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import numpy as np

class FiltersPopup(QtGui.QDialog):
    def __init__(self, filters=None):
        self.filter_dict = filters

        QtGui.QWidget.__init__(self)
        #filters list
        self.filters = QtGui.QListWidget()
        self.filters.setMaximumSize(200, 100000)
        self.filters.setMinimumSize(100, 0)
        self.filters.addItems(list(filters.keys()))
        self.filters.itemClicked.connect(self.clickItem)

        #button actions
        self.layout2 = QtGui.QGridLayout()
        self.addButton = QtGui.QPushButton('add', self)
        self.addButton.clicked.connect(self.addFilter)
        self.deleteButton = QtGui.QPushButton('delete', self)
        self.deleteButton.clicked.connect(self.deleteFilter)
        self.layout2.addWidget(self.addButton, 0, 0)
        self.layout2.addWidget(self.deleteButton, 1, 0)

        #edit actions
        self.layout3 = QtGui.QGridLayout()
        self.filter_name = QtGui.QLineEdit('Name', self)
        self.filter_data = QtGui.QTextEdit('Filter', self)
        self.apply_data = QtGui.QPushButton('Apply', self)
        self.apply_data.clicked.connect(self.applyData)
        self.layout3.addWidget(self.filter_name, 0, 0)
        self.layout3.addWidget(self.filter_data, 1, 0)
        self.layout3.addWidget(self.apply_data, 4, 0)
        self.filter_data.hide()
        self.filter_name.hide()
        self.apply_data.hide()

        #show filters value
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.filters, 0, 1)
        self.layout.addLayout(self.layout2, 0, 0)
        self.layout.addLayout(self.layout3, 0, 2)
        self.setLayout(self.layout)

    def addFilter(self):
        name = "New Filter  "
        tmp = 1
        while name in self.filter_dict:
            name = name[:-1] + str(tmp)
            tmp += 1
        self.filters.addItem(name)
        self.filter_dict[name] = ""

    def deleteFilter(self):
        curv = self.filters.currentItem().text()
        del self.filter_dict[curv]
        self.filters.clear()
        self.filters.addItems(list(self.filter_dict.keys()))

    def clickItem(self):
        self.filter_name.show()
        self.filter_data.show()
        self.apply_data.show()
        self.filter_name.setText(self.filters.currentItem().text())
        self.filter_data.setText(self.filter_dict[self.filters.currentItem().text()])

    def applyData(self):#настройка фильтров
        curv = self.filters.currentItem().text()
        del self.filter_dict[curv]
        self.filter_dict[self.filter_name.text().strip()] = self.filter_data.toPlainText().strip()
        self.filters.clear()
        self.filters.addItems(list(self.filter_dict.keys()))

    def getValues(self):
        with open("filters.conf", "w") as otp:
            otp.write(str(len(self.filter_dict)))
            otp.write("\n")
            for key, value in self.filter_dict.items():
                otp.write(str(key)+"\n")
                otp.write(str(value)+"\n")
        return self.filter_dict


class Window(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.shot = None  #opened shot
        self.folder_name = ''  #folder to search for shots
        self.current_num = 0  #current diagram
        self.currently_selected = None  #selected point plot
        self.selected_points = OrderedSet()  #point to be added
        self.current_point = None  #plot of current point
        self.overall_selected = None  #points added to selected list
        #super(Window, self).__init__(parent)
        # a figure instance to plot on
        self.figure = plt.figure()

        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setParent(parent)
        self.canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.canvas.setFocus()
        self.canvas.setMinimumSize(500, 0)
        self.canvas.mpl_connect('pick_event', self.on_pick)
        self.canvas.mpl_connect('motion_notify_event', self.on_move)
        self.canvas.hide()

        # this is the Navigation widget
        # it takes the Canvas widget and a pa rent
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.hide()

        # Show files widget
        self.files = QtGui.QListWidget()
        self.files.itemDoubleClicked.connect(self.select_file)
        self.files.setMaximumSize(200, 100000)
        self.files.setMinimumSize(100, 0)
        self.files.hide()

        # Show selected points
        self.points = ThumbListWidget(self)
        #self.points.itemDoubleClicked.connect(self.unselect_point)
        self.points.itemClicked.connect(self.points_clicked)
        self.points.itemDoubleClicked.connect(self.points_doubleclicked)
        self.points.setMaximumSize(200, 100000)
        self.points.setMinimumSize(100, 0)
        self.points.hide()

        #Show diagram widget
        self.diagrams_points = None
        self.diagrams = QtGui.QListWidget()
        self.diagrams.itemClicked.connect(self.select_item)
        self.diagrams.setMaximumSize(250, 100000)
        self.diagrams.setMinimumSize(190, 0)
        self.diagrams.hide()

        #save result button
        self.save_button = QtGui.QPushButton('Add time point', self)
        self.save_button.clicked.connect(self.add_time)
        self.save_button.hide()

        #filter menu
        self.filters_button = QtGui.QPushButton('Manage filters', self)
        self.filters_button.clicked.connect(self.show_filters)
        self.filters_button.hide()
        self.filters = OrderedDict
        self.read_filters()


        #diagramms
        self.bottom_layout = QtGui.QGridLayout()
        self.diagrams_figure = plt.figure()
        self.diagrams_canvas = FigureCanvas(self.diagrams_figure)
        self.diagrams_canvas.setParent(parent)
        self.diagrams_canvas.setMinimumSize(250, 250)
        self.diagrams_canvas.setMaximumSize(500, 500)
        self.diagrams_canvas.mpl_connect('pick_event', self.on_pick2)
        self.diagrams_toolbar = NavigationToolbar(self.diagrams_canvas, self)
        self.diagrams_toolbar.setMaximumWidth(250)
        self.diagrams_ax = self.diagrams_figure.add_subplot(111)
        #self.diagrams_ax.set_ylim(ymin=0)
        #self.diagrams_ax.set_xlim(xmin=0)
        self.diagrams_canvas.draw()

        self.enlargre_button = QtGui.QPushButton('Enlarge diagram', self)
        self.enlargre_button.clicked.connect(self.enlarge_diagram)

        self.bottom_layout.addWidget(self.diagrams_toolbar, 0, 2)
        self.bottom_layout.addWidget(self.diagrams_canvas, 1, 2, QtCore.Qt.AlignRight)
        self.bottom_layout.addWidget(self.enlargre_button, 0, 1)

        # set the layout
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.filters_button, 0, 1)
        self.layout.addWidget(self.toolbar, 0, 2)
        self.layout.addWidget(self.canvas, 1, 2)
        self.layout.addWidget(self.diagrams, 1, 1)
        self.layout.addWidget(self.files, 1, 0)
        self.layout.addWidget(self.points, 1, 3)
        self.layout.addWidget(self.save_button, 0, 3)
        self.layout.addLayout(self.bottom_layout, 2, 2)
        self.setLayout(self.layout)


    def enlarge_diagram(self): #меняет местами диаграммы
        pass

    def points_doubleclicked(self):
        if self.points._mouse_button == 1:
            num = self.points.currentRow()
            point = list(self.selected_points)[num]
            diag = self.shot.get_diagram(self.current_num)

            xs = np.array(diag.x)
            ys = np.array(diag.y)

            idx = np.absolute(xs - point[0]).argmin()

            npoint = (xs[idx], ys[idx], self.current_num, self.shot.file[0])
            for point in list(self.selected_points):
                if point[2] == self.current_point[2] and point[3] == self.current_point[3]:
                    self.selected_points.remove(point)
            self.selected_points.add(npoint)
            self.refresh_points()
    def update_diagrams(self):
        pass

    def process_flux(self, dependency=proc.build_beta_density_dependency):
        names = []
        for i in range(self.files.count()):
            names.append(join(self.folder_name, self.files.item(i).text()))
        xlabel, ylabel, points = dependency(names, 200000)
        self.diagrams_points = points
        x_nbi = [t.properties[xlabel] for t in points if t.properties['nbi']]
        y_nbi = [t.properties[ylabel] for t in points if t.properties['nbi']]

        x_oh = [t.properties[xlabel] for t in points if not t.properties['nbi']]
        y_oh = [t.properties[ylabel] for t in points if not t.properties['nbi']]

        # print(len(x))
        # print(len(y))
        # print(x)
        self.diagrams_ax.plot(x_oh, y_oh, 'bo', ms=5, alpha=0.8, markersize=5, picker=6)
        self.diagrams_ax.plot(x_nbi, y_nbi, 'ro', ms=5, alpha=0.8, markersize=5, picker=6)
        self.diagrams_canvas.draw()
        pass



    def points_clicked(self):#один клик, правая кнопка - удалить точку, левая - подсветить
        if self.points._mouse_button == 1:
            num = self.points.currentRow()
            point = list(self.selected_points)[num]
            diag = self.shot.get_diagram(self.current_num)

            xs = np.array(diag.x)
            ys = np.array(diag.y)

            idx = np.absolute(xs - point[0]).argmin()

            self.highlight.set_xdata([xs[idx]])
            self.highlight.set_ydata([ys[idx]])
        else:
            self.unselect_point(None)


    def read_filters(self):
        with open("filters.conf") as inp:
            lines = inp.readlines()
        n = int(lines[0])
        mass = []
        for i in range(n):
            mass.append((lines[2*i+1].strip(), lines[2*(i+1)].strip()))
        self.filters = OrderedDict(mass)


    def show_filters(self):
        self.f = FiltersPopup(self.filters)
        self.f.setGeometry(100, 100, 400, 200)
        self.f.exec_()
        self.filters = self.f.getValues()
        self.show_diagrams()



    def add_time(self):
        time, ok = QtGui.QInputDialog.getText(self, 'Time point', 'enter time point in seconds(e.g. 0.123):')
        if ok:
            if time.isdigit:
                diag = self.shot.get_diagram(self.current_num)

                xs = np.array(diag.x)
                ys = np.array(diag.y)

                idx = np.absolute(xs - float(time)/1000).argmin()

                npoint = (xs[idx], ys[idx], self.current_num, self.shot.file[0])
                for point in list(self.selected_points):
                    if point[2] == self.current_point[2] and point[3] == self.current_point[3]:
                        print("wololololololo")
                        self.selected_points.remove(point)
                self.selected_points.add(npoint)
                self.refresh_points()

    def select_item(self, current):
        self.figure.clf()
        name = self.diagrams.currentItem().text()
        names = self.shot.get_diagram_names()
        if name in names:
            self.current_num = names.index(name)
        else:
            self.current_num = names.index("".join(name.split(':')[1:])[1:])
        self.plot(self.shot.get_diagram(self.current_num))

    def unselect_point(self, current):
        num = self.points.currentRow()
        self.selected_points.remove(list(self.selected_points)[num])
        self.refresh_points()

    def select_file(self, current):
        self.figure.clf()
        self.show_shot(Shot(join(self.folder_name, self.files.currentItem().text())))
        self.canvas.setFocus()

    def on_pick(self, event): #Pick points on main graph
        print(self.selected_points)
        if self.current_point in self.selected_points:
            self.selected_points.remove(self.current_point)
        else:
            for point in list(self.selected_points):
                if point[2] == self.current_point[2] and point[3] == self.current_point[3]:
                    print("wololo")
                    self.selected_points.remove(point)
            self.selected_points.add(self.current_point)
        self.refresh_points()

    def on_pick2(self, event):
        thisline = event.artist
        xdata, ydata = thisline.get_data()
        ind = event.ind

        x, y = xdata[ind], ydata[ind]
        for point in self.diagrams_points:
            if x == point.t:
                print(point.t)
                print(point.file)


    def refresh_points(self):
        self.update_diagramms()
        self.points.clear()
        self.points.addItems([str(x[0]) for x in self.selected_points])
        self.overall_selected.set_xdata(self.active_points[0])
        self.overall_selected.set_ydata(self.active_points[1])


    def on_move(self, event):
        # get the x and y pixel coords
        x, y = event.x, event.y

        if event.inaxes:
            ax = event.inaxes  # the axes instance
            diag = self.shot.get_diagram(self.current_num)

            xs = np.array(diag.x)
            ys = np.array(diag.y)

            idx = np.absolute(xs - event.xdata).argmin()
            self.currently_selected.set_xdata([diag.x[idx]])
            self.currently_selected.set_ydata([diag.y[idx]])
            self.current_point = (diag.x[idx], diag.y[idx], self.current_num, self.shot.file[0])
            self.canvas.draw()

    @property
    def active_points(self):
        x = [x[0] for x in self.selected_points if x[2] == self.current_num and x[3] == self.shot.file[0]]
        y = [x[1] for x in self.selected_points if x[2] == self.current_num and x[3] == self.shot.file[0]]
        return x, y

    def plot(self, diagram=None):
        # create an axis
        ax = self.figure.add_subplot(111)

        # discards the old graph


        #pridicted max value
        ind = np.argmax(np.array(diagram.y))
        # plot data
        if diagram:
            self.highlight, = ax.plot([diagram.x[ind]], [diagram.y[ind]], 'bo', ms=12, alpha=0.8, markersize=8)
            ax.plot(diagram.x, diagram.y, 'b-')
            self.currently_selected, = ax.plot([diagram.x[ind]], [diagram.y[ind]], 'yo', ms=12, alpha=0.6, markersize=6,
                                               picker=15)
            self.overall_selected, = ax.plot(self.active_points[0], self.active_points[1], 'ro', ms=12, alpha=0.9,
                                             markersize=4)
            ax.set_xlabel('t, sec')
            ax.set_ylabel(diagram.unit)
            ax.set_title(diagram.comment)
            self.figure.tight_layout()
        # refresh canvas
        self.canvas.draw()

    def show_diagrams(self):
        names = self.shot.get_diagram_names()
        self.diagrams.clear()
        res = set()
        for x in names:
            for name, reg in self.filters.items():
                try:
                    if re.compile(reg).match(x):
                        res.add(str(name) + ': ' + str(x))
                        break
                except:
                    pass
        #self.diagrams.addItems(list(names))
        self.diagrams.addItems(list(res))
        self.diagrams.show()

    def show_shot(self, shot):
        self.shot = shot
        self.show_diagrams()
        self.toolbar.show()
        self.canvas.show()
        self.files.show()
        self.points.show()
        self.save_button.show()
        self.filters_button.show()
        self.current_num = 0
        self.plot(self.shot.get_diagram(0))
        self.canvas.setFocus()



class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.window = Window(self)
        #self.diagramms = DiagramWindow(self)
        self.initUI()
        self.setCentralWidget(self.window)

    def initUI(self):
        # exit programm action
        exitAction = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)

        #open file action
        openAction = QtGui.QAction(QtGui.QIcon('icons/open-file-icon.png'), 'Open', self)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open file')
        openAction.triggered.connect(self.openFile)

        #save file action
        saveAction = QtGui.QAction(QtGui.QIcon('icons/save-file-icon.png'), 'Save', self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.setStatusTip('Save time points')
        saveAction.triggered.connect(self.saveFile)

        #open points action
        openPointsAction = QtGui.QAction(QtGui.QIcon('icons/open-file-icon.png'), 'Open points', self)
        openPointsAction.setStatusTip('Open time points')
        openPointsAction.triggered.connect(self.openPoints)

        #process flux operation
        processFluxDensityAction = QtGui.QAction(QtGui.QIcon('icons/open-file-icon.png'), 'Process flux(density)', self)
        processFluxDensityAction.setStatusTip('Open file first')
        processFluxDensityAction.triggered.connect(self.processFlux_density)

        processFluxBetaAction = QtGui.QAction(QtGui.QIcon('icons/open-file-icon.png'), 'Process beta(density)', self)
        processFluxBetaAction.setStatusTip('Open file first')
        processFluxBetaAction.triggered.connect(self.processFlux_beta)

        processFluxTauAction = QtGui.QAction(QtGui.QIcon('icons/open-file-icon.png'), 'Process confinement time(density)', self)
        processFluxTauAction.setStatusTip('Open file first')
        processFluxTauAction.triggered.connect(self.processFlux_conf)
        self.statusBar()

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(exitAction)
        fileMenu.addAction(saveAction)
        fileMenu.addAction(openPointsAction)

        operations = menubar.addMenu("&Operations")
        operations.addAction(processFluxDensityAction)
        operations.addAction(processFluxBetaAction)
        operations.addAction(processFluxTauAction)

        toolbar = self.addToolBar('Exit')
        toolbar.addAction(openAction)
        toolbar.addAction(exitAction)
        toolbar.addAction(saveAction)

        self.setGeometry(200, 200, 600, 700)
        self.setWindowTitle('SHTty Viewer')
        self.show()

    def openFile(self):
        file_name = QtGui.QFileDialog.getOpenFileName(self, 'Open File', filter='*.sht')
        folder_name = dirname(file_name)
        if folder_name:
            folder_name += '/'
        else:
            return
        self.window.folder_name = folder_name
        self.window.files.clear()
        self.window.show_shot(Shot(file_name))

        files = [f for f in listdir(folder_name) if
                 isfile(join(folder_name, f)) and splitext(f)[1].upper() == '.SHT']

        self.window.files.addItems(files)

    def openPoints(self):
        file_name = QtGui.QFileDialog.getOpenFileName(self, 'Open points file', filter='*.txt')
        with open(file_name) as inp:
            lines = inp.readlines()
            points = []
            for line in lines:
                tmp = line.strip().split()
                points.append((float(tmp[0]), float(tmp[1]), int(tmp[2]), tmp[3]))
        self.window.selected_points = points
        self.window.refresh_points()

    def saveFile(self):
        file_name = QtGui.QFileDialog.getSaveFileName(self, 'Save File', filter='*.txt')
        with open(file_name, 'wt') as otp:
            points = list(self.window.selected_points)
            points.sort(key=operator.itemgetter(3))
            for i, point in enumerate(points):
                s = " ".join([str(x) for x in point])
                otp.write(s)
                otp.write('\n')

    def closeEvent(self, QCloseEvent):
        plt.close(self.window.diagrams_figure)
        plt.close(self.window.figure)
        QCloseEvent.accept()

    def processFlux_density(self):
        if not self.window.folder_name:
            self.openFile()
        self.window.process_flux(proc.build_flux_nl_dependency)

    def processFlux_beta(self):
        if not self.window.folder_name:
            self.openFile()
        self.window.process_flux(proc.build_beta_density_dependency)

    def processFlux_conf(self):
        if not self.window.folder_name:
            self.openFile()
        self.window.process_flux(proc.build_tau_density_dependency)
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    shot = Shot("sht08965.sht")

    main = MainWindow()
    # main.window.show_shot(shot)
    #main.show()

    sys.exit(app.exec_())