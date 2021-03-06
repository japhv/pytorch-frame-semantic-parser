"""
Frame semantic Parser using PyTorch

Authors: Japheth Adhavan
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
from utilities import get_free_gpu
import numpy as np
import models, visualize
import time
import os
import argparse
import pandas as pd
from torchtext.data import (
    Iterator,
    Field,
    BucketIterator,
    TabularDataset
)

from sklearn.metrics import precision_recall_fscore_support, accuracy_score

import logging
logging.basicConfig(level=logging.INFO)


# gpu_idx = get_free_gpu()
# device = torch.device("cuda:{}".format(gpu_idx))
#
# logging.info("Using device cuda:{}".format(gpu_idx))

device = torch.device("cuda:0")

frame_classes = ["PERSON", "LOC", "ORG", "WORK_OF_ART", "PRODUCT", "EVENT", "OTHER"]
no_of_classes = len(frame_classes)


def train_model(model, model_name, dataloaders, criterion, optimizer, scheduler, args, num_epochs=10):
    """

    :param model:
    :param criterion:
    :param optimizer:
    :param scheduler:
    :param num_epochs:
    :return:
    """
    since = time.time()

    best_model_wts = model.state_dict()
    best_acc = best_recall =  best_precision = best_f1 = 0.0
    dataset_sizes = {x: len(dataloaders[x].dataset) for x in ["train", "val"]}
    model_loss = {x: [0 for _ in range(num_epochs)] for x in ["train", "val"]}

    for epoch in range(num_epochs):
        logging.info('Epoch {}/{}'.format(epoch + 1, num_epochs))
        logging.info('-' * 10)

        for phase in ['train', 'val']:
            if phase == 'train':
                # scheduler.step()
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0

            y_true = np.empty(shape=(0, no_of_classes), dtype=int)
            y_pred = np.empty(shape=(0, no_of_classes), dtype=int)

            # iterate over data
            for batch_idx, (inputs, labels) in enumerate(dataloaders[phase]):

                targets = torch.stack(labels, dim=1)

                # zero the parameter gradients
                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == 'train'):
                    outputs, pred = model(inputs)

                    ones = torch.ones(outputs.shape).to(device)
                    zeros = torch.zeros(outputs.shape).to(device)


                    predicted = torch.where(pred > 0.4, ones, zeros)
                    loss = criterion(outputs, targets.float())

                    # backward + optimize only if in training phase
                    if phase == 'train':
                        loss.backward(retain_graph=True)
                        optimizer.step()

                y_true = np.append(y_true, targets.cpu().numpy(), axis=0)
                y_pred = np.append(y_pred, predicted.cpu().numpy(), axis=0)

                # aggregate statistics
                running_loss += loss.item() * inputs.size(0)

                if phase == 'train' and batch_idx % 50 == 0:
                    logging.info('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                        (epoch + 1),
                        (batch_idx + 1) * len(labels),
                        dataset_sizes[phase],
                        100. * (batch_idx + 1) / len(dataloaders[phase]),
                        loss.item()))

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = accuracy_score(y_true, y_pred)
            epoch_precision, epoch_recall, epoch_f1, _ = precision_recall_fscore_support(y_true, y_pred, average="micro")

            model_loss[phase][epoch] = epoch_loss

            logging.info('{} Loss: {:.4f} Acc: {:.4f} precision: {:.4f} recall: {:.4f}  f1-score: {:.4f}'.format(
                phase.capitalize(), epoch_loss, epoch_acc, epoch_precision, epoch_recall, epoch_f1))

            # deep copy the model
            if phase == 'val' and epoch_f1 > best_f1:
                best_acc = epoch_acc
                best_f1 = epoch_f1
                best_precision = epoch_precision
                best_recall = epoch_recall
                best_model_wts = model.state_dict()
                torch.save(best_model_wts, "./models/{}.pt".format(model_name))


    time_elapsed = time.time() - since
    logging.info('\nTraining completed in {:.0f}m {:.0f}s'.format(
        time_elapsed // 60, time_elapsed % 60))
    logging.info('Best overall val Acc: {:4f}'.format(best_acc))
    logging.info('Best overall val precision: {:4f}'.format(best_precision))
    logging.info('Best overall val recall: {:4f}'.format(best_recall))
    logging.info('Best overall val f1-score: {:4f}\n'.format(best_f1))

    # load best model weights
    model.load_state_dict(best_model_wts)
    return model, model_loss, best_precision, best_recall, best_f1


def test_model(model, test_loader):
    model.eval()

    y_true = np.empty(shape=(0, no_of_classes), dtype=int)
    y_pred = np.empty(shape=(0, no_of_classes), dtype=int)

    with torch.no_grad():
        for (inputs, labels) in test_loader:
            targets = torch.stack(labels, dim=1)
            outputs, pred = model(inputs)

            ones = torch.ones(outputs.shape).to(device)
            zeros = torch.zeros(outputs.shape).to(device)

            predicted = torch.where(pred > 0.4, ones, zeros)

            y_true = np.append(y_true, targets.cpu().numpy(), axis=0)
            y_pred = np.append(y_pred, predicted.cpu().numpy(), axis=0)

    test_acc = accuracy_score(y_true, y_pred)
    test_precision, test_recall, test_f1, _ = precision_recall_fscore_support(y_true, y_pred, average="micro")


    print('\nTest set: Accuracy: ({:.2f}%) precision: {:.2f} recall: {:.2f} f1-score: {:.2f} \n'.format(
        test_acc, test_precision, test_recall, test_f1))

    return y_true, y_pred


def main(args):
    np.warnings.filterwarnings('ignore')

    os.makedirs("./graphs", exist_ok=True)
    os.makedirs("./models", exist_ok=True)

    model_name = "BiLSTMNetwork" if not args.attention else "BiLSTM_AttentionNetwork"


    TEXT = Field(sequential=True, lower=True, init_token="<bos>", eos_token="<eos>")
    LABEL = Field(sequential=False, use_vocab=False, is_target=True)


    label_fields = [(frame, LABEL) for frame in frame_classes]
    fields = [('TEXT', TEXT)] + label_fields

    train, val, test = TabularDataset.splits(
        path='./data/', train='ontonotes_ner_train.csv', validation='ontonotes_ner_val.csv',
        test='ontonotes_ner_test.csv', format='csv', skip_header=True,
        fields=fields)

    TEXT.build_vocab(train, val, test, vectors="glove.6B.50d")

    model = models.BiLSTM(embedding_dim=50,
                          hidden_dim=args.hidden_size,
                          vocab=TEXT.vocab,
                          label_size=no_of_classes,
                          device=device,
                          dropout=args.dropout,
                          attention_layer=args.attention
                          )

    model.to(device)

    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr, betas=(0.01, 0.999), eps=1e-5)
    exp_lr_scheduler = lr_scheduler.StepLR(optimizer, step_size=args.step, gamma=args.gamma)

    if not args.test:

        train_iter, val_iter = BucketIterator.splits(
            (train, val),  # we pass in the datasets we want the iterator to draw data from
            batch_sizes=(args.batch_size, args.batch_size),
            device=device,  # if you want to use the GPU, specify the GPU number here
            sort_key=lambda x: len(x.TEXT),
            # the BucketIterator needs to be told what function it should use to group the data.
            sort_within_batch=False,
            repeat=False  # we pass repeat=False because we want to wrap this Iterator layer.
        )

        dataloaders = {
            "train": train_iter,
            "val": val_iter
        }

        logging.info('Training...')
        model, model_loss, precison, recall, f1_score = train_model(
                                        model,
                                        model_name,
                                        dataloaders,
                                        criterion,
                                        optimizer,
                                        exp_lr_scheduler,
                                        args,
                                        num_epochs=args.epochs
        )

        visualize.plot_loss(model_loss, model_name)

    else:

        logging.info('Testing...')

        test_iter = BucketIterator(
            test,
            batch_size=args.batch_size,
            sort_key=lambda x: len(x.TEXT),
            device=device,
            train=False,
            repeat=False
        )

        model.load_state_dict(torch.load("./models/{}.pt".format(model_name)))
        y_test, y_pred = test_model(model, test_iter)

    logging.info('Completed Successfully!')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Semantic Frame Identification')
    parser.add_argument('--batch_size', type=int, default=64, metavar='N',
                        help='input batch size for training (default: 32)')
    parser.add_argument('--test', action='store_true', default=False,
                        help='disables training, loads model')
    parser.add_argument('--epochs', type=int, default=15, metavar='N',
                        help='number of epochs to train (default: 15)')
    parser.add_argument('--lr', type=float, default=0.001, metavar='LR',
                        help='learning rate (default: 0.001)')
    parser.add_argument('--weight-decay', type=float, default=0.001, metavar='LR',
                        help='weight decay L2 Regularizer (default: 0.001)')
    parser.add_argument('--dropout', type=float, default=0, metavar='N',
                        help='factor to decrease learn-rate (default: 0)')
    parser.add_argument('--momentum', type=float, default=0.5, metavar='M',
                        help='SGD momentum (default: 0.5)')
    parser.add_argument('--step', type=int, default=3, metavar='N',
                        help='number of epochs to decrease learn-rate (default: 3)')
    parser.add_argument('--gamma', type=float, default=0.1, metavar='N',
                        help='factor to decrease learn-rate (default: 0.1)')
    parser.add_argument('--hidden-size', type=int, default=128, metavar='N',
                        help='hidden layer size (default: 128)')
    parser.add_argument('--num-layers', type=int, default=1, metavar='N',
                        help='number of layers (default: 1)')
    parser.add_argument('--attention', action='store_true', default=False,
                        help='Should add attention be added.')
    main(parser.parse_args())
