# Unit 3 submission — FitFindr

Repository URL to submit and reuse next unit:

https://github.com/Omar-Adham/ai201-project2-fitfindr-starter-v2026

- [x] `criteria.md` contains five criteria, each with a target and reason.
- [x] README has all five unit 3 sections filled in.
- [x] Tool Inventory gives typed inputs, return shapes, and empty cases.
- [x] Planning Loop states both branches and names `agent.py::run_agent`.
- [x] Sample Run includes a complete query and per-tool terminal evidence.
- [x] Real model run completed; empty search stops before the model tools.
- [x] Five offline branch/state tests pass (`python -m unittest test_agent -v`).
- [x] At least four new commits: milestones 1–5 each have their own commit,
  followed by the milestone 6 write-up.
- [ ] Paste the repository URL above into the course submission form and submit.

The course form submission must be completed separately; this file records the
URL, not a claim that the course platform has received it. Preserve this
repository and its commit history for unit 4.

# Unit 4 submission — the test

Same repository URL as unit 3 (above). Do not delete or recreate the repo.

- [x] `mcp_server.py` registers `search_listings`; `run_agent` calls it through
  `mcp_client.call_tool`, and the trace labels it `search_listings (via MCP)`.
- [x] All three failure modes triggered; `ModelUnavailable` now handled in
  `run_agent`.
- [x] Run Log — Before and After: five criteria, five tries each, cache off
  (`results/run_2026-10-14_1224_before.md`, `results/run_2026-10-14_1232_after.md`).
- [x] Verdict per criterion; criterion 5 revised underneath the original in
  `criteria.md`; the miss diagnosed to `create_fit_card` (step + mechanism).
- [x] One improvement (`create_fit_card` receives the wardrobe); revised
  criterion 5 went from MISSED 3/5 to MET 5/5.
- [x] What's Still Broken written.
- [x] Six unit 4 commits, one per milestone.
- [ ] Push to GitHub, then submit the same URL in the course form.
