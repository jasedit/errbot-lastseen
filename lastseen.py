#Plugin for crowd sourcing when/where something was last seen.

from errbot import BotPlugin, botcmd
from errbot.backends.base import Person
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

    def _get_name(self, text):
        """Attempts to extract a username from the text, returning the direct text otherwise."""
        try:
            person = self.build_identifier(text)
            if isinstance(person, Person):
                return "@{0}".format(person.username)
        except ValueError:
            pass
        return text

    @botcmd(split_args_with=',')
    def scout_find(self, mess, args):
        """Attempt to get the last reported location of an object of interest. Accepts a comma separated list of names."""
        if 'sightings' not in self:
           self['sightings'] = {}
        for ii in args:
            person = self._get_name(ii)
            yield self._report_sighting(person)

    @botcmd(split_args_with=';')
    def scout_spot(self, mess, args):
        """Reports the location of an object of interest. Arguments must be in the form of Object;Location."""
        if len(args) < 2:
            return "Report should be in the form of Target;Location"
        details = {
            'user': "@{0}".format(mess.frm.username),
            'location': args[1],
            'timestamp': datetime.datetime.now()
        }

        target = self._get_name(args[0])
        if 'sightings' not in self:
            sight = {}
        else:
            sight = self['sightings']

        sight[target] = details
        self['sightings'] = sight

        return "Sighting of {0} recorded.".format(target)

    @botcmd(split_args_with=',', admin_only=True)
    def scout_remove(self, mess, args):
        """Admin command to remove specific sightings."""
        if 'sightings' not in self:
            return
        sight = self['sightings']
        removed = []
        for ii in args:
            if ii in sight:
                del sight[ii]
                removed.append(ii)
        self['sightings'] = sight
        if removed:
            return 'Removed {0}'.format(', '.join(removed))
        else:
            return "No sightings removed."

    @botcmd(admin_only=True)
    def scout_clear(self, mess, args):
        """Admin command to clear all sightings from the database."""
        if 'sightings' in self:
            self['sightings'] = {}

        return "All sightings removed."

    def _report_sighting(self, tgt):
        """Attempts to find and report a sighting of the given target."""
        args = {'target': tgt}
        if tgt in self['sightings']:
            sighting = self['sightings'][tgt]
            args['location'] = sighting['location']
            args['user'] = sighting['user']
            args['timestamp'] = human_readable_offset(datetime.datetime.now(), sighting['timestamp'])

        if 'location' not in args:
            return tenv().get_template('miss.md').render(target=tgt)
        else:
            return tenv().get_template('report.md').render(**args)
