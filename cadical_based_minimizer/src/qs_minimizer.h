#ifndef MIN_H
#define MIN_H

#include "cadical.hpp"
#include "coverage_counter.h"
#include <string>
#include <map>
#include <unordered_set>
#include <queue>

namespace QSM {

class PIClass {
public:
    PIClass() {};
    ~PIClass() {};

    std::unordered_set<int> care_lits;
    size_t cost = 0;
    
    size_t pid = 0;
    std::string qform;

    bool decided = false;
    size_t has_const = false;
    bool has_all_const = false;
};

class QSMinimizer {
public:
    QSMinimizer();
    ~QSMinimizer();

    bool verbose;
    bool all_solutions = false;
    bool prefer_consts = false;

    std::map<int,size_t> pidIdx;
    std::vector<PIClass*> all_pic;

    std::vector<int> pids;
    std::vector<int> vals;  // [1..|PICs|]
    std::vector<int> costs; // [1..|PICs|]
    std::vector<int> coverages; // [1..|PICs|]

    void setup_cadical ();

    bool read_dimacs (std::string);
    bool read_pi_class_info(std::string);

    void solve ();

    unsigned sat_calls = 0;
    size_t cover_propagated = 0;
    bool removed = false;

private:
    CaDiCaL::Solver* solver;
    CoverageCounter* cc;

    std::vector<int> trail;
    std::vector<int> ptrail;
    
    unsigned current_cost = 0;
    unsigned best_cost = 0;
    std::vector<std::vector<int>> best_solutions;

    size_t unassigned = 0;
    bool over_UB = false;
    int min_pid = 0;
    int max_care = 0;


    void setup_coverage_counter ();

    void update_cost (int cost);

    void assign_selected (int pid);
    void assign_decided (int pid);
    void assign_not_selected (int pid);

    void unassign (int pid);

    void assign_root_essentials ();
    bool assign_conditional_essentials ();
    bool assign_covered ();

    void decide ();
    bool backtrack ();

    void evaluate_solution ();
    void print_solution (size_t idx = 0);
};

struct less_cost {
    QSMinimizer* qsm;
    less_cost (QSMinimizer * qsmin) : qsm(qsmin) { };
    bool operator() (const PIClass* l, const PIClass* r) const;
};

struct less_coverage {
    QSMinimizer* qsm;
    less_coverage (QSMinimizer * qsmin) : qsm(qsmin) { };
    bool operator() (const PIClass* l, const PIClass* r) const;
};


struct const_or_less_coverage {
    QSMinimizer* qsm;
    const_or_less_coverage (QSMinimizer * qsmin) : qsm(qsmin) { };
    bool operator() (const PIClass* l, const PIClass* r) const;
};



inline bool less_cost::operator() (const PIClass* l, const PIClass* r) const {
    const size_t lidx = qsm->pidIdx[l->pid];
    const size_t ridx = qsm->pidIdx[r->pid];
    // unassigned < assigned
    if (abs(qsm->vals[lidx]) < abs(qsm->vals[ridx])) return true;
    if (abs(qsm->vals[lidx]) > abs(qsm->vals[ridx])) return false;
    // sort by cost
    if (qsm->costs[lidx] < qsm->costs[ridx]) return true;
    if (qsm->costs[lidx] > qsm->costs[ridx]) return false;
    //sort by pid
    return l->pid < r->pid;
        
};

inline bool less_coverage::operator() (const PIClass* l, const PIClass* r) const {
    const size_t lidx = qsm->pidIdx[l->pid];
    const size_t ridx = qsm->pidIdx[r->pid];
    // unassigned < assigned
    if (abs(qsm->vals[lidx]) < abs(qsm->vals[ridx])) return true;
    if (abs(qsm->vals[lidx]) > abs(qsm->vals[ridx])) return false;
    // sort by cost
    if (qsm->coverages[lidx] < qsm->coverages[ridx]) return true;
    if (qsm->coverages[lidx] > qsm->coverages[ridx]) return false;
    //sort by pid
    return l->pid > r->pid;
        
};

inline bool const_or_less_coverage::operator() (const PIClass* l, const PIClass* r) const {
    const size_t lidx = qsm->pidIdx[l->pid];
    const size_t ridx = qsm->pidIdx[r->pid];
    // unassigned < assigned
    if (abs(qsm->vals[lidx]) < abs(qsm->vals[ridx])) return true;
    if (abs(qsm->vals[lidx]) > abs(qsm->vals[ridx])) return false;
    // sort by cost
    if (l->cost < r->cost) return true;
    if (l->cost > r->cost) return false;
    // sort by coverage
    if (qsm->coverages[lidx] < qsm->coverages[ridx]) return true;
    if (qsm->coverages[lidx] > qsm->coverages[ridx]) return false;
    // prefer constants
    if (l->has_all_const && !r->has_all_const) return true;
    if (!l->has_all_const && r->has_all_const) return false;
    // prefer having at least one constants
    if (l->has_all_const && !r->has_const) return true;
    if (!l->has_all_const && r->has_const) return false;
    // sort by pid (which is sorted by length of repr PI)
    return l->pid > r->pid;
        
};

}

#endif