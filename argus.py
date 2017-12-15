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

    def configure(self):
        self.configured = True

    def flush_data(self):
        """
        Flush the collected data to an output file to be saved
        """

    def read_config_file(self, config_file='argus.conf'):
        """
        Read the configuration for the argus daemon from the config file.

        Defaults to reading argus.conf in the current directory
        """

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
