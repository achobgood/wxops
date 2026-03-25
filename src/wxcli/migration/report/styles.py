"""CSS design system for the CUCM assessment report v3 (Authority Minimal).

Single constant `REPORT_CSS` — embedded directly into the HTML report
by the assembler.  Google Fonts loaded via <link> tags in the <head>
(see GOOGLE_FONTS_LINKS).
"""

GOOGLE_FONTS_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=IBM+Plex+Mono:wght@400;500;600&'
    'family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">'
)

REPORT_CSS = """\
/* ==========================================================================
   CUCM Assessment Report v3 — Authority Minimal Design System
   ========================================================================== */

/* -- Custom properties ---------------------------------------------------- */
:root {
    /* Core palette */
    --navy-900: #0f1729;
    --navy-800: #1e293b;

    /* Text hierarchy */
    --text-primary: #111827;
    --text-body:    #374151;
    --text-muted:   #6b7280;
    --text-faint:   #9ca3af;

    /* Accent */
    --accent:      #2563eb;
    --accent-tint: #eff6ff;

    /* Semantic status */
    --success:      #059669;
    --success-tint: #ecfdf5;
    --warning:      #d97706;
    --warning-tint: #fffbeb;
    --critical:     #dc2626;
    --critical-tint: #fef2f2;

    /* Chart colors */
    --chart-focal: #2563eb;
    --chart-gray:  #94a3b8;
    --chart-bg:    #f3f4f6;

    /* Surfaces */
    --surface:  #ffffff;
    --page-bg:  #f4f5f7;
    --border:       #e5e7eb;
    --border-strong: #d1d5db;

    /* Legacy aliases — referenced by appendix.py, explainer.py, charts.py */
    --color-primary:    var(--accent);
    --color-success:    var(--success);
    --color-warning:    var(--warning);
    --color-critical:   var(--critical);
    --color-text:       var(--text-primary);
    --color-text-muted: var(--text-muted);
    --color-text-light: var(--text-faint);
    --color-bg:         var(--surface);
    --color-border:     var(--border);
    --warm-50:          var(--page-bg);
    --slate-100:        #f1f5f9;
    --slate-300:        #cbd5e1;
    --slate-500:        #64748b;
    --slate-900:        var(--navy-900);

    /* Typography */
    --font-body: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
    --font-mono: 'IBM Plex Mono', 'Menlo', 'Consolas', monospace;

    /* Legacy font-size tokens (used in older templates) */
    --font-size-body:  0.9375rem;
    --font-size-small: 0.8125rem;
    --font-size-h1:    1.75rem;
    --font-size-h2:    1.375rem;
    --font-size-h3:    1.0625rem;
    --font-size-h4:    0.9375rem;

    /* Spacing — 8px grid */
    --spacing-xs:  4px;
    --spacing-sm:  8px;
    --spacing-md:  16px;
    --spacing-lg:  24px;
    --spacing-xl:  32px;
    --spacing-xxl: 48px;
}


/* -- Base reset & typography ---------------------------------------------- */
*, *::before, *::after {
    box-sizing: border-box;
}

html {
    font-size: 16px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

body {
    margin: 0;
    padding: 0;
    font-family: var(--font-body);
    font-weight: 400;
    line-height: 1.6;
    color: var(--text-body);
    background: var(--page-bg);
}


/* -- Sidebar layout ------------------------------------------------------- */
.sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 260px;
    height: 100vh;
    background: var(--navy-900);
    color: #fff;
    overflow-y: auto;
    padding: var(--spacing-lg) 0;
    z-index: 100;
}

.sidebar-header {
    padding: 0 var(--spacing-lg);
    margin-bottom: var(--spacing-lg);
}

.sidebar-kicker {
    display: block;
    font-size: 0.6rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: rgba(255,255,255,0.4);
    margin-bottom: 4px;
}

.sidebar-meta {
    font-size: 0.75rem;
    font-weight: 400;
    color: rgba(255,255,255,0.5);
    margin-top: 2px;
}

/* Legacy alias for sidebar brand */
.sidebar-brand {
    padding: 0 var(--spacing-lg);
    margin-bottom: var(--spacing-lg);
    font-size: 0.85rem;
    font-weight: 600;
    color: rgba(255,255,255,0.9);
    letter-spacing: 0.02em;
}

.sidebar-brand .brand-name {
    display: block;
    font-size: 1rem;
    color: #fff;
    margin-bottom: 2px;
}

.sidebar-brand .brand-sub {
    font-size: 0.7rem;
    font-weight: 400;
    color: rgba(255,255,255,0.5);
}

.sidebar nav {
    padding: 0;
}

.sidebar nav a {
    display: flex;
    align-items: center;
    padding: 8px var(--spacing-lg);
    color: rgba(255,255,255,0.6);
    text-decoration: none;
    font-size: 0.8rem;
    font-weight: 500;
    transition: background 0.15s, color 0.15s;
    gap: 8px;
}

.sidebar nav a:hover {
    background: var(--navy-800);
    color: rgba(255,255,255,0.9);
}

.sidebar nav a.active {
    background: rgba(255,255,255,0.08);
    color: #fff;
    border-left: 3px solid var(--accent);
    padding-left: calc(var(--spacing-lg) - 3px);
}

/* Nav dot (new) */
.sidebar nav .nav-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
}

.sidebar nav .nav-dot.exec {
    background: var(--accent);
}

.sidebar nav .nav-dot.tech {
    background: rgba(255,255,255,0.2);
}

/* Nav number (legacy alias) */
.sidebar nav .nav-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    font-size: 0.65rem;
    font-weight: 700;
    flex-shrink: 0;
}

.sidebar nav .nav-number.exec {
    background: var(--accent);
    color: #fff;
}

.sidebar nav .nav-number.tech {
    background: rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.7);
}

.sidebar .nav-divider {
    height: 1px;
    background: rgba(255,255,255,0.1);
    margin: var(--spacing-md) var(--spacing-lg);
}

.sidebar .nav-label {
    padding: var(--spacing-sm) var(--spacing-lg);
    font-size: 0.6rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: rgba(255,255,255,0.35);
}


/* -- Summary bar ---------------------------------------------------------- */
.summary-bar {
    position: fixed;
    top: 0;
    left: 260px;
    right: 0;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: var(--spacing-sm) var(--spacing-xl);
    display: flex;
    align-items: center;
    gap: 2.5rem;
    z-index: 90;
}

.summary-stat {
    text-align: center;
}

.summary-stat {
    display: flex;
    align-items: baseline;
    gap: 0.375rem;
}

.summary-stat .value,
.summary-stat .stat-value {
    font-family: var(--font-mono);
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
}

.summary-stat .label,
.summary-stat .stat-label {
    font-size: 0.6875rem;
    color: var(--text-muted);
}


/* -- Detail panel (main content area) ------------------------------------- */
.detail-panel {
    margin-left: 260px;
    padding-top: 3.5rem;
    min-height: 100vh;
}

.detail-panel-content {
    max-width: 720px;
    margin: 0 auto;
    padding: var(--spacing-xl) var(--spacing-lg);
}


/* -- Content card --------------------------------------------------------- */
.content-card {
    background: white;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 8px 32px rgba(0,0,0,0.06);
    padding: 2.5rem 3rem;
    margin-bottom: var(--spacing-xl);
}


/* -- Headings ------------------------------------------------------------- */
h1, h2, h3, h4 {
    font-family: var(--font-body);
    font-weight: 600;
    color: var(--text-primary);
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    line-height: 1.25;
    letter-spacing: -0.01em;
}

h1 {
    font-size: var(--font-size-h1);
    font-weight: 600;
    color: var(--text-primary);
    margin-top: 0;
}

h2 {
    font-size: var(--font-size-h2);
    color: var(--text-primary);
}

h3 { font-size: var(--font-size-h3); }
h4 { font-size: var(--font-size-h4); }


/* -- Section kicker ------------------------------------------------------- */
.section-kicker {
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    margin-bottom: var(--spacing-xs);
    display: block;
}


/* -- Paragraphs & prose --------------------------------------------------- */
p {
    margin: 0 0 var(--spacing-md);
}

.muted {
    color: var(--text-muted);
}

.small {
    font-size: var(--font-size-small);
}


/* -- Links ---------------------------------------------------------------- */
a {
    color: var(--accent);
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
}


/* -- Sections ------------------------------------------------------------- */
section {
    margin-bottom: var(--spacing-xxl);
}


/* -- Tables (editorial style) -------------------------------------------- */
table {
    width: 100%;
    border-collapse: collapse;
    margin: var(--spacing-md) 0 var(--spacing-lg);
    font-size: var(--font-size-small);
    font-variant-numeric: tabular-nums;
}

thead th {
    text-align: left;
    padding: var(--spacing-sm) var(--spacing-md);
    font-weight: 600;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    border-bottom: 2px solid var(--border);
}

tbody td {
    padding: var(--spacing-sm) var(--spacing-md);
    border-bottom: 1px solid var(--border);
    vertical-align: top;
    color: var(--text-body);
}

tbody tr:hover {
    background: var(--page-bg);
}

td.num, th.num {
    text-align: right;
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
}


/* -- Score gauge container ------------------------------------------------ */
.score-gauge {
    display: flex;
    justify-content: center;
    align-items: center;
    margin: var(--spacing-md) auto;
    max-width: 180px;
}

.score-gauge svg {
    width: 100%;
    height: auto;
}


/* -- Score breakdown bars ------------------------------------------------- */
.score-breakdown {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin: var(--spacing-md) 0;
}

.score-breakdown .factor-row {
    display: grid;
    grid-template-columns: 140px 1fr 40px;
    align-items: center;
    gap: 8px;
    font-size: 0.75rem;
}

.score-breakdown .factor-label {
    color: var(--text-muted);
    text-align: right;
    white-space: nowrap;
}

.score-breakdown .factor-bar {
    height: 8px;
    border-radius: 4px;
    background: var(--chart-bg);
    overflow: hidden;
}

.score-breakdown .factor-fill {
    height: 100%;
    border-radius: 4px;
}

.score-breakdown .factor-value {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--text-primary);
    text-align: right;
}


/* -- Key findings --------------------------------------------------------- */
.key-findings {
    list-style: none;
    padding: 0;
    margin: var(--spacing-md) 0;
}

.key-findings li {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.85rem;
    color: var(--text-body);
    line-height: 1.4;
}

.key-findings li:last-child {
    border-bottom: none;
}

.key-findings .finding-icon {
    flex-shrink: 0;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.7rem;
    margin-top: 1px;
}

.key-findings .finding-icon.check {
    background: var(--success-tint);
    color: #065f46;
}

.key-findings .finding-icon.alert {
    background: var(--warning-tint);
    color: #92400e;
}


/* -- Stat cards ----------------------------------------------------------- */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: var(--spacing-md);
    margin: var(--spacing-md) 0;
}

.stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: var(--spacing-md);
    text-align: center;
}

.stat-card .stat-number {
    font-family: var(--font-mono);
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1;
}

.stat-card .stat-label {
    font-size: 0.7rem;
    color: var(--text-muted);
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}


/* -- Effort bands --------------------------------------------------------- */
.effort-band {
    border-left: 3px solid var(--border-strong);
    background: var(--surface);
    padding: var(--spacing-md) var(--spacing-lg);
    margin: var(--spacing-md) 0;
}

.effort-band h4 {
    margin-top: 0;
    margin-bottom: var(--spacing-sm);
    font-size: 0.9rem;
}

.effort-band p {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: var(--spacing-sm);
}

.effort-band.auto {
    border-left: 3px solid var(--success);
    background: var(--success-tint);
}

.effort-band.auto h4 { color: var(--success); }

.effort-band.planning {
    border-left: 3px solid var(--warning);
    background: var(--warning-tint);
}

.effort-band.planning h4 { color: var(--warning); }

.effort-band.manual {
    border-left: 3px solid var(--critical);
    background: var(--critical-tint);
}

.effort-band.manual h4 { color: var(--critical); }

.effort-band ul {
    margin: 0;
    padding-left: var(--spacing-lg);
    font-size: 0.8rem;
    color: var(--text-body);
}

.effort-band ul li {
    margin-bottom: 4px;
}


/* -- Callouts ------------------------------------------------------------- */
.callout {
    padding: var(--spacing-md);
    margin: var(--spacing-md) 0;
    border-radius: 6px;
    border-left: 4px solid;
    background: var(--surface);
    border-color: var(--border);
}

.callout.success {
    border-left-color: var(--success);
    background: var(--success-tint);
}

.callout.warning {
    border-left-color: var(--warning);
    background: var(--warning-tint);
}

.callout.critical {
    border-left-color: var(--critical);
    background: var(--critical-tint);
}

.callout.info {
    border-left-color: var(--accent);
    background: var(--accent-tint);
}


/* -- Verdict callout ------------------------------------------------------ */
.verdict {
    padding: var(--spacing-lg);
    border-left: 3px solid var(--accent);
    background: var(--accent-tint);
    border-radius: 0 6px 6px 0;
    margin: var(--spacing-md) 0 var(--spacing-lg);
    font-size: 0.9rem;
    line-height: 1.6;
    color: var(--text-body);
}


/* -- Badges --------------------------------------------------------------- */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 0.75em;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.badge-direct   { background: var(--success-tint); color: #065f46; }
.badge-approx   { background: var(--warning-tint); color: #92400e; }
.badge-decision { background: var(--critical-tint); color: #991b1b; }
.badge-critical { background: var(--critical); color: #fff; }
.badge-high     { background: #b45309;          color: #fff; }
.badge-medium   { background: var(--warning);   color: #fff; }
.badge-low      { background: var(--success);   color: #fff; }


/* -- Technical reference interstitial ------------------------------------- */
.tech-interstitial {
    background: var(--navy-900);
    color: rgba(255,255,255,0.85);
    text-align: center;
    padding: var(--spacing-lg) var(--spacing-md);
    margin: var(--spacing-xxl) 0 var(--spacing-lg);
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
}


/* -- Details / Summary (collapsible appendix sections) -------------------- */
details {
    margin: var(--spacing-md) 0;
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
}

details[open] {
    border-color: var(--accent);
}

summary {
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--page-bg);
    font-weight: 600;
    cursor: pointer;
    list-style: none;
    user-select: none;
    color: var(--text-primary);
    font-size: 0.85rem;
}

summary::-webkit-details-marker {
    display: none;
}

summary::before {
    content: '\\25B6';
    display: inline-block;
    margin-right: var(--spacing-sm);
    font-size: 0.65em;
    transition: transform 0.15s ease;
}

details[open] > summary::before {
    transform: rotate(90deg);
}

summary .summary-count {
    font-weight: 400;
    color: var(--text-muted);
    font-size: 0.75rem;
    margin-left: 4px;
}

details > .details-content {
    padding: var(--spacing-md);
}


/* -- Explanation cards (decision detail) ---------------------------------- */
.explanation {
    padding: var(--spacing-md);
    margin: var(--spacing-md) 0;
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: 0 6px 6px 0;
    background: var(--surface);
}

.explanation h4 {
    margin-top: 0;
    color: var(--text-primary);
}

.explanation .reassurance {
    color: var(--text-muted);
    font-style: italic;
    margin-bottom: 0;
    font-size: 0.85rem;
}


/* -- Report header / footer ----------------------------------------------- */
.report-header {
    text-align: center;
    margin-bottom: var(--spacing-xxl);
}

.report-header .brand {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text-primary);
}

.report-header .meta {
    color: var(--text-muted);
    font-size: var(--font-size-small);
}

.report-footer {
    margin-top: var(--spacing-xxl);
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--border);
    text-align: center;
    color: var(--text-faint);
    font-size: var(--font-size-small);
}


/* -- Print header (hidden on screen) -------------------------------------- */
.print-header {
    display: none;
}


/* -- CSS topology --------------------------------------------------------- */
.css-topology {
    list-style: none;
    padding: 0;
    margin: var(--spacing-sm) 0;
    font-size: 0.8rem;
}

.css-topology li {
    padding: 4px 0 4px 18px;
    position: relative;
    color: var(--text-body);
}

.css-topology li::before {
    content: '';
    position: absolute;
    left: 4px;
    top: 10px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent);
}

.css-topology .partition {
    padding-left: 36px;
    color: var(--text-muted);
}

.css-topology .partition::before {
    left: 22px;
    width: 6px;
    height: 6px;
    background: var(--slate-300);
}


/* -- CTA box (Next Steps) ------------------------------------------------- */
.cta-box {
    background: var(--accent-tint);
    border: 2px solid var(--accent);
    border-radius: 8px;
    padding: var(--spacing-lg);
    text-align: center;
    margin: var(--spacing-lg) 0;
}

.cta-box h3 {
    color: var(--accent);
    margin-top: 0;
}


/* -- Decision resolution bar ---------------------------------------------- */
.resolution-bar {
    display: flex;
    height: 24px;
    border-radius: 4px;
    overflow: hidden;
    margin: var(--spacing-sm) 0;
}

.resolution-bar .bar-auto {
    background: var(--success);
}

.resolution-bar .bar-planning {
    background: var(--warning);
}

.resolution-bar .bar-manual {
    background: var(--critical);
}


/* ==========================================================================
   Print styles
   ========================================================================== */

@page {
    size: letter;
    margin: 0.75in 1in;
}

@media print {
    html {
        font-size: 10pt;
    }

    body {
        color: #000;
        background: #fff;
    }

    /* Hide sidebar on print, show print header */
    .sidebar,
    .summary-bar,
    .no-print {
        display: none !important;
    }

    .print-header {
        display: block;
        text-align: center;
        margin-bottom: var(--spacing-lg);
    }

    .detail-panel {
        margin-left: 0;
        padding-top: 0;
    }

    .detail-panel-content {
        max-width: none;
        padding: 0;
    }

    .content-card {
        max-width: none;
        box-shadow: none;
        border-radius: 0;
        padding: 0;
        background: transparent;
    }

    /* Page breaks */
    section {
        page-break-before: always;
    }

    section:first-of-type {
        page-break-before: avoid;
    }

    h2, h3 {
        page-break-after: avoid;
    }

    table, figure, .chart-container {
        page-break-inside: avoid;
    }

    /* Tables: ensure headers print */
    thead th {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    /* Details: force open for print */
    details {
        border: none;
    }

    details > summary {
        display: none;
    }

    details > .details-content {
        display: block !important;
        padding: var(--spacing-sm) 0;
    }

    /* Badges: ensure color prints */
    .badge,
    .effort-band,
    .callout {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    /* Tech interstitial */
    .tech-interstitial {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
}
"""
