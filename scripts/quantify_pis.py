import shlex
import subprocess
import yaml
import itertools
from math import comb
import os
import sys



T=3600
R=3600
S=32000

outdir = None
path_prefix = None
instance_path= None
runlim_path= None

outdir = None
path_prefix = None
pis_prefix = None

if len(sys.argv) > 1:
    assert (len(sys.argv) > 8)
    instance_path = sys.argv[1]
    path_prefix = sys.argv[2]
    outdir = sys.argv[3]
    pis_prefix = sys.argv[4]
    runlim_path = sys.argv[5]
    T = int(sys.argv[6])
    R = int(sys.argv[7])
    S = int(sys.argv[8])

c = 0
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
            pi_file = "{}/{}/{}/{}.pis".format(pis_prefix,name,output_name,output_name)

            ll = "{}/{}/qi-gen-logs".format(pis_prefix,name) 
            if not os.path.exists(ll):
                os.makedirs(ll)
            
            log_path="{}/qi-{}.log".format(ll,output_name)
            err_path="{}/qi-{}.err".format(ll,output_name)

            if not os.path.isfile(pi_file):
                print('Did not find PI list of {}.'.format(output_name))
                continue

            cmd = "{} --time-limit={} --real-time-limit={} --space-limit={} python2 ./ic3po/ic3po.py {} --size={} -m fr-qi --qi {} -o {} -n {}".format(runlim_path,T,R,S,input_file,sizes_str,pi_file,output_dir,output_name)
            # print(cmd,flush=True)
            
            spl = shlex.split(cmd)
            input_encoded = "\n".join([str(i) for i in size_list]).encode('utf-8')

            with open(log_path, 'w') as logf, open(err_path, 'w') as errf:
                try:
                    completeRun = subprocess.run(spl, input=input_encoded,stdout=logf,stderr=errf,timeout=R*1.05)
                except subprocess.TimeoutExpired:
                    print("Error, instance {} reached timeout for size: {}.".format(name,[(k,v) for (k,v) in zip(size_header,size_list)]), flush=True)
                    if len(size_header) == 1:
                        break # no need to increase the size further, the next will time out as well
                    continue
                
          