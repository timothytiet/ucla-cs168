import torch
import torchvision
from torch.utils.data.dataset import Dataset
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
import os

class MSIDataset(Dataset):
    def __init__(self, dataset, data_dir):
        # Dataset will have form (ImageName, label)
        self.dataset = dataset
        self.data_dir = data_dir
        self.to_tensor = transforms.ToTensor()
        self.int_labels = None
        self.str_to_int()
    
    def __getitem__(self, index):
        image_name, folder_num, label = self.dataset[index]
        folder_dir = os.path.join(self.data_dir, label + "_split", label + str(folder_num), image_name)
        image = Image.open(folder_dir)
        image_to_tensor = self.to_tensor(image)
        int_label = self.int_labels[index]
        return image_to_tensor, int_label
    
    def __len__(self):
        return len(self.dataset)
    

    def str_to_int(self):
        ## This will convert string labels to int number
        self.int_labels = np.unique(self.dataset[:, 2], return_inverse = True)[1]
