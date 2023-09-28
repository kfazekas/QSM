#!/usr/bin/env python3
# -*-coding:utf-8 -*-
'''
@File    :   symmetry.py
@Time    :   2023/05/12 21:42:29
@Author  :   Katalin Fazekas 
@Version :   0.0.1
@Status  :   Prototype
@Contact :   katalin.fazekas@tuwien.ac.at
@License :   MIT License, Copyright (C) 2022-2023, Katalin Fazekas, TU Wien, Austria
@Desc    :   None
'''

import sys
from math import comb
from itertools import count, permutations, product, combinations

from typing import Dict,Tuple,List,Optional

# from memory_profiler import profile

class DomainSymmetryHandler():
    """A class used to generate permutation table.

    Expects as input a list of all atoms, the signature of all relations
    and the domains together with their domain elements.
    Considering every combinations of every permutations of the domains,
    a set of reordering of the atoms is generated and stored in perm_table.
    This table then can be used to generate every symmetric variants
    of a certain state (cube).
    """

    quorum_sort_names = ['quorum','nset','nodeset']
    quorum_superset_sorts = ['node','acceptor']

    # @profile
    def __init__(self, domains, predicates, atoms, symmetric: bool = True) -> None:
        self.sort_names = list(domains.keys())
        self.domains = domains
        self.v = 0
        for k,v in self.domains.items():
            self.domains[k] = sorted(v)

        # by default only identity applies
        self.perm_table = []
        if self.v > 4: print('Atoms: {}\n Predicates: {}'.format(atoms,predicates))
                
        # 1. Check & Handle Quroum sub-sorts:
        self.has_quorum = False
        self.quorum_map: Dict[Tuple[str, ...],int] = {} # maps node-sets to quorum-name-id
        self.quorum_names: List[str] = []
        self.quorum_sort: Optional[str] = None
        self.superset_sort: Optional[str] = None
        
        self.super_set_elements: Optional[List[str]] = None

        self.setup_quorums()
        if self.v > 3: print('Quorum sort: ',self.quorum_sort)

        # When symmetry awareness is turned off, the only action
        # applied to any cube is the id permutation, i.e.
        # the perm-table has a single row with the original order.
        if not symmetric:
            self.perm_table = [list(range(len(atoms)))]
            self.print_stats(atoms)
            return        
        # Each permutation of the domain elements yields
        # a permutation of the bits of a state.
        all_perms = []
        super_set_id = -1
        for s_idx,(sort_name,domain) in enumerate(self.domains.items()):
            all_perms.append(permutations(list(range(len(domain)))))
            if self.has_quorum and sort_name == self.superset_sort:
                super_set_id = s_idx
                super_set_elements = list(sorted(domain))
            
        for pidx,perm in enumerate(product(*all_perms)):
            
            if self.has_quorum:
                if self.v > 4: print('{:<4} {}'.format(pidx,perm),end=' ')
                permuted_quorum = []
                for majority,q_idx in self.quorum_map.items():
                    permuted_majority = []
                    for m in majority:
                        ss_pos = self.get_ss_id(m)
                        perm_ss_pos = perm[super_set_id][ss_pos]
                        permuted_majority.append(super_set_elements[perm_ss_pos])
                    permuted_quorum.append(self.get_quorum_id(permuted_majority))
                if self.v > 4: print('{}'.format(tuple(permuted_quorum)))
                
            
            permuted_atom_positions = []
            for (pred,args) in atoms:
                permuted_args = []
                for arg_idx,(arg,arg_sort) in enumerate(zip(args,predicates[pred])):
                    permuted_arg = None
                    if arg_sort == self.quorum_sort:
                        permuted_arg = self.quorum_names[permuted_quorum[self.quorum_names.index(arg)]]
                    else:
                        sort_id = self.get_sort_id(arg_sort)
                        original_id = self.get_elem_id(arg_sort,arg)
                        permuted_id = perm[sort_id][original_id]
                        permuted_arg = self.get_elem(arg_sort,permuted_id)
                    permuted_args.append(permuted_arg)
                permuted_atom_id = atoms.index((pred,permuted_args))
                if self.v > 4: print(pred,args,'->',permuted_args,permuted_atom_id)
                permuted_atom_positions.append(permuted_atom_id)
            if self.v > 3: print(permuted_atom_positions)
            self.perm_table.append(permuted_atom_positions)

        self.print_stats(atoms)

    def get_sort_id(self, sort_name: str) -> int:
        return self.sort_names.index(sort_name)
    def get_elem_id(self, sort_name: str, elem: str) -> int:
        return self.domains[sort_name].index(elem)
    def get_elem(self, sort_name: str, id: int) -> str:
        return self.domains[sort_name][id]
    def get_ss_id(self, ss_elem: str) -> int:
        if self.super_set_elements:
            return self.super_set_elements.index(ss_elem)
        else:
            return -1
    def get_quorum_id(self, ss_list: List[str]) -> int:
        return self.quorum_map[tuple(sorted(ss_list))]
    def print_stats(self, atoms):
        if self.v > 3:
            print(' '.join(['{}({})'.format(pred,args) for (pred,args) in atoms]))
            for (pidx,permuted_ids) in enumerate(self.perm_table):
                print('{} {}'.format(pidx,permuted_ids))
        if self.v > 1:
            print('Length of permutation table: {}'.format(len(self.perm_table)))                
    def setup_quorums(self):
        for sort in DomainSymmetryHandler.quorum_superset_sorts:
            if sort in self.sort_names:
                self.superset_sort = sort
        if self.superset_sort is None:
            if self.v > 0:
                print('No superset candidate is found, quorum detection returns without search.')
            return 
        ss_name = self.superset_sort
        for name in DomainSymmetryHandler.quorum_sort_names:
            if name in self.sort_names:
                if self.has_quorum:
                    sys.exit('Error, maximum one quorum-sort is supported.')
                if not ss_name in self.sort_names:
                    sys.exit('Error, can not identify superset of quorum-sort {}'.format(name))
                self.quorum_sort = name
                self.has_quorum = True
                
                qsize = len(self.domains[name])
                self.super_set_elements = sorted(self.domains[ss_name])
                node_size = len(self.super_set_elements)
                nr_majorities = comb(node_size,int(node_size/2)+1)
                
                if qsize != nr_majorities:
                    sys.exit('Error, number of quorums is not correct (supposed to be {}, but has size {}).'.format(nr_majorities,qsize))

                for q_idx,node_majority in zip(range(qsize),combinations(sorted(self.domains[ss_name]),int(node_size/2)+1)):
                    self.quorum_map[node_majority] = q_idx
                    
                self.quorum_names = list(self.domains[name])
                if self.v > 3:
                    print(list(combinations(sorted(self.domains[ss_name]),int(node_size/2)+1)))
                    print(self.quorum_map.items())
                self.delete_domain(name)
    
    def delete_domain(self, domain_name: str):
        del self.domains[domain_name]
        self.sort_names = list(self.domains.keys())
    
    def get_symmetric_variants(self, cube: list):
        eq_set = set()
        cube_eq_class = []

        for perm in self.perm_table:
            new_cube = cube[::]
            for idx,val in enumerate(perm):
                new_cube[idx] = cube[val]
            if not str(new_cube) in eq_set:
                cube_eq_class.append(new_cube)
                eq_set.add(str(new_cube))

        return cube_eq_class

    """ A function to check if a given set of cubes is closed
        under domain symmetry.
    """
    def is_cube_set_symmetric(self, cube_strs) -> bool:
        
        cube_set = set()
        for cube_str in cube_strs:
            expands = [(c,) if c != '-' else ('0', '1') for c in cube_str]
            #print(cube_str,'->',expands,list(product(*expands)))
            
            for full_cube in product(*expands):
                cube_set.add(tuple(''.join(full_cube)))

        for cube_str in cube_strs:
            cube = list(cube_str)
            if '-' in cube:
                expands = [(c,) if c != '-' else ('0', '1') for c in cube_str]
                for full_cube in product(*expands):
                    eq_class = self.get_symmetric_variants(list(full_cube))
                    for other in eq_class:
                        if not tuple(other) in cube_set:
                            exit("Error, symmetric variant {} of {} is missing from the cube set.".format(''.join(other),cube_str))
            else:
                eq_class = self.get_symmetric_variants(cube)
                for other in eq_class:
                    if not tuple(other) in cube_set:
                        exit("Error, symmetric variant {} of {} is missing from the cube set.".format(''.join(other),cube_str))
        return True