## Choosing the dataset

For the dashboard I wanted a real dataset with a long, clean time
series and relationships that make physical sense, so there is
something meaningful to show. I picked the Kaggle dataset "Hourly
energy demand, generation and weather" (CC0 license), which covers
Spain from 2015 to 2018, over the other candidates (sports and air
traffic). It comes as two files: energy_dataset.csv (one row per hour
with demand, generation by source, the grid operator's day-ahead
forecasts and electricity prices) and weather_features.csv (hourly
weather measurements for several cities).

Known limitations: the data ends in 2018 and it only covers one
country.

## Storing the data

The raw CSVs weigh 6 MB and 19 MB, which would bloat the repository
history for no good reason. Instead I committed gzip-compressed copies
(.csv.gz, about 4 MB in total) and added the raw CSVs to .gitignore.
pandas reads .csv.gz files directly by looking at the extension, so
nothing has to be decompressed, and anyone who clones the repository
can run the project without downloading anything from Kaggle.

## Loading and cleaning the energy data

I explored the file first with a throwaway script (explore.py, kept out
of the repository through .gitignore) using head(), info(), isna() and
describe(), and only then wrote the cleaning logic in load_energy()
inside data_processing.py. The file has 35,064 rows, exactly four years
of hourly data, so the series is complete.

The time column is text with a UTC offset that changes between +01:00
in winter and +02:00 in summer. Parsing it with utc=True unifies both
offsets, and I use the result as the index so the data can later be
resampled and filtered by date range.

8 of the 28 numeric columns carry no information: two are completely
empty (generation hydro pumped storage aggregated and forecast wind
offshore eday ahead) and six are always 0 (coal-derived gas, oil shale,
peat, geothermal, marine and offshore wind). Instead of listing them by
name, I keep only the columns with more than one distinct value
(nunique() > 1), since an empty column has 0 distinct values and a
constant one has 1.

The remaining columns have 17 to 19 missing hours each (36 for total
load actual), about 0.05% of the data. They are isolated one- or
two-hour gaps, so I fill them with time-based interpolation: a missing
hour is almost always very similar to the hours around it. Dropping
those rows would have left holes in a time series, which would break
the plots and any resampling.

I deliberately did not reduce the resolution when loading. 35,064 rows
is tiny for pandas, and keeping one value per hour preserves daily
patterns (when demand rises, when solar produces). If the dashboard
needs fewer points, it will aggregate with resample (mean, max or sum)
only for display, never by keeping every n-th row, which could skip the
peaks.

One thing I noticed and left untouched: generation nuclear has a
minimum of 0 while its 25th percentile is 5,760 MW. It may be a real
outage or a data error, so I will check it during the EDA before
deciding anything.

## Tests

The tests live in src/tests/test_data_processing.py and the data is
loaded once through a module-scoped fixture, so the 35,000 rows aren't
reprocessed for every test. Five tests check the cleaned real dataset:
the shape (35,064 rows, 20 columns), a UTC datetime index that is
sorted and has no duplicates, no missing values, and no constant or
empty columns.

The sixth test builds a tiny five-row CSV in a temporary directory,
with a gap between 20 and 40 and a column that is always 0, and checks
that the gap is interpolated to 30 and that the constant column is
dropped. Unlike the others, it tests the logic itself and doesn't
depend on the real file.