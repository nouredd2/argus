# Argus

A collection of tools to monitor the performance of an HTTP server under SYN and connection flood attacks. 

## Tools

Argus is composed of two tools:

* Argus.py: A python daemon that monitors CPU usage, memory usage, and TCP SYN challenges sent, received, and failed
* Argus module: A Linux kernel module that monitors the size of a TCP socket's listen and accept queues

## Prerequisites

`argus.py` requires the presence of the `psutil` python package, you can install it using `pip`:

```
pip install psutil
```

To run the module, you need the standard C development tools (`gcc`, `make`, etc.) as well as the running kernel
headers. On an ubuntu machine, you can install them using

```
sudo apt install -y build-essential linux-headers-$(uname -r)
```

## Compiling and installing the module

Before compiling the module, select the appropriate polling interval. To do so, edit the file `pmonitor.c`
and change the value of the macro `LOG_INTERVAL` on line 44. This value is in milliseconds.

```C
#define LOG_INTERVAL 1000 /* for 1 second intervals */
```

To use the kernel module, you must first compile and install it. From the module's top directory use

```
make
```

and then insert the module into the kernel using

```
sudo insmod pmonitor.ko
```

## Using the kernel monitor

After inerting it, the module will do nothing, it will be dormant. To activate it,  you first have to provide
it with the process id (`pid`) of the Apache2 process running on the machine. The module will use that to
detect the socket bound to port 80. Note that the module assumes that the http process is running on port 80.
For what follows (with the exception of reading from `procfs`), you need to be root. To pass the `pid` to
the module, use the `procfs` interface

```
echo "P 1234" > /proc/pmonitor
```
and replace `1234` with the appropriate `pid`.

The module now is ready to run, the activate it use

```
echo "1" > /proc/pmonitor
```

You can query the module for the current observed values at any time using `procfs` as follows

```
cat /proc/pmonitor
```

To deactivate the module use

```
echo "0" > /proc/pmonitor
```

And finally to removed the module and cleanup use

```
rmmod pmonitor
```

Note that after removing the module, the content of the file will be lost. To retain that, after deactivating
the module, read its content using `cat` and then save it to a file

```
cat /proc/pmonitor > data.txt
```

