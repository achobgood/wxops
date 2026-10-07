import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Contact Center cc-org-settings.")


@app.command("list", short_help="List Organization Settings.")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. Supported filterable fields: id. The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" - id!=\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Organization Settings."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/organization-setting"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show", short_help="Get specific Organization Setting by ID.")
def show(
    id: str = typer.Argument(help="UUID, from: wxcli cc-org-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Organization Setting by ID.\n\n\b\nExample: wxcli cc-org-settings show ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/organization-setting/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"tenantXmlUrl":"...","ivrParkUrl":"...","wfoEnabled":true,"campaignManagerEnabled":true,"configureSpeechEnabledIVREnabled":true,"shortCallThreshold":0,"lostCallThreshold":0,"voiceContactSurgeFactor":0,"digitalContactSurgeFactor":0,"maximumActiveCalls":0,"inboundMaximumActiveCalls":0,"outdialMaximumActiveCalls":0,"allowAgentThresholds":true,"pauseResumeEnabled":true,"recordingPauseDuration":0,"recordAllCalls":true,"webexManagementEnabled":true,"retryCallbackInterval":0,"maximumCallbackAttempts":0,"cccEnabled":true,"sbrEnabled":true,"maximumTextSkills":0,"maximumSkills":0,"multiMediaEnabled":true,"maxChannels":0,"voiceCallBackEnabled":true,"jukeboxEnabled":true,"pruningStrategy":"NONE","pruningValue":0,"analyticsEnabled":true,"maximumVirtualTeams":0,"maximumAddressBooks":0,"numberOfCadVariables":0,"thresholdAlertsEnabled":true,"lastAgentRouting":true,"legRecordingEnabled":true,"multipleTimeZoneEnabled":true,"steeringDigitsEnabled":true,"socialChannel":true,"flowBuilderEnabled":true,"resourcesCreated":true,"wfoAnalyticsWithTranscription":true,"wfoBundle":true,"qualityManagement":true,"speechEnabledIVROverage":true,"campaignManagerOverage":true,"qualityManagementOverage":true,"wfoOverage":true,"wfoAnalyticsOverage":true,"wfoAnalyticsWithTranscriptionOverage":true,"wfoBundleOverage":true,"webCallBackEnabled":true,"checkAgentAvailability":true,"offerCode":"CJPPRM","ciscoPstnDID":true,"ciscoPstnTF":true,"organizationId":"...","id":"...","version":0,"concurrentVoiceContactEntitlement":0,"concurrentDigitalContactEntitlement":0,"basicNativeVirtualAgentQuantity":0,"maximumThresholdRules":0,"recordingMode":"AUDIO_ONLY","webexManagementUrl":"...","licenseVersion":"...","adapterId":"...","otgId":"...","externalId":"...","voicePrefix":"...","wfoBundleAgents":0,"speechEnabledIVRPorts":0,"orderId":"...","license":"...","serviceProvisioningId":"...","orderSubscriptionId":"...","billingGroupId":"...","outboundSipDomain":"...","purgeAllowed":true,"purgeInactiveEntitiesInterval":0,"inactivateEntitiesPurgedOn":"...","webRtcEnabled":true,"maskSensitiveData":true,"aiAssistantQuantity":0,"routingToSameAgent":"DISABLED","byovaOfferQuantity":0,"wholesaleOrder":true,"homeRegion":"...","multiRegionEnabled":true,"workforceManagementEnabled":true,"transcriptsKmsKeyMetadata":{"keyUrl":"...","kroUrl":"...","updatedTimestamp":"..."},"offerDetails":[{"offerCode":"...","licenseVolume":0}],"createdTime":0,"lastUpdatedTime":0}'

@app.command("update", short_help="Update specific Organization Setting by ID.")
def update(
    id: str = typer.Argument(help="UUID, from: wxcli cc-org-settings list"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations. User-token updates are not permitted for this field."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    tenant_xml_url: str = typer.Option(None, "--tenant-xml-url", help="Tenant Xml Url. User-token updates are not permitted for this field."),
    ivr_park_url: str = typer.Option(None, "--ivr-park-url", help="Ivr Park Url. User-token updates are not permitted for this field."),
    wfo_enabled: bool = typer.Option(None, "--wfo-enabled/--no-wfo-enabled", help="Wfo Enabled. User-token updates are not permitted for this field."),
    campaign_manager_enabled: bool = typer.Option(None, "--campaign-manager-enabled/--no-campaign-manager-enabled", help="Campaign Manager Enabled. User-token updates are not permitted for this field."),
    configure_speech_enabled_ivr_enabled: bool = typer.Option(None, "--configure-speech-enabled-ivr-enabled/--no-configure-speech-enabled-ivr-enabled", help="Configure Speech Enabled IVREnabled. User-token updates are not permitted for this field."),
    short_call_threshold: str = typer.Option(None, "--short-call-threshold", help="Short Call Threshold. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    lost_call_threshold: str = typer.Option(None, "--lost-call-threshold", help="Lost Call Threshold. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    concurrent_voice_contact_entitlement: str = typer.Option(None, "--concurrent-voice-contact-entitlement", help="Concurrent Voice Contact Entitlement. User-token updates are not permitted for this field."),
    voice_contact_surge_factor: str = typer.Option(None, "--voice-contact-surge-factor", help="Voice Contact Surge Factor. User-token updates are not permitted for this field."),
    concurrent_digital_contact_entitlement: str = typer.Option(None, "--concurrent-digital-contact-entitlement", help="Concurrent Digital Contact Entitlement. User-token updates are not permitted for this field."),
    digital_contact_surge_factor: str = typer.Option(None, "--digital-contact-surge-factor", help="Digital Contact Surge Factor. User-token updates are not permitted for this field."),
    basic_native_virtual_agent_quantity: str = typer.Option(None, "--basic-native-virtual-agent-quantity", help="Basic Native Virtual Agent Quantity. User-token updates are not permitted for this field."),
    maximum_active_calls: str = typer.Option(None, "--maximum-active-calls", help="Maximum Active Calls. User-token updates are not permitted for this field."),
    inbound_maximum_active_calls: str = typer.Option(None, "--inbound-maximum-active-calls", help="Inbound Maximum Active Calls. User-token updates are not permitted for this field."),
    outdial_maximum_active_calls: str = typer.Option(None, "--outdial-maximum-active-calls", help="Outdial Maximum Active Calls. User-token updates are not permitted for this field."),
    maximum_threshold_rules: str = typer.Option(None, "--maximum-threshold-rules", help="Maximum Threshold Rules. User-token updates are not permitted for this field."),
    allow_agent_thresholds: bool = typer.Option(None, "--allow-agent-thresholds/--no-allow-agent-thresholds", help="Allow Agent Thresholds. User-token updates are not permitted for this field."),
    pause_resume_enabled: bool = typer.Option(None, "--pause-resume-enabled/--no-pause-resume-enabled", help="Pause Resume Enabled. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    recording_pause_duration: str = typer.Option(None, "--recording-pause-duration", help="Recording Pause Duration. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    record_all_calls: bool = typer.Option(None, "--record-all-calls/--no-record-all-calls", help="Record All Calls. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    recording_mode: str = typer.Option(None, "--recording-mode", help="Choices: AUDIO_ONLY, AUDIO_AND_SCREEN, DISABLED"),
    webex_management_enabled: bool = typer.Option(None, "--webex-management-enabled/--no-webex-management-enabled", help="Webex Management Enabled. User-token updates are not permitted for this field."),
    webex_management_url: str = typer.Option(None, "--webex-management-url", help="Webex Management Url. User-token updates are not permitted for this field."),
    license_version: str = typer.Option(None, "--license-version", help="License Version. User-token updates are not permitted for this field."),
    adapter_id: str = typer.Option(None, "--adapter-id", help="Adapter Id. User-token updates are not permitted for this field."),
    otg_id: str = typer.Option(None, "--otg-id", help="Otg Id. User-token updates are not permitted for this field."),
    retry_callback_interval: str = typer.Option(None, "--retry-callback-interval", help="Retry Callback Interval. User-token updates are not permitted for this field."),
    maximum_callback_attempts: str = typer.Option(None, "--maximum-callback-attempts", help="Maximum Callback Attempts. User-token updates are not permitted for this field."),
    ccc_enabled: bool = typer.Option(None, "--ccc-enabled/--no-ccc-enabled", help="Ccc Enabled. User-token updates are not permitted for this field."),
    sbr_enabled: bool = typer.Option(None, "--sbr-enabled/--no-sbr-enabled", help="Sbr Enabled. User-token updates are not permitted for this field."),
    maximum_text_skills: str = typer.Option(None, "--maximum-text-skills", help="Maximum Text Skills. User-token updates are not permitted for this field."),
    maximum_skills: str = typer.Option(None, "--maximum-skills", help="Maximum Skills. User-token updates are not permitted for this field."),
    multi_media_enabled: bool = typer.Option(None, "--multi-media-enabled/--no-multi-media-enabled", help="Multi Media Enabled. User-token updates are not permitted for this field."),
    max_channels: str = typer.Option(None, "--max-channels", help="Max Channels. User-token updates are not permitted for this field."),
    voice_call_back_enabled: bool = typer.Option(None, "--voice-call-back-enabled/--no-voice-call-back-enabled", help="Voice Call Back Enabled. User-token updates are not permitted for this field."),
    jukebox_enabled: bool = typer.Option(None, "--jukebox-enabled/--no-jukebox-enabled", help="Jukebox Enabled. User-token updates are not permitted for this field."),
    pruning_strategy: str = typer.Option(None, "--pruning-strategy", help="Choices: NONE, TIME_BASED, STORAGE_BASED, AGENT_MINUTES"),
    pruning_value: str = typer.Option(None, "--pruning-value", help="Pruning Value. User-token updates are not permitted for this field."),
    analytics_enabled: bool = typer.Option(None, "--analytics-enabled/--no-analytics-enabled", help="Analytics Enabled. User-token updates are not permitted for this field."),
    maximum_virtual_teams: str = typer.Option(None, "--maximum-virtual-teams", help="Maximum Virtual Teams. User-token updates are not permitted for this field."),
    maximum_address_books: str = typer.Option(None, "--maximum-address-books", help="Maximum Address Books. User-token updates are not permitted for this field."),
    number_of_cad_variables: str = typer.Option(None, "--number-of-cad-variables", help="Number Of Cad Variables. User-token updates are not permitted for this field."),
    external_id: str = typer.Option(None, "--external-id", help="External Id. User-token updates are not permitted for this field."),
    threshold_alerts_enabled: bool = typer.Option(None, "--threshold-alerts-enabled/--no-threshold-alerts-enabled", help="Threshold Alerts Enabled. User-token updates are not permitted for this field."),
    last_agent_routing: bool = typer.Option(None, "--last-agent-routing/--no-last-agent-routing", help="Last Agent Routing. User-token updates are not permitted for this field."),
    leg_recording_enabled: bool = typer.Option(None, "--leg-recording-enabled/--no-leg-recording-enabled", help="Leg Recording Enabled. User-token updates are not permitted for this field."),
    multiple_time_zone_enabled: bool = typer.Option(None, "--multiple-time-zone-enabled/--no-multiple-time-zone-enabled", help="Multiple Time Zone Enabled. User-token updates are not permitted for this field."),
    voice_prefix: str = typer.Option(None, "--voice-prefix", help="Voice Prefix. User-token updates are not permitted for this field."),
    steering_digits_enabled: bool = typer.Option(None, "--steering-digits-enabled/--no-steering-digits-enabled", help="Steering Digits Enabled. User-token updates are not permitted for this field."),
    social_channel: bool = typer.Option(None, "--social-channel/--no-social-channel", help="Social Channel. User-token updates are not permitted for this field."),
    flow_builder_enabled: bool = typer.Option(None, "--flow-builder-enabled/--no-flow-builder-enabled", help="Flow Builder Enabled. User-token updates are not permitted for this field."),
    resources_created: bool = typer.Option(None, "--resources-created/--no-resources-created", help="Resources Created. User-token updates are not permitted for this field."),
    wfo_analytics_with_transcription: bool = typer.Option(None, "--wfo-analytics-with-transcription/--no-wfo-analytics-with-transcription", help="Wfo Analytics With Transcription. User-token updates are not permitted for this field."),
    wfo_bundle_agents: str = typer.Option(None, "--wfo-bundle-agents", help="Wfo Bundle Agents. User-token updates are not permitted for this field."),
    wfo_bundle: bool = typer.Option(None, "--wfo-bundle/--no-wfo-bundle", help="Wfo Bundle. User-token updates are not permitted for this field."),
    speech_enabled_ivr_ports: str = typer.Option(None, "--speech-enabled-ivr-ports", help="Speech Enabled IVRPorts. User-token updates are not permitted for this field."),
    quality_management: bool = typer.Option(None, "--quality-management/--no-quality-management", help="Quality Management. User-token updates are not permitted for this field."),
    speech_enabled_ivr_overage: bool = typer.Option(None, "--speech-enabled-ivr-overage/--no-speech-enabled-ivr-overage", help="Speech Enabled IVROverage. User-token updates are not permitted for this field."),
    campaign_manager_overage: bool = typer.Option(None, "--campaign-manager-overage/--no-campaign-manager-overage", help="Campaign Manager Overage. User-token updates are not permitted for this field."),
    quality_management_overage: bool = typer.Option(None, "--quality-management-overage/--no-quality-management-overage", help="Quality Management Overage. User-token updates are not permitted for this field."),
    wfo_overage: bool = typer.Option(None, "--wfo-overage/--no-wfo-overage", help="Wfo Overage. User-token updates are not permitted for this field."),
    wfo_analytics_overage: bool = typer.Option(None, "--wfo-analytics-overage/--no-wfo-analytics-overage", help="Wfo Analytics Overage. User-token updates are not permitted for this field."),
    wfo_analytics_with_transcription_overage: bool = typer.Option(None, "--wfo-analytics-with-transcription-overage/--no-wfo-analytics-with-transcription-overage", help="Wfo Analytics With Transcription Overage. User-token updates are not permitted for this field."),
    wfo_bundle_overage: bool = typer.Option(None, "--wfo-bundle-overage/--no-wfo-bundle-overage", help="Wfo Bundle Overage. User-token updates are not permitted for this field."),
    web_call_back_enabled: bool = typer.Option(None, "--web-call-back-enabled/--no-web-call-back-enabled", help="Web Call Back Enabled. User-token updates are not permitted for this field."),
    check_agent_availability: bool = typer.Option(None, "--check-agent-availability/--no-check-agent-availability", help="Check Agent Availability. User-token updates are not permitted for this field."),
    offer_code: str = typer.Option(None, "--offer-code", help="Offer Code. User-token updates are not permitted for this field. (use --help for choices)"),
    order_id: str = typer.Option(None, "--order-id", help="Order Id. User-token updates are not permitted for this field."),
    license: str = typer.Option(None, "--license", help="License. User-token updates are not permitted for this field."),
    service_provisioning_id: str = typer.Option(None, "--service-provisioning-id", help="Service Provisioning Id. User-token updates are not permitted for this field."),
    order_subscription_id: str = typer.Option(None, "--order-subscription-id", help="Order Subscription Id. User-token updates are not permitted for this field."),
    cisco_pstn_did: bool = typer.Option(None, "--cisco-pstn-did/--no-cisco-pstn-did", help="Cisco Pstn DID. User-token updates are not permitted for this field."),
    cisco_pstn_tf: bool = typer.Option(None, "--cisco-pstn-tf/--no-cisco-pstn-tf", help="Cisco Pstn TF. User-token updates are not permitted for this field."),
    billing_group_id: str = typer.Option(None, "--billing-group-id", help="Billing Group Id. User-token updates are not permitted for this field."),
    outbound_sip_domain: str = typer.Option(None, "--outbound-sip-domain", help="Outbound Sip Domain. User-token updates are not permitted for this field."),
    purge_allowed: bool = typer.Option(None, "--purge-allowed/--no-purge-allowed", help="Purge Allowed. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    purge_inactive_entities_interval: str = typer.Option(None, "--purge-inactive-entities-interval", help="Purge Inactive Entities Interval. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    inactivate_entities_purged_on: str = typer.Option(None, "--inactivate-entities-purged-on", help="Inactivate Entities Purged On. User-token updates are not permitted for this field."),
    web_rtc_enabled: bool = typer.Option(None, "--web-rtc-enabled/--no-web-rtc-enabled", help="Web Rtc Enabled. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    mask_sensitive_data: bool = typer.Option(None, "--mask-sensitive-data/--no-mask-sensitive-data", help="Mask Sensitive Data. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    ai_assistant_quantity: str = typer.Option(None, "--ai-assistant-quantity", help="Ai Assistant Quantity. User-token updates are not permitted for this field."),
    routing_to_same_agent: str = typer.Option(None, "--routing-to-same-agent", help="Choices: DISABLED, ENABLED"),
    byova_offer_quantity: str = typer.Option(None, "--byova-offer-quantity", help="Byova Offer Quantity. User-token updates are not permitted for this field."),
    wholesale_order: bool = typer.Option(None, "--wholesale-order/--no-wholesale-order", help="Wholesale Order. User-token updates are not permitted for this field."),
    home_region: str = typer.Option(None, "--home-region", help="Home region of the organization User-token updates are not permitted for this field."),
    multi_region_enabled: bool = typer.Option(None, "--multi-region-enabled/--no-multi-region-enabled", help="Indicates whether multi-region is enabled for the organization User-token updates are not permitted for this field."),
    workforce_management_enabled: bool = typer.Option(None, "--workforce-management-enabled/--no-workforce-management-enabled", help="Indicates whether workforce management is enabled for the organization User-token updates are not permitted for this field."),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity. User-token updates are not permitted for this field."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity. User-token updates are not permitted for this field."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Organization Setting by ID.\n\n\b\nExample: wxcli cc-org-settings update ID --tenant-xml-url TENANT_XML_URL --ivr-park-url IVR_PARK_URL --wfo-enabled --campaign-manager-enabled --configure-speech-enabled-ivr-enabled --short-call-threshold SHORT_CALL_THRESHOLD --lost-call-threshold LOST_CALL_THRESHOLD --voice-contact-surge-factor VOICE_CONTACT_SURGE_FACTOR --digital-contact-surge-factor DIGITAL_CONTACT_SURGE_FACTOR --maximum-active-calls MAXIMUM_ACTIVE_CALLS --inbound-maximum-active-calls INBOUND_MAXIMUM_ACTIVE_CALLS --outdial-maximum-active-calls OUTDIAL_MAXIMUM_ACTIVE_CALLS --allow-agent-thresholds --pause-resume-enabled --recording-pause-duration RECORDING_PAUSE_DURATION --record-all-calls --webex-management-enabled --retry-callback-interval RETRY_CALLBACK_INTERVAL --maximum-callback-attempts MAXIMUM_CALLBACK_ATTEMPTS --ccc-enabled --sbr-enabled --maximum-text-skills MAXIMUM_TEXT_SKILLS --maximum-skills MAXIMUM_SKILLS --multi-media-enabled --max-channels MAX_CHANNELS --voice-call-back-enabled --jukebox-enabled --pruning-strategy NONE --pruning-value PRUNING_VALUE --analytics-enabled --maximum-virtual-teams MAXIMUM_VIRTUAL_TEAMS --maximum-address-books MAXIMUM_ADDRESS_BOOKS --number-of-cad-variables NUMBER_OF_CAD_VARIABLES --threshold-alerts-enabled --last-agent-routing --leg-recording-enabled --multiple-time-zone-enabled --steering-digits-enabled --social-channel --flow-builder-enabled --resources-created --wfo-analytics-with-transcription --wfo-bundle --quality-management --speech-enabled-ivr-overage --campaign-manager-overage --quality-management-overage --wfo-overage --wfo-analytics-overage --wfo-analytics-with-transcription-overage --wfo-bundle-overage --web-call-back-enabled --check-agent-availability --offer-code CJPPRM --cisco-pstn-did --cisco-pstn-tf\n\n\b\nExample --json-body: '{"tenantXmlUrl":"...","ivrParkUrl":"...","wfoEnabled":true,"campaignManagerEnabled":true,"configureSpeechEnabledIVREnabled":true,"shortCallThreshold":0,"lostCallThreshold":0,"voiceContactSurgeFactor":0,"digitalContactSurgeFactor":0,"maximumActiveCalls":0,"inboundMaximumActiveCalls":0,"outdialMaximumActiveCalls":0,"allowAgentThresholds":true,"pauseResumeEnabled":true,"recordingPauseDuration":0,"recordAllCalls":true,"webexManagementEnabled":true,"retryCallbackInterval":0,"maximumCallbackAttempts":0,"cccEnabled":true,"sbrEnabled":true,"maximumTextSkills":0,"maximumSkills":0,"multiMediaEnabled":true,"maxChannels":0,"voiceCallBackEnabled":true,"jukeboxEnabled":true,"pruningStrategy":"NONE","pruningValue":0,"analyticsEnabled":true,"maximumVirtualTeams":0,"maximumAddressBooks":0,"numberOfCadVariables":0,"thresholdAlertsEnabled":true,"lastAgentRouting":true,"legRecordingEnabled":true,"multipleTimeZoneEnabled":true,"steeringDigitsEnabled":true,"socialChannel":true,"flowBuilderEnabled":true,"resourcesCreated":true,"wfoAnalyticsWithTranscription":true,"wfoBundle":true,"qualityManagement":true,"speechEnabledIVROverage":true,"campaignManagerOverage":true,"qualityManagementOverage":true,"wfoOverage":true,"wfoAnalyticsOverage":true,"wfoAnalyticsWithTranscriptionOverage":true,"wfoBundleOverage":true,"webCallBackEnabled":true,"checkAgentAvailability":true,"offerCode":"CJPPRM","ciscoPstnDID":true,"ciscoPstnTF":true,"organizationId":"...","id":"...","version":0,"concurrentVoiceContactEntitlement":0,"concurrentDigitalContactEntitlement":0,"basicNativeVirtualAgentQuantity":0,"maximumThresholdRules":0,"recordingMode":"AUDIO_ONLY","webexManagementUrl":"...","licenseVersion":"...","adapterId":"...","otgId":"...","externalId":"...","voicePrefix":"...","wfoBundleAgents":0,"speechEnabledIVRPorts":0,"orderId":"...","license":"...","serviceProvisioningId":"...","orderSubscriptionId":"...","billingGroupId":"...","outboundSipDomain":"...","purgeAllowed":true,"purgeInactiveEntitiesInterval":0,"inactivateEntitiesPurgedOn":"...","webRtcEnabled":true,"maskSensitiveData":true,"aiAssistantQuantity":0,"routingToSameAgent":"DISABLED","byovaOfferQuantity":0,"wholesaleOrder":true,"homeRegion":"...","multiRegionEnabled":true,"workforceManagementEnabled":true,"transcriptsKmsKeyMetadata":{"keyUrl":"...","kroUrl":"...","updatedTimestamp":"..."},"offerDetails":[{"offerCode":"...","licenseVolume":0}],"createdTime":0,"lastUpdatedTime":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/organization-setting/{id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if organization_id is not None:
            body["organizationId"] = organization_id
        if id_param is not None:
            body["id"] = id_param
        if version is not None:
            body["version"] = version
        if tenant_xml_url is not None:
            body["tenantXmlUrl"] = tenant_xml_url
        if ivr_park_url is not None:
            body["ivrParkUrl"] = ivr_park_url
        if wfo_enabled is not None:
            body["wfoEnabled"] = wfo_enabled
        if campaign_manager_enabled is not None:
            body["campaignManagerEnabled"] = campaign_manager_enabled
        if configure_speech_enabled_ivr_enabled is not None:
            body["configureSpeechEnabledIVREnabled"] = configure_speech_enabled_ivr_enabled
        if short_call_threshold is not None:
            body["shortCallThreshold"] = short_call_threshold
        if lost_call_threshold is not None:
            body["lostCallThreshold"] = lost_call_threshold
        if concurrent_voice_contact_entitlement is not None:
            body["concurrentVoiceContactEntitlement"] = concurrent_voice_contact_entitlement
        if voice_contact_surge_factor is not None:
            body["voiceContactSurgeFactor"] = voice_contact_surge_factor
        if concurrent_digital_contact_entitlement is not None:
            body["concurrentDigitalContactEntitlement"] = concurrent_digital_contact_entitlement
        if digital_contact_surge_factor is not None:
            body["digitalContactSurgeFactor"] = digital_contact_surge_factor
        if basic_native_virtual_agent_quantity is not None:
            body["basicNativeVirtualAgentQuantity"] = basic_native_virtual_agent_quantity
        if maximum_active_calls is not None:
            body["maximumActiveCalls"] = maximum_active_calls
        if inbound_maximum_active_calls is not None:
            body["inboundMaximumActiveCalls"] = inbound_maximum_active_calls
        if outdial_maximum_active_calls is not None:
            body["outdialMaximumActiveCalls"] = outdial_maximum_active_calls
        if maximum_threshold_rules is not None:
            body["maximumThresholdRules"] = maximum_threshold_rules
        if allow_agent_thresholds is not None:
            body["allowAgentThresholds"] = allow_agent_thresholds
        if pause_resume_enabled is not None:
            body["pauseResumeEnabled"] = pause_resume_enabled
        if recording_pause_duration is not None:
            body["recordingPauseDuration"] = recording_pause_duration
        if record_all_calls is not None:
            body["recordAllCalls"] = record_all_calls
        if recording_mode is not None:
            body["recordingMode"] = recording_mode
        if webex_management_enabled is not None:
            body["webexManagementEnabled"] = webex_management_enabled
        if webex_management_url is not None:
            body["webexManagementUrl"] = webex_management_url
        if license_version is not None:
            body["licenseVersion"] = license_version
        if adapter_id is not None:
            body["adapterId"] = adapter_id
        if otg_id is not None:
            body["otgId"] = otg_id
        if retry_callback_interval is not None:
            body["retryCallbackInterval"] = retry_callback_interval
        if maximum_callback_attempts is not None:
            body["maximumCallbackAttempts"] = maximum_callback_attempts
        if ccc_enabled is not None:
            body["cccEnabled"] = ccc_enabled
        if sbr_enabled is not None:
            body["sbrEnabled"] = sbr_enabled
        if maximum_text_skills is not None:
            body["maximumTextSkills"] = maximum_text_skills
        if maximum_skills is not None:
            body["maximumSkills"] = maximum_skills
        if multi_media_enabled is not None:
            body["multiMediaEnabled"] = multi_media_enabled
        if max_channels is not None:
            body["maxChannels"] = max_channels
        if voice_call_back_enabled is not None:
            body["voiceCallBackEnabled"] = voice_call_back_enabled
        if jukebox_enabled is not None:
            body["jukeboxEnabled"] = jukebox_enabled
        if pruning_strategy is not None:
            body["pruningStrategy"] = pruning_strategy
        if pruning_value is not None:
            body["pruningValue"] = pruning_value
        if analytics_enabled is not None:
            body["analyticsEnabled"] = analytics_enabled
        if maximum_virtual_teams is not None:
            body["maximumVirtualTeams"] = maximum_virtual_teams
        if maximum_address_books is not None:
            body["maximumAddressBooks"] = maximum_address_books
        if number_of_cad_variables is not None:
            body["numberOfCadVariables"] = number_of_cad_variables
        if external_id is not None:
            body["externalId"] = external_id
        if threshold_alerts_enabled is not None:
            body["thresholdAlertsEnabled"] = threshold_alerts_enabled
        if last_agent_routing is not None:
            body["lastAgentRouting"] = last_agent_routing
        if leg_recording_enabled is not None:
            body["legRecordingEnabled"] = leg_recording_enabled
        if multiple_time_zone_enabled is not None:
            body["multipleTimeZoneEnabled"] = multiple_time_zone_enabled
        if voice_prefix is not None:
            body["voicePrefix"] = voice_prefix
        if steering_digits_enabled is not None:
            body["steeringDigitsEnabled"] = steering_digits_enabled
        if social_channel is not None:
            body["socialChannel"] = social_channel
        if flow_builder_enabled is not None:
            body["flowBuilderEnabled"] = flow_builder_enabled
        if resources_created is not None:
            body["resourcesCreated"] = resources_created
        if wfo_analytics_with_transcription is not None:
            body["wfoAnalyticsWithTranscription"] = wfo_analytics_with_transcription
        if wfo_bundle_agents is not None:
            body["wfoBundleAgents"] = wfo_bundle_agents
        if wfo_bundle is not None:
            body["wfoBundle"] = wfo_bundle
        if speech_enabled_ivr_ports is not None:
            body["speechEnabledIVRPorts"] = speech_enabled_ivr_ports
        if quality_management is not None:
            body["qualityManagement"] = quality_management
        if speech_enabled_ivr_overage is not None:
            body["speechEnabledIVROverage"] = speech_enabled_ivr_overage
        if campaign_manager_overage is not None:
            body["campaignManagerOverage"] = campaign_manager_overage
        if quality_management_overage is not None:
            body["qualityManagementOverage"] = quality_management_overage
        if wfo_overage is not None:
            body["wfoOverage"] = wfo_overage
        if wfo_analytics_overage is not None:
            body["wfoAnalyticsOverage"] = wfo_analytics_overage
        if wfo_analytics_with_transcription_overage is not None:
            body["wfoAnalyticsWithTranscriptionOverage"] = wfo_analytics_with_transcription_overage
        if wfo_bundle_overage is not None:
            body["wfoBundleOverage"] = wfo_bundle_overage
        if web_call_back_enabled is not None:
            body["webCallBackEnabled"] = web_call_back_enabled
        if check_agent_availability is not None:
            body["checkAgentAvailability"] = check_agent_availability
        if offer_code is not None:
            body["offerCode"] = offer_code
        if order_id is not None:
            body["orderId"] = order_id
        if license is not None:
            body["license"] = license
        if service_provisioning_id is not None:
            body["serviceProvisioningId"] = service_provisioning_id
        if order_subscription_id is not None:
            body["orderSubscriptionId"] = order_subscription_id
        if cisco_pstn_did is not None:
            body["ciscoPstnDID"] = cisco_pstn_did
        if cisco_pstn_tf is not None:
            body["ciscoPstnTF"] = cisco_pstn_tf
        if billing_group_id is not None:
            body["billingGroupId"] = billing_group_id
        if outbound_sip_domain is not None:
            body["outboundSipDomain"] = outbound_sip_domain
        if purge_allowed is not None:
            body["purgeAllowed"] = purge_allowed
        if purge_inactive_entities_interval is not None:
            body["purgeInactiveEntitiesInterval"] = purge_inactive_entities_interval
        if inactivate_entities_purged_on is not None:
            body["inactivateEntitiesPurgedOn"] = inactivate_entities_purged_on
        if web_rtc_enabled is not None:
            body["webRtcEnabled"] = web_rtc_enabled
        if mask_sensitive_data is not None:
            body["maskSensitiveData"] = mask_sensitive_data
        if ai_assistant_quantity is not None:
            body["aiAssistantQuantity"] = ai_assistant_quantity
        if routing_to_same_agent is not None:
            body["routingToSameAgent"] = routing_to_same_agent
        if byova_offer_quantity is not None:
            body["byovaOfferQuantity"] = byova_offer_quantity
        if wholesale_order is not None:
            body["wholesaleOrder"] = wholesale_order
        if home_region is not None:
            body["homeRegion"] = home_region
        if multi_region_enabled is not None:
            body["multiRegionEnabled"] = multi_region_enabled
        if workforce_management_enabled is not None:
            body["workforceManagementEnabled"] = workforce_management_enabled
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, None, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



_BODY_SKELETON_UPDATE_ORGANIZATION_SETTING = '{"tenantXmlUrl":"...","ivrParkUrl":"...","wfoEnabled":true,"campaignManagerEnabled":true,"configureSpeechEnabledIVREnabled":true,"shortCallThreshold":0,"lostCallThreshold":0,"voiceContactSurgeFactor":0,"digitalContactSurgeFactor":0,"maximumActiveCalls":0,"inboundMaximumActiveCalls":0,"outdialMaximumActiveCalls":0,"allowAgentThresholds":true,"pauseResumeEnabled":true,"recordingPauseDuration":0,"recordAllCalls":true,"webexManagementEnabled":true,"retryCallbackInterval":0,"maximumCallbackAttempts":0,"cccEnabled":true,"sbrEnabled":true,"maximumTextSkills":0,"maximumSkills":0,"multiMediaEnabled":true,"maxChannels":0,"voiceCallBackEnabled":true,"jukeboxEnabled":true,"pruningStrategy":"NONE","pruningValue":0,"analyticsEnabled":true,"maximumVirtualTeams":0,"maximumAddressBooks":0,"numberOfCadVariables":0,"thresholdAlertsEnabled":true,"lastAgentRouting":true,"legRecordingEnabled":true,"multipleTimeZoneEnabled":true,"steeringDigitsEnabled":true,"socialChannel":true,"flowBuilderEnabled":true,"resourcesCreated":true,"wfoAnalyticsWithTranscription":true,"wfoBundle":true,"qualityManagement":true,"speechEnabledIVROverage":true,"campaignManagerOverage":true,"qualityManagementOverage":true,"wfoOverage":true,"wfoAnalyticsOverage":true,"wfoAnalyticsWithTranscriptionOverage":true,"wfoBundleOverage":true,"webCallBackEnabled":true,"checkAgentAvailability":true,"offerCode":"CJPPRM","ciscoPstnDID":true,"ciscoPstnTF":true,"organizationId":"...","id":"...","version":0,"concurrentVoiceContactEntitlement":0,"concurrentDigitalContactEntitlement":0,"basicNativeVirtualAgentQuantity":0,"maximumThresholdRules":0,"recordingMode":"AUDIO_ONLY","webexManagementUrl":"...","licenseVersion":"...","adapterId":"...","otgId":"...","externalId":"...","voicePrefix":"...","wfoBundleAgents":0,"speechEnabledIVRPorts":0,"orderId":"...","license":"...","serviceProvisioningId":"...","orderSubscriptionId":"...","billingGroupId":"...","outboundSipDomain":"...","purgeAllowed":true,"purgeInactiveEntitiesInterval":0,"inactivateEntitiesPurgedOn":"...","webRtcEnabled":true,"maskSensitiveData":true,"aiAssistantQuantity":0,"routingToSameAgent":"DISABLED","byovaOfferQuantity":0,"wholesaleOrder":true,"homeRegion":"...","multiRegionEnabled":true,"workforceManagementEnabled":true,"transcriptsKmsKeyMetadata":{"keyUrl":"...","kroUrl":"...","updatedTimestamp":"..."},"offerDetails":[{"offerCode":"...","licenseVolume":0}],"createdTime":0,"lastUpdatedTime":0}'

@app.command("update-organization-setting", short_help="Partially update Organization Setting by ID.")
def update_organization_setting(
    id: str = typer.Argument(help="UUID, from: wxcli cc-org-settings list"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations. User-token updates are not permitted for this field."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    tenant_xml_url: str = typer.Option(None, "--tenant-xml-url", help="Tenant Xml Url. User-token updates are not permitted for this field."),
    ivr_park_url: str = typer.Option(None, "--ivr-park-url", help="Ivr Park Url. User-token updates are not permitted for this field."),
    wfo_enabled: bool = typer.Option(None, "--wfo-enabled/--no-wfo-enabled", help="Wfo Enabled. User-token updates are not permitted for this field."),
    campaign_manager_enabled: bool = typer.Option(None, "--campaign-manager-enabled/--no-campaign-manager-enabled", help="Campaign Manager Enabled. User-token updates are not permitted for this field."),
    configure_speech_enabled_ivr_enabled: bool = typer.Option(None, "--configure-speech-enabled-ivr-enabled/--no-configure-speech-enabled-ivr-enabled", help="Configure Speech Enabled IVREnabled. User-token updates are not permitted for this field."),
    short_call_threshold: str = typer.Option(None, "--short-call-threshold", help="Short Call Threshold. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    lost_call_threshold: str = typer.Option(None, "--lost-call-threshold", help="Lost Call Threshold. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    concurrent_voice_contact_entitlement: str = typer.Option(None, "--concurrent-voice-contact-entitlement", help="Concurrent Voice Contact Entitlement. User-token updates are not permitted for this field."),
    voice_contact_surge_factor: str = typer.Option(None, "--voice-contact-surge-factor", help="Voice Contact Surge Factor. User-token updates are not permitted for this field."),
    concurrent_digital_contact_entitlement: str = typer.Option(None, "--concurrent-digital-contact-entitlement", help="Concurrent Digital Contact Entitlement. User-token updates are not permitted for this field."),
    digital_contact_surge_factor: str = typer.Option(None, "--digital-contact-surge-factor", help="Digital Contact Surge Factor. User-token updates are not permitted for this field."),
    basic_native_virtual_agent_quantity: str = typer.Option(None, "--basic-native-virtual-agent-quantity", help="Basic Native Virtual Agent Quantity. User-token updates are not permitted for this field."),
    maximum_active_calls: str = typer.Option(None, "--maximum-active-calls", help="Maximum Active Calls. User-token updates are not permitted for this field."),
    inbound_maximum_active_calls: str = typer.Option(None, "--inbound-maximum-active-calls", help="Inbound Maximum Active Calls. User-token updates are not permitted for this field."),
    outdial_maximum_active_calls: str = typer.Option(None, "--outdial-maximum-active-calls", help="Outdial Maximum Active Calls. User-token updates are not permitted for this field."),
    maximum_threshold_rules: str = typer.Option(None, "--maximum-threshold-rules", help="Maximum Threshold Rules. User-token updates are not permitted for this field."),
    allow_agent_thresholds: bool = typer.Option(None, "--allow-agent-thresholds/--no-allow-agent-thresholds", help="Allow Agent Thresholds. User-token updates are not permitted for this field."),
    pause_resume_enabled: bool = typer.Option(None, "--pause-resume-enabled/--no-pause-resume-enabled", help="Pause Resume Enabled. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    recording_pause_duration: str = typer.Option(None, "--recording-pause-duration", help="Recording Pause Duration. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    record_all_calls: bool = typer.Option(None, "--record-all-calls/--no-record-all-calls", help="Record All Calls. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    recording_mode: str = typer.Option(None, "--recording-mode", help="Choices: AUDIO_ONLY, AUDIO_AND_SCREEN, DISABLED"),
    webex_management_enabled: bool = typer.Option(None, "--webex-management-enabled/--no-webex-management-enabled", help="Webex Management Enabled. User-token updates are not permitted for this field."),
    webex_management_url: str = typer.Option(None, "--webex-management-url", help="Webex Management Url. User-token updates are not permitted for this field."),
    license_version: str = typer.Option(None, "--license-version", help="License Version. User-token updates are not permitted for this field."),
    adapter_id: str = typer.Option(None, "--adapter-id", help="Adapter Id. User-token updates are not permitted for this field."),
    otg_id: str = typer.Option(None, "--otg-id", help="Otg Id. User-token updates are not permitted for this field."),
    retry_callback_interval: str = typer.Option(None, "--retry-callback-interval", help="Retry Callback Interval. User-token updates are not permitted for this field."),
    maximum_callback_attempts: str = typer.Option(None, "--maximum-callback-attempts", help="Maximum Callback Attempts. User-token updates are not permitted for this field."),
    ccc_enabled: bool = typer.Option(None, "--ccc-enabled/--no-ccc-enabled", help="Ccc Enabled. User-token updates are not permitted for this field."),
    sbr_enabled: bool = typer.Option(None, "--sbr-enabled/--no-sbr-enabled", help="Sbr Enabled. User-token updates are not permitted for this field."),
    maximum_text_skills: str = typer.Option(None, "--maximum-text-skills", help="Maximum Text Skills. User-token updates are not permitted for this field."),
    maximum_skills: str = typer.Option(None, "--maximum-skills", help="Maximum Skills. User-token updates are not permitted for this field."),
    multi_media_enabled: bool = typer.Option(None, "--multi-media-enabled/--no-multi-media-enabled", help="Multi Media Enabled. User-token updates are not permitted for this field."),
    max_channels: str = typer.Option(None, "--max-channels", help="Max Channels. User-token updates are not permitted for this field."),
    voice_call_back_enabled: bool = typer.Option(None, "--voice-call-back-enabled/--no-voice-call-back-enabled", help="Voice Call Back Enabled. User-token updates are not permitted for this field."),
    jukebox_enabled: bool = typer.Option(None, "--jukebox-enabled/--no-jukebox-enabled", help="Jukebox Enabled. User-token updates are not permitted for this field."),
    pruning_strategy: str = typer.Option(None, "--pruning-strategy", help="Choices: NONE, TIME_BASED, STORAGE_BASED, AGENT_MINUTES"),
    pruning_value: str = typer.Option(None, "--pruning-value", help="Pruning Value. User-token updates are not permitted for this field."),
    analytics_enabled: bool = typer.Option(None, "--analytics-enabled/--no-analytics-enabled", help="Analytics Enabled. User-token updates are not permitted for this field."),
    maximum_virtual_teams: str = typer.Option(None, "--maximum-virtual-teams", help="Maximum Virtual Teams. User-token updates are not permitted for this field."),
    maximum_address_books: str = typer.Option(None, "--maximum-address-books", help="Maximum Address Books. User-token updates are not permitted for this field."),
    number_of_cad_variables: str = typer.Option(None, "--number-of-cad-variables", help="Number Of Cad Variables. User-token updates are not permitted for this field."),
    external_id: str = typer.Option(None, "--external-id", help="External Id. User-token updates are not permitted for this field."),
    threshold_alerts_enabled: bool = typer.Option(None, "--threshold-alerts-enabled/--no-threshold-alerts-enabled", help="Threshold Alerts Enabled. User-token updates are not permitted for this field."),
    last_agent_routing: bool = typer.Option(None, "--last-agent-routing/--no-last-agent-routing", help="Last Agent Routing. User-token updates are not permitted for this field."),
    leg_recording_enabled: bool = typer.Option(None, "--leg-recording-enabled/--no-leg-recording-enabled", help="Leg Recording Enabled. User-token updates are not permitted for this field."),
    multiple_time_zone_enabled: bool = typer.Option(None, "--multiple-time-zone-enabled/--no-multiple-time-zone-enabled", help="Multiple Time Zone Enabled. User-token updates are not permitted for this field."),
    voice_prefix: str = typer.Option(None, "--voice-prefix", help="Voice Prefix. User-token updates are not permitted for this field."),
    steering_digits_enabled: bool = typer.Option(None, "--steering-digits-enabled/--no-steering-digits-enabled", help="Steering Digits Enabled. User-token updates are not permitted for this field."),
    social_channel: bool = typer.Option(None, "--social-channel/--no-social-channel", help="Social Channel. User-token updates are not permitted for this field."),
    flow_builder_enabled: bool = typer.Option(None, "--flow-builder-enabled/--no-flow-builder-enabled", help="Flow Builder Enabled. User-token updates are not permitted for this field."),
    resources_created: bool = typer.Option(None, "--resources-created/--no-resources-created", help="Resources Created. User-token updates are not permitted for this field."),
    wfo_analytics_with_transcription: bool = typer.Option(None, "--wfo-analytics-with-transcription/--no-wfo-analytics-with-transcription", help="Wfo Analytics With Transcription. User-token updates are not permitted for this field."),
    wfo_bundle_agents: str = typer.Option(None, "--wfo-bundle-agents", help="Wfo Bundle Agents. User-token updates are not permitted for this field."),
    wfo_bundle: bool = typer.Option(None, "--wfo-bundle/--no-wfo-bundle", help="Wfo Bundle. User-token updates are not permitted for this field."),
    speech_enabled_ivr_ports: str = typer.Option(None, "--speech-enabled-ivr-ports", help="Speech Enabled IVRPorts. User-token updates are not permitted for this field."),
    quality_management: bool = typer.Option(None, "--quality-management/--no-quality-management", help="Quality Management. User-token updates are not permitted for this field."),
    speech_enabled_ivr_overage: bool = typer.Option(None, "--speech-enabled-ivr-overage/--no-speech-enabled-ivr-overage", help="Speech Enabled IVROverage. User-token updates are not permitted for this field."),
    campaign_manager_overage: bool = typer.Option(None, "--campaign-manager-overage/--no-campaign-manager-overage", help="Campaign Manager Overage. User-token updates are not permitted for this field."),
    quality_management_overage: bool = typer.Option(None, "--quality-management-overage/--no-quality-management-overage", help="Quality Management Overage. User-token updates are not permitted for this field."),
    wfo_overage: bool = typer.Option(None, "--wfo-overage/--no-wfo-overage", help="Wfo Overage. User-token updates are not permitted for this field."),
    wfo_analytics_overage: bool = typer.Option(None, "--wfo-analytics-overage/--no-wfo-analytics-overage", help="Wfo Analytics Overage. User-token updates are not permitted for this field."),
    wfo_analytics_with_transcription_overage: bool = typer.Option(None, "--wfo-analytics-with-transcription-overage/--no-wfo-analytics-with-transcription-overage", help="Wfo Analytics With Transcription Overage. User-token updates are not permitted for this field."),
    wfo_bundle_overage: bool = typer.Option(None, "--wfo-bundle-overage/--no-wfo-bundle-overage", help="Wfo Bundle Overage. User-token updates are not permitted for this field."),
    web_call_back_enabled: bool = typer.Option(None, "--web-call-back-enabled/--no-web-call-back-enabled", help="Web Call Back Enabled. User-token updates are not permitted for this field."),
    check_agent_availability: bool = typer.Option(None, "--check-agent-availability/--no-check-agent-availability", help="Check Agent Availability. User-token updates are not permitted for this field."),
    offer_code: str = typer.Option(None, "--offer-code", help="Offer Code. User-token updates are not permitted for this field. (use --help for choices)"),
    order_id: str = typer.Option(None, "--order-id", help="Order Id. User-token updates are not permitted for this field."),
    license: str = typer.Option(None, "--license", help="License. User-token updates are not permitted for this field."),
    service_provisioning_id: str = typer.Option(None, "--service-provisioning-id", help="Service Provisioning Id. User-token updates are not permitted for this field."),
    order_subscription_id: str = typer.Option(None, "--order-subscription-id", help="Order Subscription Id. User-token updates are not permitted for this field."),
    cisco_pstn_did: bool = typer.Option(None, "--cisco-pstn-did/--no-cisco-pstn-did", help="Cisco Pstn DID. User-token updates are not permitted for this field."),
    cisco_pstn_tf: bool = typer.Option(None, "--cisco-pstn-tf/--no-cisco-pstn-tf", help="Cisco Pstn TF. User-token updates are not permitted for this field."),
    billing_group_id: str = typer.Option(None, "--billing-group-id", help="Billing Group Id. User-token updates are not permitted for this field."),
    outbound_sip_domain: str = typer.Option(None, "--outbound-sip-domain", help="Outbound Sip Domain. User-token updates are not permitted for this field."),
    purge_allowed: bool = typer.Option(None, "--purge-allowed/--no-purge-allowed", help="Purge Allowed. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    purge_inactive_entities_interval: str = typer.Option(None, "--purge-inactive-entities-interval", help="Purge Inactive Entities Interval. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    inactivate_entities_purged_on: str = typer.Option(None, "--inactivate-entities-purged-on", help="Inactivate Entities Purged On. User-token updates are not permitted for this field."),
    web_rtc_enabled: bool = typer.Option(None, "--web-rtc-enabled/--no-web-rtc-enabled", help="Web Rtc Enabled. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    mask_sensitive_data: bool = typer.Option(None, "--mask-sensitive-data/--no-mask-sensitive-data", help="Mask Sensitive Data. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    ai_assistant_quantity: str = typer.Option(None, "--ai-assistant-quantity", help="Ai Assistant Quantity. User-token updates are not permitted for this field."),
    routing_to_same_agent: str = typer.Option(None, "--routing-to-same-agent", help="Choices: DISABLED, ENABLED"),
    byova_offer_quantity: str = typer.Option(None, "--byova-offer-quantity", help="Byova Offer Quantity. User-token updates are not permitted for this field."),
    wholesale_order: bool = typer.Option(None, "--wholesale-order/--no-wholesale-order", help="Wholesale Order. User-token updates are not permitted for this field."),
    home_region: str = typer.Option(None, "--home-region", help="Home region of the organization User-token updates are not permitted for this field."),
    multi_region_enabled: bool = typer.Option(None, "--multi-region-enabled/--no-multi-region-enabled", help="Indicates whether multi-region is enabled for the organization User-token updates are not permitted for this field."),
    workforce_management_enabled: bool = typer.Option(None, "--workforce-management-enabled/--no-workforce-management-enabled", help="Indicates whether workforce management is enabled for the organization User-token updates are not permitted for this field."),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity. User-token updates are not permitted for this field."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity. User-token updates are not permitted for this field."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Partially update Organization Setting by ID.\n\n\b\nExample: wxcli cc-org-settings update-organization-setting ID --tenant-xml-url TENANT_XML_URL --ivr-park-url IVR_PARK_URL --wfo-enabled --campaign-manager-enabled --configure-speech-enabled-ivr-enabled --short-call-threshold SHORT_CALL_THRESHOLD --lost-call-threshold LOST_CALL_THRESHOLD --voice-contact-surge-factor VOICE_CONTACT_SURGE_FACTOR --digital-contact-surge-factor DIGITAL_CONTACT_SURGE_FACTOR --maximum-active-calls MAXIMUM_ACTIVE_CALLS --inbound-maximum-active-calls INBOUND_MAXIMUM_ACTIVE_CALLS --outdial-maximum-active-calls OUTDIAL_MAXIMUM_ACTIVE_CALLS --allow-agent-thresholds --pause-resume-enabled --recording-pause-duration RECORDING_PAUSE_DURATION --record-all-calls --webex-management-enabled --retry-callback-interval RETRY_CALLBACK_INTERVAL --maximum-callback-attempts MAXIMUM_CALLBACK_ATTEMPTS --ccc-enabled --sbr-enabled --maximum-text-skills MAXIMUM_TEXT_SKILLS --maximum-skills MAXIMUM_SKILLS --multi-media-enabled --max-channels MAX_CHANNELS --voice-call-back-enabled --jukebox-enabled --pruning-strategy NONE --pruning-value PRUNING_VALUE --analytics-enabled --maximum-virtual-teams MAXIMUM_VIRTUAL_TEAMS --maximum-address-books MAXIMUM_ADDRESS_BOOKS --number-of-cad-variables NUMBER_OF_CAD_VARIABLES --threshold-alerts-enabled --last-agent-routing --leg-recording-enabled --multiple-time-zone-enabled --steering-digits-enabled --social-channel --flow-builder-enabled --resources-created --wfo-analytics-with-transcription --wfo-bundle --quality-management --speech-enabled-ivr-overage --campaign-manager-overage --quality-management-overage --wfo-overage --wfo-analytics-overage --wfo-analytics-with-transcription-overage --wfo-bundle-overage --web-call-back-enabled --check-agent-availability --offer-code CJPPRM --cisco-pstn-did --cisco-pstn-tf\n\n\b\nExample --json-body: '{"tenantXmlUrl":"...","ivrParkUrl":"...","wfoEnabled":true,"campaignManagerEnabled":true,"configureSpeechEnabledIVREnabled":true,"shortCallThreshold":0,"lostCallThreshold":0,"voiceContactSurgeFactor":0,"digitalContactSurgeFactor":0,"maximumActiveCalls":0,"inboundMaximumActiveCalls":0,"outdialMaximumActiveCalls":0,"allowAgentThresholds":true,"pauseResumeEnabled":true,"recordingPauseDuration":0,"recordAllCalls":true,"webexManagementEnabled":true,"retryCallbackInterval":0,"maximumCallbackAttempts":0,"cccEnabled":true,"sbrEnabled":true,"maximumTextSkills":0,"maximumSkills":0,"multiMediaEnabled":true,"maxChannels":0,"voiceCallBackEnabled":true,"jukeboxEnabled":true,"pruningStrategy":"NONE","pruningValue":0,"analyticsEnabled":true,"maximumVirtualTeams":0,"maximumAddressBooks":0,"numberOfCadVariables":0,"thresholdAlertsEnabled":true,"lastAgentRouting":true,"legRecordingEnabled":true,"multipleTimeZoneEnabled":true,"steeringDigitsEnabled":true,"socialChannel":true,"flowBuilderEnabled":true,"resourcesCreated":true,"wfoAnalyticsWithTranscription":true,"wfoBundle":true,"qualityManagement":true,"speechEnabledIVROverage":true,"campaignManagerOverage":true,"qualityManagementOverage":true,"wfoOverage":true,"wfoAnalyticsOverage":true,"wfoAnalyticsWithTranscriptionOverage":true,"wfoBundleOverage":true,"webCallBackEnabled":true,"checkAgentAvailability":true,"offerCode":"CJPPRM","ciscoPstnDID":true,"ciscoPstnTF":true,"organizationId":"...","id":"...","version":0,"concurrentVoiceContactEntitlement":0,"concurrentDigitalContactEntitlement":0,"basicNativeVirtualAgentQuantity":0,"maximumThresholdRules":0,"recordingMode":"AUDIO_ONLY","webexManagementUrl":"...","licenseVersion":"...","adapterId":"...","otgId":"...","externalId":"...","voicePrefix":"...","wfoBundleAgents":0,"speechEnabledIVRPorts":0,"orderId":"...","license":"...","serviceProvisioningId":"...","orderSubscriptionId":"...","billingGroupId":"...","outboundSipDomain":"...","purgeAllowed":true,"purgeInactiveEntitiesInterval":0,"inactivateEntitiesPurgedOn":"...","webRtcEnabled":true,"maskSensitiveData":true,"aiAssistantQuantity":0,"routingToSameAgent":"DISABLED","byovaOfferQuantity":0,"wholesaleOrder":true,"homeRegion":"...","multiRegionEnabled":true,"workforceManagementEnabled":true,"transcriptsKmsKeyMetadata":{"keyUrl":"...","kroUrl":"...","updatedTimestamp":"..."},"offerDetails":[{"offerCode":"...","licenseVolume":0}],"createdTime":0,"lastUpdatedTime":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ORGANIZATION_SETTING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/organization-setting/{id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if organization_id is not None:
            body["organizationId"] = organization_id
        if id_param is not None:
            body["id"] = id_param
        if version is not None:
            body["version"] = version
        if tenant_xml_url is not None:
            body["tenantXmlUrl"] = tenant_xml_url
        if ivr_park_url is not None:
            body["ivrParkUrl"] = ivr_park_url
        if wfo_enabled is not None:
            body["wfoEnabled"] = wfo_enabled
        if campaign_manager_enabled is not None:
            body["campaignManagerEnabled"] = campaign_manager_enabled
        if configure_speech_enabled_ivr_enabled is not None:
            body["configureSpeechEnabledIVREnabled"] = configure_speech_enabled_ivr_enabled
        if short_call_threshold is not None:
            body["shortCallThreshold"] = short_call_threshold
        if lost_call_threshold is not None:
            body["lostCallThreshold"] = lost_call_threshold
        if concurrent_voice_contact_entitlement is not None:
            body["concurrentVoiceContactEntitlement"] = concurrent_voice_contact_entitlement
        if voice_contact_surge_factor is not None:
            body["voiceContactSurgeFactor"] = voice_contact_surge_factor
        if concurrent_digital_contact_entitlement is not None:
            body["concurrentDigitalContactEntitlement"] = concurrent_digital_contact_entitlement
        if digital_contact_surge_factor is not None:
            body["digitalContactSurgeFactor"] = digital_contact_surge_factor
        if basic_native_virtual_agent_quantity is not None:
            body["basicNativeVirtualAgentQuantity"] = basic_native_virtual_agent_quantity
        if maximum_active_calls is not None:
            body["maximumActiveCalls"] = maximum_active_calls
        if inbound_maximum_active_calls is not None:
            body["inboundMaximumActiveCalls"] = inbound_maximum_active_calls
        if outdial_maximum_active_calls is not None:
            body["outdialMaximumActiveCalls"] = outdial_maximum_active_calls
        if maximum_threshold_rules is not None:
            body["maximumThresholdRules"] = maximum_threshold_rules
        if allow_agent_thresholds is not None:
            body["allowAgentThresholds"] = allow_agent_thresholds
        if pause_resume_enabled is not None:
            body["pauseResumeEnabled"] = pause_resume_enabled
        if recording_pause_duration is not None:
            body["recordingPauseDuration"] = recording_pause_duration
        if record_all_calls is not None:
            body["recordAllCalls"] = record_all_calls
        if recording_mode is not None:
            body["recordingMode"] = recording_mode
        if webex_management_enabled is not None:
            body["webexManagementEnabled"] = webex_management_enabled
        if webex_management_url is not None:
            body["webexManagementUrl"] = webex_management_url
        if license_version is not None:
            body["licenseVersion"] = license_version
        if adapter_id is not None:
            body["adapterId"] = adapter_id
        if otg_id is not None:
            body["otgId"] = otg_id
        if retry_callback_interval is not None:
            body["retryCallbackInterval"] = retry_callback_interval
        if maximum_callback_attempts is not None:
            body["maximumCallbackAttempts"] = maximum_callback_attempts
        if ccc_enabled is not None:
            body["cccEnabled"] = ccc_enabled
        if sbr_enabled is not None:
            body["sbrEnabled"] = sbr_enabled
        if maximum_text_skills is not None:
            body["maximumTextSkills"] = maximum_text_skills
        if maximum_skills is not None:
            body["maximumSkills"] = maximum_skills
        if multi_media_enabled is not None:
            body["multiMediaEnabled"] = multi_media_enabled
        if max_channels is not None:
            body["maxChannels"] = max_channels
        if voice_call_back_enabled is not None:
            body["voiceCallBackEnabled"] = voice_call_back_enabled
        if jukebox_enabled is not None:
            body["jukeboxEnabled"] = jukebox_enabled
        if pruning_strategy is not None:
            body["pruningStrategy"] = pruning_strategy
        if pruning_value is not None:
            body["pruningValue"] = pruning_value
        if analytics_enabled is not None:
            body["analyticsEnabled"] = analytics_enabled
        if maximum_virtual_teams is not None:
            body["maximumVirtualTeams"] = maximum_virtual_teams
        if maximum_address_books is not None:
            body["maximumAddressBooks"] = maximum_address_books
        if number_of_cad_variables is not None:
            body["numberOfCadVariables"] = number_of_cad_variables
        if external_id is not None:
            body["externalId"] = external_id
        if threshold_alerts_enabled is not None:
            body["thresholdAlertsEnabled"] = threshold_alerts_enabled
        if last_agent_routing is not None:
            body["lastAgentRouting"] = last_agent_routing
        if leg_recording_enabled is not None:
            body["legRecordingEnabled"] = leg_recording_enabled
        if multiple_time_zone_enabled is not None:
            body["multipleTimeZoneEnabled"] = multiple_time_zone_enabled
        if voice_prefix is not None:
            body["voicePrefix"] = voice_prefix
        if steering_digits_enabled is not None:
            body["steeringDigitsEnabled"] = steering_digits_enabled
        if social_channel is not None:
            body["socialChannel"] = social_channel
        if flow_builder_enabled is not None:
            body["flowBuilderEnabled"] = flow_builder_enabled
        if resources_created is not None:
            body["resourcesCreated"] = resources_created
        if wfo_analytics_with_transcription is not None:
            body["wfoAnalyticsWithTranscription"] = wfo_analytics_with_transcription
        if wfo_bundle_agents is not None:
            body["wfoBundleAgents"] = wfo_bundle_agents
        if wfo_bundle is not None:
            body["wfoBundle"] = wfo_bundle
        if speech_enabled_ivr_ports is not None:
            body["speechEnabledIVRPorts"] = speech_enabled_ivr_ports
        if quality_management is not None:
            body["qualityManagement"] = quality_management
        if speech_enabled_ivr_overage is not None:
            body["speechEnabledIVROverage"] = speech_enabled_ivr_overage
        if campaign_manager_overage is not None:
            body["campaignManagerOverage"] = campaign_manager_overage
        if quality_management_overage is not None:
            body["qualityManagementOverage"] = quality_management_overage
        if wfo_overage is not None:
            body["wfoOverage"] = wfo_overage
        if wfo_analytics_overage is not None:
            body["wfoAnalyticsOverage"] = wfo_analytics_overage
        if wfo_analytics_with_transcription_overage is not None:
            body["wfoAnalyticsWithTranscriptionOverage"] = wfo_analytics_with_transcription_overage
        if wfo_bundle_overage is not None:
            body["wfoBundleOverage"] = wfo_bundle_overage
        if web_call_back_enabled is not None:
            body["webCallBackEnabled"] = web_call_back_enabled
        if check_agent_availability is not None:
            body["checkAgentAvailability"] = check_agent_availability
        if offer_code is not None:
            body["offerCode"] = offer_code
        if order_id is not None:
            body["orderId"] = order_id
        if license is not None:
            body["license"] = license
        if service_provisioning_id is not None:
            body["serviceProvisioningId"] = service_provisioning_id
        if order_subscription_id is not None:
            body["orderSubscriptionId"] = order_subscription_id
        if cisco_pstn_did is not None:
            body["ciscoPstnDID"] = cisco_pstn_did
        if cisco_pstn_tf is not None:
            body["ciscoPstnTF"] = cisco_pstn_tf
        if billing_group_id is not None:
            body["billingGroupId"] = billing_group_id
        if outbound_sip_domain is not None:
            body["outboundSipDomain"] = outbound_sip_domain
        if purge_allowed is not None:
            body["purgeAllowed"] = purge_allowed
        if purge_inactive_entities_interval is not None:
            body["purgeInactiveEntitiesInterval"] = purge_inactive_entities_interval
        if inactivate_entities_purged_on is not None:
            body["inactivateEntitiesPurgedOn"] = inactivate_entities_purged_on
        if web_rtc_enabled is not None:
            body["webRtcEnabled"] = web_rtc_enabled
        if mask_sensitive_data is not None:
            body["maskSensitiveData"] = mask_sensitive_data
        if ai_assistant_quantity is not None:
            body["aiAssistantQuantity"] = ai_assistant_quantity
        if routing_to_same_agent is not None:
            body["routingToSameAgent"] = routing_to_same_agent
        if byova_offer_quantity is not None:
            body["byovaOfferQuantity"] = byova_offer_quantity
        if wholesale_order is not None:
            body["wholesaleOrder"] = wholesale_order
        if home_region is not None:
            body["homeRegion"] = home_region
        if multi_region_enabled is not None:
            body["multiRegionEnabled"] = multi_region_enabled
        if workforce_management_enabled is not None:
            body["workforceManagementEnabled"] = workforce_management_enabled
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, None, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("list-organization-setting", short_help="List Organization Settings.")
def list_organization_setting(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. All the fields are supported except: organizationId, inactivateEntitiesPurgedOn, createdTime, lastUpdatedTime The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported."),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(name) The examples below show some search queries - \"Cisco\" - field==\"name\";value==\"Cisco\" - fields=in=(\"name\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Organization Settings."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/organization-setting"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if attributes is not None:
        params["attributes"] = attributes
    if search is not None:
        params["search"] = search
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)


