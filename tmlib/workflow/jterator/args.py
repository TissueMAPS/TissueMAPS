# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from tmlib.workflow.args import Argument
from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.args import ExtraArguments
from tmlib.workflow import register_step_batch_args
from tmlib.workflow import register_step_submission_args
from tmlib.workflow import register_step_extra_args


@register_step_batch_args('jterator')
class JteratorBatchArguments(BatchArguments):

    plot = Argument(
        type=bool, default=False, flag='p', disabled=True,
        help='whether plotting should be activated'
    )

    batch_size = Argument(
        type=int, help='number of sites that should be processed per job',
        default=100, flag='b'
    )


@register_step_submission_args('jterator')
class JteratorSubmissionArguments(SubmissionArguments):

    pass


def get_names_of_existing_pipelines(experiment):
    '''Gets names of all existing jterator pipelines for a given experiment.

    Parameters
    ----------
    experiment: tmlib.models.Experiment
        processed experiment

    Returns
    -------
    List[str]
        names of jterator pipelines
    '''
    import os
    from tmlib.workflow.jterator.project import list_projects
    directory = os.path.join(experiment.workflow_location, 'jterator')
    if not os.path.exists(directory):
        return []
    else:
        return [
            os.path.basename(project)
            for project in list_projects(directory)
        ]


@register_step_extra_args('jterator')
class JteratorExtraArguments(ExtraArguments):

    pipeline = Argument(
        type=str, help='name of the pipeline that should be processed',
        required=True, flag='p', get_choices=get_names_of_existing_pipelines
    )
