"""Library for 1D neural networks using Theano: supports convolutional and
fully connected layers"""

import copy
import cPickle
import gzip
import matplotlib.pyplot as plt
import numpy as np
import theano
import theano.tensor as T
import time
from layers1d import ConvPoolLayer, FullyConnectedLayer
from nnet_functions import abs_error_cost, tanh


# Configure floating point numbers for Theano
theano.config.floatX = "float32"
    

class NNet1D(object):
    """A neural network implemented for 1D neural networks in Theano"""
    def __init__(self, seed, datafile, batch_size, learning_rate, momentum,
                 cost_fn=tanh):
        """Initialize network: seed the random number generator, load the
        datasets, and store model parameters"""
        # Store random number generator, batch size, learning rate and momentum
        self.rng = np.random.RandomState(seed)
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.momentum = momentum
        
        # Store cost function
        self.cost_fn = cost_fn
        
        # Initialize layers in the neural network
        self.layers = []
        
        # Input and output matrices (2D)
        self.x = T.matrix('x')
        self.y = T.matrix('y')
        
        # Split into training, validation, and testing datasets
        datasets = NNet1D.load_data(datafile)
        self.train_set_x, self.train_set_y = datasets[0]
        self.valid_set_x, self.valid_set_y = datasets[1]
        self.test_set_x, self.test_set_y = datasets[2]
        
        # Determine input and output sizes
        self.n_in = self.train_set_x.get_value(borrow=True).shape[1]
        self.n_out = self.train_set_y.get_value(borrow=True).shape[1]
        
        # Determine number of batches for each dataset
        self.n_train_batches = self.train_set_x.get_value(borrow=True).shape[0]
        self.n_train_batches /= batch_size
        self.n_valid_batches = self.valid_set_x.get_value(borrow=True).shape[0]
        self.n_valid_batches /= batch_size
        self.n_test_batches = self.test_set_x.get_value(borrow=True).shape[0]
        self.n_test_batches /= batch_size

    def add_conv_pool_layer(self, filters, filter_length, poolsize,
                            activ_fn=tanh):
        """Add a convolutional layer to the network"""
        # If first layer, use x as input
        if len(self.layers) == 0:
            input = self.x
            input_number = 1
            input_length = self.n_in
        
        # If previous layer is convolutional, use its output as input
        elif isinstance(self.layers[-1], ConvPoolLayer):
            input = self.layers[-1].output
            input_number = self.layers[-1].output_shape[1]
            input_length = self.layers[-1].output_shape[3]
        
        # If previous layer is fully connected, use its output as input
        elif isinstance(self.layers[-1], FullyConnectedLayer):
            input = self.layers[-1].output
            input_number = 1
            input_length = self.layers[-1].output_shape
        
        # Otherwise raise error
        else:
            raise TypeError("Invalid previous layer")
            
        # Add the layer
        layer = ConvPoolLayer(self.rng, input, input_length, self.batch_size,
                              filters, filter_length, input_number, poolsize,
                              activ_fn)
        self.layers.append(layer)

    def add_fully_connected_layer(self, output_length=None, activ_fn=None):
        """Add a fully connected layer to the network"""
        # If output_length is None, use self.n_out
        if output_length is None:
            output_length = self.n_out
        
        # If first layer, use x as input
        if len(self.layers) == 0:
            input = self.x
            input_length = self.n_in
        
        # If previous layer is convolutional, use its flattened output as input
        elif isinstance(self.layers[-1], ConvPoolLayer):
            input = self.layers[-1].output.flatten(2)
            output_shape = self.layers[-1].output_shape
            input_length = self.layers[-1].filter_shape[1] * output_shape[3]
        
        # If previous layer is fully connected, use its output as input
        elif isinstance(self.layers[-1], FullyConnectedLayer):
            input = self.layers[-1].output
            input_length = self.layers[-1].output_shape
        
        # Otherwise raise error
        else:
            raise TypeError("Invalid previous layer")
            
        # Add the layer
        layer = FullyConnectedLayer(self.rng, input, input_length,
                                    output_length, self.batch_size,
                                    self.cost_fn, activ_fn)
        self.layers.append(layer)

    def build(self):
        """Build the neural network from the given layers"""
        # Last layer must be fully connected and produce correct output size
        assert isinstance(self.layers[-1], FullyConnectedLayer)
        assert self.layers[-1].output_shape == self.n_out
        
        # Cost function is last layer's output cost
        self.cost = self.layers[-1].cost(self.y)
        
        # Keep a count of the number of training steps, train/valid errors
        self.epochs = 0
        self.train_errors = []
        self.valid_errors = []
        
        # Index for batching
        i = T.lscalar()
        
        # Batching for training set
        batch_size = self.batch_size
        givens = {self.x: self.train_set_x[i*batch_size:(i+1)*batch_size],
                  self.y: self.train_set_y[i*batch_size:(i+1)*batch_size]}
        
        # Stochastic gradient descent algorithm for training function
        params = [param for layer in self.layers for param in layer.params]
        updates = self.gradient_updates_momentum(params)
        
        # Make Theano training function
        self.train_batch = theano.function([i], self.cost, updates=updates,
                                           givens=givens)
        
        # Make Theano training error function
        self.train_error_batch = theano.function([i], self.cost, givens=givens)
        
        # Batching for validation set
        givens = {self.x: self.valid_set_x[i*batch_size:(i+1)*batch_size],
                  self.y: self.valid_set_y[i*batch_size:(i+1)*batch_size]}
        
        # Make Theano validation error function
        self.valid_error_batch = theano.function([i], self.cost, givens=givens)
        
        # Batching for testing set
        givens = {self.x: self.test_set_x[i*batch_size:(i+1)*batch_size],
                  self.y: self.test_set_y[i*batch_size:(i+1)*batch_size]}
        
        # Make Theano testing error function
        self.test_error_batch = theano.function([i], self.cost, givens=givens)
        
        # Shared variables for output
        x = T.matrix()
        givens = {self.x: x}
        output = self.layers[-1].output
        
        # Make Theano output function
        self.output_function = theano.function([x], output, givens=givens)

    def gradient_updates_momentum(self, params):
        """Return the updates necessary to implement momentum"""
        updates = []
        for param in params:
            # Update parameter
            param_update = theano.shared(param.get_value()*0.,
                                         broadcastable=param.broadcastable)
            updates.append((param, param - self.learning_rate*param_update))
            
            # Store gradient with exponential decay
            grad = T.grad(self.cost, param)
            updates.append((param_update,
                            self.momentum*param_update +
                            (1 - self.momentum)*grad))
            
        # Return the updates
        return updates

    @staticmethod
    def load_data(filename):
        """Load the datasets from file with filename"""
        # Unpickle raw datasets from file as numpy arrays
        with gzip.open(filename, 'rb') as file:
            train_set, valid_set, test_set = cPickle.load(file)
    
        def shared_dataset(data_xy, borrow=True):
            """Load the dataset data_xy into shared variables"""
            # Split into input and output
            data_x, data_y = data_xy
            
            # Store as numpy arrays with Theano data types
            shared_x_array = np.asarray(data_x, dtype=theano.config.floatX)
            shared_y_array = np.asarray(data_y, dtype=theano.config.floatX)
            
            # Create Theano shared variables
            shared_x = theano.shared(shared_x_array, borrow=borrow)
            shared_y = theano.shared(shared_y_array, borrow=borrow)
            
            # Return shared variables
            return shared_x, shared_y
    
        # Return the resulting shared variables
        return [shared_dataset(train_set), shared_dataset(valid_set),
                shared_dataset(test_set)]

    @classmethod
    def load_model(cls, filename):
        """Load a model from a file and return the NNet1D object associated
        with it"""
        with gzip.open(filename, "rb") as file:
            return cPickle.load(file)

    def output(self, x):
        """Return output from an input to the network"""
        # Copy x to own its data
        x = np.copy(x)
        
        # Store x's initial size
        x_size = x.shape[0]
        
        # Resize x
        x.resize(self.batch_size, self.n_in)
        
        # Return the output in x's initial size
        return self.output_function(x)[:x_size]

    def plot_test_predictions(self, display_figs=True, save_figs=False,
                              output_folder="images", output_format="png"):
        """Plots the predictions for the first batch of the test set"""
        # Load test data and make prediction
        batch_size = self.batch_size
        x = self.test_set_x.get_value()
        y = self.test_set_y.get_value()
        prediction = self.output(x)

        # Plot each chunk with its prediction
        for i, chunk in enumerate(zip(x, y, prediction)):
            # Create a figure and add a subplot with labels
            fig = plt.figure(i)
            graph = fig.add_subplot(111)
            fig.suptitle("Chunk Data", fontsize=25)
            plt.xlabel("Month", fontsize=15)
            plt.ylabel("Production", fontsize=15)

            # Make and display error label
            mean_abs_error = abs_error_cost(chunk[1], chunk[2]).eval()
            std_abs_error = T.std(T.abs_(chunk[1] - chunk[2])).eval()
            error = (mean_abs_error, std_abs_error)
            plt.title("Mean Abs Error: %f, Std: %f" % error, fontsize=10)

            # Plot the predictions as a blue line with round markers
            prediction = np.append(chunk[0], chunk[2])
            graph.plot(prediction, "b-o", label="Prediction")

            # Plot the future as a green line with round markers
            future = np.append(chunk[0], chunk[1])
            graph.plot(future, "g-o", label="Future")

            # Plot the past as a red line with round markers
            past = chunk[0]
            graph.plot(past, "r-o", label="Past")

            # Add legend
            plt.legend(loc="upper left")

            # Save the graphs to a folder
            if save_figs:
                filename = "%s/%04d.%s" % (output_folder, i, output_format)
                fig.savefig(filename, format=output_format)

            # Display the graph
            if display_figs:
                plt.show()
            
            # Clear the graph
            plt.close(fig)

    def plot_train_valid_error(self, model_name=""):
        """Plot the training and validation error as a function of epochs.
        Return the graph used (to allow plotting multiple curves)"""
        # Create a figure and add a subplot with labels
        fig = plt.figure(1)
        graph = fig.add_subplot(111)
        fig.suptitle("Error vs. Training Steps", fontsize=25)
        plt.xlabel("Epoch", fontsize=15)
        plt.ylabel("Absolute Error", fontsize=15)
        
        # Plot the training error
        graph.plot(self.train_errors, label="Training Set " + model_name)
        
        # Plot the validation error
        graph.plot(self.valid_errors, label="Validation Set " + model_name)
        
        # Add legend and display plot
        plt.legend()
        plt.show()

    def print_output_graph(self, outfile, format="svg"):
        """Print computational graph for producing output to filename in
        specified format"""
        return theano.printing.pydotprint(self.output_function, format=format,
                                          outfile=outfile)

    def save_model(self, filename):
        """Save the model to a file"""
        with gzip.open(filename, "wb") as file:
            file.write(cPickle.dumps(self))   

    def test_error(self):
        """Return average test error from the network"""
        test_errors = [self.test_error_batch(i)
                       for i in range(self.n_test_batches)]
        return np.mean(test_errors)

    def train(self):
        """Apply one training step of the network and return average training
        and validation error"""
        self.epochs += 1
        train_errors = [self.train_batch(i)
                        for i in xrange(self.n_train_batches)]
        mean_valid_error = self.valid_error()
        self.train_errors.append(np.mean(train_errors))
        self.valid_errors.append(mean_valid_error)
        return np.mean(train_errors), mean_valid_error

    def train_early_stopping(self, patience=15, min_epochs=0,
                             max_epochs=50000, print_error=True):
        """Train the model with early stopping based on validation error.
        Return the time elapsed"""
        # Start timer
        start_time = time.time()
        
        # Early stopping bests
        best_model = None
        best_validation_error = np.inf
        best_epochs = 0

        # Train model
        while self.epochs < max_epochs:
            # Run training step on model
            training_error, validation_error = self.train()
            
            # Only check bests if past min_epochs
            if self.epochs > min_epochs:
                # If lower validation error, record new best
                if validation_error < best_validation_error:
                    best_model = copy.deepcopy(self)
                    best_validation_error = validation_error
                    best_epochs = self.epochs
                    
                # If patience exceeded, done training
                if best_epochs + patience < self.epochs:
                    break
            
            # Print epoch, training error and validation error
            if print_error:
                errors = (self.epochs, training_error, validation_error)
                print "(%s, %s, %s)" % errors
        
        # Replace old model with best model
        self.__dict__ = best_model.__dict__
        
        # Stop timer
        end_time = time.time()
        
        # Test neural network and stop timer
        if print_error:
            print "Testing error = %s\n" % self.test_error()
            print "Time elapsed: %f" % (end_time-start_time)
            
        # Return time elapsed
        return end_time-start_time

    def train_error(self):
        """Return average train error from the network"""
        train_errors = [self.train_error_batch(i)
                        for i in range(self.n_train_batches)]
        return np.mean(train_errors)
    
    def valid_error(self):
        """Return average train error from the network"""
        valid_errors = [self.valid_error_batch(i)
                        for i in range(self.n_valid_batches)]
        return np.mean(valid_errors)