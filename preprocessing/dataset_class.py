import numpy as np
import os
import copy
import torch
from torch.utils.data.dataset import Dataset
import torchvision.transforms as transforms
from preprocessing.randaugment.cutout import cutout
import random
from PIL import Image

cat2int = {
  "mss": 0,
  "msimut": 1
}

transformations = {
  "translate": transforms.RandomAffine(5, translate = (0, 0.1)),
  "shear": transforms.RandomAffine(5, shear = 5),
  "pad": transforms.Compose((transforms.Pad(5, padding_mode = "reflect"), transforms.RandomCrop(224)))
  # "rotation": transforms.RandomRotation(30),
  # "random_crop": transforms.RandomCrop(224, padding = 4),
  # "horizontal_flip": transforms.RandomHorizontalFlip(p = 0.5),
  # "vertical_flip": transforms.RandomVerticalFlip(p = 0.5),
}


cutout_transform = cutout(mask_size = 16, p = 1., cutout_inside = True)
random_apply = transforms.RandomApply(list(transformations.values()))

class MSIDataset(Dataset):
  def __init__(self, dataset, data_dir, data_mode, augmentation = None):
    # Dataset will have form (ImageName, label)
    self.dataset = dataset
    self.augmentation = augmentation
    self.data_dir = data_dir
    self.data_mode = data_mode
    self.int_labels = None
    self.str_to_int()

    # Necessary transformation
    self.to_tensor = transforms.ToTensor()

    # Apply?
    if augmentation is not None:
      self.random_apply_augment = 0.5

  def __getitem__(self, index):
    folder_dir = self.dataset[index, 2]
    image = Image.open(folder_dir)
    image = image.convert('RGB')

    # Apply transformation
    if self.augmentation is not None:
      if self.random_apply_augment < random.random():
        image = random_apply(image)
      image = cutout_transform(image)

    image_to_tensor = self.to_tensor(np.array(image))

    int_label = np.array(self.int_labels[index])
    int_label = torch.from_numpy(int_label)
    int_label = int_label.type(torch.LongTensor)
    return image_to_tensor, int_label

  def __len__(self):
    return len(self.dataset)

  def get_patient_data(self, patient_id):
    return np.where(self.dataset[:, -1] == patient_id)

  def get_patient_status(self):
    return np.column_stack((self.int_labels, self.dataset[:, -1]))

  def get_patients(self):
    return np.unique(self.dataset[:, -1])

  def str_to_int(self):
    ## This will convert string labels to int number
    self.int_labels = np.vectorize(cat2int.get)(self.dataset[:, 1])

class AugmentDataSet(Dataset):
  def __init__(self, dataset, data_dir, squeeze_factor = None, augmentation = None):
    # Dataset will have form (ImageName, label)
    self.dataset = dataset
    self.data_dir = data_dir
    self.augmentation = augmentation
    self.to_tensor = transforms.ToTensor()

    if squeeze_factor is not None:
      self.squeeze_dataset(squeeze_factor)

  def __getitem__(self, index):
    folder_dir = self.dataset[index, 1]
    image = Image.open(folder_dir)
    image = image.convert('RGB')

    if self.augmentation is not None:
      for _ in range(self.augmentation):
        choice = np.random.randint(len(transformations.keys()))
        trans_name = list(transformations.keys())[choice]
        # print(choice, trans_name)
        image = transformations[trans_name](image)

    # Apply transformation
    image_to_tensor = self.to_tensor(np.array(image))

    # if len(self.dataset) == 2: return self.get_item_with_index(self.dataset[index])

    # images = torch.Tensor()
    # for row in self.dataset[index]:
    # 	image_tensor = self.get_item_with_index(row)
    # 	if len(images) == 0:
    # 		images = image_tensor[None, :, :, :]
    # 	else:
    # 		images = torch.cat((images, image_tensor[None, :, :, :]))

    return image_to_tensor

  def get_item_with_index(self, row):
    folder_dir = row[1]

    image = Image.open(folder_dir)
    image = image.convert('RGB')
    image_to_tensor = self.to_tensor(image)
    return image_to_tensor

  def __len__(self):
    return len(self.dataset)

  def squeeze_dataset(self, factor):
    self.original_dataset = copy.deepcopy(self.dataset)
    self.dataset = np.array_split(self.dataset, factor)


class SemiDataSet(Dataset):
  def __init__(self, *datasets):
    self.datasets = datasets

  def __getitem__(self, index):
    images = []
    for dataset in self.datasets:
      images.append(dataset[index])
    return images

  def __len__(self):
   return min(len(d) for d in self.datasets)

class DummyDataset(Dataset):
  def __init__(self, dataset):
    super().__init__()
    self.dataset = dataset
    self.to_tensor = transforms.ToTensor()

  def __getitem__(self, index):
   image_dir = self.dataset[index]

   image = Image.open(image_dir)
   image = image.convert("RGB")
   image_to_tensor = self.to_tensor(image)
   return image_to_tensor

  def __len__(self):
    return len(self.dataset)
