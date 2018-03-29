import os, bz2


def compress():
    data_file = ""
    # Get the file that the daemon wrote to
    with open('argus.conf', 'r') as conf_file:
        for line in conf_file:
            if 'output_file' in line:
                file_name = line.strip().split('=')[1].strip()
                # check if it starts with '/' then take the path as it is,
                # otherwise make it relative to the current directory
                if file_name[0] == '/':
                    data_file = file_name
                else:
                    data_file = os.getcwd() + '/' + file_name

    with open(data_file, 'r') as data:
        compressed_data = bz2.compress(data.read())

    with open('daemon_data.bz2', 'w') as out:
        out.write(compressed_data)


if __name__ == "__main__":
    compress()
