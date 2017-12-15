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
        self.metrics = set(['busy_workers',
                            'bytes_per_request',
                            'bytes_per_second',
                            'cpu_load',
                            'idle_workers',
                            'requests_per_second',
                            'total_accesses',
                            'total_traffic',
                            'uptime'])


    def flush_data(self):
        """
        Flush the collected data to an output file to be saved
        """


    def apply_config_option(self, o, v):
        """
        Apply the configuration option read from the config file
        """
        if o == 'output_file':
            self.output_file = v
        else:
            sys.stderr.write("unrecognized configuration option %s\n" % o)
            sys.exit(1)


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
            sys.exit(1)

        opts = [x.strip() for x in config_opts]

        for line in opts:
            values = line.split()

            option = values[0]
            value = values[1]

            self.apply_config_option(option, value)

        self.configured = True

    # override the run method
    def run(self):
        manager = ApacheManager()
        data = dict()
        while True:
            manager.refresh()
            metrics = manager.server_metrics

            # we got the dictionary, now save everything
            timestamp = time.now()
            data[timestamp] = metrics
            time.sleep(0.5)


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
