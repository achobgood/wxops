import typer
from wxc_sdk.telephony.voicemail_groups import VoicemailGroupDetail
from wxc_sdk.common import (VoicemailMessageStorage, StorageType, VoicemailNotifications,
                             VoicemailFax, VoicemailTransferToNumber, VoicemailCopyOfMessage)
from wxcli.auth import get_api
from wxcli.output import print_table, print_json

app = typer.Typer(help="Manage Webex Calling voicemail groups.")


@app.command("list")
def list_voicemail_groups(
    location_id: str = typer.Option(None, "--location", help="Filter by location ID"),
    name: str = typer.Option(None, "--name", help="Filter by name"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List voicemail groups in the organization."""
    api = get_api(debug=debug)
    groups = list(api.telephony.voicemail_groups.list(
        location_id=location_id,
        name=name,
    ))
    if output == "json":
        print_json(groups)
    else:
        print_table(
            groups,
            columns=[
                ("ID", "group_id"),
                ("Name", "name"),
                ("Extension", "extension"),
                ("Enabled", "enabled"),
            ],
            limit=limit,
        )


@app.command("show")
def show_voicemail_group(
    location_id: str = typer.Argument(help="Location ID"),
    voicemail_group_id: str = typer.Argument(help="Voicemail group ID"),
    output: str = typer.Option("json", "--output", "-o"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show details for a single voicemail group."""
    api = get_api(debug=debug)
    vg = api.telephony.voicemail_groups.details(
        location_id=location_id,
        voicemail_group_id=voicemail_group_id,
    )
    print_json(vg)


@app.command("create")
def create_voicemail_group(
    location_id: str = typer.Option(..., "--location", help="Location ID"),
    name: str = typer.Option(..., "--name", help="Voicemail group name"),
    extension: str = typer.Option(..., "--extension", help="Extension number"),
    passcode: str = typer.Option(..., "--passcode", help="Voicemail passcode (6+ digits, no repeating)"),
    language_code: str = typer.Option("en_us", "--language", help="Language code"),
    enabled: bool = typer.Option(True, "--enabled/--disabled", help="Enable voicemail group"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new voicemail group."""
    api = get_api(debug=debug)
    settings = VoicemailGroupDetail(
        name=name,
        extension=extension,
        enabled=enabled,
        passcode=passcode,
        language_code=language_code,
        message_storage=VoicemailMessageStorage(storage_type=StorageType.internal),
        notifications=VoicemailNotifications(enabled=False),
        fax_message=VoicemailFax(enabled=False),
        transfer_to_number=VoicemailTransferToNumber(enabled=False),
        email_copy_of_message=VoicemailCopyOfMessage(enabled=False),
    )
    # Workaround: wxc_sdk for_create() missing by_alias=True, sends snake_case keys
    body = settings.model_dump(mode='json', exclude_unset=True, by_alias=True,
        include={'name', 'phone_number', 'extension', 'first_name', 'last_name', 'passcode',
                 'language_code', 'message_storage', 'notifications', 'fax_message',
                 'transfer_to_number', 'email_copy_of_message'})
    url = api.telephony.voicemail_groups.ep(location_id)
    data = api.telephony.voicemail_groups.post(url=url, json=body)
    vg_id = data['id']
    typer.echo(f"Created: {vg_id} ({name})")


@app.command("update")
def update_voicemail_group(
    location_id: str = typer.Argument(help="Location ID"),
    voicemail_group_id: str = typer.Argument(help="Voicemail group ID"),
    name: str = typer.Option(None, "--name", help="New name"),
    extension: str = typer.Option(None, "--extension", help="New extension"),
    enabled: bool = typer.Option(None, "--enabled/--disabled", help="Enable or disable"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a voicemail group."""
    api = get_api(debug=debug)
    vg = api.telephony.voicemail_groups.details(
        location_id=location_id,
        voicemail_group_id=voicemail_group_id,
    )
    if name is not None:
        vg.name = name
    if extension is not None:
        vg.extension = extension
    if enabled is not None:
        vg.enabled = enabled
    api.telephony.voicemail_groups.update(
        location_id=location_id,
        voicemail_group_id=voicemail_group_id,
        settings=vg,
    )
    typer.echo(f"Updated: {voicemail_group_id}")


@app.command("delete")
def delete_voicemail_group(
    location_id: str = typer.Argument(help="Location ID"),
    voicemail_group_id: str = typer.Argument(help="Voicemail group ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a voicemail group."""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete voicemail group {voicemail_group_id}?", abort=True)
    api.telephony.voicemail_groups.delete(
        location_id=location_id,
        voicemail_group_id=voicemail_group_id,
    )
    typer.echo(f"Deleted: {voicemail_group_id}")
