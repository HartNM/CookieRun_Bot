import tkinter as tk
from tkinter import simpledialog
import cv2
from PIL import Image, ImageTk

class CropWindow(tk.Toplevel):
    def __init__(self, master, image_array, callback):
        super().__init__(master)
        self.title("Crop Template (ลากเมาส์เพื่อครอบภาพ)")
        self.callback = callback
        
        self.original_img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        self.rgb_img = cv2.cvtColor(self.original_img, cv2.COLOR_BGR2RGB)
        
        self.h, self.w = self.rgb_img.shape[:2]
        self.display_w = min(1000, self.w)
        self.scale = self.display_w / self.w
        self.display_h = int(self.h * self.scale)
        
        resized = cv2.resize(self.rgb_img, (self.display_w, self.display_h))
        self.pil_img = Image.fromarray(resized)
        self.tk_img = ImageTk.PhotoImage(self.pil_img)
        
        self.canvas = tk.Canvas(self, width=self.display_w, height=self.display_h, cursor="cross")
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        
        self.rect = None
        self.start_x = None
        self.start_y = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        
        tk.Label(self, text=" ลากเมาส์คลุมบริเวณที่ต้องการทำเป็น Template (ปล่อยเมาส์เพื่อยืนยัน) ", bg="yellow", fg="black", font=("Helvetica", 12)).place(x=10, y=10)

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=3)

    def on_move_press(self, event):
        cur_x, cur_y = (event.x, event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x, end_y = (event.x, event.y)
        x1 = int(min(self.start_x, end_x) / self.scale)
        x2 = int(max(self.start_x, end_x) / self.scale)
        y1 = int(min(self.start_y, end_y) / self.scale)
        y2 = int(max(self.start_y, end_y) / self.scale)
        
        if x2 - x1 > 5 and y2 - y1 > 5:
            cropped_bgr = self.original_img[y1:y2, x1:x2]
            name = simpledialog.askstring("Save Template", "ตั้งชื่อไฟล์ภาพ (ภาษาไทยได้):", parent=self)
            if name:
                if not name.endswith('.png'):
                    name += '.png'
                self.callback(name, cropped_bgr, x1, y1, x2, y2)
        
        self.destroy()
