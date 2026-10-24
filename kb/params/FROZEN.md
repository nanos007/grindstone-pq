# Shortlist freeze record

`shortlist_draft.yaml` is the parameter set that campaign run `196e7e91e907` measured (2026-10-22 → 10-24).
The file is left byte-identical, including its `status: DRAFT` header, because the run manifest pins it by
hash:

    sha256(shortlist_draft.yaml) = 6b3c07183cdf2fa939c63aead9808467046a5d6f6408fbeca8845bd7599763aa
    (data/manifest.jsonl, campaign_start records of runs smoke-e8741328af0b, 883946705828, 196e7e91e907)

Editing the file, even its header, breaks that link. Treat this record as the freeze. Any change to the
parameter set goes into a new file and a new campaign run.

Owner sign-off: [ ] pending (threats_to_validity.md, "Must-fix" item 3).
