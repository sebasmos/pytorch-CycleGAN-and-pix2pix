import os.path
from data.base_dataset import BaseDataset, get_transform
from data.image_folder import make_dataset
from PIL import Image
import random
import numpy as np
import sys
import csv
from imgaug import imgaug as ia
from imgaug import augmenters as iaa
#!pip install natsort
from natsort import natsorted
from skimage.morphology import square
from skimage.filters import median
from skimage import img_as_ubyte
import random
import numpy as np
import torch.utils.data as data
from PIL import Image
import torchvision.transforms as transforms
from abc import ABC, abstractmethod
from skimage import io
import tifffile
import skimage 
import skimage.exposure
import torchvision
import torchvision.transforms as T
class unalignedDataset(BaseDataset):
    """
    This dataset class can load aligned/paired datasets where A.shape != B.shape.

    It requires two directories to host training images from domain A '/path/to/data/trainA'
    and from domain B '/path/to/data/trainB' respectively.
    You can train the model with the dataset flag '--dataroot /path/to/data'.
    Similarly, you need to prepare two directories:
    '/path/to/data/testA' and '/path/to/data/testB' during test time.
    """

    def __init__(self, opt):
        """Initialize this dataset class.

        Parameters:
            opt (Option class) -- stores all the experiment flags; needs to be a subclass of BaseOptions
        """
        BaseDataset.__init__(self, opt)
        self.dir_A = os.path.join(opt.dataroot, opt.phase + 'A')  # create a path '/path/to/data/trainA'
        self.dir_B = os.path.join(opt.dataroot, opt.phase + 'B')  # create a path '/path/to/data/trainB'

        self.A_paths = natsorted(make_dataset(self.dir_A, opt.max_dataset_size))   # load images from '/path/to/data/trainA'
        self.B_paths = natsorted(make_dataset(self.dir_B, opt.max_dataset_size))    # load images from '/path/to/data/trainB'
        self.A_size = len(self.A_paths)  # get the size of dataset A
        self.B_size = len(self.B_paths)  # get the size of dataset B
        btoA = self.opt.direction == 'BtoA'
        input_nc = self.opt.output_nc if btoA else self.opt.input_nc       # get the number of channels of input image
        output_nc = self.opt.input_nc if btoA else self.opt.output_nc      # get the number of channels of output image
        self.transform_A = get_transform(train= True, size=256, HE_IF = "he")
        self.transform_B = get_transform(train= True, size=256, HE_IF = "if")
        #self.transform_A = get_transform_N(self.opt, grayscale=(input_nc == 1), Data_type = "HE")
        #self.transform_B = get_transform_N(self.opt, grayscale=(input_nc == 1), Data_type = "IF")
        #self.transform_B = get_transform_N(train=True, size=256 , HE_IF = "IF")
        assert self.A_size == self.B_size, "Every instance of A must have a corresponding instance of B!"

    def __getitem__(self, index):
            """Return a data point and its metadata information.

            Parameters:
                index (int)      -- a random integer for data indexing

            Returns a dictionary that contains A, B, A_paths and B_paths
                A (tensor)       -- an image in the input domain
                B (tensor)       -- its corresponding image in the target domain
                A_paths (str)    -- image paths
                B_paths (str)    -- image paths
            """
            A_paths = self.A_paths[index % self.A_size]  # make sure index is within range
            B_paths = self.B_paths[index % self.B_size]  # make sure index is within range
            if self.opt.serial_batches:   # make sure index is within then range
                index_B = index % self.B_size
            else:   # randomize the index for domain B to avoid fixed pairs.
                index_B = random.randint(0, self.B_size - 1)
            B_path = self.B_paths[index_B]

            ############################################################
            img = tifffile.imread(A_paths)
            target = tifffile.imread(B_paths)
            target = skimage.util.img_as_float32(target)#**ADDED**
            # Normalize images
            CHANNELS = (0, 3,17)# - (0, 3,1,17,2,4)# 6 channels
            #CHANNELS = (0, 3,1,17,2) # 5 channels
            #CHANNELS = (0,3,1,4,2,9,8,6,10,11,15)
            img = np.moveaxis(img, 0, 2)
            target = np.dstack([
                skimage.exposure.rescale_intensity(
                    target[c],
                    in_range=(np.percentile(target[c], 1), np.percentile(target[c], 99.9)),#**ADDED**: reduce clipping to 1%
                    out_range=(0, 1)
                ) 
                for c in CHANNELS
            ]).astype(np.float32)#**ADDED**

            A = self.transform_A(img)
            B = self.transform_B(target)

            return {'A': A, 'B': B, 'A_paths': A_paths, 'B_paths': B_paths}

    def __len__(self):
        """Return the total number of images in the dataset.

        As we have two datasets with potentially different number of images,
        we take a maximum of
        """
        return max(self.A_size, self.B_size)
def get_transform(train, size=256, HE_IF = "he"):
    transforms = []
    transforms.append(T.ToTensor())
    if train:
        if HE_IF=="he":
            transforms.append(T.Resize((size,size)))
        elif HE_IF=="if":
            transforms.append(T.Resize((size,size)))
        else:
            transforms.append(T.Resize((size,size)))
    # Adding transformation to both inputs
    
    transforms.append(T.RandomHorizontalFlip(0.5))

    return T.Compose(transforms)