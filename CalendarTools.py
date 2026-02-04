#Calendar Tools
import pandas as pd
from datetime import datetime, time, timedelta
from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday, nearest_workday, \
    USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay, \
    USLaborDay, USThanksgivingDay

class USTradingCalendar(AbstractHolidayCalendar):
    rules = [
        Holiday('NewYearsDay', month=1, day=1, observance=nearest_workday),
        USMartinLutherKingJr,
        USPresidentsDay,
        GoodFriday,
        USMemorialDay,
        Holiday('USIndependenceDay', month=7, day=4, observance=nearest_workday),
        USLaborDay,
        USThanksgivingDay,
        Holiday('Christmas', month=12, day=25, observance=nearest_workday),
        Holiday('Juneteenth', month=6, day=19, observance=nearest_workday)
    ]

def isTradingHoliday(date):
  holidays = USTradingCalendar().holidays(date.date(), date.date())
  return datetime.combine(date.date(), time(0,0)) in holidays

def tradingDaysToExpiry(expiryDate, startDate=datetime.today()):
  #options expire at 4pm
  expiryDate = datetime.combine(expiryDate.date(), time(16, 0))

  #shift date to start of next day to get number of complete trading days
  completeStartDate = startDate + timedelta(days=1)
  completeStartDate = datetime.combine(completeStartDate.date(), time(0,0))

  date_range = pd.date_range(start=completeStartDate, end=expiryDate, freq='B')

  #remove holidays
  holidays = USTradingCalendar().holidays(startDate.date(), expiryDate.date())
  date_range = date_range[~date_range.isin(holidays)]

  #Calculate the number of business days
  trading_days = float(len(date_range))

  #Add partial trading day at start if not weekend and not holiday
  if datetime.combine(startDate.date(), time(0,0)) not in holidays and startDate.weekday()<5:
    if time(9,30)< startDate.time() < time(16, 0):
      partialDay = datetime.combine(startDate.date(), time(16, 0)) - startDate
      trading_days+=partialDay.seconds/23400
    elif startDate.time() <= time(9, 30):
      trading_days+=1

  return trading_days

def daysToExpiry(expiryDate, startDate=datetime.today()):
  #options expire at 4pm
  expiryDate = datetime.combine(expiryDate.date(), time(16, 0))
  days = (expiryDate - startDate).total_seconds() / (24*3600)
  return days

def timeToExpiry(expiryDate, startDate=datetime.today(), convention = "days"):
  #trading days to expiry but in years
  if convention == "tradingDays":
    return tradingDaysToExpiry(expiryDate, startDate)/252
  else:
    return daysToExpiry(expiryDate, startDate)/365

def getPreviousTradingDay(date):
  previousWeekday = (date - timedelta(days=1))
  while previousWeekday.weekday() > 4 or isTradingHoliday(previousWeekday):
    previousWeekday = previousWeekday - timedelta(days=1)
  return datetime.combine(previousWeekday.date(), time(0,0))