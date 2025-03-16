import os
import sys
import subprocess

script_path = os.path.join(os.path.dirname(__file__), '../main.py')
args = ['python', '-u', script_path] + sys.argv[1:]
process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

with process.stdout:
    for line in iter(process.stdout.readline, b''):
        sys.stdout.write(line.decode())
        sys.stdout.flush()
process.wait()