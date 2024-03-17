#Finance Scraper Tools
import pandas as pd
import requests

def scrapeIndex(indexTicker):
  indexUrlTableDict = {
    '^RUI': ['https://en.wikipedia.org/wiki/Russell_1000_Index',2],
    '^SPX': ['https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',0],
    '^NDX': ['https://en.wikipedia.org/wiki/NASDAQ-100',4],
  }
  componentsDF = pd.read_html(indexUrlTableDict[indexTicker][0])[indexUrlTableDict[indexTicker][1]]
  if indexTicker == '^SPX':
    componentsDF = componentsDF.rename(columns={'Symbol':'Ticker', 'Security':'Company'})
    componentsDF = componentsDF.filter(items=['Company', 'Ticker', 'GICS Sector', 'GICS Sub-Industry'])
  return componentsDF

def scrapeEarningsCalendar(startDate, endDate = None, minMarketCap = None):
  #note mixing past earnings and future earnings will cause this to break.
  if endDate == None:
    endDate = startDate

  headers = {
    "Accept":"application/json, text/plain, */*",
    "Accept-Encoding":"gzip, deflate, br",
    "Accept-Language":"en-US,en;q=0.9",
    "Origin":"https://www.nasdaq.com",
    "Referer":"https://www.nasdaq.com",
    "User-Agent":"your user agent..."
  }
  url = 'https://api.nasdaq.com/api/calendar/earnings?'

  earningsCalendarDF = pd.DataFrame()
  for date in pd.date_range(startDate, endDate):
    payload = {"date":date.strftime('%Y-%m-%d')}
    source = requests.get( url=url, headers=headers, params=payload, verify=True )
    data = source.json()
    #skip days with no data
    if data['data']['rows'] == None:
      continue
    df = pd.DataFrame(data['data']['rows'])
    df['earningsDate'] = date
    earningsCalendarDF = pd.concat([earningsCalendarDF, df], ignore_index=True)

  earningsCalendarDF['marketCap'] = pd.to_numeric(earningsCalendarDF['marketCap'].str.replace('[\$,]', '', regex=True), errors='coerce')
  earningsCalendarDF['lastYearEPS'] = pd.to_numeric(earningsCalendarDF['lastYearEPS'].str.replace('[\$,]', '', regex=True), errors='coerce')
  earningsCalendarDF['epsForecast'] = pd.to_numeric(earningsCalendarDF['epsForecast'].str.replace('[\$,]', '', regex=True), errors='coerce')
  earningsCalendarDF['noOfEsts'] = pd.to_numeric(earningsCalendarDF['noOfEsts'], errors='coerce')
  if minMarketCap != None:
    earningsCalendarDF = earningsCalendarDF[earningsCalendarDF['marketCap']>= minMarketCap].reset_index(drop=True)
  return earningsCalendarDF