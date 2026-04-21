#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
  import boto3
  from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
except ImportError:  # pragma: no cover - handled at runtime
  boto3 = None
  BotoCoreError = ClientError = NoCredentialsError = Exception


PROJECT_ROOT = Path(__file__).parent


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Generate study audio with Amazon Polly or local macOS voices.")
  parser.add_argument("manifest", help="Path to a JSON job manifest, relative to the project root or absolute.")
  parser.add_argument("--force", action="store_true", help="Regenerate audio files even if they already exist.")
  parser.add_argument("--dry-run", action="store_true", help="Print planned work without calling Amazon Polly or editing files.")
  parser.add_argument(
    "--provider",
    choices=["polly", "macos_say"],
    help="Override the provider specified in the manifest defaults.",
  )
  parser.add_argument("--voice-id", help="Override the voice specified in the manifest defaults.")
  parser.add_argument("--rate", type=int, help="Override the macOS `say` speech rate in words per minute.")
  return parser.parse_args()


def resolve_path(path_value: str) -> Path:
  path = Path(path_value)
  return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def load_manifest(manifest_path: Path) -> dict:
  with open(manifest_path, encoding="utf-8") as f:
    return json.load(f)


def load_deck(deck_path: Path) -> dict:
  with open(deck_path, encoding="utf-8") as f:
    return json.load(f)


def save_deck(deck_path: Path, deck: dict) -> None:
  with open(deck_path, "w", encoding="utf-8") as f:
    json.dump(deck, f, indent=2, ensure_ascii=False)
    f.write("\n")


def ensure_audio_reference(deck_path: Path, item_id: str, audio_href: str, dry_run: bool) -> None:
  deck = load_deck(deck_path)
  for item in deck.get("items", []):
    if item.get("id") == item_id:
      if dry_run:
        print(f"Would set audio for {deck_path.relative_to(PROJECT_ROOT)}::{item_id} -> {audio_href}")
      else:
        if item.get("audio") != audio_href:
          item["audio"] = audio_href
          save_deck(deck_path, deck)
      return
  raise ValueError(f"Item '{item_id}' not found in deck: {deck_path}")


def normalize_macos_output_path(output_path: Path) -> Path:
  if output_path.suffix.lower() == ".mp3":
    return output_path.with_suffix(".m4a")
  return output_path


def normalize_macos_audio_href(audio_href: str) -> str:
  if audio_href.endswith(".mp3"):
    return f"{audio_href[:-4]}.m4a"
  return audio_href


def synthesize_polly_audio(client, text: str, voice_id: str, engine: str, output_format: str, language_code: str) -> bytes:
  response = client.synthesize_speech(
    Text=text,
    VoiceId=voice_id,
    Engine=engine,
    OutputFormat=output_format,
    LanguageCode=language_code,
  )
  audio_stream = response.get("AudioStream")
  if audio_stream is None:
    raise RuntimeError("Amazon Polly returned no audio stream.")
  return audio_stream.read()


def synthesize_macos_say_audio(text: str, voice_id: str, output_path: Path, rate: int | None) -> None:
  output_path.parent.mkdir(parents=True, exist_ok=True)
  with tempfile.TemporaryDirectory() as temp_dir:
    temp_aiff_path = Path(temp_dir) / "speech.aiff"
    say_command = ["say", "-v", voice_id]
    if rate is not None:
      say_command.extend(["-r", str(rate)])
    say_command.extend(["-o", str(temp_aiff_path), text])
    subprocess.run(say_command, check=True)

    if output_path.suffix.lower() == ".aiff":
      output_path.write_bytes(temp_aiff_path.read_bytes())
      return

    if output_path.suffix.lower() == ".m4a":
      subprocess.run(
        ["afconvert", "-f", "m4af", "-d", "aac", str(temp_aiff_path), str(output_path)],
        check=True,
      )
      return

  raise RuntimeError(f"Unsupported macOS output format: {output_path.suffix or '(none)'}")


def run_jobs(
  manifest: dict,
  dry_run: bool,
  force: bool,
  provider_override: str | None,
  voice_override: str | None,
  rate_override: int | None,
) -> int:
  defaults = manifest.get("defaults", {})
  jobs = manifest.get("items", [])

  if not jobs:
    print("No jobs found in manifest.")
    return 0

  client = None
  default_provider = provider_override or defaults.get("provider", "polly")
  default_voice_id = voice_override or defaults.get("voice_id", "Takumi")
  default_engine = defaults.get("engine", "neural")
  default_output_format = defaults.get("output_format", "mp3")
  default_language_code = defaults.get("language_code", "ja-JP")
  default_rate = rate_override if rate_override is not None else defaults.get("rate")

  completed = 0
  for job in jobs:
    provider = provider_override or job.get("provider", default_provider)
    voice_id = voice_override or job.get("voice_id", default_voice_id)
    engine = job.get("engine", default_engine)
    output_format = job.get("output_format", default_output_format)
    language_code = job.get("language_code", default_language_code)
    rate = rate_override if rate_override is not None else job.get("rate", default_rate)
    deck_path = resolve_path(job["deck_path"])
    output_path = resolve_path(job["output_path"])
    audio_href = job["audio_href"]
    item_id = job["item_id"]
    text = job["text"]

    if provider == "macos_say":
      output_path = normalize_macos_output_path(output_path)
      audio_href = normalize_macos_audio_href(audio_href)

    if dry_run:
      rate_suffix = f" at rate {rate}" if provider == "macos_say" and rate is not None else ""
      print(f"Would synthesize '{text}' with {provider}{rate_suffix} -> {output_path.relative_to(PROJECT_ROOT)}")
      ensure_audio_reference(deck_path, item_id, audio_href, dry_run=True)
      completed += 1
      continue

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if force or not output_path.exists():
      if provider == "polly":
        if boto3 is None:
          raise RuntimeError("boto3 is not installed. Install it with `pip install boto3` before generating audio.")
        if client is None:
          client = boto3.client("polly")
        audio_bytes = synthesize_polly_audio(
          client,
          text,
          voice_id,
          engine,
          output_format,
          language_code,
        )
        with open(output_path, "wb") as f:
          f.write(audio_bytes)
      elif provider == "macos_say":
        synthesize_macos_say_audio(text, voice_id, output_path, rate)
      else:
        raise RuntimeError(f"Unsupported provider: {provider}")

    ensure_audio_reference(deck_path, item_id, audio_href, dry_run=False)
    completed += 1
    print(f"Generated {output_path.relative_to(PROJECT_ROOT)} and updated {deck_path.relative_to(PROJECT_ROOT)}::{item_id}")

  return completed


def main() -> int:
  args = parse_args()
  manifest_path = resolve_path(args.manifest)
  if not manifest_path.exists():
    print(f"Manifest not found: {manifest_path}", file=sys.stderr)
    return 1

  try:
    manifest = load_manifest(manifest_path)
    count = run_jobs(
      manifest,
      dry_run=args.dry_run,
      force=args.force,
      provider_override=args.provider,
      voice_override=args.voice_id,
      rate_override=args.rate,
    )
  except (BotoCoreError, ClientError, NoCredentialsError, OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
    print(f"Audio generation failed: {exc}", file=sys.stderr)
    return 1

  mode_label = "planned" if args.dry_run else "generated"
  print(f"Successfully {mode_label} {count} study audio job(s).")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())