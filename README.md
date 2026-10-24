# Connected Classrooms, Unequal Opportunities

This report/website explores unequal opportunities within Australian Education.

## Running the Website Locally:

Charts load JSON over HTTP, hence serving the folder rather than opening the file directly via:

python -m http.server 8000

then open http://localhost:8000. Rebuild the constructed dataset via (doesn't include manually aggregated data):

pip install pandas openpyxl
python scripts/prepare_data.py

## Data Processing notes

- 9,694 of 9,755 schools in 2025 are mapped; schools missing enrolments or coordinates are dropped.
- School coordinates are locality centroids, so they are approximate.
- Fig 8 aggregates schools into 0.75 degree grid cells; mean ICSEA is weighted by enrolments.
- Fig 10 plots a random sample of up to 120 schools per remoteness class (seed 3179); medians use all schools.
- Fig 9 ranks are computed from the ratio, ties broken alphabetically by state.
- ABS FTE student counts (Fig 7) and ACARA headcounts (Fig 1) differ in definition, so totals are not comparable.

Date the data was accessed: 24 October 2026.
