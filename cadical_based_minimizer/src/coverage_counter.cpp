#include "coverage_counter.h"
#include <iostream>
namespace QSM {

CoverageCounter::CoverageCounter (CaDiCaL::Solver *s, int max_care_lit) : solver(s) {
        solver->connect_external_propagator(this);
        for (int idx = 1; idx <= max_care_lit; idx++) solver->add_observed_var(idx);
        std::cout << "c Number of SAT-variables: " << solver->active() << std::endl;
        std::cout << "c Number of observed SAT-variables: " << max_care_lit << std::endl;

        on_assumption_level = true;
        in_count = false;
};

void CoverageCounter::start_coverage_count () {
    in_count = true;
    call_cb_decide = true;
    on_assumption_level = true;
    assumption_coverage = root_coverage;
}

void CoverageCounter::stop_coverage_count () {
    in_count = false;
    call_cb_decide = false;
}

void CoverageCounter::notify_assignment (int, bool is_fixed) {
    if (is_fixed) {
        root_coverage++;
        if (in_count) assumption_coverage++;
    } else {
        if (in_count && on_assumption_level) assumption_coverage++;
    }
    
}

void CoverageCounter::notify_new_decision_level () {}

void CoverageCounter::notify_backtrack (size_t) {}

int CoverageCounter::cb_decide () {
    on_assumption_level = false;
    return 0;
}

}