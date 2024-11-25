#!/usr/bin/env python3

import requests
from datetime import datetime, timedelta
import time
import json
import pandas as pd

# FIXME: safeguard against dictionary keyErrors
# TODO: add support for airports in a different timezone!

class AirportDataRequester():

    def __init__(self, airport):
        """
        Args:
            airport (str): The airport ICAO code
        """
        self.airport = airport


    def get_departures(self, timestamp=None) -> list[dict]:
        """
        Returns a list of dictionaries, each containing information about a
        departing flight.

        Returns:
            list<dict> : the list of dictionaries containing flight information
        """
        flights = []

        response = self.__airport_schedule_request(timestamp=timestamp, arrivals=False)
        flights.extend(self.__extract_departures(response))
        num_pages = self.__extract_num_pages(response, False)
        for i in range(2, num_pages + 1):
            response = self.__airport_schedule_request(timestamp=timestamp, arrivals=False, page=i)
            flights.extend(self.__extract_departures(response))

            if self.__check_if_day_done(flights, timestamp, 'departure'):
                break

        return flights


    def get_arrivals(self, timestamp=None) -> list[dict]:
        """
        Returns a list of dictionaries, each containing information about an
        arriving flight.

        Returns:
            list<dict> : the list of dictionaries containing flight information
        """
        flights = []

        response = self.__airport_schedule_request(timestamp=timestamp, arrivals=True)
        flights.extend(self.__extract_arrivals(response))
        num_pages = self.__extract_num_pages(response, True)
        for i in range(2, num_pages + 1):
            response = self.__airport_schedule_request(timestamp=timestamp, arrivals=True, page=i)
            flights.extend(self.__extract_arrivals(response))

            if self.__check_if_day_done(flights, timestamp, 'arrival'):
                break

        return flights

    def __check_if_day_done(self, flights, timestamp, mode):
        day = datetime.fromtimestamp(timestamp)
        next_day = day + timedelta(days=1)
        next_day_start = datetime(next_day.year, next_day.month, next_day.day, 0, 0, 0)
        next_day_start_unix = int(time.mktime(next_day_start.timetuple()))

        if flights[-1]['flight']['time'] != None:
            return flights[-1]['flight']['time']['scheduled'][mode] > next_day_start_unix


    def __extract_num_pages(self, response, arrivals):
        mode = 'arrivals' if arrivals else 'departures'
        return response['result']['response']['airport']['pluginData']['schedule'][mode]['page']['total']


    def __extract_departures(self, response):
        """
        Given the JSON response, returns the list of flight dictionaries.
        """
        return response['result']['response']['airport']['pluginData']['schedule']['departures']['data']


    def __extract_arrivals(self, response):
        """
        Given the JSON response, returns the list of flight dictionaries.
        """
        return response['result']['response']['airport']['pluginData']['schedule']['arrivals']['data']


    def __airport_schedule_request(self, timestamp=None, arrivals=True, write_to_file=False, page=1):
        """
        Gets the current schedule for the given airport, focusing on arrivals by
        default.

        Args:
            timestamp (int) : The UNIX timestamp for the start of the 24-hour window
            arrivals (bool) : Whether to get the arrivals instead of departures
            write_to_file (bool) : Whether to write the JSON data to a file

        Returns:
            str: The JSON object (python dict) returned by the request
        """
        mode = 'arrivals' if arrivals else 'departures'
        limit = 100
        timestamp = int(time.time()) if timestamp is None else timestamp

        url = f'https://api.flightradar24.com/common/v1/airport.json?code={self.airport}&plugin[]=schedule&plugin-setting[schedule][mode]={mode}&plugin-setting[schedule][timestamp]={timestamp}&limit={limit}&page={page}'
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0) Gecko/20100101 Firefox/42.0'}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status() # if failed raise exception

            parsed_json = json.loads(response.text)
            pretty_json = json.dumps(parsed_json, indent=4)
            if write_to_file:
                with open(f'{self.airport}_{mode}.json', 'w') as file:
                    file.write(pretty_json)

            return json.loads(pretty_json)

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"An error occurred: {err}")


    def __select_json_fields(self, flight) -> dict:
        """
        Given a single flight (represented by a dictionary), return a dictionary
        with only some fields.
        """
        flight = flight['flight']
        is_arrival = False

        originCode = flight['airport']['origin'].get('code', {})
        if originCode != {}:
            originCode = originCode['icao']
            is_arrival = True
        else:
            originCode = self.airport

        destCode = flight['airport']['destination'].get('code', {})
        destCode = destCode['icao'] if destCode != {} else self.airport

        # FIXME: in what cases is the airline null?
        airline = flight['airline']['code']['icao'] if flight['airline'] != None else ''

        # FIXME: in what cases is the aircraft is null?
        aircraft = flight['aircraft']['model']['code'] if flight['aircraft'] != None else ''

        # FIXME: in what cases is the flight number null?
        flightNum = flight['identification']['number']['default'] if flight['identification'] != None else ''

        timeAppearance = flight['time']['scheduled']['arrival'] if is_arrival \
                else flight['time']['scheduled']['departure']
        if timeAppearance != None and timeAppearance != '':
            dt_object = datetime.fromtimestamp(timeAppearance)

        return {
            'origin': originCode,
            'destination': destCode,
            'aircraft': aircraft,
            'airline': airline,
            'flightNumber': flightNum,
            'scheduled': dt_object
        }

    def __JSON_to_dataframe(self, flights, timestamp):
        date_obj = datetime.fromtimestamp(timestamp)
        next_day = date_obj + timedelta(days=1)
        next_day_start = datetime(next_day.year, next_day.month, next_day.day, 0, 0, 0)

        flights = [self.__select_json_fields(fl) for fl in flights]
        df = pd.DataFrame(flights)

        return df[df['scheduled'] < next_day_start] # filter for flights on the same day

    def get_arrivals_dataframe(self, timestamp=None):
        flights = self.get_arrivals(timestamp)
        return self.__JSON_to_dataframe(flights, timestamp)

    def get_departures_dataframe(self, timestamp=None):
        flights = self.get_departures(timestamp)
        return self.__JSON_to_dataframe(flights, timestamp)

    def get_flights_dataframe(self, timestamp=None):
        """
        Returns the remaining flights to the end of the day given by `timestamp`
        obtained by get_departures() and get_arrivals() as a pandas dataframe.
        Resets the index of the dataframe.

        Args:
            timestamp (int) : the UNIX time from which to start the 24-hour window
        Returns:
            pandas dataframe : a dataframe where each row is a flight
        """
        departures = self.get_departures_dataframe(timestamp)
        arrivals = self.get_arrivals_dataframe(timestamp)
        return pd.concat((departures, arrivals), axis=0, ignore_index=True)


if __name__ == "__main__":

    syd = AirportDataRequester("YSSY")
    # print(syd.get_flights_dataframe().head())

    lax = AirportDataRequester("KLAX")
