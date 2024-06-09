import os

import numpy as np
from scipy.interpolate import interp1d

from PIL import Image
from IPython.display import display
import cv2



def get_interp(path):
    #converted_height=interp_func(pixel_height)

    with open(path, 'r') as file:
        lines = file.readlines()
        data=[]
        
        for line in lines:
            if line.strip() and line[0]!=('#'):
                line=line.strip().split()
                data_line=[float(x) for x in line]
                data.append(data_line)
    data=np.array(data)            
    if len(data)>0:
        interp_func = interp1d(data[:,2],data[:,1],kind='linear',fill_value="extrapolate")
        return interp_func
    return None



class DroneImage:
    path:str= None
    
    image: np.array= None
    image_binary: np.array=None
    image_contours: np.array=None

    contours:np.array=None
    all_rects:np.array=None
    rect_angle_tolerance=10

    pixel_height:int=None
    converted_height:int=None
    interp_func=None
   
    
    def __init__(self, path:str=None,image:np.array=None,interp_path:str='measurements.txt'):
        if path is not None: 
            self.path= path
            self.image= cv2.imread(self.path)
            self.interp_func=get_interp(interp_path)

        if image is not None:
            self.image=image
            self.interp_func=get_interp(interp_path)
       

    def display(self,key="",imshow=False):
        if key=="":
            display(Image.fromarray(self.image))
        elif key=="binary":
            display(Image.fromarray(self.image_binary))
        elif key=="contours":
            display(Image.fromarray(self.image_contours))



    def imshow(self,key="",msg=""):
        if key=="":
            cv2.imshow(f"Image{msg}", cv2.resize(self.image, (400, 640)))
        elif key=="contours":
            cv2.imshow(f"Contours{msg}", cv2.resize(self.image_contours, (400, 640)))
        elif key=="binary":
            cv2.imshow(f"Binary{msg}", cv2.resize(self.image_binary, (400, 640)))

        cv2.waitKey(0)
        cv2.destroyAllWindows()



    def preprocess(self):
        if len(self.image.shape) == 3 and self.image.shape[2] == 3:  # Check if image is BGR
            gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        else:
            gray = self.image

        _, thresh=cv2.threshold (gray, 150, 255, cv2.THRESH_BINARY)
        dilated_image = cv2.dilate(thresh, np.ones((3,3), np.uint8), iterations=1)
        self.image_binary=dilated_image


    
    def get_contours(self,filter=True):

        self.image_contours=cv2.cvtColor(self.image.copy(), cv2.COLOR_GRAY2RGB)
        
        cnts = cv2.findContours(self.image_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = cnts[0] if len(cnts) == 2 else cnts[1]

        rectangles=Rectangles(contours)
        if filter:
            rectangles.filter(self.rect_angle_tolerance)
            
        self.contours=rectangles.largest_two()   
        self.all_rects=rectangles

        for c in self.contours:
            cv2.drawContours(self.image_contours, [c] , 0, (0, 255, 0), 2)
        #cv2.drawContours(self.image_contours, [self.contours[0]] , 0, (0, 0, 255), 2)
        #cv2.drawContours(self.image_contours, [self.contours[1]] , 0, (0, 255, 0), 2)


    def draw_contours(self,raw=False):
        self.image_contours=cv2.cvtColor(self.image.copy(), cv2.COLOR_GRAY2RGB)

        for r in self.all_rects:
            r.draw(self.image_contours,raw=raw)

    
    def iterate_rects(self):
        for r in self.all_rects.rectangles:
            self.image_contours=cv2.cvtColor(self.image.copy(), cv2.COLOR_GRAY2RGB)
            r.draw(self.image_contours)
            self.imshow("contours",msg=f"; angle={r.angle:.2f}, ratio={r.ratio:.2f}")
            

    def get_height(self):
        self.preprocess()
        self.get_contours(filter=True)

        mask = np.zeros_like(self.image_contours)
        for c in self.contours:
            cv2.drawContours(mask, [c], 0, (0, 255, 0), -1)
        #display(Image.fromarray(mask))
            
        points_inside_contour = np.where(mask != 0)
        self.pixel_height = np.mean(points_inside_contour[0])

        if self.interp_func is not None:
            self.converted_height=float(self.interp_func(self.pixel_height))

        else:
            print("No Interp function found")


class Rect:
    #just a easy way to keep track of my rectangular contours.
    
    raw_contour:np.array=None
    min_rect:np.array=None
    box:np.array=None
    angle:int=None
    area:int=None
    ratio:int=None
    
    def __init__(self,raw):
        self.raw_contour=raw
        self.min_rect=cv2.minAreaRect(self.raw_contour)
        self.angle= min(self.min_rect[-1],90-self.min_rect[-1])
        self.box = np.intp(cv2.boxPoints(self.min_rect))
        self.area= cv2.contourArea(self.box)
        self.get_ratio()

    def draw(self,image,raw=False):
        if not raw:
            cv2.drawContours(image, [self.box] , 0, (0, 255, 0), 2)
        else:
            cv2.drawContours(image, [self.raw] , 0, (0, 255, 0), 2)

    def get_ratio(self):

        sums = np.sum(self.box, axis=1)
        
        upper_left_index = np.argmin(sums)
        lower_right_index = np.argmax(sums)

        upper_left=self.box[upper_left_index]
        lower_right=self.box[lower_right_index]
        
        the_rest= np.array([self.box[i] for i in range(4) if i not in [upper_left_index,lower_right_index]])
        
        upper_right = the_rest[np.argmax(the_rest[:, 0])]
        lower_left = the_rest[np.argmin(the_rest[:,0])]
        #print([upper_left,upper_right,lower_left,lower_right])

        width = np.linalg.norm(upper_left - upper_right)
        height = np.linalg.norm(upper_left - lower_left)
        
        self.ratio=height/width

class Rectangles:
    rectangles:np.array=None
    angles:np.array=None
    boxes:np.array=None
    areas:np.array=None
    
    def __init__(self,cnts=[]):
        self.rectangles=[]
        for c in cnts:
            r=Rect(c)
            self.rectangles.append(r)

        self.calculate()

    def calculate(self):
        self.angles=[]
        self.boxes=[]
        self.areas=[]
        for r in self.rectangles:
            self.angles.append(r.angle)
            self.boxes.append(r.box)
            self.areas.append(r.area) 

    
    def filter(self,angle_tolerance):
        r_fil=[]
        for r in self.rectangles:
            if r.angle<=angle_tolerance and r.ratio<1:
                r_fil.append(r)
        self.rectangles=r_fil
        self.calculate()

    def largest_two(self):
        #sort rectangles according to their areas
        args=np.argsort(self.areas)[::-1]
        sorted_areas=np.array(self.areas)[args]
        sorted_rects=np.array(self.rectangles)[args]

        return [sorted_rects[0].box,sorted_rects[1].box]
