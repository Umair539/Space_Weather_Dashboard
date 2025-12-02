import pandas as pd

def aggregate_solar_wind(solar):
    
    solar_agg = resample(solar)
    
    solar_agg = join_columns(solar_agg)
    
    return solar_agg

def resample(solar):
    solar_agg = solar.resample('h').agg(['mean', 'std', iqr])
    return solar_agg

def join_columns(solar_agg):
    solar_agg.columns = ["_".join(col) for col in solar_agg]
    return solar_agg

def iqr(series):
    return series.quantile(0.75) - series.quantile(0.25)