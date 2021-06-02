import random
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sympy as sym
import abcEconomics
from random import randint
from random import randrange
from numpy import mean
import agents
import log

import model_attributes


class MySimulation:
    def __init__(self, year_length, max_food_spoil_days, machine_quality_tiers, days_to_yield, initial_memory_range, hunger_level_max, daily_food_transactions, 
                    min_food_surplus, min_farm_proportion, min_farm_worker_proportion, max_blind_auction_rounds, start_params, age_bounds, variance_controls, production_farm, production_factory, capital_combination, death, portion_for_growing_child,
                     food_consumption, productivity, depreciation):
        self.year_length = year_length
        self.max_food_spoil_days = max_food_spoil_days
        self.machine_quality_tiers = machine_quality_tiers
        self.days_to_yield = days_to_yield
        self.initial_memory_range = initial_memory_range
        self.hunger_level_max = hunger_level_max
        self.daily_food_transactions = daily_food_transactions
        self.min_food_surplus = min_food_surplus
        self.min_farm_proportion = min_farm_proportion
        self.min_farm_worker_proportion = min_farm_worker_proportion
        self.max_blind_auction_rounds = max_blind_auction_rounds
        self.start_parameters = model_attributes.StartParameters(start_params)
        self.age_bounds = model_attributes.AgeBounds(age_bounds)
        self.variance_controls = model_attributes.VarianceControls(variance_controls)
        self.production_function = {'farm':model_attributes.CobbDouglasFunction(production_farm, self.variance_controls), 'factory':model_attributes.CobbDouglasFunction(production_factory, self.variance_controls)}
        self.capital_combination_function = model_attributes.GeneralInputRelationship(capital_combination)
        self.death_probability_function = model_attributes.DeathProbabilityFunction(death)
        self.portion_for_growing_child = portion_for_growing_child
        self.daily_food_consumption = model_attributes.DailyFoodConsumption(food_consumption)
        self.productivity_growth_function = model_attributes.ProductivityGrowthFunction(productivity) 
        self.depreciation_function = model_attributes.DepreciationFunction(depreciation)
        self.industry_switch_penalty_function = model_attributes.IndustrySwtichPenaltyFunction()
        self.total_food = self.start_parameters.food_start
        self.total_machines = self.start_parameters.machine_start
        self.total_land = self.start_parameters.landowner_start*self.start_parameters.landowner_land_start 
        self.current_year = 0
        self.adult_starvation_death = 0
        self.child_starvation_death = 0
        self.old_age_death = 0
        self.orphaned_death = 0
        self.asset_prices = model_attributes.AssetPrices()      
        self.emergency_savings_length = days_to_yield * 1.5

    def CreateInitialChildren(self, simulation):
        child_parameters = []
        for _ in range(self.start_parameters.children_start):
            age  = randint(self.age_bounds.child_lowerbound, self.age_bounds.child_upperbound)
            variance = random.uniform(0.7,1)
            possible_jobs_worked = round((age-self.age_bounds.child_upperbound)*(self.days_to_yield/self.year_length)*variance)
            if possible_jobs_worked < 0:
                possible_jobs_worked = 0
            child_parameters.append({'age':age, 'birthday':randint(0, self.year_length-1), 'family_name':randint(0,self.start_parameters.adults_start-1), 'jobs_worked':possible_jobs_worked, 'price_history_memory':randint(self.initial_memory_range[0],self.initial_memory_range[1]),'death_modifier':random.uniform(self.variance_controls.default_lowerbound, self.variance_controls.default_upperbound)})
        children = simulation.build_agents(agents.Child, 'child', agent_parameters=child_parameters)
        return children

    def GrowChildrenIntoAdults(self, adults, children, growing_children):
        adult_parameters = []
        for i in growing_children:
            child_object = children[i].ReturnSelf()[0][0]   
            machine_gift_amount = adults[child_object.parent].GiftForGrowingChild('machine', self.portion_for_growing_child, machine_quality_tiers=self.machine_quality_tiers)[0][0]                                    
            adult_parameters.append({'family_name':child_object.family_name, 'age':child_object.age, 'num_food':adults[child_object.parent].GiftForGrowingChild('food', self.portion_for_growing_child, max_food_days=self.max_food_spoil_days)[0][0],
                                    'num_money':adults[child_object.parent].GiftForGrowingChild('money', self.portion_for_growing_child)[0][0], 'num_land':adults[child_object.parent].GiftForGrowingChild('land', self.portion_for_growing_child)[0][0], 'num_machine':machine_gift_amount, 'birthday':child_object.birthday,'death_modifier':child_object.death_modifier,'offspring':[], 'farm_jobs':child_object.farm_jobs, 'factory_jobs':child_object.factory_jobs, 'price_history_memory':child_object.price_history_memory, 'industry_switch_counter':random.randint(-(self.variance_controls.industry_switch_threshold/2),self.variance_controls.industry_switch_threshold/2), 'machine_quality_tracker':adults[child_object.parent].TransferMachineQualityScores(machine_gift_amount)[0][0], 'reproduction_probability':child_object.reproduction_probability, 'parent':child_object.parent})
            grown_offspring = adults.create_agents(agents.Adult, adult_parameters)  
            adults[child_object.parent].GrowOffspring(child_object.id, grown_offspring)   
        growing_children = [('child',i) for i in growing_children]
        children.delete_agents(growing_children)
    
    def CreateChildren(self, adults, children, reproducing_adults, current_round):
        child_parameters = []
        for i in reproducing_adults:
            adult_object = adults[i].ReturnSelf()[0][0]
            child_parameters.append({'age':0, 'birthday':current_round % self.year_length, 'family_name':adult_object.family_name, 'jobs_worked':0, 'price_history_memory':round(adult_object.price_history_memory*random.uniform(self.variance_controls.default_lowerbound, self.variance_controls.default_upperbound)),'death_modifier':adult_object.death_modifier*random.uniform(self.variance_controls.default_lowerbound, self.variance_controls.default_upperbound), 'reproduction_probability':adult_object.reproduction_probability*random.uniform(self.variance_controls.default_lowerbound, self.variance_controls.default_upperbound), 'parent':adult_object.id})
            adult_object.offspring.append(children.create_agents(agents.Child, child_parameters))


    def CreateAdults(self, simulation, children):
        adult_parameters = []
        for i in range(self.start_parameters.adults_start):
            offspring=[]
            children.FindParents(i, offspring)
            age = randint(self.age_bounds.adult_lowerbound, self.age_bounds.adult_upperbound)
            machine_quality_tracker = pd.DataFrame()
            if i >= self.start_parameters.landowner_start:
                num_food = {self.max_food_spoil_days:round((self.start_parameters.food_start*(1-self.start_parameters.farm_food_bias)/self.start_parameters.nonfarm_agents_start)*random.uniform(self.variance_controls.default_lowerbound, self.variance_controls.default_upperbound), 0)}
                num_money = (self.start_parameters.money_start*(1-self.start_parameters.landowner_money_bias)/self.start_parameters.working_agents_start)*random.uniform(self.variance_controls.default_lowerbound, self.variance_controls.default_upperbound)
                num_land = 0
                num_machine = {0:0}
                current_industry = 'farm'
                # V probably do this different
                variance = random.uniform(0.7,1)
                possible_jobs_worked = round((age-self.age_bounds.child_upperbound)*(self.days_to_yield/self.year_length)*variance)
            elif i >= self.start_parameters.landowner_start*self.start_parameters.landowner_farm_bias:
                num_food = {self.max_food_spoil_days:round((self.start_parameters.food_start*(1-self.start_parameters.farm_food_bias)/self.start_parameters.nonfarm_agents_start)*random.uniform(self.variance_controls.default_lowerbound, self.variance_controls.default_upperbound), 0)}
                num_money = (self.start_parameters.money_start*(self.start_parameters.landowner_money_bias)/self.start_parameters.landowner_start)*random.uniform(self.variance_controls.default_lowerbound, self.variance_controls.default_upperbound)
                num_land = self.start_parameters.landowner_land_start
                num_machine = {0:round(self.start_parameters.machine_start*(self.start_parameters.factory_machine_bias) / self.start_parameters.landowner_start*self.start_parameters.landowner_farm_bias)}
                machine_quality_scores = [1]*num_machine[0]
                machine_quality_tracker = machine_quality_tracker.append(machine_quality_scores)
                current_industry = 'factory'
                variance = random.uniform(0.35,0.5)
                possible_jobs_worked = round((age-self.age_bounds.child_upperbound)*(self.days_to_yield/self.year_length)*variance)                
            else:
                num_food = {self.max_food_spoil_days:round((self.start_parameters.food_start*(self.start_parameters.farm_food_bias)/(self.start_parameters.landowner_start*self.start_parameters.landowner_farm_bias))*random.uniform(self.variance_controls.default_lowerbound, self.variance_controls.default_upperbound), 0)}
                num_money = (self.start_parameters.money_start*(self.start_parameters.landowner_money_bias)/self.start_parameters.landowner_start)*random.uniform(self.variance_controls.default_lowerbound, self.variance_controls.default_upperbound)
                num_land = self.start_parameters.landowner_land_start
                num_machine = {0:round(self.start_parameters.machine_start*(1-self.start_parameters.factory_machine_bias) / self.start_parameters.landowner_start*self.start_parameters.landowner_farm_bias)}
                machine_quality_scores = [1]*num_machine[0]
                machine_quality_tracker = machine_quality_tracker.append(machine_quality_scores)
                current_industry = 'farm'
                variance = random.uniform(0.35,0.5)
                possible_jobs_worked = round((age-self.age_bounds.child_upperbound)*(self.days_to_yield/self.year_length)*variance)
            for j in range(1, self.machine_quality_tiers):
                num_machine[j] = 0
            for j in range(1, self.max_food_spoil_days):
                num_food[j] = 0
            if random.randint(1,2) == 1:
                farm_jobs = 0
                factory_jobs = possible_jobs_worked
            else:
                farm_jobs = possible_jobs_worked
                factory_jobs = 0
            adult_parameters.append({'family_name':i, 'age':age, 'num_food':num_food, 'max_food_spoil_days':self.max_food_spoil_days, 'num_money':num_money, 
                                    'num_land':num_land, 'num_machine':num_machine, 'birthday':randint(1, self.year_length),'death_modifier':random.uniform(self.variance_controls.default_lowerbound, self.variance_controls.default_upperbound),'offspring':offspring, 
                                    'farm_jobs':farm_jobs, 'factory_jobs':factory_jobs, 'price_history_memory':randint(self.initial_memory_range[0],self.initial_memory_range[1]), 'industry_switch_counter':random.randint(-round(self.variance_controls.industry_switch_threshold/2),round(self.variance_controls.industry_switch_threshold/2)), 'machine_quality_tracker':machine_quality_tracker, 'current_industry':current_industry})
        adults = simulation.build_agents(agents.Adult, 'adult', agent_parameters=adult_parameters)
        children.SetInitialReproductionProbability(adults, self.age_bounds, self.variance_controls, self.year_length)
        return adults

    def FindFoodEquilibrium(self, rounds, simulation, adults):
        adults.SetFoodStrategy(self.max_food_spoil_days, self.daily_food_consumption)
        x = []
        y = []
        for i in range(rounds):
            current_round = i 
            food_transaction_prices = []
            all_buyer_seller_offer_difference = {}
            food_sellers_with_spoil_days = {}
            adults.SetInitialFoodValue(self.daily_food_consumption, self.days_to_yield, self.hunger_level_max, 0)
            adults.GetFoodSellersWithSpoilDays([], food_sellers_with_spoil_days)
            adults.BuyFood([],self.daily_food_consumption, self.days_to_yield, self.hunger_level_max, 0, food_sellers_with_spoil_days) 
            adults.SellFood(all_buyer_seller_offer_difference, self.daily_food_consumption, self.max_food_spoil_days, food_transaction_prices)
            adults.AcceptFoodCounterOffer()
            adults.MatchAgentToOfferRatio(all_buyer_seller_offer_difference)
            adults.AdjustFoodValue(self.hunger_level_max, self.variance_controls)
            adults.ResetReservedGoodsAndServices()
            for i in food_transaction_prices:
                x.append(current_round)
                y.append(i)
        self.asset_prices.SetFoodPrice(food_transaction_prices, -1, self.days_to_yield)
        return current_round


    
    def SellLaborUnits(self, adults, labor_force, max_labor_force, all_employed_agents):
        random.shuffle(labor_force)
        farm_workers = []
        no_limit_accepted_offers = {}
        for i in labor_force:
            adults.ReturnFarmWorkers(farm_workers)
            farm_only = 0
            if len(farm_workers) < math.ceil(max_labor_force*self.min_farm_worker_proportion):
                farm_only = 1
            adults[i].SellLaborUnits(adults, no_limit_accepted_offers, farm_only, self.days_to_yield, all_employed_agents)    
        return no_limit_accepted_offers, all_employed_agents

    def AdjustLaborUnitValue(self, adults, no_limit_accepted_offers):
        offered_values = {'labor_units_farm':[],'labor_units_factory':[]}
        demanded_labor_units = {'labor_units_farm':[],'labor_units_factory':[]}
        fulfilled_labor_units = {'labor_units_farm':[],'labor_units_factory':[]}
        adults.CheckLaborTransaction(offered_values, demanded_labor_units, fulfilled_labor_units, no_limit_accepted_offers)
        total_offered_value = {'labor_units_farm':sum(offered_values['labor_units_farm']),'labor_units_factory':sum(offered_values['labor_units_factory'])}
        total_demanded_labor_units = {'labor_units_farm':sum(demanded_labor_units['labor_units_farm']),'labor_units_factory':sum(offered_values['labor_units_factory'])}
        if total_demanded_labor_units['labor_units_farm'] == 0:
            total_demanded_labor_units['labor_units_farm'] = 1
        if total_demanded_labor_units['labor_units_factory'] == 0:
            total_demanded_labor_units['labor_units_factory'] = 1
        total_fulfilled_labor_units = {'labor_units_farm':sum(fulfilled_labor_units['labor_units_farm']),'labor_units_factory':sum(offered_values['labor_units_factory'])}
        percent_of_labor_units_fulfilled = {'labor_units_farm':total_fulfilled_labor_units['labor_units_farm']/total_demanded_labor_units['labor_units_farm'],'labor_units_factory':total_fulfilled_labor_units['labor_units_factory']/total_demanded_labor_units['labor_units_factory']}
        avg_offer = {'labor_units_farm':total_offered_value['labor_units_farm']/total_demanded_labor_units['labor_units_farm'],'labor_units_factory':total_offered_value['labor_units_factory']/total_demanded_labor_units['labor_units_factory']}
        new_labor_unit_asks = {'farm':[],'factory':[]}
        adults.AdjustLaborUnitSupplyValue(percent_of_labor_units_fulfilled, avg_offer, self.asset_prices, self.daily_food_consumption, self.productivity_growth_function, self.days_to_yield, new_labor_unit_asks)    
        for i in new_labor_unit_asks:
            if len(new_labor_unit_asks[i]) < 1:
                new_labor_unit_asks[i].append(0)
        lowest_labor_unit_ask = {'farm':min(new_labor_unit_asks['farm']),'factory':min(new_labor_unit_asks['factory'])}
        adults.AdjustLaborUnitDemandValue(self.asset_prices, self.production_function, self.capital_combination_function, self.productivity_growth_function, self.daily_food_consumption, self.max_food_spoil_days, lowest_labor_unit_ask, self.min_food_surplus)
    
    def PerformLaborTransaction(self, adults, max_labor_force, all_employed_agents):
        labor_force = []
        adults.GetLaborForce(labor_force)
        adults.BuyLaborUnits(labor_force)
        no_limit_accepted_offers,all_employed_agents = self.SellLaborUnits(adults, labor_force, max_labor_force, all_employed_agents)
        self.AdjustLaborUnitValue(adults, no_limit_accepted_offers)
        adults.ResetReservedGoodsAndServices()
        return labor_force, all_employed_agents
    
    def SetLaborUnitValue(self, adults):
        initial_labor_unit_asks = {'farm':[],'factory':[]}
        adults.SetLaborUnitSupplyValue(self.daily_food_consumption, self.asset_prices, self.days_to_yield, initial_labor_unit_asks)
        lowest_labor_unit_ask = {'farm':min(initial_labor_unit_asks['farm']),'factory':min(initial_labor_unit_asks['factory'])}
        adults.SetLaborUnitDemandValue(self.asset_prices, self.production_function, self.capital_combination_function, self.daily_food_consumption, self.max_food_spoil_days, lowest_labor_unit_ask, self.min_food_surplus)
    
    def FindLaborEquilibrium(self, simulation, children, adults, current_round):
        adults.SetInitialLaborStrategies(children, self.age_bounds.child_upperbound, self.productivity_growth_function)
        self.SetLaborUnitValue(adults)
        all_employed_agents = []
        labor_force = []
        adults.GetLaborForce(labor_force)
        max_labor_force = len(labor_force)
        employers_searching = [1]
        while len(labor_force) > 0:
            if sum(employers_searching) == 0 and len(labor_force) < max_labor_force:
                break
            current_round += 1
            employers_searching = []
            adults.CountEmployersSearching(employers_searching)
            labor_force,all_employed_agents = self.PerformLaborTransaction(adults, max_labor_force, all_employed_agents)
        employee_rates = {'labor_units_farm':[],'labor_units_factory':[]}
        adults.GetEmployeeRates(employee_rates)
        self.asset_prices.SetFarmLaborUnitPrice(-1, employee_rates['labor_units_farm'])
        self.asset_prices.SetFactoryLaborUnitPrice(-1, employee_rates['labor_units_factory'])
        return current_round

    def PerformMachineTransactions(self, adults):
        adults.SetMachineValue(self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.daily_food_consumption, self.emergency_savings_length, self.depreciation_function, self.machine_quality_tiers)
        machine_sellers = []
        adults.GetMachineSellers(machine_sellers)
        adults.BuyMachine(self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.daily_food_consumption, self.emergency_savings_length, self.depreciation_function, self.machine_quality_tiers, machine_sellers)
        machine_transaction_prices = []
        buyer_machine_qualities = {}
        adults.SellMachine(self.machine_quality_tiers, self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.daily_food_consumption, self.emergency_savings_length, self.depreciation_function, machine_transaction_prices, buyer_machine_qualities)
        adults.AcceptMachineCounterOffer(buyer_machine_qualities)
        adults.AdjustMachineValue(self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.daily_food_consumption, self.emergency_savings_length, self.depreciation_function, self.variance_controls, self.machine_quality_tiers)
        adults.ResetReservedGoodsAndServices()
        return machine_transaction_prices
    
    def FindMachineEquilibrium(self, rounds, simulation, adults, current_round):
        adults.SetMachineStrategy(self.variance_controls)
        for _ in range(rounds):
            current_round += 1
            machine_transaction_prices = self.PerformMachineTransactions(adults)
        self.asset_prices.SetMachinePrice(-1, machine_transaction_prices)
        return current_round
    
    def PerformLandTransactions(self, adults, children):
        land_owners = []
        adults.GetLandOwners(land_owners)
        adults.BuyLand(children, self.death_probability_function, self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.year_length, self.daily_food_consumption, self.depreciation_function, self.emergency_savings_length, land_owners)
        land_transaction_prices = []
        adults.SellLand(children, self.death_probability_function, self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.daily_food_consumption, self.depreciation_function, self.year_length, land_transaction_prices)
        adults.AdjustLandValue(children, self.death_probability_function, self.variance_controls, self.asset_prices, self.production_function, self.capital_combination_function, self.days_to_yield, self.year_length, self.daily_food_consumption, self.depreciation_function, self.emergency_savings_length)  
        adults.ResetReservedGoodsAndServices()
        return land_transaction_prices

    def FindLandEquilibrium(self, rounds, simulation, adults, current_round, children):
        adults.SetLandStrategies(self.variance_controls)
        adults.SetLandValue(self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.year_length, self.death_probability_function, self.daily_food_consumption, self.depreciation_function, children, self.emergency_savings_length)
        for _ in range(rounds):
            current_round += 1
            land_transaction_prices = self.PerformLandTransactions(adults, children)
        self.asset_prices.SetLandPrice(-1, land_transaction_prices)
        return current_round


    def HasYearPassed(self, current_round):
        if current_round % self.year_length == 0:
            self.current_year = self.current_year + 1

    def CalculateBundleSize(self, good_amount):
        bundle_size = 1
        if good_amount > self.max_blind_auction_rounds:
            bundle_size = round(good_amount/self.max_blind_auction_rounds)
        return int(bundle_size)

    def RunBlindLandAuction(self, adults, children, unclaimed_estate, donations):
        temp = unclaimed_estate.pop('land')
        unclaimed_land = temp
        bundle_size = self.CalculateBundleSize(unclaimed_land)
        adults.SetLandValue(self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.year_length, self.death_probability_function, self.daily_food_consumption, self.depreciation_function, children, self.emergency_savings_length, bundle_size)
        while unclaimed_land > 0:
            print(unclaimed_land)
            auction_bundle = bundle_size
            if bundle_size > unclaimed_land:
                auction_bundle = int(unclaimed_land)
                adults.SetLandValue(self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.year_length, self.death_probability_function, self.daily_food_consumption, self.depreciation_function, children, self.emergency_savings_length, auction_bundle)
            adult_and_land_demand_value = {}
            adults.PopulateAdultAndLandDemandValue(adult_and_land_demand_value)
            adult_descending_by_land_demand_value = sorted(adult_and_land_demand_value, key=adult_and_land_demand_value.get, reverse=True) 
            adult_with_highest_land_demand_value = adult_descending_by_land_demand_value[0]
            adults[adult_with_highest_land_demand_value].BuyUnclaimedLand(children, self.death_probability_function, self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.year_length, self.daily_food_consumption, self.depreciation_function, self.emergency_savings_length, auction_bundle)
            donations['money'] += adult_and_land_demand_value[adult_with_highest_land_demand_value]
            unclaimed_land -= bundle_size
        return unclaimed_estate,donations    

    def RunBlindMachineAuction(self, adults, unclaimed_estate, donations, unclaimed_machine_qualities):
        for i in range(self.machine_quality_tiers):
            unclaimed_machine = unclaimed_estate.pop(f'machine_{i}')
            bundle_size = self.CalculateBundleSize(unclaimed_machine)
            adults.SetMachineValue(self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.daily_food_consumption, self.emergency_savings_length, self.depreciation_function, self.machine_quality_tiers, bundle_size)
            while unclaimed_machine > 0:
                print(unclaimed_machine)
                auction_bundle = bundle_size
                if bundle_size > unclaimed_machine:
                    auction_bundle = int(unclaimed_machine)
                    adults.SetMachineValue(self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.daily_food_consumption, self.emergency_savings_length, self.depreciation_function, self.machine_quality_tiers, auction_bundle)
                adult_and_machine_demand_value = {}
                adults.PopulateAdultAndMachineDemandValue(self.machine_quality_tiers, adult_and_machine_demand_value, i)
                adult_descending_by_machine_demand_value = sorted(adult_and_machine_demand_value, key=adult_and_machine_demand_value.get, reverse=True)
                adult_with_highest_machine_demand_value = adult_descending_by_machine_demand_value[0] 
                adults[adult_with_highest_machine_demand_value].BuyUnclaimedMachine(self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.daily_food_consumption, self.emergency_savings_length, self.depreciation_function, self.machine_quality_tiers, i, unclaimed_machine_qualities, auction_bundle)
                donations['money'] += adult_and_machine_demand_value[adult_with_highest_machine_demand_value]
                unclaimed_machine -= bundle_size
        return unclaimed_estate,donations

    def FindCharityAgents(self, adults):
        adult_networth = []
        adults.CalculateNetWorth(self.asset_prices, adult_networth, self.machine_quality_tiers)
        adult_networth = np.array(adult_networth).reshape(-1,2)
        adult_networth = sorted(adult_networth, key=lambda x: x[1], reverse=True)
        charity_size_multiplier = 0.1
        num_charity_agents = round(len(adult_networth) * charity_size_multiplier)    
        charity_agents = adult_networth[-num_charity_agents:]
        charity_agents = np.array(charity_agents)  
        return charity_agents     
    
    def GetAssetRemainders(self, unclaimed_estate, num_charity_agents):
        asset_remainders = {}
        for j in unclaimed_estate:
            asset_remainders[j] = unclaimed_estate[j]%num_charity_agents
        return asset_remainders

    def InitializeCharityAgentsRemainderMap(self, charity_agents, unclaimed_estate):
        charity_agents[:,1] = 1
        if len(unclaimed_estate) > 1:
            columns_to_add = np.ones((len(charity_agents),(len(unclaimed_estate) - 1))) # -1 is because there will always be 2 columns to start
            charity_agents_remainder_map = np.hstack((charity_agents,columns_to_add))  
        return charity_agents_remainder_map
    
    def MapCharityAgentsWithRemainders(self, charity_agents_remainder_map, asset_remainders):
        column = 1
        for j in asset_remainders:               
            charity_agents_remainder_map[int(asset_remainders[j]):,column] = 0
            column += 1      
        return charity_agents_remainder_map  

    def CreateCharityAgentRemainderMap(self, charity_agents, unclaimed_estate):
        asset_remainders = self.GetAssetRemainders(unclaimed_estate, len(charity_agents))
        charity_agents_remainder_map = self.InitializeCharityAgentsRemainderMap(charity_agents, unclaimed_estate)    
        charity_agents_remainder_map = self.MapCharityAgentsWithRemainders(charity_agents_remainder_map, asset_remainders)
        return charity_agents_remainder_map
    
    def IncrementJobsForWorkingAgents(self, adults, children, all_employed_agents):
        employed_adults_farm = []
        employed_adults_factory = []
        employed_children_farm = []
        employed_children_factory = []
        for j in all_employed_agents:
            if j[0] == 'adult':
                if j[2] == 'farm':
                    employed_adults_farm.append(j[1])
                else:
                    employed_adults_factory.append(j[1])
            elif j[0] == 'child':
                if j[2] == 'farm':
                    employed_children_farm.append(j[1])
                else:
                    employed_children_factory.append(j[1])
        adults.IncrementFarmJobs(employed_adults_farm)
        adults.IncrementFactoryJobs(employed_adults_factory)
        children.IncrementFarmJobs(employed_children_farm)
        children.IncrementFactoryJobs(employed_children_factory)
    
    def RunLaborMarket(self, adults, current_round):
        adults.ResetLaborSearch()
        self.SetLaborUnitValue(adults)
        labor_force = []
        adults.GetLaborForce(labor_force)
        max_labor_force = len(labor_force)
        employers_searching = [1]
        all_employed_agents = []
        while len(labor_force) > 0 and sum(employers_searching) > 0:
            employers_searching = []
            adults.CountEmployersSearching(employers_searching)
            labor_force,all_employed_agents = self.PerformLaborTransaction(adults, max_labor_force, all_employed_agents)
        employer_rates = {'labor_units_farm':[],'labor_units_factory':[]}
        adults.GetEmployeeRates(employer_rates)
        self.asset_prices.SetFarmLaborUnitPrice(current_round, employer_rates['labor_units_farm'])
        self.asset_prices.SetFactoryLaborUnitPrice(current_round, employer_rates['labor_units_factory'])
        adults.IncludeLandOwnerChildrenInLabor(all_employed_agents)
        return all_employed_agents
    
    def RunFoodMarket(self, adults, dead_adults, current_round):
        adults.ResetFoodStrategies(current_round, self.days_to_yield, self.max_food_spoil_days, self.daily_food_consumption)
        all_buyer_seller_offer_difference = {}
        food_sellers_with_spoil_days = {}
        adults.SetInitialFoodValue(self.daily_food_consumption, self.days_to_yield, self.hunger_level_max, current_round)
        adults.GetFoodSellersWithSpoilDays(dead_adults, food_sellers_with_spoil_days)
        food_transaction_prices = []
        for _ in range(self.daily_food_transactions):
            adults.BuyFood(dead_adults, self.daily_food_consumption, self.days_to_yield, self.hunger_level_max, current_round, food_sellers_with_spoil_days) 
            adults.SellFood(all_buyer_seller_offer_difference, self.daily_food_consumption, self.max_food_spoil_days, food_transaction_prices)
            adults.AcceptFoodCounterOffer()
            adults.ResetReservedGoodsAndServices()
        adults.MatchAgentToOfferRatio(all_buyer_seller_offer_difference)
        adults.AdjustFoodValue(self.hunger_level_max, self.variance_controls)
        self.asset_prices.SetFoodPrice(food_transaction_prices, current_round, self.days_to_yield)
        
    
    def Eat(self, adults, children, dead_adults, dead_children):
        hungry_agents = {}
        hungry_adults = {}
        hungry_children = {}
        eaten_food = []
        adults.Eat(self.daily_food_consumption, hungry_agents, eaten_food)
        self.total_food -= sum(eaten_food)
        for j in hungry_agents:
            if j[0] == 'adult':
                hungry_adults[j[1]] = hungry_agents[j]
            elif j[0] == 'child':
                hungry_children[j[1]] = hungry_agents[j]
        previous_dead_adults = len(dead_adults)
        previous_dead_children = len(dead_children)
        adults.AdjustHunger(hungry_adults, self.hunger_level_max, dead_adults)
        children.AdjustHunger(hungry_children, self.hunger_level_max, dead_children)
        self.adult_starvation_death += len(dead_adults) - previous_dead_adults
        self.child_starvation_death += len(dead_children) - previous_dead_children

    def GrowAgents(self, adults, children, current_round, dead_children, dead_adults):
        adults.CheckBirthday(current_round, self.year_length)
        children.CheckBirthday(current_round, self.year_length)
        growing_children = []
        children.GetGrowingChildren(growing_children, self.age_bounds.adult_lowerbound)
        growing_children = [i for i in growing_children if i not in dead_children]
        self.GrowChildrenIntoAdults(adults, children, growing_children)
        previous_dead = len(dead_adults)
        adults.CheckDeathByOldAge(dead_adults, self.death_probability_function)
        self.old_age_death += len(dead_adults) - previous_dead
        return dead_adults
    
    def ClaimAssets(self, unclaimed_estate, all_inheritances):
        for offspring in all_inheritances:
            for asset in all_inheritances[offspring]:
                if asset in unclaimed_estate:
                    unclaimed_estate[asset] -= unclaimed_estate[asset]
        return unclaimed_estate

    def ResolveFinalAffairs(self, adults, children, dead_adults, dead_children):
        unclaimed_estate = {}
        all_inheritances = {}
        unclaimed_machine_qualities = []
        previous_dead_children = len(dead_children)
        adults.FindAssetsToAuction(dead_adults, dead_children, unclaimed_estate, adults, unclaimed_machine_qualities)
        self.orphaned_death += len(dead_children) - previous_dead_children
        adults.FindAssetsToPassDown(dead_adults, adults, children, all_inheritances, self.machine_quality_tiers)
        unclaimed_estate = self.ClaimAssets(unclaimed_estate, all_inheritances)
        adults.RemoveDeadChildrenFromOffspring(dead_children)
        dead_adults = list(dict.fromkeys(dead_adults))
        dead_children = list(dict.fromkeys(dead_children))
        dead_adults = [('adult',j) for j in dead_adults]
        dead_children = [('child',j) for j in dead_children]
        adults.delete_agents(dead_adults)
        children.delete_agents(dead_children)
        children.AssignFosterParent(adults)
        adults.AssignFosterChildrenAsOffspring(children)
        adults.InheritAssets(all_inheritances)
        if len(dead_adults) > 0:  
            donations = {}
            donations['money'] = unclaimed_estate.pop('money')
            unclaimed_estate, donations = self.RunBlindLandAuction(adults, children, unclaimed_estate, donations)
            unclaimed_estate, donations = self.RunBlindMachineAuction(adults, unclaimed_estate, donations, unclaimed_machine_qualities)
            charity_agents = self.FindCharityAgents(adults)
            charity_agents_remainder_map = self.CreateCharityAgentRemainderMap(charity_agents, unclaimed_estate)
            donations.update(unclaimed_estate)
            adults.DonateToCharity(charity_agents_remainder_map, donations)
    
    def ProduceFood(self, adults):
        food_created = []
        adults.ProduceFood(self.production_function['farm'], self.max_food_spoil_days, self.capital_combination_function, food_created)
        self.total_food += sum(food_created)
    
    def ProduceMachines(self, adults):
        machines_created = []
        adults.ProduceMachines(self.production_function['factory'], self.capital_combination_function, machines_created)
        self.total_machines += sum(machines_created)

    def RemoveBrokenMachines(self, adults):
        broken_machines = []
        adults.RemoveBrokenMachines(self.machine_quality_tiers, broken_machines)
        self.total_machines -= sum(broken_machines)

    def ChooseCurrentIndustry(self, adults):
        adults.ChooseProductionIndustry(self.production_function, self.capital_combination_function, self.asset_prices, self.days_to_yield, self.daily_food_consumption, self.depreciation_function, self.industry_switch_penalty_function, self.variance_controls.industry_switch_threshold, self.total_land, self.total_machines)
        producer_current_industries = {'farm':[],'factory':[]}
        adults.ReturnProducerCurrentIndustries(producer_current_industries)
        min_farms = math.ceil((len(producer_current_industries['farm']) + len(producer_current_industries['factory']))*self.min_farm_proportion)
        needed_farms = min_farms - len(producer_current_industries['farm'])
        random.shuffle(producer_current_industries['factory'])
        for i in range(int(needed_farms)):
            adults[producer_current_industries['factory'][i]].CreateMinimumFarms()

    def InitializeLaborMarket(self, adults, children, all_employed_agents):
        self.IncrementJobsForWorkingAgents(adults, children, all_employed_agents)
        adults.ResetLaborStrategies(children, self.age_bounds.child_upperbound, self.production_function, self.asset_prices, self.productivity_growth_function, self.daily_food_consumption, self.max_food_spoil_days, self.min_food_surplus)

    def SpoilFood(self, adults):
        adults.AgeFood()
        adults.AdjustFoodCosts()
        spoiled_food = []
        adults.DestroySpoiledFood(spoiled_food)
        self.total_food -= sum(spoiled_food)
    
    def SetAdultWealthProportion(self, adults):
        adult_networth = []
        each_wealth_proportion = {}
        adults.CalculateNetWorth(self.asset_prices, adult_networth, self.machine_quality_tiers)
        adult_networth = np.array(adult_networth).reshape(-1,2)
        adult_networth = sorted(adult_networth, key=lambda x: x[1], reverse=True)
        adult_networth = np.array(adult_networth)
        total_wealth = sum(adult_networth[:,1])
        for i in adult_networth:
            each_wealth_proportion[i[0]] = i[1]/total_wealth
        adults.SetWealthProportion(each_wealth_proportion)

    def Work(self, adults, dead_adults):
        alive_adults = []
        adults.GetAllAliveAdults(dead_adults, alive_adults)
        adults.FulfillFarmLaborContract(alive_adults)
        adults.FulfillFactoryLaborContract(alive_adults)
        adults.AcceptFarmLaborContracts('labor_units_farm', self.days_to_yield)
        adults.AcceptFactoryLaborContracts('labor_units_factory', self.days_to_yield)
    
    def Reproduce(self, adults, children, current_round):
        reproducing_adults = []
        adults.GetReproducingAdults(self.age_bounds, reproducing_adults)
        self.CreateChildren(adults, children, reproducing_adults, current_round)

    def MainSimulation(self, simulation, adults, children, rounds, current_round=0):
        all_employed_agents = []
        dead_adults = []
        dead_children = []
        for _ in range(rounds):
            simulation.advance_round(current_round)
            print(f'CURRENT_ROUND:{current_round} ADULTS ALIVE:{len(adults)} DEAD BY STARVATION ADULTS:{self.adult_starvation_death} CHILDREN:{self.child_starvation_death} OLD AGE:{self.old_age_death} ORPHANED:{self.orphaned_death}' )
            if len(dead_adults) == len(adults):
                print('All adults have died')
                break
            self.HasYearPassed(current_round)
            dead_adults = self.GrowAgents(adults, children, current_round, dead_children, dead_adults)
            if current_round % self.days_to_yield == 0:
                self.ResolveFinalAffairs(adults, children, dead_adults, dead_children)
                dead_adults = []
                dead_children = []
                adults.DepreciateMachines(self.depreciation_function)
                self.ProduceFood(adults)
                self.ProduceMachines(adults)
                self.RemoveBrokenMachines(adults)
                self.ChooseCurrentIndustry(adults)
                land_transaction_prices = self.PerformLandTransactions(adults, children)
                self.asset_prices.SetLandPrice(current_round, land_transaction_prices)
                machine_transaction_prices = self.PerformMachineTransactions(adults)
                self.asset_prices.SetMachinePrice(current_round, machine_transaction_prices)
                self.InitializeLaborMarket(adults, children, all_employed_agents)
                all_employed_agents = self.RunLaborMarket(adults, current_round)
            self.Work(adults, dead_adults)
            self.RunFoodMarket(adults, dead_adults, current_round)
            self.Eat(adults, children, dead_adults, dead_children)
            self.SpoilFood(adults)
            self.Reproduce(adults, children, current_round)
            self.SetAdultWealthProportion(adults)
            get_good = []
            for g in range(1,self.max_food_spoil_days+1):
                get_good.append(f'food_{g}')
            for g in range(self.machine_quality_tiers):
                get_good.append(f'machine_{g}')
            get_good.append('land')
            get_good.append('money')
            adults.panel_log(variables = ['wealth_proportion'], goods=get_good)
            current_round += 1