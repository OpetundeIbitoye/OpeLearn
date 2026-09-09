"""Explicit one-time provisioning; runtime loads only local model artifacts."""
import hashlib
import json
import os
from pathlib import Path

os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['DO_NOT_TRACK'] = '1'
from huggingface_hub import snapshot_download
from docling.utils.model_downloader import download_models
from sentence_transformers import SentenceTransformer
from app.kernel.config import settings


def main() -> None:
    root = Path(settings.model_directory)
    manifest_path = root / 'manifest.json'
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text())
        if existing['model_id'] != settings.embedding_model:
            raise ValueError('Model changed; explicit reprovisioning is required')
        print('Existing provisioned snapshot retained')
        return
    lock = json.loads(Path('config/models.lock.json').read_text())
    if lock['model_id'] != settings.embedding_model:
        raise ValueError('Configured model differs from the committed model lock')
    root.mkdir(parents=True, exist_ok=True)
    revision_path = root / 'embedding-revision.txt'
    if revision_path.exists():
        revision = revision_path.read_text().strip()
    else:
        revision = lock['revision']
        revision_path.write_text(revision)
    print(f'Provisioning {settings.embedding_model} at {revision}', flush=True)
    snapshot_download(settings.embedding_model, revision=revision, local_dir=root / 'embedding',
                      ignore_patterns=['onnx/*', 'openvino/*', '*.bin'])
    model = SentenceTransformer(str(root / 'embedding'), local_files_only=True, trust_remote_code=False)
    dimension = model.get_sentence_embedding_dimension()
    del model
    download_models(output_dir=root / 'docling', with_layout=True, with_tableformer=True,
                    with_code_formula=False, with_picture_classifier=False, with_rapidocr=False)
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(root.rglob('*')) if p.is_file() and '.cache' not in p.parts}
    if dimension != lock['dimension'] or hashes != lock['sha256']:
        raise ValueError('Downloaded model artifacts differ from the committed lock')
    manifest_path.write_text(json.dumps({'model_id': settings.embedding_model, 'revision': revision,
                                        'dimension': dimension, 'sha256': hashes}, indent=2) + '\n')
    print(f'Provisioned embedding dimension: {dimension}', flush=True)

if __name__ == '__main__':
    main()
