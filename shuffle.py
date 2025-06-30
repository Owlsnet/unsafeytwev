#!/usr/bin/env python3
import imageio
import numpy as np
from PIL import Image
import ffmpeg
import os
import sys
import argparse
import re

parser = argparse.ArgumentParser()
parser.add_argument('input_video', help='Input MP4 file')
args = parser.parse_args()

INPUT_VIDEO_PATH = args.input_video
EXTRA_TEXTURE_PATH = "offsets/offset_map.png"
FINAL_OUTPUT_PATH = "temp_output.mp4"
TEMP_VIDEO_ONLY_PATH = "output_video_only.mp4"

# Load extra texture once (offset map)
try:
    extra_img = Image.open(EXTRA_TEXTURE_PATH).convert("RGBA")
    extra_array = np.array(extra_img)
except FileNotFoundError:
    print(f"Error: Extra texture file not found at {EXTRA_TEXTURE_PATH}")
    sys.exit(1)

# Function to apply a simple CPU shader-like effect on each frame
def apply_offset_map(frame, offset_map):
    # frame: numpy array HxWx3 (RGB)
    # offset_map: numpy array HxWx4 (RGBA)

    # For demonstration, shift pixels horizontally by amount from red channel of offset_map
    shift_amount = (offset_map[:, :, 0].astype(np.int32) % 10) - 5  # shift range [-5..4]
    height, width, _ = frame.shape
    output = np.zeros_like(frame)

    for y in range(height):
        for x in range(width):
            new_x = x + shift_amount[y, x]
            if new_x < 0:
                new_x = 0
            elif new_x >= width:
                new_x = width - 1
            output[y, x] = frame[y, new_x]
    return output

# Open input video reader
try:
    reader = imageio.get_reader(INPUT_VIDEO_PATH, 'ffmpeg')
    meta = reader.get_meta_data()
    fps = meta.get('fps', 30)
    width, height = meta.get('size', (640, 480))
except Exception as e:
    print(f"Failed to open video {INPUT_VIDEO_PATH}: {e}")
    sys.exit(1)

# Setup output writer
try:
    writer = imageio.get_writer(TEMP_VIDEO_ONLY_PATH, fps=fps, codec='libx264', quality=8)
except Exception as e:
    print(f"Failed to create video writer: {e}")
    sys.exit(1)

# Process frames
print(f"Processing video frames from {INPUT_VIDEO_PATH}...")
frame_count = 0
token_seed = None

try:
    for frame in reader:
        # frame shape: (H, W, 3)
        # Ensure frame matches expected size
        frame_pil = Image.fromarray(frame)
        if frame_pil.size != (width, height):
            frame_pil = frame_pil.resize((width, height), Image.LANCZOS)
            frame = np.array(frame_pil)

        # Apply offset map effect
        processed_frame = apply_offset_map(frame, extra_array)

        writer.append_data(processed_frame)
        frame_count += 1

except Exception as e:
    print(f"Error processing frames: {e}")
    writer.close()
    reader.close()
    if os.path.exists(TEMP_VIDEO_ONLY_PATH):
        os.remove(TEMP_VIDEO_ONLY_PATH)
    sys.exit(1)

writer.close()
reader.close()
print(f"Finished processing {frame_count} frames.")

# Extract token seed from offsets/offset_map.png metadata or filename (simulate)
# Since original token seed comes from your batch, here just fake it from filename or a fixed value
token_seed = "FAKESEED1234567890"  # Replace this logic if you have actual seed extraction

# Merge processed video (no audio) with original audio using ffmpeg-python
try:
    video_stream = ffmpeg.input(TEMP_VIDEO_ONLY_PATH)
    audio_stream = ffmpeg.input(INPUT_VIDEO_PATH).audio
    ffmpeg.output(video_stream.video, audio_stream, FINAL_OUTPUT_PATH, vcodec='copy', acodec='copy', shortest=None).run(overwrite_output=True)
    print(f"Final output saved to {FINAL_OUTPUT_PATH}")
except ffmpeg.Error as e:
    print("ffmpeg error during merging:", e.stderr.decode('utf8'))
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error during merging: {e}")
    sys.exit(1)

if os.path.exists(TEMP_VIDEO_ONLY_PATH):
    os.remove(TEMP_VIDEO_ONLY_PATH)

print("Processing complete.")
print(f"Token (Seed): {token_seed}")
