"""CSS design system for the CUCM assessment report.

Single constant `REPORT_CSS` — embedded directly into the HTML report
by the assembler.  Fully self-contained: Inter from Google Fonts CDN
is an enhancement; system fonts are the fallback.
"""

REPORT_CSS = """\
/* ==========================================================================
   CUCM Assessment Report — Design System
   ========================================================================== */

/* -- Font import (enhancement, not required) ------------------------------ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

/* -- Custom properties ---------------------------------------------------- */
:root {
    /* Brand / status palette */
    --color-primary:    #00BCB4;   /* Webex teal                 */
    --color-success:    #2E7D32;   /* Auto-resolved / green      */
    --color-warning:    #F57C00;   /* Needs decision / amber     */
    --color-critical:   #C62828;   /* Blocking / red             */
    --color-neutral:    #37474F;   /* Headings, table headers    */
    --color-bg:         #FFFFFF;   /* Page background            */
    --color-zebra:      #F5F5F5;   /* Table alternating rows     */

    /* Text */
    --color-text:       #212121;
    --color-text-muted: #616161;
    --color-text-light: #9E9E9E;

    /* Borders */
    --color-border:     #E0E0E0;

    /* Typography */
    --font-family:      'Inter', system-ui, -apple-system, BlinkMacSystemFont,
                        'Segoe UI', Roboto, sans-serif;
    --font-size-body:   10pt;
    --font-size-small:  9pt;
    --font-size-h1:     24pt;
    --font-size-h2:     18pt;
    --font-size-h3:     14pt;
    --font-size-h4:     12pt;

    /* Spacing */
    --spacing-xs:       4px;
    --spacing-sm:       8px;
    --spacing-md:       16px;
    --spacing-lg:       24px;
    --spacing-xl:       32px;
    --spacing-xxl:      48px;

    /* Layout */
    --max-width:        900px;
}


/* -- Base reset & typography ---------------------------------------------- */
*, *::before, *::after {
    box-sizing: border-box;
}

html {
    font-size: var(--font-size-body);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

body {
    margin: 0;
    padding: var(--spacing-xl);
    font-family: var(--font-family);
    font-weight: 400;
    line-height: 1.6;
    color: var(--color-text);
    background: var(--color-bg);
}


/* -- Layout container ----------------------------------------------------- */
.report {
    max-width: var(--max-width);
    margin: 0 auto;
    padding: 0 var(--spacing-md);
}


/* -- Headings ------------------------------------------------------------- */
h1, h2, h3, h4 {
    font-family: var(--font-family);
    font-weight: 600;
    color: var(--color-neutral);
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    line-height: 1.25;
}

h1 {
    font-size: var(--font-size-h1);
    font-weight: 700;
    color: var(--color-primary);
    margin-top: 0;
    padding-bottom: var(--spacing-sm);
    border-bottom: 3px solid var(--color-primary);
}

h2 {
    font-size: var(--font-size-h2);
    padding-bottom: var(--spacing-xs);
    border-bottom: 1px solid var(--color-border);
}

h3 { font-size: var(--font-size-h3); }
h4 { font-size: var(--font-size-h4); }


/* -- Paragraphs & prose --------------------------------------------------- */
p {
    margin: 0 0 var(--spacing-md);
}

.muted {
    color: var(--color-text-muted);
}

.small {
    font-size: var(--font-size-small);
}


/* -- Links ---------------------------------------------------------------- */
a {
    color: var(--color-primary);
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
}


/* -- Sections ------------------------------------------------------------- */
section {
    margin-bottom: var(--spacing-xxl);
}


/* -- Tables --------------------------------------------------------------- */
table {
    width: 100%;
    border-collapse: collapse;
    margin: var(--spacing-md) 0 var(--spacing-lg);
    font-size: var(--font-size-small);
    font-variant-numeric: tabular-nums;
}

thead th {
    background: var(--color-neutral);
    color: #FFFFFF;
    font-weight: 600;
    text-align: left;
    padding: var(--spacing-sm) var(--spacing-md);
    white-space: nowrap;
}

thead th:first-child {
    border-radius: 4px 0 0 0;
}
thead th:last-child {
    border-radius: 0 4px 0 0;
}

tbody td {
    padding: var(--spacing-sm) var(--spacing-md);
    border-bottom: 1px solid var(--color-border);
    vertical-align: top;
}

tbody tr:nth-child(even) {
    background: var(--color-zebra);
}

tbody tr:hover {
    background: #E8F5E9;
}

/* Right-align numeric columns */
td.num, th.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}


/* -- Score gauge container ------------------------------------------------ */
.score-gauge {
    display: flex;
    justify-content: center;
    align-items: center;
    margin: var(--spacing-lg) auto;
    max-width: 250px;
}

.score-gauge svg {
    width: 100%;
    height: auto;
}


/* -- Chart containers ----------------------------------------------------- */
.chart-container {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-lg);
    justify-content: center;
    margin: var(--spacing-lg) 0;
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


/* -- Traffic-light / summary boxes ---------------------------------------- */
.summary-boxes {
    display: flex;
    justify-content: center;
    margin: var(--spacing-lg) 0;
}

.summary-boxes svg {
    width: 100%;
    max-width: 450px;
    height: auto;
}


/* -- Severity badges ------------------------------------------------------ */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 0.85em;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
.badge-critical { background: var(--color-critical); color: #fff; }
.badge-high     { background: #E65100;               color: #fff; }
.badge-medium   { background: var(--color-warning);   color: #fff; }
.badge-low      { background: var(--color-success);   color: #fff; }


/* -- Details / Summary (collapsible appendix sections) -------------------- */
details {
    margin: var(--spacing-md) 0;
    border: 1px solid var(--color-border);
    border-radius: 4px;
    overflow: hidden;
}

details[open] {
    border-color: var(--color-primary);
}

summary {
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-zebra);
    font-weight: 600;
    cursor: pointer;
    list-style: none;          /* hide default marker */
    user-select: none;
}

summary::-webkit-details-marker {
    display: none;             /* Chrome/Safari marker removal */
}

summary::before {
    content: '\\25B6';         /* right-pointing triangle   */
    display: inline-block;
    margin-right: var(--spacing-sm);
    font-size: 0.75em;
    transition: transform 0.15s ease;
}

details[open] > summary::before {
    transform: rotate(90deg);  /* rotate to down-pointing   */
}

details > :not(summary) {
    padding: var(--spacing-md);
}


/* -- Explanations (decision cards) ---------------------------------------- */
.explanation {
    padding: var(--spacing-md);
    margin: var(--spacing-md) 0;
    border-left: 4px solid var(--color-primary);
    background: #F9FFFE;
    border-radius: 0 4px 4px 0;
}

.explanation h4 {
    margin-top: 0;
    color: var(--color-neutral);
}

.explanation .reassurance {
    color: var(--color-text-muted);
    font-style: italic;
    margin-bottom: 0;
}


/* -- Report header / footer ----------------------------------------------- */
.report-header {
    text-align: center;
    margin-bottom: var(--spacing-xxl);
}

.report-header .subtitle {
    color: var(--color-text-muted);
    font-size: var(--font-size-h4);
    margin-top: var(--spacing-xs);
}

.report-header .generated-date {
    color: var(--color-text-light);
    font-size: var(--font-size-small);
}

.report-footer {
    margin-top: var(--spacing-xxl);
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--color-border);
    text-align: center;
    color: var(--color-text-light);
    font-size: var(--font-size-small);
}


/* -- Table of contents (optional in-page nav) ----------------------------- */
.toc {
    background: var(--color-zebra);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    padding: var(--spacing-md) var(--spacing-lg);
    margin-bottom: var(--spacing-xl);
}

.toc h3 {
    margin-top: 0;
    font-size: var(--font-size-h4);
}

.toc ol {
    margin: 0;
    padding-left: var(--spacing-lg);
}

.toc li {
    margin-bottom: var(--spacing-xs);
}

.toc a {
    color: var(--color-neutral);
}
.toc a:hover {
    color: var(--color-primary);
}


/* ==========================================================================
   Print styles
   ========================================================================== */

@page {
    size: letter;
    margin: 0.75in;
}

@media print {
    /* -- Base adjustments ------------------------------------------------- */
    html {
        font-size: 9pt;
    }

    body {
        padding: 0;
        color: #000;
        background: #fff;
    }

    .report {
        max-width: none;
        padding: 0;
    }

    /* -- Hide interactive / screen-only elements -------------------------- */
    .toc,
    .no-print {
        display: none !important;
    }

    /* -- Colors: ensure contrast on paper --------------------------------- */
    h1 {
        color: var(--color-primary);
        border-bottom-width: 2px;
    }

    a {
        color: var(--color-neutral);
        text-decoration: none;
    }

    /* -- Page breaks ------------------------------------------------------ */
    section {
        page-break-before: always;
    }

    section:first-of-type {
        page-break-before: avoid;    /* don't break before the first section */
    }

    h2, h3 {
        page-break-after: avoid;     /* keep heading with following content  */
    }

    table, figure, .chart-container {
        page-break-inside: avoid;
    }

    /* -- Tables: tighten for print ---------------------------------------- */
    thead th {
        background: var(--color-neutral) !important;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    tbody tr:nth-child(even) {
        background: var(--color-zebra) !important;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    tbody tr:hover {
        background: inherit;
    }

    /* -- Details: force open for print ------------------------------------ */
    details {
        border: none;
    }

    details > summary {
        display: none;              /* hide toggle, show content directly    */
    }

    details > :not(summary) {
        display: block !important;  /* force all content visible             */
        padding: var(--spacing-sm) 0;
    }

    /* -- Badges: ensure color prints -------------------------------------- */
    .badge {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    /* -- Score gauge: keep centered ---------------------------------------- */
    .score-gauge {
        max-width: 200px;
    }

    /* -- Footer: page number ---------------------------------------------- */
    .report-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        text-align: center;
        font-size: 8pt;
        color: var(--color-text-light);
        border-top: 1px solid var(--color-border);
        padding-top: var(--spacing-xs);
    }
}
"""
