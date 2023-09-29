#ifndef COVC_H
#define COVC_H

#include "cadical.hpp"
#include <string>
#include <map>
#include <unordered_set>
#include <queue>

namespace QSM {

class CoverageCounter : CaDiCaL::ExternalPropagator {
    CaDiCaL::Solver * solver;
public:
    CoverageCounter (CaDiCaL::Solver *s, int max_care_lit);
    ~CoverageCounter () {
        solver->disconnect_external_propagator ();
    };
    bool in_count = false;
    unsigned assumption_coverage = 0;

    void start_coverage_count ();
    void stop_coverage_count ();

    void notify_assignment (int, bool);
    void notify_new_decision_level ();
    void notify_backtrack (size_t); 

    int cb_decide ();

    int cb_propagate () { return 0; }
    int cb_add_reason_clause_lit (int) { return 0; }
    bool cb_check_found_model (const std::vector<int> &) {
        return true;
    }
    bool cb_has_external_clause () { return false; }
    int cb_add_external_clause_lit () { return 0; }
private:
    bool on_assumption_level = true;
    unsigned root_coverage = 0;
   
};


}

#endif