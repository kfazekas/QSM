import shlex
import subprocess
import os
import sys
import yaml
import itertools
from math import comb

minimizer_path = None
instance_path = None
path_prefix = None
outdir = None
runlim_path= None

T=3600
R=3600
S=7000
 
if len(sys.argv) > 1:
    assert(len(sys.argv)>8)
    minimizer_path = sys.argv[1]
    instance_path = sys.argv[2]
    path_prefix = sys.argv[3]
    outdir = sys.argv[4]
    runlim_path = sys.argv[5]
    T = int(sys.argv[6])
    R = int(sys.argv[7])
    S = int(sys.argv[8])

inst_counter = 0

with open(instance_path,'r') as yaml_file:
    instances = yaml.safe_load(yaml_file)
    for instance,data in instances.items():
        output_dir = "{}/{}".format(outdir,instance)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        inputs = []
        quorum_sizes = {}
        idx = 0
        quroum_idx = -1
        quorum_ss = None
        size_header = []
        for sort_name,interval in data["size"].items(): #stable
            if "superset" in interval.keys():
                quorum_ss = interval["superset"]
                ss_from = data["size"][quorum_ss]["from"]
                ss_to = data["size"][quorum_ss]["to"]+2
                for val in range(ss_from,ss_to):
                    quorum_size = comb(val,int(val/2)+1)
                    quorum_sizes[val] = quorum_size
                    quroum_idx = idx
                inputs.append(tuple([0]))   
            else:
                inputs.append(tuple(range(interval["from"],interval["to"]+2)))
            size_header.append(sort_name)
            idx += 1

        for size_input in itertools.product(*inputs):
            size_list = list(size_input)
            if quroum_idx >= 0:
                ss_idx = list(data["size"].keys()).index(quorum_ss)
                val = size_list[ss_idx]
                size_list[quroum_idx] = quorum_sizes[val]
            
            sizes_str = ','.join(["{}={}".format(k,v) for (k,v) in zip(size_header,size_list)])
            name = "{}-{}".format(instance,'-'.join([k[0]+str(v) for (k,v) in zip(size_header,size_list)]))
  
            output_dir = "{}/{}".format(outdir,instance)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            ivy_path = "{}{}".format(path_prefix,data["path"])
            pla_path = "{}/{}/{}_R.pla".format(output_dir,name,name)
   
            if not os.path.isfile(pla_path):
                print('Did not find PLA of {}.'.format(name))
                continue
   

            qpi_path = "{}/{}/{}.qpis".format(output_dir,name,name)
            if not os.path.isfile(qpi_path):
                # PI generation of instance failed
                print('Did not find quantified PI list of {}.'.format(name))
                print(qpi_path)
                continue

            log_path = "{}/{}/min-{}.log".format(output_dir,name,name)
            err_path = "{}/{}/min-{}.err".format(output_dir,name,name)
            dimacs_path = "{}/{}/{}.cnf".format(output_dir,name,name)
            orbit_info = "{}/{}/{}_qcosts.txt".format(output_dir,name,name)

            spl = shlex.split("{} --time-limit={} --real-time-limit={} --space-limit={} python3.10 {}/minimizer.py {} {} --pi-weights={} --print-dimacs={} --print-classinfo={} --all-solutions".format(runlim_path,T,R,S,minimizer_path,ivy_path,pla_path,qpi_path,dimacs_path,orbit_info))
            # print("{} Running {}".format(inst_counter,name))
            # print("{} 1> {} 2> {}".format(' '.join(spl),log_path, err_path))
            
            with open(log_path, 'w') as log, open(err_path, 'w') as err:
                    try:
                        completeRun = subprocess.run(spl, stdout=log, stderr = err, timeout=R*1.05)
                    except subprocess.TimeoutExpired:
                        # Should not happen, runlim has less time limit
                        print("Instance {} reached timeout.".format(name), flush=True)
                        
                        if len(size_header) == 1:
                            # When there is only one sort, there is no need to
                            # increase the size further, the next will time out as
                            #  well.
                            break 

                        continue

                    if not completeRun.returncode == 0:
                        print("Error, for instance {} return code was different from 0.".format(name))
    
