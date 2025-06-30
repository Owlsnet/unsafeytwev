import sys
import subprocess
import os

def run_command(cmd):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end='', flush=True)  # Ensure CMD output streams to Flask
        if "Token (Seed):" in line:
            print(line.strip(), flush=True)  # Your Flask app will capture this
    process.wait()

def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]

    # Step 1: python generate.py
    run_command(['python', 'generate.py'])

    # Step 2: python shuffle.py <input_file>
    run_command(['python', 'shuffle.py', input_file])

    # Step 3: python sound.py temp_output.mp4 result.mp4
    run_command(['python', 'sound.py', 'temp_output.mp4', 'result.mp4'])

    # Step 4: delete temp_output.mp4
    try:
        os.remove('temp_output.mp4')
        print("Deleted temp_output.mp4")
    except FileNotFoundError:
        print("temp_output.mp4 not found, skipping delete.")

if __name__ == '__main__':
    main()
