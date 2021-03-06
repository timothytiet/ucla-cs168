import pytorch_lightning as pl
import torch
import torch.nn.functional as F
import torch.nn as nn
import torchvision
import numpy as np
from evaluate.evaluator import Evaluator

class TrainerSkeleton(pl.LightningModule):
  def __init__(self,
        trainloader,
        valloader,
        valset,
        netname,
        threshold = 0.5
        ):
    super(TrainerSkeleton, self).__init__()
    self.trainloader = trainloader
    self.valloader = valloader
    self.valset = valset
    self.evaluator = Evaluator(self.valset, netname = netname)

    # Define loss
    '''
      This will eventually be same as nn.BCELoss with nn.Sigmoid.
      Here, I will use CrossEntropyLoss in case later on, the num_classes
      is expanded then I don't have to change the loss function
      TODO: Explore different cross-entropy
    '''
    self.criterion = nn.CrossEntropyLoss()

    # Logging config
    self.training_log = [] # train logs
    self.val_log = [] # val log

    # Hyperparameters
    self.threshold = threshold

  def forward(self):
    pass

  def configure_optimizers(self):
    pass

  def loss_func(self, logits, labels):
    return self.criterion(logits, labels)

  def total_epoch(self):
    return self.epoch_per_cycle * self.num_cycle

  def training_step(self, train_batch, batch_idx):
    images, labels = train_batch
    logits = self.forward(images)
    loss = self.loss_func(logits, labels)

    logs = {"learning_rate": self.optimizer.param_groups[0]["lr"], "train_loss": loss.item()}
    return {"loss": loss, "log": logs}

  def optimizer_step(self, current_epoch, batch_nb, optimizer, optimizer_i, second_order_closure=None):
    # update params
    self.optimizer.step()

    if current_epoch < self.get_num_cycle():
      self.scheduler.step()

    self.optimizer.zero_grad()

  def validation_step(self, batch, batch_idx):
    images, labels = batch
    logits = self.forward(images)
    val_loss = self.loss_func(logits, labels)

    # ! Get the prob at 1 because MSIMUT is the positive class
    # ! and we want to keep track it
    # Get the correct label
    prob = F.softmax(logits, dim = -1)
    _, y_pred_label = torch.max(prob, dim = -1)
    return {"y_pred": prob[:, 1].cpu().numpy(),
      "y_pred_label": y_pred_label.cpu().numpy(),
      "y_true": labels.cpu().numpy(),
      "val_loss": val_loss}

  def validation_epoch_end(self, outputs):
    # tn, fp, fn, tp
    # Evaluate metrics
    y_pred, y_true, y_pred_label = [], [], []
    for batch in outputs:
      y_pred = np.concatenate((y_pred, batch["y_pred"]))
      y_true = np.concatenate((y_true, batch["y_true"]))
      y_pred_label = np.concatenate((y_pred_label, batch["y_pred_label"]))

    tensorboard_logs = self.evaluator.eval_on_test_set(y_true, y_pred, y_pred_label)

    # Get the total loss of the validation
    total_loss = torch.stack([batch["val_loss"] for batch in outputs]).mean()
    tensorboard_logs["val_loss_epoch"] = total_loss

    logs = {"val_loss": total_loss, "log": tensorboard_logs}
    return logs

  def train_dataloader(self):
    return self.trainloader

  def val_dataloader(self):
    return self.valloader

  def get_channel(self):
    images, labels = next(iter(self.trainloader))
    _, channels, _, _ = images[0]
    return channels

  def get_max_epochs(self):
    return self.num_cycle * self.epoch_per_cycle + \
      self.cool_down if self.cool_down is not None else 0

  def get_num_cycle(self):
    return self.num_cycle * self.epoch_per_cycle