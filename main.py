
import random
from random import randint, randrange

import abcEconomics
from matplotlib import pyplot as plt
from numpy import mean

import model
import log

year_length = 300
max_food_spoil_days = 30
machine_quality_tiers = 4
days_to_yield = 30
initial_memory_range = [5,20]
hunger_level_max = 10
daily_food_transactions = 30
min_food_surplus = 1.5
min_farm_proportion = 0.1
min_farm_worker_proportion = 0.1
max_blind_auction_rounds = 1500

start_params = {
        'adults_start':100,
        'children_start':180,
        'food_start':50000,
        'money_start':7500000,
        'machine_start':100000, 
        'landowner_start':20,
        'landowner_farm_bias':0.5,
        'farm_food_bias':1,
        'factory_machine_bias':0.8,
        'landowner_money_bias':0.25,
        'landowner_land_start':15,
        }

age_bounds = {
        'adult_lowerbound':18,
        'adult_upperbound':50,
        'child_lowerbound':3,
        'child_upperbound':13
        }

variance_controls = {
        'food_lowerbound':0.05,
        'food_upperbound':0.15,
        'land_lowerbound':0.1,
        'land_upperbound':0.3,  
        'default_lowerbound':0.75,
        'default_upperbound':1.25,
        'transaction_food_reaction':5,
        'industry_switch_threshold':5
        }

production_farm = {
        'alpha':3/4,
        'beta':1/4,
        'output_multiplier':100,
        }

production_factory = {
        'alpha':3/4,
        'beta':1/4,
        'output_multiplier':10,
        }

capital_combination = {
        'alpha':1/4,
        'beta':3/4,
        'output_multiplier':1
        }

death = {
        'm':1/7776000000,
        'x_intercept':-24,
        'exp':5.
        }

portion_for_growing_child = {
        'food':0.1,
        'money':0.1,
        'land':0,
        'machine':0
        }

food_consumption = {
        'adult':2,
        'child':1
        }

productivity = {
        'exp':0.5,
        'y_intercept':5
        }

depreciation = {
        'idle_depreciation_max_cycles':10,
        'active_depreciation_adjuster':1/500,
        'active_depreciation_exp':1/2
        }



print('Initializing Simulation Please Wait')
simulation = abcEconomics.Simulation()
LatestSim = model.MySimulation(year_length, max_food_spoil_days, machine_quality_tiers, days_to_yield, initial_memory_range, hunger_level_max, daily_food_transactions, 
                                min_food_surplus, min_farm_proportion, min_farm_worker_proportion, max_blind_auction_rounds, start_params, age_bounds, variance_controls, production_farm, production_factory, capital_combination, death, portion_for_growing_child, 
                                food_consumption, productivity, depreciation)
children = LatestSim.CreateInitialChildren(simulation)
adults = LatestSim.CreateAdults(simulation, children)
current_round = LatestSim.FindFoodEquilibrium(25, simulation, adults)
current_round = LatestSim.FindLaborEquilibrium(simulation, children, adults, current_round)
current_round = LatestSim.FindLandEquilibrium(1, simulation, adults, current_round, children)
current_round = LatestSim.FindMachineEquilibrium(1, simulation, adults, current_round)
rounds = 200
print('Begin Main Simulation')
LatestSim.MainSimulation(simulation, adults, children, rounds)
simulation.finalize()
print('done')
