import sys
from os import path
import glob



class MinimizerRunStat():
    max_name_width = 0
    header = "{name:{width}s} {status:^8s} {rtime:^8s} {space:^8s} {vars:^8s} {cubes:^8s} {pis:^8s} {pics:^10s} {search:^8s} {sols:^8s}".\
        format(name="Name",width=40,\
            status="status",\
            rtime="time",\
            space="space",\
            vars="#vars",\
            cubes="#cubes",\
            pis="#pis",\
            pics="#pics",\
            search="search?",\
            sols="#sols")
    
    def __init__(self,instance_name) -> None:
        self.name = instance_name
        if len(instance_name) > MinimizerRunStat.max_name_width:
            MinimizerRunStat.max_name_width = len(instance_name)
        self.family = instance_name.split('-')[0]
        self.err_file = '?'
        self.log_file = '?'
        self.space = '?'
        self.rtime = '?'
        self.ctime = '?'
        self.status = '?'
        self.num_vars = '?'
        self.num_cubes = '?'
        self.num_PI = '?'
        self.num_PI_class = '?'
        self.num_solutions = '?'
        self.did_search = '?'
        self.sol_length = '?'
        self.root_length = '?'

    def parse_err_file(self,err_f):
        self.err_file = err_f
        with open(err_f,"r") as err_file:
            for line in err_file:
                if line.startswith("[runlim] status:"):
                    self.status = line.strip().split("\t")[-1]
                    if self.status == "out of time":
                        self.status = "TO"
                elif line.startswith("[runlim] real:"):
                    self.rtime = float(line.strip().split("\t")[-1].split(" ")[0])
                elif line.startswith("[runlim] time:"):
                    self.ctime = float(line.strip().split("\t")[-1].split(" ")[0])
                elif line.startswith("[runlim] space:"):
                    self.space = float(line.strip().split("\t")[-1].split(" ")[0])
    
    def parse_log_file(self,log_f):
        self.log_file = log_f
        with open(log_f,"r") as log_file:
            for line in log_file:
                if line.startswith("Number of input variables:"):
                    self.num_vars = int(line.strip().split(" ")[-1])
                elif line.startswith("Number of input cubes:"):
                    self.num_cubes = int(line.strip().split(" ")[-1])
                elif line.startswith("	Number of PIs:"):
                    self.num_PI = int(line.strip().split(" ")[-1])
                elif line.startswith("	Number of PI-classes:"):
                    self.num_PI_class = int(line.strip().split(" ")[-1])
                elif line.startswith("Root essential:"):
                    if "[]" in line:
                        self.root_essentials = []
                    else:
                        self.root_essentials = line.strip()[17:-1].split(',')
                    
                    self.root_length = len(self.root_essentials)

                elif line.startswith("Root level redundant PIs:"):
                    self.root_redundant = len(line.strip()[27:-1].split(','))
                elif line.startswith("All PIs are root-essential,"):
                    assert (self.num_solutions == '?')
                    self.num_solutions = 1
                    self.did_search = False
                
                    
                elif line.strip().endswith(" found solutions)"):
                    # A solution: [29, 33, 49, 53, 57, 61, 101, 65] (from 1 found solutions)
                    assert (self.num_solutions == '?')
                    self.num_solutions = \
                        int(line.strip().split('(')[-1].split(" ")[1])
                    
                    self.sol_length = len(''.join(line.strip().split("[")[1:]).split("]")[0].split(","))
                    self.did_search = True
        if not self.did_search and self.root_length != '?':
            self.sol_length = self.root_length
    def print_data(self):
        print("{name:{width}s} {status:^8s} {rtime:^8s} {space:^8s} {vars:^8s} {cubes:^8s} {pis:^8s} {pics:^10s} {search:^8s} {sols:^8s}".\
                format(name=self.name,width=40,\
                    status=self.status,\
                    rtime=str(self.rtime),\
                    space=str(self.space),\
                    vars=str(self.num_vars),\
                    cubes=str(self.num_cubes),\
                    pis=str(self.num_PI),\
                    pics="{}/{}".format(str(self.num_PI_class),str(self.sol_length)),\
                    search=str(self.did_search),\
                    sols=str(self.num_solutions))
        )

def main():
    if len(sys.argv) < 2:
        print("Error, root folder of running log files is expected as input argument.")
        sys.exit(1)

    log_path = sys.argv[1]
    files = glob.iglob(log_path + '/*/min-*.log', recursive=True)
    
    data = {}
    for f in files:
        
        instance = path.basename(f)
        mrs = MinimizerRunStat(instance[:-4])
        err_f = "{}.err".format(f[:-4])
        mrs.parse_err_file(err_f)
        mrs.parse_log_file(f)
        data[instance] = mrs
    
    print(MinimizerRunStat.header)
    ordered_instances = sorted(data.keys())
    for k in ordered_instances:
        data[k].print_data()

if __name__ == '__main__':
    main ()
