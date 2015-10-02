# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
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

from flask import request

from indico.modules.events.registration.models.forms import RegistrationForm


class RegistrationFormMixin(object):
    """Mixin for single registration form RH"""

    normalize_url_spec = {
        'locators': {
            lambda self: self.regform
        }
    }

    def _checkParams(self):
        self.regform = RegistrationForm.find_one(id=request.view_args['reg_form_id'], is_deleted=False)