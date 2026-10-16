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

## Combining energy and weather data

Energy and weather live in two different shapes: energy has one row
per hour for the whole country, while weather has one row per hour
and per city (five cities, 175,320 rows). To study how the weather
affects demand and prices I need them in a single table with one row
per hour, so combine_datasets reduces the weather to one row per hour
and joins it to the energy data.

The reduction is a simple mean of the five cities for each hour,
using groupby(level="time"). The columns get an avg_ prefix (avg_temp,
avg_humidity, avg_wind_speed, avg_rain_1h, avg_clouds_all) so it is
always clear that they are national averages and not a single
station. The join is done on the UTC time index with how="inner", so
only hours present in both datasets survive. Both files cover exactly
the same 35,064 hours, so nothing is lost and the final shape is
(35064, 25): the 20 energy columns plus the 5 weather ones.

I left wind_deg out on purpose. Wind direction is an angle, and the
mean of 350 and 10 degrees is 180, when the real average direction
is 0. A plain mean of angles is simply wrong, and doing it properly
(averaging the sine and cosine components) would add complexity for
a column I do not need to explain demand.

The mean is not weighted. Madrid or Barcelona count exactly the same
as Bilbao, even though they have far more population and electricity
demand. Weighting each city by its population would give a more
realistic national temperature. I decided to leave it as a future
improvement and to come back to it before closing the project.

The tests check the shape (35064, 25), that there are no missing
values after the join, and, with a small hand-made example of two
hours and two cities, that the averages come out right (10 and 20
give 15, 30 and 40 give 35).

## Exploring the data and two more cleaning rules

Before building any chart I explored the combined table with a
throwaway script, to see what the data looks like and to catch
anything suspicious. The general patterns came out as expected:
demand has a valley at 4am and two peaks, around 1pm and 9pm,
weekends are about 10% lower than weekdays, and over the year it
peaks in January and July. The official day-ahead load forecast is
off by 317 MW on average, around 1.1% of the demand. But the check
for strange values found two problems I had not seen before.

The first one is nuclear generation. It has three hours at exactly
0 in November 2017, with a mean of 6,263 MW the rest of the time.
Spain's whole nuclear fleet does not drop to zero for one hour and
come back, so I treat them as sensor failures: load_energy turns
them into missing values and the existing interpolation fills them.
They are isolated single hours, so interpolating is safe.

The second one is a 44-hour block between 18 and 20 July 2016 where
temperature, humidity and wind speed do not change at all in the
five cities at the same time. That cannot be real weather. It looks
like the data provider stopped updating and kept repeating the last
value. My first idea was to look only for repeated humidity, but
that would have been wrong: Barcelona has several blocks of 100%
humidity lasting days, and in those the temperature keeps changing,
so it is just fog and rain saturating the sensor. The rule that
works is to look at the three columns together: if temperature,
humidity and wind speed are all identical to the previous hour for
24 hours or more in a row, I consider the readings frozen. Those
rows become missing values and get interpolated, keeping the first
hour of the block because it is a real reading. Wind speed alone
repeats a lot in normal data because it comes in nearly whole
numbers, which is another reason not to look at one column.

Interpolating 44 hours is a compromise, since a straight line
loses the day and night cycle of the temperature. It affects 0.13%
of the rows, and I prefer that to trusting readings I know are
false. The tests check both rules with small files: a nuclear zero
between 6000 and 6200 becomes 6100, and a frozen day and a half of
weather turns into a ramp from 14 to 24 degrees. My first version
broke an older test because the small file had no nuclear column,
so the nuclear rule now only runs when the column exists.

## Analysis functions

The dashboard needs a few calculations on top of the clean table:
averages for different time scales, typical profiles, and how well
the official forecast does. I put them in a separate module,
analysis.py, instead of writing them inside the Streamlit code. That
way they can be tested on their own, and the app only has to call
them and draw the result.

aggregate takes the hourly table and a granularity (hour, day, week
or month) and returns the mean of every column for each period. I
use the mean and not the sum because demand and generation are
measured in MW, which is power: the mean of a day is the average
power of that day, so the four granularities stay on the same scale
and can be compared. Before grouping, the index is converted from
UTC to Madrid time. If I grouped in UTC, a day would start at 1am or
2am local time and would cut the night in half, which would distort
the daily values.

profile gives the average of a column by hour of the day, day of the
week or month, again in Madrid time. It is the same calculation I did
while exploring the data, now reusable for demand, price, solar or
any other column.

forecast_metrics compares the official load forecast with the real
demand and returns three numbers: the mean error, to see if it is
biased in one direction, the MAE in MW, and the MAPE as a
percentage, which is the easiest one to show in a KPI card.

The tests use small tables built by hand so the right answer can be
worked out on paper. The daily and hourly tests start at 23:00 UTC,
which is midnight in Madrid in winter, so every block of 24 rows is
one full local day. 4 January 2016 was a Monday, which checks that
the weekly profile starts on day 0. For the forecast, errors of +10
and -10 on loads of 100 and 200 must give a bias of 0, an MAE of 10
and a MAPE of 7.5%.