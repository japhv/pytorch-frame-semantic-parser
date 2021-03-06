import os
import matplotlib as mpl
if os.environ.get('DISPLAY', '') == '':
    print('no display found. Using non-interactive Agg backend')
mpl.use('Agg')
mpl.rcParams['agg.path.chunksize'] = 10000

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np


def plot_loss(model_loss, model_name):
    fig, ax = plt.subplots()

    train_loss = model_loss["train"]
    valid_loss = model_loss["val"]

    epochs = len(train_loss)

    x = np.linspace(1, epochs, epochs)

    ax.set_title("Average Model Loss over Epochs")
    ax.set_xlabel("Epochs")
    ax.set_ylabel("Average Loss")

    # Adjust x-axis ticks
    tick_spacing = 5
    ax.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))

    ax.plot(x, train_loss, color='purple', label="train", marker=".")
    ax.plot(x, valid_loss, color='red', label="validation", marker="x")

    fig.savefig("./graphs/{}_epoch_loss".format(model_name))


def plot_histograms(class_names, spreads, type='Simple'):
    no_of_classes = len(class_names)
    class_accuracies = [spreads[i][i] / sum(spreads[i]) for i in range(no_of_classes)]

    x = np.arange(no_of_classes)

    # Histogram plot of all 10 classes
    hfig, az = plt.subplots()
    plt.title('Relative accuracy of all classes')
    plt.bar(x, height=class_accuracies)
    plt.xticks(x, class_names)
    plt.xlabel('Class')
    plt.ylabel('Accuracy')
    hfig.savefig('./graphs/NSynth_accuracy_hist_' + type + '.png', bbox_inches='tight')

    # Plots of each class predictions
    for i in range(no_of_classes):
        hfig, az = plt.subplots()
        plt.title('Prediction spread of class: ' + class_names[i])
        plt.bar(x, height=spreads[i])
        plt.xticks(x, class_names)
        plt.xlabel('Classes')
        plt.ylabel('# Predicted')
        hfig.savefig('./graphs/NSynth_class_' + class_names[i] + '_accuracy_hist_' + type + '.png',
                     bbox_inches='tight')
