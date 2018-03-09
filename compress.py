import os, bz2

def compress():
    # Get the file that the daemon wrote to
    with open('argus.conf', 'r') as conf_file:
        for line in conf_file:
            if 'output_file' in line:
                file = line.strip().split('=')[1].strip()
                # check if it starts with '/' then take the path as it is,
                # otherwise make it relative to the current directory
                if file[0] == '/':
                    data_file = file
                else:
                    data_file = os.getcwd() + '/' + file

    with open(data_file, 'r') as data:
        compressed_data = bz2.compress(data.read())

    with open('daemon_data.bz2', 'w') as out:
        out.write(compressed_data)


if __name__ == "__main__":
    compress()