"""Provides methods for obtaining, viewing, splitting oil production data"""

import csv
import cPickle
import gzip
import matplotlib.pyplot as plt
import numpy as np
import os
import random as rnd
import numpy


# Parameters for reader
DATA_DIRECTORY = "../data"

# Splitting data
IN_MONTHS = 48
OUT_MONTHS = 12
STEP_MONTHS = 6

# Preprocessing parameters
REMOVE_ZEROS = True
SMOOTH_DATA = False
NORMALIZE_DATA = False 
SMOOTH_LEN = 4

# Random seed
SEED = 42

# Dataset assignment
DIFFERENT_WELLS = True
DIFFERENT_SITES = False
TRAIN_SITES = ["BEAP", "BEAT", "BEZE", "EUZE", "EUAP"]
VALID_SITES = ["BEDE"]
TEST_SITES = ["EUAT"]
#implentation of step function (to determine if RBMs work with binary data)
#size determines number of rows
#interval determines size of each "step"
def stepfunc(size, interval):
            l =[]
            for i in range(0, size):
                if (i/interval)%2 ==0:
                    l.append(1)
                else:
                    l.append(0)
            return np.array(l)


def get_data():
    """Returns dictionary containing data from files in data directory"""
    # Oil production data is contained in this dictionary
    # Keys are the oil well names
    # Values are lists containing oil production measurements
    data = []
    """ 
    # Get start directory
    startdir = os.getcwd()
    
    # Get data from files in data directory
    os.chdir(DATA_DIRECTORY)
    for filename in os.listdir(os.getcwd()):
        with open(filename, "rb") as csvfile:
            # Open each data file with csv reader
            reader = csv.reader(csvfile, dialect="excel")

            # Ignore the first line because it contains headers
            reader.next()

            # Add each row to the corresponding oil well
            for row in reader:
                # Get data from cells and convert appropriately
                well_name = row[3]
                oil = float(row[4])

                # Add data to the dictionary
                if not well_name in data:
                    data[well_name] = []
                data[well_name].append(oil)

    # Go back to start directory
    os.chdir(startdir)
    """
    """
    column = 1000
    for row in xrange(1000):
        n = numpy.random.randint(2,12)
        stepRow = stepfunc(48, n)
        data.append(stepRow)
    """
    """
    column = 1000
    for row in xrange(1000):
        sample = 48
        data = np.append(data, row, 0)

        for i in xrange(sample)
            column = []
            y = np.sin(sample)
            row = np.append(column, y, 1)
    """
    #sample size determines size of test set
    sample = 48
    #implementation of sine function
       
    for i in xrange(1000):
        #randomly determines size of interval
        period = numpy.random.randint(2,12)
	x = np.linspace(0, period*np.pi, sample)
        #normalizes the output
	data.append((np.sin(x)+1)/2)
    return np.array(data)
    



    # Return data dictionary
    #return data




def preprocess_data(data):
    # Initialize dataset components
    train_x = []
    train_y = [] 
    valid_x = []
    valid_y = []
    test_x = []
    test_y = []
    """
    # Shuffle wells
    well_names = data.keys()
    rnd.shuffle(well_names)
    # Go through wells and assign to datasets
    for well_index, well_name in enumerate(well_names):
        # Remove zeroed data points (push points together)
        if REMOVE_ZEROS:
            oils = np.array(filter(lambda oil: oil != 0, data[well_name]))
        else:
            oils = np.array(data[well_name])
    """
    """        
    oils = np.array(data)
    # Smooth data
    if SMOOTH_DATA:
        smooth_window = np.ones(SMOOTH_LEN)/SMOOTH_LEN
        oils = np.convolve(smooth_window, oils, mode="valid")
    """
    # Make chunks
    """ 
    for i in xrange(0, len(oils)-(IN_MONTHS+OUT_MONTHS), STEP_MONTHS):
        # Split data into x, y, and chunk
        in_index = i
        out_index = i + IN_MONTHS
        end_index = i + IN_MONTHS + OUT_MONTHS
        chunk_x = oils[in_index:out_index]
        chunk_y = oils[out_index:end_index]
    """    
    """
    # Normalize chunk w/respect to x (skip if standard deviation is 0)
        if NORMALIZE_DATA:
            mean = max(chunk_x)
            std = np.std(chunk_x)
            chunk_x = (chunk_x)/mean
            chunk_y = (chunk_y)/mean
    
         
        # Add chunk
        if DIFFERENT_SITES:
            # Assign to dataset based on site name
            if well_name[:4] in TRAIN_SITES:
                train_x.append(chunk_x)
                train_y.append(chunk_y)
            elif well_name[:4] in VALID_SITES:
                valid_x.append(chunk_x)
                valid_y.append(chunk_y)
            elif well_name[:4] in TEST_SITES:
                test_x.append(chunk_x)
                test_y.append(chunk_y)
            else:
                print "Error: site %s not classified" % name
        elif DIFFERENT_WELLS:
            # Assign to dataset based on well index
            if well_index < len(data)*6/8:
                train_x.append(chunk_x)
                train_y.append(chunk_y)
            elif well_index < len(data)*7/8:
                valid_x.append(chunk_x)
                valid_y.append(chunk_y)
            else:
                test_x.append(chunk_x)
                test_y.append(chunk_y)
        else:
            print "Error: choose a dataset assignment option"
    """ 
    #used exclusively for sanity checks
    #set x and y are identical since set y is not used (instead last 12 values are substituted in rbm.py) 
    for i in xrange(len(data)):
        if i < len(data)*6/8:
            train_x.append(data[i])
            train_y.append(data[i])
        elif i < len(data)*7/8:
            valid_x.append(data[i])
            valid_y.append(data[i])
        else:
            test_x.append(data[i])
            test_y.append(data[i])
    else:
        print "Error: choose a dataset assignment option"
    

    # Make datasets
    train_set = (np.array(train_x), np.array(train_y))
    valid_set = (np.array(valid_x), np.array(valid_y))
    test_set = (np.array(test_x), np.array(test_y))

    print "Training Set Size: %d" % train_set[0].shape[0]
    print "Validation Set Size: %d" % valid_set[0].shape[0]
    print "Test Set Size: %d" % test_set[0].shape[0]

    return train_set, valid_set, test_set


def plot_chunks(datasets):
    
    for dataset in datasets:
        for chunk in zip(dataset[0], dataset[1]):
            # Create a figure and add a subplot with labels
            fig = plt.figure(1)
            graph = fig.add_subplot(111)
            fig.suptitle("Chunk Data", fontsize=25)
            plt.xlabel("Month", fontsize=15)
            plt.ylabel("Production", fontsize=15)
            
            # Plot the predictions as a green line with round markers
            prediction = np.append(chunk[0], chunk[1])
            graph.plot(prediction, "g-o", label="Prediction")
    
            # Plot the past as a red line with round markers
            past = chunk[0]
            graph.plot(past, "r-o", label="Past")
    
            # Add legend and display plot
            plt.legend(loc="upper left")
            plt.show()
            
            # Close the plot
            plt.close(fig)


if __name__ == '__main__':
    rnd.seed(SEED)
    print "Getting data..."
    data = get_data()
    print "Preprocessing data..."
    datasets = preprocess_data(data)
    print "Writing datasets to qri.pkl.gz..."
    with gzip.open("qri.pkl.gz", "wb") as file:
        file.write(cPickle.dumps(datasets))
    print "Done!"
    print "Plotting chunks..."
    plot_chunks(datasets)
