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

## Loading and cleaning the weather data

I explored weather_features.csv.gz with the same throwaway script as the
energy file. It has 178,396 rows for five cities (Madrid, Barcelona,
Valencia, Seville and Bilbao), in long format: one row per hour and
city, not one row per hour. Each city should have the same 35,064 hours
as the energy file, but the counts were higher, and the excess added up
to exactly 3,076, which matched the number of duplicated hour-city pairs.

Looking at the duplicates, all the numeric columns were identical; the
only difference was the weather description (for example "light rain"
and "drizzle", or "rain" and "thunderstorm" for the same hour), which
are two simultaneous conditions rather than two measurements. I keep
the first copy, and since I don't use the text columns, nothing useful
is lost. After this each city has exactly 35,064 hours, with no gaps.

Two smaller problems: Barcelona appeared as " Barcelona" with a leading
space, which would have broken any filter by city name, so I strip the
names. And temperatures are stored in Kelvin, so I subtract 273.15 to
work in Celsius (the result goes from -10.9 to 42.5, which is plausible
for Spain).

The weather file has no missing values, but it has impossible ones,
which are worse because nothing flags them: pressure up to 1,008,371
hPa and as low as 0, 63 rows with a humidity of exactly 0, and wind
speeds up to 133 m/s. Humidity and wind only have a handful of bad
rows (63 and 4 out of 178,396), so I turn them into NaN and interpolate
them per city, grouping by city_name so that the weather of Madrid is
never mixed with that of Bilbao. Treating a humidity of exactly 0 as a
gap is a judgement call: it almost never happens in these cities and it
is usually a filler value.

I first handled pressure the same way, with an accepted range of
900-1100 hPa, but that range was picked without looking at the
distribution, and after cleaning the maximum was still 1,090 hPa.
Looking at the extremes, 367 rows were above 1050 and 2,311 below 960,
and they come in runs of consecutive hours with the same value (for
example seven hours in a row at 1086-1087 hPa in August 2016, a
pressure that has never been recorded in Spain), which looks like a
stuck sensor rather than isolated glitches. Cutting those would leave
long gaps, and interpolating across long gaps means inventing data, so I
dropped the pressure column entirely. It is also the variable least
related to the electricity system.

The columns kept are temp, humidity, wind_speed, wind_deg, rain_1h and
clouds_all. I dropped temp_min and temp_max (redundant with temp), the
four text columns describing the weather, and rain_3h and snow_3h
(almost always 0). The result stays in long format with city_name as a
column and the UTC time as the index, since that is what a city
selector in the dashboard needs. Combining it with the energy data is
a separate step.