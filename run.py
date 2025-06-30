import sys
import subprocess

input_file = sys.argv[1]
output_file = 'result.mp4'

cmd = ['ffmpeg', '-i', input_file, '-c:v', 'libx264', '-preset', 'fast', '-crf', '22', output_file]
subprocess.run(cmd, check=True)
