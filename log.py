import csv

class FoodLogger:
    def __init__(self):
        self.transaction_value = []
        self.round_number = []
        self.agent_type = []
    
    def LogFoodTransaction(self, round_number, transaction_value, agent_land, microround_number):
        self.round_number.append(round_number+microround_number)
        self.transaction_value.append(transaction_value)
        if agent_land < 1:
            self.agent_type.append('blue')
        else:
            self.agent_type.append('red')
    
    def CalculateAverageTransactionPriceWithinDaysToYield(self, days_to_yield):
        aggregate_transactions = []
        for i in reversed(self.round_number):
            if i%days_to_yield == 0:
                break
            aggregate_transactions.append(self.transaction_value[i])
        return sum(aggregate_transactions)/len(aggregate_transactions)
        
    
    def CalculateLatestAverageTransactionPrice(self):
        last_round = self.round_number[-1]
        index = 1
        for i in reversed(self.round_number):
            if i < last_round:
                break
            index = index + 1
        last_round_transactions = self.transaction_value[-index:]
        return sum(last_round_transactions)/len(last_round_transactions)
        # send real food price to other models


class LaborLogger:
    def __init__(self):
        self.transaction_value = []
        self.round_number = []
        self.agent_type = []
        self.labor_force = []
    
    def LogLaborTransaction(self, round_number, transaction_value, agent_type):
        self.round_number.append(round_number)
        self.transaction_value.append(transaction_value)
        if agent_type > 0:
            self.agent_type.append('red')
        else:
            self.agent_type.append('blue')

class LandLogger:
    def __init__(self):
        self.transaction_value = []
        self.round_number = []
        self.agent_type = []
    
    def LogLandTransaction(self, round_number, transaction_value, agent_type):
        self.round_number.append(round_number)
        self.transaction_value.append(transaction_value)
        if agent_type > 0:
            self.agent_type.append('red')
        else:
            self.agent_type.append('blue')
