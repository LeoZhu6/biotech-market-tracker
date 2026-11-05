# Functional check — 2026-11-04

Scope: local working copy. No deployment was performed.

## Fixes

- Clear All resets the actual multiselect and search widgets, active analysis, memo, chat and generated PDF. Favorites and saved price alerts remain available.
- Start Analysis has a single entry point in the sidebar.
- Load Favorites restores the multiselect, rather than setting a list that the widget immediately overwrites.
- New Analysis returns to configuration and removes old research while retaining selected companies.
- Refresh uses a callback so Streamlit does not discard selection widgets during an early rerun. Empty-selection refresh is disabled.
- Changing companies or period invalidates the old memo, chat context and PDF.
- PDF download remains available after subsequent interactions.
- Chat uses a stable input key and a callback to clear submitted text.
- Retry actually retries the data request.
- Known preset company names can be searched locally; common Hengrui aliases also resolve through the validated Yahoo ticker.

## Automated interaction verification

`python -m unittest discover -s tests -v`: **17 tests passed**.

These tests run the real Streamlit controls and rendering logic. Yahoo, search HTTP requests and DeepSeek are replaced with deterministic fixtures in this suite.

| Workflow | Result |
|---|---|
| Select stocks, clear selection after analysis | Passed; widget empty and charts removed |
| Start Analysis | Passed; exactly one button |
| Save, load and clear favorites | Passed |
| New Analysis after generating memo | Passed; returns to configuration |
| Refresh with selection and chosen period | Passed |
| Change stocks after memo | Passed; stale artifacts removed |
| Change period after memo | Passed; stale artifacts removed |
| Render five charts and switch technical-analysis ticker | Passed |
| Add, trigger and delete Above alert | Passed |
| All five periods; add and trigger Below alert | Passed |
| Generate streamed report | Passed with simulated AI |
| Four quick questions, custom message, clear chat | Passed with simulated AI |
| Generate PDF, retain download across rerun | Passed; PDF parsed and expected content found |
| Export CSV | Passed; generated payload parsed and ticker/numeric values checked |
| Search and add company; duplicate prevention | Passed |
| Missing market data and Retry recovery | Passed |
| AI connection failure | Passed; error shown without enabling completed chat |
| Refresh with no selection | Passed; disabled |
| Known Chinese company search without remote providers | Passed |

Multiple checks belong to a single test, so this table is not a test-count breakdown.

## Live-service and browser checks

- Yahoo search: HTTP 200 with results for Pfizer.
- Yahoo history: 65 rows returned for PFE and SPY over three months.
- Real app searches: Pfizer, huirui and 600276.SS returned Add actions without runtime exceptions.
- Real app Chinese searches after fix: 辉瑞 and 恒瑞医药 both returned Add actions without runtime exceptions.
- Browser: selected PFE, saved favorite, cleared selection, loaded favorite, confirmed a single Start Analysis, and rendered the actual Yahoo-backed analysis.
- DeepSeek: live request failed during TLS handshake (`SSL: UNEXPECTED_EOF_WHILE_READING`). Actual AI answers and live streamed reports are **not verified**. No keys were printed or changed.
- Browser CSV download confirmation timed out in the browser-control tool. Generated CSV contents and PDF bytes are verified in the automated suite; browser download completion is **not verified**.
- Plotly charts rendered with real data; individual toolbar actions (zoom/pan/fullscreen/PNG download) were not fully verified in this session.

## Existing implementation gaps

- The current app links to news providers; it does not display the fetched company news list as an in-app feed.
- README mentions optional auto-refresh and a correlation heatmap, but this working copy has no corresponding implemented UI.
- Price alerts are checked when data is loaded/rerendered; they are not a background notification service.
- These are recorded as existing limitations, not passing features.

## Subsequent model and connection verification (2026-11-04)

- Report and chat now use `deepseek-flash` (DeepSeek-V4.1-Flash-1017 per official documentation).
- The expanded automated suite passed 18 tests, including report/chat model selection.
- A subsequent live check successfully listed available models and received both regular and streamed replies using the updated local key. The earlier TLS failure above describes the initial check.
- Local `.env` values are reloaded on app execution; the key file is excluded from version control.
