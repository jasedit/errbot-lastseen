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

    def _check_storage(self):
        if 'sightings' not in self:
            self['sightings'] = {}
        if 'aliases' not in self:
            self['aliases'] = {}

    def _get_name(self, text):
        """Attempts to extract a username from the text, returning the direct text otherwise."""
        text = self['aliases'][text] if text in self['aliases'] else text
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
        self._check_storage()
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
        self._check_storage()
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
        self._check_storage()

        return "All sightings removed."

    @botcmd(split_args_with=';')
    def scout_alias(self, mess, args):
        """Add an alias for a given name - maps one name for a sighting to another.
        Arguments should be written as source;target, where target is the desired final name.
        """
        if len(args) is not 2:
            return "Argument requires two arguments separated by a ;"
        self._check_storage()

        source = args[0]
        target = args[1]
        aliases = self['aliases']

        if source not in aliases:
            aliases[source] = target
            self['aliases'] = aliases
            return "Added alias {0} to {1}.".format(source, target)

    @botcmd(split_args_with=';')
    def scout_rmalias(self, mess, args):
        """Removes the provided list of aliases."""
        self._check_storage()
        aliases = self['aliases']
        for ii in args:
            aliases.pop(ii, None)
        self['aliases'] = aliases

    @botcmd
    def scout_lsalias(self, mess, args):
        self._check_storage()
        if len(self['aliases']) == 0:
            return "No aliases currently listed."

        for ii, jj in self['aliases'].items():
            yield "{0} maps to {1}".format(ii, jj)

    @botcmd(admin_only=True)
    def scout_compact(self, mess):
        """Update all sightings using the alias map as a cleanup operation."""
        self._check_storage()
        sightings = self['sightings']
        updates = {} #Map from old name to new
        for ii in sightings:
            if ii in self['aliases']:
                updates[ii] = self['aliases'][ii]
        #Map is built, now update the sightings
        for ii, jj in updates:
            if jj not in sightings or sightings[ii]['timestamp'] < sightings[jj]['timestamps']:
                sightings[jj] = sightings[ii]
                del sightings[ii]

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
