#!/usr/bin/env python

import sys,time
from daemon import Daemon
from apache_manager import ApacheManager


class Argus(Daemon):
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
        elif 'test':
            daemon.run()
        else:
            print "Unknow command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)