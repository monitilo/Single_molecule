"""
@author: Rodrigo, the one who never doment his code
@Remastered by: German, the non-serious commenter


User interface to detect particles in a movie
and extract its traces or spot intensities in a .txt file


For extract traces:
First, A custom sized Region Of Interest(ROI) of the hole image have to be created.
(can be of the same size of the total image if wanted)
-choose a start and end frame to average frames within that ROI 
and have a sharper image where to detect the particles
-"get ROI mean" returns the image of the averaged ROI, where
then the maximums will be detected.
For that you need to put (try by hand for the best ones):
- minimum distance between the max it will gonna find.
- threshold if you want. Only detect numbers grater that's this.
automaticaly change to the mean of the first frame when the file is loaded
-Size: the estimated size of your psf,
-bgsize: the pixels at each side of the roi to take the background
     Actually you have to put a good size to don't loose any photon.
- Detect Molecules: search all the local maximums in the ROI
averaged, at distances greater than minimun distance. Draw a
square size*size on each point detected.
subtract the calculated bakground from a square bgsize pixel more than the periphery
(size + bgsize)*(size + bgsize) - size*size. Normalized by size

-Export Traces: Save the .txt file with 1 column per particle.
    And a .png file with the image to use as reference

Spots intensities: 
    Just go to the frame you want to look for.
    select your parameters:
        - Choose a Minimun distance between maximum
        - Threshold if necessary. Only detect maximums greater than this
        - Size: the size of your PSF
        - backgroun pixels to each side of your roi.
    click detect Molecules.
See in the image all the detecctions.
    export intensities from that frame. All the detection you see (not red)
        Get one file with 1 colum with sum of all phothons in the roi, 
normalized by Background.
        And another "Morgane" file with 2 colums with the individual intensity 
of the roi and from the backgroun, per spot.

    And a .png file with the image to use as reference

despite the mode, you can add ROIs by hand, using the "New Small roi" button.
    When click that, a new roi is created in the top left of the image,
    and you move it around to the place you like. Then click it and this add 
    a new roi to the image*. Continue until you have all you like.
    (Right click if you want to delete them)
    *(do not have to be perfect if you the use the gaussi fit fixing)
Also, you can filter your detections using:
    - Gaussian fit: Make a 2D Gaussian fit inside each roi, and move it to the
center. If the diferences between sigmas (of the fit) is bigger that the 
imput number, then that spot is removed (apear in red)
    - Filter bg: Look at the intensity in the background pixels. If they are
bigger than the imput threshold, discard the spot (red again)

finally, you can make a Histogram of the spots detected just to quickly see.
If the histogram window is not close, you can add the new points to it. (clicking the button again)
if close, reestart the numbers


The last button "Crazy go", is not for public use. It take the imput number
to subdivide all the frames in this amount of steps and make a full histogram
of all the detected spots. It applies both filters: bg; gauss; bg again.

"""
#import sys  # to get the path and the name of the .py file runing
#print (sys.argv[0])
#print (os.path.basename(sys.argv[0]))


#            except Exception as e:
#                print(e.__class__)

import sys

import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
from skimage import io
from tkinter import Tk, filedialog
from skimage.feature import peak_local_max
import pyqtgraph.exporters

from scipy import ndimage as ndi
from scipy import optimize

import os
from pyqtgraph.dockarea import Dock, DockArea



#import time as time

channels = ["RED","GREEN","BLUE"]

class smAnalyzer(pg.Qt.QtGui.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major')

        # Define a top-level widget to hold everything
        self.w = QtGui.QWidget()
#        self.setCentralWidget(self.w)
        self.w.setWindowTitle('SMAnalyzer - Video')
        self.w.resize(20, 100)

        # Create ImageView
        self.imv = pg.ImageView()

        self.trace_widget = pg.GraphicsLayoutWidget()

        # Create buttons
        self.btn1 = QtGui.QPushButton('Load Image')
        self.btn2 = QtGui.QPushButton('Create a small Cut')
        self.btn3 = QtGui.QPushButton('Delete de Cut area')
#        self.btn4 = QtGui.QPushButton('Get ROI mean (Traces)')
        self.btn5 = QtGui.QPushButton('Back to complete image')
        self.btn6 = QtGui.QPushButton('Detect Molecules')
        self.btn7 = QtGui.QPushButton('Export Intensities')

        # Can put colors in the buttons
        self.btn99_clearall = QtGui.QPushButton('Clear all')
        self.btn99_clearall.setStyleSheet(
                "QPushButton { background-color: rgb(210, 30, 100); }"
                "QPushButton:pressed { background-color: red; }")

        self.btn_images = QtGui.QPushButton('image analysis')
        self.btn_images.setStyleSheet(
                "QPushButton { background-color: rgb(200, 200, 10); }"
                "QPushButton:pressed { background-color: blue; }")
        
        self.btn_small_roi = QtGui.QPushButton('New small ROI')
        self.btn_small_roi.setStyleSheet(
                "QPushButton { background-color: rgb(150, 200, 10); }")

        self.btn_gauss_fit = QtGui.QPushButton('Gaussian Fit (ctrl+g)')
        self.btn_gauss_fit.setStyleSheet(
                "QPushButton { background-color: rgb(202,0,202); }")

        self.btn_filter_bg = QtGui.QPushButton('Filter bg (ctrl+b)')

        self.btn_nospot_filter = QtGui.QPushButton('filter no spot (ctrl+n)')
        self.btn_nospot_filter.setStyleSheet(
                "QPushButton { background-color: rgb(72,209,204); }")

        # labels with a fixed width
        self.gauss_fit_label = QtGui.QLabel('sigma_X / sigma_Y ><')
        self.gauss_fit_edit = QtGui.QLineEdit('1.2')
        self.gauss_fit_edit.setFixedWidth(60)

        self.btn_histogram = QtGui.QPushButton('Make Histogram')
        self.btn_save_histogram = QtGui.QPushButton('Save Histogram')
        self.btn_save_histogram.setStyleSheet(
                "QPushButton { background-color: rgb(192, 192, 192); }")

#        self.crazyStepButton = QtGui.QPushButton('Crazy go')
#        self.crazyStepEdit = QtGui.QLineEdit('10')
#        self.crazyStepEdit.setFixedWidth(40)

        self.autoWeberButton = QtGui.QPushButton('Auto Weber')
        self.autoWeberButton.setStyleSheet(
                "QPushButton:pressed { background-color: blue; }")


        self.weberRoiStepEdit = QtGui.QLineEdit('10')
        self.weberRoiStepEdit.setFixedWidth(60)
#        self.crazyStepEdit = QtGui.QLineEdit('10')
#        self.crazyStepEdit.setFixedWidth(40)

        # Create parameter fields with labels
#        self.meanStartLabel = QtGui.QLabel('Start frame:')
#        self.meanStartEdit = QtGui.QLineEdit('5')
#        self.meanEndLabel = QtGui.QLabel('End frame:')
#        self.meanEndEdit = QtGui.QLineEdit('15')
        self.maxDistLabel = QtGui.QLabel('Minimum distance:')
        self.maxDistEdit = QtGui.QLineEdit('6')
        self.maxThreshLabel = QtGui.QLabel('Threshold:')
        self.maxThreshEdit = QtGui.QLineEdit('0')
        self.moleculeSizeLabel = QtGui.QLabel('Size (pix):')
        self.moleculeSizeEdit = QtGui.QLineEdit('15')
#        self.channelDifferenceLabel = QtGui.QLabel('Channel height difference (pixels):')
#        self.channelDifferenceEdit = QtGui.QLineEdit('0')
#        self.channelCorrectionLabel = QtGui.QLabel('Secondary Channel Correction:')
#        self.channelCorrectionEdit = QtGui.QLineEdit('0')

        self.BgSizeLabel = QtGui.QLabel('BackGround (size + 2N)')
        self.BgSizeEdit = QtGui.QLineEdit('3')
        self.BgSizeEdit.setFixedWidth(30)

        self.time_adquisitionLabel = QtGui.QLabel('Adquisition time (ms)')
        self.time_adquisitionEdit = QtGui.QLineEdit('100')

        self.see_labels_button = QtGui.QCheckBox('Labels? (ctrl+a)')
        self.see_labels_button.setChecked(True)


        self.label_save = QtGui.QLabel('File Name')
        self.label_save.resize(self.label_save.sizeHint())
        self.edit_save = QtGui.QLineEdit('Test')
        self.edit_save.resize(self.edit_save.sizeHint())
        self.edit_save.setToolTip('Selec a name to save the data.\
              The name automatically changes to not replace the previous one')


        self.label_dir_save = QtGui.QPushButton('Save folder')
#        self.label_dir_save.resize(self.label_dir_save.sizeHint())
        self.edit_dir_save = QtGui.QLineEdit(os.path.split(sys.argv[0])[0])
        self.edit_dir_save.resize(self.edit_dir_save.sizeHint())
        self.edit_dir_save.setToolTip('Selec the folder where save the data')

        self.channel_combobox = QtGui.QComboBox()
        self.channel_combobox.addItems(channels)
#        self.channel_combobox.setCurrentIndex(2)
        self.channel_combobox.setToolTip('Choose the channel I want to see')
        self.channel_combobox.setFixedWidth(80)
        self.channel_combobox.activated.connect(  # it calls the color function
                                    lambda: self.channel_menu(self.channel_combobox))
        self.channel_combobox.activated.connect(self.load_image)
        self.channel_menu(self.channel_combobox)  # it gives the starting color
        channel_label = QtGui.QLabel('<strong> Choose your channel')

        # Create a grid layout to manage the widgets size and position
#        self.layout = QtGui.QGridLayout()
#        self.w.setLayout(self.layout)

        self.viewer_grid = QtGui.QGridLayout()
        self.viewer_wid = QtGui.QWidget()
        self.viewer_wid.setLayout(self.viewer_grid)

        self.trace_grid = QtGui.QGridLayout()
        self.trace_wid = QtGui.QWidget()
        self.trace_wid.setLayout(self.trace_grid)

        self.options_grid = QtGui.QGridLayout()
        self.optios_wid = QtGui.QWidget()
        self.optios_wid.setLayout(self.options_grid)

        self.post_grid = QtGui.QGridLayout()
        self.post_wid = QtGui.QWidget()
        self.post_wid.setLayout(self.post_grid)

        # Add widgets to the layout in their proper positions 
        #                                       (-Y, X, Y_width ,X_width)
#        self.layout.addWidget(QtGui.QLabel(" "),       0, 0, 1, 3)
        self.options_grid.addWidget(self.time_adquisitionLabel,     0, 0, 1, 1)
        self.options_grid.addWidget(self.time_adquisitionEdit,      0, 1, 1, 2)

        self.options_grid.addWidget(self.btn1,               1, 0, 1, 3)
        self.options_grid.addWidget(self.btn2,               2, 0, 1, 3)
        self.options_grid.addWidget(self.btn3,               3, 0, 1, 3)

#        self.options_grid.addWidget(self.meanStartLabel,     4, 0, 1, 1)
#        self.options_grid.addWidget(self.meanStartEdit,      4, 1, 1, 2)
#        self.options_grid.addWidget(self.meanEndLabel,       5, 0, 1, 1)
#        self.options_grid.addWidget(self.meanEndEdit,        5, 1, 1, 2)
        self.options_grid.addWidget(channel_label,     4, 0, 1, 1)
        self.options_grid.addWidget(self.channel_combobox,      4, 1, 1, 1)

#        self.options_grid.addWidget(self.btn4,               6, 0, 1, 1)
        self.options_grid.addWidget(self.btn_images,         6, 2, 1, 1)
        
        self.options_grid.addWidget(self.btn5,               7, 0, 1, 3)
#        self.options_grid.addWidget(QtGui.QLabel(" "),       8, 0, 1, 3)
        
        self.options_grid.addWidget(self.maxDistLabel,       9, 0, 1, 1)
        self.options_grid.addWidget(self.maxDistEdit,        9, 1, 1, 2)
        self.options_grid.addWidget(self.maxThreshLabel,    10, 0, 1, 1)
        self.options_grid.addWidget(self.maxThreshEdit,     10, 1, 1, 2)
        self.options_grid.addWidget(self.moleculeSizeLabel, 11, 0, 1, 1)
        self.options_grid.addWidget(self.moleculeSizeEdit,  11, 1, 1, 2)
        self.options_grid.addWidget(self.BgSizeLabel,       12, 0, 1, 1)
        self.options_grid.addWidget(self.BgSizeEdit,        12, 1, 1, 2)
        
        self.options_grid.addWidget(self.btn6,              13, 0, 1, 3)
        self.options_grid.addWidget(self.btn99_clearall,    14, 2, 1, 1)
        self.options_grid.addWidget(self.btn7,              15, 0, 1, 3)


        self.viewer_grid.addWidget(self.label_save,          0, 4, 1, 5)
        self.viewer_grid.addWidget(self.edit_save,          0, 9, 1, 10)

        self.viewer_grid.addWidget(self.imv,               1, 4, 16, 16)

        self.viewer_grid.addWidget(self.label_dir_save,          17, 4, 1, 5)
        self.viewer_grid.addWidget(self.edit_dir_save,          17, 9, 1, 10)

        self.trace_grid.addWidget(self.trace_widget,      1, 4, 6, 6)

        self.post_grid.addWidget(self.see_labels_button,   3, 25, 1, 2)
        self.post_grid.addWidget(self.btn_small_roi,       4, 25, 1, 1)
        self.post_grid.addWidget(self.gauss_fit_label,     5, 25, 1, 1)
        self.post_grid.addWidget(self.gauss_fit_edit,      5, 26, 1, 1)
        self.post_grid.addWidget(self.btn_gauss_fit,       6, 25, 1, 2)
        self.post_grid.addWidget(self.btn_filter_bg,       8, 25, 1, 2)
        self.post_grid.addWidget(self.btn_nospot_filter,   10, 25, 1, 2)
        self.post_grid.addWidget(self.btn_histogram,      12, 25, 1, 2)
        self.post_grid.addWidget(self.btn_save_histogram, 13, 25, 1, 1)

#        self.post_grid.addWidget(self.crazyStepEdit,    14, 26, 1, 1)
#        self.post_grid.addWidget(self.crazyStepButton,  14, 25, 1, 1)
        self.post_grid.addWidget(self.autoWeberButton,  14, 25, 1, 1)
        self.post_grid.addWidget(self.weberRoiStepEdit, 14, 26, 1, 1)

        # button actions
        self.btn1.clicked.connect(self.importImage)
        self.btn2.clicked.connect(self.createROI)
        self.btn3.clicked.connect(self.deleteROI)
#        self.btn4.clicked.connect(self.ROImean)
        self.btn5.clicked.connect(self.showVideo)
        self.btn6.clicked.connect(self.detectMaxima)
        self.btn7.clicked.connect(self.exportTraces_or_images)

        self.label_dir_save.clicked.connect(self.save_folder_select)

        self.btn_images.clicked.connect(self.image_analysis)
        self.btn_small_roi.clicked.connect(self.create_small_ROI)
        self.btn_gauss_fit.clicked.connect(self.gaussian_fit_ROI)
        self.btn_filter_bg.clicked.connect(self.filter_bg)
        self.btn_nospot_filter.clicked.connect(self.filter_nospot)
        self.btn_histogram.clicked.connect(self.make_histogram)
        self.btn_save_histogram.clicked.connect(self.save_histogram)
#        self.crazyStepButton.clicked.connect(self.automatic_crazy_start)
        self.autoWeberButton.clicked.connect(self.automatic_weber_start)

        self.btn99_clearall.clicked.connect(self.clear_all)

        self.moleculeSizeEdit.textEdited.connect(self.update_size_rois)
        self.BgSizeEdit.textEdited.connect(self.update_size_rois)

        # a Python timer that call a function with a specific clock (later)
#        self.automatic_crazytimer = QtCore.QTimer()
#        self.automatic_crazytimer.timeout.connect(self.automatic_crazy)

        self.automatic_webertimer = QtCore.QTimer()
        self.automatic_webertimer.timeout.connect(self.automatic_weber)


        self.see_labels_button.clicked.connect(self.see_labels)
        self.see_labels_button.setChecked(True)

#        # DOCK cosas, mas comodo!
        self.state = None  # defines the docks state (personalize your oun UI!)

        self.cwidget = QtGui.QWidget()
        self.setCentralWidget(self.cwidget)

        grid = QtGui.QGridLayout()
        self.cwidget.setLayout(grid)

        dockArea = DockArea()
        self.dockArea = dockArea
        grid.addWidget(self.dockArea)

        viewDock = Dock('viewbox', size=(300, 50))
        viewDock.addWidget(self.viewer_wid)
#        viewDock.hideTitleBar()
        self.dockArea.addDock(viewDock)

        postDock = Dock('posDetection', size=(1, 1))
        postDock.addWidget(self.post_wid)
        self.dockArea.addDock(postDock, "right", viewDock)

        optionsDock = Dock('Load options', size=(1, 1))
        optionsDock.addWidget(self.optios_wid)
        self.dockArea.addDock(optionsDock, "left", viewDock)

        traceDock = Dock('Live Trace', size=(100, 10))
        traceDock.addWidget(self.trace_wid)
        self.dockArea.addDock(traceDock, "bottom", postDock)

#'bottom', 'top', 'left', 'right', 'above', or 'below'

        self.setWindowTitle("Single Molecule Analizer")  # Nombre de la ventana
        self.setGeometry(10, 40, 1600, 800)  # (PosX, PosY, SizeX, SizeY)

    # initialize  parameters. Remember, this is Just at start, never come here again.
        # Create empty ROI
        self.roi = None
        self.smallroi = None

        # Molecule ROI dictionary
        self.molRoi = dict()
        self.bgRoi = dict()
        self.new_roi = dict()
        self.new_roi_bg = dict()
        
        self.removerois = []

        # ROI label dictionary
        self.label = dict()
        
        # Initial number of maximums detected
        self.maxnumber = 0
        self.fixing_number = 0

        # Save file number

        self.is_image = False
        self.histo_data = False
        self.is_trace = False
        self.cuteado = False
        self.primera = True

    # Shortcuts
        self.bgfilter_Action = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('ctrl+b'), self, self.filter_bg)

        self.gaussfilter_Action = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('ctrl+g'), self, self.gaussian_fit_ROI)

        self.nonspotfilter_Action = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('ctrl+n'), self, self.filter_nospot)

        self.seelabels_Action = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('ctrl+a'), self, self.see_labels_shortcut)

        self.makehistogram_Action = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('ctrl+h'), self, self.make_histogram)

        np.warnings.filterwarnings('ignore')

    def importImage(self):  # connected to Load Image (btn1)
        """Select a file to analyse, can be a tif or jpg(on progres)
        the tiff data comes in a shape=(Frames, x, y) """

        self.JPG = False
        # Remove annoying empty window
        root = Tk()
        root.withdraw()

        # Select image from file
        self.f = filedialog.askopenfilename(filetypes=[("All", '*.tiff;*.tif;*.jpg;*.bmp'),
                                                       ("Videos", '*.tiff;*.tif'),
                                                       ("Pictures", "*.jpg")])

        if not self.f:
            print("You choosed nothing")
        else:
            self.file_path = self.f
            print("Choosed path: \n", self.file_path, "\n")
            self.file_name = os.path.split(self.file_path)[1][:-4]

            try: 
                print(len(io.imread(self.f)[0,0,:]), "channels")
                self.data = io.imread(self.f)[:, :, self.channel]
                self.edit_save.setText(self.file_name +"_"+ channels[self.channel])
            except:
                print("1D picture")
                self.data = io.imread(self.f)
                self.edit_save.setText(self.file_name)

            self.total_size = [self.data.shape[1], self.data.shape[0]]
            self.maxThreshEdit.setText(str(np.mean(self.data[:,:]))[:7])
            self.image_data = self.data


            # Delete existing ROIs
            self.deleteROI()
            self.clear_all()

            plot_with_colorbar(self.imv, self.image_data)

#            self.w.setWindowTitle('SMAnalyzer - Video - ' + self.f)


    def load_image(self):
        try:
            TeasteandoSiHayAlgunaImagen = self.f
            try:
    #                print(len(io.imread(self.f)[0,0,:]), "channels")
                self.data = io.imread(self.f)[:, :, self.channel]
                self.edit_save.setText(self.file_name +"_"+ channels[self.channel])

            except IndexError:
                print("1D picture, no changes")
                self.data = io.imread(self.f)

            self.total_size = [self.data.shape[1], self.data.shape[0]]
            self.maxThreshEdit.setText(str(np.mean(self.data[:,:]))[:7])
            self.image_data = self.data

            if self.roi == None:
                print("no zone cut")
            elif self.cuteado == True:
                print(self.cuted_pos, self.cuted_size)
                x, y = self.cuted_pos
                dx,dy = self.cuted_size
                x, y, dx, dy = int(x), int(y), int(dx), int(dy)

                self.image_data = self.data[y:y+dy, x:x+dx]
    #                self.image_analysis()

            plot_with_colorbar(self.imv, self.image_data)

            # Delete existing ROIs
    #            self.deleteROI()
    #            self.clear_all()

        except AttributeError:
            print("Need a image")

    def save_folder_select(self):
        """Select a folder to save """

        # Remove annoying empty window
        root = Tk()
        root.withdraw()

        # Select image from file
        self.folder = filedialog.askdirectory()

        if not self.folder:
            print("You choosed nothing")
        else:
#            self.file_path = self.f
#            print("Choosed path: \n", self.folder, "\n")
             self.edit_dir_save.setText(self.folder)



    def createROI(self):  # connected to Create ROI (btn2)
        """ create a big ROI to select the area to make the analysis
        default is the size of the picture"""
        if self.roi is None:
            self.roi = pg.ROI([0, 0], (self.total_size[0]/2, self.total_size[1]/2),
                              scaleSnap=True, translateSnap=True,
                              removable=True)  # [70, 70]
            self.roi.addScaleHandle([1, 1], [0, 0])
            self.roi.addScaleHandle([0, 0], [1, 1])
            self.imv.view.addItem(self.roi)
            self.roi.sigRemoveRequested.connect(self.deleteROI)
        else:
            pass

    def deleteROI(self):  # connected to Delete ROI (btn3)
        """ delete the big ROI"""
        if self.roi is None:
            pass
        else:
            self.imv.view.removeItem(self.roi)
            self.roi = None

    def showVideo(self):  # connected to Go to vide (btn5)
        """Get the original image back. Use this to came back from the 
        ROImean image.
        If you have rois in the mean image, they are moved with translatemaxima
        to the good positions in the origianl image. So you can follow them"""

        self.is_trace = False
        self.cuteado = False
        self.image_data = self.data
        plot_with_colorbar(self.imv, self.image_data)


#        self.w.setWindowTitle('SMAnalyzer - Video - ' + self.f)
#        self.meanEndEdit.setStyleSheet(" background-color: ; ")

        try:
            self.translateMaxima()
            self.imv.view.addItem(self.roi)
        except:
            pass

    def translateMaxima(self):  # go to video call this function
        """ translate the position from the big ROI in to the video again"""
        # TODO: Falta lograr que cuando hago el corte, los rois que estan se coincidan
        # asi puedo hacer zoom in/out sin que nada cambie. 

        for i in range(len(self.molRoi)):  # np.arange(0, self.maxnumber):
            self.molRoi[i].translate(self.roi.pos())
            self.bgRoi[i].translate(self.roi.pos())
            self.label[i].setPos(self.molRoi[i].pos())
            try:
                self.gauss_roi[i].translate(self.roi.pos())
            except:
                pass

        self.relabel_new_ROI()
        self.btn3.setEnabled(True)

    def translateMaximaIN(self):  # go to video call this function
        """ translate the position from the big ROI in to the video again"""

        for i in range(len(self.molRoi)):  # np.arange(0, self.maxnumber):
            self.molRoi[i].translate(-self.roi.pos())
            self.bgRoi[i].translate(-self.roi.pos())
            self.label[i].setPos(self.molRoi[i].pos())
            try:
                self.gauss_roi[i].translate(-self.roi.pos())
            except:
                pass


        self.relabel_new_ROI()


    def detectMaxima(self):  # connected to Detect Molecules (btn6)
        """here is where the magic begins...
        if you did not had already created self.image_data
        it use the actual frame to see spots (Standar = image mode).
        Then, for each spot, creates a square roi of side size(=imput)
        and another roi bigger (also imput) to the background """

#        self.clear_all()
        self.dist = int(self.maxDistEdit.text())
        self.threshold = float(self.maxThreshEdit.text())

        # set roi Dimension array
        self.roiSize = [int(self.moleculeSizeEdit.text())] * 2
        self.bgroiSize = np.array(self.roiSize) + 2* int(self.BgSizeEdit.text())  # s pixel each side
        center = int(self.BgSizeEdit.text()) * np.array([1, 1])

        # find the local peaks
        self.maximacoord = peak_local_max(self.image_data, min_distance=self.dist, threshold_abs=self.threshold)

        maxvalues = []
        for i in range(len(self.maximacoord[:,0])):
            maxvalues.append(self.image_data[self.maximacoord[i,0], self.maximacoord[i,1]])

        # filter spurious peaks taking only the brighters ones
        nomaxlow = np.where(np.array(maxvalues) < np.mean(maxvalues))[0]
        print("len maxvalues", len(maxvalues))
        print("nomaxlow", len(nomaxlow))
        
        aux = np.arange(len(maxvalues))
        goodmax = np.delete(aux,nomaxlow)

        # Can do the same for the very brighter spots, but don't wanna
#        nomaxhigh = np.where(np.array(maxvalues) > 1.5*np.mean(np.array(maxvalues)[goodmax]))
#        toerase = np.sort(np.append(nomaxlow, nomaxhigh))

        maxindex = goodmax  # np.delete(aux,toerase)   NOT Nice for now

        print(len(goodmax), "good points finded")

        self.maxnumber = np.size(self.maximacoord[maxindex], 0)

        p = 0  
        print(self.fixing_number, "old points added")
        # I move my start because of the fixing number, so need to use p=0
        for i in np.arange(0, self.maxnumber)+self.fixing_number:

            # Translates molRoi to particle center
            corrMaxima = np.flip(self.maximacoord[maxindex[p]], 0) - 0.5*np.array(self.roiSize) + [0.5, 0.5]
            self.molRoi[i] = pg.ROI(corrMaxima, self.roiSize,scaleSnap=True,
                           translateSnap=True, movable=False, removable=True)
            self.bgRoi[i] = pg.ROI((corrMaxima - center), self.bgroiSize,
                                          scaleSnap=True, translateSnap=True,
                                          movable=False, removable=True)
            self.imv.view.addItem(self.molRoi[i])
            self.imv.view.addItem(self.bgRoi[i])

            self.molRoi[i].sigRemoveRequested.connect(self.remove_ROI)
            self.bgRoi[i].sigRemoveRequested.connect(self.remove_ROI)

            # Create ROI label
            self.label[i] = pg.TextItem(text=str(i))
            self.label[i].setPos(self.molRoi[i].pos())
            if self.see_labels_button.isChecked():
                self.imv.view.addItem(self.label[i])
            p+=1
        try:
            self.fixing_number = i + 1
        except:
            print("ZERO points finded. ZERO!!")
        self.relabel_new_ROI()

    def update_size_rois(self):
        roiSize = (int(self.moleculeSizeEdit.text()))
        bgroiSize = roiSize + 2* int(self.BgSizeEdit.text())  # s pixel each side
        try:
            center = ((roiSize - self.roiSize[0])/2) * np.array([1, 1])
        except:
            self.roiSize = [int(self.moleculeSizeEdit.text())] * 2
            center = ((roiSize - self.roiSize[0])/2) * np.array([1, 1])
        centerbg = int(self.BgSizeEdit.text()) * np.array([1, 1])

        try:
            posold = self.smallroi.pos()
            self.smallroi.setSize(roiSize, roiSize)
            self.smallroi.setPos(posold-center)
        except:
            pass
        try:
            for i in range(len(self.molRoi)):
                if i not in self.removerois:
                    posold = self.molRoi[i].pos()
                    self.molRoi[i].setSize(roiSize, roiSize)
                    self.bgRoi[i].setSize(bgroiSize, bgroiSize)

                    self.molRoi[i].setPos(posold-center)
                    self.bgRoi[i].setPos(self.molRoi[i].pos()-centerbg)
                    self.label[i].setPos(self.molRoi[i].pos())
            self.roiSize = [int(self.moleculeSizeEdit.text())] * 2
        except:
            print("You don't have rois to resize (if you have it, please tell German something is wrong)")
            pass

    def exportTraces_or_images(self):  # connected to export traces button (btn7)
        self.calculate_images()
        self.export("images")


    def image_analysis(self):  # connected to image analysis button (btn_images)
        """Choose the image analysis mode, if there is a big ROI use this 
        area at the selected start number. If its not, use the actual one."""

        if self.roi == None:
            print("you need to mark the zone")
        else:
            self.cuted_pos = self.roi.pos()
            self.cuted_size = self.roi.size()
            self.image_data = self.roi.getArrayRegion(self.data, self.imv.imageItem)
            plot_with_colorbar(self.imv, self.image_data)
            self.imv.view.removeItem(self.roi)
            self.cuteado = True
            self.btn3.setEnabled(False)
            self.translateMaximaIN()


        self.btn7.setStyleSheet(
                "QPushButton { background-color: rgb(200, 200, 10); }")



    def create_small_ROI(self):  # connected to New small Roi (btn_small_roi)
        """ creates a new green roi at (0,0) position. then you move it
        and click on it to add rois at your analysis"""
        self.isclear = False

        if self.smallroi is not None:  # only want one
            self.imv.view.scene().removeItem(self.smallroi)
            self.smallroi = None
            print("good bye old roi, Hello new Roi")

        try:
            roisize = int(self.moleculeSizeEdit.text())
            self.smallroi = pg.ROI([0, 0], [roisize, roisize],
                                   scaleSnap=True, translateSnap=True,
                                   movable=True, removable=True, pen='g')
            self.imv.view.addItem(self.smallroi)
            self.smallroi.sigRemoveRequested.connect(self.remove_small_ROI)
            self.smallroi.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
            self.smallroi.sigClicked.connect(self.small_ROI_to_new_ROI)
            self.smallroi.sigRegionChanged.connect(self.making_traces)

            if self.primera == True:
                self.p2 = self.trace_widget.addPlot(row=2, col=1, title="Line profile.SUM/t. Blue is X; Magenta is Y")
                self.p2.showGrid(x=True, y=True)
                self.curve = self.p2.plot(open='y')
                self.curvey = self.p2.plot(open='y')
                self.frame_line = pg.InfiniteLine(angle=90,
                                              movable=True,
                                              pen=pg.mkPen(color=(200,220,200),
                                              width=1))
                self.p2.addItem(self.frame_line)
                self.primera = False
        except:
            pass

    def making_traces(self):  # is not making traces, just the profile X & Y

        try:
            molline = self.smallroi.getArrayRegion(self.image_data,
                                                    self.imv.imageItem,
                                                    returnMappedCoords=False)

            valor = (np.sum(molline, axis=0) / float(self.time_adquisitionEdit.text()))   #- roisize
            valory = (np.sum(molline, axis=1) / float(self.time_adquisitionEdit.text()))  #- roisize

            if self.isclear:
                self.p2.clear()
                self.curve = self.p2.plot(open='y')
                self.curvey = self.p2.plot(open='y')
                self.primera = False
                self.isclear = False

            self.curve.setData(valor,  
                                pen=pg.mkPen(color='b', width=2),
                                shadowPen=pg.mkPen('w', width=3))
            self.curvey.setData(np.transpose(valory),  # np.linspace(0,valory.shape[0],valory.shape[0]),
                                pen=pg.mkPen(color='m', width=2),
                                shadowPen=pg.mkPen('w', width=3))
            self.frame_line.setPos(((valor.shape[0]-1)/2))

        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))

#            if self.primera == True:
#                self.p2 = self.trace_widget.addPlot(row=2, col=1, title="Line profile.SUM/t. Blue is X; Magenta is Y")
#                self.p2.showGrid(x=True, y=True)
#                self.curve = self.p2.plot(open='y')
#                self.curvey = self.p2.plot(open='y')
#                self.primera = False

    def remove_small_ROI(self, evt):  # rigth click to delete the new small roi.
        self.imv.view.scene().removeItem(evt)

    def small_ROI_to_new_ROI(self): # connected to click the new small green roi
        """ it create a yellow new roi with backgroun and add it to the
        list of rois that want to be analysed"""

        print("\n o_0 YOU CLICK MEE 0_o \n")

        self.roiSize = [int(self.moleculeSizeEdit.text())] * 2
        self.bgroiSize = np.array(self.roiSize) + 2* int(self.BgSizeEdit.text())
        center = int(self.BgSizeEdit.text()) * np.array([1, 1])

        # fixing_number exist because you can put new rois before OR after the normal ones.
        i = self.fixing_number

        self.molRoi[i] = pg.ROI(self.smallroi.pos(), self.roiSize,
                                                       scaleSnap=True,
                                                       translateSnap=True,
                                                       movable=False,
                                                       removable=True,
                                                       pen='y') 
        self.bgRoi[i] = pg.ROI((self.smallroi.pos() - center), self.bgroiSize,
                                                      scaleSnap=True,
                                                      translateSnap=True,
                                                      movable=False,
                                                      removable=True,
                                                      pen='y') 
        self.imv.view.addItem(self.molRoi[i])
        self.imv.view.addItem(self.bgRoi[i])

        self.molRoi[i].sigRemoveRequested.connect(self.remove_ROI)
        self.bgRoi[i].sigRemoveRequested.connect(self.remove_ROI)

        self.label[i] = pg.TextItem(text=str(i))
        self.label[i].setPos(self.molRoi[i].pos())
        if self.see_labels_button.isChecked():
            self.imv.view.addItem(self.label[i])

        self.fixing_number = i + 1

        self.relabel_new_ROI()

    def relabel_new_ROI(self):  # everiwhere you create or delete a roi
        """ fix the numeration and showing rois when you add or remove them
        in this case, call the normal one, and remove the manually yellow"""
        self.relabel_ROI()
        self.remove_gauss_ROI()
        for i in self.removerois:
            self.imv.view.removeItem(self.molRoi[i])
            self.imv.view.removeItem(self.bgRoi[i])
            self.imv.view.removeItem(self.label[i])
            self.imv.view.removeItem(self.label[i])

    def relabel_ROI(self):  # from the new version (relabel_new_ROI)
        """ fix the numeration and showing rois when you add or remove them"""
        p = 0
        for i in np.arange(0, self.fixing_number):
            if i not in self.removerois:
                self.label[i].setText(text=str(p), color='g')
                p+=1

    def see_labels_shortcut(self):
        if self.see_labels_button.isChecked():
            self.see_labels_button.setChecked(False)
        else:
            self.see_labels_button.setChecked(True)
        self.see_labels()

    def see_labels(self):
        self.relabel_new_ROI()
        if self.see_labels_button.isChecked():
            for i in range(len(self.molRoi)):
                if i not in self.removerois:
                    try:
                        self.imv.view.addItem(self.label[i])
                    except:
                        pass
        else:
            for i in range(len(self.molRoi)):
                try:
                    self.imv.view.removeItem(self.label[i])
                except:
                    pass

    def filter_bg(self):  # connected to filter bg (btn_filter_bg)
        """ Check at the counts in the background zone, if they are above
        the threshold level (user imput), discards the spot.
        discards the spots meas to add them the the black list (removerois)
        and then do not use them from the total molRoi list
        It check means in the columns and files of the bg Roi"""

        bgArray = dict()
        a = 0
        bgsize = int(self.BgSizeEdit.text())
        for i in range(len(self.molRoi)): #np.arange(0, self.maxnumber):
            if i not in self.removerois:
                # get background plus molecule array
                bgArray[i] = self.bgRoi[i].getArrayRegion(self.image_data, self.imv.imageItem)                
                b = True
                for l in np.arange(-bgsize,bgsize):
                    if b:
                        if np.mean(bgArray[i][:,l]) > float(self.maxThreshEdit.text()) or \
                        np.mean(bgArray[i][l,:]) > float(self.maxThreshEdit.text()):
                            b = False  # just to stop if already find this.
                            self.bgRoi[i].setPen('r')
                            self.removerois.append(i)
                            a+=1


        print("filter bg: bad/total=", a,"/", len(self.molRoi))

    def filter_nospot(self):
        molArray = dict()
        bgArray = dict()
        bg = dict()
        bgNorm = dict()
        a = 0
#        roiSize = (int(self.moleculeSizeEdit.text()))
#        bgsize = 2* int(self.BgSizeEdit.text()) + roiSize
        for i in range(len(self.molRoi)): #np.arange(0, self.maxnumber):
            if i not in self.removerois:
                molArray[i] = self.molRoi[i].getArrayRegion(self.image_data, self.imv.imageItem)
                bgArray[i] = self.bgRoi[i].getArrayRegion(self.image_data, self.imv.imageItem)

#                molnumber = np.sum(molArray[i]) / (roiSize**2)
#                print("mean array", np.mean(molArray[i]), np.sum(molArray[i]))
#                bgnumber = np.sum(bgArray[i]) / (bgsize**2)
#                print("mean bg", np.mean(bgArray[i]))

                bg[i] = np.sum(bgArray[i]) - np.sum(molArray[i])

                n = int(self.moleculeSizeEdit.text())
                m = (2*int(self.BgSizeEdit.text())) + n
                bgNorm[i] = (n*n)*(bg[i]) / (m*m - n*n)

#                print("bgNorm", bgNorm[i])

                print("final valor=", (np.sum(molArray[i]) - bgNorm[i]))

# if the average inside is smaller than outside is deleted
# I choose to take 1.5 % bigger outside, for the cases too similar

                if np.mean(bgArray[i])*1.015 >= np.mean(molArray[i]):
                    self.molRoi[i].setPen('c')
                    self.bgRoi[i].setPen('c')
                    self.removerois.append(i)
                    a+=1

        print("filter no spots: bad/total=", a,"/", len(self.molRoi))

    def gaussian_fit_ROI(self):  # connect to gaussian fit (btn_gauss_fit)
        """For each not discarted roi in molRoi, make a 2D gaussian fit
        and move to this new position x, y. Use the ratio (input) between 
        sigma_x and sigma_y to discard bad shapes.
        Also left a Blue semitransparent roi in the old position just to
        see what happened"""

        # first clear the old gauss fited
        self.remove_gauss_ROI()

        molArray = dict()
        self.gauss_roi = dict()
        roiSize = [int(self.moleculeSizeEdit.text())] * 2
        print("Gauss fit for",len(self.molRoi)-len(self.removerois), "spots")
        a = 0
        for i in range(len(self.molRoi)):
            if i not in self.removerois:
                molArray[i] = self.molRoi[i].getArrayRegion(self.image_data, self.imv.imageItem)
                data = np.transpose(molArray[i])  # not sure why, but is works

                try:  # if the fit fails, print error and continue with the next
                    new_params = fitgaussian(data)
                except:
                    continue

                (height, x, y, width_x, width_y) = new_params
                newx = x-roiSize[0]//2 + 0.5  # that is not pixel fixed
                newy = y-roiSize[1]//2 + 0.5
                originx =  self.molRoi[i].pos()[0]
                originy =  self.molRoi[i].pos()[1]
                
                # new name for the old roi position
                self.gauss_roi[i] = pg.ROI([originx,originy], roiSize, pen=(100,50,200,200),
                                                               scaleSnap=True,
                                                               translateSnap=True,
                                                               movable=False,
                                                               removable=False)

                # moves the original set of rois to the new fited coordinate
                self.molRoi[i].setPen('m')
                self.molRoi[i].translate([newx, newy])
                self.bgRoi[i].translate([newx, newy])

                self.imv.view.addItem(self.gauss_roi[i])

                threshold_sigma = float(self.gauss_fit_edit.text())
                sigma_ratio = width_x / width_y

                # take away the not so circular fits (imput gauss_fit_edit)
                if sigma_ratio > threshold_sigma or sigma_ratio < (1/threshold_sigma):
                    self.molRoi[i].setPen('r')
                    self.removerois.append(i)
                    a += 1

        print("Gauss filter: bad/total=", a,"/", len(self.molRoi))

    def remove_gauss_ROI(self):
        """removes the gauss rois. They are not useful for anything,
        only to mark the spot"""

        for i in range(len(self.molRoi)):
            try:
                self.imv.view.removeItem(self.gauss_roi[i])
                del self.gauss_roi[i]
            except:
                pass

    def remove_ROI(self,evt):
        """ Remove the clicked roi, his background and label"""

        for i in np.arange(0, self.fixing_number):
            if self.bgRoi[i] == evt or self.molRoi[i] == evt:

                index = i
                self.removerois.append(index)

        print("Removed ROI", index)

        self.imv.view.scene().removeItem(self.molRoi[index])
        self.imv.view.scene().removeItem(self.bgRoi[index])
        self.imv.view.scene().removeItem(self.label[index])

        self.relabel_new_ROI()

    def clear_all(self):  # connected to button Clear all
        """ clear all the thing in the view, and initialize the variables"""

        self.remove_gauss_ROI()
        for i in np.arange(0, self.fixing_number):
            try:
                self.imv.view.removeItem(self.molRoi[i])
                self.imv.view.removeItem(self.bgRoi[i])
                self.imv.view.removeItem(self.label[i])
                self.imv.view.removeItem(self.label[i])
                del self.molRoi[i]
                del self.bgRoi[i]
                del self.label[i]
            except IOError as e:
                print("I/O error({0}): {1}".format(e.errno, e.strerror))
                print("ya estaba borrado")  

        self.molRoi = dict()
        self.bgRoi = dict()
        self.label = dict()
        self.maxnumber = 0
        self.removerois = []
        self.fixing_number = 0
        self.is_image = False

    def calculate_images(self):# from exportTraces_or_images (<- btn7 call it)
        """ calculate the traces to save.
        For each spot take the counts of the molecular roi, and 
        substract the counts from the normalized backgruond """

#        print("Calculate Images")
        self.roiSize = [int(self.moleculeSizeEdit.text())] * 2
        self.bgroiSize = np.array(self.roiSize) + 2* int(self.BgSizeEdit.text())  # one pixel each side

        # Create dict with spots
        self.sum_spot = dict()
        molArray = dict()
        bgArray = dict()
        weber = dict()
        bg = dict()
        bgNorm = dict()
        morgane = []
        webervector = []
#        s = (2*int(self.BgSizeEdit.text()))  # bgsize = molsize + s
        p=0
        for i in range(len(self.molRoi)):  # np.arange(0, self.maxnumber):
            if i not in self.removerois:
                # get molecule array
                molArray[i] = self.molRoi[i].getArrayRegion(self.image_data, self.imv.imageItem) /float(self.time_adquisitionEdit.text())

                # get background plus molecule array
                bgArray[i] = self.bgRoi[i].getArrayRegion(self.image_data, self.imv.imageItem) /float(self.time_adquisitionEdit.text())

                # get background array
                bg[i] = np.sum(bgArray[i]) - np.sum(molArray[i])

                n = int(self.moleculeSizeEdit.text())
                m = (2*int(self.BgSizeEdit.text())) + n
                bgNorm[i] = (n*n)*(bg[i]) / (m*m - n*n)


                # get normalized background
#                bgNorm[i] = get_counts_bgNorm(self.imv, self.image_data,
#                                          self.molRoi[i], self.bgRoi[i],
#                                          int(self.moleculeSizeEdit.text()),
#                                          int(self.BgSizeEdit.text()),
#                                          float(self.time_adquisitionEdit.text()))

                self.sum_spot[p] = (np.sum(molArray[i]) - bgNorm[i])
                weber[p] = self.sum_spot[p] / bgNorm[i]
                morgane.append((self.sum_spot[p], bgNorm[i], weber[p]))

                webervector.append(weber[p])
                p +=1 # I have to use this to have order because of removerois


        self.weber = webervector
        # Save sums as an array
        a = []
        for p in range(len(self.sum_spot)):
            a.append(self.sum_spot[p])

        b = np.array(a).T
#        print("len spots", len(b))
        self.intensitys = b

        self.morgane = np.array(morgane)

    def export(self, what="images"):  # after analysis, you want to save the data
        """ to save the data.
        Makes a diference betweeen the video part (traces)
        and the spot detection function (image analysis).
        Gives you back a .txt with 1 trace per column
        or only 1 column with all the intensities.
        Also a .png with the image with the rois as you see in the UI
        Save Customname+"trace/image"+#ofdetecctions+self.n;
        this las self.n change every click to avoid lost data.
        Now, alse sabes another file with the molArray and background
        without substracting anything, as morgane aks for.
        I CHANGE THE METHOD FOR SOME BETHER WAY OF DO THAT
        (I will write the new one later)
        """

        N = 0
        number = ""
        
        self.custom_name  = str(self.edit_dir_save.text()) +"/"+ str(self.edit_save.text()) + "_"

        if what == "images":
            header = "Counts in Roi"+"    "+"Background (normalize by roisize)"+"    "+"Wever contrast"
            if self.histo_data:
                b = self.intensitys2
                c = self.morgane2
            else:
                b = self.intensitys
                c = self.morgane

            intensities_name = self.custom_name  + 'intensities-' + str(len(b))+number+ '.txt'
            while os.path.isfile(intensities_name):
#                print(intensities_name)
                number = "("+ str(N) +")"
                intensities_name = self.custom_name  + 'intensities-' + str(len(b))+number+ '.txt'
#                print(intensities_name)
                N += 1
            np.savetxt(intensities_name, b, delimiter="    ", newline='\r\n')
            print("\n", len(b), "Intensities exported as", intensities_name)

            intensities_morgane_name = self.custom_name  + 'intensities_morgane-' + str(len(c))+number+ '.txt'
            while os.path.isfile(intensities_morgane_name):
#                print(intensities_morgane_name)
                number = "("+ str(N) +")"
                intensities_morgane_name = self.custom_name  + 'intensities_morgane-' + str(len(c))+number+ '.txt'
#                print(intensities_morgane_name)
                N += 1
            np.savetxt(intensities_morgane_name, c, delimiter="    ", newline='\r\n', header=header)
            print("\n", len(c), "Intensities exported as", intensities_morgane_name)

            ratio = self.image_data.shape[1]/self.image_data.shape[0]
            height = int(1920)
            width = int(1920*ratio)
            exporter = pg.exporters.ImageExporter(self.imv.imageItem)
            exporter.params.param('width').setValue(width, blockSignal=exporter.widthChanged)
            exporter.params.param('height').setValue(height, blockSignal=exporter.heightChanged)

            png_name = self.custom_name  + 'Image_intensities-'+ str(len(b))+number+ '.png'
            while os.path.isfile(png_name):
#                print(png_name)
                number = "("+ str(N) +")"
                png_name = self.custom_name  + 'Image_intensities-'+ str(len(b))+number+ '.png'
#                print(png_name)
                N += 1
            exporter.export(png_name)
            print( "\n Picture exported as", png_name)

            import sys  # to get the path and the name of the .py file runing
            print ("\n all saved in " +sys.argv[0])

# %% Auto weber
    def automatic_weber_start(self): # connected to auto Weber button (autoWeberButton)
        """it start the timer with a specific time in ms to call again
        the function connected (automatic_crazy). 
        It stop when timer.spot is called (automatic_crazy function)"""
        self.timing = 0
        
        self.moleculeSizeEdit.setText(str(int(int(self.moleculeSizeEdit.text())-1)))
        self.update_size_rois()
        self.weber_vector = np.zeros((int(self.weberRoiStepEdit.text()), len(self.molRoi)-len(self.removerois)))

        self.autoWeberButton.setStyleSheet(
                "QPushButton { background-color: orange; }"
                "QPushButton:pressed { background-color: blue; }")

        self.automatic_webertimer.start(5)  # imput in ms
#        self.weber_vector_error = []
#        print("number of Rois to check :", int(self.weberRoiStepEdit.text()))

    def automatic_weber(self):  # from the timer of automatic_weber_start
        """ to find the best rois size based on the weber contrasts. It scan
        up to N diferent sizes, where N can be an imput."""
#        self.weber_vector[self.timing] = []
#        print("start automatic weber")
        self.calculate_images()
#        print("Calculate images finish")
#        self.weber_vector[self.timing].append(self.weber)
        self.weber_vector[self.timing,:] = self.weber
#        print("Weber vector growing")

#        self.plot_weber()  # If I have time later I do the plot in another window
        roiSize = int(self.moleculeSizeEdit.text())
#        print(roiSize, "roisize")
        self.moleculeSizeEdit.setText(str(int(roiSize+1)))
#        print(int(self.moleculeSizeEdit.text()), "roisize after")
        self.update_size_rois()
#        print(int(self.moleculeSizeEdit.text()), "Updato ro size just in case")


        self.timing +=1
        if self.timing == int(self.weberRoiStepEdit.text()):
            self.automatic_webertimer.stop()
            print(" automatic analysis finished", len(self.weber_vector))
#            print("WEBER vector", self.weber_vector)
#            plt.plot(self.weber_vector)
            self.plot_weber()
            self.autoWeberButton.setStyleSheet(
                    "QPushButton { background-color: ; }"
                    "QPushButton:pressed { background-color: blue; }")

    def plot_weber(self):
        alsteps = int(self.weberRoiStepEdit.text())
        valorx =  (np.linspace(1, alsteps, alsteps)+int(self.moleculeSizeEdit.text())-alsteps)

#        self.curve.clear()
#        self.curvey.clear()
#        self.p2.removeItem(self.frame_line)
        self.p2.clear()
        self.isclear = True

#        print("plot weber curve")
        colors = ['b', 'c', 'y', 'g', 'm', 'r']
        for i in range(len(self.molRoi)-len(self.removerois)):
            curves = self.p2.plot(open='y')
            valory = self.weber_vector[:,i]
            if i < len(colors):
                curves.setData(valorx, np.transpose(valory),
                            pen=pg.mkPen(color=colors[i], width=2),
                            shadowPen=pg.mkPen('w', width=2))
            else:
                curves.setData(valorx, np.transpose(valory),
                            pen=pg.mkPen(width=2),
                            shadowPen=pg.mkPen(width=2))
#            self.curvey.setData(valorx, np.transpose(valory))  # ,
#                            pen=pg.mkPen(color='m', width=2),
#                            shadowPen=pg.mkPen('w', width=2))


# =============================================================================
#     def plot_weber(self):
#         """Prepare to make the histogram with all the spots detected.
#         It opens a new window to run in another thread and  make it easy.
#         If the new window is not closed, it add the new data to the histogram
#         and can save all of this.
#         When closed, starts over, AND CANNOT SAVE ALL THIS"""
# 
# #        self.calculate_images()
# #        try:
# #            self.intensitys2 = np.concatenate((self.intensitys,
# #                                               self.intensitys2))
# #            self.morgane2 = np.concatenate((self.morgane,
# #                                               self.morgane2))
# #        except:
# #            self.intensitys2 = self.intensitys
# #            self.morgane2 = self.morgane
#         self.doweber()
# 
#     def doweber(self):  # from plot_weber
#         """start the new popup window. its run independenty of the Main win"""
#         self.w3 = MyPopup_weber(self)
#         self.w3.setGeometry(QtCore.QRect(750, 50, 450, 600))
#         self.w3.show()
# =============================================================================

# %% out of program

#    def automatic_crazy_start(self): # connected to crazy go (crazyStepButton)
#        """it start the timer with a specific time in ms to call again
#        the function connected (automatic_crazy). 
#        It stop when timer.spot is called (automatic_crazy function)"""
#        self.timing = 0
#        self.automatic_crazytimer.start(50)  # imput in ms
#        print("number of images to see :", int(self.crazyStepEdit.text()))

# =============================================================================
#     def automatic_crazy(self):  # from the timer of automatic_crazy_start
#         """ to make a huge histogram looking all the video in small parts
#         this is useful to have and idea or the results expected. 
#         BUT as this is not perfec, it take a lot of bad spots.
#         Makes (imput) steps"""
# 
#         self.image_data = self.data[int(self.timing*self.data.shape[0]//int(self.crazyStepEdit.text())),:,:]
#         self.clear_all()
#         self.is_image = True
#         self.detectMaxima()
#         self.imv.setCurrentIndex(int(self.timing*self.data.shape[0]//int(self.crazyStepEdit.text())))
#         self.filter_nospot()
# #        self.filter_bg()
#         self.gaussian_fit_ROI()
#         self.filter_nospot()
# #        self.filter_bg()
#         self.make_histogram()
#         print("step #", self.timing,"frame :", int(self.timing*self.data.shape[0]//int(self.crazyStepEdit.text())))
#         self.timing +=1
#         if self.timing == int(self.crazyStepEdit.text()):
#             self.automatic_crazytimer.stop()
#             print(" automatic analysis finished")
# =============================================================================

    def channel_menu(self, QComboBox):
        """ le pongo color a los menus"""
        if QComboBox.currentText() == channels[0]:  # verde
            self.channel = 0
            QComboBox.setStyleSheet("QComboBox{color: rgb(255,0,0);}\n")
        elif QComboBox .currentText() == channels[1]:  # rojo
            self.channel = 1
            QComboBox.setStyleSheet("QComboBox{color: rgb(0,128,0);}\n")
        elif QComboBox .currentText() == channels[2]: # azul
            self.channel = 2
            QComboBox.setStyleSheet("QComboBox{color: rgb(0,0,255);}\n")


# %% for the new windows.

    def save_histogram(self):
        print("data from histogram Saved")
        try:
            h = self.intensitys2
            print("intensitys2")
        except:
            h = self.intensitys
            print("Solo los ultimos puntos EXCEPT")

        N = 0
        number = ""
        self.custom_name  = str(self.edit_save.text()) + "_"

        histo_file_name = self.custom_name  + 'histogram-' + str(len(h))+number+ '.txt'
        while os.path.isfile(histo_file_name):
            number = "("+ str(N) +")"
            histo_file_name = self.custom_name  + 'histogram-' + str(len(h))+number+ '.txt'
#                print(intensities_morgane_name)
            N += 1
        np.savetxt(histo_file_name, h, delimiter="    ", newline='\r\n')
        print("\n", len(h), "Histogram exported as", histo_file_name)

    def make_histogram(self):  # connected to make histogram (btn_histogram)
        """Prepare to make the histogram with all the spots detected.
        It opens a new window to run in another thread and  make it easy.
        If the new window is not closed, it add the new data to the histogram
        and can save all of this.
        When closed, starts over, AND CANNOT SAVE ALL THIS"""

        self.calculate_images()
        try:
            self.intensitys2 = np.concatenate((self.intensitys,
                                               self.intensitys2))
            self.morgane2 = np.concatenate((self.morgane,
                                               self.morgane2))
        except:
            self.intensitys2 = self.intensitys
            self.morgane2 = self.morgane
        self.doit()
        self.histo_data = True
        if not self.is_trace:
            self.btn7.setText("Export all histogram data ({})".format(len(self.intensitys2)))


    def doit(self):  # from make_histogram
        """start the new popup window. its run independenty of the Main win"""
        self.w2 = MyPopup_histogram(self)
        self.w2.setGeometry(QtCore.QRect(750, 50, 450, 600))
        self.w2.show()

class MyPopup_histogram(QtGui.QWidget):
    """ new class to create a new window for the histogram menu
    Can put a lot of thigs to play with the histogram, but for now is only a graph"""

    def closeEvent(self, event):  # when the win is closed
        """ things to do when the windows is closed: erase all the acumulated
        data; change the text on the butto to make clear what you have"""
        self.main.intensitys2 = None
        self.main.morgane2 = None
        self.main.histo_data = False
        if not self.main.is_trace:
            self.main.btn7.setText("Export only last ({}) points".format(len(self.main.intensitys)))
        
    def __init__(self, main, *args, **kwargs):  # when doit do w2.show()
        """this is the initialize of this new windows. Make the new
        windows appear and put the histogram inside. Can have mor things
        For now, it can be closed with ESC as a shortcut"""

        QtGui.QWidget.__init__(self)
        super().__init__(*args, **kwargs)

        self.main = main
        self.Histo_widget = pg.GraphicsLayoutWidget()
        grid = QtGui.QGridLayout()  # overkill for one item...
        self.setLayout(grid)

        self.p1 = self.Histo_widget.addPlot(row=2, col=1, title="Histogram (kHz)")
        self.p1.showGrid(x=True, y=True)

        intensitys = self.main.intensitys2
        self.intensitys = intensitys

        grid.addWidget(self.Histo_widget,      0, 0, 1, 7)
#        grid.addWidget(self.play_pause_Button,  1, 0)

        self.setWindowTitle("Histogram. (ESC key, close it.)")

        vals = self.intensitys
        y,x = np.histogram(vals)
        self.p1.plot(x, y, stepMode=True, fillLevel=0, brush=(0,0,255,150))
        self.p1.showGrid(x = True, y = True, alpha = 0.5)

        # Shortcut. ESC ==> close_win
        self.close_Action = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('ESC'), self, self.close_win)

    def close_win(self):  # called pressing ESC
        """Close all when press ESC. Same changes es the other closeEvent
        (not sure about how to trigger both at the same time)"""
        
        self.main.intensitys2 = None
        self.main.histo_data = False
        self.main.btn7.setText("Export only last ({}) points".format(len(self.main.intensitys)))

        self.close()


# =============================================================================
# class MyPopup_weber(QtGui.QWidget):
#     """ new class to create a new window for the weber plot
#     for now is only a graph"""
# 
#     def closeEvent(self, event):  # when the win is closed
#         """ things to do when the windows is closed: erase all the acumulated
#         data; change the text on the butto to make clear what you have"""
# #        self.main.intensitys2 = None
# #        self.main.morgane2 = None
# #        self.main.histo_data = False
#         
#     def __init__(self, main, *args, **kwargs):  # when doit do w2.show()
#         """this is the initialize of this new windows. Make the new
#         windows appear and put the histogram inside. Can have mor things
#         For now, it can be closed with ESC as a shortcut"""
# 
#         QtGui.QWidget.__init__(self)
#         super().__init__(*args, **kwargs)
# 
#         self.main = main
#         self.Histo_widget = pg.GraphicsLayoutWidget()
#         grid = QtGui.QGridLayout()  # overkill for one item...
#         self.setLayout(grid)
# 
#         self.p1 = self.Histo_widget.addPlot(row=2, col=1, title="Histogram (kHz)")
#         self.p1.showGrid(x=True, y=True)
# 
#         intensitys = self.main.intensitys2
#         self.intensitys = intensitys
# 
#         grid.addWidget(self.Histo_widget,      0, 0, 1, 7)
# #        grid.addWidget(self.play_pause_Button,  1, 0)
# 
#         self.setWindowTitle("Histogram. (ESC key, close it.)")
# 
#         vals = self.intensitys
#         y,x = np.histogram(vals)
#         self.p1.plot(x, y, stepMode=True, fillLevel=0, brush=(0,0,255,150))
#         self.p1.showGrid(x = True, y = True, alpha = 0.5)
# 
#         # Shortcut. ESC ==> close_win
#         self.close_Action = QtGui.QAction(self)
#         QtGui.QShortcut(
#             QtGui.QKeySequence('ESC'), self, self.close_win)
# 
#     def close_win(self):  # called pressing ESC
#         """Close all when press ESC. Same changes es the other closeEvent
#         (not sure about how to trigger both at the same time)"""
#         
#         self.main.intensitys2 = None
#         self.main.histo_data = False
#         self.main.btn7.setText("Export only last ({}) points".format(len(self.main.intensitys)))
# 
#         self.close()
# =============================================================================
# %% Functions to make the Gauss fit
def gaussian(height, center_x, center_y, width_x, width_y):
    """Returns a gaussian function with the given parameters"""
    width_x = float(width_x)
    width_y = float(width_y)
    return lambda x, y: height*np.exp(
                -(((center_x-x)/width_x)**2+((center_y-y)/width_y)**2)/2)


def moments(data):
    """Returns (height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution by calculating its
    moments """
    total = data.sum()
    X, Y = np.indices(data.shape)
    x = (X*data).sum()/total
    y = (Y*data).sum()/total
    col = data[:, int(y)]
    width_x = np.sqrt(np.abs((np.arange(col.size)-y)**2*col).sum()/col.sum())
    row = data[int(x), :]
    width_y = np.sqrt(np.abs((np.arange(row.size)-x)**2*row).sum()/row.sum())
    height = data.max()
    return height, x, y, width_x, width_y


def fitgaussian(data):

    """Returns (height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution found by a fit"""
    params = moments(data)
    errorfunction = lambda p: np.ravel(gaussian(*p)(*np.indices(data.shape)) -
                                       data)
    p, success = optimize.leastsq(errorfunction, params)
    return p

# %% functions to meka the life easier

def plot_with_colorbar(imv,data):
    
    # Display the data and assign each frame a number
    x = np.linspace(1., data.shape[0], data.shape[0])

    # Load array as an image
    imv.setImage(data, xvals=x)

    # Set a custom color map
    colors = [
            (0, 0, 0),
            (45, 5, 61),
            (84, 42, 55),
            (150, 87, 60),
            (208, 171, 141),
            (255, 255, 255)
            ]
    cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, 6), color=colors)
    imv.setColorMap(cmap)

def get_counts_bgNorm(imv, image, molRoi, bgRoi, moleculeSize, BgSize, adq_time=1):

    # get molecule array
    molArray = molRoi.getArrayRegion(image, imv.imageItem)

    # get background plus molecule array
    bgArray = bgRoi.getArrayRegion(image, imv.imageItem)

    # get background array
    bg = np.sum(bgArray) - np.sum(molArray)
    
    # get total background to substract from molecule traces
    n = moleculeSize
    m = (2*BgSize) + moleculeSize
    bgNorm = (n*n)*(bg) / (m*m - n*n)
    return bgNorm / adq_time

# %% END... Its a neverending story ♪♫
if __name__ == '__main__':

    app = pg.Qt.QtGui.QApplication([])
    exe = smAnalyzer()
#    exe.w.show()
    exe.show()
    app.exec_()



"""
circularity---

Hacer que vaya y vuelva con el cuting
"""


