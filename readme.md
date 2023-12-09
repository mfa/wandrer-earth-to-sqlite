## wandrer-earth-to-sqlite

Convert [wandrer.earth your points](https://wandrer.earth/dashboard/stats) xlsx file to sqlite to query in [Datasette](https://datasette.io/).

More info in this blogpost: <https://madflex.de/view-wandrer-earth-your-points-in-sql/>.

### requirements

```
openpyxl
pandas
sqlite-utils
```

optional:
```
datasette
```


### run

Download Your Points xslx file from <https://wandrer.earth/dashboard/stats>, i.e. ``earth-09-12-23.xlsx``
```
python convert.py earth-09-12-23.xlsx
```

View newly created database with datasette:
```
datasette earth-09-12-23.db
```
Browse to <http://localhost:8001>

### Example Queries:

List of all Monthly achievements ordered by points:
```sql
SELECT full_name, name, points, updated FROM champions ORDER BY points DESC
```

Regions near to 25%:
```sql
SELECT pure_name, full_name, completed_in_km, percentage,
distance_to_25_in_km, distance_to_50_in_km, distance_to_75_in_km
FROM points WHERE percentage < 25 ORDER BY distance_to_25_in_km
```

