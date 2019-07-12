"""
Train our RNN on bottlecap or prediction files generated from our CNN.
"""
from keras.callbacks import TensorBoard, ModelCheckpoint, EarlyStopping, CSVLogger, ReduceLROnPlateau
from models import ResearchModels
from data import DataSet
import time
import os
import numpy
import pandas
import csv

def train(data_type, seq_length, model, saved_model=None,
          concat=False, class_limit=None, image_shape=None,
          load_to_memory=False):
    # Set variables.
    nb_epoch = 1000
    batch_size = 8
    seq_length= 125

    # Helper: Save the model.
    checkpointer = ModelCheckpoint(
        filepath=os.getcwd()+'\\data\\checkpoints\\' + model + '-' + data_type + \
            '.{epoch:03d}-{val_loss:.3f}.hdf5',
        verbose=2,
        save_best_only=True)
    lrScheduler = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=1, cooldown=1, verbose=2)

    # Helper: TensorBoard
    tb = TensorBoard(log_dir=os.getcwd()+'\\data\\logs')

    # Helper: Stop when we stop learning.
    early_stopper = EarlyStopping(patience=5)

    # Helper: Save results.
    timestamp = time.time()
    csv_logger = CSVLogger(os.getcwd()+'\\data\\logs\\' + model + '-' + 'training-' + \
        str(timestamp) + '.log')

    # Get the data and process it.
    if image_shape is None:
        data = DataSet(
            seq_length=seq_length,
            class_limit=class_limit
        )
    else:
        data = DataSet(
            seq_length=seq_length,
            class_limit=class_limit,
            image_shape=image_shape
        )

    # Get samples per epoch.
    # Multiply by 0.7 to attempt to guess how much of data.data is the train set.
    steps_per_epoch = (len(data.data))

    if load_to_memory:
        # Get data.
        X, y = data.get_all_sequences_in_memory(batch_size, 'train', data_type, concat)
        X_test, y_test = data.get_all_sequences_in_memory(batch_size, 'test', data_type, concat)
##        pathy = os.getcwd()+'/y.npy'
##        numpy.save(pathy,y)
##        pathyt = os.getcwd()+'/y_test.npy'
##        numpy.save(pathyt,y_test)

    else:
        # Get generators.
        generator = data.frame_generator(batch_size, 'train', data_type, concat)
        val_generator = data.frame_generator(batch_size, 'test', data_type, concat)

    # Get the model.
    rm = ResearchModels(len(data.classes), model, seq_length, saved_model)
    print("research model")
    print(rm.model.summary()) 
    # Fit!
    if load_to_memory:
        # Use standard fit.
        rm.model.fit(
            X,
            y,
            batch_size=batch_size,
            validation_data=(X_test, y_test),
            shuffle=True,
            verbose=2,
            callbacks=[checkpointer, tb, early_stopper, csv_logger, lrScheduler],
            epochs=nb_epoch)
        print("from load to memory")
    else:
        # Use fit generator.
        rm.model.fit_generator(
            generator=generator,
            steps_per_epoch=steps_per_epoch,
            epochs=nb_epoch,
            verbose=2,
            shuffle=True,
            callbacks=[checkpointer, tb, early_stopper, csv_logger, lrScheduler],
            validation_data=val_generator,
            validation_steps=10)
        print("from generator")

def main():
    """These are the main training settings. Set each before running
    this file."""
    model = 'lstm'  # see `models.py` for more
    saved_model = None # None or weights file
    class_limit = None  # int, can be 1-101 or None
    seq_length = 125
    load_to_memory = True  # pre-load the sequences into memory

    # Chose images or features and image shape based on network.
    if model == 'conv_3d' or model == 'crnn':
        data_type = 'images'
        image_shape = (80, 80, 3)
        load_to_memory = False
    else:
        data_type = 'features'
        image_shape = None

    # MLP requires flattened features.
    if model == 'mlp':
        concat = True
    else:
        concat = False

    train(data_type, seq_length, model, saved_model=saved_model,
          class_limit=class_limit, concat=concat, image_shape=image_shape,
          load_to_memory=load_to_memory)

if __name__ == '__main__':
    main()
