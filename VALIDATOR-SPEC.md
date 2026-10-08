# Validator specification, v0.1

What the validator checks when it grades an intracranial EEG dataset, and
how the grade is computed. This document is the contract: a grade means
exactly this and nothing more.

## Scope

The validator grades a dataset in BIDS-iEEG layout (on disk, or on OpenNeuro
by id) or a DANDI dandiset of NWB files (read by file headers, nothing
downloaded whole). It answers one question: **can someone who did not collect this
data use it, and trust what it says about itself?** It does not judge
scientific quality or the study design.

Two tiers:

- **Metadata tier**: reads only descriptive files (dataset description,
  participants, sidecar JSON, channel/electrode/event tables). Every check
  below belongs to this tier unless marked *signal*.
- **Signal tier**: additionally reads a sample of recordings and measures
  what the metadata claims (bad channels, line noise, the real band limit).
  Signal measurements are reported alongside the grade; they do not change it
  in v0.1.

## Checks

Each check has a weight. A check that does not apply to a dataset (for
example, event checks on a dataset with no task recordings) is skipped and
does not count. "Recordings" means iEEG recordings found in the dataset,
up to a cap of 400 spread across subjects; the report says when sampling
happened.

### Identity — can it be cited and used legally?

| Check | Weight | Passes when |
|---|---|---|
| license | 3 | `dataset_description.json` states a license |
| doi | 1 | a DatasetDOI is given |
| citation | 1 | HowToAcknowledge or ReferencesAndLinks is given |
| readme | 1 | a README of at least 300 characters exists |
| ethics | 1 | EthicsApprovals is given |
| data_present | 2 | iEEG data files exist in `ieeg/` directories |

### Acquisition — is it known how the signal was recorded?

| Check | Weight | Passes when |
|---|---|---|
| manufacturer | 3 | Manufacturer is given (not `n/a`) in ≥95% of sidecars |
| model | 1 | ManufacturersModelName is given in ≥95% |
| line_freq | 2 | PowerLineFrequency is given in ≥95% |
| hardware_filters | 3 | hardware filters stated (HardwareFilters, or low/high cutoff in channels.tsv) for ≥95% of recordings |
| software_filters | 2 | the SoftwareFilters field is present in ≥95% (`n/a` passes: it states that none were applied) |
| reference | 2 | iEEGReference is given in ≥95% |
| duration | 1 | RecordingDuration is given in ≥95% |
| sfreq | 0 | informational: the sampling rates present |

### Channels — can each channel be identified and trusted?

| Check | Weight | Passes when |
|---|---|---|
| channels_tsv | 3 | channels.tsv exists for ≥95% of recordings |
| channel_types_valid | 2 | ≥99% of channel types are valid BIDS types |
| ieeg_channels_exist | 2 | ≥95% of recordings contain ECOG/SEEG/DBS channels |
| scalp_mislabeled | 2 | no scalp-EEG or EKG channel (by name) is typed as iEEG |
| status_column | 2 | a filled `status` column exists in ≥95% of channel tables |
| units | 1 | units are given in ≥95% of channel tables |
| sidecar_counts_match | 1 | sidecar channel counts match channels.tsv in ≥95% |
| channel_count_consistency | 0 | informational: subjects whose runs differ in channel count |

### Localization — is it known where each contact is?

| Check | Weight | Passes when |
|---|---|---|
| electrodes_tsv | 3 | electrodes.tsv exists for ≥90% of subjects |
| coordsystem | 2 | every coordsystem.json names a coordinate system (not Other) |
| template_space | 2 | coordinates are available in a template (MNI-family / fsaverage) space |
| coords_complete | 2 | ≥90% of electrodes have numeric x, y, z |

### Subjects — is the cohort described?

| Check | Weight | Passes when |
|---|---|---|
| participants | 2 | participants.tsv has age and sex filled for >80% of subjects |
| participants_dictionary | 1 | participants.json exists |
| clinical_context | 2 | at least one implant/clinical column (hemisphere, implant, pathology, outcome, ...) exists |

### Labels — is there something to predict?

| Check | Weight | Passes when |
|---|---|---|
| events_present | 3 | non-empty events.tsv for ≥90% of task recordings (rest/sleep/interictal tasks excluded) |
| task_description | 1 | TaskDescription or Instructions given for ≥90% of task recordings |
| events_vocabulary | 0 | informational: distinct event labels |

## NWB datasets

For NWB, the same checks run on the equivalent fields: the dandiset's
metadata stands in for `dataset_description.json` (license, DOI, citation,
ethics approvals); each NWB file is one recording; `Device.manufacturer` and
`Device.description` stand in for Manufacturer and model; the largest
`ElectricalSeries` gives sampling rate (from `starting_time.rate`, or from
timestamps), duration, units and software filtering; the electrodes table is
the channel table (types inferred from electrode-group descriptions and
names; `good`/`bad`/`status` columns give channel status; `filtering` gives
hardware filters); `x`/`y`/`z` columns are the electrode positions; NWB
intervals are the events. NWB has no field for mains frequency, reference
scheme or coordinate space, so those pass only if the dataset states them in
a device, electrode-group or series description. `participants_dictionary`
does not apply to NWB. Up to 8 files per dandiset are read, one per subject;
subject-level checks then count only the subjects read.

## Score and grade

score = (sum of weights of passed checks) / (sum of weights of applicable checks)

| Grade | Score |
|---|---|
| A | ≥ 0.90 |
| B | ≥ 0.80 |
| C | ≥ 0.65 |
| D | ≥ 0.50 |
| F | < 0.50 |

Per-category scores are reported the same way within each category.

## Signal tier measurements (reported, not graded in v0.1)

For each sampled recording (two sampled per dataset, spread across the
dataset; 120 s per recording, from the file start for BIDS and the file
middle for NWB; iEEG channels only; files over 400 MB are not sampled):

- `flat_channels`: standard deviation below 0.1 µV
- `variance_outliers`: log-variance more than 5 robust z-scores from the median
- `bids_bad_channels`: channels the dataset itself marks bad
- `unmarked_flat`, `unmarked_outliers`: the two above minus what the dataset marks
- `line_noise_ratio`: power at the mains frequency relative to 3–10 Hz away;
  above 10 counts as strong mains noise
- `measured_band_limit_hz`: highest frequency with power within 20 dB of the
  5–20 Hz band; below 60% of Nyquist counts as band-limited before upload

Across datasets the summary reports the share of measured datasets with
unmarked flat channels, unmarked outliers, strong mains noise, and
band-limiting below Nyquist.

## Versioning

The spec version is recorded in every report. Checks, weights and bands
change only with a new spec version; a grade always refers to the version
it was issued under.
