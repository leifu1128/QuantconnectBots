class DHedge(QCAlgorithm):

    def Initialize(self):
        #Initialize Backtest Settings
        self.SetStartDate(2019, 1, 1)  
        self.SetEndDate(2021, 5, 1)
        self.SetCash(1000000)  
        self.SetBenchmark("SPY")
        
        #Initialize Variables
        self.hedgeRatio = 5
        self.posInitFlag = 0
        self.callExp = 0
        self.expLowerBound = timedelta(10)
        self.expUpperBound = timedelta(35)
        
        #Add Equities
        self.spy = self.AddEquity("SPY", Resolution.Minute)
        self.hyg = self.AddEquity("HYG", Resolution.Minute)
        self.spy.SetDataNormalizationMode(DataNormalizationMode.Raw)
        self.hyg.SetDataNormalizationMode(DataNormalizationMode.Raw)
        self.spySymbol = self.spy.Symbol
        self.hygSymbol = self.hyg.Symbol
        option = self.AddOption("SPY")
        option.PriceModel = OptionPriceModels.CrankNicolsonFD()
        option.SetFilter(-2, 2, self.expLowerBound, self.expUpperBound)


    def OnData(self, slice):
        if self.IsWarmingUp: return
    
        if(self.posInitFlag == 1):
            hedgeAMNT = (self.call.Greeks.Delta * 100 * self.posSize * self.spy.Price)
            hedgePCNT = (hedgeAMNT / self.Portfolio.Cash)
            self.SetHoldings(self.spySymbol, hedgePCNT)
            
        if(self.posInitFlag == 1) & (self.callExp == self.Time): self.Liquidate()
        
        for x in self.Portfolio:
            if x.Value.Invested and x.Value.Type == SecurityType.Option:
                return
        
        for kvp in slice.OptionChains:
            chain = kvp.Value   
            spyPrice = chain.Underlying.Price
            
            #Find ATM Call
            sorted_contracts = sorted(chain, key = lambda x: x.Strike, reverse = False)
            calls = [i for i in sorted_contracts if i.Right == OptionRight.Call and i.Strike >= spyPrice]
            if (not calls): return
            self.call = calls[0] 
            
        self.posInitFlag = 1
        callPrice = self.call.BidPrice * 100
        self.callExp = self.call.Expiry
        total = round(callPrice + (self.spy.Price * 100))
        self.posSize = round(self.Portfolio.Cash  / total) - 1
        self.MarketOrder(self.call.Symbol, -self.posSize)
        
        
        return
    
    def HourMinuteIs(self, hour, minute):
        return self.Time.hour == hour and self.Time.minute == minute