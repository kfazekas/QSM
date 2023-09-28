import shlex
import subprocess
import sys
import yaml
import itertools
from math import comb
import os

outdir = None
path_prefix = None
instance_path = None
runlim_path = None

T=3600
R=3600
S=32000

if len(sys.argv) > 1:
    assert (len(sys.argv) > 7)
    instance_path = sys.argv[1]
    path_prefix = sys.argv[2]
    outdir = sys.argv[3]
    runlim_path = sys.argv[4]
    T = int(sys.argv[5])
    R = int(sys.argv[6])
    S = int(sys.argv[7])

with open(instance_path,'r') as yaml_file:
    instances = yaml.safe_load(yaml_file)
    
    for name,data in instances.items():
        output_dir = "{}/{}".format(outdir,name)
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
            output_name = "{}-{}".format(name,'-'.join([k[0]+str(v) for (k,v) in zip(size_header,size_list)]))    
            input_file = "{}{}".format(path_prefix,data["path"])
            
            ll = "{}/pla-gen-logs/".format(output_dir)
            if not os.path.exists(ll):
                os.makedirs(ll)
            
            log_path="{}/fr-{}.log".format(ll,output_name)
            err_path="{}/fr-{}.err".format(ll,output_name)

            #print("instance:{}/{}:{}".format(output_dir,output_name,input_file.replace('vmt','ivy')))
            
            cmd = "{} --time-limit={} --real-time-limit={} --space-limit={} python2 ./ic3po/ic3po.py {} --size={} -m fr-pla -o {} -n {}".format(runlim_path,T,R,S,input_file,sizes_str,output_dir,output_name)
            #print(cmd,flush=True)
            
            spl = shlex.split(cmd)
            
            with open(log_path, 'w') as logf, open(err_path, 'w') as errf:
                try:
                    completeRun = subprocess.run(spl, stdout=logf,stderr=errf,timeout=R*1.05)
                except subprocess.TimeoutExpired:
                    print("Error, instance {} reached timeout for size: {}.".format(name,[(k,v) for (k,v) in zip(size_header,size_list)]), flush=True)
                    if len(size_header) == 1:
                        # When there is only one sort, there is no need to
                        # increase the size further, the next will time out as
                        #  well.
                        break 
                    continue
                
