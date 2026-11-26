# Observed-outcome benchmark

This scores the Type 1 share over four hours from November 2024 to October 2026. It compares the same month last year with the value two months earlier, allowing for the monthly release lag. The source is a revised workbook, so these are not archived publication vintages. The history starts after the earlier trial-period exclusions ended.

| Scored cases | Baseline mean loss | Candidate mean loss | Candidate wins | Baseline wins | Ties |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 24 | 1.885306 | 1.453649 | 15 | 9 | 0 |

**Metric:** MAE in percentage points, national Type 1 over-four-hours rate. Lower is better. See [aggregate results](observed-results.json) for the largest regression and breakdowns.

The seasonal rule reduced mean error overall. It was 3.79 percentage points worse than baseline in December 2025. This is an England-wide monthly aggregate benchmark. It does not validate trust-level forecasts, 12-hour trolley waits, or clinical decisions.

## Reproduce

Save [NHS England national A&E time series](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/11/Monthly-AE-Time-Series-October-2026-Es49Qw.xls) as `nhs.xls`. The input file SHA-256 is `87f27f8a75170dba088e45d4df8a4236cd6efe21ae4594ebd0e057ac98986b31`. The workbook requires `xlrd`; all benchmarks use `pandas` and `numpy`.

```sh
python replay/observed_backtest.py nhs.xls --output /tmp/observed-results.json
diff -u replay/observed-results.json /tmp/observed-results.json
```
