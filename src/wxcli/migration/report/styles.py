"""CSS design system for the CUCM assessment report v4 (Editorial + v3 Data).

Single constant ``REPORT_CSS`` — embedded directly into the HTML report
by the assembler.  Google Fonts loaded via <link> tags in the <head>
(see GOOGLE_FONTS_LINKS).
"""

GOOGLE_FONTS_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=IBM+Plex+Mono:wght@400;500&'
    'family=Lora:ital,wght@0,400;0,600;0,700;1,400&'
    'family=Source+Sans+3:wght@300;400;500;600;700&display=swap" rel="stylesheet">'
)

REPORT_CSS = """\
/* ==========================================================================
   CUCM Assessment Report v4 — Editorial Design System
   ========================================================================== */

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    /* -- Warm neutrals ---------------------------------------------------- */
    --warm-50:  #fdf8f3;
    --warm-100: #f9efe4;
    --warm-200: #f0dcc6;
    --warm-300: #e3c4a0;
    --warm-400: #d4a574;
    --warm-500: #b8864e;
    --warm-600: #96693a;
    --warm-700: #6b4a2a;
    --warm-800: #45301c;
    --warm-900: #2a1c10;

    --slate-50:  #f8f9fa;
    --slate-100: #eef0f3;
    --slate-200: #dde1e7;
    --slate-300: #bcc3cd;
    --slate-400: #8e97a5;
    --slate-500: #636e7e;
    --slate-600: #4a5363;
    --slate-700: #353d4a;
    --slate-800: #242a33;
    --slate-900: #181c22;

    /* -- Brand / status palette ------------------------------------------- */
    --primary:       #00897B;
    --primary-light: #E0F2F1;
    --success:       #2E7D32;
    --success-light: #E8F5E9;
    --warning:       #EF6C00;
    --warning-light: #FFF3E0;
    --critical:      #C62828;
    --critical-light:#FFEBEE;

    /* Legacy aliases (charts.py, appendix.py, explainer.py reference these) */
    --color-primary:  #00897B;
    --color-success:  #2E7D32;
    --color-warning:  #EF6C00;
    --color-critical: #C62828;
    --color-neutral:  var(--slate-700);
    --color-bg:       var(--warm-50);
    --color-border:   var(--warm-200);
    --color-text:     var(--slate-800);
    --color-text-muted: var(--slate-500);
    --color-text-light: var(--slate-400);
    --color-zebra:   var(--warm-100);

    /* -- Typography ------------------------------------------------------- */
    --font-display: 'Lora', Georgia, serif;
    --font-body:    'Source Sans 3', 'Source Sans Pro', system-ui, sans-serif;
    --font-mono:    'IBM Plex Mono', 'Menlo', monospace;
    --font-family:  var(--font-body);

    /* -- Spacing (8px grid) ----------------------------------------------- */
    --spacing-xs:  4px;
    --spacing-sm:  8px;
    --spacing-md:  16px;
    --spacing-lg:  24px;
    --spacing-xl:  32px;
    --spacing-xxl: 48px;

    /* -- Radii ------------------------------------------------------------ */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
}


/* ==========================================================================
   Base
   ========================================================================== */

html {
    font-size: 17px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

body {
    font-family: var(--font-body);
    background: var(--warm-50);
    color: var(--slate-800);
    line-height: 1.6;
}

a { color: var(--primary); text-decoration: none; }
a:hover { text-decoration: underline; }


/* ==========================================================================
   Page Header
   ========================================================================== */

.page-header {
    background: var(--slate-900);
    color: var(--warm-100);
    padding: 2rem 2.5rem 1.75rem;
}

.page-header h1 {
    font-family: var(--font-display);
    font-size: 1.75rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin-bottom: 0.25rem;
    color: white;
    border: none;
}

.page-header .subtitle {
    font-size: 0.95rem;
    color: var(--slate-400);
    font-weight: 300;
}

.page-header .brand {
    font-family: var(--font-display);
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--warm-200);
    margin-bottom: 0.125rem;
}

.page-header .meta {
    font-size: 0.8rem;
    color: var(--slate-400);
}


/* ==========================================================================
   Sidebar + Content Layout
   ========================================================================== */

.main-layout {
    display: grid;
    grid-template-columns: 320px 1fr;
    min-height: calc(100vh - 200px);
}

.step-list {
    border-right: 1px solid var(--slate-200);
    background: white;
    overflow-y: auto;
    max-height: calc(100vh - 200px);
    position: sticky;
    top: 0;
}

.step-list-section { padding: 0.625rem 0 0; }

.step-list-section-title {
    font-family: var(--font-display);
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--slate-400);
    padding: 0.5rem 1.25rem 0.375rem;
}

.step-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.625rem 1.25rem;
    cursor: pointer;
    border-left: 3px solid transparent;
    transition: all 0.15s ease;
    text-decoration: none;
    color: var(--slate-700);
    font-size: 0.85rem;
    font-weight: 500;
}

.step-item:hover { background: var(--warm-100); text-decoration: none; }
.step-item.active { background: var(--warm-100); border-left-color: var(--primary); color: var(--primary); }

.step-icon {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 500;
    color: white;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    background: var(--primary);
}

.step-icon.exec  { background: var(--primary); }
.step-icon.tech  { background: var(--slate-500); }

.detail-panel {
    padding: 2.5rem 3rem;
    overflow-y: auto;
    max-height: calc(100vh - 200px);
}


/* ==========================================================================
   Headings
   ========================================================================== */

h1, h2, h3, h4 {
    font-family: var(--font-display);
    font-weight: 600;
    color: var(--slate-800);
    line-height: 1.25;
}

h2 {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--slate-900);
    margin: 0 0 1.25rem 0;
    padding-bottom: 0.75rem;
    border-bottom: 2px solid var(--warm-200);
}

h3 {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--slate-800);
    margin: 1.75rem 0 0.75rem 0;
}

h4 {
    font-size: 0.95rem;
    font-weight: 600;
    margin: 1.25rem 0 0.5rem 0;
}


/* ==========================================================================
   Prose
   ========================================================================== */

p { margin: 0 0 1rem; }

.muted { color: var(--slate-500); }
.small { font-size: 0.85rem; }

.lead-sentence {
    font-family: var(--font-display);
    font-size: 1.05rem;
    font-weight: 400;
    font-style: italic;
    color: var(--slate-700);
    line-height: 1.5;
    margin-bottom: 1.5rem;
}


/* ==========================================================================
   Sections
   ========================================================================== */

section { margin-bottom: 2.5rem; }


/* ==========================================================================
   Environment Donut (floated beside People + Devices)
   ========================================================================== */

.env-donut {
    float: right;
    width: 340px;
    margin: 0 0 1rem 1.5rem;
}

.env-donut svg {
    width: 100%;
    height: auto;
}


/* ==========================================================================
   Stat Grid & Stat Cards
   ========================================================================== */

.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 0.75rem;
    margin: 0.75rem 0 1.5rem;
}

.stat-card {
    background: var(--warm-100);
    border-radius: var(--radius-md);
    padding: 0.875rem 1rem;
}

.stat-card .stat-label {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--slate-500);
    margin-bottom: 0.25rem;
}

.stat-card .stat-value,
.stat-card .stat-number {
    font-family: var(--font-mono);
    font-size: 1.25rem;
    font-weight: 500;
    color: var(--slate-800);
}

/* Colored variants */
.stat-card.success { border-left: 3px solid var(--success); }
.stat-card.warning { border-left: 3px solid var(--warning); }
.stat-card.critical { border-left: 3px solid var(--critical); }

.stat-card.success .stat-value { color: var(--success); }
.stat-card.warning .stat-value { color: var(--warning); }
.stat-card.critical .stat-value { color: var(--critical); }


/* ==========================================================================
   Tables — deg-table style
   ========================================================================== */

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
    margin: 0.75rem 0 1.5rem;
    font-variant-numeric: tabular-nums;
}

thead th {
    text-align: left;
    font-weight: 600;
    color: var(--slate-600);
    padding: 0.5rem 0.75rem;
    border-bottom: 2px solid var(--slate-200);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    background: transparent;
    white-space: nowrap;
}

tbody td {
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--warm-200);
    color: var(--slate-700);
    vertical-align: top;
}

tbody tr:last-child td { border-bottom: none; }

tbody tr:hover { background: var(--warm-100); }

/* Right-align numeric columns */
td.num, th.num {
    text-align: right;
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
}


/* ==========================================================================
   Badges
   ========================================================================== */

.badge {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 600;
    padding: 0.15rem 0.5rem;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.badge-direct,
.badge-low     { background: var(--success-light); color: var(--success); }
.badge-approx,
.badge-medium  { background: var(--warning-light); color: var(--warning); }
.badge-decision,
.badge-critical,
.badge-high    { background: var(--critical-light); color: var(--critical); }
.badge-auto    { background: var(--primary-light);  color: var(--primary); }


/* ==========================================================================
   Callout Boxes
   ========================================================================== */

.callout {
    border-left: 3px solid var(--warning);
    background: var(--warning-light);
    padding: 0.875rem 1.125rem;
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    font-size: 0.875rem;
    color: var(--warm-700);
    margin: 0.75rem 0;
}

.callout.success { border-left-color: var(--success); background: var(--success-light); }
.callout.critical { border-left-color: var(--critical); background: var(--critical-light); color: var(--critical); }
.callout.info { border-left-color: var(--primary); background: var(--primary-light); color: var(--slate-700); }

.callout strong { font-weight: 600; }
.callout p { margin: 0 0 0.5rem; }
.callout p:last-child { margin-bottom: 0; }


/* ==========================================================================
   Explanations (decision cards)
   ========================================================================== */

.explanation {
    padding: 1rem 1.25rem;
    margin: 0.75rem 0;
    border-left: 3px solid var(--primary);
    background: var(--primary-light);
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
}

.explanation h4 {
    margin: 0 0 0.375rem 0;
    font-size: 0.9rem;
    color: var(--slate-800);
}

.explanation p {
    font-size: 0.85rem;
    color: var(--slate-700);
    margin: 0 0 0.375rem;
    line-height: 1.55;
}

.explanation .reassurance {
    color: var(--slate-500);
    font-style: italic;
    margin-bottom: 0;
}

/* Color-code explanations by severity */
.explanation.severity-critical { border-left-color: var(--critical); background: var(--critical-light); }
.explanation.severity-high     { border-left-color: var(--warning);  background: var(--warning-light); }
.explanation.severity-medium   { border-left-color: var(--warning);  background: var(--warning-light); }
.explanation.severity-low      { border-left-color: var(--success);  background: var(--success-light); }


/* ==========================================================================
   Score Layout (v3 data, v1 theme)
   ========================================================================== */

.score-layout {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 2rem;
    align-items: start;
    margin: 1rem 0 2rem;
}

.score-gauge {
    display: flex;
    justify-content: center;
    align-items: center;
}

.score-gauge svg {
    width: 100%;
    height: auto;
    max-width: 180px;
}


/* -- Score breakdown bars ------------------------------------------------- */
.score-breakdown {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.score-breakdown .factor-row {
    display: grid;
    grid-template-columns: 140px 1fr 36px;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
}

.score-breakdown .factor-label {
    color: var(--slate-500);
    text-align: right;
    white-space: nowrap;
}

.score-breakdown .factor-bar {
    height: 10px;
    border-radius: 5px;
    background: var(--slate-100);
    overflow: hidden;
}

.score-breakdown .factor-fill {
    height: 100%;
    border-radius: 5px;
}

.score-breakdown .factor-value {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--slate-800);
    text-align: right;
}


/* -- Key findings --------------------------------------------------------- */
.key-findings {
    list-style: none;
    padding: 0;
    margin: 1rem 0;
}

.key-findings li {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--warm-200);
    font-size: 0.875rem;
    color: var(--slate-700);
    line-height: 1.5;
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
    margin-top: 2px;
}

.key-findings .finding-icon.check {
    background: var(--success-light);
    color: var(--success);
}

.key-findings .finding-icon.alert {
    background: var(--warning-light);
    color: var(--warning);
}


/* ==========================================================================
   Effort Bands (v3 data, v1 theme)
   ========================================================================== */

.effort-band {
    border-left: 3px solid var(--slate-300);
    background: var(--slate-50);
    padding: 0.875rem 1.125rem;
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    margin: 0.75rem 0;
}

.effort-band h4 {
    margin: 0 0 0.375rem 0;
    font-family: var(--font-display);
    font-size: 0.95rem;
}

.effort-band p {
    font-size: 0.85rem;
    color: var(--slate-500);
    margin-bottom: 0.5rem;
}

.effort-band.auto {
    border-left-color: var(--success);
    background: var(--success-light);
}
.effort-band.auto h4 { color: var(--success); }

.effort-band.planning {
    border-left-color: var(--warning);
    background: var(--warning-light);
}
.effort-band.planning h4 { color: var(--warning); }

.effort-band.manual {
    border-left-color: var(--critical);
    background: var(--critical-light);
}
.effort-band.manual h4 { color: var(--critical); }

.effort-band ul {
    margin: 0;
    padding-left: var(--spacing-lg);
    font-size: 0.85rem;
    color: var(--slate-700);
}

.effort-band ul li {
    margin-bottom: 4px;
}


/* -- Verdict callout ------------------------------------------------------ */
.verdict {
    padding: 1rem 1.25rem;
    border-left: 3px solid var(--primary);
    background: var(--primary-light);
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    margin: 0.75rem 0 1.5rem;
    font-size: 0.9rem;
    line-height: 1.6;
    color: var(--slate-700);
}


/* -- CTA box -------------------------------------------------------------- */
.cta-box {
    background: var(--primary-light);
    border: 2px solid var(--primary);
    border-radius: var(--radius-md);
    padding: var(--spacing-lg);
    text-align: center;
    margin: var(--spacing-lg) 0;
}

.cta-box h3 {
    color: var(--primary);
    margin-top: 0;
}


/* -- Decision resolution bar ---------------------------------------------- */
.resolution-bar {
    display: flex;
    height: 20px;
    border-radius: var(--radius-sm);
    overflow: hidden;
    margin: var(--spacing-sm) 0;
}

.resolution-bar .bar-auto { background: var(--success); }
.resolution-bar .bar-planning { background: var(--warning); }
.resolution-bar .bar-manual { background: var(--critical); }


/* ==========================================================================
   Chart Containers
   ========================================================================== */

.chart-container {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
    justify-content: center;
    margin: 1.5rem 0;
}

.chart-container > div {
    flex: 1 1 300px;
    min-width: 250px;
    max-width: 500px;
}

.chart-container svg {
    width: 100%;
    height: auto;
}

/* Traffic-light / summary boxes (legacy, kept for chart tests) */
.summary-boxes {
    display: flex;
    justify-content: center;
    margin: 1rem 0;
}

.summary-boxes svg {
    width: 100%;
    max-width: 450px;
    height: auto;
}


/* ==========================================================================
   Details / Summary (collapsible appendix sections)
   ========================================================================== */

details {
    margin: 1rem 0;
    border: 1px solid var(--warm-200);
    border-radius: var(--radius-md);
    overflow: hidden;
}

details[open] {
    border-color: var(--primary);
}

summary {
    padding: 0.75rem 1rem;
    background: white;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--slate-800);
    cursor: pointer;
    list-style: none;
    user-select: none;
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

summary::-webkit-details-marker { display: none; }

summary::before {
    content: '\\25B6';
    display: inline-block;
    font-size: 0.65rem;
    color: var(--slate-400);
    transition: transform 0.15s ease;
}

details[open] > summary::before {
    transform: rotate(90deg);
}

details[open] > summary {
    border-bottom: 1px solid var(--warm-200);
    color: var(--primary);
}

summary .summary-count {
    font-weight: 400;
    color: var(--slate-500);
    font-size: 0.75rem;
    margin-left: 4px;
}

.details-content {
    padding: var(--spacing-md);
}


/* ==========================================================================
   Section Indicator (appendix letter labels)
   ========================================================================== */

.section-indicator {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: var(--primary);
    color: white;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    font-weight: 500;
    flex-shrink: 0;
}


/* ==========================================================================
   CSS/Partition Topology
   ========================================================================== */

.css-topology {
    list-style: none;
    padding: 0;
    margin: var(--spacing-sm) 0;
    font-size: 0.8rem;
}

.css-topology li {
    padding: 4px 0 4px 18px;
    position: relative;
    color: var(--slate-700);
}

.css-topology li::before {
    content: '';
    position: absolute;
    left: 4px;
    top: 10px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--primary);
}

.css-topology .partition {
    padding-left: 36px;
    color: var(--slate-500);
}

.css-topology .partition::before {
    left: 22px;
    width: 6px;
    height: 6px;
    background: var(--slate-300);
}


/* ==========================================================================
   Report Header (legacy) / Footer
   ========================================================================== */

.report-header {
    text-align: center;
    margin-bottom: var(--spacing-xxl);
}

.report-footer {
    background: var(--slate-900);
    color: var(--slate-400);
    text-align: center;
    padding: 1.25rem 2rem;
    font-size: 0.75rem;
}

.report-footer p { margin: 0; }


/* ==========================================================================
   Print Header (hidden on screen)
   ========================================================================== */

.print-header {
    display: none;
}


/* ==========================================================================
   Checklist
   ========================================================================== */

.checklist {
    list-style: none;
    padding: 0;
}

.checklist li {
    position: relative;
    padding: 0.5rem 0 0.5rem 2rem;
    font-size: 0.875rem;
    color: var(--slate-700);
    border-bottom: 1px solid var(--warm-200);
}

.checklist li:last-child { border-bottom: none; }

.checklist li::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0.75rem;
    width: 16px;
    height: 16px;
    border: 2px solid var(--slate-300);
    border-radius: 3px;
}


/* ==========================================================================
   Responsive
   ========================================================================== */

@media (max-width: 860px) {
    .main-layout { grid-template-columns: 1fr; }
    .step-list {
        max-height: none;
        position: static;
        border-right: none;
        border-bottom: 1px solid var(--slate-200);
    }
    .detail-panel { max-height: none; padding: 1.5rem; }
}


/* ==========================================================================
   Print Styles
   ========================================================================== */

@page {
    size: letter;
    margin: 0.75in;
}

@media print {
    html { font-size: 9.5pt; }

    body {
        padding: 0;
        color: #000;
        background: #fff;
    }

    /* Hide sidebar, show linear content */
    .main-layout { display: block; }
    .step-list { display: none; }
    .detail-panel {
        max-height: none;
        padding: 0;
        overflow: visible;
    }

    /* Hide screen-only elements */
    .page-header { display: none; }
    .no-print { display: none !important; }

    /* Print header: customer name + date as page header */
    .print-header {
        display: block !important;
        text-align: center;
        margin-bottom: 2rem;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid var(--primary);
    }

    .print-header h1 {
        font-family: var(--font-display);
        font-size: 20pt;
        color: var(--primary);
        margin-bottom: 0.25rem;
        border: none;
    }

    .print-header .meta {
        font-size: 9pt;
        color: var(--slate-500);
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

    table, figure, .chart-container, .stat-grid {
        page-break-inside: avoid;
    }

    /* Tables: preserve header styling */
    thead th {
        border-bottom-color: var(--slate-800) !important;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    tbody tr:hover { background: inherit; }

    /* Details: force open */
    details { border: none; }
    details > summary { display: none; }
    details > .details-content,
    details > :not(summary) {
        display: block !important;
        padding: 0.5rem 0;
    }

    /* Badges: preserve colors */
    .badge, .stat-card, .effort-band, .callout {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    /* Score gauge: size for print */
    .score-gauge { max-width: 220px; }

    /* Footer */
    .report-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: transparent;
        color: var(--slate-500);
        font-size: 8pt;
        border-top: 1px solid var(--slate-200);
        padding: 4px 0;
    }
}
"""
