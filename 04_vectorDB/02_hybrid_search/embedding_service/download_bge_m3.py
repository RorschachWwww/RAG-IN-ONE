import os

from huggingface_hub import snapshot_download


MODEL_ID = os.getenv("EMBEDDING_MODEL_ID", "BAAI/bge-m3")
TARGET_DIR = os.getenv("EMBEDDING_MODEL_DIR", "/models/BAAI_bge-m3")


def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=TARGET_DIR,
        local_dir_use_symlinks=False,
        resume_download=True,
    )
    print(f"downloaded model to {TARGET_DIR}")


if __name__ == "__main__":
    main()
