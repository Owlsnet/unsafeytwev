from flask import Flask, request, render_template_string, Response, send_from_directory, jsonify
import subprocess
import os
import threading
import queue
import time

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
RESULT_FILE = 'result.mp4'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML = '''
<!doctype html>
<title>Live CMD Output</title>
<style>
  body {
    background-color: #2c003e; /* midnight purple */
    color: #a259ff; /* purple text */
    font-family: monospace, monospace;
    padding: 20px;
  }
  #output {
    height: 300px;
    overflow: auto;
    background: #1a0030;
    color: #a259ff;
    padding: 10px;
    white-space: pre-wrap;
  }
  a, button {
    color: #a259ff;
    background: transparent;
    border: 1px solid #a259ff;
    padding: 6px 12px;
    cursor: pointer;
    margin-top: 10px;
    text-decoration: none;
    font-family: monospace;
  }
  button:hover, a:hover {
    background-color: #450078;
  }
</style>
<h2>Upload MP4</h2>
<form id="upload-form" method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept="video/mp4" required>
  <button type="submit">Send</button>
</form>
<pre id="output"></pre>
<div id="download-container" style="display:none;">
  <a id="download-link" href="/download">Download result.mp4</a><br>
  <p id="warning"></p>
  <button id="delete-btn">Delete result.mp4 from server</button>
  <p id="token-seed"></p>
</div>

<script>
const form = document.getElementById('upload-form');
const output = document.getElementById('output');
const downloadContainer = document.getElementById('download-container');
const downloadLink = document.getElementById('download-link');
const warning = document.getElementById('warning');
const deleteBtn = document.getElementById('delete-btn');
const tokenSeedElem = document.getElementById('token-seed');

form.onsubmit = async e => {
  e.preventDefault();
  output.textContent = '';
  downloadContainer.style.display = 'none';
  warning.textContent = '';
  tokenSeedElem.textContent = '';

  const data = new FormData(form);
  const response = await fetch('/start_process', { method: 'POST', body: data });
  if (!response.ok) {
    output.textContent = 'Failed to start process';
    return;
  }

  const eventSource = new EventSource('/stream_output');
  eventSource.onmessage = e => {
    if (e.data === '[DONE]') {
      eventSource.close();
      downloadContainer.style.display = 'block';
      warning.textContent = 'After downloading, please press the button below to delete result.mp4 from the server.';
      fetch('/get_token_seed').then(res => res.text()).then(seed => {
        tokenSeedElem.textContent = 'Token seed: ' + seed;
      });
      return;
    }
    output.textContent += e.data + '\\n';
    output.scrollTop = output.scrollHeight;
  }
}

deleteBtn.onclick = async () => {
  const res = await fetch('/delete_result', { method: 'POST' });
  if (res.ok) {
    warning.textContent = 'result.mp4 deleted from server.';
    downloadLink.style.display = 'none';
    deleteBtn.style.display = 'none';
  } else {
    warning.textContent = 'Failed to delete result.mp4 from server.';
  }
};
</script>
'''

job_queue = queue.Queue()
job_lock = threading.Lock()
current_output_queue = queue.Queue()
token_seed = ""
current_processing = False

def process_job(filepath):
    global token_seed, current_processing
    token_seed = ""
    current_processing = True
   cmd = ['python', 'run.py', filepath]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)

    for line in iter(proc.stdout.readline, ''):
        if "Token (Seed):" in line:
            token_seed = line.strip()
        current_output_queue.put(line.rstrip())
    proc.stdout.close()
    proc.wait()
    current_processing = False

def worker():
    while True:
        filepath = job_queue.get()
        if filepath is None:
            break
        process_job(filepath)
        job_queue.task_done()

threading.Thread(target=worker, daemon=True).start()

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/start_process', methods=['POST'])
def start_process():
    file = request.files.get('file')
    if not file:
        return "No file uploaded", 400
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    job_queue.put(filepath)
    return ('', 204)

@app.route('/stream_output')
def stream_output():
    def event_stream():
        while True:
            if not current_processing and current_output_queue.empty():
                yield 'data: [DONE]\n\n'
                break
            try:
                line = current_output_queue.get(timeout=0.1)
                yield f'data: {line}\n\n'
            except queue.Empty:
                time.sleep(0.1)
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/download')
def download():
    return send_from_directory(directory='.', path=RESULT_FILE, as_attachment=True)

@app.route('/get_token_seed')
def get_token_seed():
    return token_seed or "No token seed found"

@app.route('/delete_result', methods=['POST'])
def delete_result():
    try:
        if os.path.exists(RESULT_FILE):
            os.remove(RESULT_FILE)
        return jsonify({"status": "deleted"})
    except Exception:
        return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
