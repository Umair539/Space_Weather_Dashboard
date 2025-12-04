## Project Requirements As Epics

## Epic 1: Data Extraction

As a Data Engineer,
I want to be able to access real-time space weather data, so that they can be transformed and ready for visualization.

### User Story 1
As a Data Engineer,
I want to be able to extract solar wind magnetometer data from a website, so that it can be transformed and ready for visualization.

### User Story 2
As a Data Engineer,
I want to be able to extract solar wind plasma data from a website, so that it can be transformed and ready for visualization.

### User Story 3
As a Data Engineer,
I want to be able to extract Dst index data from a website, so that it can be transformed and ready for visualization.

### User Story 4
As a Data Engineer,
I want to be able to extract Kp index data from a website, so that it can be transformed and ready for visualization.

### Acceptance Criteria

- [x] Given a valid URL, a connection is established to the website
- [x] Given an established connection, the JSON data must be retrieved without any errors
- [x] Given the JSON data has been retrieved successfully, it must be converted into a Pandas DataFrame
- [x] Successful extractions are logged
- [x] Failed extractions are logged
- [ ] Tests are written to verify extraction process

## Epic 2: Data Transformation

As a Data Engineer,
I want to perform any necessary transformations, including feature selection, engineering, and fixing type formats, so that the extracted data is clean and ready for visualization.

### User Story 5

As a Data Engineer,
I want to combine, enrich and aggregate solar wind data, so that it is ready for visualization

### Acceptance Criteria

- [x] Given magnetometer data, filter for the required columns
- [x] Standardise and match magnetometer and plasma data time indices
- [x] Merge the plasma and magnetometer data
- [x] Ensure all data has been set to the correct data types
- [x] Handle any missing data using interpolation, forward fill and back fill
- [x] Create a new column for solar wind pressure
- [x] Aggregate solar wind to hourly intervals using the hourly mean, standard deviation, and interquartile range
- [x] Tests are written to verify transformation process

### User Story 6

As a Data Engineer,
I want to clean Dst and Kp Index data and handle any missing data, so that it is ready for visualization

### Acceptance Criteria

- [x] Given Kp index data, filter for the required columns
- [x] Ensure all data has been set to the correct data types
- [x] Handle any missing data using interpolation, forward fill and back fill
- [ ] Tests are written to verify transformation process

## Epic 3: Data Storage

As a Data Engineer,
I want to save the raw and transformed data as csv files.

### User Story 7

As a Data Engineer,
I want to save the raw data after extraction so that in the event new data can't be extracted, data from the previous successful extraction can be used instead.

### User Story 8

As a Data Engineer,
I want to save the transformed data so that it is ready to be used for visualizations.

### Acceptance Criteria

- [x] After a successful extraction, save the raw data as csv files before beginning the transformation phase
- [x] Once the transformation phase is completed, save the transformed data as csv files
- [ ] Tests are written to verify load phase

## Epic 4: Data Visualization

As a User,
I want to access a responsive dashboard that displays space weather visualizations, so that I can assess the current state of the near-Earth space environment.

### User Story 9

As a User,
I want to view visualizations of the different solar wind parameters.

### Acceptance Criteria

- [x] Create plots for the different solar wind features
- [x] Include selection ability to allow user to choose features
- [x] Include ability to select time resolution
- [x] Include ability to select aggregation method if hourly resolution is chosen
- [x] Create ability to move the window of currently displayed data
- [x] Add text describing what solar wind is

### User Story 10

As a User,
I want to view visualizations of the different geomagnetic indices.

### Acceptance Criteria

- [x] Create plots for the Kp and Dst indices
- [x] Create ability to move the window of currently displayed data
- [x] Add text describing the Kp and Dst indices

### User Story 11

As a User,
I want to see an overview of the current status of the space weather environment.

### Acceptance Criteria

- [x] Display most recent values for the different solar wind features
- [x] Display most recent values for the Dst and Kp indices