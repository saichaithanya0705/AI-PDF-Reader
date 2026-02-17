import os

def tail_log():
    try:
        with open("backend.log", "rb") as f:
            # Go to end
            f.seek(0, os.SEEK_END)
            end_pos = f.tell()
            
            # Read last 4096 bytes
            read_size = min(4096, end_pos)
            f.seek(end_pos - read_size)
            data = f.read()
            
            # Decode utf-16le if possible, or try common encodings
            # Log file seemed to have BOM or garbage chars
            try:
                text = data.decode("utf-16", errors="replace")
            except:
                try:
                    text = data.decode("utf-8", errors="replace")
                except:
                    text = str(data)
            
            lines = text.splitlines()
            print(f"--- Last {len(lines)} lines ---")
            for line in lines[-20:]:  # Last 20 lines
                print(line)
    except Exception as e:
        print(f"Error reading log: {e}")

if __name__ == "__main__":
    tail_log()
