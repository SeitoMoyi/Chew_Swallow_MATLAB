# app.py
import os
import numpy as np
from flask import Flask, render_template, jsonify, request
from delsys_handler import DelsysDataHandler
import threading
import time
import scipy.io
import collections
import datetime
import queue  # Required for queue.Empty exception
import tkinter as tk
from tkinter import filedialog
import sys

def select_save_directory():
    """Open a dialog to select the save directory before starting the app."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.attributes('-topmost', True)  # Make the dialog topmost
    
    save_dir = filedialog.askdirectory(
        title="Select directory to save EMG recordings",
        initialdir="./recordings"  # Default directory
    )
    
    root.destroy()
    
    if not save_dir:
        print("No directory selected. Exiting.")
        sys.exit(0)
        
    return save_dir

app = Flask(__name__)

# --- Configuration ---
HOST_IP = 'localhost'
NUM_SENSORS = 16
SAMPLING_RATE = 2000.0

# Let user select save directory before starting
SAVE_DIRECTORY = select_save_directory()
METADATA_DIRECTORY = os.path.join(SAVE_DIRECTORY, "metadata")
STRUCTS_DIRECTORY = os.path.join(SAVE_DIRECTORY, "structs")
os.makedirs(SAVE_DIRECTORY, exist_ok=True)
os.makedirs(METADATA_DIRECTORY, exist_ok=True)
os.makedirs(STRUCTS_DIRECTORY, exist_ok=True)

# --- Global State ---
handler = None
recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
recording_lock = threading.Lock()
is_recording = False
start_time = None

# --- Recording Session Info ---
recording_session_start_time = None
trial_counter = 1

# --- Live Data Buffering for GUI ---
LIVE_BUFFER_CHUNKS = 10
live_data_buffers = [collections.deque(maxlen=LIVE_BUFFER_CHUNKS) for _ in range(NUM_SENSORS)]
live_data_lock = threading.Lock()

# --- Helper Functions ---
def generate_timestamps(num_samples):
    """Generate timestamps based on start_time and sampling rate."""
    if start_time is None:
        return np.zeros(num_samples)
    timestamps = start_time + np.arange(num_samples) / SAMPLING_RATE
    return timestamps

def recording_worker():
    """Worker thread to read data from the handler's queue while recording."""
    global is_recording, recording_data_buffer, start_time, live_data_buffers
    local_sample_count = 0
    print("Recording worker started.")
    try:
        while is_recording and handler and handler.streaming:
            try:
                processed_data = handler.output_queue.get(timeout=1.0)
                channel_id = processed_data['channel']
                samples = processed_data['samples']
                muscle_label = processed_data.get('muscle_label', f'Ch{channel_id}')

                with recording_lock:
                    if is_recording:
                        recording_data_buffer[channel_id + 1].extend(samples)
                        local_sample_count += len(samples)
                        if start_time is None and local_sample_count == len(samples):
                             start_time = time.time()
                             print(f"Recording start time set: {start_time}")

                with live_data_lock:
                    if is_recording:
                        live_data_buffers[channel_id].append({
                            'samples': samples.tolist(),
                            'label': muscle_label
                        })

            except queue.Empty:
                 continue
            except Exception as e:
                 print(f"Error in recording worker loop: {e}")
                 break
    except Exception as e:
         print(f"Unexpected error in recording worker: {e}")
    finally:
        print("Recording worker stopped.")

def start_delsys_recording():
    """Starts the Delsys data handler and the recording worker thread."""
    global handler, is_recording, recording_data_buffer, start_time, live_data_buffers, recording_session_start_time, trial_counter
    try:
        with recording_lock:
            if is_recording:
                return False, "Recording already in progress."

            for i in range(len(recording_data_buffer)):
                recording_data_buffer[i].clear()
            start_time = None

            with live_data_lock:
                for buffer in live_data_buffers:
                    buffer.clear()

            if handler is not None:
                try:
                    handler.stop_streaming()
                except:
                    pass
                handler = None

            # Initialize session time and trial counter if needed
            if recording_session_start_time is None:
                recording_session_start_time = datetime.datetime.now()
                trial_counter = 1

            handler = DelsysDataHandler(host_ip=HOST_IP, num_sensors=NUM_SENSORS, sampling_rate=SAMPLING_RATE)

            if handler.start_streaming():
                is_recording = True
                worker_thread = threading.Thread(target=recording_worker, daemon=True)
                worker_thread.start()
                return True, "Recording started."
            else:
                is_recording = False
                try:
                    handler.stop_streaming()
                except:
                    pass
                handler = None
                return False, "Failed to start Delsys streaming."

    except Exception as e:
        is_recording = False
        if handler:
            try:
                handler.stop_streaming()
            except:
                pass
            handler = None
        return False, f"Error starting recording: {str(e)}"

def stop_delsys_recording():
    """Stops the Delsys data handler and saves the recorded data."""
    global handler, is_recording, recording_data_buffer, start_time, trial_counter
    try:
        with recording_lock:
            if not is_recording:
                return False, "No recording in progress."

            is_recording = False
            print("Recording flag set to False.")

        time.sleep(0.2)

        if handler:
            print("Stopping Delsys handler...")
            handler.stop_streaming()
            handler = None

        with recording_lock:
             sample_counts = [len(recording_data_buffer[i]) for i in range(1, NUM_SENSORS + 1)]
             if not sample_counts or all(count == 0 for count in sample_counts):
                 recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
                 start_time = None
                 return False, "Recording stopped, but no data was captured."

             min_samples = min(sample_counts)
             print(f"Minimum samples across channels: {min_samples}")

             if min_samples == 0:
                 recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
                 start_time = None
                 return False, "Recording stopped, but no data was captured (after trimming)."

             timestamps = generate_timestamps(min_samples)
             recording_data_buffer[0] = timestamps.tolist()

             final_data_arrays = []
             for i in range(NUM_SENSORS + 1):
                 buffer_data = recording_data_buffer[i]
                 if len(buffer_data) > min_samples:
                     buffer_data = buffer_data[:min_samples]
                 elif len(buffer_data) < min_samples:
                     buffer_data.extend([0.0] * (min_samples - len(buffer_data)))
                     print(f"Warning: Padding channel {i-1} data.")

                 np_array = np.array(buffer_data, dtype=np.float64)
                 final_data_arrays.append(np_array)

             recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
             start_time = None

        interleaved_matrix = np.vstack(final_data_arrays)

        # --- Structured File Naming ---
        global recording_session_start_time, trial_counter
        if recording_session_start_time is None:
             recording_session_start_time = datetime.datetime.now()

        timestamp_str = recording_session_start_time.strftime("%Y%m%d_%H%M%S")
        trial_str = f"{trial_counter:04d}"

        filename_base = f"{timestamp_str}_Trl{trial_str}"
        bin_filename = os.path.join(SAVE_DIRECTORY, f"{filename_base}.bin")
        meta_filename = os.path.join(METADATA_DIRECTORY, f"{timestamp_str}_METADATATrl{trial_str}.mat")

        try:
            interleaved_matrix.tofile(bin_filename)
            print(f"Binary data saved to {bin_filename}")
        except Exception as e:
            return False, f"Error saving binary file: {e}"

        try:
            meta_data = {}
            meta_data['emg_ch_number'] = np.array(range(1, NUM_SENSORS + 1))
            meta_data['fs'] = float(SAMPLING_RATE)
            meta_data['total_analog_in_ch'] = float(NUM_SENSORS)
            if handler and hasattr(handler, 'muscle_labels'):
                meta_data['musc_labels'] = handler.muscle_labels
            else:
                meta_data['musc_labels'] = [
                     'L-TIBI', 'L-GAST', 'L-RECT-DIST', 'L-RECT-PROX', 'L-VAST-LATE',
                     'R-TIBI', 'R-GAST', 'R-RECT-DIST', 'R-RECT-PROX', 'R-VAST-LATE',
                     'L-SEMI', 'R-SEMI', 'NC', 'NC', 'L-BICEP-FEMO', 'R-BICEP-FEMO'
                ]
            meta_data['session_date'] = recording_session_start_time.strftime("%Y-%m-%d")
            meta_data['session_time'] = recording_session_start_time.strftime("%H:%M:%S")
            meta_data['trial_number'] = int(trial_counter)

            scipy.io.savemat(meta_filename, {'meta_data': meta_data})
            print(f"Metadata saved to {meta_filename}")
        except Exception as e:
             print(f"Warning: Could not save metadata: {e}")

        # Increment trial counter for the next recording
        trial_counter += 1

        return True, f"Recording saved successfully ({min_samples} samples)."

    except Exception as e:
        with recording_lock:
            recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
            start_time = None
        if handler:
            try:
                handler.stop_streaming()
            except:
                pass
            handler = None
        return False, f"Error stopping recording: {str(e)}"

# --- Flask Routes ---
@app.route('/')
def index():
    labels = handler.muscle_labels if handler and hasattr(handler, 'muscle_labels') else [f'Ch{i}' for i in range(NUM_SENSORS)]
    return render_template('index.html', num_sensors=NUM_SENSORS, muscle_labels=labels)

@app.route('/start_recording', methods=['POST'])
def start_recording():
    success, message = start_delsys_recording()
    return jsonify({'success': success, 'message': message})

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    success, message = stop_delsys_recording()
    return jsonify({'success': success, 'message': message})

@app.route('/live_data')
def live_data():
    global live_data_buffers, is_recording
    try:
        if not is_recording:
            return jsonify({'data': [[] for _ in range(NUM_SENSORS)], 'labels': [f'Ch{i}' for i in range(NUM_SENSORS)]})

        with live_data_lock:
            data_chunks = []
            labels = []
            for i in range(NUM_SENSORS):
                channel_chunks = []
                for chunk_dict in live_data_buffers[i]:
                    channel_chunks.extend(chunk_dict['samples'])

                data_chunks.append(channel_chunks)
                if live_data_buffers[i]:
                    labels.append(live_data_buffers[i][-1]['label'])
                else:
                    labels.append(f'Ch{i}')

        return jsonify({'data': data_chunks, 'labels': labels})
    except Exception as e:
        print(f"Error fetching live data: {e}")
        return jsonify({'data': [[] for _ in range(NUM_SENSORS)], 'labels': [f'Ch{i}' for i in range(NUM_SENSORS)]})

if __name__ == '__main__':
    try:
        print("Starting Flask server...")
        print(f"Recordings will be saved to: {os.path.abspath(SAVE_DIRECTORY)}")
        handler = DelsysDataHandler(host_ip=HOST_IP, num_sensors=NUM_SENSORS, sampling_rate=SAMPLING_RATE)
        recording_session_start_time = datetime.datetime.now()
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    finally:
        print("Flask server shutting down...")
        if handler:
            try:
                handler.stop_streaming()
            except Exception as e:
                print(f"Error stopping handler on shutdown: {e}")