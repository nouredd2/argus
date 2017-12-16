#!/usr/bin/env python

import sys,time
from daemon import Daemon
from apache_manager import ApacheManager


class Argus(Daemon):
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null',
                 stderr='/dev/null/', config_file='argus.conf'):
        super(Argus, self).__init__(pidfile, stdin, stdout, stderr)
        self.config_file = config_file
        self.configured = False
        self.output_file = 'argus.out'
        self.metrics_names = set(['busy_workers',
                            'bytes_per_request',
                            'bytes_per_second',
                            'cpu_load',
                            'idle_workers',
                            'requests_per_second',
                            'total_accesses',
                            'total_traffic',
                            'uptime'])
        self.sampling_rate = 2
        self.flush_interval = 10
        self.manager = None
        self.last_flush = 0.0
        self.write_header = True


    def flush_data(self, d):
        """
        Flush the collected data to an output file to be saved
        """
        try:
            f = open(self.output_file, 'a+')
        except IOError:
            sys.stderr.write("Error opening output file %s\n" %
                             self.output_file)
            f = None

        if f is None:
            self.stop()

        if self.write_header:
            f.write ("Timestamp ")
            for title in self.metrics_names:
                f.write(title + " ")
            f.write("\n")
            self.write_header = False

        for ts,metrics in d.iteritems():
            f.write("%lf " % ts)
            for key,val in metrics.iteritems():
                f.write("%lf " % val)
            f.write("\n")

        f.close()
        self.last_flush = time.now()


    def apply_config_option(self, o, v):
        """
        Apply the configuration option read from the config file
        """
        if o == 'output_file':
            self.output_file = v
        elif o == 'sampling_rate':
            self.sampling_rate = v
        elif o == 'flush_interval':
            self.flush_interval = v
        else:
            sys.stderr.write("unrecognized configuration option %s\n" % o)
            self.stop()


    def configure(self, config_file='argus.conf'):
        """
        Read the configuration for the argus daemon from the config file.

        Defaults to reading argus.conf in the current directory
        """
        try:
            f = file(config_file, 'r')
            config_opts = f.readlines()
            f.close()
        except IOError:
            config_opts = None

        if config_opts is None:
            sys.stderr.write("Cannot read config file %s\n" % config_file)
            self.stop()

        opts = [x.strip() for x in config_opts]

        for line in opts:
            values = line.split()

            option = values[0]
            value = values[1]

            self.apply_config_option(option, value)

        self.configured = True


    def start(self):
        self.configure()

        super(Argus, self).start()

    # override the run method
    def run(self):
        if not self.configured:
            sys.stderr.write("Argus monitoring agent is not configured.\n")
            self.stop()

        self.manager = ApacheManager()
        data = dict()
        while True:
            self.manager.refresh()
            metrics = self.manager.server_metrics

            # we got the dictionary, now save everything
            timestamp = time.now()
            data[timestamp] = metrics
            time.sleep(1.0 / self.sampling_rate)

            # check if should be flushing to file
            if self.last_flush == 0.0:
                self.last_flush = timestamp
            else:
                if (timestamp - self.last_flush) > self.flush_interval:
                    self.flush_data(data)
                    data.clear()


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
