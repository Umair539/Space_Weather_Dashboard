import pandas as pd

def process_solar_wind(mag, plasma):
    
    mag = filter_columns(mag)
    mag = format_column_name(mag)

    mag = set_time_index(mag)
    plasma = set_time_index(plasma)
    
    mag, plasma = match_time_index(mag, plasma)
    
    solar = join_mag_plasma(mag, plasma)
    
    solar = cast_to_float(solar)
    solar = interpolate_missing_data(solar)
    
    solar = add_pressure_column(solar)
    
    return solar

def filter_columns(mag):
    mag = mag[['time_tag', 'bz_gsm', 'bt']]
    return mag

def format_column_name(mag):
    mag = mag.rename(columns={'bz_gsm': 'bz'})
    return mag

def set_time_index(df):
    # new column was made and then assigned as index since assigning directly caused errors
    time_index_series = pd.to_datetime(df['time_tag']) 
    df = df.set_index(time_index_series)
    df = df.drop(columns=['time_tag'])
    df.index.name = 'time_tag'
    return df

def match_time_index(mag, plasma):
    start_time = min(mag.index.min(), plasma.index.min())
    end_time = max(mag.index.max(), plasma.index.max())

    full_range = pd.date_range(start=start_time, end=end_time, freq='min')
    
    mag = mag.reindex(full_range)
    plasma = plasma.reindex(full_range)
    return mag, plasma

def join_mag_plasma(mag, plasma):
    solar = plasma.join(mag, how='outer')
    return solar

def cast_to_float(solar):
    solar = solar.astype('float64')
    return solar

def interpolate_missing_data(solar):
    solar = solar.interpolate(method = 'linear', axis = 0).ffill().bfill()
    return solar

def add_pressure_column(solar):
    proton_mass = 1.6726e-27
    solar['pressure'] = (
        proton_mass *
        solar["density"] * 1e6 *
        solar["speed"] ** 2 * 1e6
        * 1e9 #to convert to nano pascals
        )
    return solar