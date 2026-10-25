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

## Dashboard skeleton and filters

The dashboard is a Streamlit app in src/app.py. Streamlit runs the
whole script again every time the user touches a control, so the
first thing I had to solve was not reloading the data on every
click. Reading and cleaning both files takes several seconds,
mostly the weather one with its 175,000 rows. I wrapped the loading
in a function with the st.cache_data decorator, so it runs once and
every later call returns the stored result. After the first load,
changing a filter is instant. The paths to the data files are built
from the location of app.py itself, the same trick I use in the
tests, so the app starts from any folder.

The sidebar has two filters: a date range and a granularity (hour,
day, week or month). The date range needed one extra check. While
the user is picking dates, after clicking the first one and before
the second, Streamlit returns a tuple with only one date, and
unpacking it would crash the app. If the range is incomplete the app
shows a short message and stops there with st.stop.

The filtering itself is in analysis.py as filter_dates, not inside
the app, so that it can be tested. It works in Madrid time, like
aggregate, so a selected day is always a full local day. The order
matters: the app first filters the dates and then aggregates, so
only the requested rows are grouped. With the full range, day gives
1,461 rows and month gives 48. The test builds three local days of
hourly data, asks for the middle one, and checks that it gets 24
rows starting at midnight with the right first value.

## KPI cards and demand chart

The top of the dashboard now has four KPI cards, which are the key
figures of the selected period: average demand, average price, the
forecast error and the average temperature. Under them there is a
first line chart of the demand, made with Plotly Express. A KPI is
just a summary number, the thing you want to see at a glance before
going into the detail of any chart.

One design decision here is that the cards are calculated from the
hourly data of the selected dates, not from the data already grouped
by granularity. If they came from the grouped table, the average
demand could change slightly when switching from hour to month,
because of incomplete periods at the edges of the range. This way
the four cards depend only on the date range, and the granularity
only changes the chart. With the full range the app shows 28,698 MW
of average demand, 57.9 euros per MWh, a forecast error of 1.10% and
16.6 degrees of average temperature, which match the numbers I got
while exploring the data.

The chart is interactive without extra code: hovering shows the
exact value, dragging zooms in and a double click resets it. The
daily view looks very jagged because the demand goes up and down
every week, with high weekdays and low weekends, and that rhythm
hides the yearly trend. Switching to weekly or monthly makes the
U shape of the year visible, with peaks in winter and summer. The
table behind the chart is in a collapsed section so it can be
checked without filling the screen.

This piece has no new tests. It only calls Streamlit and Plotly, and
the calculations behind the numbers, filter_dates, aggregate and
forecast_metrics, are already covered by their own tests.

## Patterns tab

The dashboard now uses tabs. The chart I already had moved to an
Overview tab, and a new Patterns tab shows the typical profile of the
demand or the price by hour of the day and by day of the week. A
radio button chooses the variable, and the dictionary that links the
readable label with the real column name lets the same two charts
work for both, because profile in analysis.py was written for any
column from the start.

The profiles are calculated from the hourly data of the selected
dates, so they follow the date range but not the granularity. A
profile by hour makes no sense on data already averaged by month. The
hours are in Madrid time, as everywhere else in the app.

With the full range the hourly profile shows what I saw while
exploring: a valley at 4am with about 22.7 GW, and two peaks, one at
1pm and another at 9pm, both around 32 GW. The price follows the same
shape, from about 47 euros per MWh at 4am to about 65 at 8 and 9pm.
By day of the week, Saturday and Sunday are around 10% below the
weekdays. The price is also lower at the weekend, and my explanation
is that with less demand the most expensive power plants are not
needed, and the price in this market is set by the last plant that
has to be switched on. I checked it later in the Generation tab, where
gas generation is clearly lower at the weekend.

One small detail: the weekday names are built from the index of the
profile and not from a fixed list of seven days. If the user selects
a very short range that does not include every day of the week, the
profile has fewer than seven values and the chart would fail with a
fixed list. This piece has no new tests, since the calculation
itself is already covered by the profile tests.

## Weather tab

The Weather tab compares the average temperature with the demand or
the price, chosen with a radio button. Earlier I had seen that the
linear correlation between temperature and demand was only 0.21, but
I expected a real relationship in the shape of a U: heating makes the
demand go up when it is cold, and air conditioning makes it go up
when it is hot. A straight line cannot describe that, so the chart
has to show the shape and not only one number.

The chart uses daily averages and not the hourly data. Drawing
35,000 points would be slow, and above all the demand changes a lot
during the day, from 22 GW to 32 GW, which would blur the effect of
the temperature. Averaging by day removes that daily cycle. Each day
is a semi-transparent point, so the places where many days pile up
are visible, and on top there is a line with the average demand for
each 2 degree bin of temperature. For that line I added binned_mean
to analysis.py, which rounds every temperature down to the start of
its bin and averages the other column inside each bin. The test uses
four values and two bins of width 10, so the right answer can be
computed by hand. In the chart the points of the line are placed at
the centre of each bin and not at its lower edge, otherwise the
whole curve would look shifted half a bin to the left.

The U shape is clear for the demand. The average goes down to about
27,400 MW around 17 degrees and goes up to 30,000 MW or more with
both cold and heat. The cloud of points is very wide, from 22,000
to 35,000 MW at the same temperature, because the temperature is
only one of the factors, and the day of the week and the season
matter too. The bins at the extremes have few days, so the line is
noisy there. The price shows a much weaker relationship, with a
minimum of about 52 euros per MWh between 13 and 15 degrees and
higher prices in the coldest days. I would not read much more into
it, since the price depends more on gas and renewables.

The temperature used here is the unweighted mean of the five
cities, the improvement I left for the end of the project. The tab
would be a good place to see its effect, since a population-weighted
temperature should fit the demand a little better.

## Generation tab

The dataset has 14 columns of generation, which is too many for a
readable chart, and one of them is not generation at all:
hydro pumped storage consumption is the electricity used to pump
water uphill, so adding it would be wrong. I left it out and grouped
the other 13 columns into 7 sources: nuclear, gas, coal, hydro, wind,
solar and other. The grouping is a dictionary in analysis.py,
MIX_GROUPS, and generation_mix sums the columns of each group. The
test gives every column the value 1 and checks that coal, with two
columns, gives 2, that other, with five, gives 5, and that the total
is 13, so no source is lost or counted twice.

The tab has three charts. A stacked area chart shows the mix over
time with the granularity chosen in the sidebar, and a bar chart
shows the share of each source in the selected dates. The third one
is the average gas generation by day of the week, and I added it to
check an explanation I had given for the lower price at the weekend:
with less demand, the expensive power plants are not needed, and the
price is set by the last plant that has to be switched on. The chart
confirms it, since gas generation falls from about 5,900 MW on
weekdays to about 4,800 MW on Sunday. In the shares, the biggest
source in the full period is nuclear with 22%, followed by gas with
about 20% and wind with about 19%. Because this only covers
generation inside the country, imports and exports are not part of
the picture.

## Forecast tab

The dataset includes the official forecast of the demand, published
the day before by the grid operator, so I can measure how well it
does. I defined the error as forecast minus actual, so a positive
value means the forecast was too high. forecast_errors returns, hour
by hour, that error in MW and the absolute error as a percentage of
the real demand. It returns a table with the same date index, so the
profile function I already had works on it without changes.

The tab shows the forecast and the real demand on the same chart,
the histogram of the hourly error, and the average absolute error by
hour of the day. In the daily view the two lines are almost on top of
each other, which says a lot about the forecast but makes the chart
dull, so the interesting view is the hourly one on a range of one or
two weeks. Overall the mean absolute error is about 317 MW, around
1.1% of the demand, and the mean error is only 13.8 MW, so there is
no relevant bias.

The histogram is centred on zero and narrow, but it has a few
isolated errors of several thousand MW, up to about 13,000 MW. I
looked at them: only seven hours are above 4,000 MW out of 35,064,
and together they add less than 2 MW to the mean absolute error of
317 MW. Two of them are on 1 May 2015, a public holiday, where the
forecast expected a normal working day and was about 4,500 MW too
high, which is a real forecast miss. The other five look more like
faulty readings of the real demand, for example 18,616 MW at 7pm on
26 August 2015 when the forecast was 31,545 MW, but I cannot prove
it, and I do not know which side of each pair is wrong, so I left
all seven as they are instead of inventing a cleaning rule.

By hour of the day, the error is lowest at night, about 0.8%
between 3 and 6am, and highest in the late afternoon, about 1.4%
around 5 and 6pm.

I did not build this tab only to describe the forecast. When I build
my own model to predict the price, the same idea applies, since the
dataset also has the day-ahead price set by the market. That column
will be the reference to beat, and the first thing to compare against
will be simple rules like repeating the price of the day before.