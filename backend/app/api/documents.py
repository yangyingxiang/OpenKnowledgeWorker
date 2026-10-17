import os

from flask import Blueprint, jsonify, request, send_file

from ..extensions import get_db
from ..models import Document, Process
from ..services.document_ingestion import ingest_document
from ..utils.file_storage import delete_file

documents_bp = Blueprint('documents', __name__)


@documents_bp.route('/<process_id>/documents', methods=['GET'])
def list_documents(process_id):
    db = get_db()
    docs = db.query(Document).filter_by(process_id=process_id).order_by(Document.created_at.desc()).all()
    return jsonify([d.to_dict() for d in docs])


@documents_bp.route('/<process_id>/documents', methods=['POST'])
def upload_document(process_id):
    db = get_db()

    # Verify process exists
    process = db.query(Process).filter_by(id=process_id).first()
    if not process:
        return jsonify({'error': 'Process not found'}), 404

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No filename'}), 400

    doc = ingest_document(process_id, file.filename, file.save)
    return jsonify(doc.to_dict()), 201


@documents_bp.route('/<process_id>/documents/<doc_id>', methods=['GET'])
def get_document(process_id, doc_id):
    db = get_db()
    doc = db.query(Document).filter_by(id=doc_id, process_id=process_id).first()
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    result = doc.to_dict()
    result['extracted_text'] = doc.extracted_text
    return jsonify(result)


@documents_bp.route('/<process_id>/documents/<doc_id>', methods=['DELETE'])
def delete_document(process_id, doc_id):
    db = get_db()
    doc = db.query(Document).filter_by(id=doc_id, process_id=process_id).first()
    if not doc:
        return jsonify({'error': 'Document not found'}), 404

    if doc.storage_path:
        delete_file(doc.storage_path)

    db.delete(doc)
    db.commit()
    return jsonify({'success': True})


@documents_bp.route('/<process_id>/documents/<doc_id>/chunks', methods=['GET'])
def list_chunks(process_id, doc_id):
    """List all chunks for a document."""
    db = get_db()
    doc = db.query(Document).filter_by(id=doc_id, process_id=process_id).first()
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    summary_only = request.args.get('summary', '').lower() == 'true'
    if summary_only:
        return jsonify([c.to_summary() for c in doc.chunks])
    return jsonify([c.to_dict() for c in doc.chunks])


@documents_bp.route('/<process_id>/documents/<doc_id>/content', methods=['GET'])
def download_document(process_id, doc_id):
    db = get_db()
    doc = db.query(Document).filter_by(id=doc_id, process_id=process_id).first()
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    if not os.path.exists(doc.storage_path):
        return jsonify({'error': 'File not found on disk'}), 404
    return send_file(doc.storage_path, download_name=doc.original_filename)
