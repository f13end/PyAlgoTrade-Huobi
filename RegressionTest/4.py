from pyalgotrade import strategy
from pyalgotrade import broker
from pyalgotrade.bar import Frequency
from pyalgotrade.barfeed.csvfeed import GenericBarFeed
from pyalgotrade.technical import ma
from pyalgotrade.technical import cross
from pyalgotrade import plotter
from pyalgotrade.stratanalyzer import returns
from pyalgotrade.bitstamp import common
import math

class floatBroker(broker.backtesting.Broker):
    def getInstrumentTraits(self, instrument):
        return common.BTCTraits()

class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, brk):
        super(MyStrategy, self).__init__(feed, brk)
        self.__position = None
        self.__instrument = instrument
        # We'll use adjusted close values instead of regular close values.
        self.setUseAdjustedValues(True)
        self.__prices = feed[instrument].getPriceDataSeries()
        self.__sma = {}
        self.__sma[60] = ma.SMA(self.__prices, 60)
        self.__sma[10] = ma.SMA(self.__prices, 10)
        self.__sma[30] = ma.SMA(self.__prices, 30)
        self.__mcash=brk.getCash();
        self.__mcoin=0
        self.__mprice = 0
        
        self.__si = 0
        self.__jsl = []

    def getSMA(self, period):
        return self.__sma[period]
    
    def onEnterOk(self, position):
        execInfo = position.getEntryOrder().getExecutionInfo()
        self.info("BUY at $%.2f %.2f %.2f" % (execInfo.getPrice(), execInfo.getQuantity(), self.getBroker().getCash()))

        __tcoin = self.__mcash / execInfo.getPrice() * 0.997
        if __tcoin > execInfo.getQuantity():
            __tcoin = execInfo.getQuantity()
        __tcoin = round(__tcoin, 4)
        self.__mcash -= execInfo.getPrice()*__tcoin/0.998
        self.__mcoin += __tcoin
        self.__mcash = int(self.__mcash)
        if self.__mcash < 0:
            print("buy error! %f"% self.__mcash)
            quit()

    def onEnterCanceled(self, position):
        self.__position = None

    def onExitOk(self, position):
        execInfo = position.getExitOrder().getExecutionInfo()
        self.info("SELL at $%.2f %.2f %.2f" % (execInfo.getPrice(), execInfo.getQuantity(), self.getBroker().getCash()))
        self.__position = None

        __tcoin = execInfo.getQuantity()
        if __tcoin > self.__mcoin:
            __tcoin = self.__mcoin
        self.__mcash += execInfo.getPrice()*__tcoin*0.998
        self.__mcoin -= __tcoin
        self.__mcash = int(self.__mcash)
        if self.__mcoin < 0:
            print("sell error!")
            quit()

    def totalEnd(self):
        print("cash:%f coin:%f total:%f"%(self.__mcash, self.__mcoin, self.__mcash + self.__mcoin*self.__mprice*0.998));

    def onExitCanceled(self, position):
        # If the exit was canceled, re-submit it.
        self.__position.exitMarket()

    def onBars(self, bars):
        self.__si += 1
        # Wait for enough bars to be available to calculate a SMA.
        if self.__sma[30][-1] is None:
            return

        bar = bars[self.__instrument]
        self.__mprice = bar.getPrice()
        # If a position was not opened, check if we should enter a long position.
        if self.__position is None:
            if cross.cross_above(self.__sma[10], self.__sma[30]) > 0:
                self.__jsl.append([self.__si-1])
                mbroker = self.getBroker();
                shares = mbroker.getCash()/bar.getPrice()*0.95;
#                self.__position = self.marketOrder(self.__instrument, self.__shares)
                print("buy%.2f in %.2f use %d"%(shares, bar.getPrice(), mbroker.getCash()))
                self.__position = self.enterLong(self.__instrument, shares, True)
        # Check if we have to exit the position.
#        elif not self.__position.exitActive() and cross.cross_below(self.__prices, self.__sma[10]) > 0:
        elif not self.__position.exitActive() and (self.__position.getReturn() > 0.3 or cross.cross_below(self.__sma[10], self.__sma[30]) > 0):
            self.__position.exitMarket()
            self.__jsl[-1].append(self.__si-1)
            #self.__position.exitMarket()
#        print("PnL:%f ret:%f"%(_p.getPnL(True), _p.getReturn()))
    def getJSL(self):
        return self.__jsl


def run_strategy():
    # Load the yahoo feed from the CSV file
    feed = GenericBarFeed(Frequency.DAY, None, None)
    feed.addBarsFromCSV("orcl", "2000.csv")

    # commission
    broker_commission = broker.backtesting.TradePercentage(0.002)
    broker_brk = floatBroker(500000, feed, broker_commission)
    # Evaluate the strategy with the feed.
    myStrategy = MyStrategy(feed, "orcl", broker_brk)
    
    returnsAnalyzer = returns.Returns()
    myStrategy.attachAnalyzer(returnsAnalyzer)
    

    # Attach the plotter to the strategy.
    plt = plotter.StrategyPlotter(myStrategy)
    # Include the SMA in the instrument's subplot to get it displayed along with the closing prices.
    plt.getInstrumentSubplot("orcl").addDataSeries("SMA60", myStrategy.getSMA(60))
    plt.getInstrumentSubplot("orcl").addDataSeries("SMA10", myStrategy.getSMA(10))
    plt.getInstrumentSubplot("orcl").addDataSeries("SMA30", myStrategy.getSMA(30))
    # Plot the simple returns on each bar.
    plt.getOrCreateSubplot("returns").addDataSeries("Simple returns", returnsAnalyzer.getReturns())
    
    
    myStrategy.run()
    print("Final portfolio value: $%.2f %.2f %.2f" %(myStrategy.getBroker().getEquity(), myStrategy.getBroker().getCash(), myStrategy.getBroker().getShares('orcl')))
    myStrategy.totalEnd()
#    myStrategy.info("Final portfolio value: $%.2f" % myStrategy.getResult())

    # Plot the strategy.
    plt.plot()
    print(myStrategy.getJSL())

run_strategy()















