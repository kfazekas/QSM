#include "qs_minimizer.h"
#include <iostream>
#include <cassert>
#include <fstream>
#include <sstream>
#include <algorithm>

namespace QSM {

QSMinimizer::QSMinimizer() {};

QSMinimizer::~QSMinimizer() {
    for(auto pic : all_pic) {
        if (pic) delete pic;
    }
    
    if (cc) delete cc;
    if (solver) delete solver;
};


void QSMinimizer::setup_cadical() {
    std::cout << "c Initializing CaDiCaL ";
    solver = new CaDiCaL::Solver;
    solver->set("inprocessing",0);
    std::cout << "(version " << solver->version() << ")." << std::endl;
    
    
};

void QSMinimizer::setup_coverage_counter () {
    cc = new CoverageCounter(solver, max_care);
    
};

bool QSMinimizer::read_dimacs (std::string dimacs_path) {
    assert (solver);
    int vars = 0;
    const char* res = solver->read_dimacs(dimacs_path.c_str(),vars,1);
    min_pid = vars;
    if (!res) return false;
    else {
        std::cout << "Error occurred during reading file: " << res << std::endl;
        return true;
    }
};

bool QSMinimizer::read_pi_class_info(std::string pic_path) {
    
    std::ifstream input_file_stream(pic_path);
    std::string line;
    if (!input_file_stream.is_open()) {
      std::cout << "c Error, could not open file '" << pic_path << "'. " << std::endl;
      return true;
    }
    
    size_t line_c = 0;
    size_t pic_c = 0;
    while (std::getline(input_file_stream, line)) {
        line_c++;
        std::istringstream line_stream(line);

        std::string token;
        size_t token_c = 0;
        
        int itoken;
        bool is_int;

        PIClass* pic = new PIClass();
        while (std::getline(line_stream, token, ';')) {
            is_int = false;
            try {
                itoken = std::stoi(token);
                is_int = true;
            } catch(std::exception& e){}
            switch (token_c) {
                case 0:
                    if (!is_int) {
                        std::cout << "Error in line " << line_c << ", token " << token_c;
                        std::cout << ": expected int." << std::endl;
                        input_file_stream.close();
                        delete pic;
                        return true;
                    } else {
                        pic->pid = itoken;
                        if (itoken < min_pid) min_pid = itoken;
                    }
                    break;
                case 1:
                    if (!is_int) {
                        std::cout << "Error in line " << line_c << ", token " << token_c;
                        std::cout << ": expected int." << std::endl;
                        input_file_stream.close();
                        delete pic;
                        return true;
                    } else pic->cost = itoken;
                    break;
                case 2: {
                    auto iss = std::istringstream{token};
                    int lit_token;
                    while (iss >> lit_token) {
                        if (lit_token) {
                            pic->care_lits.insert(lit_token);
                            if (lit_token > max_care) max_care = lit_token;
                        } else {
                            std::cout << "Error in line " << line_c << ", token " << token_c;
                            std::cout << ": expected int." << std::endl;
                            input_file_stream.close();
                            delete pic;
                            return true;
                        }
                    }
                    break;
                }
                case 3: {
                    if (!is_int) {
                        std::cout << "Error in line " << line_c << ", token " << token_c;
                        std::cout << ": expected int." << std::endl;
                        input_file_stream.close();
                        delete pic;
                        return true;
                    } else pic->has_const = itoken;
                   
                    break;
                }
                case 4: {
                    if (!is_int) {
                        std::cout << "Error in line " << line_c << ", token " << token_c;
                        std::cout << ": expected int." << std::endl;
                        input_file_stream.close();
                        delete pic;
                        return true;
                    } else pic->has_all_const = (itoken > 0);
                   
                    break;
                }
                case 5:
                    pic->qform = token;
                    break;
                default:
                    std::cout << "Error in line " << line_c << ", token " << token_c;
                    std::cout << ": unexpected token." << std::endl;
                    input_file_stream.close();
                    delete pic;
                    return true;
            }
            token_c++;
            
        }
        if (!pic->pid || !pic->cost || !pic->care_lits.size()) {
            std::cout << "Error in line " << line_c << " of " << pic_path 
                << ", unrecognized tokens." << std::endl;
            delete pic;
            return true;
        }
        // std::cout << pic->pid << " " << pic->cost << " " << pic->care_lits.size() << pic->qform << std::endl;
        pic_c++;

        pidIdx.insert(std::make_pair(pic->pid, all_pic.size()));
        
        pids.push_back(pic->pid);
        all_pic.push_back(pic);
        costs.push_back(pic->cost);
        coverages.push_back(pic->cost);
        vals.push_back(0);
        best_cost += pic->cost;
        unassigned++;
    }
    
    input_file_stream.close();
    std::cout << "c Found " << pic_c << " PI classes in " << pic_path <<"." << std::endl;
    
    return false;
};





void QSMinimizer::assign_root_essentials () {
    assert (solver);
    std::vector<int> essentials;
    for (size_t idx = 0; idx < pids.size(); idx++) {
    //for(const auto& pid : unk) {
        int pid = pids[idx];
        for(const auto& lit : all_pic[idx]->care_lits) {
            solver->assume(lit);
        }
        for(const auto& other : pids) {
            if (pid == other) continue;
            solver->assume(other);
        }
        int res = solver->solve ();
        sat_calls++;
        if (res == 10) {
            essentials.push_back(pid);
        } 
        
    }
    for(const auto& pid : essentials) {
        assign_selected (pid);
        if (verbose) std::cout << "c PI class " << pid << " is root essential." << std::endl;
    }
};

bool QSMinimizer::assign_conditional_essentials () {
    assert (solver);
    if (trail.size() == ptrail.size()) return false;
    if (!removed) return false;
    removed = false;
    std::vector<int> essentials;
    for (size_t idx = 0; idx < pids.size(); idx++) {
    //for(const auto& pid : unk) {
        if (vals[idx]) continue;
        int pid = pids[idx];

        //p-part
        for(const auto& lit : ptrail) {
            solver->assume(lit);
        }
        //u-part
        for (size_t idx_other = 0; idx_other < pids.size(); idx_other++) {
            if (idx == idx_other || vals[idx_other]) continue;
            solver->assume(pids[idx_other]);
        }
        // PI
        for(const auto& lit : all_pic[idx]->care_lits) {
            solver->assume(lit);
        }
        int res = solver->solve ();
        sat_calls++;
        if (res == 10) {
            essentials.push_back(pid);
        } 
        
    }
    for(const auto& pid : essentials) {
        assign_selected (pid);
        if (verbose) std::cout << "P" << pid << " ";
    }
    
    return (essentials.size() != 0);
};

bool QSMinimizer::assign_covered () {
    assert (solver);
    if (cover_propagated == ptrail.size()) return false;
    std::vector<int> covered;
    for (size_t idx = 0; idx < pids.size(); idx++) {
    //for(const auto& pid : unk) {
        if (vals[idx]) continue;
        int pid = pids[idx];
        for (const auto& lit : ptrail) {
            solver->assume(lit);
        }
        for(const auto& lit : all_pic[idx]->care_lits) {
            solver->assume(lit);
        }
        cc->start_coverage_count ();
        int res = solver->solve ();
        sat_calls++;
        if (res == 20) {
            covered.push_back(pid);
        } else {
            //std::cout << "PI " << pid << " coverage: " << cc->assumption_coverage << std::endl;
            coverages[idx] = cc->assumption_coverage;
        }
        cc->stop_coverage_count ();
        
    }
    for(const auto& pid : covered) {
        assign_not_selected (pid);
        //std::cout << "c PI class " << pid << " is covered." << std::endl;
        if (verbose) std::cout << "P-" << pid << " ";
    }
    cover_propagated = ptrail.size();
    return covered.size() != 0;
};

void QSMinimizer::assign_selected (int pid) {
    trail.push_back(pid);
    ptrail.push_back(pid);
    size_t idx = pidIdx[pid];
    vals[idx] = 1;
    unassigned--;
    update_cost(costs[idx]);
    
};


inline void QSMinimizer::update_cost (int cost) {
    current_cost += cost;
    if (all_solutions) 
        over_UB = (current_cost > best_cost);
    else
        over_UB = (current_cost >= best_cost);
};

void QSMinimizer::assign_not_selected (int pid) {
    trail.push_back(-pid);
    size_t idx = pidIdx[pid];
    vals[idx] = -1;
    unassigned--;
    removed = true;
};


void QSMinimizer::decide () {
    // for (auto pic : all_pic) {
    //     size_t idx = pidIdx[pic->pid];
    //     if (vals[idx]) continue;
    //     std::cout << pic->pid << " cov: " << coverages[idx] << std::endl;
    // }
    std::vector<PIClass*>::iterator it;
    if (this->prefer_consts)
        it = std::min_element(all_pic.begin(), all_pic.end(), const_or_less_coverage(this));
    else 
        it = std::min_element(all_pic.begin(), all_pic.end(), less_coverage(this));
    PIClass* min_pic = *it;
    int pid = min_pic->pid;
    if (verbose) std::cout << "D" << pid << " ";
#ifndef NDEBUG
    size_t idx = pidIdx[pid];
    assert (!vals[idx]);
#endif
    min_pic->decided = true;
    assign_selected(pid);
};

void QSMinimizer::print_solution (size_t idx) {
    assert(idx < best_solutions.size());
    for (const auto& pid : best_solutions[idx]) {
            size_t idx = pidIdx[pid];
            std::cout << "invariant [pi" << pid << "] " << all_pic[idx]->qform << std::endl;
    }
};

void QSMinimizer::evaluate_solution () {
    if (current_cost < best_cost) {
        best_solutions.clear();
        std::vector<int> new_solution {ptrail};
        best_solutions.push_back(new_solution);
        best_cost = current_cost;
        std::cout << "c IMPROVED solution was found. Length: ";
        std::cout << new_solution.size() << " cost: " << best_cost << std::endl;
    } else if (current_cost == best_cost && all_solutions) {
        std::vector<int> new_solution {ptrail};
        best_solutions.push_back(new_solution);
        std::cout << "c another solution was found. Length: ";
        std::cout << new_solution.size() << " cost: "<<  best_cost << std::endl;
    }
};

bool QSMinimizer::backtrack () {
    int cost_diff = 0;
    while(trail.size()) {
        int last_assignment = trail.back();

        int pid = abs(last_assignment);
        size_t idx = pidIdx[pid];
        PIClass* pic = all_pic[idx];

        // unassign
        trail.pop_back();
        vals[idx] = 0;
        unassigned++;
        if (last_assignment > 0) {
            ptrail.pop_back();
            cost_diff += costs[idx];
        }
        if (pic->decided) {
            // Flip
            pic->decided = false;
            assign_not_selected(pid);
            update_cost(-1*cost_diff);
            if (verbose) std::cout << "F" << pid << std::endl;
            return true;
        }
    }
    return false;
};

void QSMinimizer::solve () {
    setup_coverage_counter ();

    assign_root_essentials ();
    assign_covered ();
    if (!unassigned) {
        std::cout << "c All PIs are assigned on root-level, no search started." << std::endl;
        print_solution ();
    }
    // bool changed;
    // while (true) {
    //     if (over_UB) {
    //         if (!backtrack ()) break;
    //     }
        
    //     changed = true;
    //     while (changed) {
    //         changed = false;
    //         assign_covered ();
    //         changed = assign_conditional_essentials ();
    //         if (changed && verbose) std::cout << std::endl;
    //     }
        
    //     if (!unassigned) {
    //         evaluate_solution ();
    //         if (!backtrack ()) break;
    //     } else if (over_UB) {
    //         if (!backtrack ()) break;
    //     } else decide ();
    // } 
    while (true) {
        if (over_UB) {
            if (!backtrack ()) break;
            assign_conditional_essentials ();
        }
        
        assign_covered ();
        if (!unassigned) {
            evaluate_solution ();
            if (!backtrack ()) break;
            assign_conditional_essentials ();
        } else if (over_UB) {
            if (!backtrack ()) break;
            assign_conditional_essentials ();
        } else decide ();
    }   
    print_solution ();

    std::cout << "c Number of SAT calls: " << sat_calls << std::endl;
};


}