## What changed

Describe the user-visible change and why it is needed.

## Safety boundary

- [ ] Existing drafts are not replaced without an explicit request and backup.
- [ ] Diagnostics remain read-only unless a write test is explicitly selected.
- [ ] No tokens, cookies, private media, local draft data, or runtime caches are included.
- [ ] Upstream and vendored-license notices remain intact.

## Verification

- [ ] `python -m unittest discover -s tests -p "test_*.py" -v`
- [ ] `python tools/check_repo_hygiene.py`
- [ ] `python tools/validate_data_schema.py`
- [ ] Relevant manual JianYing/device/export checks are stated separately.
