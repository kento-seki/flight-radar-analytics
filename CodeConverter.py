#!/usr/bin/env python3

import pandas as pd

class CodeConverter():
    """
    A class that manages conversions of IATA/ICAO codes to names for aircraft
    types, airports, and airlines.
    """

    def __init__(self):
        pass

    def get_aircraft_family(self, code):

        # These are the FIRST 3 CHARACTERS from the ICAO/IATA aircraft type code
        families = {
            'A320': ('320', '321', '32Q', '32X', '32Y', 'A20', 'A21', 'A32'),
            'A330': ('330', '332', '333', '33F', '33L', '33V', '33X', 'A33'),
            'A340': ('340', '342', '343', '345', '346'),
            'A350': ('350', '351', '359', '35K', '35X', 'A35'),
            'A380': ('380', '388', 'A38'),
            'BA146': ('146', 'B46', '14Y', '14Z'),
            'B717': ('717', '71F', '71M', '71Q', '71R', '71W', 'B71'),
            'B737': ('738', '73H', '73J', '73M', '73W', '73X', '73Y', '7S8', 'B38', 'B73'),
            'B747': ('74F', '74Y', '744', '74E', '74H', '74J', '74M', '74N', '74R', '74W', '74X', 'B74'),
            'B767': ('763', '76W', '76Z', '76V'),
            'B777': ('77F', '77L', '77W', '77X', '77Y', 'B77'),
            'B787': ('788', '789', '78X', '78Z', 'B78'),
            'E190': ('E90'),
            'DHC8': ('DH8', 'DHC', 'DHT', 'DH3', 'DH4'),
            'S340': ('SF3')
        }
        for family, codes in families.items():
            if code[:3] in codes:
                return family
        return 'Unknown'

    def get_aircraft_families(self, flights, write_CSV=False):
        """
        Given a list of flight JSON objects, identifies the family each aircraft
        belongs to and returns a pandas dataframe with unique records of the
        aircraft code, name, and family.
        """
        columns = ['code', 'name', 'family']
        aircraft_list = []

        for fl in flights:
            if fl['flight']['aircraft'] is None:
                continue
            aircraft = fl['flight']['aircraft']['model']
            code = aircraft['code']
            name = aircraft['text']
            family = self.get_aircraft_family(code)

            aircraft_list.append([code, name, family])

        aircrafts = pd.DataFrame(aircraft_list, columns=columns)
        aircrafts = aircrafts.drop_duplicates()
        if write_CSV:
            aircrafts.to_csv('aircrafts.csv', index=False)

        return aircrafts
