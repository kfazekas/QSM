Requirements:
    - requirements of qiQSM (under qiQSM/ic3po)
    - lark, pysat
    - tried only with python3.10, change cmd in the run_* scripts to use/try
    another python version

QSM Toolchain: bash `./scripts/deploy_all.sh`
It is the script that calls all the necessary steps/scripts to get the results.
To use the script, certain details must be filled in/modified based on your own
running environment.
1. It requires the locations of all the relevant scripts and binaries:
    1. instances: The list of instances to run, see description below.
    2. ivybench: The path to the folder where the ivy files can be found (it
    assumes a structure of folders as in the ivybench repository, see e.g. 
    https://github.com/aman-goel/ivybench)
    3. DIRqiQSM: The path to the folder where the qiQSM version of ic3po is
    located. (For example, if you have qiQSM at /home/user/tools/qiQSM/ic3po, 
    then DIRqiQSM should be set to /home/user/tools/)
    4. DIRminimizer: Tha path to the folder where the minimizer python script is
    located. See details below.
    5. runlim_bin: The path to the binary of runlim (in case it is not
    installed). It can be installed with apt, or can be downloaded from here:
    https://fmv.jku.at/runlim/
    6. output: The folder there where the output of the scripts can be written.
    See below the details of the output structure.

2. Setting up the running environment for ic3po:
    The script has a setup_ic3po_env () function where the necessary steps to
    run ic3po can be added (I left there my steps commented out as an example).

The main steps of the script are the following:
1. Run the qiQSM version of ic3po PLA generator. The time and space limit of
    these runs are set at the beginning of scripts/pla_generator.py.
    T: time limit (sec), R: real time limit (sec), S: space limit (MB).
    Important: The runs of ic3po for pla generation will not stay under the
    space limit defined here!

2. Run the minimizer python code to enumerate the prime implicants of the
    negation of the given R-PLA. The minimizer needs at least two arguments and
    their order matters: (1) the ivy file of the protocol (to get the signature
    of the protocol relations) (2) the pla file. The further possible options:
    "--all-solutions": return every optimal solution, not necessarily just one
    "--pi-weights=[file name]": The qiQSM ic3po quantifier inference output.
    "--verbose": print more details about the steps of the search
    "--check-solution": compare the number of SAT solutions of \neg R to the
    number of solutions of the selected PIs
    "--only-pis": only enumerate and print the PI orbits
    "--prefer-consts": prefer deciding on orbits with constants with them, if no
    such, stay with coverage
    "--print-dimacs=[file name]": Prints the coverage formula a dimacs file
    "--print-classinfo=[file name]": Prints the selector variable, the weight,
    the representative PI and the quantified form of the orbits into a file.
            
3. Run the qiQSM version of ic3po to get the quantified cost of the PI orbits.
    The time and space limit of these runs are set at the beginning of
    scripts/quantify_pis.py. T: time limit (sec), R: real time limit (sec), 
    S: space limit (MB). This run will create a new output folder under tmp so
    that the previous output folder does not get overwritten. The output of this
    run is the quantified PI list, this will be considered for weights

4. Run the actual minimization python code. Note that it will also re-generate
    the PIs, and so the runtime will be the sum of PI enumeration and 
    minimization. (The runtime of the PI enumeration can be found in the pi-gen-
    err file, so we can have an idea about how much is the actual minimization).
    Further, it will look for all solutions, to show that it is unique.

5. Run Summary script. Sums up the details of the minimization runs into a table
    based on the produced min-instance-size.err files. The current version
    sums up only the log files with 'min-' prefix and their .err pair files.
    To use the script for other err files it needs some modifications, but in
    general the runlim reports are relatively easy to see through via grep.

instances.yaml
    It contains the list of problems to run. Only these problems are supported by
    our current prototype.
    For each instance it provides two information:
    1. The location of the ivy file (relative to the ivybench folder).
    2. The name and size range of every sort of the protocol.
    The run script will consider only those instances that are uncommented in
    it. It will generate every size combination over the defined ranges of each
    sort. Quroum sorts must be defined explicitly as dependent sort, the only
    argument for it is the 'superset sort' (see for example ex-toy-consensus).

    IMPORTANT: For the proper symmetry recognition in the minimizer the 
    following sort names are wired in (see beginning of symmetry.py):
    quorum_sort_names = ['quorum','nset','nodeset']
    quorum_superset_sorts = ['node','acceptor']
    In case an instance has a quorum sort with another (superset-)sort-name,
    it should be added to this list, otherwise quorum permutations might will
    not be correct! (TODO: rely on the yaml input where quorum sorts are marked
    explicitly.)

Output structure:
    For each instance a folder is created with the instance name (e.g. 
    tla-tcommit). Inside that folder, for each sort size combination a new
    folder is created (e.g. tla-tcommit-r1). In the instance folder several
    files are created:

    1. instance-size_R.pla: The PLA file of the reachable states.
    
    2. instance-size.pis: The PI list file generated by the minimizer script
        (used as input for qiQSM to generate the quantified form)
    
    3. instance-size.qpis: The quantified form of the PI lists, generated by
        qiQSM-ic3po
    
    4. instance-size.dimacs + instance-size_qcosts.txt: The covering SAT
        formula of the instance and the summary of the orbit costs and selector
        variables (can be added to the CaDiCaL-based C++ minimizer).
    
    5. min-instance-size.log: The actual output of the minimizer. It contains
        the PI list (together with their quantified form), a short log of the
        search and at the bottom, the found solution. In case the solution was
        unique, it prints them out in quantified form as invariants that can be
        included to the ivy file for later checks (lines starting with
        'invariant [piN] ')
    
    6. min-instance-size.err: The runlim log file regarding the minimizer run.
        It describes the used resources, regarding time and space. In case it
        run out of time or space, the value of the 'status' field will not be
        'ok'. The stderr output of qiQSM is going here too.

    7. gen-pis-instance-size.err: The runlim log file regarding the pi 
        generation run of the minimizer. The stderr output of qiQSM is going
        here too.

    8-. instane-size_R.dot,  instane-size_R.vmt, nstane-size_R.ivy,
        instane-size_R.results, instane-size_R.log, etc: Output generated by
        ic3po during the pla generation.

There are two further folders generated in the instance folder (beyond the
size specific folders):
1. pla-gen-logs/: Contains the runlim log and the output of the runs of
    qiQSM for the PLA generation for each specific instance. This can be
    used if you want to check which runs were unsuccessfull and in general
    home much time this step required.
2. qi-gen-logs/: The same as above, but for the runs of qiQSM for the PI 
    quantification step.

Summary file: As a last step, the script sums up the found minimizer runs
    in the output folder and writes the results into a 'summary.txt'. In 
    case an argument is given to the run_complete script, it will append it
    as a prefix to the summary file name.

tmp/ folder: This folder is used to separate the output of the two runs of
    ic3po, after run the relevant files are copied to the shared output
    folder, so this tmp folder can be deleted.

 
