"""List the bundled domain packs and create a process from one."""

from flask import Blueprint, current_app, jsonify, request

from ..services.domain_packs import DomainPackError, find_pack, install_pack, list_packs, load_pack, packs_dir

domain_packs_bp = Blueprint('domain_packs', __name__)


@domain_packs_bp.route('', methods=['GET'])
def get_domain_packs():
    return jsonify(list_packs(packs_dir(current_app.config)))


@domain_packs_bp.route('/<pack_id>/install', methods=['POST'])
def install_domain_pack(pack_id):
    """Create a new process from a pack. Body: ``{"with_sample_outputs": true}``."""
    data = request.get_json(silent=True) or {}
    try:
        pack = load_pack(find_pack(packs_dir(current_app.config), pack_id))
        process = install_pack(pack, with_sample_outputs=data.get('with_sample_outputs', True))
    except DomainPackError as e:
        return jsonify({'error': str(e)}), 404
    return jsonify(process.to_dict()), 201
