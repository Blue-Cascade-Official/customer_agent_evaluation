"""Smoke-test Postgres, GCS, OpenAI, and ElevenLabs credentials."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def test_postgres() -> None:
    from app.config import get_settings
    from sqlalchemy import create_engine, text

    settings = get_settings()
    engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        row = conn.execute(text("SELECT current_database(), 1")).one()
        print(f"[OK] Postgres -> {row[0]}")
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("[OK] pgvector available")
        except Exception as exc:
            print(f"[WARN] pgvector: {exc}")


def test_gcs() -> None:
    from app.services.gcs import upload_bytes, read_bytes
    from app.config import get_settings

    settings = get_settings()
    # Skip bucket.exists() — many SAs have object write without storage.buckets.get
    probe_path = "healthchecks/internee-eval-probe.txt"
    url = upload_bytes(b"internee-eval-ok", probe_path, "text/plain")
    data = read_bytes(url)
    assert data == b"internee-eval-ok"
    print(f"[OK] GCS -> bucket={settings.gcs_bucket} uploaded {url}")



def test_openai() -> None:
    from app.services.openai_client import embed_texts

    vecs = embed_texts(["credential probe"])
    assert vecs and len(vecs[0]) == 1536
    print(f"[OK] OpenAI embeddings -> dim={len(vecs[0])}")


def test_elevenlabs() -> None:
    import asyncio
    from app.services import elevenlabs
    from app.config import get_settings

    settings = get_settings()

    async def _run():
        token = await elevenlabs.get_conversation_token(participant_name="credential-probe")
        assert token.get("token")
        return token

    token = asyncio.run(_run())
    print(
        f"[OK] ElevenLabs token -> agent={settings.elevenlabs_agent_id} "
        f"token_len={len(token['token'])}"
    )



def main() -> None:
    errors: list[str] = []
    for name, fn in [
        ("postgres", test_postgres),
        ("gcs", test_gcs),
        ("openai", test_openai),
        ("elevenlabs", test_elevenlabs),
    ]:
        try:
            fn()
        except Exception as exc:
            errors.append(f"[FAIL] {name}: {exc}")
            print(errors[-1])
    if errors:
        raise SystemExit(1)
    print("\nAll credential checks passed.")


if __name__ == "__main__":
    main()
