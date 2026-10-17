"""Golden datasets API endpoints for multi-domain evaluation."""

from flask import Blueprint, jsonify, request

from ..services.golden_datasets import get_dataset, list_datasets, validate_engine_output

golden_bp = Blueprint('golden', __name__)


@golden_bp.route('/<process_id>/golden-datasets', methods=['GET'])
def list_golden_datasets(process_id):
    """List all available golden datasets."""
    return jsonify(list_datasets())


@golden_bp.route('/<process_id>/golden-datasets/<dataset_name>', methods=['GET'])
def get_golden_dataset(process_id, dataset_name):
    """Get a specific golden dataset with sample data."""
    ds = get_dataset(dataset_name)
    if not ds:
        return jsonify({'error': f'Dataset "{dataset_name}" not found'}), 404
    return jsonify(
        {
            'name': dataset_name,
            **ds,
        }
    )


@golden_bp.route('/<process_id>/golden-datasets/<dataset_name>/validate', methods=['POST'])
def validate_against_dataset(process_id, dataset_name):
    """Validate engine output against a golden dataset.

    Expects JSON body with engine_output containing trace_steps and summary.
    """
    data = request.get_json()
    if not data or 'engine_output' not in data:
        return jsonify({'error': 'Request body must include engine_output'}), 400

    result = validate_engine_output(dataset_name, data['engine_output'])
    if 'error' in result:
        return jsonify(result), 404
    return jsonify(result)
