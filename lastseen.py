#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#Plugin for crowd sourcing when/where something was last seen.

from errbot import BotPlugin, botcmd, arg_botcmd
from errbot.backends.base import Person
from errbot.templating import tenv
import yaml
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
        if 'info' not in self:
            self['info'] = {}

    def _get_name(self, text):
        """Attempts to extract a username from the text, returning the direct text otherwise."""
        text = self['aliases'][text] if text in self['aliases'] else text
        try:
            person = self.build_identifier(text)
            if isinstance(person, Person):
                return self.build_identifier("@{0}".format(person.username))
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

    @arg_botcmd('name', type=str)
    @arg_botcmd('-l', '--list', action='store_true', dest='list_info', default=False)
    @arg_botcmd('-u', '--update', default=None, type=str)
    @arg_botcmd('-r', '--remove', action='store_true', default=False)
    def scout_info(self, mess, name, list_info, remove, update):
        """Get or update information about a particular object of interest."""
        self._check_storage()
        target = self._get_name(name)

        if list_info: #List target information
            yield self._report_info(target)
        elif update: #Update target information
            try:
                self._update_info(target, update)
                yield "Info updated for {0}".format(target)
            except ValueError as exc:
                yield "Error in updating {0}: {1}".format(target, exc)
        elif remove: #Remove information
            try:
                infos = self[info]
                del infos[target]
                self[info] = infos
                yield "Information removed for {0}".format(target)
            except KeyError:
                yield "No information for {0} to remove".format(target)

    @arg_botcmd('name', type=str)
    @arg_botcmd('location', type=str)
    @arg_botcmd('--info', default=None, type=str)
    def scout_spot(self, mess, name=None, location=None, info=None):
        """Reports the location of an object of interest, with optional ability to specify information about an object."""
        details = {
            'user': "@{0}".format(mess.frm.username),
            'location': location,
            'timestamp': datetime.datetime.now()
        }

        target = self._get_name(name)
        self._check_storage()
        
        sight = self['sightings']
        sight[target] = details
        self['sightings'] = sight

        if info:
            try:
                self._update_info(target, info)
            except ValueError as exc:
                yield "Failed to parse info for {0}: {1}".format(target, exc)

        return "Sighting of {0} recorded.".format(target)

    @botcmd(split_args_with=',', admin_only=True)
    def scout_remove(self, mess, args):
        """Admin command to remove specific sightings."""
        if 'sightings' not in self:
            return
        sight = self['sightings']
        info = self['info']
        removed = []
        for ii in args:
            if ii in sight:
                del sight[ii]
                removed.append(ii)
            if ii in info:
                del info[ii]
        self['sightings'] = sight
        self['info'] = info
        if removed:
            return 'Removed {0}'.format(', '.join(removed))
        else:
            return "No sightings removed."

    @arg_botcmd("-i", "--info", admin_only=True, action="store_true", default=False, help="Clears info")
    def scout_clear(self, mess, info=False):
        """Admin command to clear all sightings from the database."""
        self['sightings'] = {}
        if info:
            self['info'] = {}

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
        """Command to update all sightings using the alias map as a cleanup operation."""
        self._check_storage()
        self._compact_sightings()

    def _compact_sightings(self):
        """Compacts all sighting information using alias mapping"""
        old_sightings = self['sightings']
        new_sightings = {}
        updates = {} #Map from old name to new
        new_info = {}
        for ii in old_sightings:
            if ii in self['aliases']:
                updates[ii] = self['aliases'][ii]
        for ii in self['info']:
            if ii in self['aliases']:
                new_info[ii] = self[info][self['aliases'][ii]]
        #Map is built, now update the sightings based on timestamps
        for ii, jj in updates:
            if jj not in new_sightings or old_sightings[ii]['timestamp'] < old_sightings[jj]['timestamps']:
                new_sightings[jj] = old_sightings[ii]
                del sightings[ii]
        self['sightings'] = new_sightings
        self['info'] = new_info

    def _update_info(self, tgt, info_yml):
        """Updates the information for a given target."""
        try:
            info = yaml.load(info_yml)
            #This three-step tango is to deal with how errbot handles persistence
            infos = self['info']
            infos[tgt] = info
            self['info'] = infos
        except yaml.YAMLError as exc:
            raise ValueError(exc)

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

    def _report_info(self, tgt):
        """Attempts to find and report information about a given target through the chat bot."""

        if tgt in self['info']:
            info = self['info'][tgt]
            info_yml = yaml.dump(info, default_flow_style=False, explicit_end=None)
            return tenv().get_template("info.md").render(target=tgt, info=info_yml)
        else:
            return tenv().get_template("miss_info.md").render(target=tgt)
