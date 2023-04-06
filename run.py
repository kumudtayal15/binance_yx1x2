import yfinance as yf
import pandas as pd
import statsmodels.api as sm
import datetime as dt
import os
from statsmodels.tsa.stattools import adfuller
from sklearn.metrics import mean_squared_error
import statsmodels.tsa.stattools as ts
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from ib_insync import *
import time
import csv
import pytz

from binance.um_futures import UMFutures
from binance.error import ClientError
import time
import logging
from binance.lib.utils import config_logging
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
import pandas as pd
import multiprocessing as mp
import pairs

class account:
	def __init__(self):
		self.key = "gCZ7vdcFjuojyjGzK9kxoVgOBGlrSFut2rozg4UGgQHNbH8uzOtkzEZ2I0pB2AML"
		self.secret = "HrdJniqp41Y7X1CdYpesmyOJ3Na76uswFrMudvCMeBeZXV5BCzlcnHjlsFPrADO4"
	def initialize(self):
		um_futures_client = UMFutures(key = self.key,secret = self.secret)
		return um_futures_client

if __name__ == "__main__":
	acc = account()
	client = acc.initialize()
	print("Account Created")
	tickers = pd.read_csv("tickers.csv")
	tickers = tickers.values.tolist()
	for t in tickers:
		print(t)
		p = mp.Process(target = pairs.initialize,args = (t,client,))
		p.start()
