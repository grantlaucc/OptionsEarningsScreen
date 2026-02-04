#financial tools
import numpy as np

def getLogReturns(priceSeries):
  return priceSeries.pct_change().apply(lambda x: np.log(1 + x))

def getHistoricalVolatility(priceSeries, days = 30):
    if days>=len(priceSeries):
      print("Insufficient days in priceDF")
      return None
    logReturns = getLogReturns(priceSeries)
    hVol = logReturns.rolling(days).std()*np.sqrt(252)
    #sigma = priceDF['LogReturns'][-days:].std()*np.sqrt(252)
    return hVol