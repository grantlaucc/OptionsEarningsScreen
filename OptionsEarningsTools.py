import numpy as np
import pandas as pd
from datetime import datetime, time, timedelta
import yfinance as yf
import yfinanceHelper as yfh
import CalendarTools as ct
import FinanceTools as ft
import FinanceScrapers as fs

def getSigmaForward(sigma_1, sigma_2, t_1, t_2):
  dt = t_2 - t_1
  var_forward = sigma_2**2 * t_2 - sigma_1**2 * t_1
  # Clip negative variance (significantly inverted IV term structure)
  if var_forward < 0:
    var_forward = 0.0
  sigma_forward = np.sqrt(var_forward / dt)
  return sigma_forward

def getExpectedDailyMove(yfTicker, nextEarningsDate, startDate = datetime.today()):
  #https://www.trading-volatility.com/Trading-Volatility.pdf - Chapter 6.4
  #Note T is in trading days not years here
  expiries = tuple(datetime.strptime(date_str, "%Y-%m-%d") for date_str in yfTicker.options)
  expiries = tuple(datetime.combine(expiry.date(), time(16,0)) for expiry in expiries)
  expiryIndex_T1 = min(range(len(expiries)), key=lambda i: (expiries[i] < nextEarningsDate, abs(expiries[i] - nextEarningsDate)))
  expiry_T1 = expiries[expiryIndex_T1]

  callChain_T1, putChain_T1, underlyingInfo_T1 = yfh.getYfOptionChain(yfTicker, expiry_T1)
  sigma_T1 = yfh.getYfImpliedVol(callChain_T1, putChain_T1, underlyingInfo_T1, underlyingInfo_T1['regularMarketPrice'])
  T1 = ct.tradingDaysToExpiry(expiryDate = expiry_T1, startDate = startDate) #TODO calculate time in days between today and expiry_jump

  if expiryIndex_T1 > 0: #expiry exists before earnings, use T0 to calculate sigma_diffusive
    expiryIndex_T0 = expiryIndex_T1 - 1
    expiry_T0 = expiries[expiryIndex_T0]
    callChain_T0, putChain_T0, underlyingInfo_T0 = yfh.getYfOptionChain(yfTicker, expiry_T0)
    sigma_diffusive = yfh.getYfImpliedVol(callChain_T0, putChain_T0, underlyingInfo_T0, underlyingInfo_T0['regularMarketPrice'])
  else: #Earnings expiry is closest expiry, use T2 and forward implied vol to calculate sigma_diffusive
    expiryIndex_T2 = expiryIndex_T1+1
    expiry_T2 = expiries[expiryIndex_T2]
    callChain_T2, putChain_T2, underlyingInfo_T2 = yfh.getYfOptionChain(yfTicker, expiry_T2)
    sigma_T2 = yfh.getYfImpliedVol(callChain_T2, putChain_T2, underlyingInfo_T2, underlyingInfo_T2['regularMarketPrice'])
    T2 = ct.tradingDaysToExpiry(expiryDate = expiry_T2, startDate = startDate)
    sigma_diffusive = getSigmaForward(sigma_T1, sigma_T2, T1, T2)
  sigma_jump = np.sqrt(sigma_T1**2*T1-sigma_diffusive**2*(T1-1))
  expectedDailyMove = sigma_jump/np.sqrt(252) * np.sqrt(2/np.pi)
  #TODO normalize for (subtract) index term structure
  return expectedDailyMove

def getSigma_T1(yfTicker, nextEarningsDate, startDate = datetime.today()):
  #https://www.trading-volatility.com/Trading-Volatility.pdf - Chapter 6.4
  #Note T is in trading days not years here
  expiries = tuple(datetime.strptime(date_str, "%Y-%m-%d") for date_str in yfTicker.options)
  expiries = tuple(datetime.combine(expiry.date(), time(16,0)) for expiry in expiries)
  expiryIndex_T1 = min(range(len(expiries)), key=lambda i: (expiries[i] < nextEarningsDate, abs(expiries[i] - nextEarningsDate)))
  expiry_T1 = expiries[expiryIndex_T1]

  callChain_T1, putChain_T1, underlyingInfo_T1 = yfh.getYfOptionChain(yfTicker, expiry_T1)
  sigma_T1 = yfh.getYfImpliedVol(callChain_T1, putChain_T1, underlyingInfo_T1, underlyingInfo_T1['regularMarketPrice'])
  return sigma_T1

def getEarningsTable(yfTicker, earningsTime = 'PM'):
  yfEarningsDates = yfTicker.earnings_dates
  #Get at least 8 previous quarters of earnings if possible
  if yfEarningsDates['Reported EPS'].count()<8:
    rowsNeeded = len(yfEarningsDates)+8-yfEarningsDates['Reported EPS'].count()
    yfEarningsDates = yfTicker.get_earnings_dates(limit = rowsNeeded)

  yfEarningsDates = yfEarningsDates.tz_localize(None)
  if earningsTime == 'AM':
    yfEarningsDates.index = yfEarningsDates.index.map(lambda x: x.replace(hour=9, minute=0, second=0, microsecond=0))
  else:
    yfEarningsDates.index = yfEarningsDates.index.map(lambda x: x.replace(hour=17, minute=0, second=0, microsecond=0))
  firstEarningsDate = yfEarningsDates.index[-1]
  yfHistory = yfh.getYfHistory(yfTicker, ct.getPreviousTradingDay(firstEarningsDate))
  spx_yfHistory = yfh.getYfHistory(yfh.getYfTicker('^SPX'), ct.getPreviousTradingDay(firstEarningsDate))
  if earningsTime == "AM":
    subsequentLogReturns = ft.getLogReturns(yfHistory['Close']).shift(0)
    spx_subsequentLogReturns = ft.getLogReturns(spx_yfHistory['Close']).shift(0)
  else: #earningsTime == 'PM'
    subsequentLogReturns = ft.getLogReturns(yfHistory['Close']).shift(-1) #-1
    spx_subsequentLogReturns = ft.getLogReturns(spx_yfHistory['Close']).shift(-1)
  oneDayMoves = pd.merge(yfEarningsDates, subsequentLogReturns, left_on=yfEarningsDates.index.date, right_on=subsequentLogReturns.index.date, how = 'left')['Close']
  spx_oneDayMoves = pd.merge(yfEarningsDates, spx_subsequentLogReturns, left_on=yfEarningsDates.index.date, right_on=spx_subsequentLogReturns.index.date, how = 'left')['Close']
  yfEarningsDates['1D Move'] = oneDayMoves.values
  yfEarningsDates['SPX 1D Move'] = spx_oneDayMoves.values
  return yfEarningsDates

def getEarningsScreen(ticker, earningsTime = 'PM', displayEarningsTable = False):
  yfTicker = yfh.getYfTicker(ticker)
  earningsTable = getEarningsTable(yfTicker, earningsTime = earningsTime)
  avgAbs1DMove = earningsTable['1D Move'].abs().mean()
  positive1DMoves = (earningsTable['1D Move']>0).sum()
  reportedQuarters = earningsTable['Reported EPS'].count()
  today = datetime.today()
  nextEarningsIndex = min(range(len(earningsTable.index)), key=lambda i: (earningsTable.index[i].date() < today.date(), abs(earningsTable.index[i] - today)))
  nextEarningsDate = earningsTable.index[nextEarningsIndex]
  implied1DMove = getExpectedDailyMove(yfTicker, nextEarningsDate)
  priceSeries = yfTicker.history(period = '1y')['Close']
  hvol30 = ft.getHistoricalVolatility(priceSeries, days = 30).iloc[-1]
  atmVol = getSigma_T1(yfTicker, nextEarningsDate)
  data = {
      'Symbol': [yfTicker.info['symbol']],
      'CurrentPrice': [yfTicker.info['currentPrice']],
      'EarningsDate': [nextEarningsDate.date()],
      'EarningsTime': [earningsTime],
      'AvgAbs1DMove': [avgAbs1DMove],
      'Implied1DMove': [implied1DMove],
      'Positive1DMoves': [positive1DMoves],
      'ReportedQuarters': [reportedQuarters],
      'HVOL_30D': [hvol30],
      'ATM_VOL' : [atmVol],
  }
  earningsScreenDF = pd.DataFrame(data)
  if displayEarningsTable:
    display(earningsTable)
  return earningsScreenDF

def getUpcomingEarnings(startDate, endDate, minMarketCap = None, universe = None):
  earningsCal = fs.scrapeEarningsCalendar(startDate, endDate, minMarketCap)
  if universe != None:
    indexDF = fs.scrapeIndex(universe)
    earningsCal = pd.merge(earningsCal, indexDF, left_on='symbol', right_on='Ticker', how='inner')
  earningsScreens = []
  for index, row in earningsCal.iterrows():
    earningsTime = "AM" if row['time'] == 'time-pre-market' else "PM"
    earningsScreens.append(getEarningsScreen(row['symbol'], earningsTime))
  upcomingEarnings = pd.concat(earningsScreens, ignore_index=True)
  return upcomingEarnings

if __name__ == "__main__":
    # Provide the desired arguments to the function
    stock_symbol = 'GME'
    earnings_time = 'PM'
    display_earnings_table = False

    # Call the function with the specified arguments
    getEarningsScreen(stock_symbol, earningsTime=earnings_time, displayEarningsTable=display_earnings_table)