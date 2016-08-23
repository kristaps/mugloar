#!/usr/bin/env python

from __future__ import print_function

import argparse
from collections import Counter
from xml.etree import ElementTree
from decimal import Decimal
import requests

GAME_URL = 'http://www.dragonsofmugloar.com/api/game'
SPECIFIC_GAME_URL = '{}/{{}}'.format(GAME_URL)
WEATHER_URL = 'http://www.dragonsofmugloar.com/weather/api/report/{game_id}'
SOLUTION_URL = GAME_URL + '/{game_id}/solution'


class Weather(object):
    NORMAL = 'NMR'
    STORM = 'SRO'
    RAIN = 'HVA'
    DROUGHT = 'T E'
    FOG = 'FUNDEFINEDG'


class DragonStat(object):
    SCALE_THICKNESS = 'scaleThickness'
    CLAW_SHARPNESS = 'clawSharpness'
    FIRE_BREATH = 'fireBreath'
    WING_STRENGTH = 'wingStrength'

    RAIN_STATS = (CLAW_SHARPNESS, SCALE_THICKNESS, WING_STRENGTH)


STAT_MAP = {
    'attack': DragonStat.SCALE_THICKNESS,
    'armor': DragonStat.CLAW_SHARPNESS,
    'endurance': DragonStat.FIRE_BREATH,
    'agility': DragonStat.WING_STRENGTH,
}


def transfer_stat_points(dragon, from_stat, to_stat, limit=1):
    points = min(limit, 10 - dragon[to_stat], dragon[from_stat])
    dragon[from_stat] -= points
    dragon[to_stat] += points


def design_dragon(knight, weather):
    if weather == Weather.STORM:
        return None

    elif weather == Weather.DROUGHT:
        return {stat: 5 for stat in STAT_MAP.values()}

    if weather == Weather.RAIN:
        dragon = {stat: 0 for stat in STAT_MAP.values()}
        dragon[DragonStat.CLAW_SHARPNESS] = 10
        dragon[DragonStat.SCALE_THICKNESS] = 10

        return dragon

    # Copy the knight's stats into the dragon stat counterparts
    dragon = {STAT_MAP[stat]: value for stat, value in knight.items() if stat in STAT_MAP}

    # Order the stats by assigned points in descending order
    ranked_stats = [
        stat[0]
        for stat
        in sorted(dragon.items(), key=lambda x: x[1], reverse=True)
        if stat[1] > 0
    ]

    # The first item corresponds to the knight's strongest stat - the
    # one we need to beat by 2 points to win. The other stats will be
    # reduced to obtain the required boost.
    boost_stat, donor_stats = ranked_stats[0], ranked_stats[1:]

    for donor_stat in donor_stats:
        transfer_stat_points(dragon, donor_stat, boost_stat)

    dragon['name'] = 'Trogdor'  # +10 burnination

    return dragon


def play_game(game_id=None, verbose=False):
    if game_id is not None:
        game = requests.get(SPECIFIC_GAME_URL.format(game_id)).json()

    else:
        game = requests.get(GAME_URL).json()
        game_id = game['gameId']

    knight = game['knight']

    weather_body = requests.get(WEATHER_URL.format(game_id=game_id)).content
    weather = ElementTree.fromstring(weather_body).find('code').text

    dragon = design_dragon(knight, weather)

    result = submit_solution(game_id, dragon)
    status = result['status']

    print("Game: {}, result: {}".format(game_id, status))
    if verbose:
        print("Knight:", knight)
        print("Dragon:", dragon)
        print()

    did_win = status == 'Victory'
    if not did_win:
        print(result)
        print(weather)
        print(knight)
        print(dragon)
        print()

    return did_win


def submit_solution(game_id, dragon):
    resp = requests.put(
        SOLUTION_URL.format(game_id=game_id),
        json={
            'dragon': dragon
        }
    )
    return resp.json()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-n',
        dest='game_count',
        type=int,
        default=1,
        help='How many games to play'
    )
    parser.add_argument(
        '-g',
        dest='game_id',
        type=int,
        help='Id of specific game to play'
    )
    parser.add_argument(
        '-v',
        dest='verbose',
        action='store_true',
        help='Print knight and dragon data for each game'
    )

    args = parser.parse_args()

    if args.game_id is not None:
        play_game(args.game_id, verbose=args.verbose)

    else:
        results = Counter()
        for i in range(args.game_count or 1):
            results[play_game(verbose=args.verbose)] += 1

        won_count, lost_count = results[True], results[False]
        played_count = won_count + lost_count

        print()
        print("Played:", played_count)
        print("Won:", won_count)
        print("Lost:", lost_count)
        print("Win ratio: {:.0f}%".format(
            Decimal(won_count) / Decimal(played_count) * Decimal(100)
        ))
