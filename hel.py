#!/usr/bin/env python

import sys
import time
import subprocess
from daemon import Daemon


class Hel(Daemon):
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null',
                 stderr='/dev/null/'):
        super(Hel, self).__init__(pidfile, stdin, stdout, stderr)
        self.proc_file = "/proc/pmonitor"
        self.interval = 20  # run every  20 seconds by default

    def change_difficulty(self, k, m):
        cmd = "sudo /proj/ILLpuzzle/puzzles-utils/scripts/set_difficulty.sh {} {}".format(k,m)
        subprocess.call(cmd.split(' '))
        sys.stdout.write("Changing puzzles difficulty to ({},{})".format(k,m))

    def run(self):
        while True:
            cat = subprocess.Popen(('cat', self.proc_file), stdout=subprocess.PIPE)
            module_out = subprocess.check_output(('tail', '-n', '1'), stdin=cat.stdin).decode('ascii')

            line = module_out.strip().split(';')[-1]
            accept_queue_len = int(line)

            if accept_queue_len < 1024:
                self.change_difficulty(2, 14)
            elif accept_queue_len < 2048:
                self.change_difficulty(2, 15)
            elif accept_queue_len < 3072:
                self.change_difficulty(2, 16)
            else:
                self.change_difficulty(2, 17)

            time.sleep(self.interval)

    def start(self):
        super(Hel, self).start()

    def stop(self):
        super(Hel, self).stop()
        # Remove this later if it causes problems
        sys.exit(2)


if __name__ == "__main__":
    daemon = Hel('/tmp/hel.pid', stdout='/tmp/hel.log', stderr='/tmp/hel.stderr')

    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print("Unknown command")
            sys.exit(2)
        sys.exit(0)
    else:
        print("usage: %s start|stop|restart" % sys.argv[0])
        sys.exit(2)
