# brain-bench

The trust layer for intracranial EEG (iEEG): independent grades for iEEG
datasets, a public benchmark, and private evaluation of models on data that
never leaves the people who collected it.

This repository holds the public pieces: the validator specification and
published grades, the data interface, the submission contract, the
evaluation runner, and results.

## Validator

Every human iEEG dataset on OpenNeuro has been graded under
[`VALIDATOR-SPEC.md`](VALIDATOR-SPEC.md): 32 checks in six categories
(identity, acquisition, channels, localization, subjects, labels), a weighted
score and a letter grade. The grade answers one question: can someone who did
not collect this data use it, and trust what it says about itself?

- `validator/summary.json`: grades for every dataset, per-category scores, and
  the share of datasets failing each check
- `validator/openneuro_ieeg_datasets.json`: the enumeration that was graded

Grades refer to the spec version recorded in each report; checks and weights
change only with a new spec version.

## Benchmark

Training data is provided to participating teams. Test data, including a
whole recording site never seen in training, is held privately; brain-bench
runs the evaluation and publishes the score.

## The data interface

A model receives recordings as:

- `signal`: float32 array `[channels, samples]` at 500 Hz, 0.5–200 Hz
- `channels`: one row per channel: `name`, `type` (`ecog`/`seeg`/...), `x`/`y`/`z` in mm with `coord_space`, `hardware`, `is_bad`
- `events`: `onset`, `duration`, `label` from a shared label ontology

Channel counts vary between recordings and between sites. See
`brainbench/schema.py` for the full tables and `brainbench/ontology.py`
for the labels.

```python
from brainbench.loader import BrainBench, windows

bb = BrainBench("path/to/data")
for rec in bb.recordings(split="train"):
    for x, t0 in windows(rec.signal, rec.sfreq, length_s=4.0):
        ...
```

## Tasks

| Task | Classes | Window |
|---|---|---|
| `media_vs_rest` | watching film/TV vs rest (incl. sleep/rest) | 4 s |
| `media_vs_awake_rest` | watching film/TV vs awake rest | 4 s |
| `ictal_vs_interictal` | inside a seizure vs between seizures | 4 s |

Defined in `brainbench/submission.py`. A window is labeled only when fully
inside one class.

## Submitting

A submission is one Python file that defines `build()` returning a model
implementing the contract in `brainbench/submission.py`:

```python
class MyModel:
    def fit(self, windows):              # iterable of (x, channels, sfreq, label)
        ...
    def predict_proba(self, x, channels, sfreq) -> float:   # P(positive class)
        ...

def build():
    return MyModel()
```

`submissions/example_submission.py` is a complete, runnable example. Test
your file locally on the training data you were given:

```sh
brainbench-evaluate run my_model.py --train <train-data> --test <train-data> --task media_vs_rest
```

(scoring on your own training data only checks that it runs). Then send the
file; brain-bench fits it on the training partition and scores it on the
private test partitions, and the result record is published to `results/`.
`brainbench-evaluate board results/*.json` prints the leaderboard.

Scores: per-window balanced accuracy and AUROC on `test` (same sites as
training, unseen subjects) and `test_xdevice` (a site and device never seen
in training). The cross-device number is the one that matters.

`brainbench/benchmark.py` is the baseline (mean log band-power + logistic
regression) and shows the contract in use. Results are in `results/`.

## Sources

Each benchmark release's `LICENSES.md` lists every source dataset with its
license and citation. Released data uses openly licensed sources only
(CC0 / CC-BY), cited as their licenses require. The validator grades
datasets in place and redistributes nothing.
