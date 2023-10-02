#!/usr/bin/env python3
# -*-coding:utf-8 -*-
'''
@File    :   prime_implicants.py
@Time    :   2023/05/12 21:42:49
@Author  :   Katalin Fazekas 
@Version :   0.0.1
@Status  :   Prototype
@Contact :   katalin.fazekas@tuwien.ac.at
@License :   MIT License, Copyright (C) 2022-2023, Katalin Fazekas, TU Wien, Austria
@Desc    :   None
'''

from typing import List, Tuple
from itertools import count


class Cube():
    _ids = count(-1)
    _atoms = None

    @classmethod
    def setup_universe(cls, first_cube_id: int, atoms: List[str]):
        Cube._ids = count(first_cube_id)  
        Cube._atoms = atoms[:]

    def __init__(self, lit_strs: List[str], with_id: bool =True) -> None:
        self.id = next(Cube._ids) if with_id else 0
        self.all_literals = lit_strs[:] #len(atoms)-long cube potentially with '-' values
        self.care = []
        self.care_neg = []

        for idx,lit in enumerate(lit_strs):
            v = idx+1
            if lit == '1':
                self.care.append(v)
                self.care_neg.append(-1*v)
        
            elif lit == '0':
                self.care.append(-1*v)
                self.care_neg.append(v)

        self.len = len(self.care)

    def __eq__(self, other: object) -> bool:
        # ignores cube id
        if not isinstance(other, Cube):
            return NotImplemented
        return self.all_literals == other.all_literals

    def __hash__(self):
        # ignores cube id
        return hash(str(self.all_literals))

    def __repr__(self):
        return '{}: {}'.format(self.id, ''.join(self.all_literals))
    
    def __str__(self):
        return '{}: {}'.format(self.id, ''.join(self.all_literals))

    def pp_care_atom(self, idx: int, literal: str) -> str:
        if literal == '-':
            return ""
        return Cube._atoms[idx] if literal == '1' else '~{}'.format(Cube._atoms[idx])

    def pp_neg_care_lit(self, idx: int, literal: str) -> str:
        if literal == '-':
            return ""
        return str(idx + 1) if literal == '0' else str(-1*(idx + 1))

    def pp_care_lit(self, idx: int, literal: str) -> str:
        if literal == '-':
            return ""
        return str(idx + 1) if literal == '1' else str(-1*(idx + 1))


    def pp_care(self) -> str:
        return '{}: {}'.format(self.id, ' & '.join(sorted([self.pp_care_atom(idx,lit) for (idx,lit) in enumerate(self.all_literals) if lit != '-'])))
    
    def pp_neg_care_clause(self) -> str:
        return '{}: {}'.format(self.id, ' \/ '.join(sorted([self.pp_neg_care_lit(idx,lit) for (idx,lit) in enumerate(self.all_literals) if lit != '-'])))
    
    def pp_prop_care_cube(self) -> str:
        return '{}: {}'.format(self.id, ' & '.join(sorted([self.pp_care_lit(idx,lit) for (idx,lit) in enumerate(self.all_literals) if lit != '-'])))

class PIClass():
    """A class to represent an equivalence class of prime implicants.

    When symmetry is not considered, the class has a single element.
    Otherwise, the class contains a set of equivalent (under symmetry)
    prime implicants, where one of them is a dedicated representative.
    """
    _atoms = None

    @classmethod
    def setup_universe(cls, atoms: List[Tuple[str,List[str]]]):
        PIClass._atoms = atoms[:]

    def __init__(self, repr_cube: Cube, id: int = 0) -> None:
        self.id = id if id != 0 else repr_cube.id
        self.eq_class: List[Cube] = [repr_cube]
        self.repr_pi = repr_cube
        self.is_singleton = True
        self.decided = False

        self.cost = 0
        self.has_const = 0
        self.has_all_const = False
        self.coverage = 0
        
        self.qcost = 0
        self.quantified_form = ""

        self.analyze_PI()
    
    def analyze_PI(self):
        self.cost = self.repr_pi.len

        self.has_all_const = True
        for lit,(pred,args) in zip(self.repr_pi.all_literals,PIClass._atoms):
            if lit != '-' and len(args) == 0:
                self.has_const = self.has_const + 1
            elif lit != '-' and len(args) != 0:
                self.has_all_const = False

    def add_equivalent_cube(self, cube: Cube) -> None:
        self.eq_class.append(cube)
        self.is_singleton = False

    @property
    def size(self) -> int:
        return len(self.eq_class)
    
    def has_cube(self, lit_strs: List[str]) -> bool:
        for cube in self.eq_class:
            differ = False
            for l1,l2 in zip(lit_strs,cube.all_literals):
                if l1 != l2:
                    differ = True
                    break
            if not differ:
                return True
        return False

    
    def __repr__(self) -> str:
        return '{} : [\n\t{}\n] size {} cost: {} has_const: {} has_all_const: {} singleton: {}\nQuantified form: {} Q-cost: {}'\
            .format(self.repr_pi,'\n\t'.join([sc.pp_care() for sc in self.eq_class]),\
                self.size, self.cost, self.has_const, self.has_all_const, self.is_singleton, self.quantified_form,self.qcost)


    
        


