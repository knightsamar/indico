# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from flask import session

from indico.core.db import db
from indico.modules.events import EventLogKind, EventLogRealm, logger
from indico.modules.events.layout import layout_settings
from indico.modules.events.models.references import ReferenceType


def create_reference_type(data):
    reference_type = ReferenceType()
    reference_type.populate_from_dict(data)
    db.session.add(reference_type)
    db.session.flush()
    logger.info('Reference type "%s" created by %s', reference_type, session.user)
    return reference_type


def update_reference_type(reference_type, data):
    reference_type.populate_from_dict(data)
    db.session.flush()
    logger.info('Reference type "%s" updated by %s', reference_type, session.user)


def delete_reference_type(reference_type):
    db.session.delete(reference_type)
    db.session.flush()
    logger.info('Reference type "%s" deleted by %s', reference_type, session.user)


def create_event_references(event, data):
    event.references = data['references']
    db.session.flush()
    for reference in event.references:
        logger.info('Reference "%s" created by %s', reference, session.user)


def create_event(category, event_type, data):
    from MaKaC.conference import Conference
    conf = Conference.new(category, creator=session.user, title=data.pop('title'), start_dt=data.pop('start_dt'),
                          end_dt=data.pop('end_dt'), timezone=data.pop('timezone'), event_type=event_type)
    event = conf.as_event
    theme = data.pop('theme', None)
    if theme is not None:
        layout_settings.set(event, 'timetable_theme', theme)
    event.populate_from_dict(data)
    db.session.flush()
    logger.info('Event %r created in %r by %r ', event, category, session.user)
    event.log(EventLogRealm.event, EventLogKind.positive, 'Event', 'Event created', session.user)
    return event


def update_event(event, data):
    event.populate_from_dict(data)
    db.session.flush()
    logger.info('Event %r updated with %r', event, data)


def delete_event(event):
    event.as_legacy.delete(session.user)
    db.session.flush()
    logger.info('Event %r deleted by %r', event, session.user)
