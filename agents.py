import random
import operator
import matplotlib.pyplot as plt
import abcEconomics
from random import randint
from random import randrange
from numpy import mean
import numpy as np
import copy
import math
import pandas as pd

import log
import strategies

class Adult(abcEconomics.Agent):
    def init(self, family_name, age, num_food, max_food_spoil_days, num_money, num_land, num_machine, offspring, birthday, death_modifier, farm_jobs, factory_jobs, price_history_memory, industry_switch_counter, machine_quality_tracker, current_industry=None, reproduction_probability=0, parent=-1):
        self.family_name = family_name
        self.age = age
        self.create('money', num_money)
        self.create('land', num_land)
        for i in num_food:
            self.create(f'food_{i}', num_food[i])
        for i in num_machine:
            self.create(f'machine_{i}', num_machine[i])
        self.offspring = offspring
        self.birthday = birthday
        self.death_modifier = death_modifier
        self.farm_jobs = farm_jobs
        self.factory_jobs = factory_jobs
        self.price_history_memory = price_history_memory
        self.industry_switch_counter = industry_switch_counter
        self.machine_quality_tracker = machine_quality_tracker
        self.current_industry = current_industry
        self.reproduction_probability = reproduction_probability
        self.parent = parent
        self.hunger_level = 0
        self.industry_switch_penalty_output_multiplier = 1
        self.adult_offspring = []

    def ReturnSelf(self):
        return self
        
    def GetAllAliveAdults(self, dead_adults, alive_adults):
        if self.id not in dead_adults:
            alive_adults.append(self.id)
        return alive_adults

    def GiftFood(self, gift, max_food_spoil_days):
        gift_dict = {}
        for i in range(1, max_food_spoil_days+1):
            if self[f'food_{i}'] >= gift:
                self.destroy(f'food_{i}', gift)
                gift_dict[i] = gift
                break
            else:
                gift -= self[f'food_{i}']
                gift_dict[i] = self[f'food_{i}']
                self.destroy(f'food_{i}', self[f'food_{i}'])
        return gift_dict
    
    def GetSpoilWithFood(self):
        spoil_with_food = {}
        for i in self._inventory.haves:
            if 'food' in i and (self._inventory.haves[i] - self._inventory._reserved[i]) > 0:
                _,food_spoil_days = i.split('_')
                spoil_with_food[int(food_spoil_days)] = (self._inventory.haves[i] - self._inventory._reserved[i]) 
        return spoil_with_food

    def GetFoodAmount(self):
        food_amount = 0 
        for i in self._inventory.haves:
            if 'food' in i:
                food_amount += self._inventory.haves[i]
        return food_amount

    def GetQualityTierWithMachines(self):
        quality_tier_with_machines = {}
        for i in self._inventory.haves:
            if 'machine' in i and (self._inventory.haves[i] - self._inventory._reserved[i]) > 0:
                _,machine_quality_tiers = i.split('_')
                quality_tier_with_machines[int(machine_quality_tiers)] = (self._inventory.haves[i] - self._inventory._reserved[i]) 
        return quality_tier_with_machines

    def GetMachineAmount(self):
        machine_amount = 0
        for i in self._inventory.haves:
            if 'machine' in i:
                machine_amount += (self._inventory.haves[i] - self._inventory._reserved[i])
        return machine_amount
    
    def GiftMachine(self, gift, machine_quality_tiers):
        gift_dict = {}
        for i in range(machine_quality_tiers-1,-1,-1):
            if self[f'machine_{i}'] >= gift:
                self.destroy(f'machine_{i}', gift)
                gift_dict[i] = gift
                break
            else:
                gift -= self[f'machine_{i}']
                gift_dict[i] = self[f'machine_{i}']
                self.destroy(f'machine_{i}', self[f'machine_{i}'])
        return gift_dict

    
    def ResetReservedGoodsAndServices(self):
        for i in self._inventory._reserved:
            self._inventory._reserved[i] = 0

    def ReturnAdultObjectUsingAttribute(self, attribute, targets, agent_list):
        if getattr(self, attribute) in targets:
            agent_list.append(self)
        return agent_list

    def SetFoodStrategy(self, max_food_spoil_days, daily_food_consumption):
        self.primary_food_strategy = strategies.FoodDemand(self, max_food_spoil_days, daily_food_consumption) 
        if self.primary_food_strategy.extra_food[max_food_spoil_days] > 0:
            self.primary_food_strategy = strategies.FoodSupply(self, max_food_spoil_days, daily_food_consumption)

    def ResetFoodStrategies(self, current_round, days_to_yield, max_food_spoil_days, daily_food_consumption):
        self.primary_food_strategy.SetExtraFood(self, daily_food_consumption)
        days_until_next_yield = days_to_yield-(current_round%days_to_yield)
        if not hasattr(self, 'reserve_food_strategy'):
            if type(self.primary_food_strategy) is strategies.FoodDemand and self.primary_food_strategy.extra_food[days_until_next_yield] > 0:
                self.reserve_food_strategy = self.primary_food_strategy
                self.primary_food_strategy = strategies.FoodSupply(self, max_food_spoil_days, daily_food_consumption)
            elif type(self.primary_food_strategy) is strategies.FoodSupply and self.primary_food_strategy.extra_food[days_until_next_yield] < 0:
                self.reserve_food_strategy = self.primary_food_strategy
                self.primary_food_strategy = strategies.FoodDemand(self, max_food_spoil_days, daily_food_consumption)
        else:
            if (type(self.primary_food_strategy) is strategies.FoodSupply and self.primary_food_strategy.extra_food[days_until_next_yield] < 0) or (type(self.primary_food_strategy) is strategies.FoodDemand and self.primary_food_strategy.extra_food[days_until_next_yield] > 0):
                self.primary_food_strategy, self.reserve_food_strategy = self.reserve_food_strategy, self.primary_food_strategy    
    
    def SetInitialFoodValue(self, daily_food_consumption, days_to_yield, hunger_level_max, current_round):
        if type(self.primary_food_strategy) is strategies.FoodDemand:
            self.primary_food_strategy.SetFoodValue(self, daily_food_consumption, days_to_yield, hunger_level_max, current_round)
        else:
            self.primary_food_strategy.SetFoodValue(self)

    def GetFoodExpirations(self):
        agent_food_spoil_days = []
        for i in self._inventory.haves:
            if 'food' in i and self._inventory.haves[i] > 0:
                _,food_spoil_days = i.split('_')
                agent_food_spoil_days.append(int(food_spoil_days))
        return agent_food_spoil_days
    
    def GetFoodSellersWithSpoilDays(self, dead_adults, food_sellers_with_spoil_days):
        if type(self.primary_food_strategy) is strategies.FoodSupply and self.id not in dead_adults:
            agent_food_spoil_days = self.GetFoodExpirations()
            food_sellers_with_spoil_days[self.id] = agent_food_spoil_days
        return food_sellers_with_spoil_days

    def BuyFood(self, dead_adults, daily_food_consumption, days_to_yield, hunger_level_max, current_round, food_sellers_with_spoil_days):
        if type(self.primary_food_strategy) is strategies.FoodDemand and len(food_sellers_with_spoil_days) > 0 and self.id not in dead_adults:
            self.primary_food_strategy.SetFoodValue(self, daily_food_consumption, days_to_yield, hunger_level_max, current_round)
            self.primary_food_strategy.seller_id = random.choice(list(food_sellers_with_spoil_days.keys()))
            # this V is to deal with inventory reservation issues
            extra_temp_cash = sum([food_value for food_value in self.primary_food_strategy.food_value.values() if food_value > 0])
            actual_money = self['money']
            self.create('money', extra_temp_cash)
            for food_spoil_days in food_sellers_with_spoil_days[self.primary_food_strategy.seller_id]:
                if self.primary_food_strategy.food_value[food_spoil_days] > 0:
                    self.buy(('adult', self.primary_food_strategy.seller_id), good=f'food_{food_spoil_days}', quantity=1, price=self.primary_food_strategy.food_value[food_spoil_days])
            self.destroy('money', self['money'])
            self.create('money', actual_money)

    def GetBuyerOffers(self):
        buyer_food_offers = {}
        static_open_offers = copy.deepcopy(self._open_offers_buy)
        for good in static_open_offers:
            for offer in self.get_offers(good):
                if offer.sender[1] not in buyer_food_offers:
                    buyer_food_offers[offer.sender[1]] = []
                buyer_food_offers[offer.sender[1]].append(offer)
        return buyer_food_offers
    
    def GetAdultDescendingByFoodDemandBid(self, buyer_food_offers):
        buyer_highest_food_bid = {}
        for buyer in buyer_food_offers:
            buyer_highest_food_bid[buyer] = max(buyer_food_offers[buyer], key=operator.attrgetter('price'))
        adult_descending_by_food_demand_bid = []
        for offer in reversed(sorted(buyer_highest_food_bid.values(), key=operator.attrgetter('price'))):
            adult_descending_by_food_demand_bid.append(offer.sender[1])
        return adult_descending_by_food_demand_bid
    
    def EvaluateBuyerFoodOffers(self, buyer_food_offers, buyer, oldest_harvest_spoil_days, all_buyer_seller_offer_difference, food_transaction_prices):
        for offer in buyer_food_offers[buyer]:
            _,food_spoil_days = offer.good.split('_')
            if int(food_spoil_days) == oldest_harvest_spoil_days:
                buyer_seller = f'{offer.sender[1]}:{offer.receiver[1]}'
                all_buyer_seller_offer_difference[buyer_seller] = offer.price - self.primary_food_strategy.food_value[oldest_harvest_spoil_days]
                if offer.price >= self.primary_food_strategy.food_value[oldest_harvest_spoil_days] and self.primary_food_strategy.extra_food[oldest_harvest_spoil_days] > 0:
                    counteroffer_price = (self.primary_food_strategy.food_value[oldest_harvest_spoil_days] + offer.price) / 2
                    food_transaction_prices.append(counteroffer_price)
                    self.sell(offer.sender, offer.good, offer.quantity, counteroffer_price)
            self.reject(offer)
        return all_buyer_seller_offer_difference,food_transaction_prices

    def SellFood(self, all_buyer_seller_offer_difference, daily_food_consumption, max_food_spoil_days, food_transaction_prices):
        if type(self.primary_food_strategy) is strategies.FoodSupply:
            buyer_food_offers = self.GetBuyerOffers()
            adult_descending_by_food_demand_bid = self.GetAdultDescendingByFoodDemandBid(buyer_food_offers)
            for buyer in adult_descending_by_food_demand_bid:
                self.primary_food_strategy.SetExtraFood(self, daily_food_consumption)
                self.primary_food_strategy.SetFoodValue(self)
                spoil_with_food = self.GetSpoilWithFood()
                if len(spoil_with_food) == 0:
                    break
                oldest_harvest_spoil_days = min(spoil_with_food.keys())
                self.EvaluateBuyerFoodOffers(buyer_food_offers, buyer, oldest_harvest_spoil_days, all_buyer_seller_offer_difference, food_transaction_prices)
        return all_buyer_seller_offer_difference,food_transaction_prices
    
    def AcceptFoodCounterOffer(self):
        items_being_sold = []
        for item in self._open_offers_sell:
            items_being_sold.append(item)
        for item in items_being_sold:
            for offer in self.get_sell_offers(item):
                self.accept(offer)

    def MatchAgentToOfferRatio(self, all_buyer_seller_offer_difference):
        for i in all_buyer_seller_offer_difference:
            buyer,seller = i.split(':')
            if self.id == int(buyer) or self.id == int(seller):
                self.primary_food_strategy.buyer_seller_offer_difference.append(all_buyer_seller_offer_difference[i])

    def AdjustFoodValue(self, hunger_level_max, variance_controls):
        self.primary_food_strategy.AdjustFoodValue(self, hunger_level_max, variance_controls)
    
    def ReturnFamilyFarmJobs(self, children, child_age_upperbound):
        family_farm_jobs = {}
        family_farm_jobs[('adult',self.id)] = self.farm_jobs
        offspring_objects = []
        children.ReturnChildObjectUsingAttribute('id', self.offspring, offspring_objects)
        for i in offspring_objects:
            if i.age >= child_age_upperbound:
                family_farm_jobs[('child',i.id)] = i.farm_jobs
        return family_farm_jobs
    
    def ReturnFamilyFactoryJobs(self, children, child_age_upperbound):
        family_factory_jobs = {}
        family_factory_jobs[('adult',self.id)] = self.factory_jobs
        offspring_objects = []
        children.ReturnChildObjectUsingAttribute('id', self.offspring, offspring_objects)
        for i in offspring_objects:
            if i.age >= child_age_upperbound:
                family_factory_jobs[('child',i.id)] = i.factory_jobs
        return family_factory_jobs

    def IncrementFarmJobs(self, employed_adults_farm):
        if self.id in employed_adults_farm:
            self.farm_jobs += 1
        
    def IncrementFactoryJobs(self, employed_adults_factory):
        if self.id in employed_adults_factory:
            self.factory_jobs += 1
    
    def IncludeLandOwnerChildrenInLabor(self, all_employed_agents):
        if type(self.primary_labor_farm_strategy) is strategies.LaborDemand:
            if self.current_industry == 'farm':
                primary_labor_strategy = self.primary_labor_farm_strategy
                good = 'labor_units_farm'
            else:
                primary_labor_strategy = self.primary_labor_factory_strategy
                good = 'labor_units_factory'
            for i in primary_labor_strategy.offspring_productivity:
                all_employed_agents.append(('child',i,self.current_industry))
            self.create(good, sum(primary_labor_strategy.offspring_productivity.values()))

    def SetInitialLaborStrategies(self, children, child_age_upperbound, productivity_growth_function):
        if self['land'] < 1 or self.GetMachineAmount() < 1:
            self.primary_labor_farm_strategy = strategies.LaborSupply(self.ReturnFamilyFarmJobs(children, child_age_upperbound), productivity_growth_function)
            self.primary_labor_factory_strategy = strategies.LaborSupply(self.ReturnFamilyFactoryJobs(children, child_age_upperbound), productivity_growth_function)
        elif self['land'] > 0 and self.GetMachineAmount() > 0:
            self.primary_labor_farm_strategy = strategies.LaborDemand(self.ReturnFamilyFarmJobs(children, child_age_upperbound), productivity_growth_function)
            self.primary_labor_factory_strategy = strategies.LaborDemand(self.ReturnFamilyFactoryJobs(children, child_age_upperbound), productivity_growth_function)
    
    def ResetLaborStrategies(self, children, child_age_upperbound, production_function, asset_prices, productivity_growth_function, daily_food_consumption, max_food_spoil_days, min_food_surplus):
        if not hasattr(self, 'reserve_labor_farm_strategy'):
            if (self['land'] > 0 and self.GetMachineAmount() > 0) and type(self.primary_labor_farm_strategy) is strategies.LaborSupply:
                self.reserve_labor_farm_strategy = self.primary_labor_farm_strategy
                self.primary_labor_farm_strategy = strategies.LaborDemand(self.ReturnFamilyFarmJobs(children, child_age_upperbound), productivity_growth_function)
                self.reserve_labor_factory_strategy = self.primary_labor_factory_strategy
                self.primary_labor_factory_strategy = strategies.LaborDemand(self.ReturnFamilyFactoryJobs(children, child_age_upperbound), productivity_growth_function)
            elif (self['land'] < 1 or self.GetMachineAmount() < 1) and type(self.primary_labor_farm_strategy) is strategies.LaborDemand:
                self.reserve_labor_farm_strategy = self.primary_labor_farm_strategy
                self.primary_labor_farm_strategy = strategies.LaborSupply(self.ReturnFamilyFarmJobs(children, child_age_upperbound), productivity_growth_function)
                self.reserve_labor_factory_strategy = self.primary_labor_factory_strategy
                self.primary_labor_factory_strategy = strategies.LaborSupply(self.ReturnFamilyFactoryJobs(children, child_age_upperbound), productivity_growth_function)
        else:
            if ((self['land'] > 0 and self.GetMachineAmount() > 0) and type(self.primary_labor_farm_strategy) is strategies.LaborSupply) or ((self['land'] < 1 or self.GetMachineAmount() < 1)  and type(self.primary_labor_farm_strategy) is strategies.LaborDemand):
                self.primary_labor_farm_strategy, self.reserve_labor_farm_strategy = self.reserve_labor_farm_strategy, self.primary_labor_farm_strategy
                self.primary_labor_farm_strategy.UpdateProductivity(self.ReturnFamilyFarmJobs(children, child_age_upperbound), productivity_growth_function)
                self.primary_labor_factory_strategy, self.reserve_labor_factory_strategy = self.reserve_labor_factory_strategy, self.primary_labor_factory_strategy
                self.primary_labor_factory_strategy.UpdateProductivity(self.ReturnFamilyFactoryJobs(children, child_age_upperbound), productivity_growth_function)

    def CountEmployersSearching(self, employers_searching):
        if type(self.primary_labor_farm_strategy) is strategies.LaborDemand:
            if self.current_industry == 'farm':
                employers_searching.append(self.primary_labor_farm_strategy.searching)
            else:
                employers_searching.append(self.primary_labor_factory_strategy.searching)
        return employers_searching
    
    def SetLaborUnitSupplyValue(self, daily_food_consumption, asset_prices, days_to_yield, initial_labor_unit_asks):
        if self['land'] < 1 or self.GetMachineAmount() < 1:
            self.primary_labor_farm_strategy.SetInitialLaborUnitValue(daily_food_consumption, asset_prices.food, self, days_to_yield)
            self.primary_labor_factory_strategy.SetInitialLaborUnitValue(daily_food_consumption, asset_prices.food, self, days_to_yield)
            self.primary_labor_farm_strategy.PickHigherLaborUnitValue(self.primary_labor_factory_strategy)
            self.primary_labor_factory_strategy.PickHigherLaborUnitValue(self.primary_labor_farm_strategy)
            initial_labor_unit_asks['farm'].append(self.primary_labor_farm_strategy.labor_unit_value)
            initial_labor_unit_asks['factory'].append(self.primary_labor_factory_strategy.labor_unit_value)
        return initial_labor_unit_asks
    
    def SetLaborUnitDemandValue(self, asset_prices, production_function, capital_combination_function, daily_food_consumption, max_food_spoil_days, lowest_labor_unit_ask, min_food_surplus):
        if self['land'] > 0 and self.GetMachineAmount() > 0:
            if self.current_industry == 'farm':
                self.primary_labor_farm_strategy.SetInitialLaborUnitValue(asset_prices, production_function['farm'], capital_combination_function, self, daily_food_consumption, max_food_spoil_days, lowest_labor_unit_ask['farm'], min_food_surplus)
            else:
                self.primary_labor_factory_strategy.SetInitialLaborUnitValue(asset_prices, production_function['factory'], capital_combination_function, self, daily_food_consumption, max_food_spoil_days, lowest_labor_unit_ask['factory'])

    def GetLaborForce(self, labor_force):
        if (self['land'] < 1 or self.GetMachineAmount() < 1) and (self.primary_labor_farm_strategy.searching == 1 and self.primary_labor_factory_strategy.searching == 1):
            labor_force.append(self.id)
        return labor_force

    def BuyLaborUnits(self, labor_force):
        # ABCE library throws exception when outstanding offers exceed total cash. 
        # This should not throw an exception in my program so the cash is temporarily held here while a large number replaces the agents current cash
        if type(self.primary_labor_farm_strategy) is strategies.LaborDemand:
            if self.current_industry == 'farm':
                primary_labor_strategy = self.primary_labor_farm_strategy
                good = 'labor_units_farm'
            else:
                primary_labor_strategy = self.primary_labor_factory_strategy
                good = 'labor_units_factory'
            if primary_labor_strategy.searching == 1: 
                real_money = self['money']
                lots_of_money = (primary_labor_strategy.labor_unit_value*primary_labor_strategy.optimal_labor_units*len(labor_force))**20
                self.create('money', lots_of_money)
                for i in labor_force:
                    self.buy(('adult', i), good=good, quantity=primary_labor_strategy.optimal_labor_units, price=primary_labor_strategy.labor_unit_value)
                self.destroy('money', self['money'])
                self.create('money', real_money)
    
    def ReturnFarmWorkers(self, farm_workers):
        if type(self.primary_labor_farm_strategy) is strategies.LaborSupply and self.current_industry == 'farm' and self.primary_labor_farm_strategy.searching == 0:
            farm_workers.append(self.id)
        return farm_workers

    def SellLaborUnits(self, adults, no_limit_accepted_offers, farm_only, days_to_yield, all_employed_agents):
        if type(self.primary_labor_farm_strategy) is strategies.LaborSupply:
            self.primary_labor_farm_strategy.accepted_offer_price = 0.
            self.primary_labor_factory_strategy.accepted_offer_price = 0.
            all_offers = self.get_offers("labor_units_farm")
            all_offers.extend(self.get_offers("labor_units_factory"))
            random.shuffle(all_offers)
            for offer in all_offers:
                if offer.good == 'labor_units_farm':
                    primary_labor_strategy = self.primary_labor_farm_strategy
                else:
                    primary_labor_strategy = self.primary_labor_factory_strategy          
                if offer.price >= primary_labor_strategy.labor_unit_value and (self.primary_labor_farm_strategy.accepted_offer_price == 0 and self.primary_labor_factory_strategy.accepted_offer_price == 0):
                    if offer.sender[1] not in no_limit_accepted_offers:
                        no_limit_accepted_offers[offer.sender[1]] = []
                    no_limit_accepted_offers[offer.sender[1]].append(sum(primary_labor_strategy.productivity.values())) 
                    employer_object = adults[offer.sender[1]].ReturnSelf()[0][0]
                    demanded_labor_units = offer.quantity - employer_object[offer.good]
                    modified_offer,included_labor_units = primary_labor_strategy.CreateModifiedOffer(demanded_labor_units, copy.deepcopy(offer))
                    supplied_labor_units_value = sum(included_labor_units.values()) * primary_labor_strategy.labor_unit_value
                    if modified_offer.price >= supplied_labor_units_value:
                        if farm_only == 1 and offer.good == 'labor_units_factory':
                            break
                        primary_labor_strategy.accepted_offer_price = offer.price
                        # landowners get labor units here so they can properly adjust their value. It is all destroyed after labor bidding ends
                        self.create(offer.good, modified_offer.quantity)
                        self.give(offer.sender, good=offer.good, quantity=modified_offer.quantity)
                        self.current_industry = offer.good.split('_')[-1]
                        primary_labor_strategy.SetDailyLaborContract(modified_offer, days_to_yield)
                        for agent in included_labor_units:
                            all_employed_agents.append(agent+(self.current_industry,))           
        return no_limit_accepted_offers, all_employed_agents
                

    def CheckLaborTransaction(self, offered_values, demanded_labor_units, fulfilled_labor_units, no_limit_accepted_offers):
        if type(self.primary_labor_farm_strategy) is strategies.LaborDemand:
            if self.current_industry == 'farm':
                primary_labor_strategy = self.primary_labor_farm_strategy
                good = 'labor_units_farm'
            else:
                primary_labor_strategy = self.primary_labor_factory_strategy
                good = 'labor_units_factory'
            if self.id in no_limit_accepted_offers:
                primary_labor_strategy.no_limit_accepted_labor_units = sum(no_limit_accepted_offers[self.id])
            offered_values[good].append(primary_labor_strategy.optimal_labor_units*primary_labor_strategy.labor_unit_value)
            demanded_labor_units[good].append(primary_labor_strategy.optimal_labor_units)
            fulfilled_labor_units[good].append(self[good])
            if self[good] > 0:
                primary_labor_strategy.accepted_labor_units_and_cost[0].append(self[good])
                primary_labor_strategy.accepted_labor_units_and_cost[1].append(primary_labor_strategy.labor_unit_value*self[good])
                self.destroy(good, self[good])
        return offered_values, demanded_labor_units, fulfilled_labor_units

    def AdjustLaborUnitSupplyValue(self, percent_of_labor_units_fulfilled, avg_offer, asset_prices, daily_food_consumption, productivity_growth_function, days_to_yield, new_labor_unit_asks):
        if type(self.primary_labor_farm_strategy) is strategies.LaborSupply and (self.primary_labor_farm_strategy.searching == 1 and self.primary_labor_factory_strategy.searching == 1):
            self.primary_labor_farm_strategy.AdjustLaborUnitValue(self, percent_of_labor_units_fulfilled['labor_units_farm'], avg_offer['labor_units_farm'], asset_prices.food, daily_food_consumption, productivity_growth_function, days_to_yield)
            self.primary_labor_factory_strategy.AdjustLaborUnitValue(self, percent_of_labor_units_fulfilled['labor_units_factory'], avg_offer['labor_units_factory'], asset_prices.food, daily_food_consumption, productivity_growth_function, days_to_yield)
            new_labor_unit_asks['farm'].append(self.primary_labor_farm_strategy.labor_unit_value)
            new_labor_unit_asks['factory'].append(self.primary_labor_factory_strategy.labor_unit_value)
        return new_labor_unit_asks
    
    def AdjustLaborUnitDemandValue(self, asset_prices, production_function, capital_combination_function, productivity_growth_function, daily_food_consumption, max_food_spoil_days, lowest_labor_unit_ask, min_food_surplus):
        if type(self.primary_labor_farm_strategy) is strategies.LaborDemand and (self.primary_labor_farm_strategy.searching == 1 and self.primary_labor_factory_strategy.searching == 1):
            if self.current_industry == 'farm':
                self.primary_labor_farm_strategy.AdjustLaborUnitValue(self, asset_prices.food, production_function['farm'], capital_combination_function, productivity_growth_function, daily_food_consumption, max_food_spoil_days, lowest_labor_unit_ask['farm'], min_food_surplus)
            else:
                self.primary_labor_factory_strategy.AdjustLaborUnitValue(self, asset_prices.food, production_function['factory'], capital_combination_function, productivity_growth_function, daily_food_consumption, max_food_spoil_days, lowest_labor_unit_ask['factory'])

    def GetEmployeeRates(self, employee_rates):
        if type(self.primary_labor_farm_strategy) is strategies.LaborSupply:
            if self.current_industry == 'farm':
                primary_labor_strategy = self.primary_labor_farm_strategy
                good = 'labor_units_farm'
            else:
                primary_labor_strategy = self.primary_labor_factory_strategy
                good = 'labor_units_factory'    
            employee_rates[good].append(primary_labor_strategy.price_per_unit)
        return employee_rates
    
    def ResetLaborSearch(self):
        self.primary_labor_farm_strategy.ResetLaborSearch()
        self.primary_labor_factory_strategy.ResetLaborSearch()

    def SetMachineStrategy(self, variance_controls):
        self.machine_demand_strategy = strategies.MachineDemand(variance_controls)
        self.machine_supply_strategy = strategies.MachineSupply(variance_controls)
    
    def SetMachineValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, machine_quality_tiers, demanded_machines=1):
        self.machine_demand_strategy.SetMachineValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, machine_quality_tiers, demanded_machines)
        self.machine_supply_strategy.SetMachineValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function)

    def GetMachineSellers(self, machine_sellers):
        if self.GetMachineAmount() > 1:
            machine_sellers.append(self.id)
        return machine_sellers

    def BuyMachine(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, machine_quality_tiers, machine_sellers):
        if self['land'] > 0 and len(machine_sellers) > 0:
            self.machine_demand_strategy.SetMachineValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, machine_quality_tiers)
            temp_machine_sellers = copy.deepcopy(machine_sellers)
            if self.id in temp_machine_sellers:
                temp_machine_sellers.remove(self.id)
            if len(temp_machine_sellers) > 0:
                self.buy(('adult', random.choice(temp_machine_sellers)), good=f'machine_{self.machine_demand_strategy.preferred_machine_quality_tier}', quantity=1, price=self.machine_demand_strategy.machine_max_pay)

    def RecordBuyerWithMachineQuality(self, buyer_machine_qualities, buyer, machine_quality_for_tracker):
        if buyer not in buyer_machine_qualities:
            buyer_machine_qualities[buyer] = []
        buyer_machine_qualities[buyer].append(machine_quality_for_tracker)
        return buyer_machine_qualities

    def SolveBuyerMachineBids(self, buyer_machine_offers, machine_quality_tiers):
        buyer_machine_bids = {}
        for buyer in buyer_machine_offers:
            offer = buyer_machine_offers[buyer][0]
            buyer_machine_bids[buyer] = offer.price 
        return buyer_machine_bids

    def EvaluateBuyerMachineOffers(self, offer, machine_quality_tiers, machine_transaction_prices, buyer_machine_qualities, next_highest_bid, daily_food_consumption, days_to_yield):
        _,lowest_machine_quality_tier = offer.good.split('_')
        quality_tier_with_machines = self.GetQualityTierWithMachines()
        for i in range(int(lowest_machine_quality_tier),-1,-1):
            quality_value_adjustment = (machine_quality_tiers-i)/machine_quality_tiers
            seller_machine_value = 0
            if self['money'] > (daily_food_consumption.child*len(self.offspring) + daily_food_consumption.adult) * days_to_yield:
                seller_machine_value = self.machine_supply_strategy.new_machine_value*quality_value_adjustment
            if i in quality_tier_with_machines and quality_tier_with_machines[i] > 0 and offer.price > seller_machine_value:
                if seller_machine_value > next_highest_bid:
                    counteroffer_price = (offer.price+seller_machine_value)/2
                else:
                    counteroffer_price = (offer.price+next_highest_bid)/2
                machine_transaction_prices.append(counteroffer_price*machine_quality_tiers/(machine_quality_tiers-i))
                machine_quality_tracker_at_i = self.machine_quality_tracker[(self.machine_quality_tracker[0] > (machine_quality_tiers-1-i)/machine_quality_tiers) & (self.machine_quality_tracker[0] <= (machine_quality_tiers-i)/machine_quality_tiers)]
                self.machine_quality_tracker = self.machine_quality_tracker.drop(machine_quality_tracker_at_i.index[0]).reset_index(drop=True)
                buyer_machine_qualities = self.RecordBuyerWithMachineQuality(buyer_machine_qualities, offer.sender[1], machine_quality_tracker_at_i[0].min())
                self.sell(offer.sender, good=f'machine_{i}', quantity=1, price=counteroffer_price)
                break
        self.reject(offer)
        return machine_transaction_prices
    
    def SellMachine(self, machine_quality_tiers, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, machine_transaction_prices, buyer_machine_qualities):
        if self.GetMachineAmount() > 0:
            buyer_machine_offers = self.GetBuyerOffers()
            buyer_machine_bids = self.SolveBuyerMachineBids(buyer_machine_offers, machine_quality_tiers)
            buyer_machine_bids_descending = sorted(buyer_machine_bids, key=buyer_machine_bids.get, reverse=True)
            for buyer in buyer_machine_bids_descending:
                self.machine_supply_strategy.SetMachineValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function)
                next_highest_bid = 0
                if len(buyer_machine_bids_descending) > buyer_machine_bids_descending.index(buyer)+1:
                    next_highest_bid_buyer = buyer_machine_bids_descending[buyer_machine_bids_descending.index(buyer)+1]
                    next_highest_bid = buyer_machine_bids[next_highest_bid_buyer]
                machine_transaction_prices = self.EvaluateBuyerMachineOffers(buyer_machine_offers[buyer][0], machine_quality_tiers, machine_transaction_prices, buyer_machine_qualities, next_highest_bid, daily_food_consumption, days_to_yield)
        return machine_transaction_prices

    def AcceptMachineCounterOffer(self, buyer_machine_qualities):
        items_being_sold = []
        for item in self._open_offers_sell:
            items_being_sold.append(item)
        for item in items_being_sold:
            for offer in self.get_sell_offers(item):
                self.accept(offer)
        if self.id in buyer_machine_qualities:
            machine_qualities_for_tracker = pd.DataFrame(buyer_machine_qualities[self.id])
            self.machine_quality_tracker = self.machine_quality_tracker.append(machine_qualities_for_tracker, ignore_index=True)
    
    def AdjustMachineValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, variance_controls, machine_quality_tiers):
        self.machine_demand_strategy.AdjustMachineValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, variance_controls, machine_quality_tiers)
        self.machine_supply_strategy.AdjustMachineValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, variance_controls)

    def SetLandStrategies(self, variance_controls):
        self.land_demand_strategy = strategies.LandDemand(variance_controls)
        self.land_supply_strategy = strategies.LandSupply(variance_controls)

    
    def SolveExpectedYearsLandWillBeInFamily(self, children, death_probability_function):
        death_probability_threshold = 0.95
        oldest_age = self.age
        for i in self.offspring:
            offspring_object = children[i].ReturnSelf()[0][0]
            if offspring_object.age > oldest_age:
                oldest_age = offspring_object.age
        expected_years_in_family = death_probability_function.EstimatedDeathAge(death_probability_threshold, self.death_modifier) - oldest_age
        return expected_years_in_family
    
    def SetLandValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, year_length, death_probability_function, daily_food_consumption, depreciation_function, children, emergency_savings_length, land_demanded=1):
        expected_years_in_family = self.SolveExpectedYearsLandWillBeInFamily(children, death_probability_function)
        self.land_supply_strategy.SetLandValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, expected_years_in_family, year_length)
        self.land_demand_strategy.SetLandValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, year_length, daily_food_consumption, depreciation_function, expected_years_in_family, emergency_savings_length, land_demanded)
    
    def GetLandOwners(self, land_owners):
        if self['land'] > 0:
            land_owners.append(self.id)
        return land_owners

    def BuyLand(self, children, death_probability_function, production_function, capital_combination_function, asset_prices, days_to_yield, year_length, daily_food_consumption, depreciation_function, emergency_savings_length, land_owners):
        temp_land_owners = copy.deepcopy(land_owners)
        expected_years_in_family = self.SolveExpectedYearsLandWillBeInFamily(children, death_probability_function)
        self.land_demand_strategy.SetLandValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, year_length, daily_food_consumption, depreciation_function, expected_years_in_family, emergency_savings_length)
        if self.id in temp_land_owners:
            temp_land_owners.remove(self.id)
        self.buy(('adult', random.choice(temp_land_owners)), good='land', quantity=1, price=self.land_demand_strategy.land_value)
    
    def OrderLandBuyOffers(self):
        land_offers = {}
        buyer_land_bid = {}
        for offer in self.get_offers('land'):
            land_offers[offer.sender[1]] = offer
            buyer_land_bid[offer.sender[1]] = offer.price
        return land_offers,buyer_land_bid

    def SellLand(self, children, death_probability_function, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, year_length, land_transaction_prices):
        if self['land'] > 0:
            land_offers,buyer_land_bid = self.OrderLandBuyOffers()
            buyer_land_bids_descending = sorted(buyer_land_bid, key=buyer_land_bid.get, reverse=True)
            for buyer in buyer_land_bids_descending:
                offer = land_offers[buyer]
                next_highest_bid = 0
                if len(buyer_land_bids_descending) > buyer_land_bids_descending.index(buyer)+1:
                    next_highest_bid_buyer = buyer_land_bids_descending[buyer_land_bids_descending.index(buyer)+1]
                    next_highest_bid = buyer_land_bid[next_highest_bid_buyer]
                expected_years_in_family = self.SolveExpectedYearsLandWillBeInFamily(children, death_probability_function) 
                self.land_supply_strategy.SetLandValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, expected_years_in_family, year_length)
                if offer.price >= self.land_supply_strategy.land_value and self['land'] > 0:
                    if self.land_supply_strategy.land_value > next_highest_bid:
                        counteroffer_price = self.land_supply_strategy.land_value
                    else:
                        counteroffer_price = next_highest_bid
                    offer.price = (counteroffer_price + offer.price) / 2
                    land_transaction_prices.append(offer.price)
                    self.accept(offer)
                else: 
                    self.reject(offer)
        return land_transaction_prices

    def AdjustLandValue(self, children, death_probability_function, variance_controls, asset_prices, production_function, capital_combination_function, days_to_yield, year_length, daily_food_consumption, depreciation_function, emergency_savings_length):
        expected_years_in_family = self.SolveExpectedYearsLandWillBeInFamily(children, death_probability_function) 
        self.land_demand_strategy.AdjustLandValue(self, variance_controls, asset_prices, production_function, capital_combination_function, days_to_yield, year_length, daily_food_consumption, depreciation_function, expected_years_in_family, emergency_savings_length)
        self.land_supply_strategy.AdjustLandValue(self, variance_controls, asset_prices, capital_combination_function, days_to_yield, daily_food_consumption, depreciation_function, production_function, expected_years_in_family, year_length)

    def CheckBirthday(self, current_round, year_length):
        if current_round % year_length == self.birthday:
            self.age += 1

    def CheckDeathByOldAge(self, dead_adults, death_probability_function):
        if self.age >= 60:
            death_probability = death_probability_function.SolveDeathProbability(self.age, self.death_modifier)
            if random.uniform(0,1) <= death_probability and self.id not in dead_adults:
                dead_adults.append(self.id)
        return dead_adults

    def FindAdultRelatives(self, adult_relatives, adult_object):
        if self.family_name == adult_object.family_name and self.id != adult_object.id:
            if self.id not in adult_object.adult_offspring:
                adult_relatives.append(self)
        return adult_relatives

    def GetUnclaimedEstate(self, dead_adults, dead_children, unclaimed_estate, adult_relatives, unclaimed_machine_qualities):
        if len(self.adult_offspring) == 0 and (len(adult_relatives) == 0 or len(self.offspring) == 0):
            for i in self.offspring:
                dead_children.append(i)
            if self.GetMachineAmount() > 0:
                unclaimed_machine_qualities.extend(self.machine_quality_tracker[0].to_list())
            for i in self._inventory.haves:
                if i in unclaimed_estate:
                    unclaimed_estate[i] = unclaimed_estate[i] + self._inventory.haves[i]
                else:
                    unclaimed_estate[i] = self._inventory.haves[i]
        return dead_children, unclaimed_estate, unclaimed_machine_qualities

    def FindAssetsToAuction(self, dead_adults, dead_children, unclaimed_estate, adults, unclaimed_machine_qualities):
        adult_relatives = [] 
        if self.id in dead_adults:
            adults.FindAdultRelatives(adult_relatives, self)
            self.GetUnclaimedEstate(dead_adults, dead_children, unclaimed_estate, adult_relatives, unclaimed_machine_qualities)
        return dead_children,unclaimed_estate,unclaimed_machine_qualities

    def DivideInheritance(self, offspring_list, all_inheritances, machine_quality_tiers):
        machine_quality_tracker = self.machine_quality_tracker
        for offspring in offspring_list:
            inheritance = {}
            for item in self._inventory.haves:
                if item == 'money':
                    inheritance[item] = self._inventory.haves[item]/len(offspring_list)
                else:
                    remainder = self._inventory.haves[item]%len(offspring_list)
                    inheritance[item] = (self._inventory.haves[item]-remainder)/len(offspring_list)
                    oldest_to_youngest_agent = sorted(offspring_list)
                    if offspring in oldest_to_youngest_agent[:int(remainder)]:
                        inheritance[item] += 1
                    if 'machine' in item and self.GetMachineAmount() > 0:
                        current_machine_quality = int(item.split('_')[1])
                        machine_scores_at_current_quality = machine_quality_tracker[(machine_quality_tracker[0] > (machine_quality_tiers-1-current_machine_quality)/machine_quality_tiers) & (machine_quality_tracker[0] <= (machine_quality_tiers-current_machine_quality)/machine_quality_tiers)].sort_values(by=0, ascending=False)
                        claimed_machine_scores = machine_scores_at_current_quality.iloc[:int(inheritance[item])]
                        machine_quality_tracker = machine_quality_tracker.drop(claimed_machine_scores.index).reset_index(drop=True)
                        inheritance[f'{item}_quality_tracker'] = claimed_machine_scores
            all_inheritances[offspring] = inheritance
        return all_inheritances        
    
    def FindAssetsToPassDown(self, dead_adults, adults, children, all_inheritances, machine_quality_tiers):
        if self.id in dead_adults:
            if len(self.adult_offspring) > 0:
                all_inheritances = self.DivideInheritance(self.adult_offspring, all_inheritances, machine_quality_tiers)
            else:
                all_inheritances = self.DivideInheritance(self.offspring, all_inheritances, machine_quality_tiers)
        return all_inheritances

    def AssignFosterChildrenAsOffspring(self, children):
        foster_children = []
        children.ReturnChildObjectUsingAttribute('foster_parent', [self.id], foster_children)
        for i in foster_children:
            if i.id not in self.offspring:
                self.offspring.append(i.id)
    
    def InheritAssets(self, all_inheritances):
        if self.id in all_inheritances:
            for item in all_inheritances[self.id]:
                if 'quality_tracker' in item:
                    self.machine_quality_tracker = self.machine_quality_tracker.append(all_inheritances[self.id][item], ignore_index=True)
                else:
                    self.create(item, all_inheritances[self.id][item])
        for i in self.offspring:
            if i in all_inheritances:
                for item in all_inheritances[i]:
                    if 'quality_tracker' in item:
                        self.machine_quality_tracker = self.machine_quality_tracker.append(all_inheritances[i][item], ignore_index=True)
                    else:
                        self.create(item, all_inheritances[i][item])

    def PopulateAdultAndLandDemandValue(self, adult_and_land_demand_value):
        adult_and_land_demand_value[self.id] = self.land_demand_strategy.land_value
        return adult_and_land_demand_value
    
    def BuyUnclaimedLand(self, children, death_probability_function, production_function, capital_combination_function, asset_prices, days_to_yield, year_length, daily_food_consumption, depreciation_function, emergency_savings_length, auction_bundle):
        self.destroy('money', self.land_demand_strategy.land_value)
        self.create('land', auction_bundle)
        expected_years_in_family = self.SolveExpectedYearsLandWillBeInFamily(children, death_probability_function)
        self.land_demand_strategy.SetLandValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, year_length, daily_food_consumption, depreciation_function, expected_years_in_family, emergency_savings_length, auction_bundle)

    def PopulateAdultAndMachineDemandValue(self, machine_quality_tiers, adult_and_machine_demand_value, current_machine_quality):  
        machine_bid = self.machine_demand_strategy.machine_max_pay
        if self.machine_demand_strategy.preferred_machine_quality_tier < current_machine_quality:
            machine_bid = self.machine_demand_strategy.new_machine_value * (machine_quality_tiers-current_machine_quality)/machine_quality_tiers
        adult_and_machine_demand_value[self.id] = machine_bid
        return adult_and_machine_demand_value

    def BuyUnclaimedMachine(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, machine_quality_tiers, current_machine_quality, unclaimed_machine_qualities, auction_bundle):
        self.destroy('money', self.machine_demand_strategy.machine_max_pay)
        self.create(f'machine_{current_machine_quality}', auction_bundle)
        unclaimed_machine_qualities = pd.DataFrame(unclaimed_machine_qualities)
        machine_quality_scores_at_current_machine_quality = unclaimed_machine_qualities[(unclaimed_machine_qualities[0] > (machine_quality_tiers-1-current_machine_quality)/machine_quality_tiers) & (unclaimed_machine_qualities[0] <= (machine_quality_tiers-current_machine_quality)/machine_quality_tiers)]
        highest_machine_quality_score = machine_quality_scores_at_current_machine_quality.sort_values(by=0, ascending=True).iloc[:auction_bundle]
        unclaimed_machine_qualities = unclaimed_machine_qualities.drop(highest_machine_quality_score.index).reset_index(drop=True)
        self.machine_quality_tracker = self.machine_quality_tracker.append(highest_machine_quality_score, ignore_index=True)
        self.machine_demand_strategy.SetMachineValue(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, emergency_savings_length, depreciation_function, machine_quality_tiers, auction_bundle)  
        return unclaimed_machine_qualities

    def CalculateNetWorth(self, asset_prices, adult_networth, machine_quality_tiers):
        inventory_value = [self['money']]
        for i in self._inventory.haves:
            if i != 'money' and "labor_units" not in i and 'food' not in i and 'machine' not in i:
                inventory_value.append(self[i]*getattr(asset_prices, i))
            elif 'food' in i:
                inventory_value.append(self[i]*getattr(asset_prices, 'food'))
            elif 'machine' in i:
                machine_quality = int(i.split('_')[1])
                inventory_value.append(self[i]*getattr(asset_prices, 'machine')*((machine_quality_tiers-machine_quality)/machine_quality_tiers))
        adult_networth.append(self.id)
        adult_networth.append(sum(inventory_value))
        return adult_networth

    def DonateToCharity(self, charity_agents_remainder_map, donations):
        if self.id in charity_agents_remainder_map[:,0]:
            item_column = 1
            for i in donations:
                if i == 'money':
                    self.create(i, donations[i]/len(charity_agents_remainder_map))
                else:
                    self.create(i, donations[i]//len(charity_agents_remainder_map))
                    if charity_agents_remainder_map[np.where(charity_agents_remainder_map[:,0] == self.id)][0][item_column] == 1:
                        self.create(i, 1) 
                    item_column += 1

    def FulfillFarmLaborContract(self, alive_adults):
        if type(self.primary_labor_farm_strategy) is strategies.LaborSupply and type(self.primary_labor_farm_strategy.daily_labor_contract) is not int and self.primary_labor_farm_strategy.daily_labor_contract.sender[1] in alive_adults:
            self.create(self.primary_labor_farm_strategy.daily_labor_contract.good, self.primary_labor_farm_strategy.daily_labor_contract.quantity)
            self.sell(self.primary_labor_farm_strategy.daily_labor_contract.sender, self.primary_labor_farm_strategy.daily_labor_contract.good, self.primary_labor_farm_strategy.daily_labor_contract.quantity, self.primary_labor_farm_strategy.daily_labor_contract.price)
    
    def FulfillFactoryLaborContract(self, alive_adults):
        if type(self.primary_labor_factory_strategy) is strategies.LaborSupply and type(self.primary_labor_factory_strategy.daily_labor_contract) is not int and self.primary_labor_factory_strategy.daily_labor_contract.sender[1] in alive_adults:
            self.create(self.primary_labor_factory_strategy.daily_labor_contract.good, self.primary_labor_factory_strategy.daily_labor_contract.quantity)
            self.sell(self.primary_labor_factory_strategy.daily_labor_contract.sender, self.primary_labor_factory_strategy.daily_labor_contract.good, self.primary_labor_factory_strategy.daily_labor_contract.quantity, self.primary_labor_factory_strategy.daily_labor_contract.price)
    
    def AcceptFarmLaborContracts(self, service, days_to_yield):
        if type(self.primary_labor_farm_strategy) is strategies.LaborDemand:
            for offer in self.get_offers(service):
                if offer.price <= self['money']:
                    self.accept(offer)
                else:
                    self.reject(offer)
            for i in self.primary_labor_farm_strategy.offspring_productivity:
                self.create(service, self.primary_labor_farm_strategy.offspring_productivity[i]/days_to_yield)
    
    def AcceptFactoryLaborContracts(self, service, days_to_yield):
        if type(self.primary_labor_factory_strategy) is strategies.LaborDemand:
            for offer in self.get_offers(service):
                if offer.price <= self['money']:
                    self.accept(offer)
                else:
                    self.reject(offer)
            for i in self.primary_labor_factory_strategy.offspring_productivity:
                self.create(service, self.primary_labor_factory_strategy.offspring_productivity[i]/days_to_yield)
    
    def DepreciateMachines(self, depreciation_function):
        if self.GetMachineAmount() > 0:
            labor_unit_type = f'labor_units_{self.current_industry}'
            depreciation_amount = depreciation_function.SolveDepreciationAmount(self[labor_unit_type], self['land'])
            if len(self.machine_quality_tracker[self.machine_quality_tracker[0] < 1]) > 0:
                self.machine_quality_tracker[0] = self.machine_quality_tracker[self.machine_quality_tracker[0] < 1][0] - depreciation_amount
            if len(self.machine_quality_tracker[self.machine_quality_tracker[0] == 1]) > 0:
                self.machine_quality_tracker[0] = self.machine_quality_tracker[self.machine_quality_tracker[0] == 1][0] - 0.001

    def ProduceFood(self, production_function_farm, max_spoil_days, capital_combination_function, food_created):
        if type(self.primary_labor_farm_strategy) is strategies.LaborDemand and self.current_industry == 'farm':
            output = int(production_function_farm.ProduceOutput(self['labor_units_farm'], capital_combination_function.SolveRelationship(self.GetMachineAmount(), self['land']), self.industry_switch_penalty_output_multiplier))
            food_created.append(output)  
            self.create(f'food_{max_spoil_days}', output)
            self.destroy('labor_units_farm', self['labor_units_farm'])
            labor_cost = sum(self.primary_labor_farm_strategy.accepted_labor_units_and_cost[1][1:])
            if output > 0:
                self.primary_food_strategy.food_costs[max_spoil_days] = labor_cost/output
        return food_created
    
    def ProduceMachines(self, production_function_factory, capital_combination_function, machines_created):
        if type(self.primary_labor_factory_strategy) is strategies.LaborDemand and self.current_industry == 'factory':
            output = int(production_function_factory.ProduceOutput(self['labor_units_factory'], capital_combination_function.SolveRelationship(self.GetMachineAmount(), self['land']), self.industry_switch_penalty_output_multiplier))
            machines_created.append(output)
            self.machine_quality_tracker = self.machine_quality_tracker.append([1]*output, ignore_index=True)
            self.destroy('labor_units_factory', self['labor_units_factory'])
        return machines_created
    
    def AdjustMachineQualityTiers(self, machine_quality_tiers):
        for i in range(machine_quality_tiers):
            self.destroy(f'machine_{i}', self[f'machine_{i}'])
            machines_at_quality_i = len(self.machine_quality_tracker[(self.machine_quality_tracker[0] > (machine_quality_tiers-1-i)/machine_quality_tiers) & (self.machine_quality_tracker[0] <= (machine_quality_tiers-i)/machine_quality_tiers)])
            self.create(f'machine_{i}', machines_at_quality_i)

    def RemoveBrokenMachines(self, machine_quality_tiers, broken_machines):
        if self.GetMachineAmount() > 0:
            broken_machines.append(sum(self.machine_quality_tracker[0] <= 0))
            self.machine_quality_tracker = self.machine_quality_tracker[self.machine_quality_tracker[0] > 0]
            self.AdjustMachineQualityTiers(machine_quality_tiers)
            return broken_machines

    def CalculatePossibleProfits(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, industry_switch_penalty_function, total_land, total_machines):
        land_amount = 1
        if self['land'] > land_amount:
            land_amount = self['land']
        used_machine_amount = 0
        if not self.machine_quality_tracker.empty:
            used_machine_amount = sum(self.machine_quality_tracker[0] < 1)
        current_industry_holder = self.current_industry
        self.current_industry = 'farm'
        industry_switch_penalty_output_multiplier = 1
        if current_industry_holder == 'factory':
            industry_switch_penalty_output_multiplier = industry_switch_penalty_function.CalculateIndustrySwitchPenaltyOutputMultiplier(used_machine_amount, self['land'], total_land*total_machines)
        food_profit = self.land_demand_strategy.SolveYieldProfitEquation(production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, self, land_amount, industry_switch_penalty_output_multiplier)
        self.current_industry = 'factory'
        industry_switch_penalty_output_multiplier = 1
        if current_industry_holder == 'farm':
            industry_switch_penalty_output_multiplier = industry_switch_penalty_function.CalculateIndustrySwitchPenaltyOutputMultiplier(used_machine_amount, self['land'], total_land*total_machines)
        machine_profit = self.land_demand_strategy.SolveYieldProfitEquation(production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, self, land_amount, industry_switch_penalty_output_multiplier)
        self.current_industry = current_industry_holder
        return food_profit,machine_profit,industry_switch_penalty_output_multiplier

    def IncrementIndustrySwitchCounter(self, food_profit, machine_profit, industry_switch_threshold):
        if machine_profit > food_profit:
            if self.current_industry  == 'farm':
                self.industry_switch_counter += 1
            else:
                self.industry_switch_counter -= 1
        elif machine_profit < food_profit:
            if self.current_industry  == 'factory':
                self.industry_switch_counter += 1
            else:
                self.industry_switch_counter -= 1
        if self.industry_switch_counter < -industry_switch_threshold:
           self.industry_switch_counter = -industry_switch_threshold 
    
    def SwitchIndustry(self, industry_switch_penalty_output_multiplier):
        self.industry_switch_counter = 0
        self.industry_switch_penalty_output_multiplier = industry_switch_penalty_output_multiplier
        if self.current_industry == 'farm':
            self.current_industry = 'factory'
        else:
            self.current_industry = 'farm' 

    def ChooseProductionIndustry(self, production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, industry_switch_penalty_function, industry_switch_threshold, total_land, total_machines):
        self.industry_switch_penalty_output_multiplier = 1
        food_profit,machine_profit,industry_switch_penalty_output_multiplier = self.CalculatePossibleProfits(production_function, capital_combination_function, asset_prices, days_to_yield, daily_food_consumption, depreciation_function, industry_switch_penalty_function, total_land, total_machines)
        self.IncrementIndustrySwitchCounter(food_profit, machine_profit, industry_switch_threshold)
        if self.industry_switch_counter >= industry_switch_threshold:
            self.SwitchIndustry(industry_switch_penalty_output_multiplier)
    
    def ReturnProducerCurrentIndustries(self, producer_current_industries):
        if self.GetMachineAmount() > 0 and self['land'] > 0:
            producer_current_industries[self.current_industry].append(self.id)
        return producer_current_industries
    
    def CreateMinimumFarms(self):
        self.current_industry = 'farm'
        
    def GiftForGrowingChild(self, good, portion_for_growing_child, max_food_spoil_days=0, machine_quality_tiers=0):
        if good == 'food':
            gift = math.trunc(self.GetFoodAmount()*portion_for_growing_child[good])
            gift = self.GiftFood(gift, max_food_spoil_days)
        elif good == 'machine':
            gift = math.trunc(self.GetMachineAmount()*portion_for_growing_child[good])
            gift = self.GiftMachine(gift, machine_quality_tiers)
        else:
            gift = math.trunc(self[good]*portion_for_growing_child[good])
            self.destroy(good, gift)
        return gift

    def TransferMachineQualityScores(self, machine_gift_amount):
        self.machine_quality_tracker = self.machine_quality_tracker.sort_values(by=0, ascending=True)
        machine_quality_scores = self.machine_quality_tracker.iloc[:machine_gift_amount]
        self.machine_quality_tracker.iloc = self.machine_quality_tracker.iloc[machine_gift_amount:]
        return machine_quality_scores

    
    def GrowOffspring(self, child, grown_offspring):
        self.offspring.remove(child)
        self.adult_offspring.append(grown_offspring)
    
    def GetReproducingAdults(self, age_bounds, reproducing_adults):
        if self.age >= age_bounds.adult_lowerbound and self.age <= age_bounds.adult_upperbound:
            reproduction_roll = random.uniform(0,1)
            if reproduction_roll < self.reproduction_probability:
                reproducing_adults.append(self.id)
        return reproducing_adults
    
    def AdjustFoodCosts(self):
        self.primary_food_strategy.AdjustFoodCosts()
    
    def FeedFamily(self, spoil_with_food, food_deficit):
        for i in spoil_with_food:
            if spoil_with_food[i] > food_deficit:
               self.destroy(f'food_{i}', food_deficit)
               food_deficit = 0
            else:
                food_deficit -= spoil_with_food[i]
                self.destroy(f'food_{i}', self[f'food_{i}']) 
        return food_deficit 

    def MarkHungryAgents(self, hungry_agents, spoil_with_food, daily_food_consumption):
        total_food = sum(spoil_with_food.values())
        adult_meals = total_food/daily_food_consumption.adult
        offspring_food = total_food-daily_food_consumption.adult
        if adult_meals >= 1:
            offspring_meals = offspring_food/daily_food_consumption.child
            for i in self.offspring[round(offspring_meals):]:
                hungry_agents[('child',i)] = 1
            if (offspring_food%daily_food_consumption.child)/daily_food_consumption.child >= 0.5:
                hungry_agents[('child',self.offspring[math.trunc(offspring_meals)])] = 0
        else:
            if adult_meals >= 0.5:
                hungry_agents[('adult',self.id)] = 0
            else:
                hungry_agents[('adult',self.id)] = 1
            for i in self.offspring:
                hungry_agents[('child',i)] = 1
        return hungry_agents
    
    def Eat(self, daily_food_consumption, hungry_agents, eaten_food):
        family_daily_food_consumption = len(self.offspring)*daily_food_consumption.child + daily_food_consumption.adult
        food_deficit = family_daily_food_consumption
        spoil_with_food = self.GetSpoilWithFood()
        food_deficit = self.FeedFamily(spoil_with_food, food_deficit)
        if food_deficit > 0:
            hungry_agents = self.MarkHungryAgents(hungry_agents, spoil_with_food, daily_food_consumption)
        eaten_food.append(family_daily_food_consumption - food_deficit)
        return hungry_agents, eaten_food
    
    def RemoveDeadChildrenFromOffspring(self, dead_children):
        self.offspring = [i for i in self.offspring if i not in dead_children]

    def AdjustHunger(self, hungry_adults, hunger_level_max, dead_adults):
        if self.id in hungry_adults:
            self.hunger_level += hungry_adults[self.id]
        else:
            self.hunger_level -= 1
        if self.hunger_level < 0:
            self.hunger_level = 0 
        elif self.hunger_level > hunger_level_max and self.id not in dead_adults:
            dead_adults.append(self.id)
        return dead_adults
    
    def AgeFood(self):
        spoil_with_food = self.GetSpoilWithFood()
        for i in spoil_with_food:
            self.create(f'food_{i-1}', self[f'food_{i}'])
            self.destroy(f'food_{i}', self[f'food_{i}'])
    
    def SetWealthProportion(self, each_wealth_proportion):
        self.wealth_proportion = float(each_wealth_proportion[self.id])
    
    def DestroySpoiledFood(self, spoiled_food):
        if self['food_0'] > 0:
            spoiled_food.append(self['food_0'])
            self.destroy('food_0', self['food_0'])
        return spoiled_food
    
    def LABORshowme(self, a, b, c, current_round):
        a.append(current_round)
        b.append(self.primary_labor_farm_strategy.labor_unit_value)
        if self['land'] > 0:
            c.append('red')
        else:
            c.append('blue')
        return a,b,c
    
    def LANDshowme(self, land_logger, current_round):
        land_logger.LogLandTransaction(current_round, self.land_demand_strategy.land_value, 0)
        if self['land'] > 0:
            land_logger.LogLandTransaction(current_round, self.land_supply_strategy.land_value, 1)
    
    def CapitalShowme(self):
        land_amount = self['land']
        print(f'LAND:{land_amount}MACINE:{self.GetMachineAmount()}')


class Child(abcEconomics.Agent):
    def init(self, family_name, age, birthday, jobs_worked, price_history_memory, death_modifier, reproduction_probability=0, parent=None):
        if parent is None:
            parent = family_name
        self.family_name = family_name
        self.parent = parent
        self.age = age
        self.birthday = birthday
        self.inheritance = {}
        if random.randint(1,2) == 1:
            self.farm_jobs = 0
            self.factory_jobs = jobs_worked
        else:
            self.farm_jobs = jobs_worked
            self.factory_jobs = 0
        self.price_history_memory = price_history_memory
        self.death_modifier = death_modifier
        self.reproduction_probability = reproduction_probability
        self.hunger_level = 0

    def ReturnSelf(self):
        return self

    def SetInitialReproductionProbability(self, adults, age_bounds, variance_controls, year_length):
        parent_object = adults[self.parent].ReturnSelf()[0][0]
        possible_days_to_reproduce = (age_bounds.adult_upperbound-age_bounds.adult_lowerbound) * year_length
        self.reproduction_probability = (len(parent_object.offspring) / possible_days_to_reproduce) * random.uniform(variance_controls.default_lowerbound, variance_controls.default_upperbound)

    def ReturnChildObjectUsingAttribute(self, attribute, targets, agents):
        if getattr(self, attribute) in targets:
            agents.append(self)
        return agents

    def FindParents(self, adult_name, offspring):
        if self.family_name == adult_name:
            offspring.append(self.id)
        return offspring
    
    def IncrementFarmJobs(self, employed_children_farm):
        if self.id in employed_children_farm:
            self.farm_jobs += 1

    def IncrementFactoryJobs(self, employed_children_factory):
        if self.id in employed_children_factory:
            self.factory_jobs += 1

    def CheckBirthday(self, current_round, year_length):
        if current_round % year_length == self.birthday:
            self.age += 1
    
    def AssignFosterParent(self, adults):
        adult_family = []
        adults.ReturnAdultObjectUsingAttribute('family_name', [self.family_name], adult_family)
        adult_family_most_money = (0,0)
        for i in adult_family:
            if i['money'] > adult_family_most_money[1] or (i['money'] == adult_family_most_money[1] and i.id < adult_family_most_money[0]):
                adult_family_most_money = (i.id, i['money'])
        self.foster_parent = adult_family_most_money[0]
        
    def GetGrowingChildren(self, growing_children, adult_age_lowerbound):
        if self.age == adult_age_lowerbound:
            growing_children.append(self.id)
        return growing_children
    
    def AdjustHunger(self, hungry_children, hunger_level_max, dead_children):
        if self.id in hungry_children:
            self.hunger_level += hungry_children[self.id]
        else:
            self.hunger_level -= 1
        if self.hunger_level < 0:
            self.hunger_level = 0
        elif self.hunger_level > hunger_level_max and self.id not in dead_children:
            dead_children.append(self.id)
        return dead_children


