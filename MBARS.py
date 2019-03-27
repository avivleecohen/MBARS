import sys
sys.path.append('C:\\Python27\\Lib\\site-packages')
import numpy as np
import scipy as sp
import matplotlib as mpl
import matplotlib.pyplot as plt
import scipy.misc as spm
from scipy import odr
import winsound
from scipy.optimize import curve_fit
import time
import cPickle as pickle
import os
import shutil
import matplotlib.patches as patches
#import pysal
import numpy.ma as npma
import skimage.transform as sktrans
from math import *
import skimage.feature as skfeat
import skimage.morphology as skmorph
import skimage.filters.rank as skrank
import skimage.restoration as skrestore
import skimage.util as skutil
import sklearn.cluster as skcluster
from scipy.ndimage import filters
import scipy.stats as sps
import imageio

#This is the MBARS library, it contains all the functions needed to run MBARS

#Global Variables, adjust as needed:
#REFPATH is where important reference files are stored, the key one is
# the HiRISE info file (RDRCUMINDEX.TAB) needs to be in the REFPATH folder
REFPATH = 'C://Users//dhood7//Desktop//MBARS//RefData//'
#BASEPATH is where MBARS will look for the provided filename
BASEPATH = 'C://Users//dhood7//Desktop//MBARS//Images//'
PATH = None
FNM = None

#enter product ID
ID = None
NOMAP = None

WIDFACT = 2.
LENFACT = 2.
#assigned in start as i, s, and r
INANGLE = None
NAZ = None
SAZ = None
SUNANGLE = None
RESOLUTION = None
ROTANG = None
#MAX EXPECTED BOULDER SIZE, expressed in pixels
MD = 30
MH = 30
MA = np.pi*(MD/2)**2
#minimum accepted boulder size expressed in pixels
minA = 4


'''this is called at the end to initialize the program'''
def start():
    i,s,r,n, saz,rotang = getangles(ID)
    current()
    return i,s,r,n,saz, rotang
    
#Inputs: image = Image to be analyzed (a 2 or 3-d np.array), gam = value for Gamma,
# png = boolean dictating if the image is a 3-D array (True if 3D), plot = True to plot things, False to not
#bound = where to cutoff the shadows, expressed as a fraction of gaussian max (.01 will select the point that is .01* max value as the boundary
#outputs: imagelin and imagemodlin, 1-D arrays of the image data before and after gamma modification,
# imageseg= np array with shadows marked as 0.

    
def gamfun(num,gam=.6, plot=False, manualbound = 130):
    #print(num)
    #this section causes some errors to pop up between threads, two can try and make it at the same time...
    if manualbound:
        runfile = 'gam%s_manbound%s//'%(int(gam*1000),int(manualbound))
    else:
        runfile = 'gam%s_bound%s//'%(int(gam*1000),int(boundfrac*1000))
    if not os.path.exists('%s%s'%(PATH,runfile)):
        try:
            os.makedirs('%s%s'%(PATH,runfile))
        except(WindowsError):
            #this is in case two threads try and make something at the same time
            #is it dirty? yes, does it work? also yes.
            pass
    try:
       image = imageio.imread('%s%s%s.PNG'%(PATH,FNM,num))
    except(ValueError, SyntaxError):
        return None, False, runfile
    if isinstance(image[0][0], list):
         #Black and White PNGs store three (identical) values per pixel, this flattens pngs into a 2-D array
        imagetemp = np.zeros((len(image),len(image[0])),dtype=np.uint16)
        for i in range(len(imagetemp)):
            for j in range(len(imagetemp[0])):
                imagetemp[i][j]=image[i][j][0]
        image=imagetemp
    #sharpening was attempted, it destroyed any boulder shapes, left for now
    #image = skrank.enhance_contrast(image, skmorph.disk(3))
##    if NOMAP:
##        rotang = 90+SAZ
##            else:
##        #rotang = NAZ-SAZ
##        rotang = -sunangle
        
    image = sktrans.rotate(image,ROTANG, resize=True, preserve_range=True)
    image = npma.masked_equal(image, 0)

    ''' rotation seems to cause some stray data to appear at the edge, this is often
        categorized as shadows because it is very dark but not zero, this code will
        essentially erode the edges a bit, shifting the mask up, down, left and right
        and taking the logical OR of the two masks, masking things that are adjacent to
        the mask in any direction
        '''
    shift = np.roll(image.mask,1,1)
    image.mask = np.logical_or(image.mask, shift)
    shift = np.roll(image.mask,-1,1)
    image.mask = np.logical_or(image.mask, shift)
    shift = np.roll(image.mask,1,0)
    image.mask = np.logical_or(image.mask, shift) 
    shift = np.roll(image.mask,-1,0)
    image.mask = np.logical_or(image.mask, shift)
    
    #image.dump('%s%s%s%s_rot_masked.npy'%(PATH,runfile,FNM,num))
    #rotation incurs some kind of offset to the pixel value, meaning much of the area isnt '0' anymore
    #recasting as int may solve this problem
    
    pixels = len(image)*len(image[0])

    #if the image is just blank, side effect of projected images
    if not np.any(image.compressed()):
        return None, False, runfile

    #do the actual gamma correction,
    
    top = 0.
    image = image**float(gam)
    top = np.max(image)
    scale = 255./top
    image = image*scale
    image = image.astype(int)

    #making sure the boundary is a float
    bound = float(manualbound)
    
    #print ("Shadow value boundary at:%s"%(bound))
##    imageseg = np.zeros_like(imagemod, dtype=np.uint32)
##    for i in range(len(image)):
##        for j in range(len(image[0])):
##            if imagemod[i][j] >bound:
##                imageseg[i][j]=1
    #doing the indexing in the fastest way always passes the mask, so we are unmasking
    #filling in the values with an impossible number, then putting it all back in
    imageseg = npma.copy(image)
    imageseg = imageseg.astype(float)
    imageseg = imageseg.filled(-1)

    imageseg[imageseg>bound+1] = bound+1
    imageseg = npma.masked_equal(imageseg, -1)    
    imageseg = imageseg.astype(int)
    imageseg.fill_value = 0
    
    imageseg.dump("%s%s%s%s_SEG.npy"%(PATH,runfile,FNM,num))
    #this is the full figure suite, which struggles when you have a big image
    if plot:
        fig,ax = plt.subplots(1,2,sharex = True, sharey = True)
        ax[0].imshow(image, cmap='binary_r', interpolation='none')
        ax[1].imshow(imageseg,vmax = bound, vmin = bound-1, interpolation='none')
##        plt.figure(1)
##        plt.title('Gamma stretched image')
##        plt.imshow(imagemod, cmap='binary_r')
##        plt.figure(2)
##        plt.title('shadows isolated image')
##        plt.imshow(imageseg)
        #plt.figure (3)
        #plt.imshow(sktrans.rotate(image,-SUNANGLE,resize=True, preserve_range=True), cmap='binary_r')

        plt.show()
    #This makes sure that images with data but no shadows do not go through the segmentation process
    if np.min(imageseg)>= bound:
        good = False
    else:
        good=True
    return(imageseg, good ,runfile)


#this method uses a gaussian fit to the data to find the shadow boundary
#it takes in the linearized image that you want to use and returns the shadow boundary
def gauss(x,sig,mu):
    y = (1./(sig*np.sqrt(2.*np.pi)))*np.exp((-1./2.)*(((x-mu)/sig)**2.))
    return y
def gauss_unnorm(x,sig,mu):
    y = np.exp((-1/2)*((x-mu)/sig)**2)
    return y


#########This is the measuring side of things#####################################

def boulderdetect(num,image,runfile):
    #deprecated, uses threadsafe version now
    #flag must be dtype long, otherwise it will wrap at high numbers and reset the flag to 1
    flag = long(1)
    coords = [0,0]
    save = open("%s%s%s%s_shadows.shad"%(PATH,runfile, FNM,num), 'wb')
    im_area = len(image)*(len(image[0]))
    #flagged image has the boulders marked
    #print 'Running Watershed %s\n'%(num)
    fimage = watershedmethod(image)
    #have to explicitly pass the mask on from the input image
    fimage = npma.masked_array(fimage)
    fimage.dump('%s%s%s%s_flagged.npy'%(PATH, runfile,FNM,num))
    fimage.mask = image.mask

    #close the seg image to open up memory
    image = None
    fmax = np.max(fimage)
    #shadows = []
    #print 'finding shadows %s \n'%(num)
    shade=None
    for i in range(fmax+1):
        #print 'flag %s image %s\n'%(i,num)
        pixels = np.argwhere(fimage == i)
        #must be converted to list for the neighbor-checking function to work
        pixels = pixels.tolist()
        if len(pixels) >=minA and len(pixels)<MA:
            
            shade = shadow(i, pixels, im_area)
            
            shade.run()
            
            pickle.dump(shade,save)
    save.close() 
    return

def boulderdetect_threadsafe(num,image,runfile,odr_keycard):
    #flag must be dtype long, otherwise it will wrap at high numbers and reset the flag to 1
    flag = long(1)
    coords = [0,0]
    save = open("%s%s%s%s_shadows.shad"%(PATH,runfile, FNM,num), 'wb')
    im_area = len(image)*(len(image[0]))
    #flagged image has the boulders marked
    #print 'Running Watershed %s\n'%(num)
    fimage = watershedmethod(image)
    #have to explicitly pass the mask on from the input image
    fimage = npma.masked_array(fimage)
    fimage.dump('%s%s%s%s_flagged.npy'%(PATH, runfile,FNM,num))
    fimage.mask = image.mask
    fmax = np.max(fimage)
    #clear the seg image to save memory
    image = None
    shade=None
    for i in range(fmax+1):
        
        pixels = np.argwhere(fimage == i)
        #must be converted to list for the neighbor-checking function to work
        pixels = pixels.tolist()
        
        if len(pixels) >=minA and len(pixels)<MA:
            
            shade = shadow(i, pixels, im_area)
            
            #broken into 3 steps to narrow the thread-unsafe part into one function
            shade.run_prep()
            with odr_keycard:
                shade.run_fit()
            shade.run_post()
            
            pickle.dump(shade,save)
    save.close()
    
    return
            
def watershedmethod(image):
    #this is the new way of finding the shadows in an image
    #first find the "plateau" value, we will need this for masking
    plat = sps.mode(image.compressed())
    #fill the image with a known value in order to preserve the mask
    temp = image.filled(np.max(image)+1)
    #invert the image so the shadows are peaks not lows
    temp = temp*(-1)+np.max(image)+1
    #find the peaks in the image, return the points as a nx2 array
    points = skfeat.peak_local_max(temp,min_distance=1, indices=True)

    #put in a guard against images with no shadows
    threshold = len(image.compressed())/2
    if len(points)>threshold:
        return np.ones_like(image)
    #prepare to convert the points matrix to an image-like array
    #this could perhaps be done with DBSCAN
    
    cores,labels = skcluster.dbscan(points,2,2)
    
    view = np.zeros_like(image)
    flag = 2
    excl = []
    for i in range(len(points)):
        if labels[i] == -1:
            view[points[i][0]][points[i][1]] = flag
            flag+=1
        elif labels[i] not in excl:
            view[points[i][0]][points[i][1]] = flag
            excl+=[flag]
            flag+=1

    #this will make the mask on view mask out the originally masked points (outside data)
    # as well as the plateau pixels
    temp = npma.masked_equal(image, plat[0][0])
    view.mask = np.logical_or(temp.mask, view.mask)
        
    '''details on the arguments being handed to watershed:
        in general ,the algorithm doesnt like masked arrays, hence everything is filled
        the masks are added back in the makeshadows code above
        the mask at the ennd prevents it from trying to segment all the no-data areas
        however it takes the mask in the opposite sense of the masked arrays
        in ndarrays, the mask is True where you want it masked, watershed wants 0
    '''
            
    boulds = skmorph.watershed(image.filled(np.max(image)+1), view.filled(0),mask=~view.mask)

    return boulds
def overlapcheck_threadsafe_DBSCAN(num,runfile,odr_keycard,overlap=.1):
    '''
    Code to get rid of double-counts in returned boulders, inputs:
    num - num of target image
    runfile - current runfile for shad file finding purposes
    overlap - allowed overlap between boulders, expressed in fraction of boulder area
    '''
    shadow_file = getshads(runfile, num,mode='r')
    if shadow_file == None:
        return
    parameters = []
    while True:
        try:
            data = pickle.load(shadow_file)
        except(EOFError):
            break
        #pull in the flag, the y coordiante, the x coordinate, and the width
        parameters+=[[data.flag,data.bouldcent[0],data.bouldcent[1],data.bouldwid]]
    #get rid of boudlers with no measurements
    parameters = [a for a in parameters if a[3]]
    if len(parameters) == 0:
        shadow_file.close()
        return

    #compute modified distance matrix
    #make meshgrids of every number in the calculation
    ya,yb = np.meshgrid([a[1] for a in parameters],[a[1] for a in parameters])
    xa,xb = np.meshgrid([a[2] for a in parameters],[a[2] for a in parameters])
    da,db = np.meshgrid([a[3] for a in parameters],[a[3] for a in parameters])
    
    #calculate the distance ratio
    #D = euclidean distance between points/sum of radii, this way boulders that touch have a D of 1 or less
    D = 2*np.sqrt((ya-yb)**2+(xa-xb)**2)/(da+db)
    #this is now the Distance matrix to pass to DBSCAN
    #arguments that go to DBSCAN: D, distance matrix, 1=distance to be considered neighbors, 2 min number to form group, metric: Since we are passing a distance matrix, precomputed
    cores,labels = skcluster.dbscan(D,1,2,metric='precomputed')
    #cores is a list of 'core' points, less important than labels, which groups the points into unified labels, -1 means they arent in any clusters
    #add these to the parameters list
    for i in range(len(parameters)):
        parameters[i]+=[labels[i]]
    #make our 'web' of flags, a list where every sublist is flags that are interconnected
    webs = []
    for i in range(max(labels)):
        subweb=[]
        for j in parameters:
            if j[4] == i:
                subweb+=[j[4]]
        webs+=[subweb]
    
    #now lets re-read in the shadow data
    shadow_file.seek(0)
    og_data = []
    while True:
        try:
            og_data+=[pickle.load(shadow_file)]
        except(EOFError):
            break
    #close and re-open for re-writing
    shadow_file.close()
    shadow_file = getshads(runfile,num,mode='w')

    
    problem_flags = [a[0] for a in parameters if a[4]!=-1]
    problem_boulders = []
    for i in og_data:
        if i.flag in problem_flags:
            problem_boulders+=[i]
        else:
            pickle.dump(i,shadow_file)
    og_data = None

    #OK with just the problem_boulders list, we can do the work
    for subweb in webs:
        #print subweb
        current_web = []
        #take the web list (which is just flags) and make a list of shadow objects
        for bould in problem_boulders:
            if bould.flag in subweb:
                current_web+=[bould]
        
        
        #merge = True
        while True:
            #print 'Current_web length: %s'%(len(current_web))
            #reset to no merge
            merge = False
            #current_web = newboulds
            newboulds = []
            for a in current_web:
                if merge:
                    continue
                #A_flag = j.flag
                for b in current_web:
                    if merge:
                        continue
                    #B_flag = k.flag
                    if a.flag != b.flag:
                        #look for overlapping pairs in the web
                        area = checkpos(a,b)
                        
                        if area > overlap:
                            #if they overlap too much, make a new shadow that combines their pixels and re-run
                            newbould=shadow(a.flag, a.pixels+b.pixels, a.im_area)
                            newbould.run_prep()
                            with odr_keycard:
                                newbould.run_fit()
                            newbould.run_post()
                            #you found two that needed to merge
                            A_flag = a.flag
                            B_flag = b.flag 
                            #print 'Merged %s and %s'%(A_flag,B_flag)
                            merge = True
            if merge:
                #since you found two that merged, dont add them to the next web and put the new one in
                
                for bould in current_web:
                    if bould.flag != A_flag and bould.flag != B_flag:
                        newboulds+=[bould]
                        #print bould.flag
                newboulds+=[newbould]
                current_web = newboulds
            else:
                break
                
                
            #if no merges are found in the inner loops, the code will continue to the next web
        #now save all these new ones you just made
        for boulder in current_web:
            #print'Dumping shadows'
            pickle.dump(boulder,shadow_file)
    shadow_file.close()
    return
    
                         
def touch(array,pos,wid,indflag,indpos,indwid,ind, plus=False,minus=False):
    '''Corrolary to the above overlap check function '''
    #no longer in use
    
    rad = wid/2.
    neighborflags = []
    #check the neighbors
    try:
        if (array[ind+1][indpos]-(array[ind+1][indwid])/2.) < (pos+rad) and plus:
            neighborflags+=[array[ind+1][indflag]]
            try:
                neighborflags+=touch(array,pos,wid,indflag,indpos,indwid,ind+1,True,False)
            except(RuntimeError):
                pass
    except(IndexError):
        pass
    try:
        if (array[ind-1][indpos]+(array[ind-1][indwid]/2.)) > (pos-rad) and minus:
            neighborflags+=[array[ind-1][indflag]]
            try:
                neighborflags+=touch(array,pos,wid,indflag,indpos,indwid,ind-1,False,True)
            except(RuntimeError):
                pass
    except(IndexError):
        pass
    return neighborflags

def webfinder(array,web):
    '''Corrolary to the overlap check function '''
    #no longer in use
    oldweb = web
    for i in web:
        for j in array:
            if i in j:
                for k in j:
                    if k not in web:
                        web+=[k]
    if oldweb != web:
        web = webfinder(array,web)
    else:
        return web
    
def checkpos(shadow1,shadow2):
    '''expects two shadow objects , checks how much they overlap
    returns a fraction of the area of the smaller boulder overlapped by the larger
    '''
    bouldwid1 = shadow1.bouldwid
    bouldwid2 = shadow2.bouldwid

    pos1 = shadow1.bouldcent
    pos2 = shadow2.bouldcent
    #if one is unmeasured or has no dimensions, forget it
    if pos1[0] == None or pos2[0] == None:
        return 0.
    #distance between the two circles
    d = np.sqrt((pos1[0]-pos2[0])**2+(pos1[1]-pos2[1])**2)
    r1 = bouldwid1/2.
    r2 = bouldwid2/2.
    if r1>=r2:
        ra = r1
        rb = r2
    else:
        ra = r2
        rb = r1
    #lets throw out some simple scenarios
    #the circles exactly reach or do not overlap
    if d>= ra+rb:
        return 0.
    #if the smaller is fully in the larger:
    if d+rb <=ra:
        return 1.
    #if the center of one is within the other, but not entirely
    if ra>d and d+rb>ra:
        #returning 1 beccause I always want these to merge
        return 1.
    else:
        #note: all this work is done in pixels not meters
        x = (ra**2 - rb**2 + d**2)/(2*d)
        y = np.sqrt(ra**2+x**2)
        #note: this returns in radians
        thetaA = np.arccos(x/ra)
        thetaB = np.arccos((d-x)/rb)
        #relevant EQ, area of circle slice: piR^2*(2theta/2pi), triangle .5*b*h
        area = (ra**2)*thetaA - x*y + (rb**2)*thetaB - (d-x)*y
        area = area/(np.pi*rb**2)
        return area
    

class shadow(object):

    def __init__(self, flag, pixels, im_area):
        #marker for this boulder, unique
        self.flag = flag
        #immediate pixels in this shadow
        self.pixels = pixels
        #pixels in the mirrored shadow
        self.mpixels = None
        #area of the shadow, based on how many pixels are in it
        self.area = len(pixels)
        #area for the mirrored shadow, simply 2*area for now, may change
        self.marea = 2*self.area
        #incedence angle of the sun, fixed by target image
        self.inangle = INANGLE
        #angle of the sun, fixed as coming from top (-y), this is holdover till
        #code sentive to angle is entirely gone
        self.beta = np.radians(270)
        #image resolution, tied to each shadow image for safekeeping
        self.resolution = RESOLUTION
        #image area (pixels^2) tied to each shadow for safekeeping
        self.im_area = im_area
        #find the center of the shadow
        tempx = 0.
        tempy = 0.
        for i in range(len(pixels)):
            tempy +=pixels[i][0]
            tempx +=pixels[i][1]
        self.center = [tempy/float(len(pixels)),tempx/float(len(pixels))]
        #border of the shadow
        self.border = []
        #initially, the border of the shadow without the -y(upper) side,
        #finally the rim of the mirrored shadow
        self.mborder = []
        #the flipping axis of the shadow
        self.flipaxis = []
        #initial conditions for the non Area-preserving and AP fits, 
        self.fitinit = [self.center[0], 2.0,self.center[1], 2.0, 0.]
        self.AP_fitinit = [self.center[0],2.0, self.center[1], 0.]
        #Empty variable, will be the return from the ODR fit
        self.fitbeta = None
        #Is the fit good assumed False, see ODRFit functions for conditions
        self.fitgood = False
        #records stoppping condition of the ODR, <4 is good, >4 is bad, 4 is OK
        self.fitinfo = None

        
        #has the boulder been assessed?
        self.measured = None

        #boulder morphometry
        #boulder width in pixels and meters
        self.bouldwid = None
        self.bouldwid_m = None
        #height of boulder in pixels and meters
        self.bouldheight = None
        self.bouldheight_m = None
        #center of fit ellipse
        self.bouldcent = [None, None]
        #semi-axis along the sun direction in pixels and meters
        self.shadlen = None
        self.shadlen_m = None
        #placeholder for the patch object
        self.ellipsepatch = None

    def run_prep(self):
        #main function that does most things we want it to do
        
        self.findborder()
        self.mirror()
        
    def run_fit(self):
        #to change the kind of border fit used, alter this line
        self.odrfit_m()

    def run_post(self):
        if self.fitgood:
            self.shadowmeasure_m()
        
    def findborder(self):
        #we will look at each point and see if it has neighbors, if not, there is a border
        #this cannot be the most efficient way to do this....
    
        for i in self.pixels:
            top=False
            other = False
            if [i[0]-1,i[1]] not in self.pixels:
                self.border+= [[i[0]-.5, i[1]]]
                self.border+= [[i[0]-.5, i[1]+.5]]
                self.flipaxis+= [[i[0]-.5, i[1]]]
                self.flipaxis+= [[i[0]-.5, i[1]+.5]]
                top = True
                
            if [i[0]+1,i[1]] not in self.pixels:
                self.border+= [[i[0]+.5, i[1]]]
                self.border+= [[i[0]+.5, i[1]-.5]]
                self.mborder+= [[i[0]+.5, i[1]]]
                self.mborder+= [[i[0]+.5, i[1]-.5]]
                

            if [i[0],i[1]+1] not in self.pixels:
                self.border+= [[i[0], i[1]+.5]]
                self.border+= [[i[0]+.5, i[1]+.5]]
                if not top:
                    self.mborder+= [[i[0], i[1]+.5]]
                    self.mborder+= [[i[0]+.5, i[1]+.5]]
                

            if [i[0],i[1]-1] not in self.pixels:
                self.border+= [[i[0], i[1]-.5]]
                self.border+= [[i[0]-.5, i[1]-.5]]
                if not top:
                    self.mborder+= [[i[0], i[1]-.5]]
                    self.mborder+= [[i[0]-.5, i[1]-.5]] 
    def mirror(self):
        ''' this takes the boulder shadow and border and flips it along the
            sun_perpendicular vector, which is the x axis in all cases.
            By  doing this we can fit an ellipse to what is actually an ellipse,
            theoretically giving better fits. the points flip along the MIN (most sunward)
            pixel value, 
            '''
        #step 1, find the flip axis
        yvals = np.array(self.flipaxis)
        yvals = yvals[range(len(yvals)),[0]]
        #this is the flip value
        #flipval = np.average(yvals)
        flipval = np.min(yvals)
        #make a copy of the mborder, which lacks the -y boundary
        temp = np.copy(self.mborder)
        dist = range(len(temp))
        #invert that about the flip value
        temp[dist,[0]]*=-1
        temp[dist,[0]]+=2*flipval
        #mborder is stored as a list, lets keep it that way
        temp = temp.tolist()
        #append it and you are done
        self.mborder+=temp
        return
 
    def odrfit(self):
        #not used, odrfit_m is used
        input_y = list(map(lambda f:f[0], self.border))
        input_x = list(map(lambda f:f[1], self.border))
        input_dat = [input_y, input_x]
        fit_data = odr.Data(input_dat, y=1)
        fit_model = odr.Model(self.ellipse, implicit=True)
        fit_odr = odr.ODR(fit_data, fit_model, self.fitinit)
        fit_out = fit_odr.run()
        self.fitinfo = str(fit_out.info)

        cutoff = 75
        if fit_out.beta[1] > cutoff or fit_out.beta[3] > cutoff:
            self.fitgood = False
        elif self.fitinfo == "2" or self.fitinfo == "3" or self.fitinfo == "1":
            self.fitgood = True
        
        #fit_out.pprint()
        self.fitbeta = fit_out.beta
        
    def AP_odrfit(self):
        #not used, odrfit_m is used
        input_y = list(map(lambda f:f[0], self.border))
        input_x = list(map(lambda f:f[1], self.border))
        input_dat = [input_y, input_x]
        fit_data = odr.Data(input_dat, y=1)
        fit_model = odr.Model(self.AP_ellipse, implicit=True)
        
        fit_odr = odr.ODR(fit_data, fit_model, self.AP_fitinit)
        fit_out = fit_odr.run()
        self.fitinfo = str(fit_out.info)
        temp = fit_out.beta
        self.fitbeta = [temp[0],temp[1], temp[2], self.area/(np.pi*temp[1]),temp[3]] 

        #cutoff for areas of boulders, throws out any fits that are too big
        area = np.pi*self.fitbeta[1]*self.fitbeta[3]
        if area > MA:
            self.fitgood = False
        elif self.fitinfo == "2" or self.fitinfo == "3" or self.fitinfo == "1" or self.fitinfo == '4':
            self.fitgood = True
        return
    def AP_odrfit_m(self):
        #not used, odrfit_m is used
        input_y = list(map(lambda f:f[0], self.mborder))
        input_x = list(map(lambda f:f[1], self.mborder))
        input_dat = [input_y, input_x]
        fit_data = odr.Data(input_dat, y=1)
        fit_model = odr.Model(self.AP_ellipse, implicit=True)
        fit_odr = odr.ODR(fit_data, fit_model, self.AP_fitinit)
        fit_out = fit_odr.run()
        self.fitinfo = str(fit_out.info)
        temp = fit_out.beta
        self.fitbeta = [temp[0],temp[1], temp[2], self.marea/(np.pi*temp[1]),temp[3]] 

        #cutoff for areas of boulders, throws out any fits that are too big
        area = self.marea
        if area > MA or self.fitbeta[1] > MD or self.fitbeta[3] > MD:
            self.fitgood = False
        elif self.fitinfo == "2" or self.fitinfo == "3" or self.fitinfo == "1" or self.fitinfo == '4':
            self.fitgood = True
        return

    def odrfit_m(self):
        input_y = list(map(lambda f:f[0], self.mborder))
        input_x = list(map(lambda f:f[1], self.mborder))
        input_dat = [input_y, input_x]
        fit_data = odr.Data(input_dat, y=1)
        fit_model = odr.Model(self.ellipse, implicit=True)
        fit_odr = odr.ODR(fit_data, fit_model, self.fitinit)
        #print 'doing ODR'
        fit_out = fit_odr.run()
        #print 'ODR done'
        self.fitinfo = str(fit_out.info)

        self.fitbeta = fit_out.beta

        area = abs(np.pi*self.fitbeta[1]*self.fitbeta[3])
        if area> MA or self.fitbeta[3]*2 > MD:
            self.fitgood = False
        elif self.fitinfo == "2" or self.fitinfo == "3" or self.fitinfo == "1" or self.fitinfo == '4':
            self.fitgood = True
        return
        #fit_out.pprint()
        
    def shadowmeasure_m(self):
        '''shadow measuring now that we are doubling the shadow, very straightforward'''
        #despite not being constrained, the fit ellipses are pretty much either veritcal or horizonal
        # so np.cos(alpha) is essentially either 0,1, or -1, or at least close to it. With this
        #non-zero results (~1 or -1) will be negative, others will be positive
        test = .5 - abs(np.cos(self.fitbeta[4]))
        
        if test <= 0:
            factor = np.cos(self.fitbeta[4])
            self.bouldwid = 2*abs(factor*self.fitbeta[3])
            self.shadlen = abs(factor*self.fitbeta[1])
            self.bouldcent = [self.fitbeta[0],self.fitbeta[2]]
            self.bouldheight = self.shadlen/np.tan(np.radians(self.inangle))
            self.measured = True
        if test > 0:
            factor = np.sin(self.fitbeta[4])
            self.bouldwid = 2*abs(factor*self.fitbeta[1])
            self.shadlen = abs(factor*self.fitbeta[3])
            self.bouldcent = [self.fitbeta[0],self.fitbeta[2]]
            self.bouldheight = self.shadlen/np.tan(np.radians(self.inangle))
            self.measured = True
        self.bouldwid_m = self.bouldwid*self.resolution
        self.shadlen_m = self.shadlen*self.resolution
        self.bouldheight_m = self.bouldheight*self.resolution
        if self.bouldwid > MD or self.bouldheight > MH:
            self.measured = False
        return
        
    def ellipse (self, beta, coords):
        '''note alpha (beta[4]) is recorded in radians'''
        y = coords[0]
        x = coords[1]

        yc = beta[0]
        xc = beta[2]
        ay = beta[1]
        ax = beta[3]
        alpha = beta[4]
        #alpha is the clockwise angle of rotation
        #alpha = np.arctan(self.sunangle[1]/self.sunangle[0])
        return (((y-yc)*np.cos(alpha)+(x-xc)*np.sin(alpha))/ay)**2 + (((x-xc)*np.cos(alpha)-(y-yc)*np.sin(alpha))/ax)**2 - 1
###Got doubled somehow, this one uses self.area (the area of the shadow) as opposed to marea (mirrored area, the double shadow area)
##    def AP_ellipse(self, beta, coords):
##        y = coords[0]
##        x = coords[1]
##        yc = beta[0]
##        xc = beta[2]
##        ay = beta[1]
##        ax = self.area/(np.pi*ay)
##        #alpha is the clockwise angle of rotation
##        alpha = beta[3]
##        return (((y-yc)*np.cos(alpha)+(x-xc)*np.sin(alpha))/ay)**2 + (((x-xc)*np.cos(alpha)-(y-yc)*np.sin(alpha))/ax)**2 - 1

    def AP_ellipse(self, beta, coords):
        y = coords[0]
        x = coords[1]
        yc = beta[0]
        xc = beta[2]
        ay = beta[1]
        ax = self.marea/(np.pi*ay)
        #alpha is the clockwise angle of rotation
        alpha = beta[3]
        return (((y-yc)*np.cos(alpha)+(x-xc)*np.sin(alpha))/ay)**2 + (((x-xc)*np.cos(alpha)-(y-yc)*np.sin(alpha))/ax)**2 - 1

    def patchplot(self):
        #this will be the new ellipse plotting function that uses the matplotlib patches function
        #need to figure out how to make sure they are plotting correctly though...
       
        color = 'g'
        alpha = .2
        if self.measured:
            angle = np.degrees(np.pi-(self.fitbeta[4]%(2*np.pi)))
            shadow = patches.Ellipse([self.fitbeta[2],self.fitbeta[0]], self.fitbeta[3]*2., self.fitbeta[1]*2., angle, color = color, alpha = alpha)
            boulder = patches.Circle([self.bouldcent[1],self.bouldcent[0]], (self.bouldwid/2.), alpha=alpha)
            return [shadow, boulder]
        else:
            return []

            
##############Some tools for analysis##########
def current():
    print 'Current Path is: %s'%(PATH)
    print 'Current Filename is: %s'%(FNM)
    print 'current Product ID is: %s'%(ID)
    return
def getshads(runfile, num, silenced = True, mode='r'):
    #open and prep a shadow file, returns open file object and endpoint
    #current()
    try:
        load = open('%s%s%s%s_shadows.shad'%(PATH,runfile,FNM,num), mode)
    except IOError:
        if not silenced:
            print "No shadow file exists"
        return None
    except:
        if not silenced:
            print'Likely broken file'
        return None
    return load
def GISprep(runfile,num,mod):
    '''Deprecated, use OutToGIS() instead'''
    #this takes the target file and makes the necessary  arc documents to plot them
    #assumes that source image and matching arc documents are available in same folder
    #mod is tacked onto the name, SEG will match with segmented images for example
    shutil.copyfile('%s%s%s.PGw'%(PATH,FNM,num),'%s%s%s%s_%s.PGw'%(PATH,runfile,FNM,num,mod))
    shutil.copyfile('%s%s%s.PNG.aux.xml'%(PATH,FNM,num),'%s%s%s%s_%s.PNG.aux.xml'%(PATH,runfile,FNM,num,mod))
    ###OVRs are just pyramid data, dont need to copy those
    ##shutil.copyfile('%s%s%s.PNG.ovr'%(PATH,FNM,num),'%s%s%s%s_%s.PNG.ovr'%(PATH,runfile,FNM,num,mod))
def bulkCFA(runfile,maxnum,maxd,fitmaxd,root):
    ''' runs the CFA protocol on a bunch of files and gives an average
'''
    #set value for maximum on plots (in meters)
    plotmax = 3
    while True:
        new = raw_input('make new CDFs? y/n\n')
        if new == 'y' or new == 'n':
            break
    allCFAs = []
    if new == 'n':
        for i in range(maxnum):
            try:
                data = open('%s%s%s%s_CFA.csv'%(PATH,runfile,FNM,i),'r')
                dat = np.loadtxt(data,delimiter=',')
                
            except(IOError):
                continue

            allCFAs+=[dat]
        if allCFAs == []:
            print "No CDFs Present"
            new = 'y'
    if new == 'y':
        for i in range(maxnum):
            #acuire all the CFA data, this will come in the form:
            #CFA[0] = bins
            #CFA[1] = lower error bound CFA
            #[2] = actual CFA data
            #[3] = Upper bound error CFA
            dat = CFA(runfile,i, maxd)
            #Keep an eye on this, would break quickly if CFA is changed
            if len(dat) == 3:
                #plt.plot(dat[0],dat[2],'b-',alpha=.05)
                allCFAs+=[dat]
                #print len(dat)

##    if not any(allCFAs):
##        return None, None
    #extract bins and the three CFAs (upCFAs = upper end of CFA uncertainty, downCFAs lower end of uncertainty)
    #above method is being revised, shifting to a sigma calculation
    bins = allCFAs[0][0]
    allCFAs = np.array(allCFAs)
    #CFAs = allCFAs[:,2]
    #upCFAs = allCFAs[:,1]
    #downCFAs = allCFAs[:,3]
    CFAs = allCFAs[:,1]
    CFAsigmas = allCFAs[:,2]
    #tranpose the files to go from (image,bins) to (bins,image) format
    T_CFAs = np.transpose(CFAs)
    T_CFAsigmas = np.transpose(CFAsigmas)
    #T_upCFAs = np.transpose(upCFAs)
    #T_downCFAs = np.transpose(downCFAs)
    #average accross bins, results in 1-D array of length 'bins'
    #also fetch a 25% and 75% CFA curve
    avgCFAs = map(np.average,T_CFAs)
    topqCFAs = map(lambda x: np.percentile(x,75),T_CFAs)
    botqCFAs = map(lambda x: np.percentile(x,25),T_CFAs)
    avgCFAsigmas = []
    
    for i in T_CFAsigmas:
        sigma = (1/float(len(i)))*(np.sqrt(sum(map(lambda x: x**2,i))))
        avgCFAsigmas+=[sigma]
    avgupCFAs = []
    avgdownCFAs = []
    for i in range(len(avgCFAs)):
        avgupCFAs+=[avgCFAs[i]+avgCFAsigmas[i]]
        avgdownCFAs+=[avgCFAs[i]-avgCFAsigmas[i]]
    #avgupCFAs = map(np.average,T_upCFAs)
    #avgdownCFAs = map(np.average,T_downCFAs)
##    print bins
##    print CFAs
##    print upCFAs
##    print downCFAs
    #fit to each end of the spectrum
    fit_k, fit_r2 = fittoRA(bins,avgCFAs, [1.5,fitmaxd])
    #upfit_k, upfit_r2 = fittoRA(bins,avgupCFAs, [1.5,maxd])
    #downfit_k, downfit_r2 = fittoRA(bins,avgdownCFAs, [1.5,maxd])
    upfit_k, upfit_r2 = fittoRA(bins,avgupCFAs, [1.5,fitmaxd])
    downfit_k, downfit_r2 = fittoRA(bins,avgdownCFAs, [1.5,fitmaxd])
    topqfit_k, topqft_r2 = fittoRA(bins,topqCFAs,[1.5,fitmaxd])
    botqfit_k, botqft_r2 = fittoRA(bins,botqCFAs,[1.5,fitmaxd])
    
    #calculate RA for each side of uncertainty
    fit_bins = np.linspace(min(bins),max(bins),100)
    fitRA = GolomPSDCFA(fit_bins,fit_k)
    upfitRA = GolomPSDCFA(fit_bins,upfit_k)
    downfitRA = GolomPSDCFA(fit_bins,downfit_k)
    topqfitRA = GolomPSDCFA(fit_bins,topqfit_k)
    botqfitRA = GolomPSDCFA(fit_bins,botqfit_k)

    #plot them all!
    #errors in format of array [2,bins] all must be positive, lower errors first, see matplotlib API
    errors = []
    errors+=[fitRA-downfitRA]
    errors+=[upfitRA-fitRA]
    #plots stack in reverse, so plot what you want on top first (I think...)
    plt.errorbar(bins,avgCFAs,label = root,zorder=3, yerr = avgCFAsigmas,fmt = 'none', ecolor = 'g', c = 'g', marker='|')
    
    plt.errorbar(fit_bins,fitRA,zorder=2,label = 'RA Envelope',yerr = errors,ecolor = 'k',c = 'k',marker='|',alpha=.5)
    plt.plot(fit_bins,topqfitRA,zorder=3,label = '75th Percentile RA')
    plt.plot(fit_bins,botqfitRA,zorder=3,label = '25th Percentile RA')
    plotCFArefs(plotmax)
    plt.xscale('log')
    plt.yscale('log')
    plt.xlim(xmin= 1, xmax = plotmax)
    plt.xlabel('Boulder Diameter (m)')
    plt.ylabel('Cumulative Fractional Area')
    plt.ylim(ymin=10**(-5))
    plt.legend(loc=3)
    plt.title('CFA for image %s at parameters %s'%(root,runfile))
    plt.savefig('%s%sCFAPlot.png'%(PATH,runfile))

    #save the CFA data:
    savecfa = open('%s%sCFAdata_maxd_%s_fitmaxd_%s.csv'%(PATH,runfile,maxd,fitmaxd),'w')
    savecfa.write('Bins,')
    for i in bins:
        savecfa.write('%s,'%i)
    savecfa.write('\n')
    savecfa.write('avgCFA,')
    for i in avgCFAs:
        savecfa.write('%s,'%i)
    savecfa.write('\n')
    savecfa.write('sigma,')
    for i in avgCFAsigmas:
        savecfa.write('%s,'%i)
    savecfa.write('\n')
    savecfa.write('topq,')
    for i in topqCFAs:
        savecfa.write('%s,'%i)
    savecfa.write('\n')
    savecfa.write('botq,')
    for i in botqCFAs:
        savecfa.write('%s,'%i)
    savecfa.write('\n')
    savecfa.close()
    #plt.show()
    return fit_k,topqfit_k,botqfit_k, fit_r2
    
def CFA(runfile,num,maxd):
    #Produces data for Cumulative Fractional Area, saves and produces plot
    #plt.show must be called after to plot all the data
    load = getshads(runfile,num)
    sizes = []
    if not load:
        return [None]
    while True:
        try:
            dat = pickle.load(load)
        except EOFError:
            break
        if dat.measured:
            sizes+=[dat.bouldwid_m]
    
            res = dat.resolution
            #may need to re-run some boulder detection to get this into the shad file
            im_area = dat.im_area
    if not any(sizes):
        return [None]
    #im = imageio.imread('%s%s%s.PNG'%(PATH,FNM,num))
    #im = npma.array(im)
    #get the image area in meters
    #im_area = float(len(im.compressed()))*res*res
    #print area
    #create the two ends of the uncertainy spectrum, assumes 1 pixel uncertainty
    err = 1
    sigma = err*res
    sizes = np.asarray(sizes)
    
    sizes = [x for x in sizes if x < maxd]
    
    sizes = np.asarray(sizes)
    
    bins = np.linspace(0,maxd,20*maxd+1)
    SFD, binsconf = np.histogram(sizes, bins=bins)
    #SFD = np.append(SFD,0)
    SFD = SFD/im_area
    sizes.sort()

    #Total  Area, sum of all boudlers
    #TA = sum(areas)
    #CFA will be a list of y points, with the x points in sizes
    CFA = np.zeros_like(bins)
    CFAsigma = np.zeros_like(bins)
    #upCFA = np.copy(CFA)
    #downCFA = np.copy(CFA)
    for i in range(len(bins)):
        CFA[i] = float(sum(map(lambda x: np.pi*((x/2.)**2),sizes[sizes>bins[i]])))/im_area
        CFAsigma[i] = sigma*np.sqrt((np.pi/im_area)*CFA[i])
        #upCFA[i] = float(sum(map(lambda x: np.pi*((x/2.)**2),upsizes[upsizes>bins[i]])))/im_area
        #downCFA[i] = float(sum(map(lambda x: np.pi*((x/2.)**2),downsizes[downsizes>bins[i]])))/im_area
    #save1 = [bins,upCFA.tolist(),CFA.tolist(),downCFA.tolist()]
    save1 = [bins,CFA.tolist(), CFAsigma.tolist()]
    save2 = [binsconf[:-1].tolist(),SFD.tolist()]
    cfasavefile = open('%s%s%s%s_CFA.csv'%(PATH,runfile,FNM,num),'w')
    np.savetxt(cfasavefile, save1,delimiter=',')
    sfdsavefile = open('%s%s%s%s_SFD.csv'%(PATH,runfile,FNM,num),'w')
    np.savetxt(sfdsavefile, save2,delimiter=',')  
##    CFA[0] = TFA-(areas[0]/area)
##    for i in range(1,len(sizes)):
##        CFA[i] = CFA[i-1] - (areas[i]/area)

    #plt.plot(bins, CFA, 'b-', alpha=.01)
    #plt.xscale('log')
    #plt.yscale('log')
    #return [bins,upCFA.tolist(),CFA.tolist(),downCFA.tolist()]
    return [bins, CFA.tolist(), CFAsigma.tolist()]

def plotCFArefs(xmax):
    ''' plots data from golombek 2008 for comparison, user controlled which one
'''
    query = 'Plot: 1= just reference \n 2= just TRA_000828_2495 \n 3=Sholes PSP_007718_2350 Hand Counts \n 5=all\n'
    option = int(raw_input(query))
    if option == 1 or option == 5:
        #dat = np.loadtxt('%sGolomRefCFACurves.csv'%(REFPATH),delimiter=',')
        xs = np.linspace(.1,xmax)
        y20 = GolomPSDCFA(xs,.2)
        y30 = GolomPSDCFA(xs,.3)
        y40 = GolomPSDCFA(xs,.4)
        y50 = GolomPSDCFA(xs,.5)
        x = np.tile(xs,4)
        y = np.concatenate((y20,y30,y40,y50))
        plt.plot(x,y,'m*',alpha=.2,label = '20,30,40,50% RA',zorder=1)
    if option == 2 or option == 5:
        print 'cannot do until data is provided'
        #dat = np.loadtxt('%sGolomCFADat_TRA_000828_2495.csv'%(REFPATH),delimiter=',')
        #plt.plot(dat[0],dat[1],'k*',alpha=.7)
    if option == 3 or option == 5:
        dat = np.loadtxt('%sPSP_007718_2350Ref.csv'%(REFPATH),delimiter=',')
        plt.plot(dat[0],dat[1],'b*',label='Manual Results')
    return
    
def PSD(k):
    ''' the particle size distribution for the martian surface, according to Charalambous 2014 (dissertation
'''
    #These values based on Charambolous
    t = 3
    p = .79
    return sp.special.binom(t+k-1,k)*(p**k)*(1-p)**t

def GolomPSDCFA(D,k):
    ''' The Model curves used in Golombek's 2012 work, similar to those used in Li 2018
    k is fractional area covered by rocks
    this produces a CFA
'''
    q = 1.79 + .152/k
    F = k*np.exp(-q*D)
    return F

def fittoRA(xdat,ydat,RNG = [1.5,2.25]):
    '''Function to fit CFA results to a rock abundance
    Takes in bins as xdat, CFA as ydat, lower and upper bounds as RNG (assumed 1.5-2.25 to match Golombek 2012
'''
    fit_xdat = []
    fit_ydat = []
    for i in range(len(xdat)):
        if xdat[i] <= RNG[1] and xdat[i] >= RNG[0]:
            fit_xdat+=[xdat[i]]
            fit_ydat+=[ydat[i]]
    popt,pcov = sp.optimize.curve_fit(GolomPSDCFA,fit_xdat,fit_ydat,p0=[.1])
    #calculate the R2 on the fit maybe??
    ybar = np.average(fit_ydat)
    SStot = np.sum((fit_ydat-ybar)**2)
    predicted = GolomPSDCFA(fit_xdat,popt)
    SSres = np.sum((fit_ydat-predicted)**2)
    R2 = 1-SSres/SStot
    return popt, R2

def checkbads(runfile,num):
    #this is for when you want to get all the shadows that went awry and plot them
    load = getshads(runfile,num)
    bads = []
    while True:
        try:
            dat = pickle.load(load)
        except EOFError:
            break
        if not dat.measured:
            bads+=[dat]
    patches = []
    for j in bads:
        j.shadowmeasure()
        patches+=j.patchplot()
    fig=plt.figure(1)
    ax = fig.add_subplot(111)
    #image = np.load('%s%s%s%s_rot_masked.npy'%(PATH, runfile,FNM, num))
    
    plt.imshow(image, cmap='binary_r')
    for j in patches:
        ax.add_patch(j)
    plt.show()
    return bads
    
def exportdata(runfile,num):
    #this takes a shadow file and converts it to a csv file with relevant data
    load = open('%s%s%s%s_shadows.shad'%(PATH,runfile,FNM,num),'rb')
    attributes = [['flag','bouldwid','bouldcent_y','bouldcent_x','alpha']]
    while True:
        try:
            dat = pickle.load(load)
        except EOFError:
            break
        attributes +=[[dat.flag, dat.bouldwid, dat.bouldcent,dat.fitbeta[3]]]
    datfile = open('%s%s%s%s_data.csv'%(PATH,runfile, FNM,num),'w')
    for item in attributes:
        datfile.write('%s\n'%item)
    datfile.close()
    #np.savetxt('%s%s%s_data.csv'%(PATH,FNM,num),attributes, delimiter="'")
    return attributes

def FindIdealParams(filename, oldvals = False):
    '''Code to identify ideal parameters for running images, will assume single set of values for entire image
    returns gam,bound
    '''
    root, ID, NOMAP, num = RunParams(filename)
    PATH = 'C://Users//dhood7//Desktop//MBARS//Images//%s//'%(filename)
    FNM = filename
    #first see if it has been run before and offer to use those:
    if os.path.isfile('%slastrun.txt'%(PATH)):
        #temporary while testing something else
        lastrun = open('%slastrun.txt'%(PATH))
        data = lastrun.readline()
        data = data.rstrip()
        oldgam,oldbound = data.split(',')
        oldgam = float(oldgam)
        oldbound = float(oldbound)
        if oldvals:
            print 'Using old values\n'
            return oldgam,oldbound
        prompt = 'Use old params, gam = %s, bound = %s y/n?\n'%(oldgam,oldbound)
        answer = raw_input(prompt)
        
        if answer == 'y':
            print 'Using old values\n'
            return oldgam,oldbound
        else:
            if answer !='n':
                print 'Lets assume you meant \'n\''
            print 'OK, lets make new values\n'
    while True:
        imnum = np.random.random_integers(0,num)
        image = imageio.imread('%s%s%s.PNG'%(PATH,FNM,imnum))
        print 'Is the following sub-image representative of the entire image?\n'
        plt.imshow(image, cmap='binary_r')
        plt.show()
        answer = raw_input('y/n\n')
        if answer == 'y':
            print 'image %s selected, lets get params'%(imnum)
            break
        else:
            print 'trying new image...\n'

        
    userinterp = True
    while userinterp:
        gam = .6 
        image = npma.masked_equal(image, 0)
        imagemod = np.zeros_like(image, dtype=np.uint16)
        top = 0.
        imagemod = image**float(gam)
        top = np.max(imagemod)
        scale = 255./top
        imagemod = imagemod*scale
        imagemod = imagemod.astype(int)
        bound = int(np.average(imagemod.compressed()))
        while True:
            imageseg = npma.copy(imagemod)
            imageseg = imageseg.astype(float)
            imageseg = imageseg.filled(-1)
            imageseg[imageseg>bound] = bound+1
            imageseg = npma.masked_equal(imageseg, -1)    
            imageseg = imageseg.astype(int)
            imageseg.fill_value = 0
            print ('Boundary at %s\n'%(bound))
            print ('(I)ncrease or (D)ecrease the boundary? or is it (C)orrect?\n')
            fig,ax = plt.subplots(1,2,sharex = True,sharey = True)
            ax[0].imshow(image,cmap = 'binary_r')
            ax[1].imshow(image,cmap = 'binary_r',alpha = .5, zorder = 1)
            ax[1].imshow(imageseg,vmin = bound,vmax = (bound+1), zorder = 0)
            plt.show()
            prompt = 'I,D,C?\n'
            answer = raw_input(prompt)
            if answer == 'C' or answer == 'c':
                save = open('%slastrun.txt'%(PATH),'w')
                save.write('%s,%s'%(gam,bound))
                return gam,bound
            prompt = 'Move by how much? (integer please)\n'
            size = raw_input(prompt)
            try:
                size = int(size)
            except(ValueError):
                print 'that was not an int'
                size = 5
            
            if answer == 'I' or answer == 'i':
                bound+=size
            else:
                bound-= size
            
                
            



    return gam,bound
    
    
def ExamineImage(runfile,num, showblanks):
    hasshads = True

    if hasshads:
        load = getshads(runfile,num)
        #nned two so you dont reuse same artist, silly but necessary
        patches1 = []
        patches2 = []
        while True:
            try:
                dat = pickle.load(load)
            except EOFError:
                break
            patches1 += dat.patchplot()
            patches2 +=dat.patchplot()
        #image = np.load('%s%s%s%s_rot_masked.npy'%(PATH,runfile,FNM,num))
        image = imageio.imread('%s%s%s.PNG'%(PATH,FNM,num))
        image = sktrans.rotate(image,ROTANG, resize=True, preserve_range=True)
        image = npma.masked_equal(image, 0)
        filtimage = np.load('%s%s%s%s_SEG.npy'%(PATH,runfile,FNM,num))
        fig,ax = plt.subplots(2,2,sharex = True, sharey = True)
        ax[0][0].imshow(image, cmap='binary_r', interpolation='none')
        ax[0][1].imshow(image,cmap='binary_r',interpolation='none')
        ax[1][0].imshow(filtimage,interpolation='none')
        ax[1][1].imshow(filtimage,interpolation='none')
        for j in patches1:
            ax[0][1].add_patch(j)
        for j in patches2:
            ax[1][1].add_patch(j)
        plt.show()
##        plt.figure(1)
##        plt.imshow(image)
##        plt.figure(2)
##        plt.imshow(sktrans.rotate(image, -ROTANG))
##        plt.show()
    elif showblanks:
        #image = np.load('%s%s%s%s_rot_masked.npy'%(PATH,runfile,FNM,num))
        image = imageio.imread('%s%s%s.PNG'%(PATH,FNM,num))
        image = sktrans.rotate(image,ROTANG, resize=True, preserve_range=True)
        image = npma.masked_equal(image, 0)
        filtimage = np.load('%s%s%s%s_SEG.npy'%(PATH,runfile,FNM,num))
        fig,ax = plt.subplots(2,2,sharex = True, sharey = True)
        ax[0][0].imshow(image, cmap='binary_r', interpolation='none')
        ax[0][1].imshow(image,cmap='binary_r',interpolation='none')
        ax[1][0].imshow(filtimage,interpolation='none')
        ax[1][1].imshow(filtimage,interpolation='none')
        plt.show()
    return
        
        
def FindBigs(runfile,num,diam = 3):
    '''code to find and identify large boulders thay may be causing issues in the CFA'''
    shads = []
    load = getshads(runfile,num)
    if load == None:
        return None
    while True:
        try:
            dat = pickle.load(load)
            shads+=[dat]
        except(EOFError):
            break
    bigs = []
    patches = []
    total = 0
    for i in shads:
        if i.bouldwid_m>diam:
            bigs+=[i]
            patches+= i.patchplot()
        if i.measured:
            total+=1
    if np.any(bigs) == False:
        return None
    tossout = float(len(bigs)/total)
    #image = np.load('%s%s%s%s_rot_masked.npy'%(PATH,runfile,FNM,num))
    #replacing this with the original image to save on drive space.
    image = imageio.imread('%s%s%s.PNG'%(PATH,FNM,num))
    image = sktrans.rotate(image,ROTANG, resize=True, preserve_range=True)
    image = npma.masked_equal(image, 0) 
    fig,ax = plt.subplots(1,2, sharex = True, sharey = True)
    ax[0].imshow(image,cmap='binary_r',interpolation='none')
    ax[1].imshow(image,cmap='binary_r',interpolation='none')
    for j in patches:
        ax[1].add_patch(j)
    return bigs
def FindExcluded(runfile,maxnum,maxdiam):
    '''finds how many boulders were ignored due to exclusion of large boulders'''
    total = long(0)
    used = long(0)
    for i in range(maxnum):
        shads = []
        load = getshads(runfile,i)
        if load == None:
            continue
        while True:
            try:
                dat = pickle.load(load)
                shads+=[dat]
            except(EOFError):
                break
        for j in shads:
            if j.measured:
                total+=1
                if j.bouldwid_m<maxdiam:
                    used+=1
    exclpercent = 100.*(float(total-used)/float(total))
    print ('%s boulders found in image, %s percent ignored due to diameter'%(total,exclpercent))
    return
    
def ManualMerge(runfile,num,flags):
    '''Code to manually merge two boulders, only to be used in exception circumstances
        runfile and num specify the image, boulders listed in flags will be merged into one with lowest flag value.
        '''
    shads = getshads(runfile,num,mode = 'r')
    boulds=[]
    mergeboulds = []
    while True:
        try:
            dat = pickle.load(shads)
        except(EOFError):
            break
        if dat.flag in flags:
            mergeboulds += [dat]
        else:
            boulds+=[dat]
    print len(mergeboulds)
    shads.close()
    shads = getshads(runfile,num,mode='w')
    for obj in boulds:
        pickle.dump(obj,shads)
    if len(mergeboulds) == len(flags):
        finalflag = mergeboulds[0].flag
        finalarea = mergeboulds[0].im_area
        finalpixels = []
        for i in mergeboulds:
            finalpixels+=i.pixels
        
        newbould=shadow(finalflag, finalpixels, finalarea)
        newbould.run_prep()                  
        newbould.run_fit()
        newbould.run_post()
        pickle.dump(newbould,shads)
        shads.close
        print 'succesfully merged input boulders with flags %s'%(flags)
        return

    else:
        print'Did not find %s boulders, aborting merge'%(len(flags))
        for obj in mergeboulds:
            pickle.dump(obj,shads)
        shads.close()
        return
        
    
    

def OutToGIS(runfile,maxnum,dlow = 1.0, dhigh = 2.25,extension='.PGw'):
    '''this code will take an entire run and export the boulder data to a GIS-interpretable format, assume pngs for the moment'''
    ''' A key part of this is interpreting the PGW files, which follow this convention:
        6 values on 6 lines:
        A
        D
        B
        E
        C
        F
        these are inputs to two equations for xmap and ymap, the coordinates of the pixel in the map, based on x and y, the pixel coordinates of the image:
        xmap = Ax + By +C
        ymap = Dx + Ey +F
    '''
    if not os.path.exists('%sGISFiles//%s'%(PATH,runfile)):
        os.makedirs('%sGISFiles//%s'%(PATH,runfile))
    datafile = open("%sGISFiles//%s%s_boulderdata.csv"%(PATH,runfile,FNM),'w')
    datafile2 = open("%sGISFiles//%s%s_DEFINITEboulderdata.csv"%(PATH,runfile,FNM),'w')
    #put in the headers, we will start small with the boulders:
    headers = 'image,flag,xloc,yloc,bouldwid_m,bouldheight_m,shadlen\n'
    datafile.write(headers)
    datafile2.write(headers)
    #bring in the original rotation information
    rotang_r = np.radians(ROTANG)
    for i in range(maxnum+1):
        #bring in the image each time, wouldnt have to do this if they were all identical
        #but that cant be gauranteed
        try:
            seg = np.load('%s%s%s%s_flagged.npy'%(PATH,runfile,FNM,i))
        except(IOError):
            continue
        shads = getshads(runfile,i)
        if not shads:
            continue
        lycent = len(seg)/2.
        lxcent = len(seg[0])/2.
        seg = None
        o_image = imageio.imread('%s%s%s.PNG'%(PATH,FNM,i))
        o_lycent = len(o_image)/2.
        o_lxcent = len(o_image[0])/2.
        o_image = None
        
        worldfile = open('%s%s%s%s'%(PATH,FNM,i,extension),'r')
        constants = []
        for line in worldfile:
            val = float(line.rstrip())
            constants+=[val]
        boulds = []
        marks = []
        while True:
            try:
                dat  = pickle.load(shads)
            except(EOFError):
                break
            if dat.measured:
                flag = dat.flag
                bouldwid_m = dat.bouldwid_m
                bouldheight_m = dat.bouldheight_m
                shadlen = dat.shadlen
                #weve got to do something a little tricky here, we need the pixel location of the boulders in the un-rotated images
                #first we make a pointmap with flags to keep track
                #boulds+=[dat]
               
                xpos = dat.bouldcent[1]
                ypos = dat.bouldcent[0]

                #change xpos and ypos to origin on the image center
                xpos_c = xpos-lxcent
                ypos_c = ypos-lycent

                #rotate them, must give the negative rotation
                xpos_rot_c = xpos_c*np.cos(rotang_r) - ypos_c*np.sin(rotang_r)
                ypos_rot_c = xpos_c*np.sin(rotang_r) + ypos_c*np.cos(rotang_r)

                #re-reference to the corner of the image
                xpos_rot = xpos_rot_c + o_lxcent
                ypos_rot = ypos_rot_c + o_lycent
                xmap = constants[0]*xpos_rot + constants[2]*ypos_rot + constants[4]
                ymap = constants[1]*xpos_rot + constants[3]*ypos_rot + constants[5]
                #write it all down
                info = '%s,%s,%s,%s,%s,%s,%s\n'%(i,flag,xmap,ymap,bouldwid_m,bouldheight_m,shadlen)
                datafile.write(info)
                if bouldwid_m < dhigh and bouldwid_m >dlow:
                    datafile2.write(info)
                
                
        shads.close()           
    datafile.close()
    return
            
        
        
            
    
def LROCAdapter():
    '''this code is  intended as a quick fix to looking at LROC images, longer term
better infrastructure should be put in place to make this smoother'''
    #the only real problem is reaching for the metadata, we have to shortcut this
    #these are called when MBARS initializes and with MBARS.start, so we can call this instead and it shoudl work
    
    INANGLE = None
    NAZ = None
    SAZ = None
    SUNANGLE = None
    RESOLUTION = None

    return


def plotborder(array):
    #this is to speed up plotting up borders
    #array is in form [[y,x],[y,x]....]
    ydat = []
    xdat = []
    l = len(array)
    array = np.copy(array)
    ydat = array[range(l),[0]*l]
    xdat = array[range(l),[1]*l]
    plt.plot(xdat, ydat, "o")
    return
#Range of Floats List, tool to make lists of floats not ints
def ROFL (start, stop, step):
    nums = []
    i = float(start)
    while i < stop:
        nums+=[i]
        i+=step
    return nums


def getangles(ID, path = REFPATH):
    '''
    input is the product ID of the HiRISE image, returns key observation values:
    Incedence angle (sun's angle below peak
    sun direction (emission angle of the sun, clockwise from right of image)
    Resolution(m/px)
    North Azimuth (clockwise north direction from right hand side of image
    Sun Azimuth (
    '''
    cumindex = open(path+'RDRCUMINDEX.TAB','r')
    for line in cumindex:
        try:
            dat = line
        except EOFError:
            print 'No such HiRISE image, check product ID or update CUMINDEX file'
            return None, None, None
        dat = dat.split(',')
        pid = dat[5]
        pid = pid.replace(" ","")
        pid = pid.replace('"','')
        if pid == ID:
            break
    """ key factors we are looking for in the TAB file are as follows:
        Attribute                INDEX
        Product ID:             5
        SubSpacecraft lat/long: 29/30
        SubSolar lat/long:      27/28
        Incedence Angle:        20
        North Azimuth:          25
        Sun Azimuth:            26
        Resolution:             40
        Projection_type:        41     
    """
    
    naz = float(dat[25])
    saz = float(dat[26])
    inangle = float(dat[20])
    glat = float(dat[29])
    glong = float(dat[30])
    slat = float(dat[27])
    slong = float(dat[28])
    sunangle = groundaz(glat,glong,slat,slong)

    if NOMAP:
        rotang = 90+saz
    else:
        projection = dat[41]
        projection = projection.replace("\"","")
        projection = projection.rstrip()
        if projection == 'EQUIRECTANGULAR':
            #print 'Map Projection is listed as %s, make sure to project to Equirectangualr projection in GIS before Paneling'%(dat[40])
            rotang = sunangle
        elif projection == 'POLAR STEREOGRAPHIC':
            rotang = -glong+sunangle
        else:
            print 'Projection listed as %s, I am error'%(projection)
            return (None)

    ''' Inangle is returned as measured from azimuth, sunangle as clockwise from North'''
    
    #HiRISE_INFO has the resolution, PID is on index 11, resolution on the last one
    info = open(path+'HiRISE_INFO.txt','r')
    for line in info:
        try: dat=line
        except EOFError:
            print 'No such HiRISE image, check product ID or update CUMINDEX file'
            return None, None, None
        dat = dat.split(',')
        if ID == dat[11]:
            break
    res = dat[-1].strip()
    res = float(res)
    
    
        
    return inangle, sunangle, res, naz, saz, rotang

def decon_PSF(image, iterations = 10, binned = False):
    '''my kernel for the HiRISE Point Spread Function, used to deconvolve the image
        from McEwen 2007, the FWHM of the PSF is 2 if the image is unbinned, or 1 if binned at 2x2
        as such, we will allow for both options
        '''
    #THIS DOES NOT WORK< NOT SURE WHY
    if binned:
        sigma = 1./(2*np.sqrt(2*np.log(2)))

    else:
        sigma = 2./(2*np.sqrt(2*np.log(2)))
    #PSF = np.zeros((11,11))
    k1d = np.linspace(0,10,11)
    k1d = gauss(k1d,sigma,5)
    k2d = np.outer(k1d,k1d)
    k2d = k2d/k2d.sum()
    
    image = image.astype(float)
    #trying out manual iterating since the internal iterations arent working
   
    #image_decon = skrestore.richardson_lucy(image, k2d,1,False)
    image_decon = skrestore.wiener(image, k2d, 1.0, None, True, False)
    
    return image_decon
        
def groundaz(glat, glon, slat, slon):
    """
    Translated directly from the ISIS GroundAzimuth C function
    inputs and outputs in degrees
    first pair is ground lat/lon, second is either subsun or subspacecraft
    Originally Authored by Caleb Fassett
    """

    if (glat >= 0):
        a=radians(90-slat)
        b=radians(90-glat)

    else:
        a=radians(90+slat)
        b=radians(90+glat)

    cslon=slon
    cglon=glon
    if cslon>cglon:
        if ((cslon-cglon)>180):
            while ((cslon-cglon)>180):
                cslon=cslon-360

    if cglon>cslon:
        if ((cglon-cslon)>180):
            while ((cglon-cslon)>180):
                cglon=cglon-360

    if (slat>=glat):
        if (slon>=glon):
            quad=1

        else:
            quad=2

    else:
        if (slon>=glon):
            quad=4

        else:
            quad=3

    dlon=radians(glon-slon)
    if dlon<0:  dlon=-dlon
    
    c=acos(cos(a)*cos(b)+sin(a)*sin(b)*cos(dlon))
    az=0

    if (((sin(b)==0)|(sin(c)==0))|((sin(b)*sin(c))==0)):
        
        return az

    else:

        try:
            bigA=degrees(acos((cos(a)-cos(b)*cos(c))/(sin(b)*sin(c))))
        except:
            return az

        ### This is a kludge -- domain errors (perhaps near 180 lon)

        if (glat>=0):
            if ((quad==1)|(quad==4)):
                az=bigA

            else:
                az=360-bigA

        else:
            if ((quad==1)|(quad==4)):
                az=180-bigA

            else:
                az=180+bigA

        return az

def RunParams(filename):
    '''a long term solution to running multiple images, this will
create text files in each image file so that various parameters dont need to be
reentered, files read:
root
ID
NOMAP
Panels
'''
    parampath = '%s%s//runparams.txt'%(BASEPATH,filename)
    if not os.path.isdir('%s%s'%(BASEPATH,filename)):
        print 'no such directory\n'
        return None,None,None,None
    if os.path.isfile(parampath):
        print 'Running Parameters found\n'
        #get these parameters
        paramfile = open(parampath,'rb')
        info = paramfile.readline()
        info = info.rstrip()
        root,mbarsid,mbarsnomap,panels = info.split(',')
##        root = paramfile.readline()
##        root = root.rstrip
        
##        mbarsid = paramfile.readline
##        mbarsid = mbarsid.rstrip()
        
##        mbarsnomap = paramfile.readline()
        if 'True' in mbarsnomap:
            mbarsnomap = True
        else:
            mbarsnomap = False

##        panels = paramfile.readline()
##        panels = panels.rstrip()
        panels = int(panels)

        
    else:
        print "no parameters found, making new file\n"
        
        params = open(parampath,'wb')
        q1 = 'enter MBARS ID\n'
        mbarsid = raw_input(q1)
        
        q2 = 'Is the image projected (i.e. north is up?) y/n \n'
        while True:
            answer = raw_input(q2)
            if answer == 'y':
                mbarsnomap = False
                
                break
            elif answer == 'n':
                mbarsnomap = True
                break
            else:
                print 'y/n \n'
        #retrieve number of panels
        files = os.listdir('%s%s'%(BASEPATH,filename))
        files = [s for s in files if '.PNG' in s]
        files = [s.replace(filename,'') for s in files]
        files = [filter(lambda s: s in '0123456789',j) for j in files]
        files = [int(s) for s in files]
        panels = np.max(files) +1
        print('%s panels found'%panels)

        root = filename

        #write it all in:
        params.write('%s,'%root)
        params.write('%s,'%mbarsid)
        params.write('%s,'%mbarsnomap)
        params.write('%s'%panels)
        params.close()

    return root, mbarsid, mbarsnomap, panels
        

########INITIALIZATION##########
INANGLE,SUNANGLE,RESOLUTION,NAZ, SAZ, ROTANG = start()


    
