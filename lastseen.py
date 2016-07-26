#Plugin for crowd sourcing when/where something was last seen.

from errbot import BotPlugin, botcmd
from errbot.templating import tenv
import datetime
import math
import dateutil.relativedelta

def human_readable_offset(time1, time2):
  # Credit for the core cleverness to Sharoon Thomas:
  # http://code.activestate.com/recipes/578113-human-readable-format-for-a-given-time-delta/
  delta = dateutil.relativedelta.relativedelta(time1, time2)
  attrs = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']
  statements = ['%d %s' % (getattr(delta, attr), getattr(delta, attr) != 1 and attr or attr[:-1])
      for attr in attrs if getattr(delta, attr)]

  if len(statements) > 1:
    statements[-1] = "and {0}".format(statements[-1])
  return ', '.join(statements)

class LastSeen(BotPlugin):
  min_err_version = "1.6.0"

  @botcmd(split_args_with=None)
  def scout(self, mess, args):
    if not self['sightings']:
      self['sightings'] = {}

    for ii in args:
      if ii in self['sightings']:
        pass

  @botcmd(split_args_with='@')
  def spot(self, mess, args):

    if len(args) < 2:
      return "Report should be in the form of Target@Location"
    details = {
    'user': mess.frm,
    'location': args[1],
    'timestamp': datetime.datetime.now()
    }

    if not self['sightings']:
      self['sightings'] = {}
    self['sightings'][args[0]] = details

    return "Sighting of {0} recorded.".format(args[0])

  def _print_sighting(tgt, sighting):
    args = {'tgt': tgt}
    if sighting:
      args['location'] = sighting['location']
      args['user'] = sighting['user']
      args['timestamp'] = human_readable_offset(sighting['timestamp'], datetime.datetime.now())

    if not sighting:
      return tenv.get_template('miss.md').render
      return "{0} has no sightings reported.".format(tgt)
    else:
      response = "{tgt} was last reported at {location} by {user} {time} ago"
      return .format