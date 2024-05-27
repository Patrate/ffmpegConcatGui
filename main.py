import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QFrame, QScrollArea, QGridLayout, QProgressBar
)
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QDrag, QImage
from PyQt6.QtCore import Qt, QMimeData, QPoint, QThread, pyqtSignal
import cv2
import shutil
import subprocess
from datetime import datetime

configDir = ".ffmpegConcatConfig"
configFile = configDir + "/config"
if not os.path.isdir(configDir):
    os.mkdir(configDir)
if not os.path.isfile(configFile):
    with open(configFile, "w") as f:
        f.write("")

class DraggableLabel(QFrame):
    def __init__(self, pixmap, path):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setAcceptDrops(True)
        self.setStyleSheet("background-color: white; margin: 5px; padding: 5px;")
        self.path = path
      

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.thumbnail = QLabel()
        self.thumbnail.setPixmap(pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio))
        self.layout.addWidget(self.thumbnail)

        self.path_label = QLabel(path.rsplit('/', 1)[-1])
        self.layout.addWidget(self.path_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.path_label.text())
            drag.setMimeData(mime_data)
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())
            drag.exec(Qt.DropAction.MoveAction)

class DropZone(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isfile(path) and path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                    pixmap = self.get_video_thumbnail(path)
                    if pixmap:
                        label = DraggableLabel(pixmap, path)
                        self.layout.addWidget(label)
        elif event.mimeData().hasText():
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            source = event.source()
            position = event.position().toPoint()

            for i in range(self.layout.count()):
                widget = self.layout.itemAt(i).widget()
                if widget.geometry().contains(position):
                    self.layout.insertWidget(i, source)
                    break
            else:
                self.layout.addWidget(source)

    def get_video_thumbnail(self, path):
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return None

        ret, frame = cap.read()
        if not ret:
            return None

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)

        cap.release()
        return pixmap
    
    def swap_labels(self, index1, index2):
        if index1 == index2:
            return

        item1 = self.layout.itemAt(index1)
        item2 = self.layout.itemAt(index2)

        if item1 and item2:
            widget1 = item1.widget()
            widget2 = item2.widget()

            self.layout.insertWidget(index1, widget2)
            self.layout.insertWidget(index2, widget1)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Concatenator")
        self.setGeometry(100, 100, 800, 600)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        
        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        
        self.drop_zone = DropZone()
        self.drop_zone_scroll = QScrollArea()
        self.drop_zone_scroll.setWidgetResizable(True)
        self.drop_zone_scroll.setWidget(self.drop_zone)
        
        self.controls = QWidget()
        self.controls_layout = QHBoxLayout()
        self.controls.setLayout(self.controls_layout)
        
        self.folder_label = QLabel()
        self.folder_label.setText("LOLXD")
        with open(configFile, "r") as f:
            savedOut = f.read()
            if len(savedOut) == 0:
                self.folder_label.setText("Choose output folder")
                self.output_folder = "./"
            else:
                self.folder_label.setText(savedOut)
                self.output_folder = savedOut
        
        self.choose_folder_btn = QPushButton("Choose Folder")
        self.choose_folder_btn.clicked.connect(self.choose_folder)
        
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_drop_zone)
        
        self.concat_btn = QPushButton("Concatenate")
        self.concat_btn.clicked.connect(self.concatenate_videos)
        
        self.controls_layout.addWidget(self.folder_label)
        self.controls_layout.addWidget(self.choose_folder_btn)
        self.controls_layout.addWidget(self.reset_btn)
        self.controls_layout.addWidget(self.concat_btn)
        
        self.main_layout.addWidget(self.drop_zone_scroll)
        self.main_layout.addWidget(self.controls)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        self.main_layout.addWidget(self.progress_label)
    
    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose Output Folder")
        if folder:
            self.output_folder = folder
            self.folder_label.setText(folder)
            with open(configFile, "w") as f:
                f.write(folder)
    
    def reset_drop_zone(self):
        for i in reversed(range(self.drop_zone.layout.count())):
            widget_to_remove = self.drop_zone.layout.itemAt(i).widget()
            self.drop_zone.layout.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None)
    
    def concatenate_videos(self):
        videos = [self.drop_zone.layout.itemAt(i).widget() for i in range(self.drop_zone.layout.count())]
        
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)

        self.worker = ConcatenateWorker(videos, self.output_folder)
        self.worker.progress.connect(self.update_progress)
        self.worker.start()

    def update_progress(self, value, text=""):
        self.progress_bar.setValue(value)
        #self.progress_bar.setFormat(text)
        self.progress_label.setText(text)
        if value == 100:
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
    

class ConcatenateWorker(QThread):
    progress = pyqtSignal(int, str)

    def __init__(self, videos, outDir):
        super().__init__()
        self.videos = videos
        self.outDir = outDir

    def run(self):
        if len(self.videos) == 0:
            print("No files")
            self.progress.emit(100)
            return
        print("Concatenating videos...")
        tmpDir = configDir + "/ffmpeg_tmp"
        if os.path.isdir(tmpDir):
            shutil.rmtree(tmpDir)
        os.mkdir(tmpDir)
        
        # create tmp folder
        # for vid in programme, convert to ts in tmp folder

        for i in range(len(self.videos)):
            current_widget = self.videos[i]
            self.progress.emit(int((i * 80) / len(self.videos)), f"Converting {current_widget.path_label.text()}")
            fout = tmpDir + f"/intermediate{i}.ts"
            print(f"{i}: {current_widget.path}")
            print(f'RUN: ffmpeg -i "{current_widget.path}" -c copy "{fout}"')
            subprocess.run(f'ffmpeg -i "{current_widget.path}" -c copy "{fout}"', shell=True)
            print(f"Converted {current_widget.path} as {fout}")
            
        self.progress.emit(80, f"Concatenation")
        fout = self.outDir + f"/{datetime.today().strftime('%Y%m%d%H%M%S')}.mp4"
        concatString = tmpDir + "/intermediate0.ts"
        
        for i in range(1, len(self.videos)):
            concatString += "|" + tmpDir + f"/intermediate{i}.ts"
        
        print(f"ConcatString is {concatString}")
        print("RUN: " + f'ffmpeg -i "concat:{concatString}" -c copy {fout}')
        subprocess.run(f'ffmpeg -i "concat:{concatString}" -c copy {fout}', shell=True)
        self.progress.emit(100, "done")
        shutil.rmtree(tmpDir)
            


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())