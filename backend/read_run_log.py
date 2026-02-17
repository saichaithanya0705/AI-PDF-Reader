import os

def read_log_tail(filepath, num_bytes=5000):
    try:
        with open(filepath, 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(size - num_bytes, 0))
            content = f.read()
        return content.decode('utf-8', errors='replace')
    except Exception as e:
        return f"Error reading log: {e}"

if __name__ == "__main__":
    print(read_log_tail("backend_run.log"))
