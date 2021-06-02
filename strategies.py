import abc
import math
from numpy import mean
from numpy import array
import statistics
import random
import copy

def ConvertValueToFood(value, food_price):
    return value/food_price

def SolveInitialFoodDemand(y, m, x, b):
    if y == 'solve':
        answer = m * x ** 2 + b
    if m == 'solve':
        answer = (y - b) / x ** 2
    if x == 'solve':
        answer = ((y - b) / m) ** (1 / 2)
    if b == 'solve':
        answer = y - (m * x ** 2)
    return answer

def SolveInitialFoodSupply(y, m, x, b):
    if y == 'solve':
        answer = m * x ** -2 + b
    if m == 'solve':
        answer = (y - b) / x ** -2
    if x == 'solve':
        answer = ((y - b) / m) ** (-1 / 2)
    if b == 'solve':
        answer = y - (m * x ** -2)
    return answer

class FoodStrategies(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, agent_object, max_food_spoil_days, daily_food_consumption):
        self.model_shift = 0.
        self.transaction_counter = 0
        self.model_multiplier = 0.0001
        self.food_value = 0.
        self.max_food_spoil_days = max_food_spoil_days
        self.food_value = {}
        self.buyer_seller_offer_difference = []
        self.food_costs = {}
        self.SetExtraFood(agent_object, daily_food_consumption)


    def GetFoodAfterSpoilDays(self, spoil_with_food, spoil_day):
        food_after_spoil_days = 0
        for i in spoil_with_food:
            if int(i) > spoil_day:
                food_after_spoil_days += spoil_with_food[i]
        return food_after_spoil_days

    def GetFoodBeforeSpoilDays(self, spoil_with_food, spoil_day, daily_food_consumption, offspring_number):
        food_before_spoil_days = 0
        for spoil_days in spoil_with_food:
            if spoil_days < spoil_day:
                max_personal_storage_in_spoil_days = daily_food_consumption.adult*spoil_days + daily_food_consumption.child*spoil_days*offspring_number
                if spoil_with_food[spoil_days] + food_before_spoil_days > max_personal_storage_in_spoil_days :
                    food_before_spoil_days = max_personal_storage_in_spoil_days 
                else:
                    food_before_spoil_days = spoil_with_food[spoil_days]+food_before_spoil_days
        return food_before_spoil_days
    
    def SetExtraFood(self, agent_object, daily_food_consumption):
        extra_food = {}
        spoil_with_food = agent_object.GetSpoilWithFood()
        for i in range(1,self.max_food_spoil_days+1):
            daily_family_consumption = daily_food_consumption.adult + daily_food_consumption.child*len(agent_object.offspring)
            max_personal_storage_in_i_days = daily_family_consumption*i
            food_after_spoil_days = self.GetFoodAfterSpoilDays(spoil_with_food, i)
            food_before_spoil_days = self.GetFoodBeforeSpoilDays(spoil_with_food, i, daily_food_consumption, len(agent_object.offspring))
            food_with_spoil_days = agent_object[f'food_{i}']
            extra_food[i] = food_after_spoil_days+food_before_spoil_days+food_with_spoil_days - max_personal_storage_in_i_days
        self.extra_food = extra_food
    
    def SetTransactionCounter(self):
        transaction_counter = 0
        for i in self.buyer_seller_offer_difference:
            if i >= 0:
                transaction_counter += 1
            else:
                transaction_counter -= 1
        return transaction_counter
    
    def AdjustFoodCosts(self):
        if 1 in self.food_costs:
            del self.food_costs[1]
        for i in list(self.food_costs.keys()):
            self.food_costs[i-1] = self.food_costs.pop(i)

    @abc.abstractmethod
    def SetFoodValue(self):
        pass

    @abc.abstractmethod
    def AdjustFoodValue(self):
        pass


class FoodSupply(FoodStrategies):
    def SetFoodValue(self, agent_object):
        for i in self.extra_food:
            if self.extra_food[i] < 1 or agent_object[f'food_{i}'] < 1:
                self.food_value[i] = -1
            else:
                self.food_value[i] = SolveInitialFoodSupply('solve', self.model_multiplier, self.extra_food[i], self.model_shift)
                if i in self.food_costs and self.food_costs[i] > self.food_value[i] and i > 1:
                    self.food_value[i] = self.food_costs[i]
                elif self.food_value[i] < 0:
                    # value should get close to but never touch 0 this keeps that from happening
                    self.food_value[i] = 0.001

    def AdjustFoodValue(self, agent_object, hunger_level_max, variance_controls):
        transaction_counter = self.SetTransactionCounter()
        if transaction_counter > variance_controls.transaction_food_reaction or transaction_counter < -variance_controls.transaction_food_reaction:
            median_difference = statistics.median(self.buyer_seller_offer_difference)
            hunger_sensitivity = agent_object.hunger_level
            if median_difference > 0:
                hunger_sensitivity = (hunger_level_max - agent_object.hunger_level)
            hunger_sensitivity_adjuster = (hunger_sensitivity/hunger_level_max) * 10
            self.model_shift += median_difference * random.uniform(variance_controls.food_lowerbound, variance_controls.food_upperbound) * hunger_sensitivity_adjuster
            self.buyer_seller_offer_difference = []

    

class FoodDemand(FoodStrategies):
    def KeepBidFromFromDroppingBelowZero(self, days_until_next_yield):
        food_bid = SolveInitialFoodDemand('solve', self.model_multiplier, self.extra_food[days_until_next_yield],self.model_shift)
        if food_bid < 0:
            self.model_shift += abs(food_bid)+0.001

    def SetFoodValue(self, agent_object, daily_food_consumption, days_to_yield, hunger_level_max, current_round):
        days_until_next_yield = (days_to_yield - current_round%days_to_yield)
        food_needed_before_yield = daily_food_consumption.adult * days_until_next_yield
        self.KeepBidFromFromDroppingBelowZero(days_until_next_yield)
        for i in self.extra_food:
            if self.extra_food[i] > -1:
                # maybe signify agent has sufficient food?
                self.food_value[i] = 0
            else:
                self.food_value[i] = SolveInitialFoodDemand('solve', self.model_multiplier, self.extra_food[i],self.model_shift)
                if self.food_value[i] > agent_object['money']/food_needed_before_yield or agent_object.hunger_level+2 >= hunger_level_max:
                    self.food_value[i] =  agent_object['money']/food_needed_before_yield

    def AdjustFoodValue(self, agent_object, hunger_level_max, variance_controls):
        transaction_counter = self.SetTransactionCounter()
        if transaction_counter > variance_controls.transaction_food_reaction or transaction_counter < -variance_controls.transaction_food_reaction:
            median_difference = statistics.median(self.buyer_seller_offer_difference)
            hunger_sensitivity = agent_object.hunger_level
            if median_difference > 0:
                hunger_sensitivity = hunger_level_max - agent_object.hunger_level
            hunger_sensitivity_adjuster = (hunger_sensitivity/hunger_level_max) * 10
            self.model_shift -= median_difference * random.uniform(variance_controls.food_lowerbound, variance_controls.food_upperbound) * hunger_sensitivity_adjuster
            self.buyer_seller_offer_difference = []


class MachineStrategies(object):
    __metaclass__ = abc.ABCMeta
    def __init__(self, variance_controls):
        self.new_machine_value = 0.
        self.market_optimism = random.uniform(variance_controls.default_lowerbound, variance_controls.default_upperbound)
        self.market_optimism_bounds = [variance_controls.default_lowerbound, variance_controls.default_upperbound]
        self.all_output_asset_prices = []
        self.all_labor_unit_costs = []
    
    def SolveYieldProfitEquation(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, agent_object, machine_amount):
        if agent_object.current_industry == 'farm':
            output_item_price = getattr(asset_prices, 'food', None)
            wage_cost = getattr(asset_prices, 'labor_unit_farm', None)
        else:
            output_item_price = getattr(asset_prices, 'machine', None)
            wage_cost = getattr(asset_prices, 'labor_unit_factory', None)
        wage_in_output = wage_cost/output_item_price
        differential = production_function[agent_object.current_industry].FindProductionDifferential(capital_combination_function.SolveRelationship(machine_amount, agent_object['land']))
        optimal_workforce = production_function[agent_object.current_industry].SolveOptimalWorkForce(differential, wage_in_output)
        daily_food_cost = (len(agent_object.offspring)*daily_food_consumption.child + daily_food_consumption.adult) * asset_prices.food
        profit = production_function[agent_object.current_industry].SolveProduction(optimal_workforce, capital_combination_function.SolveRelationship(machine_amount, agent_object['land']))*output_item_price - optimal_workforce*wage_cost - daily_food_cost*days_to_yield
        return profit,optimal_workforce

    def CalculateMarketDirection(self, output_price_relative_to_inputs):
        market_direction = 0
        first_price = output_price_relative_to_inputs[0]
        for i in output_price_relative_to_inputs[1:]:
            second_price = i
            market_direction += second_price - first_price
            first_price = i
        return market_direction
    
    def AdjustMarketOptimism(self, agent_object, variance_controls, asset_prices):
        if agent_object.current_industry == 'farm':
            good = 'food'
            labor = 'labor_unit_farm'
        else:
            good = 'machine'
            labor = 'labor_unit_factory'
        good_price_history = getattr(asset_prices, f'{good}_history', None)
        labor_price_history = getattr(asset_prices, f'{labor}_history', None)
        land_price_history = getattr(asset_prices, 'land_history', None)
        price_history_memory = agent_object.price_history_memory
        shortest_history = min([len(good_price_history),len(labor_price_history),len(land_price_history)])
        if price_history_memory > shortest_history:
            price_history_memory = shortest_history
        if price_history_memory < 2:
            return
        remembered_output_prices = array(good_price_history[-price_history_memory:])
        remembered_labor_prices = array(labor_price_history[-price_history_memory:])
        remembered_land_prices = array(land_price_history[-price_history_memory:])
        output_price_relative_to_inputs = remembered_output_prices/(remembered_labor_prices*remembered_land_prices)
        market_direction = self.CalculateMarketDirection(output_price_relative_to_inputs)
        if market_direction > 0:
            self.market_optimism += (self.market_optimism_bounds[1] - self.market_optimism) * random.uniform(variance_controls.land_lowerbound, variance_controls.land_upperbound)
        elif market_direction < 0:
            self.market_optimism -= (self.market_optimism - self.market_optimism_bounds[0]) * random.uniform(variance_controls.land_lowerbound, variance_controls.land_upperbound)
    
    @abc.abstractmethod
    def SetMachineValue(self):
        pass

    @abc.abstractmethod
    def AdjustMachineValue(self):
        pass

class MachineDemand(MachineStrategies):
    def AdjustMachineQualityWithCurrentMoney(self, agent_object, daily_food_consumption, asset_prices, emergency_savings_length, machine_quality_tiers):
        family_daily_food_consumption = daily_food_consumption.adult + len(agent_object.offspring)*daily_food_consumption.child
        emergency_savings = (family_daily_food_consumption*emergency_savings_length)*asset_prices.food
        money_after_saving = agent_object['money'] - emergency_savings
        if money_after_saving < 0:
            money_after_saving = 0
        self.preferred_machine_quality_tier = 0
        self.machine_max_pay = self.new_machine_value
        if self.new_machine_value > money_after_saving:
            machine_quality_tier_threshold = 1/machine_quality_tiers
            affordable_machine_quality = money_after_saving/self.new_machine_value
            preferred_machine_quality_tier = (machine_quality_tiers-1) - math.ceil(affordable_machine_quality/machine_quality_tier_threshold)
            self.preferred_machine_quality_tier = preferred_machine_quality_tier
            self.machine_max_pay = money_after_saving
    
    def SetMachineValue(self, agent_object, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, machine_quality_tiers, demanded_machines=1):
        if agent_object['land'] < 1:
            self.new_machine_value = 0
            self.machine_max_pay = self.new_machine_value
            self.preferred_machine_quality_tier = 0
            return
        current_yield_profit_estimation = 0
        if agent_object['land'] > 0 and agent_object.GetMachineAmount() > 0:
            current_yield_profit_estimation,_ = self.SolveYieldProfitEquation(production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, agent_object, agent_object.GetMachineAmount())
        possible_yield_profit,optimal_workforce = self.SolveYieldProfitEquation(production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, agent_object, agent_object.GetMachineAmount()+demanded_machines)
        self.new_machine_value = (possible_yield_profit - current_yield_profit_estimation) * math.ceil(1/depreciation_function.SolveDepreciationAmount(optimal_workforce,agent_object['land']))
        self.new_machine_value *= self.market_optimism
        if self.new_machine_value < 0:
            self.new_machine_value = 0
        self.AdjustMachineQualityWithCurrentMoney(agent_object, daily_food_consumption, asset_prices, emergency_savings_length, machine_quality_tiers)

    def AdjustMachineValue(self, agent_object, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, variance_controls, machine_quality_tiers):
        self.AdjustMarketOptimism(agent_object, variance_controls, asset_prices)
        self.SetMachineValue(agent_object, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, machine_quality_tiers)  

class MachineSupply(MachineStrategies):
    def SetMachineValue(self, agent_object, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function):
        if agent_object.GetMachineAmount() < 1 or agent_object['land'] < 1:
            self.new_machine_value = 0
        else:
            current_yield_profit_estimation,optimal_workforce = self.SolveYieldProfitEquation(production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, agent_object, agent_object.GetMachineAmount())
            possible_yield_profit = 0
            if agent_object.GetMachineAmount() > 1:
                possible_yield_profit,_ = self.SolveYieldProfitEquation(production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, agent_object, agent_object.GetMachineAmount()-1)
            self.new_machine_value = (current_yield_profit_estimation - possible_yield_profit) * math.ceil(1/depreciation_function.SolveDepreciationAmount(optimal_workforce,agent_object['land']))
            self.new_machine_value *= self.market_optimism
    
    def AdjustMachineValue(self, agent_object, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, variance_controls):
        self.AdjustMarketOptimism(agent_object, variance_controls, asset_prices)
        self.SetMachineValue(agent_object, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function)  


class LaborStrategies(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def SetInitialLaborUnitValue(self):
        pass

    @abc.abstractmethod
    def AdjustLaborUnitValue(self):
        pass

    @abc.abstractclassmethod
    def ResetLaborSearch(self):
        pass


class LaborSupply(LaborStrategies):
    def __init__(self, harvests_worked, productivity_growth_function):
        self.highest_offer = 0.
        self.labor_unit_value = 0.
        self.percent_of_labor_units_fulfilled = 0.
        self.accepted_offer_price = 0.
        self.productivity = {}
        self.UpdateProductivity(harvests_worked, productivity_growth_function)
        self.searching = 1
        self.daily_labor_contract = -1
        self.price_per_unit = -1

    def UpdateProductivity(self, harvests_worked, productivity_growth_function):
        for i in harvests_worked:
            self.productivity[i] = productivity_growth_function.SolveProductivity(harvests_worked[i])

    def ResetLaborSearch(self):
        self.searching = 1
        self.daily_labor_contract = -1
        self.price_per_unit = -1
    
    def CalculateLaborUnits(self, included_agent_objects):
        labor_units = 0
        for i in self.productivity:
            if i[1] in included_agent_objects:
                labor_units += self.productivity[i]
        return labor_units

    def SetInitialLaborUnitValue(self, daily_food_consumption, food_price, agent_object, days_to_yield):
        initial_labor_unit_value = ((((len(self.productivity) - 1) * daily_food_consumption.child + daily_food_consumption.adult) * food_price) / self.CalculateLaborUnits([agent_object.id]))*days_to_yield
        if self.labor_unit_value < initial_labor_unit_value:
            self.labor_unit_value = initial_labor_unit_value
    
    def PickHigherLaborUnitValue(self, other_labor_strategy):
        if other_labor_strategy.labor_unit_value > self.labor_unit_value:
            self.labor_unit_value = other_labor_strategy.labor_unit_value
    
    def CreateModifiedOffer(self, demanded_labor_units, initial_offer):        
        included_labor_units = {}
        for i in self.productivity:
            included_labor_units[i] = self.productivity[i]
            if sum(included_labor_units.values()) >= demanded_labor_units:
                break
        supplied_labor_units = sum(included_labor_units.values())
        if supplied_labor_units <= demanded_labor_units:
            fulfilled_labor_units = supplied_labor_units
        else:
            fulfilled_labor_units = demanded_labor_units                                 
        initial_offer.quantity = fulfilled_labor_units
        initial_offer.price *= fulfilled_labor_units
        modified_offer = initial_offer
        return modified_offer,included_labor_units
    
    def AdjustLaborUnitValue(self, agent_object, percent_of_labor_units_fulfilled, avg_offer, food_price, daily_food_consumption, productivity_growth_function, days_to_yield):
        if self.accepted_offer_price > 0:
            self.labor_unit_value = self.accepted_offer_price
            self.searching = 0
        else:
            if self.labor_unit_value > avg_offer:
                adjust_base = (self.labor_unit_value-avg_offer)
            else:
                adjust_base = food_price/productivity_growth_function.y_intercept
            highest_spoil_days = max(agent_object.primary_food_strategy.extra_food.keys())
            total_food_demand = agent_object.GetFoodAmount() - agent_object.primary_food_strategy.extra_food[highest_spoil_days]
            fulfilled_food_demand = agent_object.GetFoodAmount()/total_food_demand
            if fulfilled_food_demand > 1:
                fulfilled_food_demand = 1
            adjust_scalar = percent_of_labor_units_fulfilled* (1-fulfilled_food_demand)
            new_labor_unit_value = self.labor_unit_value - adjust_base*adjust_scalar
            daily_adult_food_cost = daily_food_consumption.adult*food_price
            if new_labor_unit_value >= (daily_adult_food_cost*days_to_yield)/self.CalculateLaborUnits([agent_object.id]):
                self.labor_unit_value = new_labor_unit_value
    
    def SetDailyLaborContract(self, modified_offer, days_to_yield):
        self.daily_labor_contract = modified_offer
        self.price_per_unit = modified_offer.price / modified_offer.quantity
        self.daily_labor_contract.price = modified_offer.price / days_to_yield
        self.daily_labor_contract.quantity = modified_offer.quantity / days_to_yield
    


class LaborDemand(LaborStrategies):
    def __init__(self, harvests_worked, productivity_growth_function):
        self.accepted_labor_units_and_cost = [['labor_units'],['total_cost']]
        self.labor_unit_value = 0.
        self.searching = 1
        self.no_limit_accepted_labor_units = 0
        self.offspring_productivity = {}
        self.UpdateProductivity(harvests_worked, productivity_growth_function)
    
    def UpdateProductivity(self, harvests_worked, productivity_growth_function):
        for i in harvests_worked:
            if 'child' in i[0]:
                self.offspring_productivity[i] = productivity_growth_function.SolveProductivity(harvests_worked[i])
    
    def ResetLaborSearch(self):
        self.searching = 1
        self.accepted_labor_units_and_cost = [['labor_units'],['total_cost']]


    def SetInitialLaborUnitValue(self, asset_prices, production_function, capital_combination_function, agent_object, daily_food_consumption, max_food_spoil_days, lowest_labor_unit_ask, min_food_surplus=0):
        if self.labor_unit_value < lowest_labor_unit_ask:
           self.labor_unit_value = lowest_labor_unit_ask
        self.optimal_labor_units = self.CalculateOptimalLaborUnits(production_function, capital_combination_function, agent_object, asset_prices.food)
        expected_output = production_function.SolveProduction(self.optimal_labor_units, capital_combination_function.SolveRelationship(agent_object.GetMachineAmount(), agent_object['land']))
        max_personal_food_consumption = (len(agent_object.offspring)*daily_food_consumption.child + daily_food_consumption.adult)*max_food_spoil_days
        if expected_output < max_personal_food_consumption*min_food_surplus:
            self.AdjustLaborUnitValueForMinProduction(self.labor_unit_value, production_function, max_personal_food_consumption, min_food_surplus, agent_object, sum(self.accepted_labor_units_and_cost[0][1:]))
        if self.optimal_labor_units == 0:
            self.searching = 0

    def AdjustLaborUnitValue(self, agent_object, food_price, production_function, capital_combination_function, productivity_growth_function, daily_food_consumption, max_food_spoil_days, lowest_labor_unit_ask, min_food_surplus=0):
        accepted_labor_amount = sum(self.accepted_labor_units_and_cost[0][1:])
        accepted_labor_cost = sum(self.accepted_labor_units_and_cost[1][1:])
        food_portion_adjustment = (1 - self.no_limit_accepted_labor_units/self.optimal_labor_units)*(food_price/productivity_growth_function.y_intercept)
        self.no_limit_accepted_labor_units = 0
        possible_labor_unit_value = self.labor_unit_value + food_portion_adjustment
        if possible_labor_unit_value < lowest_labor_unit_ask:
            possible_labor_unit_value = lowest_labor_unit_ask
        self.ShouldAdultKeepSearchingForLabor(production_function, capital_combination_function, agent_object, food_price, accepted_labor_cost, accepted_labor_amount, possible_labor_unit_value, daily_food_consumption, max_food_spoil_days, min_food_surplus)

    def AdjustLaborUnitValueForMinProduction(self, possible_labor_unit_value, production_function, max_personal_food_consumption, min_food_surplus, agent_object, accepted_labor_amount):
        labor_units_for_min_food_production = production_function.SolveLaborUnitsForSetProductionAmount((max_personal_food_consumption*min_food_surplus), agent_object['land'])
        needed_labor_units = labor_units_for_min_food_production - accepted_labor_amount
        if self.optimal_labor_units >= needed_labor_units and self.labor_unit_value >= possible_labor_unit_value:
            new_optimal_labor_units = self.optimal_labor_units+1
            possible_labor_unit_value = self.labor_unit_value
            if new_optimal_labor_units*possible_labor_unit_value > agent_object['money']:
                self.searching = 0
                return
        else:
            self.labor_unit_value = possible_labor_unit_value
            new_optimal_labor_units = needed_labor_units
        if new_optimal_labor_units*possible_labor_unit_value > agent_object['money']:
            max_affordable_units = agent_object['money'] // possible_labor_unit_value
            new_optimal_labor_units = max_affordable_units  
        if new_optimal_labor_units == 0:
            self.searching = 0
        self.optimal_labor_units = new_optimal_labor_units
    

    def ShouldAdultKeepSearchingForLabor(self, production_function, capital_combination_function, agent_object, food_price, accepted_labor_cost, accepted_labor_amount, possible_labor_unit_value, daily_food_consumption, max_food_spoil_days, min_food_surplus):
        expected_output = production_function.SolveProduction(accepted_labor_amount, capital_combination_function.SolveRelationship(agent_object.GetMachineAmount(), agent_object['land']))
        max_personal_food_consumption = (len(agent_object.offspring)*daily_food_consumption.child + daily_food_consumption.adult)*max_food_spoil_days
        if expected_output < max_personal_food_consumption*min_food_surplus:
            self.AdjustLaborUnitValueForMinProduction(possible_labor_unit_value, production_function, max_personal_food_consumption, min_food_surplus, agent_object, accepted_labor_amount)
            return
        possible_labor_units = self.CalculateOptimalLaborUnits(production_function, capital_combination_function, agent_object, food_price, possible_labor_unit_value)
        if possible_labor_units <= 0 or self.labor_unit_value == possible_labor_unit_value:
            self.searching = 0
            return
        expected_profit = expected_output*food_price - accepted_labor_cost
        possible_labor_cost = possible_labor_units * possible_labor_unit_value
        possible_profit = production_function.SolveProduction(accepted_labor_amount+possible_labor_units, capital_combination_function.SolveRelationship(agent_object.GetMachineAmount(), agent_object['land']))*food_price - (accepted_labor_cost+possible_labor_cost)
        if possible_profit > expected_profit:
            self.labor_unit_value = possible_labor_unit_value
            self.optimal_labor_units = self.CalculateOptimalLaborUnits(production_function, capital_combination_function, agent_object, food_price)
        else:
            self.searching = 0
        
    def CalculateOptimalLaborUnits(self, production_function, capital_combination_function, agent_object, food_price, labor_unit_value=-1):
        if labor_unit_value == -1:
            labor_unit_value = self.labor_unit_value
        fulfilled_labor_units = sum(self.accepted_labor_units_and_cost[0][1:]) + sum(self.offspring_productivity.values())
        differential = production_function.FindProductionDifferential(capital_combination_function.SolveRelationship(agent_object.GetMachineAmount(), agent_object['land']), fulfilled_labor_units)
        optimal_labor_units = math.floor(production_function.SolveOptimalWorkForce(differential, ConvertValueToFood(labor_unit_value, food_price)))
        if self.labor_unit_value*optimal_labor_units > agent_object['money']:
            optimal_labor_units = agent_object['money']/self.labor_unit_value
        if optimal_labor_units < 0:
            optimal_labor_units = 0
        return optimal_labor_units
    

class LandStrategies(object):
    __metaclass__ = abc.ABCMeta
    def __init__(self, variance_controls):
        self.land_value = 0.
        self.market_optimism = random.uniform(variance_controls.default_lowerbound, variance_controls.default_upperbound)
        self.market_optimism_bounds = [variance_controls.default_lowerbound, variance_controls.default_upperbound]
        self.all_output_asset_prices = []
        self.all_labor_unit_costs = []
    
    def SolveYieldProfitEquation(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, agent_object, land_amount, industry_switch_penalty_output_multiplier=1):
        if agent_object.GetMachineAmount() > 0:
            machine_amount = agent_object.GetMachineAmount()
        else:
            machine_amount = 1
        if agent_object.current_industry == 'farm':
            output_item_price = getattr(asset_prices, 'food', None)
            wage_cost = getattr(asset_prices, 'labor_unit_farm', None)
        else:
            output_item_price = getattr(asset_prices, 'machine', None)
            wage_cost = getattr(asset_prices, 'labor_unit_factory', None)
        wage_in_output = wage_cost/output_item_price
        differential = production_function[agent_object.current_industry].FindProductionDifferential(capital_combination_function.SolveRelationship(machine_amount, land_amount))
        optimal_workforce = production_function[agent_object.current_industry].SolveOptimalWorkForce(differential, wage_in_output)
        daily_food_cost = (len(agent_object.offspring)*daily_food_consumption.child + daily_food_consumption.adult) * asset_prices.food
        current_machinery_value = 0
        if agent_object.GetMachineAmount() > 0:
            for i in agent_object.machine_quality_tracker[0].to_list():
                current_machinery_value += i*asset_prices.machine
        aggregate_machine_depreciation_cost = depreciation_function.SolveDepreciationAmount(optimal_workforce, land_amount) * machine_amount * asset_prices.machine
        output = production_function[agent_object.current_industry].SolveProduction(optimal_workforce, capital_combination_function.SolveRelationship(machine_amount, land_amount), industry_switch_penalty_output_multiplier)
        profit = output*output_item_price + current_machinery_value - optimal_workforce*wage_cost - daily_food_cost*days_to_yield - aggregate_machine_depreciation_cost
        return profit

    def CalculateMarketDirection(self, output_price_relative_to_inputs):
        market_direction = 0
        first_price = output_price_relative_to_inputs[0]
        for i in output_price_relative_to_inputs[1:]:
            second_price = i
            market_direction += second_price - first_price
            first_price = i
        return market_direction
    
    def AdjustMarketOptimism(self, agent_object, variance_controls, asset_prices):
        if agent_object.current_industry == 'farm':
            good = 'food'
            labor = 'labor_unit_farm'
        else:
            good = 'machine'
            labor = 'labor_unit_factory'
        good_price_history = getattr(asset_prices, f'{good}_history', None)
        labor_price_history = getattr(asset_prices, f'{labor}_history', None)
        machine_price_history = getattr(asset_prices, 'machine_history', None)
        price_history_memory = agent_object.price_history_memory
        shortest_history = min([len(good_price_history),len(labor_price_history),len(machine_price_history)])
        if price_history_memory > shortest_history:
            price_history_memory = shortest_history
        if price_history_memory < 2:
            return
        remembered_output_prices = array(good_price_history[-price_history_memory:])
        remembered_labor_prices = array(labor_price_history[-price_history_memory:])
        remembered_machine_prices = array(machine_price_history[-price_history_memory:])
        output_price_relative_to_inputs = remembered_output_prices/(remembered_labor_prices*remembered_machine_prices)
        market_direction = self.CalculateMarketDirection(output_price_relative_to_inputs)
        if market_direction > 0:
            self.market_optimism += (self.market_optimism_bounds[1] - self.market_optimism) * random.uniform(variance_controls.land_lowerbound, variance_controls.land_upperbound)
        elif market_direction < 0:
            self.market_optimism -= (self.market_optimism - self.market_optimism_bounds[0]) * random.uniform(variance_controls.land_lowerbound, variance_controls.land_upperbound)
     
    @abc.abstractmethod
    def SetLandValue(self):
        pass

    @abc.abstractmethod
    def AdjustLandValue(self):
        pass

class LandDemand(LandStrategies):
    def ConstrainTrueLandValueWithCurrentMoney(self, agent_object, daily_food_consumption, asset_prices, emergency_savings_length, savings_for_first_machine, true_land_value):
        family_daily_food_consumption = daily_food_consumption.adult + len(agent_object.offspring)*daily_food_consumption.child
        emergency_savings = (family_daily_food_consumption*emergency_savings_length)*asset_prices.food + savings_for_first_machine
        money_after_saving = agent_object['money'] - emergency_savings
        if money_after_saving <= 0:
            self.land_value = 0
            return
        if true_land_value > money_after_saving:
            self.land_value = money_after_saving
        else:
            self.land_value = true_land_value
    
    def SetLandValue(self, agent_object, production_function, capital_combination_function, asset_prices, days_to_yield, year_length, daily_food_consumption, depreciation_function, expected_years_in_family, emergency_savings_length, land_demanded=1):
        current_yield_profit_estimation = 0
        if agent_object['land'] > 0:
            current_yield_profit_estimation = self.SolveYieldProfitEquation(production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, agent_object, agent_object['land'])
        possible_yield_profit = self.SolveYieldProfitEquation(production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, agent_object, agent_object['land']+land_demanded)
        true_land_value = (possible_yield_profit - current_yield_profit_estimation) * expected_years_in_family * (days_to_yield/year_length)
        true_land_value *= self.market_optimism
        savings_for_first_machine = 0
        if agent_object.GetMachineAmount() == 0:
            savings_for_first_machine = asset_prices.machine
        self.ConstrainTrueLandValueWithCurrentMoney(agent_object, daily_food_consumption, asset_prices, emergency_savings_length, savings_for_first_machine, true_land_value)
        if self.land_value < 0:
            self.land_value = 0

    def AdjustLandValue(self, agent_object, variance_controls, asset_prices, production_function, capital_combination_function, days_to_yield, year_length, daily_food_consumption, depreciation_function, expected_years_in_family, emergency_savings_length):
        self.AdjustMarketOptimism(agent_object, variance_controls, asset_prices)
        self.SetLandValue(agent_object, production_function, capital_combination_function, asset_prices, days_to_yield, year_length, daily_food_consumption, depreciation_function, expected_years_in_family, emergency_savings_length)



class LandSupply(LandStrategies):
    def SetLandValue(self, agent_object, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, expected_years_in_family, year_length):
        self.land_value = 0
        if agent_object['land'] > 0:
            current_yearly_profit = self.SolveYieldProfitEquation(production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, agent_object, agent_object['land'])
            possible_yearly_profit = 0
            if agent_object['land'] > 1:
                possible_yearly_profit = self.SolveYieldProfitEquation(production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, agent_object, agent_object['land']-1)
            self.land_value = (current_yearly_profit - possible_yearly_profit) * expected_years_in_family * (days_to_yield/year_length)
            self.land_value *= self.market_optimism 
            if self.land_value < daily_food_consumption.adult*days_to_yield*asset_prices.food:
                self.land_value = daily_food_consumption.adult*days_to_yield*asset_prices.food

    def AdjustLandValue(self, agent_object, variance_controls, asset_prices, capital_combination_function, days_to_yield, daily_food_consumption, depreciation_function, production_function, expected_years_in_family, year_length):
        self.AdjustMarketOptimism(agent_object, variance_controls, asset_prices)
        self.SetLandValue(agent_object, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, expected_years_in_family, year_length)

        