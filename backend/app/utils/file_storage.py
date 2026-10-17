import os
import uuid

from flask import current_app


def new_storage_path(process_id, filename):
    """Return a fresh, unique storage path for a document of this process."""
    upload_dir = os.path.join(current_app.config['UPLOAD_DIR'], str(process_id))
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(filename)[1] if filename else ''
    return os.path.join(upload_dir, f"{uuid.uuid4()}{ext}")


def save_uploaded_file(file, process_id):
    """Save an uploaded file and return the storage path."""
    path = new_storage_path(process_id, file.filename)
    file.save(path)
    return path


def get_file_path(storage_path):
    """Return absolute path to stored file."""
    return storage_path


def delete_file(storage_path):
    """Delete a stored file."""
    if os.path.exists(storage_path):
        os.remove(storage_path)
