# Built-in IP profiles

BrandLoom ships three independent, equally selectable IP profiles:

| ID | Locked visual cues | Role |
| --- | --- | --- |
| `author-anime` | Black tousled hair; light gray jacket; white inner shirt; friendly confident expression | Presenter |
| `tuotuo` | Blue rounded form; square black glasses; lightning-shaped head feature | Execution/system |
| `xingbi` | Yellow five-point star; white gloves and shoes; friendly smile | Feedback/result |

Each profile includes a lossless canonical `reference.png` and JSON
provenance. The newly authorized exact files are kept as additional references
without replacing those historical canonical files:

- `ip/shared/tuotuo-xingbi-front-v1.png` is the shared primary 2D appearance
  reference and is included only when both `tuotuo` and `xingbi` are selected.
- `ip/tuotuo/tuotuo-five-view-v1.png` and
  `ip/xingbi/xingbi-five-view-v1.png` are supplemental geometry/turnaround
  references. They inform proportions and views, not the primary rendering
  style.

The exact source bytes, hashes, user confirmation, public-package scope, and
roles are recorded beside each file in its same-stem `.provenance.json`.
