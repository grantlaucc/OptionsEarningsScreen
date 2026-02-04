#yfinance helper tools
import yfinance as yf
import numpy as np

def getYfTicker(ticker):
  return yf.Ticker(ticker)

def getYfHistory(yfTicker, startDate, endDate=None):
  return yfTicker.history(start = startDate, end = endDate)

def getYfOptionChain(yfTicker, expiry):
  callChain, putChain, underlyingInfo = yfTicker.option_chain(expiry.strftime('%Y-%m-%d'))
  return callChain, putChain, underlyingInfo

def getYfImpliedVol(callChain, putChain, underlyingInfo, strike, interpolation = 'linear'):
#returns implied vol for an option with strike price = strike
#Expiry date is specified in the call & put chains.
#TODO Could add moneyness/delta strike.
  spot = underlyingInfo['regularMarketPrice']

  if strike>=spot: #use call chain for OTM calls
    optionChain = callChain
  else: #use put chain for OTM puts
    optionChain = putChain

  if strike in optionChain['strike'].values:
    iv = optionChain[optionChain['strike'] == strike]['impliedVolatility'].values[0]
  else:
    lowerStrike = optionChain.loc[optionChain['strike'] < strike, 'strike'].max()
    upperStrike = optionChain.loc[optionChain['strike'] > strike, 'strike'].min()

    # Linear interpolation
    lowerIV = optionChain.loc[optionChain['strike'] == lowerStrike, 'impliedVolatility'].values[0]
    upperIV = optionChain.loc[optionChain['strike'] == upperStrike, 'impliedVolatility'].values[0]

    iv = np.interp(strike, [lowerStrike, upperStrike], [lowerIV, upperIV])
  return iv