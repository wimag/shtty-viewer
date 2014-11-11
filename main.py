import sys
from os import listdir
from os.path import isfile, join, dirname, splitext
import operator
from PyQt4 import QtGui, QtCore

from converter import Shot, Diagram
# from plotter import PointBrowser

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import numpy as np


class Window(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.shot = None  #opened shot
        self.folder_name = ''  #folder to search for shots
        self.current_num = 0  #current diagram
        self.currently_selected = None  #selected point plot
        self.selected_points = set()  #point to be added
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
        self.points = QtGui.QListWidget()
        self.points.itemDoubleClicked.connect(self.unselect_point)
        self.points.setMaximumSize(200, 100000)
        self.points.setMinimumSize(100, 0)
        self.points.hide()

        #Show diagram widget
        self.diagrams = QtGui.QListWidget()
        self.diagrams.itemClicked.connect(self.select_item)
        self.diagrams.setMaximumSize(250, 100000)
        self.diagrams.setMinimumSize(190, 0)
        self.diagrams.hide()

        #save result button
        self.save_button = QtGui.QPushButton('Clear time points', self)
        self.save_button.clicked.connect(self.clear_times)
        self.save_button.hide()

        # set the layout
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.toolbar, 0, 2)
        self.layout.addWidget(self.canvas, 1, 2)
        self.layout.addWidget(self.diagrams, 1, 1)
        self.layout.addWidget(self.files, 1, 0)
        self.layout.addWidget(self.points, 1, 3)
        self.layout.addWidget(self.save_button, 0, 3)
        self.setLayout(self.layout)

    def clear_times(self):
        self.selected_points.clear()
        self.refresh_points()

    def select_item(self, current):
        self.figure.clf()
        self.current_num = self.diagrams.currentRow()
        self.plot(self.shot.get_diagram(self.current_num))

    def unselect_point(self, current):
        num = self.points.currentRow()
        self.selected_points.remove(list(self.selected_points)[num])
        self.refresh_points()

    def select_file(self, current):
        self.figure.clf()
        self.show_shot(Shot(join(self.folder_name, self.files.currentItem().text())))
        self.canvas.setFocus()

    def on_pick(self, event):
        print(self.current_point)
        if self.current_point in self.selected_points:
            self.selected_points.remove(self.current_point)
        else:
            self.selected_points.add(self.current_point)
        self.refresh_points()

    def refresh_points(self):
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
            xa = max(np.absolute(xs))
            ya = max(np.absolute(ys))
            xs = xs / xa
            ys = ys / ya

            idx = (np.hypot(xs - event.xdata / xa, ys - event.ydata / ya)).argmin()
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
            ax.plot([diagram.x[ind]], [diagram.y[ind]], 'bo', ms=12, alpha=0.8, markersize=8)
            ax.plot(diagram.x, diagram.y, 'b-')
            self.currently_selected, = ax.plot([diagram.x[ind]], [diagram.y[ind]], 'yo', ms=12, alpha=0.6, markersize=6,
                                               picker=15)
            self.overall_selected, = ax.plot(self.active_points[0], self.active_points[1], 'ro', ms=12, alpha=0.9,
                                             markersize=4)
            ax.set_xlabel('t, sec')
            ax.set_ylabel(diagram.unit)
            ax.set_title(diagram.comment)
            plt.tight_layout()
        # refresh canvas
        self.canvas.draw()


    def show_shot(self, shot):
        self.shot = shot
        self.diagrams.clear()
        self.diagrams.addItems(shot.get_diagram_names())
        self.toolbar.show()
        self.canvas.show()
        self.diagrams.show()
        self.files.show()
        self.points.show()
        self.save_button.show()
        self.current_num = 0
        self.plot(self.shot.get_diagram(0))
        self.canvas.setFocus()


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.window = Window(self)
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
        saveAction.setStatusTip('Save tome points')
        saveAction.triggered.connect(self.saveFile)

        self.statusBar()

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(exitAction)
        fileMenu.addAction(saveAction)

        toolbar = self.addToolBar('Exit')
        toolbar.addAction(openAction)
        toolbar.addAction(exitAction)
        toolbar.addAction(saveAction)

        self.setGeometry(200, 200, 600, 450)
        self.setWindowTitle('SHTty Viewer')
        self.show()

    def openFile(self):
        file_name = QtGui.QFileDialog.getOpenFileName(self, 'Open File', filter='*.sht')
        folder_name = dirname(file_name)
        if folder_name:
            folder_name += '/'
        else:
            return
        print(folder_name)
        self.window.folder_name = folder_name
        self.window.files.clear()
        self.window.show_shot(Shot(file_name))

        files = [f for f in listdir(folder_name) if
                 isfile(join(folder_name, f)) and splitext(f)[1].upper() == '.SHT']

        self.window.files.addItems(files)

    def saveFile(self):
        file_name = QtGui.QFileDialog.getSaveFileName(self, 'Save File', filter='*.txt')
        with open(file_name, 'wt') as otp:
            points = list(self.window.selected_points)
            points.sort(key=operator.itemgetter(3))
            for i, point in enumerate(points):
                if not i or point[3] != points[i-1][3]:
                    otp.write("\n")
                    otp.write(point[3])
                    otp.write("\n\n")
                otp.write(str(point[0]))
                otp.write("\n")


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    shot = Shot("sht08965.sht")

    main = MainWindow()
    # main.window.show_shot(shot)
    #main.show()

    sys.exit(app.exec_())