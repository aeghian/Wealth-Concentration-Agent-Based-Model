import sympy as sym
import random
import csv
import pandas as pd
import math
import statistics
import time

class GeneralInputRelationship:
    def __init__(self, parameters):
        for i in parameters:
            setattr(self, i, parameters[i])

    def SolveRelationship(self, x, y):
        return self.output_multiplier * x**self.beta * y**self.alpha

    def FindProductionDifferential(self, y, current_input_amount=0):
        x = sym.Symbol('x')
        return sym.diff(self.output_multiplier * (x+current_input_amount)**self.beta * y**self.alpha)
    
    def SolveForOptimalResult(self, differential, cost_in_output):
        x = sym.Symbol('x')
        optimal_result = sym.solve(sym.Eq(differential, cost_in_output), x)[0]
        return optimal_result

class CobbDouglasFunction(GeneralInputRelationship):
    def __init__(self, production, variance_controls):
        GeneralInputRelationship.__init__(self, production)
        self.yield_variance = [variance_controls.default_lowerbound, variance_controls.default_upperbound]
    
    def ProduceOutput(self, labor, capital, industry_switch_penalty_output_multiplier):
        output = round((self.output_multiplier * labor**self.beta * capital**self.alpha) * random.uniform(self.yield_variance[0], self.yield_variance[1]))
        output *= industry_switch_penalty_output_multiplier
        return output 
    
    def SolveOptimalWorkForce(self, differential, worker_cost_in_output):
        return self.SolveForOptimalResult(differential, worker_cost_in_output)
    
    def SolveLaborUnitsForSetProductionAmount(self, production_amount, capital):
        return math.trunc((production_amount/(self.output_multiplier*capital**self.alpha))**(1/self.beta))+1
    
    def SolveProduction(self, labor, capital, industry_switch_penalty_output_multiplier=1):
        output = self.SolveRelationship(labor, capital)
        output *= industry_switch_penalty_output_multiplier
        return output
    

class DepreciationFunction:
    def __init__(self, depreciation):
        for i in depreciation:
            setattr(self, i, depreciation[i])
    
    def SolveDepreciationAmount(self, labor, land):
        return ((labor*land)**self.active_depreciation_exp)*self.active_depreciation_adjuster + 1/self.idle_depreciation_max_cycles


class DeathProbabilityFunction:
    def __init__(self, death):
        for i in death:
            setattr(self, i, death[i])
    
    def SolveDeathProbability(self, age, genetic_multiplier):
        death_probability = self.m * (age-self.x_intercept)**self.exp * genetic_multiplier
        return death_probability

    def EstimatedDeathAge(self, death_probability_threshold, genetic_multiplier):
        estimated_death_age = (death_probability_threshold / (self.m*genetic_multiplier)) ** (1/self.exp) + self.x_intercept
        return estimated_death_age

class AgeBounds:
    def __init__(self, age_bounds):
        for i in age_bounds:
            setattr(self, i, age_bounds[i])

class VarianceControls:
    def __init__(self, variance_controls):
        for i in variance_controls:
            setattr(self, i, variance_controls[i])

class DailyFoodConsumption:
    def __init__(self, food_consumption):
        for i in food_consumption:
            setattr(self, i, food_consumption[i])

class StartParameters:
    def __init__(self, start_params):
        for i in start_params:
            setattr(self, i, start_params[i])
        self.working_agents_start = self.adults_start - self.landowner_start
        self.nonfarm_agents_start = self.adults_start - (self.landowner_start*self.landowner_farm_bias)

class AssetPrices:
    def __init__(self):
        self.food = 0
        self.labor_unit_farm = 0.5
        self.labor_unit_factory = 0.5
        self.land = 0
        self.food_history = []
        self.labor_unit_farm_history = []
        self.labor_unit_factory_history = []
        self.land_history = []
        self.machine = 10
        self.machine_history = []
        self.epoch = time.time()
    
    def RecordInCSV(self, transaction_prices, good, current_round):
        row = [current_round, transaction_prices, getattr(self, good)]
        file_action = 'a'
        if current_round < 0:
            file_action = 'w'
        with open(f'logging_info/{good}_prices_{self.epoch}.csv', file_action) as price_file:
            writer = csv.writer(price_file)
            writer.writerow(row)


    def SetFoodPrice(self, food_transaction_prices, current_round, days_to_yield):
        if len(food_transaction_prices) > 0:
            self.food  = statistics.median(food_transaction_prices)
            if len(self.food_history) >= 300:
                del self.food_history[0]
            self.food_history.append(self.food)
            self.RecordInCSV(food_transaction_prices, 'food', current_round)
        

    def SetFactoryLaborUnitPrice(self, current_round, employee_rates):
        employed_adult_rates = list(filter(lambda i: i != -1, employee_rates))
        if len(employed_adult_rates) > 0:
            self.labor_unit_factory = statistics.median(employed_adult_rates)
            if len(self.labor_unit_factory_history) >= 300:
                del self.labor_unit_factory_history[0]
            self.labor_unit_factory_history.append(self.labor_unit_factory)
            self.RecordInCSV(employed_adult_rates, 'labor_unit_factory', current_round)

    def SetFarmLaborUnitPrice(self, current_round, employee_rates):
        employed_adult_rates = list(filter(lambda i: i != -1, employee_rates))
        if len(employed_adult_rates) > 0:
            self.labor_unit_farm = statistics.median(employed_adult_rates)
            if len(self.labor_unit_farm_history) >= 300:
                del self.labor_unit_farm_history[0]
            self.labor_unit_farm_history.append(self.labor_unit_farm)
            self.RecordInCSV(employed_adult_rates, 'labor_unit_farm', current_round)

    def SetLandPrice(self, current_round, land_transaction_prices):
        if len(land_transaction_prices) > 0:
            self.land = statistics.median(land_transaction_prices)
            if len(self.land_history) >= 300:
                del self.land_history[0]
            self.land_history.append(self.land)
            self.RecordInCSV(land_transaction_prices, 'land', current_round)

    def SetMachinePrice(self, current_round, machine_transaction_prices):
        if len(machine_transaction_prices) > 0:
            self.machine = statistics.median(machine_transaction_prices)
            if len(self.machine_history) >= 300:
                del self.machine_history[0]
            self.machine_history.append(self.machine)
            self.RecordInCSV(machine_transaction_prices, 'machine', current_round)
        
class ProductivityGrowthFunction:
    def __init__(self, productivity):
        for i in productivity:
            setattr(self, i, productivity[i])
    
    def SolveProductivity(self, yields_hired):
        productivity = yields_hired**self.exp + self.y_intercept 
        return productivity

class IndustrySwtichPenaltyFunction:
    def CalculateTotalCapitalAdjustment(self, total_capital_multiplied):
        return 1 / (total_capital_multiplied/2)**0.5

    def CalculateIndustrySwitchPenaltyOutputMultiplier(self, machines, land, total_capital_multiplied):
        capital = machines*land
        total_capital_adjustment = self.CalculateTotalCapitalAdjustment(total_capital_multiplied)
        penalty_output_multiplier = 1 - total_capital_adjustment*(capital**0.5)
        if penalty_output_multiplier < 0:
            penalty_output_multiplier = 0
        return penalty_output_multiplier

