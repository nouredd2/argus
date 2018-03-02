#!/usr/bin/env python

import sys,time,os
from daemon import Daemon
# from apache_manager import ApacheManager
import subprocess
import psutil


class Argus(Daemon):
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null',
                 stderr='/dev/null/', config_file='argus.conf'):
        super(Argus, self).__init__(pidfile, stdin, stdout, stderr)
        self.config_file = config_file
        self.configured = False
        self.metrics_names = set(['busy_workers',
                            'bytes_per_request',
                            'bytes_per_second',
                            'cpu_load',
                            'idle_workers',
                            'requests_per_second',
                            'total_accesses',
                            'total_traffic',
                            'uptime'])
        self.sampling_rate = 1.0 / 2
        self.flush_interval = 5.0
        self.manager = None
        self.last_flush = 0.0
        self.write_header = True
        self.cwd = os.getcwd()
        self.output_file = self.cwd + '/argus.out'


    def flush_data(self, d):
        """
        Flush the collected data to an output file to be saved
        """
        try:
            with open(self.output_file, 'a+') as f:
                if self.write_header:
                    f.write ("Timestamp ")
                    for title in self.metrics_names:
                        f.write(title + " ")
                    f.write("\n")
                    self.write_header = False

                for timestamp,metrics in d.iteritems():
                    f.write("%lf " % timestamp)
                    if isinstance(metrics, dict):
                        for key,val in metrics.iteritems():
                            f.write(val)
                    elif isinstance(metrics, list):
                        for val in metrics:
                            f.write(str(val))
                    f.write("\n")

                self.last_flush = time.time()
        except IOError:
            sys.stderr.write("Error opening output file %s\n" % self.output_file)
            self.stop()


    def apply_config_option(self, o, v):
        """
        Apply the configuration option read from the config file
        """
        if o == 'output_file':
            # check if it starts with '/' then take the path as it is,
            # otherwise make it relative to the current directory
            if v[0] == '/':
                self.output_file = v
            else:
                self.output_file = self.cwd + '/' + v
        elif o == 'sampling_rate':
            self.sampling_rate = 1.0 / int(v)
        elif o == 'flush_interval':
            self.flush_interval = float(v)
        else:
            sys.stderr.write("unrecognized configuration option %s\n" % o)
            self.stop()


    def configure(self, config_file='argus.conf'):
        """
        Read the configuration for the argus daemon from the config file.
        Defaults to reading argus.conf in the current directory
        """
        try:
            with open(config_file, 'r') as f:
                opts = [line.rstrip('\n') for line in f]
        except IOError:
            sys.stderr.write("Cannot read config file %s, make sure it exists.\n" % config_file)
            # Not sure this needs to be here, since the daemon hasn't even started yet
            self.stop()

        for line in opts:
            # Skip comments and empty lines
            if len(line) <= 1 or line[0] == '#': continue

            option, value = [x.strip() for x in line.split('=')]
            self.apply_config_option(option, value)

        # Don't allow writing data more often than we capture it
        if self.sampling_rate > self.flush_interval:
            self.flush_interval = self.sampling_rate

        self.configured = True


    # override the run method
    def run(self):
        if not self.configured:
            sys.stderr.write("Argus monitoring agent is not configured.\n")
            self.stop()

        data = dict()
        while True:
            # REPLACE -p 2948 WITH PID OF DAEMON
            # subprocess.call(["top", "-n1"], stdout=file(self.output_file, 'w+'))

            # metrics = {proc.name()+'a':proc.name() for proc in psutil.process_iter()}
            # print(psutil.virtual_memory())
            metrics = [psutil.cpu_percent(), psutil.virtual_memory().active]

            timestamp = time.time()
            data[timestamp] = metrics

            time.sleep(self.sampling_rate)

            # check if should be flushing to file
            if self.last_flush == 0.0:
                self.last_flush = timestamp
            elif (timestamp - self.last_flush) > self.flush_interval:
                self.flush_data(data)
                data.clear()


    def start(self):
        self.configure()
        super(Argus, self).start()


    def stop(self):
        super(Argus, self).stop()
        # Remove this later if it causes problems
        sys.exit(2)


if __name__ == "__main__":
    daemon = Argus('/tmp/daemon-example.pid', stdout='/tmp/argus.out', stderr='/tmp/argus.err')

    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknow command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
