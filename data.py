"""
Class for managing our data.
"""
import csv
import numpy as np
import random
import glob
from os import path
import os
import pandas as pd
import sys
import operator
from processor import process_image
from keras.utils import np_utils

class DataSet():

    def __init__(self, seq_length=50, class_limit=None, image_shape=(224, 224, 3)):#class_limit=None
        """Constructor.
        seq_length = (int) the number of frames to consider
        class_limit = (int) number of classes to limit the data to.
            None = no limit.
        """
        self.seq_length = seq_length
        self.class_limit = class_limit
        self.sequence_path = os.getcwd() + '\\data\\sequences\\'
        self.max_frames = 60000  # max number of frames a video can have for us to use it
        
        # Get the data.
        self.data = self.get_data()

        # Get the classes.
        self.classes = self.get_classes()

        # Now do some minor data cleaning.
        self.data = self.clean_data()

        self.image_shape = image_shape

    @staticmethod
    def get_data():
        """Load our data from file."""
        with open(os.getcwd()+'\\data\\data_file.csv', 'r') as fin:
            reader = csv.reader(fin)
            data = list(reader)

        return data

    def clean_data(self):
        """Limit samples to greater than the sequence length and fewer
        than N frames. Also limit it to classes we want to use."""
        data_clean = []
        for item in self.data:
            if len(item) == 0:
                continue;
            
            if int(item[3]) >= self.seq_length and int(item[3]) <= self.max_frames \
                    and item[1] in self.classes:
                data_clean.append(item)

        return data_clean

    def get_classes(self):
        """Extract the classes from our data. If we want to limit them,
        only return the classes we need."""
        classes = []
    
        for item in self.data:
            if len(item) == 0:
                continue;
            
            if item[1] not in classes:
                classes.append(item[1])

        # Sort them.
        classes = sorted(classes)
        
        # Return.
        if self.class_limit is not None:
            return classes[:self.class_limit]
        else:
            return classes

    def get_target(self):
        target = []
    
        for item in self.data:
            if len(item) == 0:
                continue;
            target.append(item[4])
        #print(target)

        return target

    def split_train_test(self):
        """Split the data into train and test groups."""
        train = []
        test = []
        for item in self.data:
            if item[0] == 'train':
                train.append(item)
            else:
                test.append(item)
        return train, test

    def get_all_sequences_in_memory(self, batch_Size, train_test, data_type, concat=False):
        """
        This is a mirror of our generator, but attempts to load everything into
        memory so we can train way faster.
        """
        # Get the right dataset.
        train, test = self.split_train_test()
        data = train if train_test == 'train' else test

        print("Getting %s data with %d samples." % (train_test, len(data)))
        X, y = [], []
        for row in data:
            sequence = self.get_extracted_sequence(data_type, row)
            if sequence is None:
                print("Can't find sequence. Did you generate them?")
                raise

            if concat:
                # We want to pass the sequence back as a single array. This
                # is used to pass into a CNN or MLP, rather than an RNN.
                sequence = np.concatenate(sequence).ravel()

            X.append(sequence)
            #y.append(self.get_class_one_hot(row[1]))
            y.append(row[4])
        return np.array(X), np.array(y)

    def frame_generator(self, batch_size, train_test, data_type, concat=False):
        """Return a generator that we can use to train on. There are
        a couple different things we can return:

        data_type: 'features', 'images'
        """
        # Get the right dataset for the generator.
        train, test = self.split_train_test()
        data = train if train_test == 'train' else test
        sample_file = []
        print("Creating %s generator with %d samples." % (train_test, len(data)))
        
        while 1:
            for iii in range(len(data)):
                X, y = [], []

                # Generate batch_size samples.
                for _ in range(batch_size):
                    # Reset to be safe.
                    sequence = None

                    # Get a random sample.
                    sample = data[iii]
                    print(sample)
                    sample_file.append([sample])
##                    with open('sample_file.csv', 'w') as fout:
##                        writer = csv.writer(fout)
##                        writer.writerows(sample_file)
                    sample3 = pd.DataFrame(sample_file).to_csv('sample_file.csv')
                    

                    # Check to see if we've already saved this sequence.
                    if data_type is "images":
                        # Get and resample frames.
                        frames = self.get_frames_for_sample(sample)
                        frames = self.rescale_list(frames, self.seq_length)

                        # Build the image sequence
                        sequence = self.build_image_sequence(frames)
                    else:
                        # Get the sequence from disk.
                        sequence = self.get_extracted_sequence(data_type, sample)

                    if sequence is None:
                        print("Can't find sequence. Did you generate them?")
                        sys.exit()  # TODO this should raise

                    if concat:
                        # We want to pass the sequence back as a single array. This
                        # is used to pass into an MLP rather than an RNN.
                        sequence = np.concatenate(sequence).ravel()

                    X.append(sequence)
                    #y.append(self.get_class_one_hot(sample[1]))
                    y.append(sample[4])
                yield np.array(X), np.array(y)

    def build_image_sequence(self, frames):
        """Given a set of frames (filenames), build our sequence."""
        return [process_image(x, self.image_shape) for x in frames]

    def get_extracted_sequence(self, data_type, sample):
        """Get the saved extracted features."""
        filename = sample[2]
        path = self.sequence_path + filename + '-' + str(self.seq_length) + \
            '-' + data_type + '.txt'
        if os.path.isfile(path):
            # Use a dataframe/read_csv for speed increase over numpy.
            features = pd.read_csv(path, sep=" ", header=None)
            return features.values
        else:
            return None

    @staticmethod
    def get_frames_for_sample(sample):
        """Given a sample row from the data file, get all the corresponding frame
        filenames."""
        path = os.getcwd()+'\\data\\' + sample[0] + '\\' + sample[1] + '\\'
        filename = sample[2]
        images = sorted(glob.glob(path + filename + '*jpg'))
        return images

    @staticmethod
    def get_filename_from_image(filename):
        parts = filename.split('\\')
        return parts[-1].replace('.jpg', '')

    @staticmethod
    def rescale_list(input_list, size):
        """Given a list and a size, return a rescaled/samples list. For example,
        if we want a list of size 5 and we have a list of size 25, return a new
        list of size five which is every 5th element of the origina list."""
        assert len(input_list) >= size

        # Get the number to skip between iterations.
        skip = len(input_list) // size

        # Build our new output.
        output = [input_list[i] for i in range(0, len(input_list), skip)]

        # Cut off the last one if needed.
        return output[:size]

    @staticmethod
    def print_class_from_prediction(predictions, nb_to_return=10):
        """Given a prediction, print the top classes."""
        # Get the prediction for each label.
        label_predictions = {}
        for i, label in enumerate(data.classes):
            label_predictions[label] = predictions[i]

        # Now sort them.
        sorted_lps = sorted(
            label_predictions.items(),
            key=operator.itemgetter(1),
            reverse=True
        )

        # And return the top N.
        for i, class_prediction in enumerate(sorted_lps):
            if i > nb_to_return - 1 or class_prediction[1] == 0.0:
                break
            print("%s: %.2f" % (class_prediction[0], class_prediction[1]))