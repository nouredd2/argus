#!/usr/bin/env python

import sys
import time
import subprocess
import math
from daemon import Daemon


class Hel(Daemon):
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null',
                 stderr='/dev/null/'):
        super(Hel, self).__init__(pidfile, stdin, stdout, stderr)
        self.proc_file = "/proc/pmonitor"
        self.interval = 20  # run every  20 seconds by default

    def change_difficulty(self, k, m):
        cmd = "sudo /proj/ILLpuzzle/puzzles-utils/scripts/set_difficulty.sh {} {}".format(k, m)
        subprocess.call(cmd.split(' '))
        sys.stdout.write("{}: Changing puzzles difficulty to ({},{})\n".format(time.ctime(), k, m))

    def run(self):
        while True:
            cat = subprocess.Popen(('cat', self.proc_file), stdout=subprocess.PIPE)
            module_out = subprocess.check_output(('tail', '-n', '1'), stdin=cat.stdout).decode('ascii')

            line = module_out.strip().split(';')[-1]
            try:
                accept_queue_len = int(line)

                # should probably do this by bitwise manipulation!
                if accept_queue_len > 0:
                    msb = math.ceil(math.log(accept_queue_len, 2))
                else:
                    msb = 0

                if accept_queue_len >= 4096:
                    self.change_difficulty(2, 17)
                else:
                    self.change_difficulty(2, msb + 5)
            except:
                sys.stderr.write("{}: Got {} from the module\n".format(time.ctime(), line))
            finally:
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
