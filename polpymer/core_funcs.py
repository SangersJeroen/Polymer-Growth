"""Polpymer Data Processing

This script contains all the functions used to analyse the physicial quantities
and observables of the simulated polymer.

These functions are written to be used on the results obtained by use of the
functions in core_funcs.py
"""


# Module imports
from typing import Tuple
from random import choice
import numpy as np
from copy import deepcopy


# Defining global variables
ANGLE_TO_ADD: list[Tuple[int,int]] = [
    (1,0),
    (0,1),
    (-1,0),
    (0,-1)
]


# Top-level functions and classes
class Monomer:
    """ Single Monomere element part of longe Polymer chain.
    single monomer groups together starting and ending point.
    """
    def __init__(self, ang: int):
        """Initialises Monomer class, takes single argument ang(le).

        Parameters
        ----------
        ang : int
            integer angle argument where 1 correpsonds to 90 degrees, options are
            0, 1, 2, 3 for x, y, -x, -y respectively
        """
        self.angle = ang
        self.location: Tuple[int,int] = None
        self.end_location: Tuple[int,int] = None

    def __str__(self):
        """ Prints description of monomer by specifying start and end points.

        Returns
        -------
        _type_
            _description_
        """
        string: str = "Monomer from {} to {}".format(self.location,
        self.end_location)
        return string

    def calculate_end(self):
        """ Calculates end coordinates of monomer link based on angle and
        starting position

        Raises
        ------
        ValueError
            If function is called without specifying the starting location first
        """
        if self.location is None:
            raise ValueError("Location of end not possible when location is None")
        else:
            add = ANGLE_TO_ADD[self.angle]
            start_loc = self.location
            self.end_location = (start_loc[0]+add[0], start_loc[1]+add[1])

class Polymer:
    """ Polymer object encapsulates dictionary of monomer objects

    Returns
    -------
    Polymer
        Object containing grouped information on the polymer chain

    Yields
    ------
    Iterable
        Allows for iterating over the monomers in the polymer

    Raises
    ------
    ValueError
        If invalid parameter is passed to the add_monomer function
    Exception
        If adding the monomer creates a self crossing
    """

    chain_length: int = 0
    chain_start: Tuple[int,int] = None
    chain_end: Tuple[int,int] = None

    monomers: dict[int, Monomer] = {}
    claimed_sites: list[Tuple[int,int]] = []

    nodes_locsx: np.ndarray = None
    nodes_locsy: np.ndarray = None
    node_m_vals: list[int,...] = []
    node_weights: list[int,...] = []

    end_to_end: np.ndarray = None
    gyration: np.ndarray = None

    pruned: bool = None

    def __init__(self,
        dims: Tuple[int, int],
        origin: Tuple[int,int],
        init_with_monomer: bool=True):
        """ Initialises the Polymer class with an initial Monomer

        Parameters
        ----------
        dims : Tuple[int, int]
            Amount of nodes in either x and y direction, unused for now
        origin : Tuple[int,int]
            Starting node of the first monomer
        starting_monomer : Monomer
            Monomer object that will start the chain
        """

        self.dimensions = dims
        self.origin = origin
        self.chain_start = origin

        if init_with_monomer:
            starting_monomer = Monomer(choice([0,1,2,3]))
        else:
            starting_monomer = Monomer(0)

        starting_monomer.location = origin
        starting_monomer.calculate_end()


        self.chain_end = starting_monomer.end_location
        self.monomers = {}
        self.monomers['monomer_0'] = starting_monomer
        self.chain_length = 1

        self.claimed_sites = [origin, self.chain_end]

        self.pruned = False

    def __iter__(self) -> Monomer:
        for i in range(len(self)):
            string: str = 'monomer_{}'.format(str(i))
            yield self.monomers[string]

    def __str__(self):
        string: str = "Polymer chain consisting of {} monomers".format(self.chain_length)
        return string

    def __getitem__(self, item):
        item_str: str = "monomer_{}".format(item+1)
        return self.monomers[item_str]

    def __len__(self):
        return self.chain_length

    def add_monomer(self, ang: int, loc: str = 'end'):
        """ Adds a monomer to the polymer chain

        Parameters
        ----------
        ang : int
            Angle of new monomer with respect to the global orientation
        loc : str, optional
            wether to add the monomer to the starting node or ending node.
            specify with either 'start' or 'end', by default 'end'

        Raises
        ------
        ValueError
            If string loc not 'start' or 'end'
        Exception
            If addition of monomer would create a self-crossing.
        """
        if loc == 'start':
            start_loc = self.chain_start
        elif loc == 'end':
            start_loc = self.chain_end
        else:
            raise ValueError("string location either 'start' or 'end',\
                 default is 'end'")

        proposed_monomer = Monomer(ang)
        proposed_monomer.location = start_loc
        proposed_monomer.calculate_end()

        if not self.conflict(proposed_monomer):
            self.chain_length += 1
            self.monomers['monomer_'+str(self.chain_length-1)] = proposed_monomer
            if start_loc == self.chain_start:
                self.chain_start = proposed_monomer.end_location
            elif start_loc == self.chain_end:
                self.chain_end = proposed_monomer.end_location
            self.claimed_sites.append(self.chain_end)
        else:
            raise Exception("Proposed monomer's end location already a node of polymer")


    def conflict(self, prop_monomer: Monomer) -> bool:
        """ Function returns True if the proposed monomer's addition to the chain would cause a conflict. conflict include: closing the loop, a self crossing, and not attaching to the start or end of the polymer chain

        Parameters
        ----------
        prop_monomer : Monomer
            monomer object with angle and starting position intialised

        Returns
        -------
        bool
            Result of whether addition of monomer would cause conflict
        """
        start = prop_monomer.location
        end = prop_monomer.end_location
        cross: bool = bool(end in self.claimed_sites)
        attach_end: bool = not bool((start == self.chain_start) or (start == self.chain_end))
        is_conflicting: bool = bool(cross or attach_end)
        return is_conflicting

    def observables(self):
        """ Function computes the observables of self

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            numpy array-like objects of polymers end-to-end distances and radii
            of gyration
        """
        if (self.nodes_locsx is None) or (self.nodes_locsy is None):
            self.compute_node_weights()

        L = self.chain_length
        x_ = self.nodes_locsx
        y_ = self.nodes_locsy

        end_to_end = np.array([])
        gyration = np.array([])

        for i in range(L):
            end_to_end_i = (x_[0] - x_[i+1])**2 + (y_[0] - y_[i+1])**2
            end_to_end = np.append(end_to_end, end_to_end_i)

            cm_x = 1/(i+1) * np.sum(x_[0:i+1])
            cm_y = 1/(i+1) * np.sum(y_[0:i+1])

            gyration_x_i = 1/(i+1) * np.sum((x_[0:i+1] - cm_x)**2)
            gyration_y_i = 1/(i+1) * np.sum((y_[0:i+1] - cm_y)**2)
            gyration_i = gyration_x_i + gyration_y_i
            gyration = np.append(gyration, gyration_i)


        return end_to_end, gyration


    def grow_polymer(self, length):
        """randomly grows a polymer up to a length of L or until it can't grow anymore and stores the number of growth option for each growth step to determine the weigth of the polymer

        """

        m = np.asarray([4], dtype=np.float64)
        grow_directions = [0,1,2,3]
        for i in range(length-1):
            grow_options = [0,1,2,3]
            for j in grow_directions:
                proposed_monomer = Monomer(j)
                proposed_monomer.location = self.chain_end
                proposed_monomer.calculate_end()
                if self.conflict(proposed_monomer):
                    grow_options.remove(j)
            if len(grow_options) > 0:
                    #m[i] = len(grow_options)
                    m = np.append(m, len(grow_options))
                    self.add_monomer(choice(grow_options))
            else:
                m = np.append(m,0)
                break
        #m = m[m!=0]
        self.node_m_vals = m

    def compute_node_weights(self):
        """ Computes the weights of each node in self
        """
        m = self.node_m_vals
        length = self.chain_length

        x_ = np.array([])
        y_ = np.array([])
        w_ = np.array([])

        polymer = self

        for monomer in polymer:
            start = monomer.location

            x_ = np.append(x_, start[0])
            y_ = np.append(y_, start[1])

        x_ = np.append(x_, polymer.chain_end[0])
        y_ = np.append(y_, polymer.chain_end[1])

        for i in range(length):
            w_ = np.append(w_, np.prod(m[0:i+1]))

        self.nodes_locsx = x_
        self.nodes_locsy = y_
        self.node_weights = w_


class Dish: #As in a Petri-dish
    """ Petri-dish like object, allows for the collection of Polymer objects within a single class. Allows for easy creation of Polymer ensembles.
    """

    polymers: list[object,...] = []
    end_to_end: np.ndarray = None
    gyration: np.ndarray = None
    weights: np.ndarray = None
    angles: np.ndarray = None
    bouqet: list[Polymer,...] = None
    correlation_matrix: np.ndarray = None
    corr_metric: float = None

    def __init__(self, dims: Tuple[int,int], origin: Tuple[int,int]):
        self.dimension = dims
        self.origin = origin
        self.polymers = []



    def find_N_polymer(self, N: int, length: int):
        """find a polymer that has the desired lenght L

        Parameters
        ----------
        dims : Tuple[int, int]
            Amount of nodes in either x and y direction, unused for now
        origin : Tuple[int,int]
            Starting node of the first monomer
        L : Tuple[int]
            Length of each polymer
        """

        dims = self.dimension
        origin = self.origin

        n = 0
        while n != N:
            trial_polymer = Polymer(dims, origin)
            trial_polymer.grow_polymer(length)
            self.polymers.append(trial_polymer)
            L = trial_polymer.chain_length
            if L == length:
                n += 1


    def find_polymer(self, length: int):
        """find a polymer that has the desired lenght L

        Parameters
            Starting node of the first monomer
        L : Tuple[int]
            Length of each polymer

        Return
        ------
        m : nd.array
            the weight of the polymer
        polymer: polymer of length L
        """

        dims = self.dimension
        origin = self.origin

        n = 0
        while n != length:
            trial_polymer = Polymer(dims, origin)
            trial_polymer.grow_polymer(length)
            n = trial_polymer.chain_length

        m = trial_polymer.node_m_vals
        return m, trial_polymer




    def analyse_polymers(self, length: int):
        """fuction to generate N polymers of length L

        Parameter
        ---------
        L : int
            maximum length of the polymers generated

        Return
        ------
        end_to_end : nd.array
            N x L matrix where the (i,j) element represents the end_to_end distance of polymer i with length j+1
        gyration : nd.array
            N x L matrix where the (i,j) element represents the radius of gyration of polymer i with length j+1
        w : nd.array
            N x L matrix where the (i,j) element represents the weight of polymer
        """
        N = len(self.polymers)
        end_to_end = np.zeros((N,length))
        gyration = np.zeros((N,length))
        w = np.zeros((N,length))

        for i in range(N):
            polymer = self.polymers[i]

            polymer.compute_node_weights()
            x_i = polymer.nodes_locsx
            y_i = polymer.nodes_locsy
            w_i = polymer.node_weights
            end_to_end_i, gyration_i = polymer.observables()

            end_to_end[i,:] = np.append(end_to_end_i,np.zeros(length-polymer.chain_length))
            gyration[i,:] = np.append(gyration_i,np.zeros(length-polymer.chain_length))
            w[i,:] = np.append(w_i,np.zeros(length-polymer.chain_length))

        self.end_to_end = end_to_end
        self.gyration = gyration
        self.weights = w

        return end_to_end, gyration, w

    def PERM(self, N: int, cplus: float, L: int):
        """Pruned-enriched Rosenbluth method (PERM)

        Parameter
        ---------
        N : int
            Number of polymers
        cplus : float
            Factor determining the low and high thresholds.
            cplus and cminus are set to cplus/cminus = 10, as found by Grassberger
        L : int
            Length of the polymers

        Return
        ------
        weights : nd.array
            Element (i,j) represents the weight of polymer i and node j
        end_to_end : nd.array
            Element (i,j) represents the end_to_end distance of polymer i between node (0) and node (j+1)
        gyration : nd.array
            Element (i,j) represents the radius of gyration of polymer j between node (0) and node (j+1)
        """
        cminus = cplus/10

        for i in range(N):
            m, polymer = self.find_polymer(1)
            self.polymers.append(polymer)

        grow_directions = [0,1,2,3]

        for i in range(L-1):

            w = []
            N_polymers = 0
            for polymer in self.polymers:
                m = np.asarray(polymer.node_m_vals, dtype=np.float64)
                grow_options = [0,1,2,3]
                if not polymer.pruned:
                    for j in grow_directions:
                        proposed_monomer = Monomer(j)
                        proposed_monomer.location = polymer.chain_end
                        proposed_monomer.calculate_end()
                        if polymer.conflict(proposed_monomer):
                            grow_options.remove(j)
                    if len(grow_options) > 0:
                        m = np.append(m,len(grow_options))
                        polymer.add_monomer(choice(grow_options))
                        N_polymers += 1
                    else:
                        polymer.pruned = True
                        m = np.append(m,0)

                else:
                    m = np.append(m,0)
                polymer.node_m_vals = m
                polymer.compute_node_weights()
                w.append(polymer.node_weights[-1])


            W_tilde = sum(w)/N_polymers
            W_plus = cplus*W_tilde
            W_minus = cminus*W_tilde

            copied_polymers = []

            for polymer in self.polymers:
                if not polymer.pruned:
                    if polymer.node_weights[-1] < W_minus:
                        if choice([0,1]) == 0:
                            polymer.node_m_vals[-1] = 0
                            polymer.pruned = True
                        else:
                            polymer.node_m_vals[-1] = 2*polymer.node_m_vals[-1]
                        polymer.compute_node_weights()
                    elif polymer.node_weights[-1] > W_plus:
                        polymer.node_m_vals[-1] = 0.5*polymer.node_m_vals[-1]
                        polymer.compute_node_weights()
                        copied_polymers.append(deepcopy(polymer))

            for polymer in copied_polymers:
                self.polymers.append(polymer)

        amnt = len(self.polymers)

        end_to_end = np.zeros((amnt,L))
        gyration = np.zeros((amnt,L))
        w = np.zeros((amnt,L))

        for i in range(amnt):
            polymer = self.polymers[i]
            w_i = polymer.node_weights
            end = len(w_i)
            w[i,0:end] = w_i
            end_to_end[i,0:end], gyration[i,0:end] = polymer.observables()

        self.weights = w
        self.end_to_end = end_to_end
        self.gyration = gyration


    def FRW(self, N:int, length: int):
        """generates a set of N free random walks of specified length


        """
        for i in range(N):
            m, polymer = self.find_polymer(1)
            self.polymers.append(polymer)

        grow_directions = [0,1,2,3]

        end_to_end = np.zeros((N,length))
        gyration = np.zeros((N,length))

        j = 0

        for polymer in self.polymers:
            for i in range(length-1):
                polymer.claimed_sites = []
                polymer.add_monomer(choice(grow_directions))


            x_ = np.array([])
            y_ = np.array([])


            for monomer in polymer:
                start = monomer.location

                x_ = np.append(x_, start[0])
                y_ = np.append(y_, start[1])

            x_ = np.append(x_, polymer.chain_end[0])
            y_ = np.append(y_, polymer.chain_end[1])

            polymer.nodes_locsx = x_
            polymer.nodes_locsy = y_

            end_to_end_i, gyration_i = polymer.observables()
            end_to_end[j,:] = end_to_end_i
            gyration[j,:] = gyration_i

            j += 1

        self.end_to_end = end_to_end
        self.gyration = gyration

    def polymer_correlation(self, bouqet: bool=False): #Function should probably be renamed
        """ Function allows for the bouqeting of the polymers and creates a matrix of inter-polymer correlations.

        Parameters
        ----------
        bouqet : bool, optional
            Toggle whether to create a polymer bouqet, by default False
        """

        polymer_amnt: int = len(self.polymers)

        polymer_lengths: list[int,...] = \
            [polymer.chain_length for polymer in self.polymers]
        max_chain_length: int = max(polymer_lengths)

        # We create an array that characterises all polymers by their angles
        angles: np.ndarray[int] = np.zeros((polymer_amnt, max_chain_length)) + 8

        i = 0
        for polymer in self.polymers:
            monomer_angles: list[int,...] = []
            for monomer in polymer:
                ang: int = monomer.angle
                monomer_angles.append(ang)

            length: int = len(monomer_angles)
            angles[i,0:length] = monomer_angles
            i += 1

        # Rotating polymers such that their first monomers overlap angle 0
        first_angle: np.ndarray = angles[:,0]
        mask = np.where(angles==8, True, False)
        angles: np.ndarray = angles - first_angle[:, np.newaxis]

        # Removing negative angles
        angles: np.ndarray = ((angles + 4) % 4).astype('int8')
        angles[mask] = 100


        # Creating a "bouqet" of polymers
        if bouqet == True:
            bouqet: list[Polymer,...] = []

            for i in range(polymer_amnt):
                new_polymer = Polymer(
                    self.dimension,
                    (0,0),
                    init_with_monomer=False
                )

                for angle in angles[i,1:]:
                    if angle != 100:
                        new_polymer.add_monomer(angle)
                    else:
                        pass
                bouqet.append(new_polymer)
            self.bouqet = bouqet

        self.angles = angles

        correlation = correlation_angles(angles)
        self.correlation_matrix = correlation

    def correlation(self):
        """ Function reduces the inter-polymer correlation matrix to a single correlation metric.
        """

        if self.correlation_matrix is None:
            self.polymer_correlation(bouqet=True)

        lengths = np.asarray(
            [polymer.chain_length for polymer in self.polymers]
        )
        corr_metric = correlation_metric(self.correlation_matrix, lengths)

        self.corr_metric = corr_metric


def correlation_angles(angles):
    """Function splits the angle array of an induvidual polymer in two signals,
    one for both x and y directions. These signals contain values of +1, 0, -1
    for both going in the positive direction, not moving in that direction or moving in the negative direction respectively.

    The correlation is then calculated for two polymer's x and y signals respectively by using the standard correlation defination:

    ..math::
        r_{x}^{i,j} = \sum_{k=1}^n (x_{i,k} - \bar{x_{i}})(x_{j,k}-\bar{x_{j}}) / \sqrt{ \sum_{k=1} (x_{i,k} - \bar{x_i})^2 \sum_{k=1} (x_{j,k} - \bar{y})^2}



    Parameters
    ----------
    angles : ndarray
        array of the angle string per polymer

    Returns
    -------
    ndarray
        ndarray of the correlation between polymer i and j.
    """

    (amnt, trash) = angles.shape

    correlation_matrix = np.zeros((amnt,amnt))

    for i in range(amnt):

        # Decoding the angles array for the ith polymer's angles
        trace_i = angles[i]
        x_i = np.where((trace_i == 0) | (trace_i == 2) | (trace_i == 100),
            trace_i, 100)
        y_i = np.where((trace_i == 1) | (trace_i == 3) | (trace_i == 100),
            trace_i, 100)

        x_i_ = np.where(x_i == 0, 1, 0)
        x_i = np.where(x_i == 2, -1, 0) + x_i_

        y_i_ = np.where(y_i == 1, 1, 0)
        y_i = np.where(y_i == 3, -1, 0) + y_i_

        xi_mean = np.average(x_i)
        yi_mean = np.average(y_i)

        for j in range(amnt):
            trace_j = angles[j]
            x_j = np.where((trace_j == 0) | (trace_j == 2) | (trace_j == 100),
                trace_i, 100)
            y_j = np.where((trace_j == 1) | (trace_j == 3) | (trace_j == 100),
                trace_j, 100)

            x_j_ = np.where(x_j == 0, 1, 0)
            x_j = np.where(x_j == 2, -1, 0) + x_j_

            y_j_ = np.where(y_j == 1, 1, 0)
            y_j = np.where(y_j == 3, -1, 0) + y_j_

            xj_mean = np.average(x_j)
            yj_mean = np.average(y_j)

            rx_ij = np.sum((x_i - xi_mean)*(x_j - xj_mean))/ \
                np.sqrt(np.sum((x_i - xi_mean)**2)*np.sum((x_j-xj_mean)**2))

            ry_ij = np.sum((y_i - yi_mean)*(y_j - yj_mean))/ \
                np.sqrt(np.sum((y_i - yi_mean)**2)*np.sum((y_j-yj_mean)**2))

            correlation_matrix[i,j] = np.sqrt(rx_ij**2 + ry_ij**2)

    return correlation_matrix


def correlation_metric(
    correlation_matrix: np.ndarray,
    polymer_lengths: np.ndarray)  -> float:
    """ Function that handles the call by Polymer.correlation(), creates a single metric from an array of inter-polymer correlations by taking the average of all lower triangular entries of the inter-polymer correlation matrix.

    Parameters
    ----------
    correlation_matrix : np.ndarray
        Matrix were the i,j'th entry is the correlation between polymer i and polymer j
    polymer_lengths : np.ndarray
        Lengths of the polymers, unused, unchecked

    Returns
    -------
    float
        A single floating point value resembling the correlation of the polymer ensemble.
    """

    shape = correlation_matrix.shape

    ones = np.ones(shape)
    metric = np.sum(np.tril(correlation_matrix))/np.sum(np.tril(ones))

    return metric






# Checking if the file is ran by itself or imported:
if __name__ == "__main__":
    print("import module with 'from polpymer.data_funcs import *' \
    , instead of running directly")


