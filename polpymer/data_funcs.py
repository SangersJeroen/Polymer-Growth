"""Polpymer Data Processing

This script contains all the functions used to analyse the physicial quantities
and observables of the simulated polymer.

These functions are written to be used on the results obtained by use of the
functions in core_funcs.py
"""


# Module imports
from xml.etree.ElementPath import prepare_parent
import numpy as np
from typing import Dict, NewType, Tuple


# Defining global variables
zin_in: bool = True
ANGLE_TO_ADD: list[Tuple[int,int]] = [
    (1,0),
    (0,1),
    (-1,0),
    (0,-1)
]


# Top-level functions and classes
class Monomer:
    def __init__(self, ang: int):
        self.angle = ang
        self.location: Tuple[int,int] = None
        self.end_location: Tuple[int,int] = None

    def __str__(self):
        string: str = "Monomer from {} to {}".format(self.location,
        self.end_location)
        return string

    def calculate_end(self):
        if self.location is None:
            raise ValueError("Location of end not possible when location is None")
        else:
            add = ANGLE_TO_ADD[self.angle]
            start_loc = self.location
            self.end_location = (start_loc[0]+add[0], start_loc[1]+add[1])

class Polymer:

    chain_length: int = 0
    chain_start: Tuple[int,int] = None
    chain_end: Tuple[int,int] = None

    monomers: dict[int, Monomer] = {}
    claimed_sites: list[Tuple[int,int]] = []


    def __init__(self,
        dims: Tuple[int, int],
        origin: Tuple[int,int],
        starting_monomer: Monomer):

        self.dimensions = dims
        self.origin = origin

        starting_monomer.location = origin
        starting_monomer.calculate_end()

        self.chain_start = origin
        self.chain_end = starting_monomer.end_location

        self.monomers['monomer_0'] = starting_monomer
        self.chain_length = 1

    def __iter__(self) -> Monomer:
        for monomer in self.monomers:
            yield monomer

    def __str__(self):
        string: str = "Polymer chain consisting of {} monomers".format(self.chain_length)
        return string

    def __getitem__(self, item):
        item_str: str = "monomer_{}".format(item+1)
        return self.monomers[item_str]

    def add_monomer(self, ang: int, loc: str = 'end'):
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
            self.claimed_sites.append(loc)
        else:
            raise Exception("Proposed monomer's end location already a node of polymer")


    def conflict(self, prop_monomer: Monomer) -> bool:
        start = prop_monomer.location
        end = prop_monomer.end_location
        cross: bool = bool(end in self.claimed_sites)
        attach_end: bool = not bool((start == self.chain_start) or (start == self.chain_end))
        close: bool = bool(end == self.chain_start)

        is_conflicting: bool = bool(cross or attach_end or close)
        return is_conflicting




# Checking if the file is ran by itself or imported:
if __name__ == "__main__":
    print("import module with 'from polpymer.data_funcs import *' \
    , instead of running directly")
