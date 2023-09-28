import subprocess
import sys
import yaml
import os
import io
import shutil
import time

instance_path = "instances.yaml"
outdir = "output"
summarydir = "output/summary"
logsdir = "output/logs"
T = "3600"
R = "3600"
S = "64000"

if not os.path.exists(summarydir):
    os.makedirs(summarydir)
if not os.path.exists(logsdir):
    os.makedirs(logsdir)

processes = {}
running = set()
finished = []

with open(instance_path,'r') as yaml_file:
    instances = yaml.safe_load(yaml_file)
    
    for name,data in instances.items():
        output_dir = "{}/{}".format(outdir,name)
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir)
        output_yaml = "{}/{}.yaml".format(output_dir,name)
        output_data = {name: data}
        with io.open(output_yaml, 'w', encoding='utf8') as outfile:
            yaml.dump(output_data, outfile, default_flow_style=False, allow_unicode=True)
        cmd = "./scripts/run_qsm.sh {} {} {} {} {} > {}/{}-log.txt".format(name, outdir, T, R, S, logsdir, name)
        proc = subprocess.Popen(cmd, shell=True)
        processes[name] = proc
        running.add(name)
        print("Deployed {}".format(name))
        time.sleep(5)
    total = len(processes)
    print("Deployed {} runs".format(len(processes)))

    while running:
        time.sleep(5)
        newly_completed = []
        for name in running:
            proc = processes[name]
            ret_code = proc.poll()
            if ret_code is not None:
                newly_completed.append(name)
                finished.append(name)
                print("[{} / {}] Finished {} with code {}".format(len(finished), len(processes), name, ret_code))
        for name in newly_completed:
            running.remove(name)


