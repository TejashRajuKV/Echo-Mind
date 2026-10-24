const { test, expect } = require('@playwright/test');

const apiOrigin = 'http://localhost:8080';
const analysis = {
  classification: 'Suspicious',
  score: 45,
  explanation: 'Mocked analysis result for deterministic browser tests.',
  evidence: 'Insufficient independent evidence.',
  evidence_sources: [],
  consensus: {
    status: 'Unverified / Insufficient Independent Evidence',
    detail: 'Test fixture contains no live evidence.',
    consensus_direction: 'unknown',
    consensus_percentage: 0,
    supporting_sources_count: 0,
    refuting_sources_count: 0,
    neutral_sources_count: 0,
    independent_publisher_count: 0,
    conflict_detected: false,
  },
  credibility_breakdown: {
    source_convergence_score: 50,
    evidence_authority_score: 50,
    publisher_independence_score: 40,
    formula_explanation: 'Deterministic test fixture.',
  },
  gamification: { points: 10, badges: [], badge_earned: null },
  personalization: { category: 'General', tip: 'Check the primary source.' },
  tips: ['Open the original source.'],
  subclaims: [],
};

async function mockApi(page) {
  await page.route(apiOrigin + '/**', async route => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === '/analyze') {
      const payload = {
        ...analysis,
        explanation: '<img src=x onerror=alert(1)><script id="xss-probe">alert(1)</script>Mocked analysis result.',
      };
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
    }
    if (path === '/evolution') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        claim: url.searchParams.get('claim'), timeline: [], verdict_drift_detected: false,
      }) });
    }
    if (path === '/monitor/subscribe') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        status: 'subscribed', message: 'Subscribed successfully!',
      }) });
    }
    if (path === '/report') {
      return route.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>Mock report</title><h1>Mock report opened</h1>' });
    }
    if (path === '/document/analyze') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        document_integrity_score: 80, total_passages: 2, total_claims_extracted: 1,
        verified_claims: [{
          paragraph_num: 1, estimated_page: 1, verdict: 'Suspicious', score: 40,
          claim_text: 'Mock document claim', surrounding_context: 'Mock context',
        }],
      }) });
    }
    if (path === '/transparency') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        citation_coverage_pct: 80, retrieval_success_pct: 90, unresolved_conflict_pct: 10,
        average_latency_ms: 120, eval_benchmark_accuracy: 'Not measured', open_human_corrections: 0,
      }) });
    }
    if (path === '/correction') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        status: 'received', message: 'Correction received into audit queue!',
      }) });
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });
}

async function loadAnalysis(page) {
  await mockApi(page);
  await page.goto('/');
  await page.locator('#claimInput').fill('A deterministic test claim');
  await page.locator('#checkClaim').click();
  await expect(page.locator('.action-toolbar')).toBeVisible();
}

test.beforeEach(async ({ page }) => {
  await loadAnalysis(page);
});

test('claim analysis renders safely and removes executable markup', async ({ page }) => {
  await expect(page.locator('.verdict-title')).toContainText('Suspicious');
  await expect(page.locator('#demoOutput #xss-probe')).toHaveCount(0);
  await expect(page.locator('#demoOutput [onerror]')).toHaveCount(0);
  await expect(page.locator('#demoOutput')).toContainText('Mocked analysis result.');
});

test('evolution timeline action calls API and opens a modal', async ({ page }) => {
  await page.locator('#btnViewEvolution').click();
  await expect(page.locator('#echoModalBackdrop')).toContainText('Claim Evolution');
});

test('monitor action submits subscription and shows confirmation', async ({ page }) => {
  await page.locator('#btnMonitorClaim').click();
  await page.locator('#monitorEmailInput').fill('tester@example.com');
  await page.locator('#btnConfirmMonitor').click();
  await expect(page.locator('#monitorStatusMsg')).toContainText('Subscribed successfully!');
});

test('share report action opens report in a new tab', async ({ page, context }) => {
  const popupPromise = context.waitForEvent('page');
  await page.locator('#btnShareReport').click();
  const popup = await popupPromise;
  await popup.waitForLoadState();
  await expect(popup.locator('h1')).toHaveText('Mock report opened');
});

test('document scan action submits pasted content and renders results', async ({ page }) => {
  await page.locator('#btnOpenDocAnalysis').click();
  await page.locator('#docTitleInput').fill('Mock document');
  await page.locator('#docContentInput').fill('A paragraph with a claim.');
  await page.locator('#btnRunDocScan').click();
  await expect(page.locator('#docScanResults')).toContainText('Document Integrity Score');
  await expect(page.locator('#docScanResults')).toContainText('Mock document claim');
});

test('transparency action fetches and renders dashboard metrics', async ({ page }) => {
  await page.locator('#btnOpenTransparency').click();
  await expect(page.locator('#echoModalBackdrop')).toContainText('Citation Coverage');
  await expect(page.locator('#echoModalBackdrop')).toContainText('120 ms');
});

test('correction action submits feedback and displays acknowledgement', async ({ page }) => {
  await page.locator('#btnSubmitCorrection').click();
  await page.locator('#corrUrlInput').fill('https://example.org/primary-evidence');
  await page.locator('#corrRationaleInput').fill('Mocked primary evidence rationale.');
  await page.locator('#btnSendCorrection').click();
  await expect(page.locator('#corrStatusMsg')).toContainText('Correction received into audit queue!');
});
