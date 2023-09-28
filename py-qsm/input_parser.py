#!/usr/bin/env python3
# -*-coding:utf-8 -*-
'''
@File    :   input_parser.py
@Time    :   2023/05/12 21:43:17
@Author  :   Katalin Fazekas 
@Version :   0.0.1
@Status  :   Prototype
@Contact :   katalin.fazekas@tuwien.ac.at
@License :   MIT License, Copyright (C) 2022-2023, Katalin Fazekas, TU Wien, Austria
@Desc    :   None
'''

import sys
from collections import defaultdict
from lark import Lark
from lark.visitors import Interpreter

from typing import Dict,Tuple,List,Optional,Set

from symmetry import *
ivy_relevant_grammar = r"""
    
    %import common.LETTER
    %import common.DIGIT
    %import common.WS_INLINE

    start: (type_declr | relation_declr | function_declr | individual_declr | other)*

    type_declr: "type" typename
    
    relation_declr:  "relation" name args
    function_declr: "function" name args ":" typename
    individual_declr: "individual" name ":" typename
    
    args: ("(" (parameter)? ("," parameter)* ")")?
    parameter: name ":" typename
    ?name: IDENTIFIER
    ?typename: IDENTIFIER
    IDENTIFIER: CNAME
    CNAME: ("_"|LETTER) ("_"|LETTER|DIGIT)*
    other: EVERYTHING? _NL
    EVERYTHING.-1: /.+/
    CR : /\r/
    LF : /\n/
    _NL: (CR? LF)+
    COMMENT: /#[^\n]*/
    %ignore COMMENT
    %ignore WS_INLINE
"""

pla_grammar = r"""
    %import common.WS_INLINE
    %import common.INT
    %import common.LETTER
    %import common.DIGIT
    start: (num_i_vars | num_o_vars | i_var_names | o_var_names | cube | unrecognized)*
    num_i_vars: ".i" INT _NL
    num_o_vars: ".o" INT _NL
    i_var_names: ".ilb" relation+ _NL
    ?relation: CNAME args | "(" CNAME "=" CNAME ")" | "(" CNAME args "=" CNAME ")"
    ?args: ("(" (CNAME)? ("," CNAME)* ")")? | ("(" ("`"CNAME"`")? ("," "`" CNAME "`")* ")")?
    CNAME: ("_"|LETTER) ("_"|LETTER|DIGIT|":"|".")*
    o_var_names: ".ob" CNAME+ _NL
    cube: BINARY* BINARY _NL
    unrecognized: EVERYTHING? _NL
    EVERYTHING.-1: /.+/
    
    CR : /\r/
    LF : /\n/
    _NL: (CR? LF)+
    BINARY: "0" | "1" | "-"
    COMMENT: /#[^\n]*/ _NL
    %ignore COMMENT
    %ignore WS_INLINE
"""


protocol_parser = Lark(ivy_relevant_grammar,parser='lalr')
pla_parser = Lark(pla_grammar,parser='lalr')


class ProtocolPredicates():
    def __init__(self) -> None:
        self.sorts: List[str] = []
        self.sort_elements: Dict[str,Set[str]] = defaultdict(set)
        self.predicates: Dict[str,List[str]] = {} # For each predicate a list of sorts is assigned (types of arguments)
        self.atoms: List[Tuple[str,List[str]]] = []
        self.atom_strs: List[str] = []

    def add_predicate(self,name,arg_sorts):
        assert(not name in self.predicates)
        
        self.predicates[name] = [arg_sort.lower() for arg_sort in arg_sorts]
    
    def add_sort(self,sort_name):
        sort_name = sort_name.lower()
        assert(not sort_name in self.sorts)
        
        self.sorts.append(sort_name)

    def add_predicate_instance(self,pred_name,args):
        
        if not pred_name in self.predicates:
            sub_pred = False
            for pname,p in self.predicates.items():
                if pred_name.endswith("."+pname):
                    print(pred_name)
                    self.predicates[pred_name] = p.copy()
                    del self.predicates[pname]
                    # if self.verbosity > 0:
                    #     print("Predicate {} is mapped to {}.".format(pname,pred_name))
                    sub_pred = True
                    break
            if not sub_pred:
                sys.exit("Undefined predicate: \'{}\'".format(pred_name))
        if len(self.predicates[pred_name]) != len(args):
            print(pred_name, args)
            sys.exit("Predicate {} should have {} arguments, but {} found. ({})".format(pred_name,len(self.predicates[pred_name]),len(args),args))           
        for val,sort in zip(args,self.predicates[pred_name]):
            self.sort_elements[sort].add(val)

        self.atoms.append((pred_name,args))
        self.atom_strs.append('{}({})'.format(pred_name,','.join(args)))
        
        

class DeclarationCollector(Interpreter):   
    def __init__(self) -> None:
        super().__init__()
        self.pp = ProtocolPredicates()
        self.verbosity = 1

    def relation_declr(self, tree):   
        pred_name = str(tree.children[0])
        pred_args = []
        if len(tree.children) > 1:
            for arg in tree.children[1].children:
                pred_args.append(str(arg.children[1]))
        self.pp.add_predicate(pred_name,pred_args)
       
        if self.verbosity > 0:
            print('relation declaration: {}({})'.format(tree.children[0],', '.join(pred_args)))

    
    def function_declr(self, tree):
        return_type = str(tree.children[-1])
        pred_name = str(tree.children[0])
        pred_args = []
            
        if len(tree.children) > 2:
            for arg in tree.children[1].children:
                pred_args.append(str(arg.children[1]))
        if return_type != 'bool':
            pred_args.append(return_type)
            
            
        self.pp.add_predicate(pred_name,pred_args)
        
        if self.verbosity > 0:
            print('boolean function declaration:',tree.children[0])

    def individual_declr(self, tree): #"individual" name ":" typename
        return_type = str(tree.children[-1])
        
        pred_name = str(tree.children[0])
        pred_args = []
        # Individuals are treated as predicates
        # e.g. start_node : node is treated as start_node(n0) ... start_node(nN) predicates
        if return_type != 'bool':
            assert(len(tree.children)==2)
            pred_args.append(return_type)
        
        
        self.pp.add_predicate(pred_name,pred_args)
        if self.verbosity > 0:
            print('boolean individual declaration: {}({}) -> {}'.format(tree.children[0],', '.join(pred_args),tree.children[-1]))
        

    def type_declr(self, tree):
        if self.verbosity > 0: print('type declaration:',tree.children[0])
        
        self.pp.add_sort(tree.children[0])


class InputCubes():
    def __init__(self) -> None:
        self.with_members = False
        self.num_i_vars = -1
        self.num_o_vars = -1
        self.i_var_names = [] # type: ignore
        self.o_var_names = [] # type: ignore
        self.cubes: Dict[str,str] = {}
        self.reduced_cubes: Dict[str,str] = {}
    
    def flatten_args(self, children):
        args = []
        if hasattr(children,"children"):
            if children == 'args':
                return self.flatten_args(children.children)
            for idx,gchild in enumerate(children):
                args.extend(self.flatten_args(gchild))
        else:
            return [children]

    def validate_input(self, pp : ProtocolPredicates):
        member_pred_idxs = []
        if len(self.i_var_names) != self.num_i_vars:
            sys.exit('Error, number of input variables is {} but {} names were given.'.format(self.num_i_vars,len(self.i_var_names)))
            
        for idx,iname in enumerate(self.i_var_names):
            pred_name = iname.children[0]
            args = []
 
            if len(iname.children) > 1:
                if len(iname.children) == 2:
                    # Pred , args case
                    assert(len(iname.children[1:])==1)
                    if hasattr(iname.children[1],'children'):
                        for idx, children in enumerate(iname.children[1].children):
                            args.append(str(children))
                    else:
                        args.append(str(iname.children[1]))
                else:
                    for idx, children in enumerate(iname.children[1:]):
                        if hasattr(iname.children[idx],'children'):
                            args.append(str(children.children[1]))
                        else:
                            args.append(str(children))
                #print(pred_name,args)

            if pred_name.startswith("__"):
                pred_name = pred_name[2:]
            if ":" in pred_name:
                pred_name = pred_name.split(":")[0]
            if pred_name.startswith("member"):
                member_pred_idxs.append(idx)
                if (self.with_members):
                    pp.add_predicate_instance(pred_name,args)
            else:
                pp.add_predicate_instance(pred_name,args)
        if len(member_pred_idxs) == 0:
            self.with_members = True
        assert (len(member_pred_idxs) ==0 or max(member_pred_idxs)  - min(member_pred_idxs) + 1== len(member_pred_idxs))
        if self.num_o_vars != 1:
            sys.exit('Error, number of output variables is expected to be one.')
        if len(self.o_var_names) != 1:
            sys.exit('Error, no name for outut variable is found (line .ob name is missing).')
        
        for cube,res in self.cubes.items():
            if not self.with_members:
                reduced = cube[:min(member_pred_idxs)] + cube[max(member_pred_idxs)+1:]
                self.reduced_cubes[reduced] = res
                if len(reduced) != (self.num_i_vars-len(member_pred_idxs)):
                    sys.exit("Error, cube length is expected to be {}, but found to be {}.".format(self.num_i_vars,len(cube)))
            elif len(cube) != self.num_i_vars:
                sys.exit("Error, cube length is expected to be {}, but found to be {}.".format(self.num_i_vars,len(cube)))
            if res != '1':
                sys.exit("Error, cube should map to True (1), but found result is {}.".format(res))

class CubeCollector(Interpreter):
    def __init__(self) -> None:
        super().__init__()
        self.ic = InputCubes()
        self.verbose = 0

    def num_i_vars(self, tree):
        if self.verbose > 0: print('num-i-vars: ',tree.children[0])
        self.ic.num_i_vars = int(tree.children[0])
    
    def num_o_vars(self, tree):
        if self.verbose > 0: print('num-o-vars: ',tree.children[0])
        self.ic.num_o_vars = int(tree.children[0])
        
    def i_var_names(self, tree):
        if self.verbose > 0: print('input variables: ({})'.format(len(tree.children)),tree.children)
        
        for vname in tree.children:
            self.ic.i_var_names.append(vname)
    
    def o_var_names(self, tree):
        if self.verbose > 0: print('output variables: ({})'.format(len(tree.children)),tree.children)
        for vname in tree.children:
            self.ic.o_var_names.append(vname)

    def cube(self, tree):
        if self.verbose > 1: print('cube:',''.join(tree.children[:-1]),'->',tree.children[-1])
        cube_str = ''.join(tree.children[:-1])
        if cube_str in self.ic.cubes:
            print('Repeated occurrence of cube is ignored: {} -> {} (found with output {})'.format(cube_str,tree.children[-1],self.ic.cubes[cube_str]))
            return
        self.ic.cubes[cube_str] = str(tree.children[-1])
    
    def unrecognized(self,tree):
        #print("Unrecognized token in pla-file is ignored: ",tree.children)
        return
        

def parse_input_files(ivy_file, pla_file, silent=False) -> Tuple[ProtocolPredicates,List[str]]:
    dc = DeclarationCollector()
    if silent:
        dc.verbosity = 0
    ptree = None
    with open(ivy_file, 'r', newline='') as protocol_file:
        ptree = protocol_parser.parse(protocol_file.read())
    
    dc.visit(ptree)

    with open(pla_file, 'r', newline='') as cubes_file:
        ptree = pla_parser.parse(cubes_file.read())
    
    cc = CubeCollector()
    cc.visit(ptree)
    cc.ic.validate_input(dc.pp)

    if cc.ic.with_members:
        return dc.pp, list(cc.ic.cubes.keys())
    else:
        return dc.pp, list(cc.ic.reduced_cubes.keys())

    
if __name__ == '__main__':
    if len(sys.argv) > 2:        
        ivy_file = sys.argv[1]
        pla_file = sys.argv[2]
        
        parse_input_files(ivy_file,pla_file)
