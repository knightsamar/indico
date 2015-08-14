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

from __future__ import unicode_literals

from datetime import date, timedelta
from uuid import uuid4

from indico.core.db import db
from indico.modules.events.surveys.models.surveys import Survey
from indico.modules.events.surveys.models.questions import SurveyQuestion
from indico.modules.events.surveys.models.submissions import SurveySubmission, SurveyAnswer
from indico.modules.users import User
from indico.util.console import cformat
from indico.util.date_time import localize_as_utc
from indico.util.struct.iterables import committing_iterator
from indico_zodbimport import Importer, convert_to_unicode


class SurveyImporter(Importer):
    def has_data(self):
        return Survey.has_rows

    def migrate(self):
        self.print_step("Migrating old event evaluations")
        for event, evaluation in committing_iterator(self._iter_evaluations(), 10):
            db.session.add(self.migrate_survey(evaluation, event))
        self.update_merged_users(SurveySubmission.user, "survey submissions")

    def migrate_survey(self, evaluation, event):
        survey = Survey(event=event)
        survey.title = convert_to_unicode(evaluation.title) if evaluation.title else "Evaluation"
        survey.introduction = convert_to_unicode(evaluation.announcement)
        if evaluation.contactInfo:
            survey.introduction += "\n\nContact: {}".format(convert_to_unicode(evaluation.contactInfo))
        survey.submission_limit = evaluation.submissionsLimit if evaluation.submissionsLimit else None
        survey.anonymous = evaluation.anonymous
        # Guest users can only submit if survey is not anonymous
        survey.require_user = not survey.anonymous and not evaluation.mandatoryAccount

        if evaluation.startDate.date() == date.min or evaluation.endDate.date() == date.min:
            survey.start_dt = event.endDate
            survey.end_dt = survey.start_dt + timedelta(days=7)
        else:
            survey.start_dt = localize_as_utc(evaluation.startDate, event.tz)
            survey.end_dt = localize_as_utc(evaluation.endDate, event.tz)
        if survey.end_dt < survey.start_dt:
            survey.end_dt = survey.end_dt + timedelta(days=7)

        self.print_success(cformat('%{cyan}{}%{reset}').format(survey), event_id=event.id, always=True)

        question_map = {}
        for position, old_question in enumerate(evaluation._questions):
            question = self.migrate_question(old_question, position)
            question_map[old_question] = question
            survey.questions.append(question)

        for old_submission in evaluation._submissions:
            submission = self.migrate_submission(old_submission, question_map, event.tz)
            survey.submissions.append(submission)

        return survey

    def migrate_question(self, old_question, position):
        question = SurveyQuestion()
        question.position = position
        question.title = convert_to_unicode(old_question.questionValue)
        question.description = convert_to_unicode(old_question.description)
        question.is_required = old_question.required
        question.field_data = {}
        class_name = old_question.__class__.__name__
        if class_name == 'Textbox':
            question.field_type = 'text'
        elif class_name == 'Textarea':
            question.field_type = 'text'
            question.field_data['multiline'] = True
        elif class_name == 'Password':
            question.field_type = 'text'
        elif class_name in ('Checkbox', 'Radio', 'Select'):
            question.field_type = 'single_choice' if class_name == 'Radio' else 'multiselect'
            question.field_data['options'] = []
            for option in old_question.choiceItems:
                question.field_data['options'].append({'option': option, 'id': unicode(uuid4())})
        self.print_success(" - Question: {}".format(question.title))
        return question

    def migrate_submission(self, old_submission, question_map, timezone):
        submission = SurveySubmission()
        submitted_dt = old_submission.submissionDate
        submission.submitted_dt = submitted_dt if submitted_dt.tzinfo else localize_as_utc(submitted_dt, timezone)
        if not old_submission.anonymous and old_submission._submitter:
            avatar = old_submission._submitter
            with db.session.no_autoflush:
                submission.user = User.get(int(avatar.id))
        self.print_success(" - Submission from user {}".format(submission.user_id or 'anonymous'))
        for old_answer in old_submission._answers:
            question = question_map[old_answer._question]
            answer = self.migrate_answer(old_answer, question)
            submission.answers.append(answer)
            question.answers.append(answer)
        return submission

    def migrate_answer(self, old_answer, question):
        answer = SurveyAnswer()
        if old_answer.__class__.__name__ == 'MultipleChoicesAnswer':
            answer.data = []
            for option in old_answer._selectedChoiceItems:
                answer.data.append(self._get_option_id(question, option))
        elif old_answer._question.__class__.__name__ in ('Radio', 'Select'):
            if old_answer._answerValue:
                answer.data = self._get_option_id(question, old_answer._answerValue)
        else:
            answer.data = convert_to_unicode(old_answer._answerValue)
        self.print_success("   - Answer: {}".format(answer.data))
        return answer

    def _iter_evaluations(self):
        for event in self.flushing_iterator(self.zodb_root['conferences'].itervalues()):
            for evaluation in event._evaluations:
                if evaluation._questions:
                    yield event, evaluation

    def _get_option_id(self, question, option):
        return next((opt['id'] for opt in question.field_data['options'] if opt['option'] == option), None)