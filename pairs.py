from binance.um_futures import UMFutures
from binance.error import ClientError
import time
import logging
from binance.lib.utils import config_logging
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
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


class pair:
	def __init__(self,tickers,client):
		print("Initiation Started For :",tickers)
		self.client = client
		self.y = tickers[0]
		self.x1 = tickers[1]
		self.x2 = tickers[2]
		self.lookback = int(tickers[3])
		self.data_y = []
		self.data_x1 = []
		self.data_x2 = []
		self.data = []
		self.prices = {}
		self.positions = {"Y":0,"X1":0,"X2":0}
		self.se = 0
		self.beta = 0
		self.get_data()
		self.money = 150
		self.leverage = 30
		self.model = self.get_model(self.data)
		self.threshold = int(tickers[4])
		self.ws = UMFuturesWebsocketClient()
		self.direction = ""
		self.subscribe_to_ws()

	def buy(self,symbol,qty,leverage):
		symbol = symbol.upper()
		i = 2
		qty = round(qty,i)
		while True:
			try:
				response = self.client.new_order(
					symbol = symbol,
					side = "BUY",
					type = "MARKET",
					quantity = qty,
					leverage = leverage)
				break
			except Exception as e:
				if i > 0:
					i = i-1
					qty = round(qty,i)
				else:
					print(e)
					return -1
		return qty

	def sell(self,symbol,qty,leverage):
		symbol = symbol.upper()
		i = 2
		qty = round(qty,i)
		while True:
			print(qty)
			try:
				response = self.client.new_order(
					symbol = symbol,
					side = "SELL",
					type = "MARKET",
					quantity = qty,
					leverage = leverage)
				break
			except Exception as e:
				if i > 0:
					i = i-1
					qty = round(qty,i)
				else:
					print(e)
					return -1
		return qty

	def message_handler_y(self,message):
		if message.get('k') != None:
			if message['k']['x'] == True:
				# print("Data Recieved For:",self.y)
				self.prices["y"] = float(message['k']['c'])
				self.strategy()

	def message_handler_x1(self,message):
		# print("Data Recieved For:",self.x1)
		if message.get('k') != None:
			if message['k']['x'] == True:
				# print("Data Recieved For:",self.x1)
				self.prices["x1"] = float(message['k']['c'])
				self.strategy()
		
	def message_handler_x2(self,message):
		# print("Data Recieved For:",self.x2)
		if message.get('k') != None:
			if message['k']['x'] == True:
				# print("Data Recieved For:",self.x2)
				self.prices["x2"] = float(message['k']['c'])
				self.strategy()

	def subscribe_to_ws(self):
		self.ws.start()
		self.ws.continuous_kline(
			pair = self.y,
			id = 1,
			contractType = "perpetual",
			interval = "1m",
			callback = self.message_handler_y)
		self.ws.continuous_kline(
			pair = self.x1,
			id = 1,
			contractType = "perpetual",
			interval = "1m",
			callback = self.message_handler_x1)
		self.ws.continuous_kline(
			pair = self.x2,
			id = 1,
			contractType = "perpetual",
			interval = "1m",
			callback = self.message_handler_x2)

	def get_model(self,d):
		try:
			y = d["Y"]
			x = d[["X1","X2"]]
			mlr = LinearRegression()
			mlr.fit(x,y)
			y_pred = mlr.predict(x)
			res = (y-y_pred)**2
			self.se = res.mean()**0.5
			self.beta = dict(zip(["X1","X2"],mlr.coef_))
			# print(self.beta)
			# print(self.beta)
			return mlr
		except Exception as e:
			print("Cant generate model")
			print(e)

	def prepare_data(self,symbol):
		data = pd.DataFrame(self.client.klines(symbol,interval = "1h",limit = 800))
		data = data.iloc[:,:6]
		data.columns = ["Time","O","H","L","C","Volume"]
		return data

	def get_data(self):
		self.data_y = self.prepare_data(self.y)
		self.data_x1 = self.prepare_data(self.x1)
		self.data_x2 = self.prepare_data(self.x2)
		self.data = pd.DataFrame()
		self.data["Y"] = self.data_y["C"]
		self.data["X1"] = self.data_x1["C"]
		self.data["X2"] = self.data_x2["C"]
		self.data["Y"] = self.data["Y"].astype(float)
		self.data["X1"] = self.data["X1"].astype(float)
		self.data["X2"] = self.data["X2"].astype(float)
		# print(self.data)


	def strategy(self):
		if len(self.prices) < 3:
			return
		else:
			ub = self.threshold
			lb = - self.threshold
			s_ub = ub/2
			s_lb = lb/2

			if self.model!=None:
				y = self.prices["y"]
				x1 = self.prices["x1"]
				x2 = self.prices["x2"]
				x = pd.DataFrame([[x1,x2]],columns = ["X1","X2"])
				ypred = self.model.predict(x[["X1","X2"]])
				trig = (y - ypred)/self.se
				res = trig[0]
				# print(y,x1,x2,"Z-score : ",res,"Beta : ",self.beta)
				# if abs(res) >self.threshold:
				print(self.y,self.x1,self.x2,"Z-score : ",res,"Beta : ",self.beta)
				posy,posx1,posx2 = self.positions["Y"],self.positions["X1"],self.positions["X2"]
				if posy==0 and posx1==0 and posx2==0:
					if res >= ub:
						print('SHORT')
						self.direction = "S"
						# ratio = 1/(y + x1 + x2)
						# qtyY = y*ratio*self.money
						# qtyX1 = x1*ratio*self.money
						# qtyX2 = x2*ratio*self.money
						qtyY = (self.money/3)/y
						qtyX1 = (self.money/3)/x1
						qtyX2 = (self.money/3)/x2

						quantity = self.sell(self.y,qtyY,self.leverage)
						if quantity == -1:
							return
						self.positions["Y"] = -quantity
						
						quantity = self.buy(self.x1,qtyX1,self.leverage)
						if quantity == -1:
							return
						self.positions["X1"] = quantity
						# else:
						# 	quantity = self.sell(self.x1,qtyX1,self.leverage)
						# 	self.positions["X1"] = -quantity
						# if self.beta["X2"] > 0:
						
						quantity = self.buy(self.x2,qtyX2,self.leverage)
						if quantity == -1:
							return
						self.positions["X2"] = quantity
						# else:
						# 	quantity = self.sell(self.x2,qtyX2,self.leverage)
						# 	self.positions["X2"] = -quantity
					if res <= lb:
						print('LONG')
						self.direction = "L"
						# ratio = 1/(y + x1 + x2)
						# qtyY = y*ratio*self.money
						# qtyX1 = x1*ratio*self.money
						# qtyX2 = x2*ratio*self.money

						qtyY = (self.money/3)/y
						qtyX1 = (self.money/3)/x1
						qtyX2 = (self.money/3)/x2
						
						quantity = self.buy(self.y,qtyY,self.leverage)
						if quantity == -1:
							return
						self.positions["Y"] = quantity
						
						quantity = self.sell(self.x1,qtyX1,self.leverage)
						if quantity == -1:
							return
						self.positions["X1"] = -quantity
						# else:
						# 	quantity = self.sell(self.x1,qtyX1,self.leverage)
						# 	self.positions["X1"] = -quantity
						# if self.beta["X2"] > 0:
						
						quantity = self.sell(self.x2,qtyX2,self.leverage)
						if quantity == -1:
							return
						self.positions["X2"] = -quantity
				else:
					if res <= s_ub and self.direction == "S":
						print("SQUARE OFF SHORT")
						self.direction = ""
						if posy < 0:
							self.buy(self.y,-posy,self.leverage)
							self.positions["Y"] = 0
						if posx1>0:
							self.sell(self.x1,posx1,self.leverage)
							self.positions["X1"] = 0
						if posx2>0:
							self.sell(self.x2,posx2,self.leverage)
							self.positions["X2"] = 0

					elif res>=s_lb and self.direction == "L":
						print("SQUARE OFF LONG")
						self.direction = ""
						if posy > 0:
							self.sell(self.y,posy,self.leverage)
							self.positions["Y"] = 0
						if posx1<0:
							self.buy(self.x1,-posx1,self.leverage)
							self.positions["X1"] = 0
						if posx2<0:
							self.buy(self.x2,-posx2,self.leverage)
							self.positions["X2"] = 0
			self.get_data()
			self.get_model(self.data)
			self.prices = {}
			return

def initialize(tickers,client):
	p = pair(tickers,client)