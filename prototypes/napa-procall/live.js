/* ================================================================
   live.js — swaps the mock Wxcc adapter for the real
   @webex/contact-center SDK. Loaded only when you click "Go Live".

   Every signature below was read from the installed package's
   TypeScript definitions (v3.12.0), not from documentation.
   ================================================================ */

const LIVE = {
  webex:null, cc:null, task:null, profile:null, muted:false,
  connecting:false, queues:[], entryPoints:[], buddies:[],

  /* Every goLive() used to call Webex.init() without disposing the previous
     instance. The orphans keep their websockets and WebRTC device
     registrations alive, and after a few reconnects service discovery starts
     failing with:
        service-interceptor: 'wcc-api-gateway' is not a known service
     which looks like an outage but is purely local accumulation. Always tear
     the old session down first. */
  async teardown(){
    if(!LIVE.webex) return;
    trace('note','disposing previous SDK session before reconnecting');
    /* Order matters. deregister() explicitly LEAVES the agent logged in to the
       contact center (per the SDK's own docs) — it only drops the websocket and
       listeners. The next Webex.init() then finds a live station session whose
       WebRTC device died with the old instance, attempts an internal
       silentRelogin, and fails with "Error while performing silentRelogin".
       Log the station out first, then deregister. */
    try { if(LIVE.cc) await LIVE.cc.stationLogout({logoutReason:'Reconnecting POS prototype'}); }
    catch(e){ trace('note','stationLogout during teardown: '+e.message); }
    try { if(LIVE.cc) await LIVE.cc.deregister(); }
    catch(e){ trace('note','deregister: '+e.message); }
    await new Promise(r=>setTimeout(r,1200));
    LIVE.webex=null; LIVE.cc=null; LIVE.task=null; LIVE.profile=null;
    setMode(false);
  },

  async connect(token, loginOption){
    if(typeof Webex === 'undefined'){
      trace('note','SDK not loaded — is vendor/contact-center.min.js present?'); return;
    }
    if(LIVE.connecting){ trace('note','already connecting — ignoring'); return; }
    LIVE.connecting = true;
    try { await LIVE.teardown(); } finally {}
    trace('call', "Webex.init({credentials:{access_token:'…'}})");
    const webex = Webex.init({credentials:{access_token: token}});
    await new Promise(res => webex.once('ready', res));
    LIVE.webex = webex; LIVE.cc = webex.cc;
    trace('evt','webex ready');

    /* register() opens the websocket and returns the agent's profile */
    trace('call', "webex.cc.register()");
    const profile = await webex.cc.register();
    LIVE.profile = profile;
    trace('evt', "registered as "+profile.agentMailId+" ("+profile.agentId+")");
    /* TRAP: the shipped .d.ts declares Team = {teamId, teamName}, but the
       runtime payload is {id, name, teamType, ...}. Reading teamId gives
       undefined and stationLogin then fails with a bare
       "Error while performing stationLogin". Accept both, and fall back to
       profile.currentTeamId which the platform also populates. */
    trace('note', "teams: "+profile.teams.map(t=>t.name||t.teamName).join(', ')+
                  " | webRtcEnabled: "+profile.webRtcEnabled+
                  " | loginVoiceOptions: "+JSON.stringify(profile.loginVoiceOptions));

    /* Use the codes the platform actually returns rather than our
       hardcoded list — this picks up the 11 PROCall codes automatically. */
    if(profile.wrapupCodes?.length){
      const byName = Object.fromEntries(profile.wrapupCodes.map(c=>[c.name, c.id]));
      let matched=0;
      DISPOSITIONS.forEach(d=>{ if(byName[d.label]){ d.auxCodeId=byName[d.label]; matched++; } });
      trace('note', "wrap-up codes from platform: "+profile.wrapupCodes.length+
                    ", matched to dispositions: "+matched+"/"+DISPOSITIONS.length);
      renderDispList();
    }
    if(profile.idleCodes?.length){
      IDLE_CODES.length = 0;
      /* id "0" is the pseudo-code for Available, not a real idle reason —
         it already has its own entry at the top of the state menu. */
      profile.idleCodes.filter(c=>c.id!=='0')
        .forEach(c=>IDLE_CODES.push({name:c.name, id:c.id}));
      document.getElementById('stateMenu')?.remove(); buildStateMenu();
      trace('note', "idle codes from platform: "+profile.idleCodes.map(c=>c.name).join(', '));
    }

    const t0 = profile.teams?.[0] || {};
    const teamId = t0.id || t0.teamId || profile.currentTeamId;
    if(!teamId){ trace('note','no teamId resolvable from profile — cannot station login'); return; }

    /* An existing station session must be dropped first. Adopting it looks
       like it works — register() succeeds and state changes to Idle are
       accepted — but the WebRTC endpoint belongs to whichever page/app did
       the original stationLogin, so THIS page has no media and the platform
       refuses to make the agent Available. allowMultiLogin also defaults to
       false, so we cannot simply log in a second time alongside it. */
    let adoptExisting = false;
    if(profile.isAgentLoggedIn){
      trace('note','isAgentLoggedIn=true (deviceType '+profile.deviceType+') — '+
                   'dropping the existing station session so this page owns the media');
      trace('call', "webex.cc.stationLogout({logoutReason:'Switching to POS'})");
      try {
        await webex.cc.stationLogout({logoutReason:'Switching to POS'});
        await new Promise(r=>setTimeout(r,1500));
      } catch(e){
        const msg = e.message || String(e);
        trace('note','stationLogout failed: '+msg);
        /* AGENT_HAS_ASSIGNED_CONTACTS means a contact is still attached to the
           agent — almost always an unfinished wrap-up. The platform will refuse
           BOTH logout and a fresh login (AGENT_SESSION_ALREADY_EXISTS), so
           forcing a new station login here just hard-fails and locks the agent
           out of the prototype entirely. Adopt the existing session instead and
           let the agent finish the wrap-up that is holding it. */
        if(/ASSIGNED_CONTACTS/i.test(msg)){
          adoptExisting = true;
          trace('note','a contact is still assigned — most likely an unfinished wrap-up.');
          trace('note','adopting the existing session so the pending wrap-up can be completed.');
        } else {
          adoptExisting = true;
          trace('note','could not drop the old session; adopting it rather than failing.');
        }
      }
    }

    const params = {teamId, loginOption};
    if(loginOption !== 'BROWSER'){
      const dn = profile.defaultDn || profile.dn || document.getElementById('liveDn')?.value;
      if(!dn){ trace('note','loginOption '+loginOption+' needs a dialNumber; profile has none'); return; }
      params.dialNumber = dn;
    }
    if(adoptExisting){
      trace('note','skipping stationLogin — the platform already holds a session for this agent');
      trace('note','if audio does not work, finish the pending wrap-up then reload');
    } else {
      trace('call', "webex.cc.stationLogin("+JSON.stringify(params)+")");
      await webex.cc.stationLogin(params);
    }

    LIVE.wireEvents();
    LIVE.swapAdapter();
    await LIVE.loadDestinations();
    setStatePill('ready','Ready (Voice,VM)');
    Wxcc.state='IDLE';
    trace('evt','agent:stationLoginSuccess — LIVE');
    setMode(true);
    LIVE.connecting = false;
  },

  wireEvents(){
    const cc = LIVE.cc;
    /* Verified event names from the SDK types. Note there is no
       task:assigned / task:wrappedup — the real names are below. */
    cc.on('agent:stationLoginFailed', e => trace('note','stationLoginFailed: '+JSON.stringify(e)));
    cc.on('agent:stateChangeSuccess', e => trace('evt','agent:stateChangeSuccess'));
    cc.on('agent:stateChangeFailed',  e => trace('note','agent:stateChangeFailed: '+JSON.stringify(e)));

    cc.on('task:incoming', async task => {
      trace('evt','task:incoming');
      /* An outdial is delivered to the agent as an offered contact, i.e. through
         this same event — startOutdial() itself returns an AQM response, not a
         Task. Without this branch a call you just placed pops the "Incoming
         Call" Accept/Decline dialog, which is nonsense. */
      if(LIVE.outboundPending){
        const dest = LIVE.outboundPending; LIVE.outboundPending = null;
        LIVE.attachTask(task, {outbound:true});
        trace('note','outbound task bound (dialled '+dest+') — auto-accepting the agent leg');
        try { await task.accept(); } catch(e){ trace('note','outbound accept: '+(e.message||e)); }
        LIVE.showCallBar({label:'Active Call'});
        LIVE.startTimer();
        return;
      }
      LIVE.attachTask(task);
      /* Verified path: task.data.interaction.callProcessingDetails.{ani,dnis}.
         It is callProcessingDetails, NOT callAssociatedDetails — the latter
         does not exist and silently yields undefined on every call. */
      const cpd = task.data?.interaction?.callProcessingDetails || {};
      const ani  = cpd.ani || cpd.displayAni || 'unknown';
      const dnis = cpd.dnis || '';
      trace('note','ANI '+ani+(cpd.displayAni&&cpd.displayAni!==ani?' (display '+cpd.displayAni+')':'')+
                   ' → DNIS '+dnis);
      LIVE.screenPop(ani, dnis);

    });
  },

  /* Shared by inbound and outbound. An outbound task comes back from
     startOutdial() and never fires task:incoming, so without this the call bar
     would simply never appear for a click-to-dial call. */
  attachTask(task, meta){
    LIVE.task = task;
    const outbound = !!(meta && meta.outbound);
    LIVE.probeFlowData(task);

    task.on('task:media', track => {
      const a = document.getElementById('remote-audio');
      a.srcObject = new MediaStream([track]);
      a.play().catch(err => trace('note','audio play blocked: '+err.message));
      trace('evt','task:media — audio attached');
    });
    task.on('task:ringing', () => {
      trace('evt','task:ringing');
      if(outbound) LIVE.showCallBar({label:'Dialing…', ringing:true});
    });
    task.on('task:established', () => {
      trace('evt','task:established');
      LIVE.showCallBar({label:'Active Call'});
      LIVE.startTimer();
    });
    /* Recording. Verified in the SDK source shipped in vendor/*.map:
         Task.pauseRecording()                  services/task/index.ts:968
         Task.resumeRecording({autoResumed})    services/task/index.ts:1060
         event names                            services/task/types.ts:300-324
       The button is driven ONLY by these events, never by the click. WxCC
       auto-resumes after the tenant's pauseDuration and announces it with the
       same task:recordingResumed a manual resume produces — a local boolean
       would drift and show "paused" over a live recording. */
    task.on('task:recordingPaused',  () => {
      trace('evt','task:recordingPaused'); Wxcc.recPaused=true;
      setRecordBtn('paused'); cbAlert('');
    });
    task.on('task:recordingResumed', () => {
      trace('evt','task:recordingResumed'); Wxcc.recPaused=false;
      setRecordBtn('recording'); cbAlert('');
    });
    /* A failed pause is the dangerous one: the agent asked for silence, did not
       get it, and is about to read a card number onto the recording. Say so in
       the call bar, not in the trace panel. */
    task.on('task:recordingPauseFailed', e => {
      trace('note','recordingPauseFailed: '+JSON.stringify(e));
      Wxcc.recPaused=false; setRecordBtn(LIVE.recordState());
      cbAlert('⚠ Recording did NOT pause — do not read card details.');
    });
    task.on('task:recordingResumeFailed', e => {
      trace('note','recordingResumeFailed: '+JSON.stringify(e));
      setRecordBtn(LIVE.recordState());
      cbAlert('⚠ Recording did NOT resume.');
    });
    task.on('task:hold',   () => trace('evt','task:hold'));
    task.on('task:end',    () => { trace('evt','task:end'); LIVE.toWrapup(); });
    task.on('task:ended',  () => trace('evt','task:ended'));
    task.on('task:error',  e  => trace('note','task:error '+JSON.stringify(e)));
  },

  /* Recording state is read off the task, never tracked locally. All four
     fields live on callProcessingDetails (services/task/types.ts:605-614) and
     are STRINGS, not booleans — 'true'/'false'. pauseResumeEnabled reflects the
     queue's Control Hub recording config; if it isn't on, the button must read
     "Pause N/A" rather than looking armed. */
  recordState(task){
    const c = (task || LIVE.task)?.data?.interaction?.callProcessingDetails || {};
    const yes = v => String(v).toLowerCase() === 'true';
    if(!yes(c.pauseResumeEnabled)) return 'unavailable';
    if(!yes(c.recordInProgress) && !yes(c.recordingStarted)) return 'off';
    return yes(c.isPaused) ? 'paused' : 'recording';
  },

  /* Render everything the flow delivered with this call into the two on-screen
     panels (screen pop + order screen), and mirror a summary to the trace.

     The SDK declares callProcessingDetails as a CLOSED set with no index
     signature, but this codebase has already caught the types lying about the
     wire format twice (Team.teamId vs .id; StateChange not exported). So we
     display what ARRIVED rather than what the type says can arrive. Keys the
     type does not declare are your flow's own variables — they sort to the top
     and are marked ★. */
  probeFlowData(task){
    const i   = task?.data?.interaction || {};
    const cpd = i.callProcessingDetails || {};
    /* callFlowParams is the DECLARED home for flow variables — an open
       Record<string, {name, value, valueDataType, …}>, so arbitrary keys are
       expected here, not a surprise (services/task/types.ts:736-751). */
    const fp  = i.callFlowParams || {};
    const custom = renderFlowData(cpd, null, fp);
    trace('note','flow: '+(cpd.workflowName||'(none)')+
                 ' | queue: '+(cpd.virtualTeamName||cpd.QueueId||'?'));
    trace('note','callFlowParams: '+(Object.keys(fp).length || 'EMPTY')+
                 ' | callProcessingDetails: '+Object.keys(cpd).length+' keys');
    trace('note','flow-set values on screen: '+(custom.length ? custom.join(', ') : 'NONE'));
    /* Newer SDK builds (v3.12.0-next.96+) also carry callAssociatedData and
       callAssociatedDetails. The vendored build declares neither — log them
       anyway, because the wire payload is not limited by the shipped types. */
    console.log('[WXCC PROBE] callFlowParams', fp);
    console.log('[WXCC PROBE] callProcessingDetails', cpd);
    console.log('[WXCC PROBE] callAssociatedData', i.callAssociatedData);
    console.log('[WXCC PROBE] callAssociatedDetails', i.callAssociatedDetails);
    console.log('[WXCC PROBE] interaction keys', Object.keys(i));
    console.log('[WXCC PROBE] task.data', task?.data);
  },

  /* Bring up the persistent call bar. Used by accept() and by outbound dial. */
  showCallBar({label, ringing}={}){
    Wxcc.state='CONNECTED'; Wxcc.held=false; LIVE.muted=false;
    setStatePill('oncall','On Call');
    document.getElementById('callBar').classList.remove('hidden');
    document.getElementById('statStrip').classList.add('hidden');
    document.getElementById('holdLabel').textContent='Hold';
    document.getElementById('muteLabel').textContent='Mute';
    document.getElementById('btnHold').classList.remove('on');
    document.getElementById('btnMute').classList.remove('on');
    Wxcc.recPaused=false; setRecordBtn(LIVE.recordState()); cbAlert('');
    const live=document.querySelector('.callbar-live');
    if(live) live.innerHTML='<span class="pulse"></span> '+(label||'Active Call');
    /* Hold/transfer are meaningless until the far end answers. */
    document.getElementById('btnHold').disabled = !!ringing;
    document.getElementById('btnMute').disabled = !!ringing;
    showView('order');
  },

  startTimer(){
    clearInterval(Wxcc.timer); Wxcc.seconds=0;
    document.getElementById('callTimer').textContent='0:00';
    document.getElementById('btnHold').disabled=false;
    document.getElementById('btnMute').disabled=false;
    Wxcc.timer=setInterval(()=>{ Wxcc.seconds++;
      document.getElementById('callTimer').textContent=fmt(Wxcc.seconds); },1000);
  },

  /* Match the inbound ANI against the POS customer book, exactly as the
     mock does — this is the screen pop. */
  screenPop(ani, dnis){
    const cust = matchCustomer(ani);
    document.getElementById('popName').textContent = cust ? cust.name : 'Unknown caller';
    /* Always show the number the customer is ACTUALLY calling from. Showing the
       account's primary number instead is misleading — the agent needs to know
       which line rang, and on a matched-by-alternate-number call the two differ. */
    const realAni = fmtAni(ani);
    const primary = cust ? cust.phone : null;
    document.getElementById('popNum').textContent = realAni;
    const sub = document.getElementById('popStore');
    if(cust && primary && last10(primary) !== last10(ani)){
      sub.textContent = cust.name+' • primary on file '+primary;
    } else if(cust){
      sub.textContent = 'DM001 - Main Store';
    }
    document.getElementById('popAcct').textContent = cust ? cust.acct.replace(/[^0-9|]/g,'').trim() : '—';
    document.querySelector('.pop-badges').innerHTML = cust
      ? '<span class="chip c-green">Customer Identified</span>'+
        cust.badges.map(b=>'<span class="chip '+b[1]+'">'+b[0]+'</span>').join('')
      : '<span class="chip c-gray">Not in customer book</span>';
    /* Keep the order screen consistent with whoever actually called. */
    if(cust){
      document.getElementById('cbCust').textContent = cust.name+' ('+cust.acct.replace(/[^0-9|]/g,'').trim()+')';
      document.getElementById('cbNum').textContent  = cust.phone;
    } else {
      document.getElementById('cbCust').textContent = 'Unidentified caller';
      document.getElementById('cbNum').textContent  = fmtAni(ani);
    }
    trace('note', cust ? 'screen pop → '+cust.name : 'no customer match for '+ani);
    /* Open the flow-data panel on the pop: when the ANI does NOT match, these
       variables are the next place to look for an account number. */
    toggleFlowBox('popFlow', true);
    Wxcc.state='RINGING';
    openModal('modal-incoming');
  },

  toWrapup(){
    clearInterval(Wxcc.timer);
    document.getElementById('acwDur').textContent = fmt(Wxcc.seconds);
    enterWrapup();
  },

  /* Pull the tenant's real routing targets so a transfer actually routes.
     The mock ships invented store phone numbers; those would fail live. */
  async loadDestinations(){
    const grab = async (label, fn) => {
      try { const r = await fn(); return r?.data?.data || r?.data || []; }
      catch(e){ trace('note', label+' failed: '+e.message); return []; }
    };
    LIVE.queues      = await grab('getQueues',      () => LIVE.cc.getQueues());
    LIVE.entryPoints = await grab('getEntryPoints', () => LIVE.cc.getEntryPoints());
    trace('note','routing targets: '+LIVE.queues.length+' queues, '+
                 LIVE.entryPoints.length+' entry points');

    /* Outbound needs a contact-centre ANI in E.164. Prefer an explicit override,
       otherwise ask the platform for the entries behind profile.outdialANIId. */
    LIVE.outdialAni = window.WXCC_LOCAL?.outdialAni || null;
    if(!LIVE.outdialAni && LIVE.profile?.outdialANIId){
      const rows = await grab('getOutdialAniEntries',
        () => LIVE.cc.getOutdialAniEntries({outdialANI: LIVE.profile.outdialANIId, page:0, pageSize:100}));
      const first = (Array.isArray(rows)?rows:[]).map(r=>r.number||r.dialNumber||r.ani).filter(Boolean)[0];
      if(first) LIVE.outdialAni = first.startsWith('+') ? first : '+'+first.replace(/\D/g,'');
    }
    trace('note', LIVE.outdialAni
      ? 'outdial ANI: '+LIVE.outdialAni
      : 'no outdial ANI resolved — outbound calls will be refused until you set outdialAni in local-token.js');
  },

  async refreshBuddies(){
    try {
      const r = await LIVE.cc.getBuddyAgents({mediaType:'telephony', state:'Available'});
      LIVE.buddies = r?.data?.agentList || [];
      if(!LIVE.buddies.length)
        trace('note','no buddy agents Available — sign agent2@ or supervisor@ in and set them Available');
    } catch(e){ LIVE.buddies=[]; trace('note','getBuddyAgents failed: '+e.message); }
  },

  /* Replace every mock method with the real SDK call. The UI is untouched. */
  swapAdapter(){
    const T = () => LIVE.task;

    /* Real destinations replace the invented store list. Warm consult can
       target an ENTRYPOINT; a cold transfer cannot, so it uses QUEUE. */
    window.renderDest = async () => {
      const kind = document.querySelector('input[name=tdest]:checked').value;
      const warm = document.querySelector('input[name=ttype]:checked').value==='warm';
      const q    = (document.getElementById('destSearch').value||'').toLowerCase();
      const el   = document.getElementById('destList');
      let rows=[];
      if(kind==='store'){
        const src = warm && LIVE.entryPoints?.length ? LIVE.entryPoints : LIVE.queues;
        const kindLabel = (warm && LIVE.entryPoints?.length) ? 'entry point' : 'queue';
        rows = (src||[]).filter(x=>(x.name||'').toLowerCase().includes(q)).map(x=>({
          id:x.id, t:x.name, s:kindLabel+' • '+(x.channelType||'TELEPHONY'), r:'', ok:x.active!==false }));
      } else if(kind==='agent'){
        await LIVE.refreshBuddies();
        rows = (LIVE.buddies||[]).filter(a=>JSON.stringify(a).toLowerCase().includes(q)).map(a=>({
          id:a.agentId||a.id, t:a.agentName||a.name||a.agentId, s:(a.state||'Available')+' • '+(a.teamName||''), r:'', ok:true }));
      } else {
        rows=[{id:q.replace(/\D/g,'')||'', t:q?('Dial '+q):'Type a number above', s:'external • DIALNUMBER', r:'', ok:!!q}];
      }
      el.innerHTML = rows.length ? rows.map(r=>
        '<div class="dest" data-id="'+r.id+'" onclick="selectDest(this)">'+
          '<div><div class="dest-name">'+r.t+'</div><div class="dest-sub">'+r.s+'</div></div>'+
          '<div style="text-align:right">'+(r.ok?'<span class="tams up">● active</span>':'<span class="tams down">● inactive</span>')+'</div>'+
        '</div>').join('')
        : '<div style="padding:14px" class="muted">Nothing available for this destination type.</div>';
    };

    Wxcc.simulateIncoming = () => trace('note','LIVE mode — place a real call to the entry point');

    Wxcc.accept = async () => {
      closeModal('modal-incoming');
      trace('call','task.accept()');
      try { await T().accept(); } catch(e){ return trace('note','accept failed: '+e.message); }
      LIVE.showCallBar({label:'Active Call'});
      LIVE.startTimer();
    };

    Wxcc.decline = async () => {
      closeModal('modal-incoming'); trace('call','task.decline()');
      try { await T().decline(); } catch(e){ trace('note','decline failed: '+e.message); }
      Wxcc.state='IDLE';
    };

    Wxcc.toggleHold = async () => {
      Wxcc.held = !Wxcc.held;
      trace('call', Wxcc.held ? 'task.hold()' : 'task.resume()');
      try { Wxcc.held ? await T().hold() : await T().resume(); }
      catch(e){ Wxcc.held=!Wxcc.held; return trace('note','hold/resume failed: '+e.message); }
      document.getElementById('holdLabel').textContent = Wxcc.held ? 'Resume' : 'Hold';
      document.getElementById('btnHold').classList.toggle('on', Wxcc.held);
    };

    Wxcc.toggleMute = async () => {
      trace('call','task.toggleMute()');
      try { await T().toggleMute(); LIVE.muted=!LIVE.muted; }
      catch(e){ return trace('note','mute failed: '+e.message); }
      document.getElementById('muteLabel').textContent = LIVE.muted ? 'Unmute' : 'Mute';
      document.getElementById('btnMute').classList.toggle('on', LIVE.muted);
    };

    Wxcc.toggleRecording = async () => {
      const st = LIVE.recordState();
      if(st==='unavailable') return cbAlert('Pause/resume is not enabled for this queue in Control Hub.');
      if(st==='off')         return cbAlert('This interaction is not being recorded.');
      const pausing = st !== 'paused';
      trace('call', pausing ? 'task.pauseRecording()'
                            : 'task.resumeRecording({autoResumed:false})');
      try {
        if(pausing) await T().pauseRecording();
        else        await T().resumeRecording({autoResumed:false});
      } catch(e){
        trace('note','recording toggle failed: '+(e.message||e));
        setRecordBtn(LIVE.recordState());
        return cbAlert(pausing ? '⚠ Recording did NOT pause — do not read card details.'
                               : '⚠ Recording did NOT resume.');
      }
      /* No optimistic UI on purpose. A resolved promise means the platform
         ACCEPTED the request, not that recording stopped — the button flips on
         task:recordingPaused / task:recordingResumed and nowhere else. */
    };

    Wxcc.endCall = async () => {
      trace('call','task.end()');
      try { await T().end(); } catch(e){ trace('note','end failed: '+e.message); }
    };

    Wxcc.doTransfer = async () => {
      const warm = document.querySelector('input[name=ttype]:checked').value==='warm';
      const kind = document.querySelector('input[name=tdest]:checked').value;
      const sel  = document.querySelector('.dest.sel');
      if(!sel) return trace('note','pick a destination first');
      /* The enum VALUES are camelCase, not the KEY names. The shipped types
         declare them only as `string`:
             QUEUE:'queue'  DIALNUMBER:'dialNumber'
             AGENT:'agent'  ENTRYPOINT:'entryPoint'
         Sending 'QUEUE'/'AGENT' etc. is accepted without an obvious error and
         the call simply never moves. Also: entryPoint is consult-only, so a
         cold transfer to a store must use queue. */
      const dtype = kind==='agent' ? 'agent'
                  : kind==='number' ? 'dialNumber'
                  : (warm && LIVE.entryPoints?.length) ? 'entryPoint' : 'queue';
      const payload = {to: sel.dataset.id, destinationType: dtype};
      closeModal('modal-transfer');
      try {
        if(warm){
          trace('call','task.consult('+JSON.stringify({...payload, holdParticipants:true})+')');
          await T().consult({...payload, holdParticipants:true});
          document.getElementById('consultWho').textContent = sel.querySelector('.dest-name').textContent;
          document.getElementById('consultBar').classList.remove('hidden');
        } else {
          trace('call','task.transfer('+JSON.stringify(payload)+')');
          await T().transfer(payload);
        }
      } catch(e){ trace('note','transfer failed: '+e.message); }
    };

    Wxcc.completeConsult = async (mode) => {
      document.getElementById('consultBar').classList.add('hidden');
      try {
        if(mode==='conference'){ trace('call','task.consultConference()'); await T().consultConference(); }
        else { trace('call','task.consultTransfer()'); await T().consultTransfer(); }
      } catch(e){ trace('note','consult completion failed: '+e.message); }
    };

    Wxcc.endConsult = async () => {
      trace('call','task.endConsult()');
      document.getElementById('consultBar').classList.add('hidden');
      try { await T().endConsult(); } catch(e){ trace('note','endConsult failed: '+e.message); }
    };

    Wxcc.saveWrapup = async () => {
      /* Every failure below used to either throw uncaught or only whisper into
         the trace, so the dialog just sat there doing nothing. Surface it. */
      const d = (selectedDisp === null || selectedDisp === undefined)
        ? null : DISPOSITIONS[selectedDisp];
      if(!d)            return acwError('Pick a disposition first.');
      if(!d.auxCodeId)  return acwError('No WxCC wrap-up code is mapped to "'+d.label+'".');
      if(!T())          return acwError(
        'No live task to wrap up — the call handle was lost. '+
        'The wrap-up must be completed in Cisco Agent Desktop, or reload after it clears.');

      acwError('');
      trace('call',"task.wrapup({wrapUpReason:'"+d.label+"', auxCodeId:'"+d.auxCodeId+"'})");
      try { await T().wrapup({wrapUpReason:d.label, auxCodeId:d.auxCodeId}); }
      catch(e){
        const msg = e?.message || String(e);
        trace('note','wrapup failed: '+msg);
        return acwError('Wrap-up rejected by the platform: '+msg);
      }
      /* Clear WRAPUP before closing — closeModal() refuses while in wrap-up. */
      Wxcc.state='IDLE'; exitWrapup(); closeModal('modal-acw');
      selectedDisp=null; LIVE.task=null;
      renderFlowData({}, null, {});
      lines=[]; renderLines(); renderStock(null);
      document.getElementById('dispLabel').textContent='Select a disposition...';
      document.getElementById('btnSaveAcw').disabled=true;
      document.getElementById('acwNotes').value='';
      setStatePill('ready','Ready (Voice,VM)');
      document.getElementById('statStrip').classList.remove('hidden');
      showView('dashboard');
    };

    window.chooseState = async (auxId,name) => {
      document.getElementById('stateMenu').classList.add('hidden');
      /* GOTCHA: auxCodeId is mandatory for BOTH states. Going Available with
         {state:'Available'} alone fails with a bare "Error while performing
         setAgentState". The platform returns an idle code named "Available"
         whose id is the string "0" — that is what Available expects. None of
         this is visible in the shipped types (StateChange isn't even exported). */
      const payload = auxId ? {state:'Idle', auxCodeId:auxId}
                            : {state:'Available', auxCodeId:'0'};
      trace('call','webex.cc.setAgentState('+JSON.stringify(payload)+')');
      try { await LIVE.cc.setAgentState(payload); }
      catch(e){ return trace('note','setAgentState failed: '+e.message); }
      if(auxId){ setStatePill('wrap','Idle — '+name); Wxcc.state='IDLE_CODED'; }
      else { setStatePill('ready','Ready (Voice,VM)'); Wxcc.state='IDLE'; }
    };

    /* startOutdial(destination, origin) — two positional args, not an object.
       `origin` is the CONTACT CENTRE's outbound number in E.164 (per the SDK's
       own docs), NOT the agent's DN — passing profile.defaultDn was wrong, and
       on this tenant defaultDn is undefined anyway. entryPointId is added by
       the SDK itself from profile.outDialEp. */
    window.dial = async (num) => {
      const dest = e164(num);
      const origin = LIVE.outdialAni;
      if(!origin){
        trace('note','no outdial ANI available — set outdialAni in local-token.js to place outbound calls');
        return;
      }
      trace('call',"webex.cc.startOutdial('"+dest+"', '"+origin+"')");
      /* Show the bar immediately so the agent has End available while it rings —
         if the far end never answers there would otherwise be no way out. */
      document.getElementById('cbCust').textContent = matchCustomer(num)?.name || 'Outbound call';
      document.getElementById('cbNum').textContent  = fmtAni(dest);
      /* Drop the previous handle before the bar goes up: showCallBar() reads
         recording state off LIVE.task, and a finished task would leak its state
         onto a call that has not started yet. */
      LIVE.task = null;
      LIVE.outboundPending = dest;
      LIVE.showCallBar({label:'Dialing…', ringing:true});
      try {
        /* Returns TaskResponse (AgentContact | Error | void) — NOT an ITask.
           The usable Task arrives via the task:incoming handler above. */
        const res = await LIVE.cc.startOutdial(dest, origin);
        trace('evt','outdial accepted — interactionId '+(res?.data?.interactionId||'(n/a)'));
      } catch(e){
        LIVE.outboundPending = null;
        trace('note','startOutdial failed: '+(e.message||e));
        /* Roll the UI back rather than stranding the agent on a bar for a call
           that never started. */
        clearInterval(Wxcc.timer);
        document.getElementById('callBar').classList.add('hidden');
        document.getElementById('statStrip').classList.remove('hidden');
        Wxcc.state='IDLE'; setStatePill('ready','Ready (Voice,VM)');
      }
    };

    trace('note','adapter swapped — all controls now hit the live tenant');
  }
};

async function goLive(){
  const token=document.getElementById('liveToken').value.trim();
  const opt=document.getElementById('liveOpt').value;
  if(!token) return trace('note','paste an access token first');
  closeModal('modal-live');

  /* The SDK wants one Webex instance per page. Reconnecting in place — even
     with a clean stationLogout + deregister — leaves enough residue that the
     next register() fails ("not a known service", then "silentRelogin", then
     stationLogin). Rather than fight it, reconnect by reloading and carrying
     the credentials across in sessionStorage. Reliable and boring. */
  if(LIVE.webex){
    trace('note','already connected — reloading for a clean session');
    try { sessionStorage.setItem('wxcc.reconnect', JSON.stringify({token, opt})); } catch(e){}
    try { if(LIVE.cc) await LIVE.cc.stationLogout({logoutReason:'Reconnect'}); } catch(e){}
    location.reload();
    return;
  }

  try { await LIVE.connect(token, opt); }
  catch(e){
    LIVE.connecting=false;
    const msg = e.message||String(e);
    trace('note','connect failed: '+msg);
    if(/not a known service/i.test(msg)){
      trace('note','service discovery incomplete — this is the stacked-session bug. '+
                   'Reload the page (⌘R) and Go Live once; do not reconnect repeatedly in one page.');
    }
    setMode(false);
    console.error(e);
  }
}

/* The mock defaults the state pill to "Ready (Voice,VM)". With no session that
   reads as a live, ready agent — which is how a dead connection went unnoticed.
   Make the mode explicit and always visible instead. */
function setMode(isLive){
  const b=document.getElementById('liveBadge');
  b.classList.remove('hidden','c-green','c-gray');
  b.classList.add(isLive?'c-green':'c-gray');
  b.textContent = isLive ? '● LIVE' : '○ MOCK';
  if(!isLive && typeof Wxcc!=='undefined' && Wxcc.state!=='CONNECTED') {
    setStatePill('ready','Ready (Voice,VM)');
  }
}

/* Reloading without deregistering orphans the websocket and leaves a WebRTC
   device registered against the agent (Webex caps users at 5 devices). */
window.addEventListener('beforeunload', () => {
  try { LIVE.cc && LIVE.cc.deregister(); } catch(e){}
});

setMode(false);

/* Bring the session up on load: either resuming a reconnect that asked for a
   reload, or from the gitignored local-token.js. Reconnect wins if both exist. */
(function autoStart(){
  /* ?mock=1 suppresses auto-connect. An agent can hold only one station
     session, so opening a second tab that auto-connects will fight the real
     one. Use this to exercise the UI without touching the tenant. */
  if(/[?&]mock=1/.test(location.search)){
    trace('note','?mock=1 — auto-connect suppressed, staying in MOCK mode');
    return;
  }
  let saved=null;
  try { saved = JSON.parse(sessionStorage.getItem('wxcc.reconnect')||'null'); } catch(e){}
  if(saved) sessionStorage.removeItem('wxcc.reconnect');

  const cfg = saved
    ? {token:saved.token, opt:saved.opt, why:'resuming after reload', avail:true}
    : (window.WXCC_LOCAL && window.WXCC_LOCAL.autoConnect)
      ? {token:window.WXCC_LOCAL.token, opt:window.WXCC_LOCAL.loginOption||'BROWSER',
         why:'auto-connecting from local-token.js', avail:window.WXCC_LOCAL.autoAvailable!==false}
      : null;

  if(!cfg){
    if(window.WXCC_LOCAL?.token){
      document.getElementById('liveToken').value = window.WXCC_LOCAL.token;
      trace('note','token loaded from local-token.js — click Go Live when ready');
    }
    return;
  }

  /* live.js is the last script on the page, after a 1.8 MB SDK bundle, so the
     window 'load' event has usually ALREADY fired by the time this runs — a
     listener added here would never be called. Run immediately when the
     document is done, and only fall back to the event if it genuinely isn't. */
  const whenReady = fn => document.readyState === 'complete'
    ? setTimeout(fn, 0)
    : window.addEventListener('load', fn, {once:true});

  whenReady(async () => {
    trace('note', cfg.why);
    document.getElementById('liveToken').value = cfg.token;
    document.getElementById('liveOpt').value   = cfg.opt;
    try {
      await LIVE.connect(cfg.token, cfg.opt);
      if(cfg.avail && LIVE.profile){
        await new Promise(r=>setTimeout(r,800));
        await chooseState(null);          // Available (sends auxCodeId '0')
      }
    } catch(e){
      LIVE.connecting=false;
      trace('note','auto-connect failed: '+(e.message||e));
      if(/401|403|token/i.test(e.message||'')) trace('note','token may have expired — replace it in local-token.js');
      setMode(false);
    }
  });
})();
