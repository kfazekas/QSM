#include <stdio.h>
#include <stdlib.h>
#include <string>
#include <iostream>
#include <iomanip>
#include <signal.h>
#include <stdexcept>      // std::out_of_range
#include <map>
#include "src/qs_minimizer.h"

using namespace QSM;

const int ver {1};

static void SIGINT_exit(int);

static void (*signal_SIGINT)(int);
static void (*signal_SIGXCPU)(int);
static void (*signal_SIGSEGV)(int);
static void (*signal_SIGTERM)(int);
static void (*signal_SIGABRT)(int);

static void SIGINT_exit(int signum) {
  signal(SIGINT, signal_SIGINT);
  signal(SIGXCPU, signal_SIGXCPU);
  signal(SIGSEGV, signal_SIGSEGV);
  signal(SIGTERM, signal_SIGTERM);
  signal(SIGABRT, signal_SIGABRT);

  std::cout << "c Signal interruption." << std::endl;

  fflush(stdout);
  fflush(stderr);

  raise (signum);
}

static const std::map<std::string,std::string> option_list = {
    {"--help",                "Print usage message with all possible options"},
    {"-cnf <path to dimacs>", "Define path of the input DIMACS file"},
    {"-pic <path to PI list>","Define path PI information file"},
    {"--all-solutions",       "Search for all optimal solutions. [default: false]"},
    {"--prefer-consts",       "Prefer PI orbits over constants in decisions. [default: false]"},
    {"--verbose",             "Increase verbosity."}
};

int get_number_arg(std::string const& arg) {
    try {
        std::size_t pos;
        int x = std::stoi(arg, &pos);
        if (pos < arg.size()) {
            std::cerr << "Trailing characters after number: " << arg << '\n';
        }
        return x;
    } catch (std::invalid_argument const &ex) {
      std::cerr << "Invalid number: " << arg << '\n';
      return 0;
    } catch (std::out_of_range const &ex) {
      std::cerr << "Number out of range: " << arg << '\n';
      return 0;
    }
}

void print_usage() {
    std::cout << "usage: minimizer -cnf protocol_R.dimacs -pic PI-info-and-weights.txt [ <option> ... ] " << std::endl;
    std::cout << "where '<option>' is one of the following options:" << std::endl;
    std::cout << std::endl;
    for (auto option : option_list)  {
        std::cout << std::left << "\t" << std::setw(30) << option.first << "\t" << option.second  << std::endl;
    }
    std::cout << std::endl;
}

int main (int argc, char ** argv) {
    signal_SIGINT =  signal(SIGINT, SIGINT_exit);
    signal_SIGXCPU = signal(SIGXCPU, SIGINT_exit);
    signal_SIGSEGV = signal(SIGSEGV, SIGINT_exit);
    signal_SIGTERM = signal(SIGTERM, SIGINT_exit);
    signal_SIGABRT = signal(SIGABRT, SIGINT_exit);

    QSMinimizer* qsm;

    std::string dimacs_file;
    std::string piclass_file;
    
    std::cout << "c Minimizer 0." << ver << "." << std::endl;
    
    if(argc < 2) {
      std::cerr << "c Error, no dimacs file was specified." << std::endl;
      print_usage();
      return 1;
    }

    qsm = new QSMinimizer ();
    
    qsm->setup_cadical ();

    for (int i = 1; i < argc; i++) {
        if (argv[i] == std::string("-cnf")) {
            bool error = qsm->read_dimacs(argv[++i]);
            if (error) {
                delete qsm;
                return 1;
            }
        } else if (argv[i] == std::string("-pic")) {
            bool error = qsm->read_pi_class_info(argv[++i]);
            if (error) {
                delete qsm;
                return 1;
            }
        } else if (argv[i] == std::string("--all-solutions")) {
            std::cout << "c option found: " << argv[i] << std::endl;
            qsm->all_solutions = true;
        } else if (argv[i] == std::string("--verbose")) {
            std::cout << "c option found: " << argv[i] << std::endl;
            qsm->verbose = true;
        } else if (argv[i] == std::string("--prefer-consts")) {
            std::cout << "c option found: " << argv[i] << std::endl;
            qsm->prefer_consts = true;
        } else if (argv[i] == std::string("--help")) {
            print_usage();
            delete qsm;
            return 1;
        } else {
            std::cerr << "Unrecognized option: " << argv[i] << std::endl;
            print_usage ();
            delete qsm;
            return 1;
        }
    }
    

    qsm->solve ();
    delete qsm;
}
