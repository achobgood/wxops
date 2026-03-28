"""Download and bulk-export converged recording artifacts (audio, transcript, AI notes)."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import requests
import typer
from rich.console import Console
from wxc_sdk.rest import RestError

from wxcli.auth import get_api
from wxcli.errors import handle_rest_error

logger = logging.getLogger(__name__)
console = Console()

BASE = "https://webexapis.com/v1"

# Mapping from temporaryDirectDownloadLinks field → output filename
ARTIFACT_MAP = {
    "transcriptDownloadLink": ("transcript.txt", "transcript", False),
    "suggestedNotesDownloadLink": ("suggested_notes.html", "suggestedNotes", False),
    "shortNotesDownloadLink": ("short_notes.html", "shortNotes", False),
    "actionItemsDownloadLink": ("action_items.html", "actionItems", False),
    "audioDownloadLink": ("audio.mp3", "audioFile", True),
}


@dataclass
class DownloadResult:
    recording_id: str
    metadata: dict
    downloaded: list[str] = field(default_factory=list)
    unavailable: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    audio_path: str | None = None


def download_recording_artifacts(
    api,
    recording_id: str,
    output_dir: Path,
    include_audio: bool = False,
) -> DownloadResult:
    """Fetch recording detail and download all available artifacts."""
    url = f"{BASE}/convergedRecordings/{recording_id}"
    detail = api.session.rest_get(url)

    result = DownloadResult(recording_id=recording_id, metadata=detail)

    # Write metadata.json
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(detail, indent=2, default=str))

    links = detail.get("temporaryDirectDownloadLinks") or {}

    for link_field, (filename, _content_key, is_audio) in ARTIFACT_MAP.items():
        if is_audio and not include_audio:
            continue

        download_url = links.get(link_field)
        if not download_url:
            result.unavailable.append(filename)
            continue

        try:
            if is_audio:
                resp = requests.get(download_url, timeout=300, stream=True)
                resp.raise_for_status()
            else:
                resp = requests.get(download_url, timeout=300)
                resp.raise_for_status()
        except Exception as e:
            logger.warning("Failed to download %s for %s: %s", filename, recording_id, e)
            result.failed.append(filename)
            continue

        file_path = output_dir / filename
        if is_audio:
            with open(file_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            result.audio_path = str(file_path)
        else:
            file_path.write_text(resp.text, encoding="utf-8")

        result.downloaded.append(filename)

    return result


def register(app: typer.Typer) -> None:
    """Register download and export commands on the converged-recordings app."""

    @app.command("download")
    def download(
        recording_id: str = typer.Argument(help="Recording ID to download"),
        include_audio: bool = typer.Option(False, "--include-audio", help="Download the MP3 audio file"),
        output_dir: str = typer.Option("./recordings", "--output-dir", "-d", help="Target directory"),
        debug: bool = typer.Option(False, "--debug"),
    ):
        """Download a single recording's artifacts to a local directory."""
        api = get_api(debug=debug)
        out_path = Path(output_dir) / recording_id

        console.print(f"Downloading recording {recording_id}...")

        try:
            result = download_recording_artifacts(api, recording_id, out_path, include_audio)
        except RestError as e:
            handle_rest_error(e)
            return  # unreachable — handle_rest_error always raises
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

        # Summary
        parts = []
        if result.downloaded:
            parts.append(f"downloaded: {', '.join(result.downloaded)}")
        if result.unavailable:
            parts.append(f"not available: {', '.join(result.unavailable)}")
        if result.failed:
            parts.append(f"failed: {', '.join(result.failed)}")

        console.print(f"  Output: {out_path}")
        console.print(f"  {'; '.join(parts)}")

        if not result.downloaded:
            raise typer.Exit(1)

    @app.command("export")
    def export(
        from_date: str = typer.Option(..., "--from", help="Start date, ISO 8601 (required)"),
        to_date: str = typer.Option(..., "--to", help="End date, ISO 8601 (required)"),
        owner_email: str = typer.Option(None, "--owner-email", help="Filter by owner email"),
        owner_id: str = typer.Option(None, "--owner-id", help="Filter by owner ID"),
        owner_type: str = typer.Option(None, "--owner-type", help="Filter: user|place|virtualLine|callQueue"),
        location_id: str = typer.Option(None, "--location-id", help="Filter by location ID"),
        service_type: str = typer.Option(None, "--service-type", help="Filter: calling|customerAssist"),
        status: str = typer.Option(None, "--status", help="Filter: available|deleted"),
        topic: str = typer.Option(None, "--topic", help="Filter by topic keyword"),
        include_audio: bool = typer.Option(False, "--include-audio", help="Download MP3 audio files"),
        fmt: str = typer.Option("jsonl", "--format", help="Output format: jsonl|json-per-file"),
        output_dir: str = typer.Option("./recording-export", "--output-dir", "-d", help="Target directory"),
        limit: int = typer.Option(0, "--limit", help="Max recordings to export (0=all)"),
        debug: bool = typer.Option(False, "--debug"),
    ):
        """Bulk export recordings with text/AI artifacts for BI consumption."""
        api = get_api(debug=debug)
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # Build list query params
        params: dict = {"from": from_date, "to": to_date}
        if owner_email:
            params["ownerEmail"] = owner_email
        if owner_id:
            params["ownerId"] = owner_id
        if owner_type:
            params["ownerType"] = owner_type
        if location_id:
            params["locationId"] = location_id
        if service_type:
            params["serviceType"] = service_type
        if status:
            params["status"] = status
        if topic:
            params["topic"] = topic

        # Paginate the admin listing endpoint
        console.print("Listing recordings...")
        list_url = f"{BASE}/admin/convergedRecordings"
        try:
            recordings = list(api.session.follow_pagination(url=list_url, params=params, item_key="items"))
            if limit > 0:
                recordings = recordings[:limit]
        except RestError as e:
            handle_rest_error(e)
            return

        if not recordings:
            console.print("[yellow]No recordings found for the given filters.[/yellow]")
            return

        total = len(recordings)
        console.print(f"Found {total} recording(s). Exporting...")

        # Track stats
        exported = 0
        failed_ids: list[str] = []
        artifact_counts: dict[str, int] = {"downloaded": 0, "unavailable": 0, "failed": 0}
        audio_count = 0

        # JSONL mode: open the output file
        jsonl_file = None
        if fmt == "jsonl":
            jsonl_file = open(out_path / "recordings.jsonl", "w", encoding="utf-8")
            if include_audio:
                (out_path / "audio").mkdir(exist_ok=True)

        try:
            for i, rec in enumerate(recordings, 1):
                rec_id = rec.get("id", "unknown")
                console.print(f"Exporting recording {i}/{total} ({rec_id[:16]}...)...")

                try:
                    if fmt == "json-per-file":
                        rec_dir = out_path / rec_id
                        dl_result = download_recording_artifacts(api, rec_id, rec_dir, include_audio)
                    else:
                        # JSONL mode: fetch detail, download artifacts inline
                        detail_url = f"{BASE}/convergedRecordings/{rec_id}"
                        detail = api.session.rest_get(detail_url)
                        links = detail.get("temporaryDirectDownloadLinks") or {}

                        # Build the JSONL record — all metadata fields except download links
                        record: dict = {
                            k: v for k, v in detail.items()
                            if k != "temporaryDirectDownloadLinks"
                        }

                        dl_result = DownloadResult(recording_id=rec_id, metadata=detail)

                        # Download text artifacts inline
                        for link_field, (filename, content_key, is_audio) in ARTIFACT_MAP.items():
                            if is_audio:
                                continue
                            download_url = links.get(link_field)
                            if not download_url:
                                record[content_key] = None
                                dl_result.unavailable.append(filename)
                                continue
                            try:
                                resp = requests.get(download_url, timeout=300)
                                resp.raise_for_status()
                                record[content_key] = resp.text
                                dl_result.downloaded.append(filename)
                            except Exception as e:
                                logger.warning("Failed to download %s for %s: %s", filename, rec_id, e)
                                record[content_key] = None
                                dl_result.failed.append(filename)

                        # Audio (opt-in)
                        if include_audio:
                            audio_url = links.get("audioDownloadLink")
                            if not audio_url:
                                record["audioFile"] = None
                                dl_result.unavailable.append("audio.mp3")
                            else:
                                try:
                                    resp = requests.get(audio_url, timeout=300, stream=True)
                                    resp.raise_for_status()
                                    audio_path = out_path / "audio" / f"{rec_id}.mp3"
                                    with open(audio_path, "wb") as af:
                                        for chunk in resp.iter_content(chunk_size=8192):
                                            af.write(chunk)
                                    record["audioFile"] = f"audio/{rec_id}.mp3"
                                    dl_result.audio_path = str(audio_path)
                                    dl_result.downloaded.append("audio.mp3")
                                except Exception as e:
                                    logger.warning("Failed to download audio for %s: %s", rec_id, e)
                                    record["audioFile"] = None
                                    dl_result.failed.append("audio.mp3")
                        else:
                            record["audioFile"] = None

                        jsonl_file.write(json.dumps(record, default=str) + "\n")
                        jsonl_file.flush()

                    exported += 1
                    artifact_counts["downloaded"] += len(dl_result.downloaded)
                    artifact_counts["unavailable"] += len(dl_result.unavailable)
                    artifact_counts["failed"] += len(dl_result.failed)
                    if dl_result.audio_path:
                        audio_count += 1

                except RestError as e:
                    logger.warning("Failed to export recording %s: %s", rec_id, e)
                    failed_ids.append(rec_id)
                except Exception as e:
                    logger.warning("Failed to export recording %s: %s", rec_id, e)
                    failed_ids.append(rec_id)

        finally:
            if jsonl_file:
                jsonl_file.close()

        # Final summary
        console.print("")
        console.print("[bold]Export Summary[/bold]")
        console.print(f"  Total recordings: {total}")
        console.print(f"  Exported:         {exported}")
        console.print(f"  Failed:           {len(failed_ids)}")
        console.print(f"  Artifacts downloaded:  {artifact_counts['downloaded']}")
        console.print(f"  Artifacts unavailable: {artifact_counts['unavailable']}")
        console.print(f"  Artifacts failed:      {artifact_counts['failed']}")
        if include_audio:
            console.print(f"  Audio files:      {audio_count}")
        console.print(f"  Output directory: {out_path}")

        if failed_ids:
            console.print(f"\n[yellow]Failed recording IDs:[/yellow]")
            for fid in failed_ids:
                console.print(f"  - {fid}")
            raise typer.Exit(1)
