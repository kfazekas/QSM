#!/usr/bin/env python3
# -*-coding:utf-8 -*-
'''
@File    :   sat_encodings.py
@Time    :   2023/05/12 21:42:39
@Author  :   Katalin Fazekas 
@Version :   0.0.1
@Status  :   Prototype
@Contact :   katalin.fazekas@tuwien.ac.at
@License :   MIT License, Copyright (C) 2022-2023, Katalin Fazekas, TU Wien, Austria
@Desc    :   None
'''

from collections import defaultdict

from typing import Dict,Tuple,List,Optional
from prime_implicants import PIClass, Cube
from symmetry import DomainSymmetryHandler

from pysat.formula import  CNF # type: ignore
from pysat.card import ITotalizer # type: ignore
from pysat.solvers import Solver, Glucose4 # type: ignore
from pysat.solvers import Cadical153 as Cadical # type: ignore

class DualEncoder():
    def __init__(self, atom_strs: List[str]) -> None:
        self.atoms = atom_strs
        self.nof_atoms = len(atom_strs)
        self.topv = 0
        self.verbosity = 1
        # the domain starts with 0, it is based on the bit position in the state,
        # the range of the varmap starts with 1, odd and even expresses polarity
        # atom 0 -> vars [1,2]
        # atom 1 -> vars [3,4]
        # ...
        # atom nof_atoms-1 -> vars [2*nof_atoms-1,2*nof_atoms]
        
        # variables of each atom of minterms representing the two possible polarities of it
        self.atom2vars: Dict[int,Dict[int,int]] = defaultdict(dict)
    
    def build_dualrail_clauses(self, cubes: List[str]) -> List[List[int]]:
        # Encode the negation of each cube with dual-rail encoding -> set of clauses
        clauses = []

        self.atom2vars = defaultdict(dict)
        for idx in range(self.nof_atoms):
            self.atom2vars[idx][1] = (idx)*2+1
            self.atom2vars[idx][0] = (idx)*2+2
            
            clauses.append([-1*self.atom2vars[idx][0],-1*self.atom2vars[idx][1]])
        self.topv = 2*(self.nof_atoms)
        for cube_str in cubes:
            cube_clause = []
            for atom,polarity in enumerate(cube_str):
                # We negate the values, so polarity is flipped
                if polarity == '0':
                    # Add positive literal
                    cube_clause.append(self.atom2vars[atom][1])
                elif  polarity == '1':
                    # Add the negative literal
                    cube_clause.append(self.atom2vars[atom][0])
                #case '-': dont care values can be ignored here

            clauses.append(cube_clause)
        return clauses

    def pp_dualrail_map(self):
        for idx,atom in enumerate(self.atoms):
            print('{}:  {}\n~{}: {}'.format(atom,self.atom2vars[idx][1],atom,self.atom2vars[idx][0]))

    def extract_prime_implicants(self, dsh: DomainSymmetryHandler, cube_strs: List[str]) -> List[PIClass]:
        pi_classes = []
        clause_db = CNF(from_clauses=self.build_dualrail_clauses(cube_strs))
        if self.verbosity > 0:
            print("Dual encoding:")
            print('\tNumber of variables: {}'.format(self.topv))
            print('\tNumber of clauses: {}'.format(len(clause_db.clauses)))
        
        n = len(self.atoms)
        all_literals = list(range(1,self.topv+1))
        t = ITotalizer(lits=all_literals, ubound=n, top_id=self.topv)
        clause_db.extend(t.cnf.clauses)

        pi_count = 0
        pi_class_count = 0

        with Cadical(bootstrap_with=clause_db) as sat_solver:
            # ub=0 will cover the case when the formula is empty.
            for ub in range(0,n+1):
                res = sat_solver.solve(assumptions=[-1*t.rhs[ub]])
                if self.verbosity > 3: print("(v{} + ... + v{}) <= {}: {}".format(all_literals[0],all_literals[-1],ub,res))
                while (res):
                    sol = sat_solver.get_model()
                    cube = ['-']*n
                
                    for idx,atom in enumerate(self.atoms):
                        if self.atom2vars[idx][1] in sol:
                            cube[idx] = '1'

                        elif self.atom2vars[idx][0] in sol:
                            cube[idx] = '0'
                    pi_class_count += 1
                    cube_class = dsh.get_symmetric_variants(cube)
                    
                    pi_class = None
                    for c in cube_class:
                        pi_count += 1
                        blocking_clause = []
                        for idx,_ in enumerate(self.atoms):
                            if c[idx] == '1':
                                blocking_clause.append(-1*self.atom2vars[idx][1])
                            elif c[idx] == '0':
                                blocking_clause.append(-1*self.atom2vars[idx][0])
                        pi_cube = Cube(c)
                        
                        if pi_class is None:
                            # pi_cube will be the representative of this PI-class
                            pi_class = PIClass(pi_cube)
                        else:
                            pi_class.add_equivalent_cube(pi_cube)

                        sat_solver.add_clause(blocking_clause)
                    
                    pi_classes.append(pi_class)

                    res = sat_solver.solve(assumptions=[-1*t.rhs[ub]])                                            
                
        if self.verbosity > 0:
            print('\tNumber of PIs: {}'.format(pi_count))
            print('\tNumber of PI-classes: {}'.format(pi_class_count))
        
        return pi_classes


class CoverTable():
    """ A class to encode and store the cover table of a set of PIs
        as a propositional formula in CNF.

        Builds a CNF from negation of each PI extended with
        an activation variable (the id of the PI). Every
        PI of the same class gets extended with the same
        activation variable (the id of the repr. PI).
    """
    def __init__(self, PIcs : PIClass, max_input_var: int) -> None:
        self.v = 0
        self.sat_solver = Glucose4(incr=True)
        self.all_PIs: Dict[int, PIClass] = {}
        self.max_input_var = max_input_var

        
        self.topv = 0
        for pic in PIcs:
            act_var = pic.id
            self.topv = act_var if act_var > self.topv else self.topv
            self.all_PIs[act_var] = pic
            for cube in pic.eq_class:

                self.sat_solver.add_clause([-1*act_var] + cube.care_neg[::])
                if self.v > 4: print([-1*act_var] + cube.care_neg[::])
        self.sat_calls = 0


    def print_CNF(self,path_to_CNF):
        formula = CNF()
        for pid,pic in self.all_PIs.items():
            for cube in pic.eq_class:
                formula.append([-1*pid] + cube.care_neg[::])
        formula.to_file(path_to_CNF)
                
    def propagate(self, selectors: List[int]):
        res, assigned = self.sat_solver.propagate(assumptions = selectors)
        return res,assigned

    def analyze_solutions (self):
        new_selector = max(self.all_PIs.keys()) + 1
        selectors = [pid for (pid,pic) in self.all_PIs.items()]
        selectors.append(new_selector)
        print(selectors)
        res = self.sat_solver.solve(assumptions = selectors)
        m_count = 0
        while(res):
            m = self.sat_solver.get_model()
            m_count += 1
            print("model {}: {}".format(m_count,[v for v in m if abs(v) < 7]))
            
            blocking_clause = [-1*v for v in m if abs(v) < 7]
            blocking_clause.append(-new_selector)
            self.sat_solver.add_clause(blocking_clause)
            res = self.sat_solver.solve(assumptions = selectors)
        print("number of solutions: ",m_count)

    def compare_solutions(self, selectors: List[int]) -> bool:
        # Compares the set of initial solutions to the set of solution of the subset
        # of clauses identified by the selectors.
        print("Comparing found solutions:")
        clean_sat_solver = Cadical()
        clean_full_sat_solver = Cadical()
        for pid,pic in self.all_PIs.items():
            for cube in pic.eq_class:
                if pid in selectors:
                    clean_sat_solver.add_clause(cube.care_neg[::])
                clean_full_sat_solver.add_clause(cube.care_neg[::])
        
        res = clean_full_sat_solver.solve()
        ref_count = 0
        n = len(PIClass._atoms)
        base_model_set = set()
        while(res):
            m = clean_full_sat_solver.get_model()
            
            ref_count += 1
            if self.v > 3: print("model {}: {}".format(ref_count,[v for v in m if abs(v) <= n]))
            base_model_set.add(tuple([v for v in m if abs(v) <= n]))
            blocking_clause = [-1*v for v in m if abs(v) <= n]
            clean_full_sat_solver.add_clause(blocking_clause)
            res = clean_full_sat_solver.solve(assumptions = selectors)
        if self.v > -1: print("Number of solutions all input clauses: ",ref_count)
        if self.v > -1: print("------------------------------------------------------")
        res = clean_sat_solver.solve()
        m_count = 0
        n = len(PIClass._atoms)
        while(res):
            m = clean_sat_solver.get_model()
            
            m_count += 1
            
            b = tuple([v for v in m if abs(v) <= n])
            if b not in base_model_set:
                if self.v > 3: print("** model {}: {}".format(m_count,b))
                print("** model {}: {}".format(m_count,b))
                print("Solution is not current, has model that was not a solution for the original problem.")
                break
            else:
                if self.v > 3: print("model {}: {}".format(m_count,b))
            blocking_clause = [-1*v for v in m if abs(v) <= n]
            clean_sat_solver.add_clause(blocking_clause)
            res = clean_sat_solver.solve(assumptions = selectors)
        print("Number of solutions of selected PIs: ",m_count)
        return (ref_count == m_count)

    def solve(self, assume: List[int]) -> bool:
        res = self.sat_solver.solve(assumptions = assume)
        self.sat_calls += 1

        return res

    def get_root_essentials(self) -> List[int]:
        essentials = []
        for pid,pic in self.all_PIs.items():
            u_part = [other_pid for other_pid in self.all_PIs.keys() if other_pid != pid]
            assume = pic.repr_pi.care + u_part
            res = self.solve(assume)
            if res:
                essentials.append(pid)
    
        return essentials

    def remove_covered_pis(self, ptrail, unk, trail):
        # Move PIs of unk to trail that are fully covered by ptrail.
        covered = []
        new_unk = []
        maxvar = self.max_input_var
        
        for pid in unk:
            assume = self.all_PIs[pid].repr_pi.care + ptrail
            res = self.solve(assume)
            
            if not res:
                trail.append(-1*pid)
                covered.append(pid)
            else:
                new_unk.append(pid)
                res, coverage = self.sat_solver.propagate(assume)
                
                relevant_coverage = [p for p in coverage if (-maxvar <= p and p <= maxvar)]
                self.all_PIs[pid].coverage = len(relevant_coverage)
                
        if covered:
            unk[:] = new_unk

        return covered

    def move_conditional_essentials(self, ptrail, unk, trail) -> List[int]:
        if len(ptrail) == len(trail):
            # We need some removed PIs to have a chance of new essentials to arise
            return []
        essentials = []
        new_unk = []
        # pySAT does not like duplicated assumption, ptrail gets some of the unk
        # pids during the loop, so we have to use the original (disjoint) ptrail
        # and unk in the assumption building.
        p_part = ptrail[:]

        for pid in unk:
            u_part = [other_pid for other_pid in unk if other_pid != pid]
            assume = self.all_PIs[pid].repr_pi.care + p_part + u_part
            res = self.solve(assume)
            if res:
                essentials.append(pid)
                trail.append(pid)
                ptrail.append(pid)
            else:
                new_unk.append(pid)
        
        if essentials:
            unk[:] = new_unk
    
        return essentials


