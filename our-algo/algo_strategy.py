import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):

    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))
        
    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global FILTER, ENCRYPTOR, DESTRUCTOR, PING, EMP, SCRAMBLER
        FILTER = config["unitInformation"][0]["shorthand"]
        ENCRYPTOR = config["unitInformation"][1]["shorthand"]
        DESTRUCTOR = config["unitInformation"][2]["shorthand"]
        PING = config["unitInformation"][3]["shorthand"]
        EMP = config["unitInformation"][4]["shorthand"]
        SCRAMBLER = config["unitInformation"][5]["shorthand"]
        # This is a good place to do initial setup
        self.scored_on_locations = [] 
        global row13, row12
        row12 = [[1, 12], [2, 12], [3, 12], [4, 12], [5, 12], [6, 12], [7, 12], [8, 12], [9, 12], [10, 12], [11, 12], [16, 12], [17, 12], [18, 12], [19, 12], [20, 12], [21, 12], [22, 12], [23, 12], [24, 12], [25, 12], [26, 12]]
        row13 = [[0, 13], [1, 13], [2, 13], [3, 13], [4, 13], [5, 13], [6, 13], [7, 13], [8, 13], [9, 13], [10, 13], [11, 13], [12, 13], [15, 13], [16, 13], [17, 13], [18, 13], [19, 13], [20, 13], [21, 13], [22, 13], [23, 13], [24, 13], [25, 13], [26, 13], [27, 13]]

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """
    

    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some Scramblers early on.
        We will place destructors near locations the opponent managed to score on.
        For offense we will use long range EMPs if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Pings to try and score quickly.
        """
        self.static_defense(game_state)
        self.general_attack_strategy(game_state)
        
    def first_strike(self, game_state):
        # Get the damage estimate each path will take
        damages = []
        for location in game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT):
            path = game_state.find_path_to_edge(location)
            damage = 0
            if path is None:
                return
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(DESTRUCTOR, game_state.config).damage
                # TODO: Get number of shields to subtract!!!!
            damages.append(damage)
        
        if (min(damages) == 0):
            game_state.attempt_spawn(PING, game_state.game_map.BOTTOM_LEFT(damages.index(min(damages))), 10000)
            return
        
        damages = []
        for location in game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT):
            path = game_state.find_path_to_edge(location)
            damage = 0
            if path is None:
                return
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(DESTRUCTOR, game_state.config).damage
                # TODO: Get number of shields to subtract!!!!
            damages.append(damage)

        if (min(damages) == 0):
            game_state.attempt_spawn(PING, game_state.game_map.BOTTOM_RIGHT(damages.index(min(damages))), 10000)
            return


    def general_attack_strategy(self, game_state):
        '''
        Ultimately, we are trying an attack down the middle.
        1) Build lines on both sides
          - This enables us 4 attack points (2 release and 2 gates)
                - We should check which of these 4 attack points is blocked
                    - Check to see if it the blocker is strong (like a filter) or weak
                - Check which of these attack points causes damage to encryptors
        2) Send attack for best line
        '''
        release_locations = [[15, 1], [12, 1]] # these locations are for before corners are blocked
        blocked_release_locations = [[2, 11], [25, 11]] # these locations are for after corners are blocked
        
        if (1 <= game_state.turn_number <= 2):
            # do an analysis and attack
            self.first_strike(game_state)

        min_size_of_attack = 10 # the number of minimum pings we want to send
        next_turn_to_increment = 20
        if (game_state.turn_number % next_turn_to_increment == 0 and game_state.turn_number != 0):
            min_size_of_attack += 3
            next_turn_to_increment += 10

        if (game_state.turn_number > 2 and game_state.get_resource(game_state.BITS) >= min_size_of_attack): # might want to switch this up
            self.build_left_wall(game_state)
            self.build_right_wall(game_state)


            # We can tell that corners are blocked when the second step in the path has a lower y
            for location in blocked_release_locations:
                path = game_state.find_path_to_edge(location)
                if (path is not None and len(path) > 2):
                    if (path[0][1] > path[1][1]): # TODO: Chck this does not throw error
                        release_locations.insert(0, location) # these locations should have priority

            game_state.attempt_spawn(PING, self.best_spawn_calculation(game_state, release_locations), 10000)

    def build_left_wall(self, game_state):
        left_wall_locations = [[12, 3], [11, 4], [10, 5], [9, 6], [8, 7], [7, 8], [6, 9], [5, 10], [4, 11]]
        game_state.attempt_spawn(ENCRYPTOR, left_wall_locations)

    def build_right_wall(self, game_state):
        right_wall_locations = [[15, 3], [16, 4], [17, 5], [18, 6], [19, 7], [20, 8], [21, 9], [22, 10], [23, 11]]
        game_state.attempt_spawn(ENCRYPTOR, right_wall_locations)

    def best_spawn_calculation(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.

        It will also search for what defenses are on the path that it can add (NOT YET ADDED)
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(DESTRUCTOR, game_state.config).damage
                # TODO: Get number of shields to subtract!!!!
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    # def get_buffers(self, game_map, location, player_index):
    #     """Gets the encryptors threatening a given location

    #     Args:
    #         * location: The location of a hypothetical defender
    #         * player_index: The index corresponding to the defending player, 0 for you 1 for the enemy

    #     Returns:
    #         A list of encryptors that would attack a unit controlled by the given player at the given location

    #     """

    #     encryptors = []
    #     """
    #     Get locations in the range of DESTRUCTOR units
    #     """
    #     possible_locations= game_map.get_locations_in_range(location, self.config["unitInformation"][UNIT_TYPE_TO_INDEX[ENCRYPTOR]]["range"])
    #     for location in possible_locations:
    #         for unit in self.game_map[location]:
    #             if unit.unit_type == ENCRYPTOR and unit.player_index != player_index:
    #                 attackers.append(unit)
    #     return attackers

    def get_ratio_for_defense(self, game_state):
        scale_defense = 1
        if (game_state.enemy_health < 20):
            scale_defense = 0.8
        elif (game_state.enemy_health < 10):
            scale_defense = 0.5
        elif (game_state.enemy_health < 5):
            scale_defense = 0.3

        if (game_state.turn_number > 15): # only during a high turn
            if (game_state.my_health > 35):
                return 0.5 * scale_defense
            elif (game_state.my_health > 30):
                return 0.75 * scale_defense
            elif (game_state.my_health > 25):
                return 0.8 * scale_defense
                
        return 1
        

    ''' DANIEL '''
    def static_defense(self, game_state):

        filter_points = [[1, 13], [26, 13], [6, 13], [21, 13], [11, 13], [16, 13]]
        destructor_points = [[1, 12], [26, 12], [6, 12], [21, 12], [11, 12], [16, 12]]

        if game_state.turn_number == 0:
            game_state.attempt_spawn(FILTER, filter_points)
            game_state.attempt_spawn(DESTRUCTOR, destructor_points)

        else:
            filter_points.extend([[0, 13], [27, 13], [2, 13], [25, 13], [8, 13], [19, 13], [17, 13], [10, 13], [23, 13]])
            destructor_points.extend([[3, 13], [24, 13], [3, 12], [24, 12], [7, 12], [20, 12], [22, 12], [10, 12], [5, 12], [17, 1]])

        
            game_state.attempt_spawn(FILTER, filter_points)
            game_state.attempt_spawn(DESTRUCTOR, destructor_points)

            full13 = game_state.attempt_spawn(FILTER, row13)
            full12 = game_state.attempt_spawn(DESTRUCTOR, row12)

            if not full13 and not full12:
                mid_filter_points = [[12, 12], [15, 12], [12, 11], [15, 11], [12, 10], [15, 10], [12, 9], [15, 9], [12, 8], [15, 8], [12, 7], [15, 7], [12, 6], [15, 6], [12, 5], [15, 5]]
                gamelib.debug_write(mid_filter_points)
                game_state.attempt_spawn(FILTER, mid_filter_points)

                # # y - 11 to 16 x 11
                mid_destructor_points = [[11, 11], [16, 11], [11, 10], [16, 10], [11, 9], [16, 9], [11, 8], [16, 8], [11, 7], [16, 7], [11, 6], [16, 6], [11, 5], [16, 5], [12, 4], [15, 4], [12, 3], [15, 3]]
                gamelib.debug_write(mid_destructor_points)
                game_state.attempt_spawn(DESTRUCTOR, mid_destructor_points)

            extra_destructors = [[6, 11], [7, 11], [8, 11], [9, 11], [10, 11], [17, 11], [18, 11], [19, 11], [20, 11], [21, 11], [10, 10], [17, 10], [10, 9], [17, 9], [10, 8], [17, 8], [10, 7], [17, 7], [10, 6], [17, 6]]

    ''' RYAN '''
    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy EMPs can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place destructors that attack enemy units
        destructor_locations = [[0, 13], [27, 13], [8, 11], [19, 11], [13, 11], [14, 11]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        for destructor_location in destructor_locations:
            success = game_state.attempt_spawn(DESTRUCTOR, destructor_location)
            if success == 1:
                new_filter_location = [destructor_location[0] + 1, destructor_location[1]]
                game_state.attempt_spawn(FILTER, new_filter_location)
       # for destructor_death in self.destructor_deaths:
        #    game_state.attempt_spawn(destructor_death)
         #   new_filter_location = [destructor_death[0] + 1, destructor_death[1] - 1]
          #  game_state.attempt_spawn(FILTER, new_filter_location)
           # self.destructor_deaths.clear()
        # Place filters in front of destructors to soak up damage for them
        game_state.attempt_spawn(DESTRUCTOR, destructor_locations)
        filter_locations = [[8, 12], [19, 12]]
        game_state.attempt_spawn(FILTER, filter_locations)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build destructor one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(DESTRUCTOR, build_location)

    def stall_with_scramblers(self, game_state):
        """
        Send out Scramblers at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own firewalls 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining bits to spend lets send out scramblers randomly.
        while game_state.get_resource(game_state.BITS) >= game_state.type_cost(SCRAMBLER) and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(SCRAMBLER, deploy_location)
            """
            We don't have to remove the location since multiple information 
            units can occupy the same space.
            """

    def emp_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our EMP's can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [FILTER, DESTRUCTOR, ENCRYPTOR]
        cheapest_unit = FILTER
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost < gamelib.GameUnit(cheapest_unit, game_state.config).cost:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our EMPs from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn EMPs next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(EMP, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(DESTRUCTOR, game_state.config).damage
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at: https://docs.c1games.com/json-docs.html
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
