Think Before Coding (no silent assumptions about regulations or partner fields).

Simplicity First (minimal pipeline: one live source → one rule → one gap → one alert).

Surgical Changes (Bob should only touch files you ask it to change).

Goal-Driven Execution (success = end-to-end rule→gap→alert, not “lots of code”).

Read Before You Write (Bob must read partners.json, taxonomy.json, sample_expected_output.json before generating assessment code).

Checkpoint After Every Significant Step (Bob summarizes after scraper, after rule parser, after gap assessor, after alert).

Surface Conflicts, Don’t Average Them
If two patterns in the data or code disagree, don’t blend them.
Pick one (more recent / more explicit), explain why, and flag the other.

Fail Loud
If you aren’t sure a gap or rule application is correct, say so explicitly.
Prefer surfacing uncertainty over silently assuming everything worked.