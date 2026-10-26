document.addEventListener('DOMContentLoaded', function() {
    // Centralized initialization - Updated 2024-09-21 14:21
    initializeMobileNav();
    initializeSmoothScroll();
    initializeDemoFunctionality();
    initializeScrollAnimations();
    initializeInteractiveEffects();
    initializeTypingEffect();
});

// Keep the public site pointed at the active Cloud Run service. The older
// project-number URL was retired and now returns a Google Frontend 503.
const ECHO_MIND_API_BASE = 'https://echo-mind-5act.onrender.com';

// Anonymous, browser-local identity used to scope claim history without login.
function getEchoMindSessionId() {
    let sid = localStorage.getItem('echomind_session_id');
    if (!sid) {
        sid = 'sess_' + Math.random().toString(36).substring(2, 15) + '_' + Date.now().toString(36);
        localStorage.setItem('echomind_session_id', sid);
    }
    return sid;
}

function sanitizeHTML(markup) {
    const parsed = new DOMParser().parseFromString(String(markup), 'text/html');
    parsed.querySelectorAll('script, iframe, object, embed, form').forEach(node => node.remove());
    parsed.body.querySelectorAll('*').forEach(node => {
        Array.from(node.attributes).forEach(attribute => {
            const name = attribute.name.toLowerCase();
            const value = attribute.value.trim();
            if (name.startsWith('on') || ((name === 'href' || name === 'src' || name === 'xlink:href') && /^\s*(javascript|vbscript|data):/i.test(value))) {
                node.removeAttribute(attribute.name);
            }
        });
    });
    return parsed.body.innerHTML;
}

function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[character]));
}

function renderExplanationMarkdown(value) {
    const text = String(value ?? '')
        .replace(/\\r\\n|\\n|&#x0*a;|&#(?:10|13);/gi, '\n')
        .replace(/&#x0*20;|&#0*32;|&nbsp;/gi, ' ')
        .replace(/&amp;#x0*a;/gi, '\n')
        .replace(/&amp;#x0*20;/gi, ' ')
        .replace(/&amp;/gi, '&');
    const lines = text.split(/\r?\n/);
    const blocks = [];
    let paragraph = [];
    let listType = '';
    let listItems = [];

    const inline = line => escapeHTML(line)
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
    const flushParagraph = () => {
        if (!paragraph.length) return;
        blocks.push(`<p>${inline(paragraph.join(' '))}</p>`);
        paragraph = [];
    };
    const flushList = () => {
        if (!listItems.length) return;
        blocks.push(`<${listType}>${listItems.map(item => `<li>${inline(item)}</li>`).join('')}</${listType}>`);
        listType = '';
        listItems = [];
    };

    for (const rawLine of lines) {
        const line = rawLine.trim();
        if (!line) {
            flushParagraph();
            flushList();
            continue;
        }
        if (/^#{1,6}$/.test(line)) continue;
        const bullet = line.match(/^[-*]\s+(.+)$/);
        const numbered = line.match(/^\d+[.)]\s+(.+)$/);
        if (bullet || numbered) {
            flushParagraph();
            const nextType = numbered ? 'ol' : 'ul';
            if (listType && listType !== nextType) flushList();
            listType = nextType;
            listItems.push((bullet || numbered)[1]);
            continue;
        }
        flushList();
        const heading = line.match(/^\*\*(.+)\*\*:?$/) || line.match(/^#{1,4}\s+(.+)$/);
        if (heading) {
            flushParagraph();
            blocks.push(`<h5>${inline(heading[1].replace(/:$/, ''))}</h5>`);
        } else {
            paragraph.push(line.replace(/^\*\*|\*\*$/g, ''));
        }
    }
    flushParagraph();
    flushList();
    return blocks.join('');
}

function initializeMobileNav() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    if (!navToggle || !navMenu) return;
    
    navToggle.addEventListener('click', function() {
        navMenu.classList.toggle('active');
        
        // Animate hamburger bars
        const bars = navToggle.querySelectorAll('.bar');
        bars.forEach((bar, index) => {
            if (navMenu.classList.contains('active')) {
                if (index === 0) bar.style.transform = 'rotate(-45deg) translate(-5px, 6px)';
                if (index === 1) bar.style.opacity = '0';
                if (index === 2) bar.style.transform = 'rotate(45deg) translate(-5px, -6px)';
            } else {
                bar.style.transform = 'none';
                bar.style.opacity = '1';
            }
        });
    });

    // Close mobile menu when clicking on a link
    const navLinks = document.querySelectorAll('.nav-menu a');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            navMenu.classList.remove('active');
            const bars = navToggle.querySelectorAll('.bar');
            bars.forEach(bar => {
                bar.style.transform = 'none';
                bar.style.opacity = '1';
            });
        });
    });
}

function initializeSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Sanitize every HTML string before inserting API/user-controlled values into the DOM.
function sanitizeHtml(input) {
    const parsed = new DOMParser().parseFromString(String(input == null ? '' : input), 'text/html');
    parsed.querySelectorAll('script,iframe,object,embed,base,meta,link,svg,math').forEach(node => node.remove());
    parsed.body.querySelectorAll('*').forEach(node => {
        Array.from(node.attributes).forEach(attr => {
            const name = attr.name.toLowerCase();
            const value = attr.value.trim().toLowerCase();
            if (name.startsWith('on') || name === 'srcdoc') {
                node.removeAttribute(attr.name);
            } else if (['href', 'src', 'xlink:href', 'action', 'formaction'].includes(name) &&
                /^(javascript|vbscript|data):/.test(value)) {
                node.removeAttribute(attr.name);
            } else if (name === 'style' && /(expression\s*\(|url\s*\(\s*['"]?\s*(javascript|data):)/i.test(attr.value)) {
                node.removeAttribute(attr.name);
            }
        });
    });
    return parsed.body.innerHTML;
}

function initializeDemoFunctionality() {
    const claimInput = document.getElementById('claimInput');
    const checkClaimBtn = document.getElementById('checkClaim');
    const demoOutput = document.getElementById('demoOutput');

    if (!claimInput || !checkClaimBtn || !demoOutput) {
        console.error("Demo UI elements not found!");
        return;
    }

    function isLocal() {
        const h = window.location.hostname;
        const proto = window.location.protocol;
        // file:// = opened directly from disk; localhost / 127.0.0.1 = local dev server
        return proto === 'file:' || h === 'localhost' || h === '127.0.0.1' || h === '';
    }

    function getBaseUrl() {
        return isLocal() ? 'http://localhost:8080' : ECHO_MIND_API_BASE;
    }

    function getApiUrl() {
        return getBaseUrl() + '/analyze';
    }

    const SAVED_CLAIMS_KEY = 'echomind_saved_claims';
    let recentChecks = [];
    let libraryView = 'recent';

    function getSavedClaims() {
        try {
            const claims = JSON.parse(localStorage.getItem(SAVED_CLAIMS_KEY) || '[]');
            return Array.isArray(claims) ? claims.filter(claim => typeof claim === 'string') : [];
        } catch (_) {
            return [];
        }
    }

    function renderClaimLibrary() {
        const list = document.getElementById('claimLibraryList');
        const count = document.getElementById('historyCount');
        if (!list) return;

        const savedClaims = getSavedClaims();
        if (count) count.textContent = String(recentChecks.length);
        const entries = libraryView === 'recent'
            ? recentChecks.map(entry => ({ ...entry, saved: savedClaims.includes(entry.claim) }))
            : savedClaims.map(claim => ({ claim, verdict: 'Saved', score: null, saved: true }));

        if (!entries.length) {
            list.innerHTML = `<p class="library-empty">${libraryView === 'recent' ? 'Your checked claims will appear here.' : 'Save a claim from Recent to keep it here.'}</p>`;
            return;
        }

        list.innerHTML = entries.map(entry => `
            <div class="claim-library-item">
                <button type="button" class="library-load-claim" data-load-claim="${escapeHTML(entry.claim)}" title="Load this claim into the checker">
                    <span class="library-claim-text">${escapeHTML(entry.claim)}</span>
                    <span class="library-claim-meta">${escapeHTML(entry.verdict || 'Checked')}${entry.score !== null && entry.score !== undefined ? ` · ${escapeHTML(entry.score)}/100` : ''}</span>
                </button>
                <button type="button" class="library-save-claim ${entry.saved ? 'is-saved' : ''}" data-save-claim="${escapeHTML(entry.claim)}" aria-label="${entry.saved ? 'Remove saved claim' : 'Save claim'}" title="${entry.saved ? 'Remove saved claim' : 'Save claim'}">
                    <i class="${entry.saved ? 'fas' : 'far'} fa-bookmark" aria-hidden="true"></i>
                </button>
            </div>
        `).join('');
    }

    async function refreshClaimLibrary() {
        const status = document.getElementById('libraryStatus');
        try {
            const response = await fetch(`${getBaseUrl()}/history`, {
                headers: { 'X-Session-ID': getEchoMindSessionId() }
            });
            if (!response.ok) throw new Error('History is unavailable');
            const data = await response.json();
            recentChecks = Array.isArray(data.history) ? data.history : [];
            if (status) status.textContent = '';
            renderClaimLibrary();
        } catch (_) {
            if (status) status.textContent = 'History unavailable';
            renderClaimLibrary();
        }
    }

    const getClassificationTheme = (classification) => {
        const c = (classification || '').toLowerCase();
        if (c.includes('trustworthy') || c.includes('true')) {
            return {
                heroClass: 'verdict-trustworthy',
                chipClass: 'chip-consensus-supported',
                icon: '<i class="fas fa-check-circle"></i>',
                title: 'Trustworthy',
                tag: 'VERIFIED CREDIBLE'
            };
        }
        if (c.includes('false') || c.includes('debunked')) {
            return {
                heroClass: 'verdict-false',
                chipClass: 'chip-consensus-refuted',
                icon: '<i class="fas fa-times-circle"></i>',
                title: 'False Claim',
                tag: 'REFUTED / MISINFORMATION'
            };
        }
        return {
            heroClass: 'verdict-suspicious',
            chipClass: 'chip-consensus-conflict',
            icon: '<i class="fas fa-exclamation-triangle"></i>',
            title: 'Suspicious / Contested',
            tag: 'NEEDS SCRUTINY'
        };
    };

    // Full Evidence Intelligence Engine HTML Renderer
    function displayAnalysisResult(data) {
        const theme = getClassificationTheme(data.classification);
        const consensus = data.consensus || {};
        const sources = data.evidence_sources || [];
        const subclaims = data.subclaims || [];
        const breakdown = data.credibility_breakdown || {};
        const gamification = data.gamification || { points: 0, badges: [] };
        const personalization = data.personalization || { category: 'General', tip: '' };
        const apiDecision = data.api_decision || {};
        const apiRouteLabels = {
            local_factchecks: 'Local fact-check archive',
            google_fact_check: 'Google Fact Check Tools',
            live_news: 'Live news',
            realtime_cache: 'Live context cache'
        };
        const apiRouteRows = Object.entries(apiDecision.routes || {}).map(([key, route]) => {
            const state = route.used ? 'Queried' : (route.configured ? 'Available' : 'Skipped');
            const provider = route.provider ? ` · ${escapeHTML(route.provider)}` : '';
            const count = Number.isFinite(route.results_found) ? ` · ${route.results_found} matches` : '';
            return `<li><span class="api-route-state">${state}</span><strong>${apiRouteLabels[key] || escapeHTML(key)}${provider}${count}</strong><span>${escapeHTML(route.reason || '')}</span></li>`;
        }).join('');

        // Consensus stance calculations for bar
        const supCount = consensus.supporting_sources_count || 0;
        const refCount = consensus.refuting_sources_count || 0;
        const neuCount = consensus.neutral_sources_count || 0;
        const totalCount = Math.max(1, supCount + refCount + neuCount);
        const supPct = Math.round((supCount / totalCount) * 100);
        const refPct = Math.round((refCount / totalCount) * 100);
        const neuPct = Math.max(0, 100 - supPct - refPct);

        let consensusChipStyle = 'chip-consensus-unverified';
        if (consensus.conflict_detected) {
            consensusChipStyle = 'chip-consensus-conflict';
        } else if (consensus.consensus_direction === 'supported') {
            consensusChipStyle = 'chip-consensus-supported';
        } else if (consensus.consensus_direction === 'refuted') {
            consensusChipStyle = 'chip-consensus-refuted';
        }

        return sanitizeHTML(`
            <div class="evidence-dashboard" style="text-align: left;">
                <!-- 1. Hero Verdict Card -->
                <div class="verdict-hero ${theme.heroClass}">
                    <div class="verdict-badge-group">
                        <div class="verdict-icon">
                            ${theme.icon}
                        </div>
                        <div>
                            <div class="verdict-label">${theme.tag}</div>
                            <div class="verdict-title">${theme.title}</div>
                            ${data.staleness_warning ? `
                                <div style="margin-top: 0.35rem; display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.2rem 0.6rem; border-radius: 6px; background: #fff1f2; color: #e11d48; font-size: 0.78rem; font-weight: 700;">
                                    <i class="fas fa-clock"></i> Time-sensitive claim — verify with live sources
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    <div class="score-radial">
                        <div class="score-number">${data.score || 50}</div>
                        <div class="score-label">Credibility Score</div>
                    </div>
                </div>

                <!-- Indian Language Verification Banner (Vernacular Preservation) -->
                ${data.language_info && data.language_info.is_indian_language ? `
                    <div class="indian-lang-banner">
                        <div class="indian-lang-header">
                            <div class="lang-title">
                                <i class="fas fa-language" style="color: #d97706;"></i>
                                Native ${data.language_info.language_name} (${data.language_info.native_name}) Preserved
                            </div>
                            <span class="lang-badge">Regional Source Verification Active</span>
                        </div>
                        <div style="font-size: 0.85rem; color: #78350f;">
                            Colloquial vernacular meaning preserved. Corroborated with regional trusted publishers:
                        </div>
                        <div class="regional-chips">
                            ${(data.language_info.regional_sources || []).map(r => `
                                <span class="regional-chip"><i class="fas fa-shield-alt"></i> ${r.name} (${r.authority}/100)</span>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                <!-- Action Toolbar for Extensions -->
                <div class="action-toolbar" aria-label="Tools for this claim">
                    <div class="action-toolbar-primary">
                        <button class="action-btn btn-primary-action" id="btnViewEvolution">
                            <i class="fas fa-history" aria-hidden="true"></i><span>Timeline <small>${data.claim_evolution ? (data.claim_evolution.total_variants || 1) : 1}</small></span>
                        </button>
                        <button class="action-btn" id="btnMonitorClaim">
                            <i class="fas fa-bell" aria-hidden="true"></i><span>Follow updates</span>
                        </button>
                        <button class="action-btn" id="btnShareReport">
                            <i class="fas fa-file-alt" aria-hidden="true"></i><span>Share report</span>
                        </button>
                        <button class="action-btn" id="btnExportEvidence" ${sources.length ? '' : 'disabled'}>
                            <i class="fas fa-download" aria-hidden="true"></i><span>Export sources</span>
                        </button>
                    </div>
                    <details class="action-toolbar-more">
                        <summary><i class="fas fa-plus" aria-hidden="true"></i> More tools <span>3</span></summary>
                        <div class="action-toolbar-secondary">
                            <button class="action-btn" id="btnOpenDocAnalysis">
                                <i class="fas fa-file-pdf" aria-hidden="true"></i><span>Scan a document</span>
                            </button>
                            <button class="action-btn" id="btnOpenTransparency">
                                <i class="fas fa-chart-line" aria-hidden="true"></i><span>Quality metrics</span>
                            </button>
                            <button class="action-btn" id="btnSubmitCorrection">
                                <i class="fas fa-edit" aria-hidden="true"></i><span>Suggest a correction</span>
                            </button>
                        </div>
                    </details>
                </div>

                ${apiRouteRows ? `
                    <details class="api-routing-note">
                        <summary><i class="fas fa-route" aria-hidden="true"></i> Why these sources?</summary>
                        <div class="api-routing-meta">${escapeHTML(apiDecision.topic || 'general')} · ${escapeHTML(apiDecision.language || 'English')}${apiDecision.time_sensitive ? ' · time-sensitive' : ''}</div>
                        <ul>${apiRouteRows}</ul>
                        <p class="api-reasoning-note">Reasoning: ${escapeHTML(apiDecision.reasoning || 'Evidence is retrieved before analysis.')}</p>
                    </details>
                ` : ''}

                <div class="followup-widget" id="followupForm">
                    <label for="followupQuestion"><i class="fas fa-comment-dots" aria-hidden="true"></i> Ask about this check</label>
                    <div class="followup-controls">
                        <input id="followupQuestion" name="question" type="text" maxlength="1200" placeholder="What evidence supports this verdict?" required>
                        <button class="btn btn-primary" id="askFollowup" type="button">Ask</button>
                    </div>
                    <div id="followupAnswer" class="followup-answer" aria-live="polite"></div>
                </div>

                <!-- 2. Multi-Source Conflict & Consensus Audit -->
                <div class="consensus-panel">
                    <div class="panel-header">
                        <div class="panel-title">
                            <i class="fas fa-balance-scale" style="color: #6366f1;"></i>
                            Multi-Source Verification & Conflict Audit
                        </div>
                        <span class="consensus-chip ${consensusChipStyle}">
                            ${consensus.status || 'Verified Multi-Source'}
                        </span>
                    </div>

                    <p style="color: #475569; font-size: 0.92rem; line-height: 1.5; margin: 0 0 0.75rem 0;">
                        ${consensus.detail || 'Aggregated reporting across independent authoritative publishers.'}
                    </p>

                    <!-- Stance Bar -->
                    <div class="consensus-bar-wrap">
                        <div class="consensus-bar">
                            <div class="bar-segment-support" style="width: ${supPct}%" title="Supporting: ${supCount}"></div>
                            <div class="bar-segment-refute" style="width: ${refPct}%" title="Refuting: ${refCount}"></div>
                            <div class="bar-segment-neutral" style="width: ${neuPct}%" title="Neutral Context: ${neuCount}"></div>
                        </div>
                        <div class="bar-legend">
                            <div class="legend-item"><span class="legend-dot dot-support"></span> Supports (${supCount})</div>
                            <div class="legend-item"><span class="legend-dot dot-refute"></span> Refutes (${refCount})</div>
                            <div class="legend-item"><span class="legend-dot dot-neutral"></span> Neutral Context (${neuCount})</div>
                        </div>
                    </div>

                    <!-- Metrics Badges -->
                    <div class="consensus-metrics">
                        <div class="metric-pill">
                            <i class="fas fa-building" style="color: #6366f1;"></i>
                            <strong>${consensus.independent_publisher_count || sources.length || 1}</strong> Independent Publishers
                        </div>
                        <div class="metric-pill">
                            <i class="fas fa-shield-alt" style="color: #10b981;"></i>
                            Domain Authority Weighted
                        </div>
                        ${consensus.echo_chamber_detected ? `
                            <div class="metric-pill echo-alert">
                                <i class="fas fa-bullhorn"></i> Syndicated Wire Reprints Detected (Echo-chamber deduplicated)
                            </div>
                        ` : ''}
                    </div>
                </div>

                <!-- 3. Decomposed Atomic Sub-claims (if compound claim) -->
                ${subclaims.length > 0 ? `
                    <div class="subclaims-section">
                        <div class="panel-title">
                            <i class="fas fa-project-diagram" style="color: #3b82f6;"></i>
                            Claim Decomposition & Atomic Parts
                        </div>
                        <div class="subclaims-list">
                            ${subclaims.map((sc, i) => `
                                <div class="subclaim-card">
                                    <div class="subclaim-text">
                                        <span style="font-weight: 700; color: #6366f1; margin-right: 0.5rem;">Part ${i + 1}:</span>
                                        "${sc.text}"
                                    </div>
                                    <span style="font-size: 0.78rem; font-weight: 700; padding: 0.25rem 0.65rem; border-radius: 6px; white-space: nowrap; ${
                                        (sc.status || '').includes('Refuted') ? 'background: #fee2e2; color: #dc2626;' :
                                        (sc.status || '').includes('Supported') ? 'background: #dcfce7; color: #15803d;' :
                                        'background: #f1f5f9; color: #475569;'
                                    }">
                                        ${sc.status || 'Evaluated'}
                                    </span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                <!-- 4. Auditable Evidence Sources Grid -->
                <div class="evidence-sources-section">
                    <div class="panel-header">
                        <div class="panel-title">
                            <i class="fas fa-newspaper" style="color: #059669;"></i>
                            Auditable Source Evidence Trail (${sources.length})
                        </div>
                        <span style="font-size: 0.8rem; color: #64748b; font-weight: 500;">
                            Primary & Secondary Verified Reporting
                        </span>
                    </div>

                    ${sources.length > 0 ? `
                        <div class="source-tools" role="search" aria-label="Filter source evidence">
                            <label class="source-search-label" for="sourceSearch">Find a source</label>
                            <input id="sourceSearch" class="source-search" type="search" placeholder="Publisher or headline" autocomplete="off">
                            <label class="source-search-label" for="sourceStanceFilter">Stance</label>
                            <select id="sourceStanceFilter" class="source-filter">
                                <option value="all">All sources</option>
                                <option value="supports">Supports</option>
                                <option value="refutes">Refutes</option>
                                <option value="neutral">Context</option>
                            </select>
                            <label class="source-search-label" for="sourceSort">Sort</label>
                            <select id="sourceSort" class="source-filter">
                                <option value="original">Original order</option>
                                <option value="authority">Authority: high to low</option>
                            </select>
                            <span id="sourceFilterCount" class="source-filter-count" aria-live="polite"></span>
                        </div>
                        <div class="sources-grid">
                            ${sources.map(s => {
                                const isHighAuth = (s.authority_score || 50) >= 80;
                                const stance = ['supports', 'refutes'].includes(String(s.stance || '').toLowerCase()) ? String(s.stance).toLowerCase() : 'neutral';
                                const authority = Number.isFinite(Number(s.authority_score)) ? Math.max(0, Math.min(100, Number(s.authority_score))) : 50;
                                const stanceClass = stance === 'supports' ? 'stance-supports' : (stance === 'refutes' ? 'stance-refutes' : 'stance-neutral');
                                const stanceLabel = s.stance === 'supports' ? 'SUPPORTS CLAIM' : (s.stance === 'refutes' ? 'REFUTES CLAIM' : 'NEUTRAL CONTEXT');
                                return `
                                    <div class="source-card" data-source-stance="${stance}" data-source-authority="${authority}">
                                        <div>
                                            <div class="source-card-header">
                                                <div class="source-publisher">
                                                    <i class="fas fa-globe" style="color: #94a3b8; margin-right: 0.3rem;"></i>
                                                    ${s.publisher || 'Verified Source'}
                                                </div>
                                                <span class="source-authority-badge ${isHighAuth ? 'auth-tier-high' : ''}" title="${s.authority_tier || ''}">
                                                    ${s.authority_score || 50}/100 Auth
                                                </span>
                                            </div>
                                            
                                            <div class="source-stance-pill ${stanceClass}">
                                                ${stanceLabel}
                                            </div>

                                            <div class="source-title">${s.title || ''}</div>
                                            
                                            ${s.excerpt ? `
                                                <div class="source-excerpt">
                                                    "${s.excerpt}"
                                                </div>
                                            ` : ''}
                                        </div>

                                        <div class="source-footer">
                                            <span>${s.date ? `<i class="far fa-calendar-alt"></i> ${s.date}` : (s.authority_tier || 'Verified')}</span>
                                            ${s.url ? `
                                                <a href="${s.url}" target="_blank" rel="noopener noreferrer" class="source-link">
                                                    View Source <i class="fas fa-external-link-alt"></i>
                                                </a>
                                            ` : '<span style="color: #94a3b8;">Direct Record</span>'}
                                        </div>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    ` : `
                        <div style="background: #f8fafc; padding: 1.25rem; border-radius: 8px; border: 1px solid #e2e8f0; color: #475569; font-size: 0.9rem;">
                            <i class="fas fa-info-circle" style="color: #3b82f6; margin-right: 0.4rem;"></i>
                            ${data.evidence || 'No direct fact-check database match found. Cross-referenced against authoritative domain guidelines and reasoning engine.'}
                        </div>
                    `}
                </div>

                <!-- 5. Transparent Credibility Formula Breakdown -->
                ${breakdown.source_convergence_score !== undefined ? `
                    <div class="credibility-formula-card">
                        <div class="panel-title">
                            <i class="fas fa-calculator" style="color: #8b5cf6;"></i>
                            Transparent Credibility Formula
                        </div>
                        <div class="formula-grid">
                            <div class="formula-item">
                                <div class="formula-label">
                                    <span>Source Convergence</span>
                                    <strong>${breakdown.source_convergence_score || 50}%</strong>
                                </div>
                                <div class="formula-bar">
                                    <div class="formula-bar-fill" style="width: ${breakdown.source_convergence_score || 50}%"></div>
                                </div>
                            </div>
                            <div class="formula-item">
                                <div class="formula-label">
                                    <span>Evidence Authority</span>
                                    <strong>${breakdown.evidence_authority_score || 50}%</strong>
                                </div>
                                <div class="formula-bar">
                                    <div class="formula-bar-fill" style="width: ${breakdown.evidence_authority_score || 50}%"></div>
                                </div>
                            </div>
                            <div class="formula-item">
                                <div class="formula-label">
                                    <span>Publisher Independence</span>
                                    <strong>${breakdown.publisher_independence_score || 50}%</strong>
                                </div>
                                <div class="formula-bar">
                                    <div class="formula-bar-fill" style="width: ${breakdown.publisher_independence_score || 50}%"></div>
                                </div>
                            </div>
                        </div>
                        <div class="formula-desc">
                            ${breakdown.formula_explanation || 'Weighted combination of multi-source agreement, verified institution authority, and publisher diversity.'}
                        </div>
                    </div>
                ` : ''}

                <!-- 6. In-depth Reasoning & Fact-Checking Tips -->
                <div style="background: #ffffff; padding: 1.5rem; border-radius: 14px; border: 1px solid #e2e8f0;">
                    <h4 style="margin: 0 0 0.75rem 0; color: #1e293b; font-size: 1.05rem; display: flex; align-items: center; gap: 0.5rem;">
                        <i class="fas fa-brain" style="color: #4f46e5;"></i>
                        Evidence and explanation
                    </h4>
                    <span class="reasoning-mode ${data.explanation_mode === 'gemini_grounded' ? 'reasoning-mode-ai' : 'reasoning-mode-fallback'}">
                        ${data.explanation_mode === 'gemini_grounded' ? 'Gemini · grounded in retrieved sources' : (data.explanation_mode === 'evidence_reconciled' ? 'Evidence policy · verdict reconciled' : 'Evidence-only fallback · no Gemini explanation')}
                    </span>
                    <div class="reasoning-copy" style="color: #334155; line-height: 1.7; font-size: 0.95rem;">
                        ${renderExplanationMarkdown(data.explanation || 'No explanation was returned.')}
                    </div>

                    ${data.tips && data.tips.length > 0 ? `
                        <div style="margin-top: 1.25rem; padding: 1rem 1.25rem; background: #fffbeb; border-radius: 8px; border: 1px solid #fef3c7;">
                            <strong style="color: #92400e; font-size: 0.88rem; display: block; margin-bottom: 0.5rem;">
                                <i class="fas fa-lightbulb" style="color: #f59e0b;"></i> Actionable Fact-Checking Tips:
                            </strong>
                            <ul style="margin: 0; padding-left: 1.25rem; color: #78350f; font-size: 0.85rem; line-height: 1.5;">
                                ${data.tips.slice(0, 4).map(tip => `<li style="margin: 0.35rem 0;">${escapeHTML(String(tip).replace(/&#x0*20;/gi, ' ').replace(/&#x0*a;/gi, ' '))}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>

                <!-- 7. Gamification & Personalized Insights -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem;">
                    <div style="padding: 1.25rem; background: #ecfdf5; border-radius: 12px; border: 1px solid #a7f3d0;">
                        <div style="font-weight: 700; color: #065f46; margin-bottom: 0.5rem;">
                            <i class="fas fa-award" style="color: #059669; margin-right: 0.3rem;"></i>
                            Your Fact-Checking Journey
                        </div>
                        <div style="font-size: 1.25rem; font-weight: 800; color: #047857;">
                            ${gamification.points} Points Earned (+10)
                        </div>
                        <div style="font-size: 0.85rem; color: #065f46; margin-top: 0.35rem;">
                            Badges: <strong>${(gamification.badges && gamification.badges.length) ? gamification.badges.join(', ') : 'Truth Explorer'}</strong>
                        </div>
                        ${gamification.badge_earned ? `
                            <div style="margin-top: 0.75rem; padding: 0.5rem; background: #ffffff; border-radius: 6px; font-weight: 700; color: #059669; font-size: 0.85rem;">
                                🎉 New Badge Unlocked: ${gamification.badge_earned}!
                            </div>
                        ` : ''}
                    </div>

                    <div style="padding: 1.25rem; background: #eff6ff; border-radius: 12px; border: 1px solid #bfdbfe;">
                        <div style="font-weight: 700; color: #1e40af; margin-bottom: 0.5rem;">
                            <i class="fas fa-compass" style="color: #2563eb; margin-right: 0.3rem;"></i>
                            Personalized Guidance (${personalization.category})
                        </div>
                        <div style="font-size: 0.85rem; color: #1e3a8a; line-height: 1.5;">
                            ${personalization.tip || 'Cross-reference claims with official authorities and maintain a healthy skepticism towards sensationalized viral claims.'}
                        </div>
                    </div>
                </div>
            </div>
        `);
    }

    function displayError(errorMessage) {
        return sanitizeHTML(`
            <div class="demo-result" style="border-left-color: #ef4444; background: #fef2f2; padding: 1.5rem; border-radius: 12px;">
                <h3 style="color: #b91c1c; display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                    <i class="fas fa-exclamation-circle"></i> Service Notice
                </h3>
                <p style="color: #7f1d1d; margin-bottom: 1rem;">${isLocal() ? 'Could not connect to the local analysis service.' : 'The hosted analysis service is currently unavailable. The public site depends on its Cloud Run backend; try again after the service is restored.'}</p>
                <p style="font-family: monospace; background: #ffffff; padding: 0.75rem; border-radius: 6px; font-size: 0.85rem; color: #991b1b; border: 1px solid #fecaca;">${errorMessage}</p>
                <div style="margin-top: 1rem; padding: 1rem; background: #ffffff; border-radius: 8px; border: 1px solid #fecaca; font-size: 0.88rem; color: #7f1d1d;">
                    <strong>Next Steps:</strong>
                    <ol style="margin: 0.5rem 0 0 1.25rem; line-height: 1.6;">
                        ${isLocal() ? '<li>Start the backend with <code>python app.py</code> and check <code>http://localhost:8080/health</code>.</li>' : '<li>Check the Cloud Run service and restore billing for project <code>echo-mind-472808</code>.</li>'}
                    </ol>
                </div>
            </div>
        `);
    }

    checkClaimBtn.addEventListener('click', async function() {
        const claim = claimInput.value.trim();
        
        if (!claim) {
            demoOutput.innerHTML = `
                <div style="color: #e11d48; text-align: center; padding: 2.5rem;">
                    <i class="fas fa-exclamation-circle" style="font-size: 2.5rem; margin-bottom: 1rem; display: block;"></i>
                    <p style="font-size: 1.1rem; font-weight: 600;">Please enter a claim or statement to fact-check!</p>
                </div>
            `;
            return;
        }
        
        // Show rich loading state
        demoOutput.innerHTML = `
            <div class="loading" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 3rem 1.5rem; gap: 1rem; text-align: center;">
                <div class="spinner" style="width: 44px; height: 44px; border: 4px solid #f1f5f9; border-top: 4px solid #6366f1; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <div style="font-weight: 700; color: #1e293b; font-size: 1.1rem;">
                    Evidence Intelligence Engine in Action
                </div>
                <div style="color: #64748b; font-size: 0.88rem; max-width: 420px; line-height: 1.5;">
                    Retrieving primary fact-checks, evaluating domain authority, decomposing atomic sub-claims, and detecting multi-source consensus...
                </div>
            </div>
        `;
        
        try {
            const apiUrl = getApiUrl();
            const sessionId = getEchoMindSessionId();
            console.log('🚀 Sending claim to backend:', apiUrl, 'Session:', sessionId);

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': sessionId
                },
                body: JSON.stringify({ claim: claim }),
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server responded with status: ${response.status}. ${errorText}`);
            }

            const data = await response.json();
            console.log('Analysis result received:', data);
            demoOutput.innerHTML = sanitizeHtml(displayAnalysisResult(data));
            bindActionToolbarEvents(data, claim);
            refreshClaimLibrary();

        } catch (error) {
            console.error('Fetch Error:', error);
            demoOutput.innerHTML = sanitizeHtml(displayError(error.message));
        }
    });

    // Add Enter key support for the textarea
    claimInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            checkClaimBtn.click();
        }
    });

    const library = document.getElementById('claimLibrary');
    if (library) {
        library.addEventListener('click', function(event) {
            const viewButton = event.target.closest('[data-library-view]');
            if (viewButton) {
                libraryView = viewButton.dataset.libraryView;
                library.querySelectorAll('.library-tab').forEach(button => {
                    button.classList.toggle('active', button === viewButton);
                    button.setAttribute('aria-pressed', String(button === viewButton));
                });
                renderClaimLibrary();
                return;
            }

            const loadButton = event.target.closest('[data-load-claim]');
            if (loadButton) {
                claimInput.value = loadButton.dataset.loadClaim || '';
                claimInput.focus();
                claimInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return;
            }

            const saveButton = event.target.closest('[data-save-claim]');
            if (saveButton) {
                const claim = saveButton.dataset.saveClaim || '';
                const saved = getSavedClaims();
                const next = saved.includes(claim)
                    ? saved.filter(item => item !== claim)
                    : [claim, ...saved].slice(0, 30);
                localStorage.setItem(SAVED_CLAIMS_KEY, JSON.stringify(next));
                renderClaimLibrary();
            }
        });
        refreshClaimLibrary();
    }

    // =========================================================================
    // Modal Helpers & Extension Event Handlers
    // =========================================================================
    function showModal(title, contentHtml) {
        let existing = document.getElementById('echoModalBackdrop');
        if (existing) existing.remove();

        const modal = document.createElement('div');
        modal.id = 'echoModalBackdrop';
        modal.className = 'echo-modal-backdrop';
        modal.innerHTML = sanitizeHtml(`
            <div class="echo-modal-box">
                <button class="modal-close-btn" id="modalCloseBtn">&times;</button>
                <h3 style="margin: 0 0 1rem 0; font-size: 1.25rem; color: #1e293b;">${title}</h3>
                <div>${contentHtml}</div>
            </div>
        `);
        document.body.appendChild(modal);

        modal.querySelector('#modalCloseBtn').addEventListener('click', closeModal);
        modal.addEventListener('click', function(e) {
            if (e.target === modal) closeModal();
        });
    }

    function closeModal() {
        const modal = document.getElementById('echoModalBackdrop');
        if (modal) modal.remove();
    }

    function bindActionToolbarEvents(data, currentClaim) {
        const followupForm = document.getElementById('followupForm');
        if (followupForm) {
            const askFollowup = async function() {
                const questionInput = document.getElementById('followupQuestion');
                const submitButton = document.getElementById('askFollowup');
                const answerBox = document.getElementById('followupAnswer');
                const question = questionInput.value.trim();
                if (!question) return;

                submitButton.disabled = true;
                answerBox.textContent = 'Checking the cited evidence…';
                answerBox.classList.add('is-loading');
                try {
                    const response = await fetch(`${getBaseUrl()}/followup`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            claim: currentClaim,
                            question,
                            classification: data.classification,
                            score: data.score,
                            explanation: data.explanation,
                            evidence_sources: (data.evidence_sources || []).slice(0, 8)
                        })
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.message || 'Could not answer this question.');
                    answerBox.innerHTML = `<p>${escapeHTML(result.answer || 'The available evidence does not answer this question.')}</p><span class="followup-mode">${result.grounded ? 'Grounded in this check’s sources' : 'Evidence-only fallback'}</span>`;
                } catch (error) {
                    answerBox.textContent = error.message || 'Could not answer this question right now.';
                } finally {
                    submitButton.disabled = false;
                    answerBox.classList.remove('is-loading');
                }
            };
            document.getElementById('askFollowup').addEventListener('click', askFollowup);
            document.getElementById('followupQuestion').addEventListener('keydown', function(event) {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    askFollowup();
                }
            });
        }

        // Search, stance filters, authority sorting, and CSV export for the evidence trail.
        const sourceGrid = document.querySelector('#demoOutput .sources-grid');
        const sourceSearch = document.getElementById('sourceSearch');
        const sourceStanceFilter = document.getElementById('sourceStanceFilter');
        const sourceSort = document.getElementById('sourceSort');
        const sourceFilterCount = document.getElementById('sourceFilterCount');
        const sourceCards = sourceGrid ? Array.from(sourceGrid.querySelectorAll('.source-card')) : [];

        function updateSourceList() {
            if (!sourceGrid) return;
            const query = (sourceSearch?.value || '').trim().toLocaleLowerCase();
            const stance = sourceStanceFilter?.value || 'all';
            sourceCards.forEach(card => {
                const matchesText = !query || card.textContent.toLocaleLowerCase().includes(query);
                const matchesStance = stance === 'all' || card.dataset.sourceStance === stance;
                card.hidden = !(matchesText && matchesStance);
            });
            if (sourceSort?.value === 'authority') {
                sourceCards.slice().sort((a, b) => Number(b.dataset.sourceAuthority) - Number(a.dataset.sourceAuthority))
                    .forEach(card => sourceGrid.appendChild(card));
            } else {
                sourceCards.forEach(card => sourceGrid.appendChild(card));
            }
            const visibleCount = sourceCards.filter(card => !card.hidden).length;
            if (sourceFilterCount) sourceFilterCount.textContent = `${visibleCount} of ${sourceCards.length}`;
        }

        [sourceSearch, sourceStanceFilter, sourceSort].forEach(control => {
            control?.addEventListener(control === sourceSearch ? 'input' : 'change', updateSourceList);
        });
        updateSourceList();

        const exportEvidenceButton = document.getElementById('btnExportEvidence');
        exportEvidenceButton?.addEventListener('click', function() {
            const rows = [['Publisher', 'Title', 'Stance', 'Authority score', 'Date', 'URL', 'Excerpt']];
            (data.evidence_sources || []).forEach(source => rows.push([
                source.publisher, source.title, source.stance, source.authority_score, source.date, source.url, source.excerpt
            ].map(value => {
                const text = String(value ?? '').replace(/\s+/g, ' ').trim();
                return /^[\s]*[=+@-]/.test(text) ? `'${text}` : text;
            })));
            const csv = rows.map(row => row.map(value => `"${value.replace(/"/g, '""')}"`).join(',')).join('\r\n');
            const blob = new Blob(['\ufeff', csv], { type: 'text/csv;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'echo-mind-evidence.csv';
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        });

        // 1. Claim Evolution Timeline Modal
        const btnEvolution = document.getElementById('btnViewEvolution');
        if (btnEvolution) {
            btnEvolution.addEventListener('click', async function() {
                showModal('Claim Evolution & Mutation Timeline', `
                    <div style="text-align: center; padding: 2rem;">
                        <div class="spinner" style="margin: 0 auto 1rem;"></div>
                        <div>Loading mutation history...</div>
                    </div>
                `);
                try {
                    const resp = await fetch(`${getBaseUrl()}/evolution?claim=${encodeURIComponent(currentClaim)}`);
                    const ev = await resp.json();
                    const timeline = ev.timeline || [];
                    const content = `
                        <p style="color: #475569; font-size: 0.9rem; line-height: 1.5; margin-bottom: 1.5rem;">
                            Tracing how this claim evolved across time in wording, evidence accumulation, and verdict changes.
                            ${ev.verdict_drift_detected ? '<strong style="color: #b45309; display: block; margin-top: 0.5rem;">⚠️ Verdict drift detected across mutation history!</strong>' : ''}
                        </p>
                        <div class="evolution-timeline">
                            ${timeline.map((node, i) => `
                                <div class="timeline-node">
                                    <div class="timeline-dot"></div>
                                    <div class="timeline-card">
                                        <div class="timeline-date">${node.recorded_at ? node.recorded_at.substring(0, 10) : 'Recent'} • Variant #${i+1}</div>
                                        <div class="timeline-variant">"${node.variant_text}"</div>
                                        <div style="display: flex; gap: 0.5rem; align-items: center; font-size: 0.78rem;">
                                            <span style="font-weight: 700; color: ${node.verdict === 'Trustworthy' ? '#15803d' : (node.verdict === 'False' ? '#b91c1c' : '#b45309')}">
                                                Verdict: ${node.verdict} (${node.score} pts)
                                            </span>
                                            <span>• Primary: ${node.primary_source || 'Synthesized'}</span>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                    showModal('Claim Evolution & Mutation Timeline', content);
                } catch (err) {
                    showModal('Claim Evolution', `<div style="color:#e11d48;">Could not fetch evolution timeline: ${err.message}</div>`);
                }
            });
        }

        // 2. Opt-in Claim Monitoring
        const btnMonitor = document.getElementById('btnMonitorClaim');
        if (btnMonitor) {
            btnMonitor.addEventListener('click', function() {
                showModal('Opt-In Claim Monitoring', `
                    <p style="color: #475569; font-size: 0.92rem; margin-bottom: 1.25rem;">
                        Follow <strong>"${escapeHTML(currentClaim.substring(0, 70))}..."</strong> and get alerted only when significant new evidence, official announcements, or a verdict correction occurs.
                    </p>
                    <div style="margin-bottom: 1rem;">
                        <label style="font-size: 0.85rem; font-weight: 600; color: #334155; display: block; margin-bottom: 0.35rem;">Email for Notifications (Optional):</label>
                        <input type="email" id="monitorEmailInput" placeholder="your.email@example.com" style="width: 100%; padding: 0.6rem; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 0.9rem;" />
                    </div>
                    <button id="btnConfirmMonitor" class="btn btn-primary" style="width: 100%; padding: 0.75rem;">
                        <i class="fas fa-bell"></i> Activate Claim Monitoring
                    </button>
                    <div id="monitorStatusMsg" style="margin-top: 1rem;"></div>
                `);

                document.getElementById('btnConfirmMonitor').addEventListener('click', async function() {
                    const email = document.getElementById('monitorEmailInput').value.trim();
                    const statusDiv = document.getElementById('monitorStatusMsg');
                    statusDiv.innerHTML = '<div style="color: #6366f1;">Subscribing...</div>';

                    try {
                        const resp = await fetch(`${getBaseUrl()}/monitor/subscribe`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json', 'X-Session-ID': getEchoMindSessionId() },
                            body: JSON.stringify({
                                claim: currentClaim,
                                verdict: data.classification,
                                score: data.score,
                                email: email || null,
                                evidence_count: (data.evidence_sources || []).length
                            })
                        });
                        const res = await resp.json();
                        if (!resp.ok) throw new Error(res.message || res.error || 'Subscription failed');
                        statusDiv.innerHTML = sanitizeHtml(`
                            <div style="background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; padding: 0.75rem; border-radius: 8px; font-size: 0.88rem;">
                                <i class="fas fa-check-circle"></i> ${res.message || 'Subscribed successfully!'}
                            </div>
                        `);
                    } catch (err) {
                        statusDiv.innerHTML = sanitizeHtml(`<div style="color: #e11d48;">Subscription error: ${err.message}</div>`);
                    }
                });
            });
        }

        // 3a. Copy a link to the shareable report or open a preview.
        const btnShareReport = document.getElementById('btnShareReport');
        if (btnShareReport) {
            btnShareReport.addEventListener('click', function() {
                const reportUrl = `${getBaseUrl()}/report?claim=${encodeURIComponent(currentClaim)}`;
                showModal('Share this report', `
                    <p class="share-intro">A report link is ready for this claim.</p>
                    <div class="share-link-row">
                        <input id="shareReportUrl" type="text" readonly value="${escapeHTML(reportUrl)}" aria-label="Share report URL">
                        <button type="button" class="btn btn-primary" id="copyReportLink">Copy link</button>
                    </div>
                    <a class="share-preview-link" href="${escapeHTML(reportUrl)}" target="_blank" rel="noopener noreferrer">Open report preview ↗</a>
                    <div class="share-copy-status" id="shareCopyStatus" aria-live="polite"></div>
                `);
                document.getElementById('copyReportLink').addEventListener('click', async function() {
                    const status = document.getElementById('shareCopyStatus');
                    try {
                        await navigator.clipboard.writeText(reportUrl);
                        status.textContent = 'Copied to clipboard';
                    } catch (_) {
                        const input = document.getElementById('shareReportUrl');
                        input.select();
                        status.textContent = 'Select and copy the link';
                    }
                });
            });
        }

        // 3. Research Document Deep-Scan Modal
        const btnDocScan = document.getElementById('btnOpenDocAnalysis');
        if (btnDocScan) {
            btnDocScan.addEventListener('click', function() {
                showModal('Research Document & Official Notice Deep-Scan', `
                    <p style="color: #475569; font-size: 0.9rem; margin-bottom: 1rem;">
                        Paste the text of a research paper, official government circular, court order, or press notice.
                        Echo Mind will chunk passages, isolate individual factual claims, and trace citations back to exact passages.
                    </p>
                    <div style="margin-bottom: 1rem;">
                        <label style="font-size: 0.85rem; font-weight: 600; color: #334155; display: block; margin-bottom: 0.35rem;">Document Title:</label>
                        <input type="text" id="docTitleInput" placeholder="e.g. Health Ministry Circular #2026" style="width: 100%; padding: 0.6rem; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 0.9rem;" />
                    </div>
                    <div style="margin-bottom: 1.25rem;">
                        <label style="font-size: 0.85rem; font-weight: 600; color: #334155; display: block; margin-bottom: 0.35rem;">Document Text Content:</label>
                        <textarea id="docContentInput" rows="6" placeholder="Paste full document or circular text here..." style="width: 100%; padding: 0.75rem; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 0.9rem; font-family: inherit;"></textarea>
                    </div>
                    <button id="btnRunDocScan" class="btn btn-primary" style="width: 100%; padding: 0.75rem;">
                        <i class="fas fa-microscope"></i> Deep-Scan Document & Trace Citations
                    </button>
                    <div id="docScanResults" style="margin-top: 1.5rem;"></div>
                `);

                document.getElementById('btnRunDocScan').addEventListener('click', async function() {
                    const title = document.getElementById('docTitleInput').value.trim() || 'Submitted Document';
                    const text = document.getElementById('docContentInput').value.trim();
                    const resultsDiv = document.getElementById('docScanResults');

                    if (!text) {
                        resultsDiv.innerHTML = '<div style="color: #e11d48;">Please paste document content!</div>';
                        return;
                    }

                    resultsDiv.innerHTML = '<div style="text-align: center; padding: 1.5rem;"><div class="spinner" style="margin: 0 auto 0.75rem;"></div><div>Chunking passages and tracing claims...</div></div>';

                    try {
                        const resp = await fetch(`${getBaseUrl()}/document/analyze`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ title: title, text: text })
                        });
                        const res = await resp.json();
                        if (!resp.ok) throw new Error(res.message || res.error || 'Document analysis failed');
                        const verified = res.verified_claims || [];
                        resultsDiv.innerHTML = sanitizeHtml(`
                            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1rem; margin-bottom: 1rem;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                    <strong>Document Integrity Score:</strong>
                                    <span style="font-size: 1.25rem; font-weight: 800; color: #6366f1;">${res.document_integrity_score}/100</span>
                                </div>
                                <div style="font-size: 0.85rem; color: #64748b;">
                                    Passages Analyzed: <strong>${res.total_passages}</strong> • Claims Extracted: <strong>${res.total_claims_extracted}</strong>
                                </div>
                            </div>
                            <h4 style="margin: 0 0 0.75rem 0; font-size: 1rem; color: #1e293b;">Extracted Claims & Passage Tracing:</h4>
                            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                                ${verified.map(vc => `
                                    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid ${vc.verdict === 'Trustworthy' ? '#10b981' : (vc.verdict === 'False' ? '#ef4444' : '#f59e0b')}; border-radius: 8px; padding: 0.85rem;">
                                        <div style="display: flex; justify-content: space-between; font-size: 0.76rem; color: #64748b; margin-bottom: 0.35rem;">
                                            <span>Paragraph #${vc.paragraph_num} • Estimated Page ${vc.estimated_page}</span>
                                            <span style="font-weight: 700; color: ${vc.verdict === 'Trustworthy' ? '#059669' : (vc.verdict === 'False' ? '#dc2626' : '#d97706')}">${vc.verdict} (${vc.score} pts)</span>
                                        </div>
                                        <div style="font-size: 0.92rem; font-weight: 600; color: #1e293b; margin-bottom: 0.35rem;">"${vc.claim_text}"</div>
                                        <div style="font-size: 0.82rem; color: #64748b; font-style: italic; background: #f8fafc; padding: 0.4rem 0.6rem; border-radius: 4px;">Context: "${vc.surrounding_context}"</div>
                                    </div>
                                `).join('')}
                            </div>
                        `);
                    } catch (err) {
                        resultsDiv.innerHTML = sanitizeHtml(`<div style="color: #e11d48;">Scan error: ${err.message}</div>`);
                    }
                });
            });
        }

        // 4. Quality & Transparency Observability Dashboard
        const btnTransparency = document.getElementById('btnOpenTransparency');
        if (btnTransparency) {
            btnTransparency.addEventListener('click', async function() {
                showModal('Quality & Transparency Observability Dashboard', `
                    <div style="text-align: center; padding: 2rem;">
                        <div class="spinner" style="margin: 0 auto 1rem;"></div>
                        <div>Loading real-time telemetry metrics...</div>
                    </div>
                `);

                try {
                    const resp = await fetch(`${getBaseUrl()}/transparency`);
                    const m = await resp.json();
                    showModal('Quality & Transparency Observability Dashboard', `
                        <p style="color: #475569; font-size: 0.9rem; line-height: 1.5; margin-bottom: 1.5rem;">
                            Live operational benchmarks tracking citation coverage, domain authority integrity, and verification latency.
                        </p>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                            <div style="background: #f8fafc; padding: 1.25rem; border-radius: 10px; border: 1px solid #e2e8f0; text-align: center;">
                                <div style="font-size: 1.8rem; font-weight: 900; color: #10b981;">${m.citation_coverage_pct}%</div>
                                <div style="font-size: 0.82rem; font-weight: 600; color: #64748b; text-transform: uppercase;">Citation Coverage</div>
                            </div>
                            <div style="background: #f8fafc; padding: 1.25rem; border-radius: 10px; border: 1px solid #e2e8f0; text-align: center;">
                                <div style="font-size: 1.8rem; font-weight: 900; color: #3b82f6;">${m.retrieval_success_pct}%</div>
                                <div style="font-size: 0.82rem; font-weight: 600; color: #64748b; text-transform: uppercase;">Retrieval Success</div>
                            </div>
                            <div style="background: #f8fafc; padding: 1.25rem; border-radius: 10px; border: 1px solid #e2e8f0; text-align: center;">
                                <div style="font-size: 1.8rem; font-weight: 900; color: #f59e0b;">${m.unresolved_conflict_pct}%</div>
                                <div style="font-size: 0.82rem; font-weight: 600; color: #64748b; text-transform: uppercase;">Unresolved Conflicts</div>
                            </div>
                            <div style="background: #f8fafc; padding: 1.25rem; border-radius: 10px; border: 1px solid #e2e8f0; text-align: center;">
                                <div style="font-size: 1.8rem; font-weight: 900; color: #6366f1;">${m.average_latency_ms} ms</div>
                                <div style="font-size: 0.82rem; font-weight: 600; color: #64748b; text-transform: uppercase;">Avg Latency</div>
                            </div>
                        </div>
                        <div style="background: #f8fafc; padding: 1rem 1.25rem; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 0.85rem; color: #475569;">
                            <i class="fas fa-certificate" style="color: #6366f1; margin-right: 0.35rem;"></i>
                            Benchmark Evaluation: <strong>${m.eval_benchmark_accuracy}</strong>
                            <br>
                            Open Community Corrections: <strong>${m.open_human_corrections}</strong>
                        </div>
                    `);
                } catch (err) {
                    showModal('Observability Dashboard', `<div style="color: #e11d48;">Could not fetch metrics: ${err.message}</div>`);
                }
            });
        }

        // 5. Submit Human Correction Modal
        const btnCorrection = document.getElementById('btnSubmitCorrection');
        if (btnCorrection) {
            btnCorrection.addEventListener('click', function() {
                showModal('Submit Fact-Check Correction & Audit Feedback', `
                    <p style="color: #475569; font-size: 0.9rem; margin-bottom: 1.25rem;">
                        Echo Mind adheres to traceable source attribution and transparent correction policies.
                        Submit external primary evidence if you believe a verdict or citation requires revision.
                    </p>
                    <div style="margin-bottom: 1rem;">
                        <label style="font-size: 0.85rem; font-weight: 600; color: #334155; display: block; margin-bottom: 0.35rem;">Suggested Verdict:</label>
                        <select id="corrVerdictSelect" style="width: 100%; padding: 0.6rem; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 0.9rem;">
                            <option value="Trustworthy">Trustworthy</option>
                            <option value="False">False</option>
                            <option value="Suspicious">Suspicious / Disputed</option>
                        </select>
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label style="font-size: 0.85rem; font-weight: 600; color: #334155; display: block; margin-bottom: 0.35rem;">Primary Evidence URL (Required):</label>
                        <input type="url" id="corrUrlInput" placeholder="https://who.int/... or https://pib.gov.in/..." style="width: 100%; padding: 0.6rem; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 0.9rem;" required />
                    </div>
                    <div style="margin-bottom: 1.25rem;">
                        <label style="font-size: 0.85rem; font-weight: 600; color: #334155; display: block; margin-bottom: 0.35rem;">Rationale & Factual Breakdown:</label>
                        <textarea id="corrRationaleInput" rows="3" placeholder="Explain the factual basis with reference to the primary source link above..." style="width: 100%; padding: 0.6rem; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 0.9rem; font-family: inherit;"></textarea>
                    </div>
                    <button id="btnSendCorrection" class="btn btn-primary" style="width: 100%; padding: 0.75rem;">
                        <i class="fas fa-paper-plane"></i> Submit to Public Audit Log
                    </button>
                    <div id="corrStatusMsg" style="margin-top: 1rem;"></div>
                `);

                document.getElementById('btnSendCorrection').addEventListener('click', async function() {
                    const suggested = document.getElementById('corrVerdictSelect').value;
                    const url = document.getElementById('corrUrlInput').value.trim();
                    const rationale = document.getElementById('corrRationaleInput').value.trim();
                    const statusDiv = document.getElementById('corrStatusMsg');

                    if (!url || !rationale) {
                        statusDiv.innerHTML = '<div style="color: #e11d48;">Please fill in both the Evidence URL and Rationale.</div>';
                        return;
                    }

                    statusDiv.innerHTML = '<div style="color: #6366f1;">Submitting to audit log...</div>';

                    try {
                        const resp = await fetch(`${getBaseUrl()}/correction`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                claim_text: currentClaim,
                                reported_verdict: data.classification,
                                suggested_verdict: suggested,
                                evidence_url: url,
                                rationale: rationale
                            })
                        });
                        const res = await resp.json();
                        statusDiv.innerHTML = sanitizeHtml(`
                            <div style="background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; padding: 0.75rem; border-radius: 8px; font-size: 0.88rem;">
                                <i class="fas fa-check-circle"></i> ${res.message || 'Correction received into audit queue!'}
                            </div>
                        `);
                    } catch (err) {
                        statusDiv.innerHTML = sanitizeHtml(`<div style="color: #e11d48;">Error: ${err.message}</div>`);
                    }
                });
            });
        }
    }
}

// Scroll animations
function initializeScrollAnimations() {
    const observerOptions = { threshold: 0.1, rootMargin: '0px 0px -50px 0px' };
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target); // Stop observing once animated
            }
        });
    }, observerOptions);

    const animateElements = document.querySelectorAll('.feature-card, .stat-card, .contact-item, .mission-card');
    animateElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}

function initializeInteractiveEffects() {
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach(card => {
        card.addEventListener('mouseenter', function(e) {
            this.style.transform = 'translateY(-5px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function(e) {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
    
    const statNumbers = document.querySelectorAll('.stat-number');
    const animateCounters = () => {
        statNumbers.forEach(stat => {
            const target = stat.textContent;
            if (target.includes('%')) {
                animateCounter(stat, 0, parseInt(target), '%');
            } else if (target.includes('<')) {
                stat.innerHTML = '&lt;2s';
            } else if (target.includes('+')) {
                animateCounter(stat, 0, parseInt(target), '+');
            }
        });
    };

    const animateCounter = (element, start, end, suffix = '') => {
        const duration = 2000;
        const startTime = performance.now();

        const updateCounter = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const current = Math.floor(start + (end - start) * progress);
            element.textContent = current + suffix;

            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            }
        };

        requestAnimationFrame(updateCounter);
    };

    // Trigger counter animation when stats section comes into view
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
                statsObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    const aboutStats = document.querySelector('.about-stats');
    if (aboutStats) {
        statsObserver.observe(aboutStats);
    }
}

function initializeTypingEffect() {
    const heroTitle = document.querySelector('.hero-title');
    if (!heroTitle) return;

    // This is a placeholder function - implement typing effect if needed
    // For now, we'll just ensure the title is visible
    heroTitle.style.opacity = '1';
}

function initializeVoiceWelcome() {
    // Check if the browser supports Speech Synthesis
    if (!('speechSynthesis' in window)) {
        console.log('Speech Synthesis not supported in this browser');
        return;
    }

    // Check if this is the first visit to avoid repeated announcements on refresh
    const hasPlayedWelcome = sessionStorage.getItem('echoMindVoiceWelcome');
    
    if (hasPlayedWelcome) {
        return; // Don't play if already played in this session
    }

    // Add welcome voice button instead of auto-play (due to browser restrictions)
    addWelcomeVoiceButton();
}

function speakWelcomeMessage() {
    try {
        // Create speech synthesis utterance
        const welcomeText = "Welcome to Echo Mind. Your AI-powered fact checker by Thunderwing Falcons.";
        const utterance = new SpeechSynthesisUtterance(welcomeText);
        
        // Configure voice settings
        utterance.rate = 0.9; // Slightly slower for clarity
        utterance.pitch = 1.0; // Normal pitch
        utterance.volume = 0.8; // 80% volume to not be too loud
        
        // Try to use a nice voice if available
        const voices = speechSynthesis.getVoices();
        if (voices.length > 0) {
            // Prefer female voices or specific high-quality voices
            const preferredVoice = voices.find(voice => 
                voice.name.includes('Google') || 
                voice.name.includes('Microsoft') || 
                voice.name.includes('Samantha') ||
                voice.gender === 'female'
            ) || voices[0];
            
            utterance.voice = preferredVoice;
        }

        // Event listeners for voice feedback
        utterance.onstart = () => {
            console.log('🎤 Echo Mind voice welcome started');
            showVoiceIndicator();
        };
        
        utterance.onend = () => {
            console.log('🎤 Echo Mind voice welcome completed');
            hideVoiceIndicator();
        };
        
        utterance.onerror = (event) => {
            console.error('🎤 Voice welcome error:', event.error);
        };

        // Speak the welcome message
        speechSynthesis.speak(utterance);
        
    } catch (error) {
        console.error('Error with voice welcome:', error);
    }
}

// Optional: Add a function to replay the welcome message
function replayWelcomeMessage() {
    // Stop any current speech
    speechSynthesis.cancel();
    
    // Play the welcome message again
    setTimeout(() => {
        speakWelcomeMessage();
    }, 100);
}

// Add welcome voice button for user interaction
function addWelcomeVoiceButton() {
    // Create a welcome voice button
    const welcomeButton = document.createElement('div');
    welcomeButton.id = 'welcome-voice-button';
    welcomeButton.innerHTML = `
        <button onclick="playWelcomeVoice()" class="welcome-voice-btn" title="Click to hear welcome message">
            🎤 Welcome Message
        </button>
    `;
    welcomeButton.style.cssText = `
        position: fixed;
        top: auto;
        bottom: 20px;
        right: 20px;
        z-index: 1000;
        animation: none;
    `;
    
    // Add bounce animation
    if (!document.getElementById('welcome-voice-style')) {
        const style = document.createElement('style');
        style.id = 'welcome-voice-style';
        style.textContent = `
            .welcome-voice-btn {
                background: #20231f;
                color: #fffdf8;
                border: 1px solid #df6945;
                padding: 0.65rem 0.9rem;
                border-radius: 2px;
                font-size: 0.76rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 3px 3px 0 rgba(223, 105, 69, 0.65);
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            .welcome-voice-btn:hover {
                transform: translateY(-2px);
                box-shadow: 3px 3px 0 rgba(49, 95, 199, 0.65);
            }
            @keyframes bounce {
                0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
                40% { transform: translateY(-10px); }
                60% { transform: translateY(-5px); }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(welcomeButton);
    
    // Remove button after 10 seconds if not used
    setTimeout(() => {
        if (document.getElementById('welcome-voice-button')) {
            document.getElementById('welcome-voice-button').remove();
        }
    }, 10000);
}

// Function to play welcome voice (called by button)
function playWelcomeVoice() {
    speakWelcomeMessage();
    sessionStorage.setItem('echoMindVoiceWelcome', 'true');
    
    // Remove the button after clicking
    const button = document.getElementById('welcome-voice-button');
    if (button) {
        button.style.animation = 'fadeOut 0.5s ease-out';
        setTimeout(() => button.remove(), 500);
    }
}

// Visual feedback functions
function showVoiceIndicator() {
    // Create a subtle visual indicator when voice is speaking
    const indicator = document.createElement('div');
    indicator.id = 'voice-indicator';
    indicator.innerHTML = '🎤 Speaking...';
    indicator.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-size: 0.9rem;
        z-index: 1000;
        animation: pulse 2s infinite;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    `;
    
    // Add pulse animation
    if (!document.getElementById('voice-animation-style')) {
        const style = document.createElement('style');
        style.id = 'voice-animation-style';
        style.textContent = `
            @keyframes pulse {
                0% { opacity: 0.8; transform: scale(1); }
                50% { opacity: 1; transform: scale(1.05); }
                100% { opacity: 0.8; transform: scale(1); }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(indicator);
}

function hideVoiceIndicator() {
    const indicator = document.getElementById('voice-indicator');
    if (indicator) {
        indicator.style.animation = 'fadeOut 0.5s ease-out';
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.parentNode.removeChild(indicator);
            }
        }, 500);
    }
}

// Optional: Add voice controls for accessibility
function addVoiceControls() {
    // You can call this function if you want to add voice control buttons later
    const voiceControlsHTML = `
        <div class="voice-controls" style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;">
            <button onclick="replayWelcomeMessage()" class="voice-btn" title="Replay Welcome Message">
                🔊
            </button>
        </div>
    `;
    
    // Uncomment the line below if you want to add the replay button
    // document.body.insertAdjacentHTML('beforeend', voiceControlsHTML);
}


// Investigation workspace: use textContent for all untrusted claim/source labels.
document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('investigation-workspace');
  if (!root) return;
  let selectedId = null;
  const $ = id => document.getElementById(id);
  const status = message => { $('workspace-status').textContent = message; };
  const localPreview = ['localhost', '127.0.0.1'].includes(window.location.hostname);
  const apiBaseReady = (async () => {
    if (!localPreview) return '';
    try {
      const probe = await fetch('/health', { cache: 'no-store' });
      if (probe.status === 404) return ECHO_MIND_API_BASE;
    } catch (_) { /* Keep same-origin routing; the visible status will explain connection failures. */ }
    return '';
  })();
  const apiUrl = async path => (localPreview ? (await apiBaseReady) : ECHO_MIND_API_BASE) + path;
  const showServiceError = error => {
    $('workspace-list').textContent = 'Recent investigations are unavailable.';
    status(error.message.includes('(404)')
      ? 'Workspace API not found. Start the Flask app with “python app.py”.'
      : 'Could not connect to the investigation service. Try again shortly.');
  };
  const request = async (url, options = {}) => {
    const response = await fetch(await apiUrl(url), { ...options, headers: { 'Content-Type': 'application/json', 'X-Session-ID': getEchoMindSessionId(), ...(options.headers || {}) } });
    const data = response.headers.get('content-type')?.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) throw new Error(data?.message || data?.error || 'Request failed (' + response.status + ')');
    return data;
  };
  const loadGraph = async () => {
    if (!selectedId) return;
    const graph = await request('/investigations/' + encodeURIComponent(selectedId) + '/provenance');
    $('workspace-graph').textContent = JSON.stringify(graph, null, 2);
  };
  const loadInvestigations = async () => {
    const data = await request('/investigations?limit=30');
    const list = $('workspace-list');
    list.replaceChildren();
    if (!data.investigations?.length) { list.textContent = 'No investigations saved yet.'; return; }
    data.investigations.forEach(item => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = (item.verdict || 'Not yet verified') + ' — ' + item.claim;
      button.addEventListener('click', async () => {
        selectedId = item.id;
        $('workspace-claim').value = item.claim;
        $('workspace-selected').textContent = 'Selected: ' + item.claim;
        $('workspace-save-sources').disabled = false;
        try { await loadGraph(); status('Investigation loaded. Add source links to build provenance.'); }
        catch (e) { status(e.message); }
      });
      list.appendChild(button);
    });
  };
  $('workspace-create').addEventListener('click', async () => {
    const claim = $('workspace-claim').value.trim();
    if (!claim) { status('Enter a claim first.'); return; }
    try {
      const result = await request('/investigations', { method: 'POST', body: JSON.stringify({ claim }) });
      selectedId = result.investigation.id;
      $('workspace-selected').textContent = 'Selected: ' + claim;
      $('workspace-save-sources').disabled = false;
      status('Investigation created. It is not verified until evidence is checked.');
      await loadInvestigations();
      await loadGraph();
    } catch (e) {
      showServiceError(e);
    }
  });
  $('workspace-refresh').addEventListener('click', () => loadInvestigations().catch(showServiceError));
  $('workspace-compare').addEventListener('click', async () => {
    const claimA = $('workspace-claim').value.trim();
    const claimB = $('workspace-compare-claim').value.trim();
    const button = $('workspace-compare');
    const results = $('workspace-compare-results');
    if (!claimA || !claimB) { results.textContent = 'Enter both claim versions to compare.'; return; }

    button.disabled = true;
    results.textContent = 'Comparing wording…';
    try {
      const comparison = await request('/claim-family/compare', {
        method: 'POST',
        body: JSON.stringify({ claim_a: claimA, claim_b: claimB })
      });
      const card = document.createElement('div');
      card.className = 'claim-compare-result';
      const heading = document.createElement('strong');
      heading.textContent = (comparison.candidate_family ? 'Likely related wording' : 'No strong wording match') +
        ' · ' + Math.round((comparison.similarity || 0) * 100) + '% overlap';
      const note = document.createElement('p');
      note.textContent = comparison.material_change
        ? 'A number, date, or negation changed. Recheck this version before relying on the earlier result.'
        : comparison.must_reverify
          ? 'The wording changed enough that this version should be checked separately.'
          : 'No material number, date, or negation change was detected.';
      card.append(heading, note);
      const tokens = comparison.shared_tokens || [];
      if (tokens.length) {
        const shared = document.createElement('small');
        shared.textContent = 'Shared terms: ' + tokens.join(', ');
        card.append(shared);
      }
      results.replaceChildren(card);
    } catch (error) {
      results.textContent = error.message || 'Could not compare these claims.';
    } finally {
      button.disabled = false;
    }
  });
  $('workspace-save-sources').addEventListener('click', async () => {
    if (!selectedId) return;
    let sources;
    try { sources = JSON.parse($('workspace-sources').value || '[]'); }
    catch (_) { status('Sources must be valid JSON.'); return; }
    if (!Array.isArray(sources)) { status('Sources must be a JSON array.'); return; }
    try {
      const graph = await request('/investigations/' + encodeURIComponent(selectedId) + '/provenance', { method: 'POST', body: JSON.stringify({ sources }) });
      $('workspace-graph').textContent = JSON.stringify(graph, null, 2);
      status('Provenance graph saved. Only valid HTTP(S) source URLs are retained.');
    } catch (e) { status(e.message); }
  });
  $('workspace-ocr').addEventListener('click', async () => {
    const file = $('workspace-image').files?.[0];
    if (!file) { $('workspace-ocr-status').textContent = 'Choose an image first.'; return; }
    const form = new FormData(); form.append('image', file);
    try {
      const response = await fetch(await apiUrl('/message/ocr'), { method: 'POST', body: form });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'OCR failed');
      $('workspace-claim').value = data.text || '';
      $('workspace-ocr-status').textContent = data.warning || 'Text extracted. Verify it against the original image.';
    } catch (e) { $('workspace-ocr-status').textContent = e.message; }
  });
  $('workspace-language-match').addEventListener('click', async () => {
    const text = $('workspace-claim').value.trim();
    if (!text) { status('Enter or OCR a claim first.'); return; }
    try {
      const data = await request('/message/multilingual-match', { method: 'POST', body: JSON.stringify({ text }) });
      $('workspace-match-results').textContent = JSON.stringify(data, null, 2);
      status(data.note || 'Related claim lookup complete.');
    } catch (e) { status(e.message); }
  });
  loadInvestigations().catch(showServiceError);
});
