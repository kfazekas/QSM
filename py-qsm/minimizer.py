#!/usr/bin/env python3
# -*-coding:utf-8 -*-
'''
@File    :   minimizer.py
@Time    :   2023/05/12 21:43:00
@Author  :   Katalin Fazekas 
@Version :   0.0.1
@Status  :   Prototype
@Contact :   katalin.fazekas@tuwien.ac.at
@License :   MIT License, Copyright (C) 2022-2023, Katalin Fazekas, TU Wien, Austria
'''


import sys
from os import path
from input_parser import parse_input_files
from sat_encodings import *
from prime_implicants import *
from operator import attrgetter,itemgetter

class Minimizer():
    def __init__(self, pic_list: List[PIClass]) -> None:
        self.v = 0
        self.all_PIs: Dict[int, PIClass] = {}
        self.all_solutions = False
        self.check_solution = False

        self.prefer_consts = True

        self.best_solutions = []
        self.current_cost = 0
        self.max_cost = 0
        self.UB = None

        self.pic_list = pic_list
        
    def init_solve(self):
        self.ct = CoverTable(self.pic_list, len(PIClass._atoms))
        if self.v > -1:
            print("PI details:")
            for pic in self.pic_list:
                print(pic)

        self.all_PIs = self.ct.all_PIs.copy() # shallow

        self.ptrail = self.ct.get_root_essentials()
        self.trail = self.ptrail[:]
        self.unk = []
        
        for pid,pic in self.all_PIs.items():
            if pic.qcost > 0:
                pic.cost = pic.qcost
            self.max_cost += pic.cost
            if not pid in self.ptrail:
                self.unk.append(pid)
            else:
                self.current_cost += pic.cost

        self.UB = self.max_cost + 1

        print("Root essential: {}".format(self.ptrail))

        if not self.unk:
            return

        covered = self.ct.remove_covered_pis(self.ptrail, self.unk, self.trail)
        self.unk.sort(key=lambda pid: self.all_PIs[pid].coverage)

        print("Root level redundant PIs: {}".format(covered))
        print("Unknown: {} (ordered by coverage)".format(self.unk))
        print("Current cost: {} (UB: {})".format(self.current_cost,self.UB))

    def solve(self):
        self.init_solve()

        if not self.unk:
            if self.check_solution:
                self.ct.compare_solutions(self.ptrail)
            print("All PIs are root-essential, no search started.")
            print()
            for pid in self.ptrail:
                qform = self.all_PIs[pid].quantified_form
                if qform != "":
                    print("invariant [pi{}] {}".format(pid,qform))
                else:
                    break
            return

        while (True):
            while (True):
                covered = self.ct.remove_covered_pis(self.ptrail, self.unk, self.trail)
                if self.v > 2:
                    for pid in covered:
                        print("P-{}".format(pid),end=' ')
                essentials = self.ct.move_conditional_essentials(self.ptrail,self.unk,self.trail)
                for pid in essentials:
                    self.current_cost += self.all_PIs[pid].cost
                    if self.v > 2: print("P{}".format(pid),end=' ')
                if not covered and not essentials:
                    break

            if not self.unk:
                self.evaluate_solution()
                pid = self.backtrack()
                if not pid:
                    break
            elif self.cost_is_over_UB():
                while (self.cost_is_over_UB() and pid):
                    pid = self.backtrack()
                if not pid:
                    break
            else:
                pid = self.decide()
                if self.v > 2: print("\nD{}".format(pid),end=' ')
                
                if self.cost_is_over_UB():
                    pid = self.backtrack()
                    if not pid:
                        break            
        print()
        print("Looking for ALL solutions: {}".format(self.all_solutions))
        print("All PIs:    ",list(self.all_PIs.keys()))
        print("A solution: {} (from {} found solutions)".format(self.best_solutions[0],len(self.best_solutions)))
        if self.check_solution: 
            for idx,sol in enumerate(self.best_solutions):
                print('Solution {}'.format(idx))
                self.ct.compare_solutions(sol)

        if self.all_solutions:
            print('ALL solutions:')
            for sol in self.best_solutions:
                print(sol)
        
        if len(self.best_solutions) == 1:
            print()
            for pid in self.best_solutions[0]:
                qform = self.all_PIs[pid].quantified_form
                if qform != "":
                    print("invariant [pi{}] {}".format(pid,qform))
                else:
                    break

    def backtrack(self):
        pid = 0
      
        while (self.trail):
            v = self.trail.pop()
            pid = abs(v)
            pic = self.all_PIs[pid]
           
            if v > 0:
                self.ptrail.pop()
                self.current_cost -= pic.cost
                
            if pic.decided:
                if self.v > 2: print("undo&flip decision {} (trail length: {}/{})".format(v,len(self.trail)+1,len(self.all_PIs)))
                pic.decided = False
                self.assign(-1*v)
           
                return pid
            else:
                self.unk.append(pid)
            
        return 0

    def decide(self):
        idx = 0
        
        #self.unk.sort(key=lambda pid: self.all_PIs[pid].cost)
        self.unk.sort(key=lambda pid: self.all_PIs[pid].coverage)
        
        if self.prefer_consts:
            for u_idx, pid in enumerate(self.unk):
                if self.all_PIs[pid].has_all_const:
                    idx = u_idx
                    break
        
        pid = self.unk.pop(idx)
        self.all_PIs[pid].decided = True
        self.assign(pid)
  
        return pid

    def assign(self, lit: int):
        assert(lit != 0)
        self.trail.append(lit)
        if lit > 0:
            self.ptrail.append(lit)
            self.current_cost += self.all_PIs[lit].cost
            
    def evaluate_solution(self):
        if self.current_cost < self.UB:
            self.best_solutions = []
            self.best_solutions.append(self.ptrail[:])
            self.UB = self.current_cost
            print('IMPROVED solution is found with len {} and cost: {}'.format(len(self.ptrail),self.current_cost))
            
        elif self.current_cost == self.UB and self.all_solutions:
            self.best_solutions.append(self.ptrail[:])
            print('Another solution is found with len {} and cost: {}'.format(len(self.ptrail),self.current_cost))
    
    def cost_is_over_UB(self) -> bool:
        if self.all_solutions:
            return self.current_cost > self.UB
        else:
            return self.current_cost >= self.UB

def usage ():
    print("Usage: python3 minimizer.py protocol.ivy cubes.pla [options]")
    print("Possible options:")
    print("--only-pis\t\t\t\t\t\tEnumerate all PI implicant classes and return (default: False).")
    print("--all-solutions\t\t\t\t\t\tFind all optimal solutions (default: False).")
    print("--verbose\t\t\t\t\t\tPrint all details of search (default: False).")
    print("--check-solution\t\t\t\t\tCompare number of found solutions with solutions of R (default: False).")
    print("--pi-weights=PI-quantification-results-from-ic3po\tConsider the qcosts of the found orbits.")
    print("--print-dimacs=path-to-dimancs-file.dimacs\t\tDump the underlying SAT formula of the minimization to file.")
    print("--print-classinfo=path-to-qcost-orbit-relation-file\tDump the short summary of qcosts and quantified forms to file.")
    print("--prefer-consts\t\t\t\t\t\tPrioritize orbits with constants in them during decision (default: False).")
def usage_and_exit ():
    usage()
    sys.exit(1)


def get_R_as_PI_classes(R_cubes,dsh,atoms):
    n = len(atoms)
    pi_classes = []
    for cube_str in R_cubes:
        cube = ['-']*n
        for idx,atom in enumerate(atoms):
            if cube_str[idx] == '1':
                cube[idx] = '1'

            elif cube_str[idx] == '0':
                cube[idx] = '0'

        found = False
        for pic in pi_classes:
            if pic.has_cube(cube):
                found = True
                break
        if found:
            continue
        cube_class = dsh.get_symmetric_variants(cube)
        
        pi_class = None
        for c in cube_class:
            pi_cube = Cube(c)
            
            if pi_class is None:
                pi_class = PIClass(pi_cube)
            else:
                pi_class.add_equivalent_cube(pi_cube)

        print('{}'.format(pi_class))
        
        pi_classes.append(pi_class)
    return pi_classes

def calculate_weights(all_pis,wfile):
    # ->
    #     pla:    ----------1----1
    #     quantifier-free:        (~committed(r1) | ~aborted(r0))
    #     quantified:     (forall R1, R2 . ((R2 = R1) | ~aborted(R2) | ~committed(R1)))
    #     num-forall:     2
    #     num-exists:     0
    #     num-lits:       3

    with open(wfile,"r") as weights:
        pi_details = {}
        for line in weights:
            if line.startswith("->"):
                cube_str = next(weights).split(":")[1].strip()
                _ = next(weights)
                qform = next(weights).split(":")[1].strip()
                num_forall = int(next(weights).split(":")[1].strip())
                num_exists = int(next(weights).split(":")[1].strip())
                num_lits = int(next(weights).split(":")[1].strip())
                qcost = num_forall + num_exists + num_lits
#                 qcost = (1+num_forall) * (1+num_exists) * (1+num_lits)
                pi_details[cube_str] = (qform,qcost)

    for pic in all_pis:
        cube_str = ''.join(pic.repr_pi.all_literals)
        if cube_str in pi_details:
            print(pi_details[cube_str])
            pic.quantified_form, pic.qcost = pi_details[cube_str]
            

def main ():
    if len(sys.argv) < 3:
        usage_and_exit ()

    for idx in range(2):
        if not path.isfile(sys.argv[idx+1]):
            print("Cannot find file: {}".format(sys.argv[idx+1]))
            usage_and_exit ()

    ivy_file = sys.argv[1]
    pla_file = sys.argv[2]

    silent = False
    import_costs = False
    print_dimacs = False
    print_picinfo = False
    weight_path = None 
   
    for opt in sys.argv[3:]:
        if not opt in ["--all-solutions","--verbose","--check-solution","--only-pis", "--prefer-consts"] and\
            not opt.startswith("--pi-weights=") and\
            not opt.startswith("--print-dimacs=") and\
            not opt.startswith("--print-classinfo="):
            print("Unrecognized option: ",opt)
            usage_and_exit ()
        if opt.startswith("--pi-weights="):
            import_costs = True
            weight_path = opt[13:]
        elif opt.startswith("--print-dimacs="):
            print_dimacs = True
            dimacs_path = opt[15:]
        elif opt.startswith("--print-classinfo="):
            print_picinfo = True
            picinfo_path = opt[18:]
        elif opt == "--only-pis":
            silent = True
            
    pp, cube_strs = parse_input_files(ivy_file,pla_file,silent)
    atoms = pp.atom_strs
    domains = pp.sort_elements
    Cube.setup_universe(len(atoms)+1,atoms)
    PIClass.setup_universe(pp.atoms)

    dsh = DomainSymmetryHandler(domains,pp.predicates,pp.atoms)

    # R_pi_classes = get_R_as_PI_classes(cube_strs,dsh,atoms)
    # mm = Minimizer(R_pi_classes)
    
    de = DualEncoder(atoms)
    if silent:
        de.verbosity = 0
    all_pis = de.extract_prime_implicants(dsh, cube_strs)

    if import_costs:
        calculate_weights(all_pis,weight_path)

    if print_dimacs:
        ct = CoverTable(all_pis, len(PIClass._atoms))
        ct.print_CNF(dimacs_path)
    
    if print_picinfo:

        with open(picinfo_path, "w") as picfile:
            has_qform = (len(all_pis) > 0 and all_pis[0].qcost != 0)
            for pic in all_pis:
                if has_qform:
                    picfile.write("{};{};{}; {}\n".format(\
                        pic.id,pic.qcost,\
                        ' '.join([str(lit) for lit in pic.repr_pi.care]),\
                        pic.quantified_form)) 
                else:
                    picfile.write("{};{};{}; {}\n".format(\
                        pic.id,pic.cost,\
                        ' '.join([str(lit) for lit in pic.repr_pi.care]),\
                        "none")) 
                    
    if ("--only-pis" in sys.argv[3:]):
        print("// PIC list of {}".format(pla_file.split('/')[-1]))
        print("// PLA Header: {}".format(' '.join(atoms)))
        for pic in all_pis:    
            print(''.join(pic.repr_pi.all_literals))
        
        return

    mm = Minimizer(all_pis)

    if ("--all-solutions" in sys.argv[3:]): mm.all_solutions = True
    if ("--verbose" in sys.argv[3:]): mm.v = 3
    if ("--check-solution" in sys.argv[3:]): mm.check_solution = True
    
    if not silent:
        print("Protocol specification: {}".format(ivy_file))
        print("Reachable states: {}".format(pla_file))
        print("Further options: ",sys.argv[3:])
        print('Number of input variables: {}'.format(len(atoms)))
        print('Number of input cubes: {}'.format(len(cube_strs)))

    mm.solve()

if __name__ == '__main__':
    main ()





