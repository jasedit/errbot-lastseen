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
    """Plugin which allows users to report and request location of objects of interest."""
    min_err_version = "1.6.0"

    @botcmd(split_args_with=',')
    def scout(self, mess, args):
        """Attempt to get the last reported location of an object of interest. Accepts a comma separated list of names."""
      if 'sightings' not in self:
          self['sightings'] = {}

      for ii in args:
          if ii in self['sightings']:
            yield self._print_sightings(ii, self['sightings'][ii])

    @botcmd(split_args_with=';')
    def spot(self, mess, args):
        """Reports the location of an object of interest. Arguments must be in the form of Object;Location."""
        if len(args) < 2:
            return "Report should be in the form of Target;Location"
        details = {
            'user': mess.frm,
            'location': args[1],
            'timestamp': datetime.datetime.now()
        }

        if 'sightings' not in self:
            self['sightings'] = {}
        self['sightings'][args[0]] = details

        return "Sighting of {0} recorded.".format(args[0])

    def _print_sighting(self, tgt, sighting):
        """Attempts to find and report a sighting of the given target."""
        args = {'target': tgt}
        if sighting:
            args['location'] = sighting['location']
            args['user'] = sighting['user']
            args['timestamp'] = human_readable_offset(sighting['timestamp'], datetime.datetime.now())

        if not sighting:
            return tenv.get_template('miss.md').render(target=tgt)
        else:
            return tenv.get_template('report.md').render(**args)