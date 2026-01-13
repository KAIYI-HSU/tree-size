import os

def get_dir_size(path: str) -> int:
    """Calculates the total size of a directory recursively."""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
    except Exception as e:
        print(f"Error accessing {path}: {e}")
    return total_size

def format_bytes(size: int) -> str:
    """Formats bytes into human-readable string."""
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size >= power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

def _walk_and_add(current_path: str, parent_path: str, data_list: list, current_depth: int = 0, max_depth: int = 2):
    """
    Helper to traverse deeper.
    Limiting max_depth to avoid browser crash with too many nodes.
    """
    if current_depth >= max_depth:
        return

    try:
        items = os.listdir(current_path)
        for item in items:
            item_path = os.path.join(current_path, item)
            # Skip symbolic links to avoid infinite loops
            if os.path.islink(item_path):
                continue

            if os.path.isdir(item_path):
                size = get_dir_size(item_path)
                data_list.append({
                    'id': item_path,
                    'parent': current_path,
                    'label': item,
                    'value': size
                })
                # Recurse
                _walk_and_add(item_path, current_path, data_list, current_depth + 1, max_depth)
            else:
                size = os.path.getsize(item_path)
                data_list.append({
                    'id': item_path,
                    'parent': current_path,
                    'label': item,
                    'value': size
                })
    except PermissionError:
        pass
    except Exception:
        pass

def scan_directory(path: str, progress_callback=None) -> list:
    """
    Scans the directory structure and prepares data for Sunburst chart.
    Returns a list of dictionaries suitable for DataFrame creation.
    """
    raw_data = []

    # Root node
    root_size = get_dir_size(path)
    raw_data.append(dict(id=path, parent="", label=os.path.basename(path) or path, value=root_size))

    # Walk top level
    try:
        top_items = os.listdir(path)
        total = len(top_items)
        for idx, item in enumerate(top_items):
            p = os.path.join(path, item)

            if progress_callback:
                progress_callback((idx+1)/total, text=f"Analyzing {item}...")

            # Skip symlinks
            if os.path.islink(p):
                continue

            if os.path.isdir(p):
                s = get_dir_size(p)
                raw_data.append(dict(id=p, parent=path, label=item, value=s))
                # Go deeper (level 2)
                _walk_and_add(p, path, raw_data, max_depth=1)
            else:
                s = os.path.getsize(p)
                raw_data.append(dict(id=p, parent=path, label=item, value=s))

    except Exception as e:
        print(f"Error scanning: {e}")

    return raw_data
