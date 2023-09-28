import sys
from os import path
import glob


class RunStat():
    def __init__(self,instance_name) -> None:
        self.name = instance_name
        self.family = instance_name.split('-')[0]
        self.err_file = '?'
        self.space = 0
        self.rtime = 0
        self.ctime = 0
        self.status = '?'

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

class StepStats():
    def __init__(self) -> None:
        self.space = 0
        self.rtime = 0
        self.ctime = 0

    def add(self, space, rtime, ctime):
        self.space = max(self.space, space)
        self.rtime += rtime
        self.ctime += ctime

class Stats():
    header = "{name},{space},{total},{pla},{pi},{qi},{min}".\
                format(name="Protocol",\
                    space="space",\
                    total="time-total",\
                    pla="time-pla",\
                    pi="time-pi",\
                    qi="time-qi",\
                    min="time-min")

    def __init__(self, instance) -> None:
        self.instance = instance
        self.stats = {}
        self.stats["pla"] = StepStats()
        self.stats["pi"] = StepStats()
        self.stats["qi"] = StepStats()
        self.stats["min"] = StepStats()
        self.stats["total"] = StepStats()

    def add(self, space, rtime, ctime, step):
        self.stats[step].add(space, rtime, ctime)
        self.stats["total"].add(space, rtime, ctime)

    def print_data(self):
        print("%s,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f" %
                (   self.instance,\
                    self.stats["total"].space,\
                    self.stats["total"].ctime,\
                    self.stats["pla"].ctime,\
                    self.stats["pi"].ctime,\
                    self.stats["qi"].ctime,\
                    self.stats["min"].ctime)
        )

def get_instance_name(name):
    sanitized = ""
    for word in name.split('-'):
        if sanitized != "" and any(i.isdigit() for i in word):
            break
        if sanitized != "":
            sanitized += "-"
        sanitized += word
    return sanitized

def main():
    if len(sys.argv) < 2:
        print("Error, root folder of running log files is expected as input argument.")
        sys.exit(1)

    log_path = sys.argv[1]
    stats = {}

    files = glob.iglob(log_path + '/*/pla-gen-logs/*.err')
    for err_f in files:
        instance = get_instance_name(path.basename(err_f)[3:-4])
        mrs = RunStat(instance)
        mrs.parse_err_file(err_f)
        if instance not in stats:
            stats[instance] = Stats(instance)
        stats[instance].add(mrs.space, mrs.rtime, mrs.ctime, "pla")

    files = glob.iglob(log_path + '/*/*/gen-pis-*.err')
    for err_f in files:
        instance = get_instance_name(path.basename(err_f)[8:-4])
        mrs = RunStat(instance)
        mrs.parse_err_file(err_f)
        if instance not in stats:
            stats[instance] = Stats(instance)
        stats[instance].add(mrs.space, mrs.rtime, mrs.ctime, "pi")

    files = glob.iglob(log_path + '/*/qi-gen-logs/*.err')
    for err_f in files:
        instance = get_instance_name(path.basename(err_f)[3:-4])
        mrs = RunStat(instance)
        mrs.parse_err_file(err_f)
        if instance not in stats:
            stats[instance] = Stats(instance)
        stats[instance].add(mrs.space, mrs.rtime, mrs.ctime, "qi")

    files = glob.iglob(log_path + '/*/*/min-*.err')
    for err_f in files:
        instance = get_instance_name(path.basename(err_f)[4:-4])
        mrs = RunStat(instance)
        mrs.parse_err_file(err_f)
        if instance not in stats:
            stats[instance] = Stats(instance)
        stats[instance].add(mrs.space, mrs.rtime, mrs.ctime, "min")

    print(Stats.header)
    ordered_instances = sorted(stats.keys())
    for k in ordered_instances:
        stats[k].print_data()

if __name__ == '__main__':
    main ()
