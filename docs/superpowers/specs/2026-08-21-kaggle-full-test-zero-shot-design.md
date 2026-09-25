# Kaggle full-test zero-shot design

Add a `test` phase to the existing SEA-LION Kaggle evaluation path. The phase loads every QA from `dataset/qas_test.json`, applies no sampling or final-ID filtering, and runs only zero-shot inference when selected by the notebook.

Update `notebooks/kaggle_sea_lion_poma.ipynb` to use `--phase test --mode zero_shot`, describe the full test run, and keep outputs cleared. Preserve resumable output behavior in the existing runner. Add focused parser, dataset-selection, and notebook regression tests.
