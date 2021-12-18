class SStrangle(QCAlgorithm):

    def Initialize(self):
        #Initialize Stock Selection 
        self.reGenTime = datetime.min # helper variable to regenerate stock list/universe 
        self.AddUniverse(self.CoarseFilter)
        self.UniverseSettings.Resolution = Resolution.Daily
        self.UniverseSettings.DataNormalizationMode=DataNormalizationMode.Raw
        self.activeSet = set()
        
        #Initialize Backtest Settings
        self.SetStartDate(2019, 1, 1)  # set Start Date
        self.SetCash(1000000)  # set Strategy Cash
        self.SetBenchmark("SPY")
        
        #Initialize Algo Params
        self.numSymbols = 5
        self.maxExp = 29
        self.devMult = 5
        self.devRes = Resolution.Daily
        self.devLookBack = 30
        
        
    def CoarseFilter(self, coarse):
        if self.Time <= self.reGenTime: 
            return self.Universe.Unchanged # return if not time to regenerate
        
        self.Liquidate()
        self.Log("Liquidating")
        self.rebalanceTime = self.Time + timedelta(30)
        sortedByDollarVolume = sorted(coarse, key=lambda x: x.DollarVolume, reverse=True)
       
        return [x.Symbol for x in sortedByDollarVolume[:self.numSymbols]]
        
        
    def OnSecuritiesChanged(self, changes):
        for x in changes.RemovedSecurities:
            self.Log(self.activeSet)
            if str(x.Symbol) not in self.activeSet: continue
            self.activeSet.remove(x.Symbol)
            if x.Symbol.SecurityType != SecurityType.Equity: continue
                
            for symbol in self.Securities.Keys:
                    if symbol.SecurityType == SecurityType.Option and symbol.Underlying == x.Symbol:
                        self.RemoveSecurity(symbol)
            
        for x in changes.AddedSecurities:
            self.activeSet.add(x.Symbol)
            if x.Symbol.SecurityType != SecurityType.Equity: continue
            option = self.AddOption(x.Symbol.Value, Resolution.Minute)
            dev = self.STD(x.Symbol.Value, self.devLookBack, self.devRes)
            dev = round(dev.Current.Value)
            option.SetFilter(-dev, +dev, timedelta(0), timedelta(self.maxExp))   
            
        return
            
    
    '''
    def OnOrderEvent(self, orderEvent):
        order = self.Transactions.GetOrderById(orderEvent.OrderId)
        
        #Liquidate on Assigment
        if order.Type == OrderType.OptionExercise:
            if orderEvent.IsAssignment:
                for x in self.option_invested:
                    orderSym = re.findall(r'([^\s]+)', orderEvent.Symbol)
                    if ((x.UnderlyingSymbol == orderSym) & (x.Symbol.Value != orderEvent.Symbol)):
                        self.MarketOrder(x.Symbol, -(orderEvent.Quantity))
        
        return
    '''
        
    def OnData(self, slice):
        if self.IsWarmingUp: 
            return
        
        
        #Enter Positions if None
        if not self.Portfolio.Invested:
            self.option_invested =[]
            
            for kvp in slice.OptionChains:
                chain = kvp.Value
                sortedContracts = sorted(chain, key = lambda x: x.Expiry, reverse = True)
                if not sortedContracts: return
            
                #Select Lowest Strik Call
                calls = [i for i in sortedContracts if i.Right == OptionRight.Call]
                self.call = calls[0] if calls else None
            
                #Select Highest Strike Put
                puts = [i for i in sortedContracts if i.Right == OptionRight.Put]
                self.put = puts[-1] if puts else None
                
                if (not self.call) or (not self.put): continue
                
                self.option_invested.append(self.call)
                self.option_invested.append(self.put)
                self.MarketOrder(self.call.Symbol, -10)
                self.MarketOrder(self.put.Symbol, -10)

            
        #Delta Hedge Positions
        if self.Portfolio.Invested and self.HourMinuteIs(10, 1):
            for stock in self.activeSet:
                netDelta = 0
                for x in self.option_invested:
                    if stock == x.UnderlyingSymbol:
                        netDelta = netDelta + (x.Greeks.Delta * 100)
                    
                self.SetHoldings(stock, netDelta)        
            
            
    def HourMinuteIs(self, hour, minute):
        return self.Time.hour == hour and self.Time.minute == minute
    